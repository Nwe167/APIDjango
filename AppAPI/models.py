import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.utils.crypto import get_random_string
import json


# ============================================================
# ENUMS (Using Django Choices)
# ============================================================

class FileSpace(models.TextChoices):
    DRIVE = 'drive', 'Drive'
    APP_DATA_FOLDER = 'appDataFolder', 'App Data Folder'
    PHOTOS = 'photos', 'Photos'


class FileSource(models.TextChoices):
    USER_UPLOAD = 'user_upload', 'User Upload'
    GOOGLE_WORKSPACE = 'google_workspace', 'Google Workspace'
    THIRD_PARTY_APP = 'third_party_app', 'Third Party App'
    API_CREATED = 'api_created', 'API Created'


class PermissionType(models.TextChoices):
    USER = 'user', 'User'
    GROUP = 'group', 'Group'
    DOMAIN = 'domain', 'Domain'
    ANYONE = 'anyone', 'Anyone'


class PermissionRole(models.TextChoices):
    OWNER = 'owner', 'Owner'
    ORGANIZER = 'organizer', 'Organizer'
    FILE_ORGANIZER = 'fileOrganizer', 'File Organizer'
    WRITER = 'writer', 'Writer'
    COMMENTER = 'commenter', 'Commenter'
    READER = 'reader', 'Reader'


class CommentStatus(models.TextChoices):
    OPEN = 'open', 'Open'
    RESOLVED = 'resolved', 'Resolved'
    DELETED = 'deleted', 'Deleted'


class ActivityAction(models.TextChoices):
    FILE_CREATE = 'file_create', 'File Created'
    FILE_EDIT = 'file_edit', 'File Edited'
    FILE_RENAME = 'file_rename', 'File Renamed'
    FILE_MOVE = 'file_move', 'File Moved'
    FILE_COPY = 'file_copy', 'File Copied'
    FILE_DELETE = 'file_delete', 'File Deleted'
    FILE_RESTORE = 'file_restore', 'File Restored'
    FILE_VIEW = 'file_view', 'File Viewed'
    FILE_DOWNLOAD = 'file_download', 'File Downloaded'
    FILE_SHARE = 'file_share', 'File Shared'
    FILE_UNSHARE = 'file_unshare', 'File Unshared'
    PERMISSION_CHANGE = 'permission_change', 'Permission Changed'
    COMMENT_ADD = 'comment_add', 'Comment Added'
    COMMENT_RESOLVE = 'comment_resolve', 'Comment Resolved'
    FOLDER_CREATE = 'folder_create', 'Folder Created'
    FOLDER_DELETE = 'folder_delete', 'Folder Deleted'
    MEMBER_ADD = 'member_add', 'Member Added'
    MEMBER_REMOVE = 'member_remove', 'Member Removed'


class TrashState(models.TextChoices):
    TRASHED = 'trashed', 'Trashed'
    PENDING_PURGE = 'pending_purge', 'Pending Purge'
    PURGED = 'purged', 'Purged'
    RESTORED = 'restored', 'Restored'


class UserTheme(models.TextChoices):
    LIGHT = 'light', 'Light'
    DARK = 'dark', 'Dark'
    SYSTEM = 'system', 'System'


class SpamVerdict(models.TextChoices):
    CLEAN = 'clean', 'Clean'
    SPAM = 'spam', 'Spam'
    PHISHING = 'phishing', 'Phishing'
    MALWARE = 'malware', 'Malware'
    POLICY_VIOLATION = 'policy_violation', 'Policy Violation'
    REVIEW_PENDING = 'review_pending', 'Review Pending'


# ============================================================
# USER & PROFILE MODELS
# ============================================================

