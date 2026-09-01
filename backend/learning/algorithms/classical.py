from __future__ import annotations

import math
from collections import Counter
from typing import Any

import networkx as nx
import numpy as np

from .errors import AlgorithmInputError
from .graph import build_nx_graph, nx_to_graph
from .results import chart, overlay, table


def _component_count(network: nx.Graph | nx.DiGraph) -> int:
    if len(network) == 0:
        return 0
    return nx.number_weakly_connected_components(network) if network.is_directed() else nx.number_connected_components(network)


def _connected(network: nx.Graph | nx.DiGraph) -> bool:
    if len(network) == 0:
        return False
    return nx.is_weakly_connected(network) if network.is_directed() else nx.is_connected(network)


def _summary(network: nx.Graph | nx.DiGraph) -> dict[str, Any]:
    n = len(network)
    component_count = _component_count(network)
    undirected = network.to_undirected()
    largest = max(nx.connected_components(undirected), key=len) if n else set()
    subgraph = undirected.subgraph(largest)
    return {
        "node_count": n,
        "edge_count": network.number_of_edges(),
        "density": float(nx.density(network)) if n > 1 else 0.0,
        "components": component_count,
        "average_degree": float(sum(dict(network.degree()).values()) / n) if n else 0.0,
        "average_clustering": float(nx.average_clustering(undirected, weight=None)) if n else 0.0,
        "diameter": int(nx.diameter(subgraph)) if len(subgraph) > 1 else 0,
        "average_path_length": float(nx.average_shortest_path_length(subgraph)) if len(subgraph) > 1 else 0.0,
    }


def _degree_chart(network: nx.Graph | nx.DiGraph) -> dict[str, Any]:
    counts = Counter(dict(network.degree()).values())
    return chart(
        "degree_distribution",
        "bar",
        [{"name": "节点数", "data": [{"x": degree, "y": counts[degree]} for degree in sorted(counts)]}],
        x_label="度",
        y_label="节点数",
    )


def _floyd_bundle(network: nx.Graph | nx.DiGraph, path_pair_limit: int) -> dict[str, Any]:
    """Dense Floyd iteration with a next-hop matrix so every distance carries its node sequence."""
    nodes = list(sorted(network.nodes, key=str))
    index = {node: offset for offset, node in enumerate(nodes)}
    order = len(nodes)
    distances = np.full((order, order), np.inf)
    np.fill_diagonal(distances, 0.0)
    successors = np.full((order, order), -1, dtype=np.int64)
    for left, right, data in network.edges(data=True):
        first, second = index[left], index[right]
        weight = float(data.get("weight", 1))
        if weight < distances[first, second]:
            distances[first, second] = weight
            successors[first, second] = second
        if not network.is_directed() and weight < distances[second, first]:
            distances[second, first] = weight
            successors[second, first] = first
    for middle in range(order):
        candidate = distances[:, middle, None] + distances[None, middle, :]
        improved = candidate < distances
        row, column = np.nonzero(improved)
        distances[row, column] = candidate[row, column]
        successors[row, column] = successors[row, middle]

    def node_sequence(first: int, second: int) -> list[str] | None:
        sequence = [first]
        cursor = first
        while cursor != second:
            following = int(successors[cursor, second])
            if following < 0:
                return None
            cursor = following
            sequence.append(cursor)
            if len(sequence) > order:
                return None
        return [nodes[offset] for offset in sequence]

    distance_rows: list[dict[str, Any]] = []
    path_rows: list[dict[str, Any]] = []
    reachable_pairs = 0
    distance_total = 0.0
    unreachable = False
    truncated = False
    for first_offset, first_node in enumerate(nodes):
        for second_offset, second_node in enumerate(nodes):
            value = float(distances[first_offset, second_offset])
            if math.isinf(value):
                unreachable = True
                distance_rows.append({"source": first_node, "target": second_node, "distance": None})
                continue
            distance_rows.append({"source": first_node, "target": second_node, "distance": value})
            if first_offset != second_offset:
                reachable_pairs += 1
                distance_total += value
            if len(path_rows) >= path_pair_limit:
                truncated = True
                continue
            sequence = node_sequence(first_offset, second_offset)
            path_rows.append({
                "source": first_node,
                "target": second_node,
                "path": " -> ".join(map(str, sequence)) if sequence else None,
                "distance": value,
            })
    average_length = round(distance_total / reachable_pairs, 6) if reachable_pairs else None
    warnings = ["图中存在不可达节点对，以 null 表示无穷距离。"] if unreachable else []
    if truncated:
        warnings.append(f"完整路径节点序列仅输出前 {path_pair_limit} 个点对，可用 path_pair_limit 提高上限。")
    summary_row = {
        "average_shortest_path_length": average_length,
        "reachable_pairs": reachable_pairs,
        "unreachable_pairs": sum(1 for row in distance_rows if row["distance"] is None),
    }
    return {
        "tables": [
            table("distances", "Floyd 距离矩阵", distance_rows),
            table("paths", "最短路径节点序列", path_rows),
            table("path_summary", "平均最短路径", [summary_row]),
        ],
        "charts": [chart("distance_heatmap", "heatmap", [{"name": "distance", "data": distance_rows}])],
        "warnings": warnings,
        "provenance": {
            "average_shortest_path_length": average_length,
            "iteration": "d_ij=min(d_ij,d_ik+d_kj)",
            "path_sequence_limit": path_pair_limit,
            "path_sequence_truncated": truncated,
        },
    }


