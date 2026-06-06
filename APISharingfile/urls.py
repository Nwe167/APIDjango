"""
URL configuration for APISharingfile project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.urls import re_path
from AppAPI import frontend as frontend_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('AppAPI.urls')),
    path('api-auth/', include('rest_framework.urls')),
    path('api/auth/login/', frontend_views.api_login, name='api-login'),
    path('api/auth/logout/', frontend_views.api_logout, name='api-logout'),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    
    # Frontend URLs - NEW DJANGO TEMPLATE-BASED VIEWS
    path('', frontend_views.frontend_index, name='frontend_index'),
    path('frontend/', frontend_views.frontend_index, name='frontend_index_alt'),
    path('frontend/login/', frontend_views.frontend_login, name='frontend_login'),
    path('frontend/register/', frontend_views.frontend_register, name='frontend_register'),
    path('frontend/forgot-password/', frontend_views.frontend_forgot_password, name='frontend_forgot_password'),
    path('frontend/dashboard/', frontend_views.frontend_dashboard, name='frontend_dashboard'),
    path('frontend/files/', frontend_views.frontend_files, name='frontend_files'),
    path('frontend/folders/', frontend_views.frontend_folders, name='frontend_folders'),
    path('frontend/shared/', frontend_views.frontend_shared, name='frontend_shared'),
    path('frontend/trash/', frontend_views.frontend_trash, name='frontend_trash'),
    path('frontend/activity/', frontend_views.frontend_activity, name='frontend_activity'),
    path('frontend/notifications/', frontend_views.frontend_notifications, name='frontend_notifications'),
    path('frontend/settings/', frontend_views.frontend_settings, name='frontend_settings'),
    path('frontend/profile/', frontend_views.frontend_profile, name='frontend_profile'),
    path('frontend/api/', frontend_views.frontend_api, name='frontend_api'),
    path('frontend/admin-security/', frontend_views.frontend_admin_security, name='frontend_admin_security'),

    # Legacy project URLs kept for saved links in old notifications/emails
    path('project/notifications.html', frontend_views.frontend_notifications, name='legacy_notifications'),
    path('project/files.html', frontend_views.frontend_files, name='legacy_files'),
    
    # Serve project HTML files (legacy - for backward compatibility)
    re_path(r'^project/(?P<path>.*\.html)$', serve, {'document_root': settings.BASE_DIR / 'project'}),
    re_path(r'^project/(?P<path>.*)$', serve, {'document_root': settings.BASE_DIR / 'project'}),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
