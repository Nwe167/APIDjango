from rest_framework import viewsets, generics, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import AllowAny
from rest_framework.reverse import reverse
from django.conf import settings
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth.models import User
from datetime import timedelta
import uuid
import mimetypes

from .models import (
    UserProfile, UserSession, UserPreference, UserNotification,
    File, FilePath, FileRevision, FileContentHint, ImageMediaMetadata, VideoMediaMetadata,
    TrashItem, SpamFlag, Permission, ShareLink, ShareLinkAccess, FileRequest, FileRequestSubmission,
    Comment, CommentReply, CommentMention, ActivityFeed, Label, LabelField, FileLabel,
    SearchIndex, SavedSearch, SearchHistory, AuditLog, DLPViolation, Product
)

from .serializers import (
    UserSerializer, UserRegistrationSerializer, UserProfileSerializer, UserSessionSerializer, UserPreferenceSerializer, UserNotificationSerializer,
    FileDetailSerializer, FileListSerializer, FileCreateUpdateSerializer, FilePathSerializer,
    FileRevisionSerializer, FileContentHintSerializer, FileImageMetadataSerializer, FileVideoMetadataSerializer,
    TrashItemSerializer, SpamFlagSerializer,
    PermissionSerializer, PermissionCreateSerializer, ShareLinkSerializer, ShareLinkAccessSerializer,
    FileRequestSerializer, FileRequestSubmissionSerializer,
    CommentSerializer, CommentReplySerializer, CommentMentionSerializer, ActivityFeedSerializer,
    LabelSerializer, LabelFieldSerializer, FileLabelSerializer, SavedSearchSerializer, SearchHistorySerializer, SearchIndexSerializer,
    AuditLogSerializer, DLPViolationSerializer, ProductSerializer
)

from .email_utils import send_file_shared_email, send_file_unshared_email
from .authentication import GlobalTokenRequired, CsrfExemptSessionAuthentication


def refresh_file_shared_state(file_obj):
    """Keep the file's shared flag aligned with active permissions and share links."""
    has_active_permissions = file_obj.permissions.filter(deleted=False).filter(accepted_permission_filter()).exists()
    has_active_share_links = file_obj.share_links.filter(revoked_at__isnull=True).exists()
    is_shared = has_active_permissions or has_active_share_links

    if file_obj.is_shared != is_shared:
        file_obj.is_shared = is_shared
        file_obj.save(update_fields=['is_shared', 'modified_time'])


WRITE_ROLES = {'owner', 'organizer', 'fileOrganizer', 'writer'}


def accepted_permission_filter():
    return Q(share_notifications__share_status=UserNotification.SHARE_ACCEPTED) | Q(share_notifications__isnull=True)


def user_active_permissions(user):
    return Permission.objects.filter(
        grantee_user=user,
        deleted=False
    ).filter(accepted_permission_filter()).distinct()


def get_accessible_file_ids(user):
    """Return files the user owns, files shared with them, and children of accessible folders."""
    accessible_ids = set(
        File.objects.filter(owner=user, trashed=False).values_list('id', flat=True)
    )
    accessible_ids.update(
        user_active_permissions(user)
        .filter(file__trashed=False)
        .values_list('file_id', flat=True)
    )

    while True:
        folder_ids = set(
            File.objects.filter(id__in=accessible_ids, trashed=False)
            .filter(Q(mime_type='folder') | Q(mime_type__icontains='folder'))
            .values_list('id', flat=True)
        )
        child_ids = set(
            File.objects.filter(parent_id__in=folder_ids, trashed=False)
            .values_list('id', flat=True)
        )
        new_ids = child_ids - accessible_ids
        if not new_ids:
            break
        accessible_ids.update(new_ids)

    return accessible_ids


def has_folder_write_access(user, folder):
    """Allow owners or users with writer-like permission on a folder/ancestor to add items."""
    current = folder
    while current:
        if current.owner_id == user.id:
            return True
        if user_active_permissions(user).filter(
            file=current,
            role__in=WRITE_ROLES
        ).exists():
            return True
        current = current.parent
    return False


def has_file_write_access(user, file_obj):
    if file_obj.owner_id == user.id:
        return True
    return user_active_permissions(user).filter(
        file=file_obj,
        role__in=WRITE_ROLES
    ).exists()