def _node_measure_bundle(network: nx.Graph | nx.DiGraph, values: dict[Any, float], name: str) -> dict[str, Any]:
    rows = [{"node": str(node), "value": float(values[node])} for node in sorted(values, key=str)]
    return {
        "tables": [table("nodes", name, rows)],
        "overlays": [overlay("node_values", nodes=rows)],
        "charts": [chart("ranking", "bar", [{"name": name, "data": [{"x": row["node"], "y": row["value"]} for row in sorted(rows, key=lambda row: (-row["value"], row["node"]))]}], title=f"{name}排名（全部节点，从高到低）")],
    }


def _pagerank(network: nx.Graph | nx.DiGraph, alpha: float, max_iterations: int, tolerance: float) -> tuple[dict[Any, float], int]:
    nodes = list(sorted(network.nodes, key=str))
    n = len(nodes)
    if n == 0:
        return {}, 0
    scores = {node: 1 / n for node in nodes}
    out_weight = {node: sum(float(data.get("weight", 1)) for _, _, data in network.out_edges(node, data=True)) if network.is_directed() else sum(float(data.get("weight", 1)) for _, _, data in network.edges(node, data=True)) for node in nodes}
    for iteration in range(1, max_iterations + 1):
        dangling = sum(scores[node] for node in nodes if out_weight[node] == 0)
        updated = {node: (1 - alpha) / n + alpha * dangling / n for node in nodes}
        for source in nodes:
            if out_weight[source] == 0:
                continue
            edges = network.out_edges(source, data=True) if network.is_directed() else network.edges(source, data=True)
            for edge in edges:
                if network.is_directed():
                    _, target, data = edge
                else:
                    left, right, data = edge
                    target = right if left == source else left
                updated[target] += alpha * scores[source] * float(data.get("weight", 1)) / out_weight[source]
        delta = sum(abs(updated[node] - scores[node]) for node in nodes)
        scores = updated
        if delta <= tolerance:
            return scores, iteration
    raise AlgorithmInputError(f"PageRank 在 {max_iterations} 次迭代内未收敛。", code="non_convergence")


def _hits(network: nx.Graph | nx.DiGraph, max_iterations: int, tolerance: float) -> tuple[dict[Any, float], dict[Any, float], int]:
    nodes = list(sorted(network.nodes, key=str))
    if not nodes:
        return {}, {}, 0
    authorities = {node: 1 / math.sqrt(len(nodes)) for node in nodes}
    hubs = dict(authorities)
    directed = network if network.is_directed() else network.to_directed()
    for iteration in range(1, max_iterations + 1):
        new_authorities = {node: sum(hubs[source] * float(data.get("weight", 1)) for source, _, data in directed.in_edges(node, data=True)) for node in nodes}
        norm = math.sqrt(sum(value * value for value in new_authorities.values())) or 1
        new_authorities = {node: value / norm for node, value in new_authorities.items()}
        new_hubs = {node: sum(new_authorities[target] * float(data.get("weight", 1)) for _, target, data in directed.out_edges(node, data=True)) for node in nodes}
        norm = math.sqrt(sum(value * value for value in new_hubs.values())) or 1
        new_hubs = {node: value / norm for node, value in new_hubs.items()}
        delta = max(abs(new_authorities[node] - authorities[node]) + abs(new_hubs[node] - hubs[node]) for node in nodes)
        authorities, hubs = new_authorities, new_hubs
        if delta <= tolerance:
            return hubs, authorities, iteration
    raise AlgorithmInputError(f"HITS 在 {max_iterations} 次迭代内未收敛。", code="non_convergence")


def _random_model(key: str, params: dict[str, Any], seed: int | None) -> dict[str, Any]:
    n = params["n"]
    if key == "model.er":
        network = nx.gnp_random_graph(n, params["p"], seed=seed)
    elif key == "model.ws":
        k = params["k"]
        if k >= n or k % 2:
            raise AlgorithmInputError("WS 参数 k 必须是小于 n 的偶数。", path="parameters.k")
        network = nx.watts_strogatz_graph(n, k, params["p"], seed=seed)
    else:
        m = params["m"]
        if m >= n:
            raise AlgorithmInputError("BA 参数 m 必须小于 n。", path="parameters.m")
        network = nx.barabasi_albert_graph(n, m, seed=seed)
    generated = nx_to_graph(network)
    return {
        "tables": [table("evidence", "结构证据", [_summary(network)])],
        "overlays": [overlay("generated_graph", nodes=generated["nodes"], edges=generated["edges"])],
        "charts": [_degree_chart(network)],
        "provenance": {"generated_graph": generated, "generator": key.removeprefix("model.").upper()},
    }


