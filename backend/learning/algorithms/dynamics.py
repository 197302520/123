from __future__ import annotations

import random
from collections import Counter, defaultdict
from typing import Any

import networkx as nx

from .errors import AlgorithmInputError
from .graph import build_nx_graph, coerce_finite_float, normalize_graph
from .results import chart, overlay, table


def _initial_opinions(network: nx.Graph | nx.DiGraph, params: dict[str, Any]) -> dict[Any, float]:
    supplied = params.get("opinions", {})
    if not isinstance(supplied, dict):
        raise AlgorithmInputError("opinions 必须是节点到数值的对象。", path="parameters.opinions")
    nodes = list(sorted(network.nodes, key=str))
    opinions: dict[Any, float] = {}
    for index, node in enumerate(nodes):
        value = supplied.get(str(node), index / max(1, len(nodes) - 1))
        converted = coerce_finite_float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None
        if converted is None or not 0 <= converted <= 1:
            raise AlgorithmInputError(f"节点 '{node}' 的意见必须在 0–1 之间。", path=f"parameters.opinions.{node}")
        opinions[node] = converted
    return opinions


def _influence_average(network: nx.Graph | nx.DiGraph, opinions: dict[Any, float], node: Any) -> float:
    neighbors = list(network.predecessors(node)) if network.is_directed() else list(network.neighbors(node))
    weighted = [(node, 1.0)] + [(neighbor, float(network[neighbor][node].get("weight", 1))) for neighbor in neighbors]
    denominator = sum(weight for _, weight in weighted)
    return sum(opinions[neighbor] * weight for neighbor, weight in weighted) / denominator


def _history_chart(history: list[dict[Any, float]]) -> dict[str, Any]:
    nodes = list(sorted(history[0], key=str)) if history else []
    return chart(
        "opinion_trajectory",
        "line",
        [
            {"name": str(node), "data": [{"x": step, "y": float(values[node])} for step, values in enumerate(history)]}
            for node in nodes
        ],
        x_label="迭代",
        y_label="意见",
    )


