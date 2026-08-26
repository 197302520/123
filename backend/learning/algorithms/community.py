from __future__ import annotations

import importlib.util
import math
import random
import time
from collections import Counter, defaultdict
from typing import Any, Callable, Iterable

import networkx as nx

from .errors import AlgorithmInputError
from .graph import build_nx_graph
from .results import chart, overlay, table


def _canonical(communities: Iterable[Iterable[Any]]) -> list[set[Any]]:
    cleaned = [set(community) for community in communities if community]
    cleaned.sort(key=lambda community: tuple(sorted(map(str, community))))
    return cleaned


def _community_criteria_rows(network: nx.Graph, communities: list[set[Any]]) -> list[dict[str, Any]]:
    """Radicchi-style verdicts: strong / weak / density per 说明书 6.1."""
    overall_density = float(nx.density(network)) if len(network) > 1 else 0.0
    n = network.number_of_nodes()
    rows: list[dict[str, Any]] = []
    for index, community in enumerate(communities):
        members = set(community)
        strong = True
        internal_degree_total = 0.0
        external_degree_total = 0.0
        boundary_pairs = 0
        for node in members:
            node_internal = 0.0
            node_external = 0.0
            for neighbor, data in network[node].items():
                weight = float(data.get("weight", 1))
                if neighbor in members:
                    node_internal += weight
                else:
                    node_external += weight
                    boundary_pairs += 1
            strong = strong and node_internal > node_external
            internal_degree_total += node_internal
            external_degree_total += node_external
        internal_pairs = int(internal_degree_total / 2)
        weak = internal_degree_total > external_degree_total
        size = len(members)
        pair_denominator = size * (size - 1) / 2
        cross_denominator = size * (n - size)
        internal_density = round(internal_pairs / pair_denominator, 6) if pair_denominator else 0.0
        cross_density = round(boundary_pairs / cross_denominator, 6) if cross_denominator else None
        density_ok = pair_denominator > 0 and internal_density > overall_density and (cross_density is not None and cross_density < overall_density)
        if strong and weak:
            verdict = "强社区且满足弱社区"
        elif strong:
            verdict = "强社区"
        elif weak:
            verdict = "弱社区"
        else:
            verdict = "不满足判定"
        rows.append({
            "community": index,
            "size": size,
            "internal_degree_sum": round(internal_degree_total, 6),
            "boundary_degree_sum": round(external_degree_total, 6),
            "internal_edge_pairs": internal_pairs,
            "boundary_edge_pairs": boundary_pairs,
            "internal_density": internal_density,
            "cross_density": cross_density,
            "strong_community": strong,
            "weak_community": weak,
            "density_criterion": density_ok,
            "verdict": verdict,
        })
    return rows


def _partition_bundle(network: nx.Graph, communities: Iterable[Iterable[Any]], *, hierarchy: list[Any] | None = None) -> dict[str, Any]:
    canonical = _canonical(communities)
    memberships: dict[Any, list[int]] = defaultdict(list)
    for index, community in enumerate(canonical):
        for node in community:
            memberships[node].append(index)
    for node in network.nodes:
        if not memberships[node]:
            canonical.append({node})
            memberships[node].append(len(canonical) - 1)
    rows = [
        {"node": str(node), "community": memberships[node][0], "memberships": memberships[node]}
        for node in sorted(network.nodes, key=str)
    ]
    palette = ["#0f766e", "#b45309", "#4338ca", "#be123c", "#047857", "#7e22ce"]
    styles = {row["node"]: {"community": row["community"], "color": palette[row["community"] % len(palette)]} for row in rows}
    modularity = None
    disjoint = all(len(value) == 1 for value in memberships.values())
    if network.number_of_edges() and disjoint:
        modularity = float(nx.community.modularity(network, canonical, weight="weight"))
    bundle: dict[str, Any] = {
        "tables": [table("communities", "社区成员", rows)],
        "overlays": [overlay("communities", node_styles=styles)],
        "charts": [chart("community_sizes", "bar", [{"name": "社区规模", "data": [{"x": index, "y": len(group)} for index, group in enumerate(canonical)]}])],
        "provenance": {"community_count": len(canonical), "modularity": modularity, "overlapping": not disjoint},
    }
    if network.number_of_edges():
        criteria_rows = _community_criteria_rows(network, canonical)
        bundle["tables"].append(table("community_criteria", "强社区/弱社区/密度判定", criteria_rows))
        bundle["provenance"]["overall_edge_density"] = float(nx.density(network)) if len(network) > 1 else 0.0
    if hierarchy is not None:
        bundle["tables"].append(table("hierarchy", "层次步骤", hierarchy))
    return bundle


