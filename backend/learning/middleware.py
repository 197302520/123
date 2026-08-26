from __future__ import annotations

from ipaddress import ip_address
import secrets

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse


def client_ip(request) -> str | None:
    """Return a validated client address, trusting the configured reverse proxy only."""
    candidates = []
    if getattr(settings, "TRUST_PROXY_HEADERS", False):
        candidates.append(request.META.get("HTTP_X_REAL_IP"))
    candidates.append(request.META.get("REMOTE_ADDR"))
    for value in candidates:
        if not isinstance(value, str):
            continue
        try:
            return str(ip_address(value.strip()))
        except ValueError:
            continue
    return None


class TeacherLoginThrottleMiddleware:
    """Bound repeated Django-admin login POSTs without storing credentials or bodies."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "POST" and request.path.rstrip("/") == "/admin/login":
            address = client_ip(request) or "unknown"
            key = f"teacher-login:{address}"
            limit = int(getattr(settings, "TEACHER_LOGIN_ATTEMPTS", 5))
            duration = int(getattr(settings, "TEACHER_LOGIN_WINDOW_SECONDS", 900))
            if cache.add(key, 1, duration):
                attempts = 1
            else:
                try:
                    attempts = cache.incr(key)
                except ValueError:
                    cache.set(key, 1, duration)
                    attempts = 1
            if attempts > limit:
                return JsonResponse({"detail": "登录尝试过多，请稍后再试。"}, status=429)
            response = self.get_response(request)
            if response.status_code in {301, 302, 303, 307, 308}:
                cache.delete(key)
            return response
        return self.get_response(request)


class AnonymousPublicSessionMiddleware:
    """Give anonymous API clients a random rate-limit bucket without creating a profile."""

    prefixes = ("/api/graphs/", "/api/runs", "/api/reports")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        generated = False
        if request.path.startswith(self.prefixes):
            cookie_name = settings.SESSION_COOKIE_NAME
            identity = request.COOKIES.get(cookie_name)
            if not identity:
                identity = secrets.token_urlsafe(32)
                generated = True
            request._anonymous_public_session_key = identity
        response = self.get_response(request)
        if generated:
            response.set_cookie(
                settings.SESSION_COOKIE_NAME,
                request._anonymous_public_session_key,
                max_age=2 * 60 * 60,
                secure=settings.SESSION_COOKIE_SECURE,
                httponly=True,
                samesite=settings.SESSION_COOKIE_SAMESITE,
            )
        return response