def has_file_read_access(user, file_obj):
    if file_obj.owner_id == user.id:
        return True

    current = file_obj
    while current:
        if user_active_permissions(user).filter(file=current).exists():
            return True
        current = current.parent
    return False


def resolve_notification_share_permission(notification):
    """Link older share notifications to their Permission record when possible."""
    if notification.share_permission_id:
        return notification.share_permission

    if notification.notification_type != 'share_received':
        return None

    body = notification.body or ''
    file_name = ''
    if "'" in body:
        parts = body.split("'")
        if len(parts) >= 3:
            file_name = parts[1]

    permissions_qs = Permission.objects.select_related('file').filter(
        grantee_user=notification.user,
    ).order_by('-created_at')

    if file_name:
        exact_matches = [
            permission for permission in permissions_qs
            if permission.file.name == file_name
        ]
        exact_matches.sort(key=lambda permission: permission.deleted)
        if exact_matches:
            permission = exact_matches[0]
            notification.share_permission = permission
            notification.save(update_fields=['share_permission'])
            return permission

    matches = []
    for permission in permissions_qs:
        if permission.file.name and (
            f"'{permission.file.name}'" in body or permission.file.name in body
        ):
            matches.append(permission)

    if matches:
        matches.sort(key=lambda permission: permission.deleted)
        permission = matches[0]
        notification.share_permission = permission
        notification.save(update_fields=['share_permission'])
        return permission

    if permissions_qs.count() == 1:
        permission = permissions_qs.first()
        notification.share_permission = permission
        notification.save(update_fields=['share_permission'])
        return permission

    return None


def get_user_permission_for_file_or_ancestor(user, file_obj):
    """Find the permission that gives a user access to a file or parent folder."""
    current = file_obj
    while current:
        permission = user_active_permissions(user).filter(file=current).first()
        if permission:
            return permission
        current = current.parent
    return None


# ============================================================
# PERMISSIONS
# ============================================================

class IsOwnerOrReadOnly(permissions.BasePermission):
    """Permission to check if user is owner for modifications"""
    def has_permission(self, request, view):
        if request.method == 'POST':
            return request.user and request.user.is_authenticated
        if request.method in permissions.SAFE_METHODS:
            return True
        return True

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return has_file_write_access(request.user, obj)


class CanAccessFile(permissions.BasePermission):
    """Permission to check if user can access file"""
    def has_object_permission(self, request, view, obj):
        file_obj = None
        if hasattr(obj, 'owner'):
            file_obj = obj
        elif hasattr(obj, 'file'):
            file_obj = obj.file
        else:
            return False
        return has_file_read_access(request.user, file_obj)


# ============================================================
# USER VIEWS
# ============================================================

class RegistrationView(generics.CreateAPIView):
    """POST: register a new user (no token needed). GET: list all users (token + admin only)."""
    serializer_class = UserRegistrationSerializer
    authentication_classes = [CsrfExemptSessionAuthentication]
    queryset = User.objects.none()

    def get_permissions(self):
        if self.request.method == 'GET':
            return [GlobalTokenRequired()]
        return [AllowAny()]

    def get(self, request, *args, **kwargs):
        if not request.user or not request.user.is_staff:
            return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)
        users = User.objects.values('id', 'username', 'email').order_by('id')
        return Response(list(users))

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        UserProfile.objects.get_or_create(user=user)
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'message': 'Account created successfully. Please log in.'
        }, status=status.HTTP_201_CREATED)