def _agglomerative(network: nx.Graph, target: int, resolution: float) -> tuple[list[set[Any]], list[dict[str, Any]]]:
    communities = [{node} for node in sorted(network.nodes, key=str)]
    history: list[dict[str, Any]] = []
    while len(communities) > max(1, target):
        best: tuple[float, int, int] | None = None
        current_q = nx.community.modularity(network, communities, weight="weight", resolution=resolution) if network.number_of_edges() else 0.0
        for left in range(len(communities)):
            for right in range(left + 1, len(communities)):
                candidate = [set(group) for index, group in enumerate(communities) if index not in {left, right}]
                candidate.append(communities[left] | communities[right])
                score = nx.community.modularity(network, candidate, weight="weight", resolution=resolution) if network.number_of_edges() else -len(candidate)
                option = (score - current_q, -left, -right)
                if best is None or option > best:
                    best = option
        assert best is not None
        left, right = -best[1], -best[2]
        merged = communities[left] | communities[right]
        history.append({"step": len(history) + 1, "left": "|".join(sorted(map(str, communities[left]))), "right": "|".join(sorted(map(str, communities[right]))), "gain": float(best[0])})
        communities = [group for index, group in enumerate(communities) if index not in {left, right}] + [merged]
        communities = _canonical(communities)
    return communities, history


def _divisive(network: nx.Graph, target: int) -> tuple[list[set[Any]], list[dict[str, Any]]]:
    working = network.copy()
    history: list[dict[str, Any]] = []
    while nx.number_connected_components(working) < min(target, len(working)) and working.number_of_edges():
        values = nx.edge_betweenness_centrality(working, weight="weight")
        maximum = max(values.values())
        candidates = [edge for edge, value in values.items() if math.isclose(value, maximum)]
        source, target_node = min(candidates, key=lambda edge: (str(edge[0]), str(edge[1])))
        working.remove_edge(source, target_node)
        history.append({"step": len(history) + 1, "source": str(source), "target": str(target_node), "edge_betweenness": float(maximum)})
    return _canonical(nx.connected_components(working)), history


def _lfm(network: nx.Graph, alpha: float, seed: int | None) -> list[set[Any]]:
    rng = random.Random(seed)
    remaining = set(network.nodes)
    communities: list[set[Any]] = []

    def fitness(group: set[Any]) -> float:
        internal = 0.0
        external = 0.0
        for node in group:
            for neighbor, data in network[node].items():
                if neighbor in group:
                    internal += float(data.get("weight", 1))
                else:
                    external += float(data.get("weight", 1))
        denominator = (internal + external) ** alpha
        return internal / denominator if denominator else 0.0

    while remaining:
        seed_node = rng.choice(sorted(remaining, key=str))
        group = {seed_node}
        while True:
            frontier = sorted({neighbor for node in group for neighbor in network.neighbors(node)} - group, key=str)
            if not frontier:
                break
            base = fitness(group)
            gains = [(fitness(group | {candidate}) - base, str(candidate), candidate) for candidate in frontier]
            gain, _, candidate = max(gains)
            if gain <= 1e-12:
                break
            group.add(candidate)
        communities.append(group)
        remaining -= group
    return _canonical(communities)


def _slpa(network: nx.Graph, iterations: int, threshold: float, seed: int | None) -> list[set[Any]]:
    rng = random.Random(seed)
    memory: dict[Any, Counter[Any]] = {node: Counter({node: 1}) for node in network.nodes}
    listeners = list(sorted(network.nodes, key=str))
    for _ in range(iterations):
        rng.shuffle(listeners)
        for listener in listeners:
            heard: list[Any] = []
            for speaker in sorted(network.neighbors(listener), key=str):
                labels = sorted(memory[speaker], key=str)
                weights = [memory[speaker][label] for label in labels]
                heard.append(rng.choices(labels, weights=weights, k=1)[0])
            if heard:
                counts = Counter(heard)
                maximum = max(counts.values())
                chosen = rng.choice(sorted([label for label, count in counts.items() if count == maximum], key=str))
                memory[listener][chosen] += 1
    labels_to_nodes: dict[Any, set[Any]] = defaultdict(set)
    total = iterations + 1
    for node, labels in memory.items():
        retained = [label for label, count in labels.items() if count / total >= threshold]
        if not retained:
            retained = [labels.most_common(1)[0][0]]
        for label in retained:
            labels_to_nodes[label].add(node)
    groups = list(labels_to_nodes.values())
    maximal = [group for group in groups if not any(group < other for other in groups)]
    return _canonical(maximal)