class UserProfile(models.Model):
    """Extended user profile with storage quota and settings"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    given_name = models.CharField(max_length=150, blank=True)
    family_name = models.CharField(max_length=150, blank=True)
    photo_url = models.URLField(blank=True, null=True)
    locale = models.CharField(max_length=10, default='en')
    is_suspended = models.BooleanField(default=False)
    storage_quota_limit_bytes = models.BigIntegerField(null=True, blank=True)
    storage_quota_usage_bytes = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    last_login_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f"{self.user.email} - {self.user.first_name} {self.user.last_name}"


class UserSession(models.Model):
    """Track user sessions for security"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    access_token = models.TextField()
    refresh_token = models.TextField(null=True, blank=True)
    token_scope = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'expires_at']),
        ]

    def __str__(self):
        return f"Session for {self.user.email}"


class UserPreference(models.Model):
    """User UI and display preferences"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preferences')
    theme = models.CharField(max_length=20, choices=UserTheme.choices, default='system')
    default_view = models.CharField(max_length=20, default='list')  # list or grid
    sort_field = models.CharField(max_length=50, default='modified_time')
    sort_direction = models.CharField(max_length=10, default='desc')  # asc or desc
    show_hidden_files = models.BooleanField(default=False)
    density = models.CharField(max_length=20, default='comfortable')  # comfortable or compact
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Preferences for {self.user.email}"


class UserNotification(models.Model):
    """User notifications"""
    SHARE_PENDING = 'pending'
    SHARE_ACCEPTED = 'accepted'
    SHARE_DECLINED = 'declined'
    SHARE_STATUS_CHOICES = [
        (SHARE_PENDING, 'Pending'),
        (SHARE_ACCEPTED, 'Accepted'),
        (SHARE_DECLINED, 'Declined'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(
        max_length=50,
        choices=[
            ('share_received', 'Share Received'),
            ('quota_warning', 'Quota Warning'),
            ('comment_mention', 'Comment Mention'),
            ('file_request', 'File Request'),
        ]
    )
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    deep_link = models.URLField(blank=True, null=True)
    share_permission = models.ForeignKey(
        'Permission',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='share_notifications'
    )
    share_status = models.CharField(max_length=20, choices=SHARE_STATUS_CHOICES, default=SHARE_PENDING)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} for {self.user.email}"


# ============================================================
# FILES & FOLDER HIERARCHY
# ============================================================

class File(models.Model):
    """Core file/folder model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, db_index=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_files')
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )
    mime_type = models.CharField(max_length=100)  # e.g., 'application/pdf', 'folder'
    description = models.TextField(blank=True)
    size_bytes = models.BigIntegerField(null=True, blank=True)
    space = models.CharField(max_length=50, choices=FileSpace.choices, default='drive')
    source = models.CharField(max_length=50, choices=FileSource.choices, default='user_upload')
    
    # Status flags
    trashed = models.BooleanField(default=False, db_index=True)
    starred = models.BooleanField(default=False)
    viewed_by_me = models.BooleanField(default=False)
    
    # Checksums and links
    md5_checksum = models.CharField(max_length=32, blank=True)
    sha256_checksum = models.CharField(max_length=64, blank=True)
    web_view_link = models.URLField(blank=True)
    web_content_link = models.URLField(blank=True)
    thumbnail_link = models.URLField(blank=True)
    icon_link = models.URLField(blank=True)
    
    # Versioning and sharing
    version = models.IntegerField(default=1)
    has_thumbnail = models.BooleanField(default=False)
    is_shared = models.BooleanField(default=False)
    is_shared_with_me = models.BooleanField(default=False)
    writers_can_share = models.BooleanField(default=True)
    copy_requires_writer = models.BooleanField(default=False)
    
    # Capabilities stored as JSON
    capabilities = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_time = models.DateTimeField(auto_now_add=True)
    modified_time = models.DateTimeField(auto_now=True, db_index=True)
    viewed_by_me_time = models.DateTimeField(null=True, blank=True)
    shared_with_me_time = models.DateTimeField(null=True, blank=True)
    trashed_time = models.DateTimeField(null=True, blank=True)
    
    # File storage path
    file_path = models.FileField(upload_to='files/%Y/%m/%d/', null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['owner', 'trashed']),
            models.Index(fields=['parent', 'trashed']),
            models.Index(fields=['mime_type']),
            models.Index(fields=['modified_time']),
        ]
        ordering = ['-modified_time']

    def __str__(self):
        return self.name

    def is_folder(self):
        return self.mime_type == 'application/vnd.google-apps.folder' or self.mime_type == 'folder'


