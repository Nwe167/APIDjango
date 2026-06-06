from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.utils.crypto import get_random_string
from .models import (
    UserProfile, UserPreference, UserNotification,
    File, FileRevision,
    TrashItem, Permission, ShareLink,
    Comment, CommentReply, ActivityFeed, AuditLog, APIToken
)


# ============================================================
# CUSTOM USER ADMIN (fixes FK cascade delete order)
# ============================================================

admin.site.unregister(User)

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    def delete_model(self, request, obj):
        # Delete notifications first (has FK to Permission which has FK to User)
        obj.notifications.all().delete()
        # Permanently delete all owned files directly to avoid signal FK conflicts
        obj.owned_files.all().delete()
        obj.delete()

    def delete_queryset(self, request, queryset):
        for user in queryset:
            user.notifications.all().delete()
            user.owned_files.all().delete()
        queryset.delete()


# ============================================================
# CUSTOM ADMIN FILTERS
# ============================================================

class IsSharedFilter(admin.SimpleListFilter):
    title = 'Shared Status'
    parameter_name = 'is_shared'
    
    def lookups(self, request, model_admin):
        return [
            ('yes', 'Shared'),
            ('no', 'Not Shared'),
        ]
    
    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(is_shared=True)
        elif self.value() == 'no':
            return queryset.filter(is_shared=False)


class IsTrashedFilter(admin.SimpleListFilter):
    title = 'Trash Status'
    parameter_name = 'trashed'
    
    def lookups(self, request, model_admin):
        return [
            ('trashed', 'Trashed'),
            ('active', 'Active'),
        ]
    
    def queryset(self, request, queryset):
        if self.value() == 'trashed':
            return queryset.filter(trashed=True)
        elif self.value() == 'active':
            return queryset.filter(trashed=False)


# ============================================================
# USER & PROFILE ADMINS
# ============================================================

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user_email', 'storage_usage', 'is_suspended', 'last_login_at']
    list_filter = ['is_suspended', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'storage_quota_usage_bytes']

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'

    def storage_usage(self, obj):
        if obj.storage_quota_limit_bytes:
            usage_percent = (obj.storage_quota_usage_bytes / obj.storage_quota_limit_bytes) * 100
            return f"{usage_percent:.1f}% ({obj.storage_quota_usage_bytes / 1024**3:.2f} GB)"
        return f"{obj.storage_quota_usage_bytes / 1024**3:.2f} GB (Unlimited)"
    storage_usage.short_description = 'Storage Usage'


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user_email', 'theme', 'default_view', 'density']
    list_filter = ['theme', 'default_view', 'density']
    search_fields = ['user__email']
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'


@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    list_display = ['user_email', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__email', 'title']
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'


# ============================================================
# FILE & FOLDER ADMINS
# ============================================================

@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner_email', 'mime_type', 'size_display', 'is_shared', 'trashed', 'created_time']
    list_filter = [IsSharedFilter, IsTrashedFilter, 'mime_type', 'created_time']
    search_fields = ['name', 'owner__email', 'description']
    readonly_fields = ['created_time', 'modified_time', 'id']
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'owner', 'parent', 'mime_type', 'description')
        }),
        ('Storage', {
            'fields': ('size_bytes', 'file_path', 'md5_checksum', 'sha256_checksum')
        }),
        ('Sharing & Status', {
            'fields': ('is_shared', 'is_shared_with_me', 'writers_can_share', 'starred', 'trashed')
        }),
        ('Links', {
            'fields': ('web_view_link', 'web_content_link', 'thumbnail_link'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_time', 'modified_time', 'viewed_by_me_time', 'shared_with_me_time'),
            'classes': ('collapse',)
        }),
    )
    
    def owner_email(self, obj):
        return obj.owner.email
    owner_email.short_description = 'Owner'
    
    def size_display(self, obj):
        if obj.size_bytes:
            return f"{obj.size_bytes / 1024**2:.2f} MB"
        return "N/A"
    size_display.short_description = 'Size'


@admin.register(FileRevision)
class FileRevisionAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'revision_id', 'modified_by_email', 'modified_time', 'size_display']
    list_filter = ['modified_time']
    search_fields = ['file__name', 'revision_id']
    readonly_fields = ['modified_time']

    def file_name(self, obj):
        return obj.file.name
    file_name.short_description = 'File'

    def modified_by_email(self, obj):
        return obj.modified_by.email if obj.modified_by else 'System'
    modified_by_email.short_description = 'Modified By'

    def size_display(self, obj):
        if obj.size_bytes:
            return f"{obj.size_bytes / 1024**2:.2f} MB"
        return "N/A"
    size_display.short_description = 'Size'


# ============================================================
# TRASH ADMIN
# ============================================================

@admin.register(TrashItem)
class TrashItemAdmin(admin.ModelAdmin):
    list_display = ['original_name', 'owner_email', 'state', 'trashed_at', 'purge_after']
    list_filter = ['state', 'trashed_at', 'purge_after']
    search_fields = ['original_name', 'owner__email']
    readonly_fields = ['trashed_at', 'purged_at', 'restored_at']
    
    def owner_email(self, obj):
        return obj.owner.email
    owner_email.short_description = 'Owner'


# ============================================================
# PERMISSION & SHARING ADMINS
# ============================================================

