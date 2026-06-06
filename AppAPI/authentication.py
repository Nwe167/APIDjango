from rest_framework.permissions import BasePermission
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.authentication import SessionAuthentication
from django.http import JsonResponse


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """SessionAuthentication without CSRF enforcement — used on public endpoints."""
    def enforce_csrf(self, request):
        return


class APITokenMiddleware:
    """
    Middleware that enforces the global API token on every request
    under /api/v1/ — cannot be bypassed by view-level permission overrides.
    Exempt paths: /api/v1/users/register/ (POST only) and /api/auth/.
    """
    EXEMPT = [
        '/api/auth/login/',
        '/api/auth/logout/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # Only gate /api/v1/ routes
        if path.startswith('/api/v1/'):
            # Allow POST to register without token
            if path == '/api/v1/users/register/' and request.method == 'POST':
                return self.get_response(request)

            from .models import APIToken
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            if auth_header.startswith('Token '):
                key = auth_header[6:].strip()
            else:
                key = request.GET.get('token', '').strip()

            if not key or not APIToken.objects.filter(key=key, is_active=True).exists():
                return JsonResponse(
                    {'detail': 'A valid active API token is required.'},
                    status=403
                )

        return self.get_response(request)


class GlobalTokenRequired(BasePermission):
    """
    Every request to /api/v1/ must supply the global API token either as:
        Authorization: Token <key>
    or as a query parameter:
        ?token=<key>

    This is enforced at the middleware level via ALWAYS_APPLY so it cannot
    be bypassed by view-level permission_classes overrides.
    """

    message = 'A valid active API token is required.'

    def has_permission(self, request, view):
        from .models import APIToken

        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Token '):
            key = auth_header[6:].strip()
        else:
            key = request.GET.get('token', '').strip()

        if not key:
            return False

        return APIToken.objects.filter(key=key, is_active=True).exists()
