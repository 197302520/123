from __future__ import annotations

import hashlib
import json
from typing import Any

from .graph import graph_hash


def table(key: str, name: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    columns = list(rows[0]) if rows else []
    return {"key": key, "name": name, "columns": columns, "rows": rows}


def chart(key: str, chart_type: str, series: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    return {"key": key, "type": chart_type, "series": series, **extra}


def overlay(
    key: str,
    *,
    nodes: list[dict[str, Any]] | None = None,
    edges: list[dict[str, Any]] | None = None,
    node_styles: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "key": key,
        "nodes": nodes or [],
        "edges": edges or [],
        "node_styles": node_styles or {},
    }

def result(
    algorithm: str,
    version: str,
    graph: dict[str, Any],
    parameters: dict[str, Any],
    seed: int | None,
    *,
    tables: list[dict[str, Any]] | None = None,
    overlays: list[dict[str, Any]] | None = None,
    charts: list[dict[str, Any]] | None = None,
    warnings: list[str] | None = None,
    provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    parameter_digest = hashlib.sha256(
        json.dumps(parameters, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()
    return {
        "tables": tables or [],
        "overlays": overlays or [],
        "charts": charts or [],
        "warnings": warnings or [],
        "provenance": {
            "algorithm": algorithm,
            "version": version,
            "seed": seed,
            "graph_hash": graph_hash(graph),
            "parameter_hash": parameter_digest,
            **(provenance or {}),
        },
        "validation": {"valid": True, "errors": [], "graph": graph},
    }