class FilePath(models.Model):
    """Store full file paths for quick lookups"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.OneToOneField(File, on_delete=models.CASCADE, related_name='path_info')
    full_path = models.TextField(db_index=True)  # e.g., '/My Drive/Projects/report.pdf'
    depth = models.IntegerField()  # Nesting depth
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_path


class FileRevision(models.Model):
    """Version history for files"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.ForeignKey(File, on_delete=models.CASCADE, related_name='revisions')
    revision_id = models.CharField(max_length=255, unique=True)
    mime_type = models.CharField(max_length=100, blank=True)
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    size_bytes = models.BigIntegerField(null=True, blank=True)
    md5_checksum = models.CharField(max_length=32, blank=True)
    keep_forever = models.BooleanField(default=False)
    published = models.BooleanField(default=False)
    published_outside_domain = models.BooleanField(default=False)
    published_link = models.URLField(blank=True)
    download_url = models.URLField(blank=True)
    modified_time = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=['file', 'modified_time']),
        ]
        ordering = ['-modified_time']

    def __str__(self):
        return f"{self.file.name} - v{self.revision_id}"


class FileContentHint(models.Model):
    """Store indexable text and thumbnail data for files"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.OneToOneField(File, on_delete=models.CASCADE, related_name='content_hint')
    indexable_text = models.TextField(blank=True)  # For full-text search
    thumbnail_data = models.TextField(blank=True)  # Base64-encoded
    thumbnail_mime = models.CharField(max_length=100, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Content hint for {self.file.name}"


class ImageMediaMetadata(models.Model):
    """Metadata for image files"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.OneToOneField(File, on_delete=models.CASCADE, related_name='image_metadata')
    width_px = models.IntegerField(null=True, blank=True)
    height_px = models.IntegerField(null=True, blank=True)
    rotation_degrees = models.IntegerField(default=0)
    camera_make = models.CharField(max_length=100, blank=True)
    camera_model = models.CharField(max_length=100, blank=True)
    exposure_time = models.CharField(max_length=50, blank=True)
    aperture = models.FloatField(null=True, blank=True)
    flash_used = models.BooleanField(null=True, blank=True)
    focal_length = models.FloatField(null=True, blank=True)
    iso_speed = models.IntegerField(null=True, blank=True)
    taken_at = models.DateTimeField(null=True, blank=True)
    gps_latitude = models.FloatField(null=True, blank=True)
    gps_longitude = models.FloatField(null=True, blank=True)
    gps_altitude = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"Image metadata for {self.file.name}"


class VideoMediaMetadata(models.Model):
    """Metadata for video files"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.OneToOneField(File, on_delete=models.CASCADE, related_name='video_metadata')
    width_px = models.IntegerField(null=True, blank=True)
    height_px = models.IntegerField(null=True, blank=True)
    duration_ms = models.BigIntegerField(null=True, blank=True)
    codec = models.CharField(max_length=100, blank=True)
    frame_rate = models.FloatField(null=True, blank=True)
    audio_channels = models.IntegerField(null=True, blank=True)
    audio_sample_rate = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"Video metadata for {self.file.name}"


# ============================================================
# TRASH & SPAM
# ============================================================

class TrashItem(models.Model):
    """Track deleted files"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.ForeignKey(File, on_delete=models.CASCADE, related_name='trash_items')
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    trashed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='trashed_files'
    )
    state = models.CharField(max_length=50, choices=TrashState.choices, default='trashed')
    original_parent = models.ForeignKey(
        File,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+'
    )
    original_path = models.TextField(blank=True)
    original_name = models.CharField(max_length=255)
    size_bytes = models.BigIntegerField(null=True, blank=True)
    trashed_at = models.DateTimeField(auto_now_add=True)
    purge_after = models.DateTimeField(null=True, blank=True)  # Auto-delete after 30 days
    purged_at = models.DateTimeField(null=True, blank=True)
    restored_at = models.DateTimeField(null=True, blank=True)
    restored_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='restored_files'
    )

    class Meta:
        indexes = [
            models.Index(fields=['owner', 'state']),
            models.Index(fields=['purge_after']),
            models.Index(fields=['trashed_at']),
        ]
        ordering = ['-trashed_at']

    def __str__(self):
        return f"{self.original_name} (Trashed)"


