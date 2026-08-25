"""Shared public API shapes mirrored by frontend/src/api/contracts.ts."""
from __future__ import annotations

from typing import NotRequired, TypedDict


class GraphInputNode(TypedDict):
    id: str
    label: NotRequired[str]


class GraphInputEdge(TypedDict):
    source: str
    target: str
    weight: NotRequired[float]


class GraphInputSpec(TypedDict):
    directed: bool
    nodes: list[GraphInputNode]
    edges: list[GraphInputEdge]


class GraphNode(TypedDict):
    id: str
    label: str


class GraphEdge(TypedDict):
    source: str
    target: str
    weight: float


class GraphSpec(TypedDict):
    directed: bool
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class AlgorithmSpec(TypedDict):
    key: str
    name: str
    supported_graph_types: list[str]
    parameters: dict[str, object]
    version: str
    description: str
    limits: dict[str, int]
    formula: str
    explanation: str
    advantages: list[str]
    limitations: list[str]


class RunRequest(TypedDict):
    algorithm: str
    graph: GraphInputSpec
    parameters: dict[str, object]
    seed: NotRequired[int | None]


class RunResult(TypedDict):
    run_id: str
    status: str
    tables: list[object]
    overlays: list[object]
    charts: list[object]
    warnings: list[str]
    provenance: dict[str, object]
    validation: dict[str, object]


from .algorithms.registry import ALGORITHM_REGISTRY as _ALGORITHM_REGISTRY


ALGORITHM_REGISTRY: list[AlgorithmSpec] = _ALGORITHM_REGISTRY  # type: ignore[assignment]
GRAPH_VALIDATE_SPEC: AlgorithmSpec = ALGORITHM_REGISTRY[0]
