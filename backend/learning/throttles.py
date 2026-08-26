from __future__ import annotations

from django.conf import settings
from django.core.cache import cache
from rest_framework.throttling import SimpleRateThrottle


HEAVY_ALGORITHMS = {
    "paths.floyd",
    "community.divisive",
    "community.girvan_newman",
    "robustness.attack",
    "community.dynamic",
    "embedding.ae",
    "embedding.cnn",
    "embedding.gcn",
    "embedding.gat",
    "link_prediction.common_neighbors",
    "link_prediction.jaccard",
    "link_prediction.adamic_adar",
    "link_prediction.resource_allocation",
}


class ClientCategoryThrottle(SimpleRateThrottle):
    """Throttle anonymous work by IP/session and independently by operation category."""

    category = "public"
    setting_name = "PUBLIC_OPERATION_RATES"
    identity_scope = "ip"

    def allow_request(self, request, view):
        self.request = request
        self.rate = self.get_rate()
        if self.rate is None:
            return True
        self.num_requests, self.duration = self.parse_rate(self.rate)
        self.key = self.get_cache_key(request, view)
        if self.key is None:
            return True
        if cache.add(self.key, 1, self.duration):
            count = 1
        else:
            try:
                count = cache.incr(self.key)
            except ValueError:
                cache.set(self.key, 1, self.duration)
                count = 1
        return count <= self.num_requests

    def wait(self):
        return self.duration

    def get_category(self, request) -> str:
        return self.category

    def get_rate(self):
        rates = getattr(settings, self.setting_name, {})
        request = getattr(self, "request", None)
        category = self.get_category(request) if request is not None else self.category
        return rates.get(category)

    def get_cache_key(self, request, view):
        self.request = request
        identity = self.get_identity(request)
        if identity is None:
            return None
        scope = f"{self.get_category(request)}:{self.identity_scope}"
        return self.cache_format % {"scope": scope, "ident": identity}

    def get_identity(self, request) -> str | None:
        return self.get_ident(request)


class PublicOperationIPThrottle(ClientCategoryThrottle):
    pass


class SessionIdentityMixin:
    identity_scope = "session"

    def get_identity(self, request) -> str | None:
        return getattr(request._request, "_anonymous_public_session_key", None)


class PublicOperationSessionThrottle(SessionIdentityMixin, ClientCategoryThrottle):
    pass


class AlgorithmIPThrottle(ClientCategoryThrottle):
    setting_name = "PUBLIC_ALGORITHM_RATES"

    def get_category(self, request) -> str:
        data = request.data if isinstance(request.data, dict) else {}
        return "heavy" if data.get("algorithm") in HEAVY_ALGORITHMS else "standard"


class AlgorithmSessionThrottle(SessionIdentityMixin, AlgorithmIPThrottle):
    pass
