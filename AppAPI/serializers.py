from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    UserProfile, UserSession, UserPreference, UserNotification,
    File, FilePath, FileRevision, FileContentHint, ImageMediaMetadata, VideoMediaMetadata,
    TrashItem, SpamFlag, Permission, ShareLink, ShareLinkAccess, FileRequest, FileRequestSubmission,
    Comment, CommentReply, CommentMention, ActivityFeed, Label, LabelField, FileLabel,
    SearchIndex, SavedSearch, SearchHistory, AuditLog, DLPViolation, Product
)


# ============================================================
# USER & PROFILE SERIALIZERS
# ============================================================

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'date_joined']
        read_only_fields = ['id', 'date_joined']


class UserRegistrationSerializer(serializers.Serializer):
    """Serializer for user registration"""
    username = serializers.CharField(write_only=True, required=True)
    email = serializers.EmailField(write_only=True, required=True)
    password = serializers.CharField(write_only=True, required=True, min_length=6)
    first_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    last_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists.")
        return value
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists.")
        return value
    
    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'user', 'given_name', 'family_name', 'photo_url', 'locale',
            'is_suspended', 'storage_quota_limit_bytes', 'storage_quota_usage_bytes',
            'created_at', 'last_login_at'
        ]
        read_only_fields = ['id', 'created_at', 'storage_quota_usage_bytes']
    
    def update(self, instance, validated_data):
        """Update profile and handle nested user updates"""
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class UserSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSession
        fields = [
            'id', 'user', 'token_scope', 'ip_address', 'user_agent',
            'expires_at', 'created_at', 'revoked_at'
        ]
        read_only_fields = ['id', 'created_at']


class UserPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreference
        fields = [
            'id', 'user', 'theme', 'default_view', 'sort_field', 'sort_direction',
            'show_hidden_files', 'density', 'updated_at'
        ]
        read_only_fields = ['id', 'updated_at']


class UserNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserNotification
        fields = [
            'id', 'user', 'notification_type', 'title', 'body', 'deep_link',
            'share_permission', 'share_status', 'is_read', 'created_at', 'read_at'
        ]
        read_only_fields = ['id', 'created_at']


# ============================================================
# FILE & FOLDER SERIALIZERS
# ============================================================

class FileImageMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImageMediaMetadata
        fields = [
            'id', 'width_px', 'height_px', 'rotation_degrees', 'camera_make',
            'camera_model', 'exposure_time', 'aperture', 'flash_used',
            'focal_length', 'iso_speed', 'taken_at', 'gps_latitude',
            'gps_longitude', 'gps_altitude'
        ]
        read_only_fields = ['id']


class FileVideoMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoMediaMetadata
        fields = [
            'id', 'width_px', 'height_px', 'duration_ms', 'codec',
            'frame_rate', 'audio_channels', 'audio_sample_rate'
        ]
        read_only_fields = ['id']


class FileContentHintSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileContentHint
        fields = ['id', 'indexable_text', 'thumbnail_data', 'thumbnail_mime', 'updated_at']
        read_only_fields = ['id', 'updated_at']


class FileRevisionSerializer(serializers.ModelSerializer):
    modified_by_email = serializers.CharField(source='modified_by.email', read_only=True)
    
    class Meta:
        model = FileRevision
        fields = [
            'id', 'revision_id', 'mime_type', 'modified_by', 'modified_by_email',
            'size_bytes', 'md5_checksum', 'keep_forever', 'published',
            'published_outside_domain', 'published_link', 'download_url', 'modified_time'
        ]
        read_only_fields = ['id', 'modified_time']


class FileListSerializer(serializers.ModelSerializer):
    owner_email = serializers.CharField(source='owner.email', read_only=True)
    permissions_count = serializers.SerializerMethodField()
    
    class Meta:
        model = File
        fields = [
            'id', 'name', 'owner', 'owner_email', 'parent', 'mime_type',
            'size_bytes', 'is_shared', 'is_shared_with_me', 'trashed',
            'starred', 'created_time', 'modified_time', 'permissions_count'
        ]
        read_only_fields = ['id', 'created_time', 'modified_time']
    
    def get_permissions_count(self, obj):
        return obj.permissions.filter(deleted=False).count()


