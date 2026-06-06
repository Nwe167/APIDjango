from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json


def _get_active_token():
    """Return the key of the first active APIToken, or empty string."""
    from AppAPI.models import APIToken
    token = APIToken.objects.filter(is_active=True).first()
    return token.key if token else ''


def _ctx():
    """Base context injected into every template."""
    return {'API_TOKEN': _get_active_token()}


def frontend_index(request):
    return redirect('frontend_login')


def frontend_login(request):
    return render(request, 'app/login.html', _ctx())


def frontend_register(request):
    return render(request, 'app/register.html', _ctx())


def frontend_dashboard(request):
    return render(request, 'app/dashboard.html', _ctx())


def frontend_files(request):
    return render(request, 'app/files.html', _ctx())


def frontend_folders(request):
    return render(request, 'app/folders.html', _ctx())


def frontend_shared(request):
    return render(request, 'app/shared.html', _ctx())


def frontend_trash(request):
    return render(request, 'app/trash.html', _ctx())


def frontend_activity(request):
    return render(request, 'app/activity.html', _ctx())


def frontend_notifications(request):
    return render(request, 'app/notifications.html', _ctx())


def frontend_settings(request):
    return render(request, 'app/settings.html', _ctx())


def frontend_profile(request):
    return render(request, 'app/profile.html', _ctx())


def frontend_admin_security(request):
    return render(request, 'app/admin-security.html', _ctx())


def frontend_api(request):
    return render(request, 'app/api.html', _ctx())


def frontend_forgot_password(request):
    return render(request, 'app/forgot-password.html', _ctx())


# ============================================================
# LOGIN / LOGOUT API  (replaces /api-token-auth/)
# ============================================================

@csrf_exempt
@require_http_methods(['POST'])
def api_login(request):
    """
    POST /api/auth/login/
    Body: {"username": "...", "password": "..."}

    Creates a Django session and returns the global API token.
    The frontend stores this token and sends it as:
        Authorization: Token <key>
    on every subsequent request.
    """
    try:
        body = json.loads(request.body)
    except (ValueError, KeyError):
        return JsonResponse({'detail': 'Invalid JSON.'}, status=400)

    username = body.get('username', '').strip()
    password = body.get('password', '').strip()

    if not username or not password:
        return JsonResponse({'detail': 'username and password are required.'}, status=400)

    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({'detail': 'Invalid credentials.'}, status=400)

    if not user.is_active:
        return JsonResponse({'detail': 'Account is disabled.'}, status=403)

    auth_login(request, user)

    from AppAPI.models import APIToken
    token = APIToken.objects.filter(is_active=True).first()
    if not token:
        return JsonResponse({'detail': 'Service temporarily unavailable. Please contact the administrator.'}, status=503)

    return JsonResponse({
        'token': token.key,
        'user_id': user.id,
        'username': user.username,
        'email': user.email,
    })


@csrf_exempt
@require_http_methods(['POST'])
def api_logout(request):
    """POST /api/auth/logout/ — ends the Django session."""
    auth_logout(request)
    return JsonResponse({'detail': 'Logged out.'})
