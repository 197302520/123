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


def _xml_legal_text(value: str) -> bool:
    return all(
        character in "\t\n\r"
        or "\x20" <= character <= "\ud7ff"
        or "\ue000" <= character <= "\ufffd"
        or "\U00010000" <= character <= "\U0010ffff"
        for character in value
    )


def _validate_attribute_value(value: Any, path: str) -> None:
    if value is None or isinstance(value, (bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise AlgorithmInputError("节点属性数值必须是有限值。", path=path)
        return
    if isinstance(value, str):
        if not _xml_legal_text(value):
            raise AlgorithmInputError("节点属性包含 XML 不支持的控制字符。", path=path)
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_attribute_value(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str) or not _xml_legal_text(key):
                raise AlgorithmInputError("节点属性名必须是安全文本。", path=path)
            _validate_attribute_value(item, f"{path}.{key}")
        return
    raise AlgorithmInputError("节点属性必须是 JSON 值。", path=path)


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

    normalized_nodes: list[dict[str, Any]] = []
    node_ids: set[str] = set()
    for index, node in enumerate(nodes):
        node_id = node.get("id") if isinstance(node, dict) else None
        if not isinstance(node_id, str) or not node_id:
            raise AlgorithmInputError("节点 id 必须是非空字符串。", path=f"nodes[{index}].id")
        if not _xml_legal_text(node_id):
            raise AlgorithmInputError("节点 id 包含 XML 不支持的控制字符。", path=f"nodes[{index}].id")
        if node_id in node_ids:
            raise AlgorithmInputError(f"节点 '{node_id}' 重复。", path=f"nodes[{index}].id")
        node_ids.add(node_id)
        label = node.get("label", node_id)
        label = label if isinstance(label, str) else node_id
        if not _xml_legal_text(label):
            raise AlgorithmInputError("节点标签包含 XML 不支持的控制字符。", path=f"nodes[{index}].label")
        normalized_node: dict[str, Any] = {"id": node_id, "label": label}
        if "attributes" in node:
            attributes = node["attributes"]
            if not isinstance(attributes, dict):
                raise AlgorithmInputError("节点 attributes 必须是对象。", path=f"nodes[{index}].attributes")
            _validate_attribute_value(attributes, f"nodes[{index}].attributes")
            normalized_node["attributes"] = attributes
        normalized_nodes.append(normalized_node)

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
    network.add_nodes_from(
        (node["id"], {"label": node["label"], **node.get("attributes", {})})
        for node in graph["nodes"]
    )
    network.add_weighted_edges_from(
        (edge["source"], edge["target"], edge["weight"]) for edge in graph["edges"]
    )
    return network


def nx_to_graph(network: nx.Graph | nx.DiGraph) -> dict[str, Any]:
    nodes = []
    for node in sorted(network.nodes, key=str):
        values = dict(network.nodes[node])
        normalized_node = {"id": str(node), "label": str(values.pop("label", node))}
        if values:
            normalized_node["attributes"] = values
        nodes.append(normalized_node)
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