class FileDetailSerializer(serializers.ModelSerializer):
    owner_email = serializers.CharField(source='owner.email', read_only=True)
    owner_name = serializers.SerializerMethodField()
    image_metadata = FileImageMetadataSerializer(read_only=True)
    video_metadata = FileVideoMetadataSerializer(read_only=True)
    content_hint = FileContentHintSerializer(read_only=True)
    permissions = serializers.SerializerMethodField()
    children = FileListSerializer(many=True, read_only=True)
    
    class Meta:
        model = File
        fields = [
            'id', 'name', 'owner', 'owner_email', 'owner_name', 'parent', 'mime_type',
            'description', 'size_bytes', 'space', 'source', 'trashed', 'starred',
            'viewed_by_me', 'is_shared', 'is_shared_with_me', 'writers_can_share',
            'capabilities', 'created_time', 'modified_time', 'viewed_by_me_time',
            'shared_with_me_time', 'image_metadata', 'video_metadata', 'content_hint',
            'permissions', 'children'
        ]
        read_only_fields = ['id', 'created_time', 'modified_time']
    
    def get_owner_name(self, obj):
        return f"{obj.owner.first_name} {obj.owner.last_name}".strip()
    
    def get_permissions(self, obj):
        perms = obj.permissions.filter(deleted=False)
        return PermissionSerializer(perms, many=True).data


class FileCreateUpdateSerializer(serializers.ModelSerializer):
    MAX_FILE_NAME_LENGTH = 255
    MAX_DESCRIPTION_LENGTH = 1000
    WRITE_ROLES = {'owner', 'organizer', 'fileOrganizer', 'writer'}

    class Meta:
        model = File
        fields = [
            'name', 'parent', 'mime_type', 'description', 'file_path',
            'space', 'starred'
        ]

    def validate_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError('File name cannot be empty.')

        if len(value) > self.MAX_FILE_NAME_LENGTH:
            raise serializers.ValidationError('File name is too long.')

        invalid_chars = ['<', '>', ':', '\\', '|', '?', '*']
        if any(char in value for char in invalid_chars):
            raise serializers.ValidationError('File name contains invalid characters.')

        return value

    def validate_description(self, value):
        if value and len(value) > self.MAX_DESCRIPTION_LENGTH:
            raise serializers.ValidationError('Description is too long.')
        return value

    def validate_parent(self, value):
        if value is None:
            return value

        if not value.is_folder():
            raise serializers.ValidationError('Parent must be a folder.')

        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return value

        current = value
        while current:
            if current.owner_id == request.user.id:
                return value
            if Permission.objects.filter(
                file=current,
                grantee_user=request.user,
                role__in=self.WRITE_ROLES,
                deleted=False
            ).exists():
                return value
            current = current.parent

        raise serializers.ValidationError('You do not have permission to add files to this folder.')


class FilePathSerializer(serializers.ModelSerializer):
    class Meta:
        model = FilePath
        fields = ['id', 'file', 'full_path', 'depth', 'updated_at']
        read_only_fields = ['id', 'updated_at']


# ============================================================
# TRASH & SPAM SERIALIZERS
# ============================================================

class TrashItemSerializer(serializers.ModelSerializer):
    file_name = serializers.CharField(source='file.name', read_only=True)
    owner_email = serializers.CharField(source='owner.email', read_only=True)
    
    class Meta:
        model = TrashItem
        fields = [
            'id', 'file', 'file_name', 'owner', 'owner_email', 'trashed_by',
            'state', 'original_name', 'original_path', 'size_bytes',
            'trashed_at', 'purge_after', 'restored_at'
        ]
        read_only_fields = ['id', 'trashed_at']