def run_opinion(key: str, graph: dict[str, Any], params: dict[str, Any], seed: int | None) -> dict[str, Any]:
    network = build_nx_graph(graph)
    if len(network) == 0:
        raise AlgorithmInputError("意见模型至少需要 1 个节点。")
    opinions = _initial_opinions(network, params)
    history = [dict(opinions)]
    tolerance = params["tolerance"]
    converged = False
    iterations = 0

    if key in {"opinion.degroot", "opinion.friedkin_johnsen"}:
        initial = dict(opinions)
        stubbornness = params["stubbornness"] if key == "opinion.friedkin_johnsen" else 0.0
        for iterations in range(1, params["max_iterations"] + 1):
            averages = {node: _influence_average(network, opinions, node) for node in network.nodes}
            updated = {
                node: stubbornness * initial[node] + (1 - stubbornness) * averages[node]
                for node in network.nodes
            }
            delta = max(abs(updated[node] - opinions[node]) for node in network.nodes)
            opinions = updated
            history.append(dict(opinions))
            if delta <= tolerance:
                converged = True
                break
    elif key == "opinion.deffuant":
        rng = random.Random(seed)
        edges = list(sorted(network.edges, key=lambda edge: (str(edge[0]), str(edge[1]))))
        if not edges:
            converged = True
        for iterations in range(1, params["steps"] + 1):
            if not edges:
                break
            source, target = rng.choice(edges)
            if abs(opinions[source] - opinions[target]) <= params["confidence"]:
                difference = opinions[target] - opinions[source]
                opinions[source] += params["mu"] * difference
                opinions[target] -= params["mu"] * difference
            if iterations <= 100 or iterations % max(1, params["steps"] // 100) == 0:
                history.append(dict(opinions))
        # Deffuant converges to one or more stable bounded-confidence clusters.
        active_differences = [abs(opinions[source] - opinions[target]) for source, target in edges if abs(opinions[source] - opinions[target]) <= params["confidence"]]
        converged = not active_differences or max(active_differences) <= max(tolerance, 1e-3)
    elif key == "opinion.hk":
        confidence = params["confidence"]
        for iterations in range(1, params["max_iterations"] + 1):
            updated: dict[Any, float] = {}
            for node in network.nodes:
                structural = {node} | (set(network.predecessors(node)) if network.is_directed() else set(network.neighbors(node)))
                trusted = [neighbor for neighbor in structural if abs(opinions[neighbor] - opinions[node]) <= confidence]
                updated[node] = sum(opinions[neighbor] for neighbor in trusted) / len(trusted)
            delta = max(abs(updated[node] - opinions[node]) for node in network.nodes)
            opinions = updated
            history.append(dict(opinions))
            if delta <= tolerance:
                converged = True
                break
    else:
        raise KeyError(key)

    rows = [{"node": str(node), "initial_opinion": history[0][node], "opinion": float(opinions[node])} for node in sorted(network.nodes, key=str)]
    warnings = [] if converged else [f"在 {iterations} 次迭代/交互后未达到设定收敛容差。"]
    return {
        "tables": [table("opinions", "意见结果", rows)],
        "overlays": [overlay("opinions", nodes=[{"node": row["node"], "value": row["opinion"]} for row in rows])],
        "charts": [_history_chart(history)],
        "warnings": warnings,
        "provenance": {"converged": converged, "iterations": iterations, "final_range": max(opinions.values()) - min(opinions.values())},
    }

def _parse_partition(values: list[Any], nodes: set[str]) -> list[set[str]]:
    if not isinstance(values, list):
        raise AlgorithmInputError("每个快照的社区分区必须是数组。", path="parameters.snapshot_communities")
    result: list[set[str]] = []
    for value in values:
        if isinstance(value, str):
            group = {item for item in value.split("|") if item}
        elif isinstance(value, list):
            group = {str(item) for item in value}
        else:
            raise AlgorithmInputError("社区必须是节点数组或以 | 分隔的字符串。", path="parameters.snapshot_communities")
        unknown = group - nodes
        if unknown:
            raise AlgorithmInputError(f"快照社区包含不存在的节点：{sorted(unknown)}。", path="parameters.snapshot_communities")
        if group:
            result.append(group)
    counts = Counter(node for group in result for node in group)
    duplicated = sorted(node for node, count in counts.items() if count > 1)
    if duplicated:
        raise AlgorithmInputError(f"快照社区中的节点重复归属：{duplicated}。", path="parameters.snapshot_communities")
    missing = sorted(nodes - set(counts))
    if missing:
        raise AlgorithmInputError(f"快照社区分区缺少节点：{missing}。", path="parameters.snapshot_communities")
    return sorted(result, key=lambda group: tuple(sorted(group)))


def _detect_partition(snapshot: dict[str, Any], seed: int | None) -> list[set[str]]:
    network = build_nx_graph(snapshot)
    if not network:
        return []
    if not network.number_of_edges():
        return [{str(node)} for node in sorted(network.nodes, key=str)]
    return [set(map(str, group)) for group in nx.community.louvain_communities(network, weight="weight", seed=seed)]


def _jaccard(left: set[str], right: set[str]) -> float:
    return len(left & right) / len(left | right) if left | right else 0.0


def run_dynamic(graph: dict[str, Any], params: dict[str, Any], seed: int | None, limits: dict[str, int]) -> dict[str, Any]:
    raw_snapshots = params.get("snapshots") or [graph]
    if not isinstance(raw_snapshots, list) or not raw_snapshots:
        raise AlgorithmInputError("snapshots 必须是非空图数组。", path="parameters.snapshots")
    snapshots = []
    for index, raw_snapshot in enumerate(raw_snapshots):
        try:
            snapshot = normalize_graph(raw_snapshot)
        except AlgorithmInputError as exc:
            raise AlgorithmInputError(str(exc), code=exc.code, path=f"parameters.snapshots[{index}].{exc.path}") from exc
        if snapshot["directed"]:
            raise AlgorithmInputError("动态社区快照仅支持无向图。", code="unsupported_graph_type", path=f"parameters.snapshots[{index}].directed")
        if len(snapshot["nodes"]) > limits["max_nodes"]:
            raise AlgorithmInputError(f"动态社区每个快照最多支持 {limits['max_nodes']} 个节点。", code="limit_exceeded", path=f"parameters.snapshots[{index}].nodes")
        if len(snapshot["edges"]) > limits["max_edges"]:
            raise AlgorithmInputError(f"动态社区每个快照最多支持 {limits['max_edges']} 条边。", code="limit_exceeded", path=f"parameters.snapshots[{index}].edges")
        snapshots.append(snapshot)
    supplied = params.get("snapshot_communities") or []
    if supplied and (not isinstance(supplied, list) or len(supplied) != len(snapshots)):
        raise AlgorithmInputError("snapshot_communities 必须与 snapshots 等长。", path="parameters.snapshot_communities")
    partitions = []
    for index, snapshot in enumerate(snapshots):
        nodes = {node["id"] for node in snapshot["nodes"]}
        partitions.append(_parse_partition(supplied[index], nodes) if supplied else _detect_partition(snapshot, seed))

    events: list[dict[str, Any]] = []
    threshold = params["threshold"]
    for time in range(len(partitions) - 1):
        previous, current = partitions[time], partitions[time + 1]
        scores = {(left, right): _jaccard(previous[left], current[right]) for left in range(len(previous)) for right in range(len(current))}
        successors = {left: [right for right in range(len(current)) if scores[left, right] >= threshold] for left in range(len(previous))}
        predecessors = {right: [left for left in range(len(previous)) if scores[left, right] >= threshold] for right in range(len(current))}
        best_successor = {left: max(successors[left], key=lambda right: (scores[left, right], -right)) for left in range(len(previous)) if successors[left]}
        best_predecessor = {right: max(predecessors[right], key=lambda left: (scores[left, right], -left)) for right in range(len(current)) if predecessors[right]}
        for left, right in best_successor.items():
            if best_predecessor.get(right) == left:
                events.append({"time": time + 1, "event": "continuation", "source": left, "target": right, "similarity": scores[left, right]})
        for left, targets in successors.items():
            if len(targets) > 1:
                events.append({"time": time + 1, "event": "split", "source": left, "target": targets, "similarity": max(scores[left, target] for target in targets)})
            if not targets:
                events.append({"time": time + 1, "event": "death", "source": left, "target": None, "similarity": 0.0})
        for right, sources in predecessors.items():
            if len(sources) > 1:
                events.append({"time": time + 1, "event": "merge", "source": sources, "target": right, "similarity": max(scores[source, right] for source in sources)})
            if not sources:
                events.append({"time": time + 1, "event": "birth", "source": None, "target": right, "similarity": 0.0})
    partition_rows = [
        {"snapshot": time, "community": index, "nodes": sorted(group)}
        for time, partition in enumerate(partitions)
        for index, group in enumerate(partition)
    ]
    return {
        "tables": [table("events", "动态社区事件", events), table("snapshot_communities", "快照社区", partition_rows)],
        "overlays": [overlay("latest_communities", node_styles={node: {"community": index} for index, group in enumerate(partitions[-1]) for node in group})],
        "charts": [chart("community_timeline", "timeline", [{"name": "events", "data": events}])],
        "provenance": {"snapshot_count": len(snapshots), "matching": "jaccard", "threshold": threshold},
    }