def run_classical(key: str, graph: dict[str, Any], params: dict[str, Any], seed: int | None) -> dict[str, Any]:
    if key.startswith("model."):
        return _random_model(key, params, seed)
    network = build_nx_graph(graph)
    if key != "graph.validate" and len(network) == 0:
        raise AlgorithmInputError("该算法至少需要一个节点。", path="graph.nodes")
    if key == "graph.validate":
        return {}
    if key == "topology.summary":
        summary = _summary(network)
        warnings = [] if _connected(network) else ["图非连通；直径与平均路径仅基于最大弱连通分量。"]
        return {"tables": [table("summary", "拓扑摘要", [summary])], "charts": [_degree_chart(network)], "warnings": warnings}
    if key == "paths.floyd":
        return _floyd_bundle(network, params["path_pair_limit"])
    if key == "clustering.coefficient":
        values = nx.clustering(network, weight=None)
        rows = [{"node": str(node), "coefficient": float(values[node])} for node in sorted(values, key=str)]
        bundle = {
            "tables": [table("nodes", "聚类系数", rows)],
            "overlays": [overlay("node_values", nodes=[{"node": row["node"], "value": row["coefficient"]} for row in rows])],
            "charts": [chart("ranking", "bar", [{"name": "聚类系数", "data": [{"x": row["node"], "y": row["coefficient"]} for row in rows]}])],
        }
        bundle["provenance"] = {"average": float(sum(values.values()) / len(values)) if values else 0.0}
        return bundle
    if key == "centrality.degree":
        return _node_measure_bundle(network, nx.degree_centrality(network), "度中心性")
    if key == "centrality.closeness":
        return _node_measure_bundle(network, nx.closeness_centrality(network, distance="weight"), "接近中心性")
    if key == "centrality.betweenness":
        return _node_measure_bundle(network, nx.betweenness_centrality(network, normalized=True, weight="weight"), "中介中心性")
    if key == "centrality.eigenvector":
        values = nx.eigenvector_centrality(network, max_iter=params["max_iterations"], tol=params["tolerance"], weight="weight")
        bundle = _node_measure_bundle(network, values, "特征向量中心性")
        if not _connected(network):
            bundle["warnings"] = ["图为非连通图，特征向量分数可集中于主谱半径分量。"]
        return bundle
    if key == "centrality.pagerank":
        values, iterations = _pagerank(network, params["alpha"], params["max_iterations"], params["tolerance"])
        bundle = _node_measure_bundle(network, values, "PageRank")
        bundle["provenance"] = {"iterations": iterations, "converged": True}
        return bundle
    if key == "centrality.hits":
        hubs, authorities, iterations = _hits(network, params["max_iterations"], params["tolerance"])
        rows = [{"node": str(node), "hub": float(hubs[node]), "authority": float(authorities[node])} for node in sorted(network.nodes, key=str)]
        authority_top = sorted(rows, key=lambda row: (-row["authority"], row["node"]))[:10]
        hub_top = sorted(rows, key=lambda row: (-row["hub"], row["node"]))[:10]
        return {
            "tables": [table("nodes", "HITS 枢纽-权威", rows)],
            "overlays": [overlay("hits", nodes=rows)],
            "charts": [
                chart("authority_top", "bar", [{"name": "权威分 authority", "data": [{"x": row["node"], "y": row["authority"]} for row in authority_top]}],
                      title="权威分 TOP10：被指向最多的节点"),
                chart("hub_top", "bar", [{"name": "枢纽分 hub", "data": [{"x": row["node"], "y": row["hub"]} for row in hub_top]}],
                      title="枢纽分 TOP10：指向别人最多的节点"),
                chart("hits_scatter", "scatter", [{"name": "HITS", "data": [{"x": row["hub"], "y": row["authority"], "label": row["node"]} for row in rows]}],
                      x_axis="枢纽分 hub", y_axis="权威分 authority", title="枢纽-权威散点"),
            ],
            "provenance": {"iterations": iterations, "converged": True},
        }
    if key == "centralization.degree":
        n = len(network)
        degrees = dict(network.degree())
        maximum = max(degrees.values(), default=0)
        numerator = sum(maximum - value for value in degrees.values())
        denominator = (n - 1) * (n - 2) if not network.is_directed() else (n - 1) ** 2
        value = float(numerator / denominator) if denominator > 0 else 0.0
        return {
            "tables": [table("centralization", "度中心势", [{"centralization": value, "numerator": numerator, "denominator": denominator}])],
            "charts": [chart("centralization", "gauge", [{"name": "度中心势", "data": [{"value": value}]}])],
        }
    raise KeyError(key)
