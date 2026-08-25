from __future__ import annotations

import math
import random
from typing import Any, Callable

import networkx as nx

from .errors import AlgorithmInputError
from .graph import build_nx_graph
from .results import chart, overlay, table


def run_robustness(graph: dict[str, Any], params: dict[str, Any], seed: int | None) -> dict[str, Any]:
    network = build_nx_graph(graph)
    n = len(network)
    if n == 0:
        raise AlgorithmInputError("鲁棒性分析至少需要 1 个节点。")
    strategy = params["strategy"]
    rng = random.Random(seed)
    working = network.copy()
    rows: list[dict[str, Any]] = []
    removed: list[str] = []

    def record() -> None:
        largest = max((len(group) for group in nx.connected_components(working)), default=0)
        rows.append({
            "removed_fraction": len(removed) / n,
            "remaining_nodes": len(working),
            "largest_component": largest,
            "S_q": largest / n,
            "removed_node": removed[-1] if removed else None,
        })

    record()
    while working:
        if strategy == "random":
            node = rng.choice(sorted(working.nodes, key=str))
        elif strategy == "degree":
            values = dict(working.degree())
            node = min((candidate for candidate in working if values[candidate] == max(values.values())), key=str)
        elif strategy == "betweenness":
            values = nx.betweenness_centrality(working, normalized=True)
            node = min((candidate for candidate in working if math.isclose(values[candidate], max(values.values()))), key=str)
        else:
            raise AlgorithmInputError(f"不支持的攻击策略：{strategy}。", path="parameters.strategy")
        removed.append(str(node))
        working.remove_node(node)
        record()
    robustness = sum(row["S_q"] for row in rows) / len(rows)
    return {
        "tables": [table("robustness", "攻击鲁棒性", rows)],
        "overlays": [overlay("removal_order", nodes=[{"node": node, "order": index + 1} for index, node in enumerate(removed)])],
        "charts": [chart("robustness_curve", "line", [{"name": "S(q)", "data": [{"x": row["removed_fraction"], "y": row["S_q"]} for row in rows]}])],
        "provenance": {"R": robustness, "strategy": strategy, "removal_order": removed},
    }

def _score_function(key: str) -> Callable[[nx.Graph, Any, Any], float]:
    def common(network: nx.Graph, source: Any, target: Any) -> set[Any]:
        return set(network.neighbors(source)) & set(network.neighbors(target))

    if key == "link_prediction.common_neighbors":
        return lambda network, source, target: float(len(common(network, source, target)))
    if key == "link_prediction.jaccard":
        return lambda network, source, target: (
            len(common(network, source, target)) / len(set(network.neighbors(source)) | set(network.neighbors(target)))
            if set(network.neighbors(source)) | set(network.neighbors(target)) else 0.0
        )
    if key == "link_prediction.adamic_adar":
        return lambda network, source, target: float(sum(1 / math.log(network.degree(node)) for node in common(network, source, target) if network.degree(node) > 1))
    if key == "link_prediction.resource_allocation":
        return lambda network, source, target: float(sum(1 / network.degree(node) for node in common(network, source, target) if network.degree(node)))
    raise KeyError(key)


def _ordered_edge(source: Any, target: Any) -> tuple[str, str]:
    left, right = str(source), str(target)
    return (left, right) if left <= right else (right, left)


def _auc(positive_scores: list[float], negative_scores: list[float]) -> float | None:
    if not positive_scores or not negative_scores:
        return None
    wins = sum(
        1 if positive > negative else 0.5 if math.isclose(positive, negative) else 0
        for positive in positive_scores
        for negative in negative_scores
    )
    return float(wins / (len(positive_scores) * len(negative_scores)))


def run_link_prediction(key: str, graph: dict[str, Any], params: dict[str, Any], seed: int | None) -> dict[str, Any]:
    network = build_nx_graph(graph)
    if len(network) < 3:
        raise AlgorithmInputError("链路预测至少需要 3 个节点。")
    score = _score_function(key)
    candidates = sorted(nx.non_edges(network), key=lambda edge: (str(edge[0]), str(edge[1])))
    rows = [
        {"source": _ordered_edge(source, target)[0], "target": _ordered_edge(source, target)[1], "score": score(network, source, target)}
        for source, target in candidates
    ]
    rows.sort(key=lambda row: (-row["score"], row["source"], row["target"]))

    rng = random.Random(seed)
    all_edges = sorted((_ordered_edge(source, target) for source, target in network.edges()), key=lambda edge: edge)
    shuffled = list(all_edges)
    rng.shuffle(shuffled)
    requested = params["test_fraction"]
    test_count = min(len(all_edges), max(1, round(len(all_edges) * requested))) if requested > 0 and all_edges else 0
    test_edges = sorted(shuffled[:test_count])
    training = network.copy()
    training.remove_edges_from(test_edges)
    training_edges = sorted((_ordered_edge(source, target) for source, target in training.edges()), key=lambda edge: edge)
    positive_scores = [score(training, source, target) for source, target in test_edges]
    negative_candidates = sorted(
        (_ordered_edge(source, target) for source, target in nx.non_edges(network)),
        key=lambda edge: edge,
    )
    rng.shuffle(negative_candidates)
    negatives = sorted(negative_candidates[:max(1, len(test_edges))]) if test_edges else []
    negative_scores = [score(training, source, target) for source, target in negatives]
    auc = _auc(positive_scores, negative_scores)
    warnings = []
    if auc is None:
        warnings.append("原图缺少可用的正负样本，无法计算 AUC。")
    return {
        "tables": [table("predictions", "候选链路得分", rows)],
        "overlays": [overlay("predicted_edges", edges=rows[: min(50, len(rows))])],
        "charts": [chart("prediction_scores", "bar", [{"name": "score", "data": [{"x": f'{row["source"]}-{row["target"]}', "y": row["score"]} for row in rows[:50]]}])],
        "warnings": warnings,
        "provenance": {
            "evaluation": {
                "auc": auc,
                "test_edges_hidden_before_scoring": True,
                "test_edges": [list(edge) for edge in test_edges],
                "training_edges": [list(edge) for edge in training_edges],
                "negative_edges": [list(edge) for edge in negatives],
            }
        },
    }
