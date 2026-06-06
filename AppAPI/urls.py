from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router and register our viewsets
router = DefaultRouter()

# User management
router.register(r'users/profile', views.UserProfileViewSet, basename='user-profile')
router.register(r'users/sessions', views.UserSessionViewSet, basename='user-session')
router.register(r'users/preferences', views.UserPreferenceViewSet, basename='user-preferences')
router.register(r'users/notifications', views.UserNotificationViewSet, basename='user-notifications')

# Files
router.register(r'files', views.FileViewSet, basename='file')
router.register(r'files/paths', views.FilePathViewSet, basename='file-path')
router.register(r'files/revisions', views.FileRevisionViewSet, basename='file-revision')
router.register(r'files/content-hints', views.FileContentHintViewSet, basename='file-content-hint')
router.register(r'files/image-metadata', views.ImageMediaMetadataViewSet, basename='image-metadata')
router.register(r'files/video-metadata', views.VideoMediaMetadataViewSet, basename='video-metadata')

# Permissions and sharing
router.register(r'permissions', views.PermissionViewSet, basename='permission')
router.register(r'share-links', views.ShareLinkViewSet, basename='share-link')
router.register(r'share-link-accesses', views.ShareLinkAccessViewSet, basename='share-link-access')

# File requests
router.register(r'file-requests', views.FileRequestViewSet, basename='file-request')
router.register(r'file-request-submissions', views.FileRequestSubmissionViewSet, basename='file-request-submission')

# Trash and spam
router.register(r'trash', views.TrashViewSet, basename='trash')
router.register(r'spam-flags', views.SpamFlagViewSet, basename='spam-flag')

# Comments
router.register(r'comments', views.CommentViewSet, basename='comment')
router.register(r'comment-replies', views.CommentReplyViewSet, basename='comment-reply')
router.register(r'comment-mentions', views.CommentMentionViewSet, basename='comment-mention')

# Activity and audit
router.register(r'activity', views.ActivityFeedViewSet, basename='activity-feed')
router.register(r'audit-logs', views.AuditLogViewSet, basename='audit-log')
router.register(r'dlp-violations', views.DLPViolationViewSet, basename='dlp-violation')

# Labels
router.register(r'labels', views.LabelViewSet, basename='label')
router.register(r'label-fields', views.LabelFieldViewSet, basename='label-field')
router.register(r'file-labels', views.FileLabelViewSet, basename='file-label')

# Search
router.register(r'search-index', views.SearchIndexViewSet, basename='search-index')
router.register(r'saved-searches', views.SavedSearchViewSet, basename='saved-search')
router.register(r'search-history', views.SearchHistoryViewSet, basename='search-history')

# Products
router.register(r'apiproducts/products', views.ProductViewSet, basename='product')

urlpatterns = [
    # Public API root (no auth) to help discover endpoints
    path('', views.api_root, name='api-root'),
    # Registration endpoint
    path('users/register/', views.RegistrationView.as_view(), name='user-register'),
    
    # Category pages
    path('PostAPICategory/', views.PostAPICategory, name='PostAPICategory'),
    path('PutAPICategory/', views.PutAPICategory, name='PutAPICategory'),
    path('DeleteAPICategory/', views.DeleteAPICategory, name='DeleteAPICategory'),
    path('files/create-folder/', views.create_folder, name='create-folder'),
    path('files/create_folder/', views.create_folder, name='create-folder-legacy'),
    
    path('', include(router.urls)),
    path('storage/quota/', views.storage_quota, name='storage-quota'),
]