class SpamFlag(models.Model):
    """Flag files as spam or abuse"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.ForeignKey(File, on_delete=models.CASCADE, related_name='spam_flags')
    reported_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    verdict = models.CharField(max_length=50, choices=SpamVerdict.choices, default='review_pending')
    confidence = models.FloatField(null=True, blank=True)  # 0.0-1.0
    reason = models.TextField(blank=True)
    scanner_version = models.CharField(max_length=50, blank=True)
    raw_signals = models.JSONField(default=dict, blank=True)
    quarantined = models.BooleanField(default=False)
    quarantined_at = models.DateTimeField(null=True, blank=True)
    resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_spam_flags'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['file', 'verdict']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Spam flag for {self.file.name}"


# ============================================================
# PERMISSIONS & SHARING
# ============================================================

class Permission(models.Model):
    """File and folder permissions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.ForeignKey(File, on_delete=models.CASCADE, related_name='permissions')
    grantee_user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    grantee_email = models.EmailField(blank=True)
    grantee_domain = models.CharField(max_length=255, blank=True)
    grantee_group_email = models.EmailField(blank=True)
    permission_type = models.CharField(max_length=50, choices=PermissionType.choices)
    role = models.CharField(max_length=50, choices=PermissionRole.choices)
    allow_file_discovery = models.BooleanField(default=False)
    deleted = models.BooleanField(default=False)
    expiration_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='revoked_permissions'
    )

    class Meta:
        indexes = [
            models.Index(fields=['file']),
            models.Index(fields=['grantee_user']),
            models.Index(fields=['expiration_time']),
        ]

    def __str__(self):
        return f"{self.get_role_display()} on {self.file.name}"


class ShareLink(models.Model):
    """Public share links for files"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.ForeignKey(File, on_delete=models.CASCADE, related_name='share_links')
    token = models.CharField(max_length=255, unique=True, db_index=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    password_hash = models.CharField(max_length=255, blank=True)
    max_uses = models.IntegerField(null=True, blank=True)
    use_count = models.IntegerField(default=0)
    role = models.CharField(max_length=50, choices=PermissionRole.choices, default='reader')
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['expires_at']),
        ]

    def save(self, *args, **kwargs):
        """Generate a unique token if not already set"""
        if not self.token:
            # Generate a unique 32-character token
            while True:
                self.token = get_random_string(32, allowed_chars='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
                # Check if token already exists
                if not ShareLink.objects.filter(token=self.token).exists():
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Share link for {self.file.name}"


class ShareLinkAccess(models.Model):
    """Track access to public share links"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    link = models.ForeignKey(ShareLink, on_delete=models.CASCADE, related_name='accesses')
    accessor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    accessed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['link', 'accessed_at']),
        ]

    def __str__(self):
        return f"Access to share link on {self.accessed_at}"