class UserProfileViewSet(viewsets.ModelViewSet):
    """ViewSet for user profiles"""
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserProfile.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get', 'patch'])
    def me(self, request):
        profile, created = UserProfile.objects.get_or_create(user=request.user)

        if request.method == 'PATCH':
            user_data = request.data.get('user', {})

            if 'password' in user_data:
                request.user.set_password(user_data['password'])
                request.user.save()
                return Response({
                    'message': 'Password changed successfully',
                    'detail': 'Profile updated'
                }, status=status.HTTP_200_OK)

            user_update_fields = ['first_name', 'last_name', 'email']
            user_updated = False
            for field in user_update_fields:
                if field in user_data:
                    setattr(request.user, field, user_data[field])
                    user_updated = True

            if user_updated:
                request.user.save()

            profile_data = {k: v for k, v in request.data.items() if k != 'user'}
            if profile_data:
                serializer = self.get_serializer(profile, data=profile_data, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer.save()

            updated_profile, _ = UserProfile.objects.get_or_create(user=request.user)
            serializer = self.get_serializer(updated_profile)
            return Response(serializer.data, status=status.HTTP_200_OK)

        serializer = self.get_serializer(profile)
        return Response(serializer.data)


class UserPreferenceViewSet(viewsets.ModelViewSet):
    """ViewSet for user preferences"""
    queryset = UserPreference.objects.all()
    serializer_class = UserPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserPreference.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get', 'put'])
    def me(self, request):
        preference, created = UserPreference.objects.get_or_create(user=request.user)

        if request.method == 'PUT':
            serializer = self.get_serializer(preference, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

        serializer = self.get_serializer(preference)
        return Response(serializer.data)


class UserNotificationViewSet(viewsets.ModelViewSet):
    """ViewSet for user notifications"""
    queryset = UserNotification.objects.all()
    serializer_class = UserNotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserNotification.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
        serializer = self.get_serializer(notification)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        UserNotification.objects.filter(user=request.user, is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )
        return Response({'status': 'All notifications marked as read'})

    @action(detail=True, methods=['post'])
    def accept_share(self, request, pk=None):
        notification = self.get_object()
        permission = resolve_notification_share_permission(notification)
        if notification.notification_type != 'share_received' or not permission:
            return Response({'detail': 'This notification is not a share invitation.'}, status=status.HTTP_400_BAD_REQUEST)

        if permission.deleted:
            permission.deleted = False
            permission.revoked_at = None
            permission.revoked_by = None
            permission.save(update_fields=['deleted', 'revoked_at', 'revoked_by'])

        notification.share_status = UserNotification.SHARE_ACCEPTED
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=['share_status', 'is_read', 'read_at'])

        permission.file.shared_with_me_time = timezone.now()
        permission.file.save(update_fields=['shared_with_me_time', 'modified_time'])
        refresh_file_shared_state(permission.file)

        serializer = self.get_serializer(notification)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def decline_share(self, request, pk=None):
        notification = self.get_object()
        permission = resolve_notification_share_permission(notification)
        if notification.notification_type != 'share_received':
            return Response({'detail': 'This notification is not a share invitation.'}, status=status.HTTP_400_BAD_REQUEST)

        if permission and not permission.deleted:
            permission.deleted = True
            permission.revoked_at = timezone.now()
            permission.revoked_by = request.user
            permission.save(update_fields=['deleted', 'revoked_at', 'revoked_by'])
            refresh_file_shared_state(permission.file)

        notification.share_status = UserNotification.SHARE_DECLINED
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=['share_status', 'is_read', 'read_at'])

        serializer = self.get_serializer(notification)
        return Response(serializer.data)


class UserSessionViewSet(viewsets.ModelViewSet):
    """ViewSet for user sessions"""
    queryset = UserSession.objects.all()
    serializer_class = UserSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserSession.objects.filter(user=self.request.user)


# ============================================================
# FILE VIEWS
# ============================================================

@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def create_folder(request):
    if request.method == 'GET':
        return Response({
            'endpoint': request.build_absolute_uri(),
            'method': 'POST',
            'description': 'Create a folder. Pass parent to create a nested folder.',
            'body': {'name': 'New Folder', 'parent': '<optional_parent_folder_id>'},
        })

    name = request.data.get('name')
    parent_id = request.data.get('parent')

    if not name:
        return Response({'detail': 'Folder name is required.'}, status=status.HTTP_400_BAD_REQUEST)

    parent_folder = None
    if parent_id:
        try:
            parent_folder = File.objects.get(id=parent_id, mime_type__icontains='folder')
            if not has_folder_write_access(request.user, parent_folder):
                return Response({'detail': 'You do not have permission to add folders here.'}, status=status.HTTP_403_FORBIDDEN)
        except File.DoesNotExist:
            return Response({'detail': 'Parent folder not found or you do not have permission to access it.'}, status=status.HTTP_404_NOT_FOUND)

    new_folder = File.objects.create(
        name=name,
        owner=request.user,
        parent=parent_folder,
        mime_type='folder'
    )

    ActivityFeed.objects.create(
        actor=request.user,
        target_file=new_folder,
        action='folder_create',
        new_value={'name': new_folder.name}
    )

    serializer = FileListSerializer(new_folder, context={'request': request})
    return Response(serializer.data, status=status.HTTP_201_CREATED)


