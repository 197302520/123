from __future__ import annotations

from ipaddress import ip_address

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
            attempts = int(cache.get(key, 0))
            limit = int(getattr(settings, "TEACHER_LOGIN_ATTEMPTS", 5))
            if attempts >= limit:
                return JsonResponse({"detail": "登录尝试过多，请稍后再试。"}, status=429)
            cache.set(key, attempts + 1, int(getattr(settings, "TEACHER_LOGIN_WINDOW_SECONDS", 900)))
        return self.get_response(request)