@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'grantee_display', 'role', 'permission_type', 'created_at']
    list_filter = ['role', 'permission_type', 'created_at']
    search_fields = ['file__name', 'grantee_email', 'grantee_user__email']
    readonly_fields = ['created_at']
    
    def file_name(self, obj):
        return obj.file.name
    file_name.short_description = 'File'
    
    def grantee_display(self, obj):
        if obj.grantee_user:
            return obj.grantee_user.email
        return obj.grantee_email or obj.grantee_domain
    grantee_display.short_description = 'Grantee'


@admin.register(ShareLink)
class ShareLinkAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'token_short', 'role', 'use_count', 'created_at', 'expires_at']
    list_filter = ['role', 'created_at', 'expires_at']
    search_fields = ['file__name', 'token']
    readonly_fields = ['token', 'created_at']
    fieldsets = None

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return [(None, {'fields': ('file', 'role', 'max_uses', 'expires_at', 'password_hash')})]
        return [(None, {'fields': ('file', 'token', 'role', 'max_uses', 'use_count', 'expires_at', 'password_hash', 'created_at', 'revoked_at')})]

    def file_name(self, obj):
        return obj.file.name
    file_name.short_description = 'File'

    def token_short(self, obj):
        return obj.token[:10] + '...'
    token_short.short_description = 'Token'


# ============================================================
# COMMENT ADMINS
# ============================================================

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'author_email', 'status', 'created_at', 'is_deleted']
    list_filter = ['status', 'created_at', 'is_deleted']
    search_fields = ['file__name', 'author__email', 'content']
    readonly_fields = ['created_at', 'modified_at']
    
    def file_name(self, obj):
        return obj.file.name
    file_name.short_description = 'File'
    
    def author_email(self, obj):
        return obj.author.email
    author_email.short_description = 'Author'


@admin.register(CommentReply)
class CommentReplyAdmin(admin.ModelAdmin):
    list_display = ['comment_short', 'author_email', 'created_at']
    list_filter = ['created_at']
    search_fields = ['comment__file__name', 'author__email', 'content']
    readonly_fields = ['created_at']

    def comment_short(self, obj):
        return f"Reply to comment on {obj.comment.file.name}"
    comment_short.short_description = 'Comment'

    def author_email(self, obj):
        return obj.author.email
    author_email.short_description = 'Author'


# ============================================================
# ACTIVITY & AUDIT ADMINS
# ============================================================

@admin.register(ActivityFeed)
class ActivityFeedAdmin(admin.ModelAdmin):
    list_display = ['actor_email', 'file_name', 'action', 'occurred_at']
    list_filter = ['action', 'occurred_at']
    search_fields = ['actor__email', 'target_file__name']
    readonly_fields = ['occurred_at']
    
    def actor_email(self, obj):
        return obj.actor.email if obj.actor else 'System'
    actor_email.short_description = 'Actor'
    
    def file_name(self, obj):
        return obj.target_file.name if obj.target_file else 'N/A'
    file_name.short_description = 'File'


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['actor_email', 'file_name_short', 'action', 'risk_score_display', 'occurred_at']
    list_filter = ['action', 'occurred_at']
    search_fields = ['actor_email', 'target_file_name', 'target_email']
    readonly_fields = ['occurred_at', 'event_id']
    
    def file_name_short(self, obj):
        return obj.target_file_name[:30] + '...' if obj.target_file_name and len(obj.target_file_name) > 30 else obj.target_file_name
    file_name_short.short_description = 'File'
    
    def risk_score_display(self, obj):
        if obj.risk_score:
            if obj.risk_score > 0.7:
                color = '#dc3545'
            elif obj.risk_score > 0.4:
                color = '#ffc107'
            else:
                color = '#28a745'
            return format_html(
                f'<span style="background-color:{color};color:white;padding:5px 10px;border-radius:3px;">{obj.risk_score:.2f}</span>'
            )
        return 'N/A'
    risk_score_display.short_description = 'Risk Score'


# ============================================================
# API TOKEN ADMIN
# ============================================================

@admin.register(APIToken)
class APITokenAdmin(admin.ModelAdmin):
    list_display = ['label', 'key_preview', 'status_badge', 'created_at']
    readonly_fields = ['key', 'created_at']
    fields = ['label', 'key', 'is_active', 'created_at']
    actions = ['enable_tokens', 'disable_tokens', 'regenerate_tokens']

    def key_preview(self, obj):
        return obj.key[:12] + '...' + obj.key[-6:]
    key_preview.short_description = 'Token (preview)'

    def status_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="background:#28a745;color:#fff;padding:3px 10px;border-radius:4px">Active</span>')
        return format_html('<span style="background:#dc3545;color:#fff;padding:3px 10px;border-radius:4px">Disabled</span>')
    status_badge.short_description = 'Status'

    def save_model(self, request, obj, form, change):
        if not obj.key:
            obj.key = get_random_string(64)
        super().save_model(request, obj, form, change)

    @admin.action(description='Enable selected tokens')
    def enable_tokens(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f'{queryset.count()} token(s) enabled.')

    @admin.action(description='Disable selected tokens')
    def disable_tokens(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f'{queryset.count()} token(s) disabled.')

    @admin.action(description='Regenerate selected tokens (new key)')
    def regenerate_tokens(self, request, queryset):
        for token in queryset:
            token.key = get_random_string(64)
            token.save(update_fields=['key'])
        self.message_user(request, f'{queryset.count()} token(s) regenerated.')


# ============================================================
# ADMIN SITE CUSTOMIZATION
# ============================================================

admin.site.site_header = "File Sharing & Document Management System"
admin.site.site_title = "Admin Portal"
admin.site.index_title = "Welcome to Admin Portal"