class FileViewSet(viewsets.ModelViewSet):
    """ViewSet for files and folders"""
    queryset = File.objects.all()
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return FileDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return FileCreateUpdateSerializer
        return FileListSerializer

    def get_queryset(self):
        accessible_ids = get_accessible_file_ids(self.request.user)
        return File.objects.select_related(
            'owner', 'parent'
        ).prefetch_related(
            'permissions', 'file_labels__label'
        ).filter(id__in=accessible_ids, trashed=False).distinct().order_by('-modified_time')

    def perform_create(self, serializer):
        parent = serializer.validated_data.get('parent')
        if parent and not has_folder_write_access(self.request.user, parent):
            raise PermissionDenied('You do not have permission to add files to this folder.')
        file_obj = serializer.save(owner=self.request.user)
        ActivityFeed.objects.create(
            actor=self.request.user,
            target_file=file_obj,
            action='file_create',
            new_value={'name': file_obj.name, 'mime_type': file_obj.mime_type}
        )

    def perform_update(self, serializer):
        old_data = {'name': self.get_object().name, 'mime_type': self.get_object().mime_type}
        new_parent = serializer.validated_data.get('parent', None)
        if new_parent and not has_folder_write_access(self.request.user, new_parent):
            raise PermissionDenied('You do not have permission to move files to this folder.')
        file_obj = serializer.save()
        ActivityFeed.objects.create(
            actor=self.request.user,
            target_file=file_obj,
            action='file_edit',
            old_value=old_data,
            new_value={'name': file_obj.name, 'mime_type': file_obj.mime_type}
        )

    @action(detail=True, methods=['post'])
    def star(self, request, pk=None):
        try:
            file_obj = self.get_object()
            file_obj.starred = not file_obj.starred
            file_obj.save()
            return Response(self.get_serializer(file_obj).data)
        except Exception as e:
            return Response({'detail': f'Error updating star: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def trash(self, request, pk=None):
        try:
            file_obj = File.objects.select_related('owner', 'parent').get(pk=pk, trashed=False)
        except Exception:
            return Response({'detail': 'File not found or you do not have access to it.'}, status=status.HTTP_404_NOT_FOUND)

        if file_obj.owner_id != request.user.id:
            permission = get_user_permission_for_file_or_ancestor(request.user, file_obj)
            if not permission:
                return Response({'detail': 'You do not have permission to remove this shared item.'}, status=status.HTTP_403_FORBIDDEN)

            permission.deleted = True
            permission.revoked_at = timezone.now()
            permission.revoked_by = request.user
            permission.save(update_fields=['deleted', 'revoked_at', 'revoked_by'])

            UserNotification.objects.filter(
                user=request.user,
                share_permission=permission,
                notification_type='share_received',
            ).update(share_status=UserNotification.SHARE_DECLINED, is_read=True, read_at=timezone.now())
            refresh_file_shared_state(permission.file)

            ActivityFeed.objects.create(actor=request.user, target_file=file_obj, action='file_unshare')

            return Response({'detail': 'Shared item removed from your files.', 'removed_share': True, 'file': str(file_obj.id)}, status=status.HTTP_200_OK)

        try:
            file_obj.trashed = True
            file_obj.trashed_time = timezone.now()
            file_obj.save()

            original_path = ''
            if hasattr(file_obj, 'path_info') and file_obj.path_info:
                original_path = getattr(file_obj.path_info, 'full_path', '')

            TrashItem.objects.create(
                file=file_obj,
                owner=file_obj.owner,
                trashed_by=request.user,
                original_name=file_obj.name,
                original_path=original_path,
                size_bytes=file_obj.size_bytes,
                purge_after=timezone.now() + timedelta(days=30)
            )
            ActivityFeed.objects.create(actor=request.user, target_file=file_obj, action='file_delete')
            return Response(self.get_serializer(file_obj).data)
        except Exception as e:
            file_obj.trashed = False
            file_obj.trashed_time = None
            file_obj.save()
            return Response({'detail': f'Error moving file to trash: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        try:
            file_obj = self.get_object()
        except Exception:
            return Response({'detail': 'File not found or you do not have access to it.'}, status=status.HTTP_404_NOT_FOUND)

        if file_obj.owner_id != request.user.id:
            return Response({'detail': 'You can only restore files you own.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            file_obj.trashed = False
            file_obj.trashed_time = None
            file_obj.save()
            TrashItem.objects.filter(file=file_obj).update(state='restored', restored_at=timezone.now(), restored_by=request.user)
            ActivityFeed.objects.create(actor=request.user, target_file=file_obj, action='file_restore')
            return Response(self.get_serializer(file_obj).data)
        except Exception as e:
            file_obj.trashed = True
            file_obj.trashed_time = timezone.now()
            file_obj.save()
            return Response({'detail': f'Error restoring file: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def children(self, request, pk=None):
        file_obj = self.get_object()
        children = file_obj.children.filter(trashed=False)
        return Response(self.get_serializer(children, many=True).data)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        file_obj = self.get_object()
        if not file_obj.file_path:
            return Response({'detail': 'No file content available.'}, status=status.HTTP_404_NOT_FOUND)
        from django.http import FileResponse, Http404
        try:
            return FileResponse(open(file_obj.file_path.path, 'rb'), as_attachment=True, filename=file_obj.name)
        except Exception:
            raise Http404

    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        file_obj = self.get_object()
        if not file_obj.file_path:
            return Response({'detail': 'No file content available.'}, status=status.HTTP_404_NOT_FOUND)
        from django.http import FileResponse, Http404
        try:
            return FileResponse(open(file_obj.file_path.path, 'rb'), as_attachment=False, filename=file_obj.name, content_type=file_obj.mime_type or 'application/octet-stream')
        except Exception:
            raise Http404

    @action(detail=False, methods=['get'])
    def root(self, request):
        root, created = File.objects.get_or_create(
            name='My Drive', owner=request.user, parent=None,
            defaults={'mime_type': 'folder'}
        )
        return Response(self.get_serializer(root).data)

    @action(detail=False, methods=['get'])
    def search(self, request):
        query = request.query_params.get('q', '')
        files = self.get_queryset().filter(Q(name__icontains=query) | Q(description__icontains=query))
        return Response(self.get_serializer(files, many=True).data)

    @action(detail=False, methods=['post'], parser_classes=(MultiPartParser, FormParser), permission_classes=[permissions.IsAuthenticated])
    def upload_multiple(self, request):
        parent_id = request.data.get('parent')
        parent = None
        if parent_id:
            try:
                parent = File.objects.get(id=parent_id)
            except File.DoesNotExist:
                return Response({'detail': 'Parent folder not found.'}, status=status.HTTP_404_NOT_FOUND)
            if not parent.is_folder():
                return Response({'detail': 'The specified parent is not a folder.'}, status=status.HTTP_400_BAD_REQUEST)
            if not has_folder_write_access(request.user, parent):
                return Response({'detail': 'You do not have permission to upload into this folder.'}, status=status.HTTP_403_FORBIDDEN)

        files = request.FILES.getlist('files')
        if not files:
            return Response({'detail': 'No files provided.'}, status=status.HTTP_400_BAD_REQUEST)

        created_files = []
        for f in files:
            mime = getattr(f, 'content_type', None) or mimetypes.guess_type(f.name)[0] or 'application/octet-stream'
            try:
                file_obj = File.objects.create(
                    name=f.name, owner=request.user, parent=parent,
                    mime_type=mime, size_bytes=getattr(f, 'size', None), file_path=f
                )
                ActivityFeed.objects.create(actor=request.user, target_file=file_obj, action='file_create', new_value={'name': file_obj.name, 'mime_type': file_obj.mime_type})
                created_files.append(file_obj)
            except Exception:
                continue

        return Response(self.get_serializer(created_files, many=True).data, status=status.HTTP_201_CREATED)


class FileRevisionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FileRevision.objects.all()
    serializer_class = FileRevisionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        file_id = self.request.query_params.get('file_id')
        if file_id:
            return FileRevision.objects.filter(file_id=file_id)
        return FileRevision.objects.none()


class FilePathViewSet(viewsets.ModelViewSet):
    queryset = FilePath.objects.all()
    serializer_class = FilePathSerializer
    permission_classes = [permissions.IsAuthenticated]


class FileContentHintViewSet(viewsets.ModelViewSet):
    queryset = FileContentHint.objects.all()
    serializer_class = FileContentHintSerializer
    permission_classes = [permissions.IsAuthenticated]


class ImageMediaMetadataViewSet(viewsets.ModelViewSet):
    queryset = ImageMediaMetadata.objects.all()
    serializer_class = FileImageMetadataSerializer
    permission_classes = [permissions.IsAuthenticated]


class VideoMediaMetadataViewSet(viewsets.ModelViewSet):
    queryset = VideoMediaMetadata.objects.all()
    serializer_class = FileVideoMetadataSerializer
    permission_classes = [permissions.IsAuthenticated]


# ============================================================
# PERMISSION & SHARING VIEWS
# ============================================================

class PermissionViewSet(viewsets.ModelViewSet):
    queryset = Permission.objects.filter(deleted=False)
    serializer_class = PermissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return PermissionCreateSerializer
        return PermissionSerializer

    def get_queryset(self):
        queryset = Permission.objects.filter(file__owner=self.request.user, deleted=False)
        file_id = self.request.query_params.get('file')
        if file_id:
            queryset = queryset.filter(file_id=file_id)
        return queryset

    def perform_create(self, serializer):
        permission = serializer.save()
        refresh_file_shared_state(permission.file)

        recipient_email = permission.grantee_email or (permission.grantee_user.email if permission.grantee_user else None)

        if permission.grantee_user:
            shared_by_name = f"{self.request.user.first_name} {self.request.user.last_name}".strip() or self.request.user.username
            item_type = 'folder' if permission.file.is_folder() else 'file'
            UserNotification.objects.create(
                user=permission.grantee_user,
                notification_type='share_received',
                title=f'New {item_type} shared with you',
                body=f"{shared_by_name} shared '{permission.file.name}' with you as {permission.get_role_display().lower()}. Accept it to add it to your shared files.",
                deep_link=f"{settings.SITE_URL}/frontend/notifications/",
                share_permission=permission,
                share_status=UserNotification.SHARE_PENDING,
            )
            refresh_file_shared_state(permission.file)

        if recipient_email:
            shared_by_name = f"{self.request.user.first_name} {self.request.user.last_name}".strip() or self.request.user.username
            send_file_shared_email(
                recipient_email=recipient_email,
                file_name=permission.file.name,
                shared_by_name=shared_by_name,
                shared_by_email=self.request.user.email,
                file_id=str(permission.file.id),
                role=permission.role
            )

        ActivityFeed.objects.create(
            actor=self.request.user, target_file=permission.file, action='file_share',
            new_value={'permission_id': str(permission.id), 'role': permission.role}
        )
        AuditLog.objects.create(
            event_id=str(uuid.uuid4()), actor_user=self.request.user, actor_email=self.request.user.email,
            target_file=permission.file, target_file_name=permission.file.name,
            target_user=permission.grantee_user, target_email=permission.grantee_email,
            action='share_create', new_state={'role': permission.role, 'type': permission.permission_type}
        )

    def perform_destroy(self, instance):
        recipient_email = instance.grantee_email or (instance.grantee_user.email if instance.grantee_user else None)

        if recipient_email:
            unshared_by_name = f"{self.request.user.first_name} {self.request.user.last_name}".strip() or self.request.user.username
            send_file_unshared_email(recipient_email=recipient_email, file_name=instance.file.name, unshared_by_name=unshared_by_name)

        instance.deleted = True
        instance.revoked_at = timezone.now()
        instance.revoked_by = self.request.user
        instance.save()
        refresh_file_shared_state(instance.file)

        ActivityFeed.objects.create(actor=self.request.user, target_file=instance.file, action='file_unshare')
        AuditLog.objects.create(
            event_id=str(uuid.uuid4()), actor_user=self.request.user, actor_email=self.request.user.email,
            target_file=instance.file, target_file_name=instance.file.name,
            target_user=instance.grantee_user, target_email=instance.grantee_email,
            action='share_revoke', new_state={'deleted': True}
        )


class ShareLinkViewSet(viewsets.ModelViewSet):
    queryset = ShareLink.objects.all()
    serializer_class = ShareLinkSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ShareLink.objects.filter(file__owner=self.request.user)

    def perform_create(self, serializer):
        link = serializer.save(created_by=self.request.user)
        refresh_file_shared_state(link.file)
        ActivityFeed.objects.create(actor=self.request.user, target_file=link.file, action='file_share', new_value={'link_id': link.token})

    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        link = self.get_object()
        link.revoked_at = timezone.now()
        link.save()
        refresh_file_shared_state(link.file)
        ActivityFeed.objects.create(actor=request.user, target_file=link.file, action='file_unshare')
        return Response(self.get_serializer(link).data)


class ShareLinkAccessViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ShareLinkAccess.objects.all()
    serializer_class = ShareLinkAccessSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ShareLinkAccess.objects.filter(share_link__created_by=self.request.user)


class FileRequestViewSet(viewsets.ModelViewSet):
    queryset = FileRequest.objects.all()
    serializer_class = FileRequestSerializer
    permission_classes = [permissions.IsAuthenticated]


class FileRequestSubmissionViewSet(viewsets.ModelViewSet):
    queryset = FileRequestSubmission.objects.all()
    serializer_class = FileRequestSubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]


# ============================================================
# TRASH VIEWS
# ============================================================

class TrashViewSet(viewsets.ModelViewSet):
    queryset = TrashItem.objects.all()
    serializer_class = TrashItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TrashItem.objects.filter(owner=self.request.user)

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        trash_item = self.get_object()
        file_obj = trash_item.file
        file_obj.trashed = False
        file_obj.trashed_time = None
        file_obj.save()
        trash_item.state = 'restored'
        trash_item.restored_at = timezone.now()
        trash_item.restored_by = request.user
        trash_item.save()
        return Response(self.get_serializer(trash_item).data)

    @action(detail=True, methods=['delete'])
    def purge(self, request, pk=None):
        trash_item = self.get_object()
        file_obj = trash_item.file
        if file_obj.file_path:
            file_obj.file_path.delete()
        trash_item.state = 'purged'
        trash_item.purged_at = timezone.now()
        trash_item.save()
        file_obj.delete()
        return Response({'status': 'File permanently deleted'})


class SpamFlagViewSet(viewsets.ModelViewSet):
    queryset = SpamFlag.objects.all()
    serializer_class = SpamFlagSerializer
    permission_classes = [permissions.IsAuthenticated]


# ============================================================
# COMMENT VIEWS
# ============================================================

class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.filter(is_deleted=False)
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated, CanAccessFile]

    def get_queryset(self):
        accessible_ids = get_accessible_file_ids(self.request.user)
        queryset = Comment.objects.select_related('author', 'file').prefetch_related('replies').filter(file_id__in=accessible_ids, is_deleted=False)
        file_id = self.request.query_params.get('file_id')
        if file_id:
            return queryset.filter(file_id=file_id)
        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        file_obj = serializer.validated_data.get('file')
        if not file_obj or not has_file_read_access(self.request.user, file_obj):
            raise PermissionDenied('You do not have permission to comment on this file.')
        comment = serializer.save(author=self.request.user)
        ActivityFeed.objects.create(actor=self.request.user, target_file=comment.file, action='comment_add', new_value={'comment_id': str(comment.id)})

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        comment = self.get_object()
        comment.status = 'resolved'
        comment.resolved_at = timezone.now()
        comment.resolved_by = request.user
        comment.save()
        return Response(self.get_serializer(comment).data)


class CommentReplyViewSet(viewsets.ModelViewSet):
    queryset = CommentReply.objects.filter(is_deleted=False)
    serializer_class = CommentReplySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        comment_id = self.request.query_params.get('comment_id')
        if comment_id:
            return CommentReply.objects.filter(comment_id=comment_id, is_deleted=False)
        return CommentReply.objects.none()

    def perform_create(self, serializer):
        reply = serializer.save(author=self.request.user)
        if reply.action == 'resolve':
            reply.comment.status = 'resolved'
            reply.comment.resolved_at = timezone.now()
            reply.comment.resolved_by = self.request.user
            reply.comment.save()


class CommentMentionViewSet(viewsets.ModelViewSet):
    queryset = CommentMention.objects.all()
    serializer_class = CommentMentionSerializer
    permission_classes = [permissions.IsAuthenticated]


# ============================================================
# ACTIVITY VIEWS
# ============================================================

class ActivityFeedViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ActivityFeed.objects.all()
    serializer_class = ActivityFeedSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        file_id = self.request.query_params.get('file_id')
        if file_id:
            file_obj = File.objects.get(id=file_id, owner=self.request.user)
            return ActivityFeed.objects.filter(target_file=file_obj)
        user_files = File.objects.filter(owner=self.request.user)
        return ActivityFeed.objects.filter(target_file__in=user_files)


# ============================================================
# AUDIT LOG VIEWS
# ============================================================

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return AuditLog.objects.all()
        return AuditLog.objects.none()


class DLPViolationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DLPViolation.objects.all()
    serializer_class = DLPViolationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return DLPViolation.objects.all()
        return DLPViolation.objects.none()


# ============================================================
# CATEGORY VIEWS (HTML Pages)
# ============================================================

def PostAPICategory(request):
    return render(request, 'app/PostAPICategory.html')


def PutAPICategory(request):
    return render(request, 'app/PutAPICategory.html')


def DeleteAPICategory(request):
    return render(request, 'app/DeleteAPICategory.html')


# ============================================================
# SEARCH VIEWS
# ============================================================

class SavedSearchViewSet(viewsets.ModelViewSet):
    queryset = SavedSearch.objects.all()
    serializer_class = SavedSearchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SavedSearch.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SearchHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SearchHistory.objects.all()
    serializer_class = SearchHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SearchHistory.objects.filter(user=self.request.user)


class SearchIndexViewSet(viewsets.ModelViewSet):
    queryset = SearchIndex.objects.all()
    serializer_class = SearchIndexSerializer
    permission_classes = [permissions.IsAuthenticated]


# ============================================================
# LABEL VIEWS
# ============================================================

class LabelViewSet(viewsets.ModelViewSet):
    queryset = Label.objects.all()
    serializer_class = LabelSerializer
    permission_classes = [permissions.IsAuthenticated]


class LabelFieldViewSet(viewsets.ModelViewSet):
    queryset = LabelField.objects.all()
    serializer_class = LabelFieldSerializer
    permission_classes = [permissions.IsAuthenticated]


class FileLabelViewSet(viewsets.ModelViewSet):
    queryset = FileLabel.objects.all()
    serializer_class = FileLabelSerializer
    permission_classes = [permissions.IsAuthenticated]


@api_view(['GET'])
@permission_classes([GlobalTokenRequired])
def api_root(request, format=None):
    """Public API root — lists all main endpoints."""
    base = request.build_absolute_uri('/api/v1/')
    return Response({
        'auth': {
            'login':          '/api/auth/login/',
            'logout':         '/api/auth/logout/',
            'register':       f'{base}users/register/',
        },
        'folders': {
            'list_root':      f'{base}files/root/',
            'list_children':  f'{base}files/<folder_id>/children/',
            'create_folder':  f'{base}files/create-folder/',
            'detail':         f'{base}files/<id>/',
            'rename':         f'{base}files/<id>/  [PATCH {{name}}]',
            'delete_trash':   f'{base}files/<id>/trash/',
            'move':           f'{base}files/<id>/  [PATCH {{parent}}]',
        },
        'files': {
            'list':           f'{base}files/',
            'upload_single':  f'{base}files/  [POST multipart]',
            'upload_multiple': f'{base}files/upload_multiple/',
            'download':       f'{base}files/<id>/download/',
            'preview':        f'{base}files/<id>/preview/',
            'children':       f'{base}files/<id>/children/',
        },
        'sharing': {
            'permissions':    f'{base}permissions/',
            'share_links':    f'{base}share-links/',
        },
        'users': {
            'profile':        f'{base}users/profile/me/',
            'preferences':    f'{base}users/preferences/me/',
            'notifications':  f'{base}users/notifications/',
        },
        'storage': {
            'quota':          f'{base}storage/quota/',
        },
        'trash': {
            'list':           f'{base}trash/',
            'restore':        f'{base}trash/<id>/restore/',
            'purge':          f'{base}trash/<id>/purge/',
        },
        'activity':           f'{base}activity/',
        'comments':           f'{base}comments/',
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def storage_quota(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    usage = profile.storage_quota_usage_bytes or 0
    limit = profile.storage_quota_limit_bytes or getattr(settings, 'DEFAULT_USER_STORAGE_QUOTA_BYTES', 5 * 1024 * 1024 * 1024)
    try:
        percent = int(usage * 100 / limit) if limit and limit > 0 else 0
    except Exception:
        percent = 0
    return Response({'usage_bytes': usage, 'limit_bytes': limit, 'percent_used': percent})


# ============================================================
# PRODUCT VIEWS
# ============================================================

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by('-productDate')
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    parser_classes = (MultiPartParser, FormParser)
