from __future__ import annotations

import math
from typing import Any

import networkx as nx

from .errors import AlgorithmInputError


def coerce_finite_float(value: Any) -> float | None:
    try:
        converted = float(value)
    except (OverflowError, TypeError, ValueError):
        return None
    return converted if math.isfinite(converted) else None


def normalize_graph(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise AlgorithmInputError("图必须是对象。", path="graph")
    directed = payload.get("directed")
    nodes = payload.get("nodes")
    edges = payload.get("edges")
    if not isinstance(directed, bool):
        raise AlgorithmInputError("directed 必须是布尔值。", path="directed")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise AlgorithmInputError("nodes 和 edges 必须是数组。", path="graph")

    normalized_nodes: list[dict[str, str]] = []
    node_ids: set[str] = set()
    for index, node in enumerate(nodes):
        node_id = node.get("id") if isinstance(node, dict) else None
        if not isinstance(node_id, str) or not node_id:
            raise AlgorithmInputError("节点 id 必须是非空字符串。", path=f"nodes[{index}].id")
        if node_id in node_ids:
            raise AlgorithmInputError(f"节点 '{node_id}' 重复。", path=f"nodes[{index}].id")
        node_ids.add(node_id)
        label = node.get("label", node_id)
        normalized_nodes.append({"id": node_id, "label": label if isinstance(label, str) else node_id})

    normalized_edges: list[dict[str, Any]] = []
    seen_edges: set[tuple[str, str]] = set()
    for index, edge in enumerate(edges):
        source = edge.get("source") if isinstance(edge, dict) else None
        target = edge.get("target") if isinstance(edge, dict) else None
        if not isinstance(source, str) or source not in node_ids:
            raise AlgorithmInputError(f"节点 '{source}' 不存在。", path=f"edges[{index}].source")
        if not isinstance(target, str) or target not in node_ids:
            raise AlgorithmInputError(f"节点 '{target}' 不存在。", path=f"edges[{index}].target")
        weight = edge.get("weight", 1) if isinstance(edge, dict) else 1
        if isinstance(weight, bool) or not isinstance(weight, (int, float)):
            raise AlgorithmInputError("边权重必须是数值。", path=f"edges[{index}].weight")
        normalized_weight = coerce_finite_float(weight)
        if normalized_weight is None:
            raise AlgorithmInputError("边权重必须是有限数值。", path=f"edges[{index}].weight")
        if normalized_weight <= 0:
            raise AlgorithmInputError("边权重必须大于 0。", path=f"edges[{index}].weight")
        edge_key = (source, target) if directed or source <= target else (target, source)
        if edge_key in seen_edges:
            raise AlgorithmInputError(f"边 '{source}-{target}' 重复。", path=f"edges[{index}]")
        seen_edges.add(edge_key)
        normalized_edges.append({"source": source, "target": target, "weight": normalized_weight})
    return {"directed": directed, "nodes": normalized_nodes, "edges": normalized_edges}


def build_nx_graph(graph: dict[str, Any]) -> nx.Graph | nx.DiGraph:
    network: nx.Graph | nx.DiGraph = nx.DiGraph() if graph["directed"] else nx.Graph()
    network.add_nodes_from((node["id"], {"label": node["label"]}) for node in graph["nodes"])
    network.add_weighted_edges_from(
        (edge["source"], edge["target"], edge["weight"]) for edge in graph["edges"]
    )
    return network


def nx_to_graph(network: nx.Graph | nx.DiGraph) -> dict[str, Any]:
    nodes = [
        {"id": str(node), "label": str(network.nodes[node].get("label", node))}
        for node in sorted(network.nodes, key=str)
    ]
    edges = [
        {"source": str(source), "target": str(target), "weight": float(data.get("weight", 1))}
        for source, target, data in sorted(network.edges(data=True), key=lambda edge: (str(edge[0]), str(edge[1])))
    ]
    return {"directed": network.is_directed(), "nodes": nodes, "edges": edges}


def graph_hash(graph: dict[str, Any]) -> str:
    import hashlib
    import json

    canonical_edges = []
    for edge in graph["edges"]:
        canonical_edge = dict(edge)
        if not graph["directed"] and canonical_edge["source"] > canonical_edge["target"]:
            canonical_edge["source"], canonical_edge["target"] = canonical_edge["target"], canonical_edge["source"]
        canonical_edges.append(canonical_edge)
    canonical = {
        "directed": graph["directed"],
        "nodes": sorted(graph["nodes"], key=lambda item: item["id"]),
        "edges": sorted(canonical_edges, key=lambda item: (item["source"], item["target"], item["weight"])),
    }
    return hashlib.sha256(json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