class FileRequest(models.Model):
    """Request files from others"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    destination_folder = models.ForeignKey(File, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    email_message = models.TextField(blank=True)
    accept_multiple = models.BooleanField(default=True)
    is_open = models.BooleanField(default=True)
    closes_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title


class FileRequestSubmission(models.Model):
    """Track file submissions to file requests"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.ForeignKey(FileRequest, on_delete=models.CASCADE, related_name='submissions')
    submitted_file = models.ForeignKey(File, on_delete=models.CASCADE)
    submitter = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    submitter_email = models.EmailField(blank=True)
    submitter_name = models.CharField(max_length=255, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['request', 'submitted_at']),
        ]

    def __str__(self):
        return f"Submission to {self.request.title}"


# ============================================================
# COMMENTS & ACTIVITY
# ============================================================

class Comment(models.Model):
    """Comments on files"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.ForeignKey(File, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    quoted_file_content = models.TextField(blank=True)
    anchor = models.JSONField(default=dict, blank=True)  # Anchoring region
    status = models.CharField(max_length=50, choices=CommentStatus.choices, default='open')
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_comments'
    )

    class Meta:
        indexes = [
            models.Index(fields=['file', 'status']),
            models.Index(fields=['author']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"Comment by {self.author.email} on {self.file.name}"


class CommentReply(models.Model):
    """Replies to comments"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='replies')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    action = models.CharField(max_length=50, blank=True)  # resolve, reopen, etc.
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['comment', 'author']),
        ]
        ordering = ['created_at']

    def __str__(self):
        return f"Reply by {self.author.email}"


class CommentMention(models.Model):
    """Track @mentions in comments"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True, blank=True)
    reply = models.ForeignKey(CommentReply, on_delete=models.CASCADE, null=True, blank=True)
    mentioned_user = models.ForeignKey(User, on_delete=models.CASCADE)
    notified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Mention for {self.mentioned_user.email}"


class ActivityFeed(models.Model):
    """Track file activities"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    target_file = models.ForeignKey(File, on_delete=models.CASCADE, related_name='activities')
    action = models.CharField(max_length=50, choices=ActivityAction.choices)
    old_value = models.JSONField(default=dict, blank=True)
    new_value = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['actor', 'occurred_at']),
            models.Index(fields=['target_file', 'occurred_at']),
            models.Index(fields=['action']),
        ]
        ordering = ['-occurred_at']

    def __str__(self):
        return f"{self.get_action_display()} by {self.actor.email if self.actor else 'System'}"


# ============================================================
# LABELS & SEARCH
# ============================================================

class Label(models.Model):
    """Labels for organizing files"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    published = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    revised_at = models.DateTimeField(auto_now=True)
    disabled_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title


class LabelField(models.Model):
    """Fields within labels"""
    FIELD_TYPE_CHOICES = [
        ('dateString', 'Date String'),
        ('integer', 'Integer'),
        ('selection', 'Selection'),
        ('text', 'Text'),
        ('user', 'User'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    label = models.ForeignKey(Label, on_delete=models.CASCADE, related_name='fields')
    field_key = models.CharField(max_length=100)
    display_name = models.CharField(max_length=255)
    field_type = models.CharField(max_length=50, choices=FIELD_TYPE_CHOICES)
    is_required = models.BooleanField(default=False)
    display_order = models.IntegerField(default=0)

    class Meta:
        unique_together = ('label', 'field_key')

    def __str__(self):
        return f"{self.label.title} - {self.display_name}"


class FileLabel(models.Model):
    """Apply labels to files"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.ForeignKey(File, on_delete=models.CASCADE, related_name='file_labels')
    label = models.ForeignKey(Label, on_delete=models.CASCADE)
    applied_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    removed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('file', 'label')

    def __str__(self):
        return f"{self.label.title} on {self.file.name}"


class SearchIndex(models.Model):
    """Full-text search index"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.OneToOneField(File, on_delete=models.CASCADE, related_name='search_index')
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    ts_vector = models.TextField()  # Tokenized search text
    name_tokens = models.TextField()
    content_hash = models.CharField(max_length=32, blank=True)
    indexed_at = models.DateTimeField(auto_now_add=True)
    needs_reindex = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['owner', 'needs_reindex']),
        ]

    def __str__(self):
        return f"Search index for {self.file.name}"


class SavedSearch(models.Model):
    """Save custom searches"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_searches')
    name = models.CharField(max_length=255)
    query = models.TextField()
    filters = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_run_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} by {self.user.email}"


