from __future__ import annotations

import hashlib
import json
from typing import Any

from django.utils import timezone

from .algorithms.graph import graph_hash
from .models import Run


def build_cache_key(
    *, algorithm: str, version: str, graph: dict[str, Any], parameters: dict[str, Any], seed: int | None,
) -> str:
    canonical = {
        "algorithm": algorithm,
        "version": version,
        "graph_hash": graph_hash(graph),
        "parameters": parameters,
        "seed": seed,
    }
    encoded = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def active_cached_run(cache_key: str) -> Run | None:
    return (
        Run.objects.filter(
            cache_key=cache_key,
            status=Run.Status.COMPLETED,
            expires_at__gt=timezone.now(),
        )
        .exclude(result={})
        .order_by("created_at")
        .first()
    )
