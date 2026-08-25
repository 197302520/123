from __future__ import annotations

import importlib.util
import math
import random
from collections import Counter, defaultdict
from typing import Any, Iterable

import networkx as nx

from .errors import AlgorithmInputError
from .graph import build_nx_graph
from .results import chart, overlay, table


def _canonical(communities: Iterable[Iterable[Any]]) -> list[set[Any]]:
    cleaned = [set(community) for community in communities if community]
    cleaned.sort(key=lambda community: tuple(sorted(map(str, community))))
    return cleaned


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
        bundle = _partition_bundle(network, [{node} for node in sorted(network.nodes, key=str)])
        bundle["warnings"] = ["无边图不含社区连接证据；每个节点作为独立社区返回。"]
        return bundle
    target = min(params.get("communities", 2), len(network))
    resolution = params.get("resolution", 1.0)
    warnings: list[str] = []
    extra_provenance: dict[str, Any] = {}
    hierarchy = None
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