class SearchHistory(models.Model):
    """Track search history"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    query = models.TextField()
    result_count = models.IntegerField(null=True, blank=True)
    searched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'searched_at']),
        ]
        ordering = ['-searched_at']

    def __str__(self):
        return f"Search: {self.query} by {self.user.email}"


# ============================================================
# AUDIT LOGS & COMPLIANCE
# ============================================================

class AuditLog(models.Model):
    """Comprehensive audit trail"""
    AUDIT_ACTIONS = [
        ('file_create', 'File Created'),
        ('file_view', 'File Viewed'),
        ('file_edit', 'File Edited'),
        ('file_rename', 'File Renamed'),
        ('file_copy', 'File Copied'),
        ('file_move', 'File Moved'),
        ('file_download', 'File Downloaded'),
        ('file_delete', 'File Deleted'),
        ('file_restore', 'File Restored'),
        ('share_create', 'Share Created'),
        ('share_update', 'Share Updated'),
        ('share_revoke', 'Share Revoked'),
        ('link_create', 'Link Created'),
        ('link_revoke', 'Link Revoked'),
        ('member_add', 'Member Added'),
        ('member_remove', 'Member Removed'),
        ('app_authorized', 'App Authorized'),
        ('app_revoked', 'App Revoked'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_id = models.CharField(max_length=255, unique=True, db_index=True)
    actor_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    actor_email = models.EmailField()
    target_file = models.ForeignKey(File, on_delete=models.SET_NULL, null=True, blank=True)
    target_file_name = models.CharField(max_length=255, blank=True)
    target_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_targets'
    )
    target_email = models.EmailField(blank=True)
    action = models.CharField(max_length=50, choices=AUDIT_ACTIONS)
    old_state = models.JSONField(default=dict, blank=True)
    new_state = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    country_code = models.CharField(max_length=2, blank=True)
    user_agent = models.TextField(blank=True)
    risk_score = models.FloatField(null=True, blank=True)  # 0.0-1.0
    occurred_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['actor_user', 'occurred_at']),
            models.Index(fields=['target_file', 'occurred_at']),
            models.Index(fields=['action']),
        ]
        ordering = ['-occurred_at']

    def __str__(self):
        return f"{self.get_action_display()} by {self.actor_email}"


class DLPViolation(models.Model):
    """Data Loss Prevention violations"""
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    audit_log = models.OneToOneField(AuditLog, on_delete=models.CASCADE, related_name='dlp_violation')
    policy_name = models.CharField(max_length=255)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    description = models.TextField()
    matched_pattern = models.CharField(max_length=255, blank=True)
    action_taken = models.CharField(max_length=50)  # block, warn, log
    detected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['severity', 'detected_at']),
        ]

    def __str__(self):
        return f"DLP Violation: {self.policy_name}"


# ============================================================
# API TOKEN
# ============================================================

class APIToken(models.Model):
    """Single global API token to gate access to /api/v1/"""
    label = models.CharField(max_length=100, default='Default API Token')
    key = models.CharField(max_length=64, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'API Token'
        verbose_name_plural = 'API Tokens'

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = get_random_string(64)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.label} ({'active' if self.is_active else 'disabled'})"


# ============================================================
# PRODUCT MODEL
# ============================================================

class Product(models.Model):
    """Product model for e-commerce API"""
    id = models.AutoField(primary_key=True)
    productName = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    productImage = models.CharField(max_length=500, blank=True, null=True)
    productDate = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-productDate']
        verbose_name = 'Product'
        verbose_name_plural = 'Products'

    def __str__(self):
        return self.productName