class SpamFlagSerializer(serializers.ModelSerializer):
    file_name = serializers.CharField(source='file.name', read_only=True)
    
    class Meta:
        model = SpamFlag
        fields = [
            'id', 'file', 'file_name', 'reported_by', 'verdict', 'confidence',
            'reason', 'quarantined', 'resolved', 'resolved_at', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


# ============================================================
# PERMISSION & SHARING SERIALIZERS
# ============================================================

class PermissionSerializer(serializers.ModelSerializer):
    grantee_name = serializers.SerializerMethodField()
    file_name = serializers.CharField(source='file.name', read_only=True)
    share_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Permission
        fields = [
            'id', 'file', 'file_name', 'grantee_user', 'grantee_email', 'grantee_name',
            'permission_type', 'role', 'allow_file_discovery', 'expiration_time',
            'created_at', 'revoked_at', 'share_status'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_grantee_name(self, obj):
        if obj.grantee_user:
            return f"{obj.grantee_user.first_name} {obj.grantee_user.last_name}".strip()
        return obj.grantee_email

    def get_share_status(self, obj):
        notification = obj.share_notifications.order_by('-created_at').first()
        return notification.share_status if notification else 'accepted'


class PermissionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating permissions with enhanced validation"""
    grantee_email = serializers.EmailField(required=False, allow_blank=True)
    
    class Meta:
        model = Permission
        fields = [
            'file', 'grantee_user', 'grantee_email', 'permission_type', 'role',
            'allow_file_discovery', 'expiration_time'
        ]
    
    def validate(self, data):
        """Validate permission data"""
        permission_type = data.get('permission_type')
        grantee_user = data.get('grantee_user')
        grantee_email = data.get('grantee_email')
        
        # For 'user' type, at least one of grantee_user or grantee_email must be provided
        if permission_type == 'user':
            if not grantee_user and not grantee_email:
                raise serializers.ValidationError(
                    "For 'user' permission type, either grantee_user or grantee_email is required."
                )
        
        # If email is provided, try to find the user
        if grantee_email and not grantee_user:
            try:
                user = User.objects.get(email=grantee_email)
                data['grantee_user'] = user
            except User.DoesNotExist:
                # Email doesn't correspond to existing user - that's ok, we'll store just the email
                pass
        
        # Check for duplicate permissions
        file_obj = data.get('file')
        existing = Permission.objects.filter(
            file=file_obj,
            permission_type=permission_type,
            deleted=False
        )
        
        if grantee_user:
            existing = existing.filter(grantee_user=grantee_user)
        elif grantee_email:
            existing = existing.filter(grantee_email=grantee_email)
        
        if existing.exists():
            raise serializers.ValidationError(
                "This user or email already has access to this file."
            )
        
        return data


class ShareLinkAccessSerializer(serializers.ModelSerializer):
    accessor_email = serializers.CharField(source='accessor.email', read_only=True)
    
    class Meta:
        model = ShareLinkAccess
        fields = ['id', 'accessor', 'accessor_email', 'ip_address', 'accessed_at']
        read_only_fields = ['id', 'accessed_at']


class ShareLinkSerializer(serializers.ModelSerializer):
    accesses = ShareLinkAccessSerializer(many=True, read_only=True)
    file_name = serializers.CharField(source='file.name', read_only=True)
    
    class Meta:
        model = ShareLink
        fields = [
            'id', 'file', 'file_name', 'token', 'created_by', 'max_uses',
            'use_count', 'role', 'expires_at', 'revoked_at', 'created_at', 'accesses'
        ]
        read_only_fields = ['id', 'token', 'created_at', 'use_count']


class FileRequestSubmissionSerializer(serializers.ModelSerializer):
    submitted_file_name = serializers.CharField(source='submitted_file.name', read_only=True)
    
    class Meta:
        model = FileRequestSubmission
        fields = [
            'id', 'request', 'submitted_file', 'submitted_file_name', 'submitter',
            'submitter_email', 'submitter_name', 'submitted_at'
        ]
        read_only_fields = ['id', 'submitted_at']


class FileRequestSerializer(serializers.ModelSerializer):
    submissions = FileRequestSubmissionSerializer(many=True, read_only=True)
    created_by_email = serializers.CharField(source='created_by.email', read_only=True)
    
    class Meta:
        model = FileRequest
        fields = [
            'id', 'destination_folder', 'created_by', 'created_by_email', 'title',
            'description', 'email_message', 'accept_multiple', 'is_open',
            'closes_at', 'created_at', 'closed_at', 'submissions'
        ]
        read_only_fields = ['id', 'created_at']


# ============================================================
# COMMENT & ACTIVITY SERIALIZERS
# ============================================================

class CommentReplySerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    
    class Meta:
        model = CommentReply
        fields = [
            'id', 'comment', 'author', 'author_name', 'content', 'action',
            'is_deleted', 'created_at', 'modified_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_author_name(self, obj):
        return f"{obj.author.first_name} {obj.author.last_name}".strip()


class CommentSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    file_name = serializers.CharField(source='file.name', read_only=True)
    replies = CommentReplySerializer(many=True, read_only=True)
    anchor = serializers.JSONField(required=False, default=dict)
    
    class Meta:
        model = Comment
        fields = [
            'id', 'file', 'file_name', 'author', 'author_name', 'content', 'quoted_file_content',
            'anchor', 'status', 'is_deleted', 'created_at', 'modified_at',
            'resolved_at', 'resolved_by', 'replies'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_author_name(self, obj):
        return (
            f"{obj.author.first_name} {obj.author.last_name}".strip()
            or obj.author.username
            or obj.author.email
        )

    def validate_anchor(self, value):
        # Coerce null anchor values to an empty object to avoid DB NOT NULL errors
        if value is None:
            return {}
        return value


class CommentMentionSerializer(serializers.ModelSerializer):
    mentioned_user_email = serializers.CharField(source='mentioned_user.email', read_only=True)
    
    class Meta:
        model = CommentMention
        fields = ['id', 'comment', 'mentioned_user', 'mentioned_user_email', 'created_at']
        read_only_fields = ['id', 'created_at']


class ActivityFeedSerializer(serializers.ModelSerializer):
    actor_email = serializers.CharField(source='actor.email', read_only=True)
    file_name = serializers.CharField(source='target_file.name', read_only=True)
    
    class Meta:
        model = ActivityFeed
        fields = [
            'id', 'actor', 'actor_email', 'target_file', 'file_name', 'action',
            'old_value', 'new_value', 'ip_address', 'occurred_at'
        ]
        read_only_fields = ['id', 'occurred_at']


# ============================================================
# LABEL & SEARCH SERIALIZERS
# ============================================================

class LabelFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabelField
        fields = ['id', 'label', 'field_key', 'display_name', 'field_type', 'is_required', 'display_order']
        read_only_fields = ['id']


class LabelSerializer(serializers.ModelSerializer):
    fields = LabelFieldSerializer(many=True, read_only=True)
    
    class Meta:
        model = Label
        fields = ['id', 'title', 'description', 'published', 'created_by', 'created_at', 'revised_at', 'disabled_at', 'fields']
        read_only_fields = ['id', 'created_at', 'revised_at']


class FileLabelSerializer(serializers.ModelSerializer):
    label_title = serializers.CharField(source='label.title', read_only=True)
    
    class Meta:
        model = FileLabel
        fields = ['id', 'file', 'label', 'label_title', 'applied_by', 'applied_at', 'removed_at']
        read_only_fields = ['id', 'applied_at']


class SavedSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedSearch
        fields = ['id', 'user', 'name', 'query', 'filters', 'created_at', 'last_run_at']
        read_only_fields = ['id', 'created_at']


class SearchHistorySerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = SearchHistory
        fields = ['id', 'user', 'user_email', 'query', 'result_count', 'searched_at']
        read_only_fields = ['id', 'searched_at']


class SearchIndexSerializer(serializers.ModelSerializer):
    file_name = serializers.CharField(source='file.name', read_only=True)
    
    class Meta:
        model = SearchIndex
        fields = [
            'id', 'file', 'file_name', 'owner', 'ts_vector', 'name_tokens',
            'content_hash', 'indexed_at', 'needs_reindex'
        ]
        read_only_fields = ['id', 'indexed_at']


# ============================================================
# AUDIT LOG SERIALIZERS
# ============================================================

class DLPViolationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DLPViolation
        fields = [
            'id', 'audit_log', 'policy_name', 'severity', 'description',
            'matched_pattern', 'action_taken', 'detected_at'
        ]
        read_only_fields = ['id', 'detected_at']


class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.CharField(source='actor_user.email', read_only=True)
    file_name = serializers.CharField(source='target_file.name', read_only=True, allow_null=True)
    dlp_violation = DLPViolationSerializer(read_only=True)
    
    class Meta:
        model = AuditLog
        fields = [
            'id', 'event_id', 'actor_user', 'actor_email', 'target_file', 'file_name',
            'target_user', 'target_email', 'action', 'old_state', 'new_state',
            'ip_address', 'country_code', 'user_agent', 'risk_score', 'occurred_at',
            'dlp_violation'
        ]
        read_only_fields = ['id', 'occurred_at']


# ============================================================
# PRODUCT SERIALIZER
# ============================================================

class ProductSerializer(serializers.ModelSerializer):
    productImage = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = ['id', 'productName', 'price', 'productImage', 'productDate']
        read_only_fields = ['id', 'productDate']
    
    def get_productImage(self, obj):
        """Return the product image URL"""
        if obj.productImage:
            # productImage is already a string URL
            return obj.productImage
        return None