def _girvan_newman_partition(network: nx.Graph, target: int) -> list[set[Any]]:
    generator = nx.community.girvan_newman(network)
    communities = [{node for node in group} for group in next(generator)]
    while len(communities) < min(target, len(network)):
        communities = [{node for node in group} for group in next(generator)]
    return communities


def _compare_bundle(network: nx.Graph, params: dict[str, Any], seed: int | None) -> dict[str, Any]:
    """One aggregate run: modularity table across algorithms plus a best-partition conclusion."""
    resolution = params["resolution"]
    target = min(params.get("communities", 2), len(network))
    small_network = len(network) <= 60
    agenda: list[tuple[str, str, bool, Callable[[], Iterable[Iterable[Any]]]]] = [
        ("community.fast_newman", "Fast Newman 贪心模块度", False,
         lambda: nx.community.greedy_modularity_communities(network, weight="weight", resolution=resolution)),
        ("community.louvain", "Louvain", False,
         lambda: nx.community.louvain_communities(network, weight="weight", resolution=resolution, seed=seed)),
        ("community.leiden", "Leiden", False, lambda: _leiden(network, resolution, seed)[0]),
        ("community.lpa", "标签传播 LPA", False,
         lambda: nx.community.asyn_lpa_communities(network, weight="weight", seed=seed)),
    ]
    if small_network:
        agenda.extend([
            ("community.kernighan_lin", "Kernighan–Lin 二分", False,
             lambda: nx.community.kernighan_lin_bisection(network, weight="weight", seed=seed)),
            ("community.agglomerative", "凝聚层次社区", False, lambda: _agglomerative(network, target, resolution)[0]),
            ("community.divisive", "分裂层次社区", False, lambda: _divisive(network, target)[0]),
            ("community.girvan_newman", "Girvan–Newman", False, lambda: _girvan_newman_partition(network, target)),
            ("community.cpm", "CPM 派系渗透法（重叠）", True,
             lambda: nx.community.k_clique_communities(network, params.get("clique_size", 3))),
            ("community.lfm", "LFM 局部适应度（重叠）", True, lambda: _lfm(network, params.get("alpha", 1.0), seed)),
            ("community.slpa", "SLPA 标签传播（重叠）", True,
             lambda: _slpa(network, params.get("iterations", 30), params.get("threshold", 0.1), seed)),
        ])
    rows: list[dict[str, Any]] = []
    for key, label, declared_overlapping, producer in agenda:
        started = time.perf_counter()
        status = "ok"
        try:
            grouping = [group for group in producer() if group]
            if not grouping:
                raise AlgorithmInputError("该算法未产生任何社区。")
            membership_counts = Counter(node for group in grouping for node in group)
            disjoint = all(count == 1 for count in membership_counts.values())
            overlapping = not disjoint
            modularity = (
                float(nx.community.modularity(network, grouping, weight="weight", resolution=resolution))
                if disjoint and network.number_of_edges()
                else None
            )
            community_count = len(grouping)
        except Exception as exc:  # noqa: BLE001 - one failing algorithm must not kill the battery.
            status = f"运行失败：{type(exc).__name__}"
            modularity = None
            community_count = None
            overlapping = declared_overlapping
        rows.append({
            "algorithm": label,
            "key": key,
            "modularity": round(modularity, 6) if modularity is not None else None,
            "community_count": community_count,
            "overlapping": overlapping,
            "comparable": modularity is not None,
            "runtime_ms": round((time.perf_counter() - started) * 1000, 1),
            "status": status,
        })
    comparable_rows = sorted(
        (row for row in rows if row["comparable"]),
        key=lambda row: (-row["modularity"], row["key"]),
    )
    non_comparable_rows = [row for row in rows if not row["comparable"]]
    ordered_rows = [
        {**row, "rank": index + 1}
        for index, row in enumerate(comparable_rows)
    ] + [{**row, "rank": None} for row in non_comparable_rows]
    warnings: list[str] = []
    if not small_network:
        warnings.append("节点数超过 60；二分与层次类算法在大网络代价过高，本次仅对比可扩展方法（重叠算法不参与模块度排序）。")
    conclusion = None
    provenance_extra: dict[str, Any] = {}
    if comparable_rows:
        best = comparable_rows[0]
        conclusion = (
            f"在分辨率 γ={resolution} 下，{best['algorithm']} 以最高模块度 Q={best['modularity']:.6f} 领先；"
            "建议以该划分为基准，结合可视化与业务含义复核最优算法筛选结论。"
        )
        provenance_extra = {"best_algorithm": best["algorithm"], "best_algorithm_key": best["key"], "best_modularity": best["modularity"]}
    else:
        warnings.append("本次没有任何可比较的非重叠划分，无法给出最优算法筛选结论。")
    return {
        "tables": [table("modularity_comparison", "多算法模块度对比表", ordered_rows)],
        "charts": [chart(
            "modularity_comparison",
            "bar",
            [{"name": "模块度 Q", "data": [{"x": row["algorithm"], "y": row["modularity"]} for row in comparable_rows]}],
        )],
        "warnings": warnings,
        "provenance": {
            **provenance_extra,
            "conclusion": conclusion,
            "compared_algorithms": len(rows),
            "resolution": resolution,
        },
    }


def _leiden(network: nx.Graph, resolution: float, seed: int | None) -> tuple[list[set[Any]], dict[str, Any], list[str]]:
    if importlib.util.find_spec("igraph") and importlib.util.find_spec("leidenalg"):
        import igraph as ig
        import leidenalg

        nodes = list(sorted(network.nodes, key=str))
        index = {node: offset for offset, node in enumerate(nodes)}
        graph = ig.Graph(n=len(nodes), edges=[(index[source], index[target]) for source, target in network.edges()], directed=False)
        graph.es["weight"] = [float(network[source][target].get("weight", 1)) for source, target in network.edges()]
        partition = leidenalg.find_partition(
            graph,
            leidenalg.RBConfigurationVertexPartition,
            weights="weight",
            resolution_parameter=resolution,
            seed=0 if seed is None else seed,
        )
        return [{nodes[offset] for offset in community} for community in partition], {"implementation": "leidenalg", "fallback": None}, []
    communities = nx.community.louvain_communities(network, weight="weight", resolution=resolution, seed=seed)
    warning = "Leiden 可选依赖 igraph/leidenalg 未安装；本次明示回退到 Louvain。"
    return communities, {"implementation": "networkx.louvain_communities", "fallback": "louvain", "missing_dependencies": ["igraph", "leidenalg"]}, [warning]


def run_community(key: str, graph: dict[str, Any], params: dict[str, Any], seed: int | None) -> dict[str, Any]:
    network = build_nx_graph(graph)
    if len(network) < 2:
        raise AlgorithmInputError("社区发现至少需要 2 个节点。", path="graph.nodes")
    if network.number_of_edges() == 0:
        if key == "community.compare":
            raise AlgorithmInputError("无边图不含可比较的社区划分证据。", path="graph.edges")
        bundle = _partition_bundle(network, [{node} for node in sorted(network.nodes, key=str)])
        bundle["warnings"] = ["无边图不含社区连接证据；每个节点作为独立社区返回。"]
        return bundle
    target = min(params.get("communities", 2), len(network))
    resolution = params.get("resolution", 1.0)
    warnings: list[str] = []
    extra_provenance: dict[str, Any] = {}
    hierarchy = None
    if key == "community.compare":
        return _compare_bundle(network, params, seed)
    if key == "community.kernighan_lin":
        left, right = nx.community.kernighan_lin_bisection(network, weight="weight", seed=seed)
        communities = [left, right]
    elif key == "community.agglomerative":
        communities, hierarchy = _agglomerative(network, target, resolution)
    elif key == "community.divisive":
        communities, hierarchy = _divisive(network, target)
    elif key == "community.girvan_newman":
        generator = nx.community.girvan_newman(network)
        communities = next(generator)
        while len(communities) < target:
            communities = next(generator)
    elif key == "community.fast_newman":
        communities = nx.community.greedy_modularity_communities(network, weight="weight", resolution=resolution)
    elif key == "community.louvain":
        communities = nx.community.louvain_communities(network, weight="weight", resolution=resolution, seed=seed)
    elif key == "community.leiden":
        communities, extra_provenance, warnings = _leiden(network, resolution, seed)
    elif key == "community.lpa":
        communities = list(nx.community.asyn_lpa_communities(network, weight="weight", seed=seed))
    elif key == "community.cpm":
        communities = list(nx.community.k_clique_communities(network, params["clique_size"]))
    elif key == "community.lfm":
        communities = _lfm(network, params["alpha"], seed)
    elif key == "community.slpa":
        communities = _slpa(network, params["iterations"], params["threshold"], seed)
    else:
        raise KeyError(key)
    bundle = _partition_bundle(network, communities, hierarchy=hierarchy)
    bundle["warnings"] = warnings
    bundle["provenance"].update(extra_provenance)
    return bundle
