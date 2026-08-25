import csv
import io
import json
import math

import pytest

from learning.algorithms import AlgorithmInputError, execute_algorithm, get_registry
from learning.algorithms.exports import export_graph
from learning.algorithms.text import extract_chinese_graph, preprocess_chinese


def graph(nodes, edges, *, directed=False):
    return {
        "directed": directed,
        "nodes": [{"id": node, "label": node} for node in nodes],
        "edges": [
            {"source": source, "target": target, "weight": float(weight)}
            for source, target, weight in edges
        ],
    }


PATH3 = graph(["a", "b", "c"], [("a", "b", 1), ("b", "c", 1)])
TRIANGLE = graph(
    ["a", "b", "c"],
    [("a", "b", 1), ("b", "c", 1), ("c", "a", 1)],
)
TWO_TRIANGLES = graph(
    ["a", "b", "c", "d", "e", "f"],
    [
        ("a", "b", 1), ("b", "c", 1), ("c", "a", 1),
        ("d", "e", 1), ("e", "f", 1), ("f", "d", 1),
        ("c", "d", 0.2),
    ],
)


def table_rows(result, key="nodes"):
    return next(table["rows"] for table in result["tables"] if table["key"] == key)


def assert_uniform_result(result, algorithm):
    assert set(result) >= {"tables", "overlays", "charts", "warnings", "provenance", "validation"}
    assert result["provenance"]["algorithm"] == algorithm
    assert result["provenance"]["version"]
    assert result["validation"]["valid"] is True
    assert isinstance(result["tables"], list)
    assert isinstance(result["overlays"], list)
    assert isinstance(result["charts"], list)


def test_registry_is_complete_and_teaching_metadata_is_not_partial():
    required = {
        "graph.validate", "topology.summary", "paths.floyd", "clustering.coefficient",
        "model.er", "model.ws", "model.ba",
        "centrality.degree", "centrality.closeness", "centrality.betweenness",
        "centrality.eigenvector", "centrality.pagerank", "centrality.hits",
        "centralization.degree", "community.kernighan_lin", "community.agglomerative",
        "community.divisive", "community.girvan_newman", "community.fast_newman",
        "community.louvain", "community.leiden", "community.lpa", "community.cpm",
        "community.lfm", "community.slpa", "robustness.attack",
        "link_prediction.common_neighbors", "link_prediction.jaccard",
        "link_prediction.adamic_adar", "link_prediction.resource_allocation",
        "opinion.degroot", "opinion.friedkin_johnsen", "opinion.deffuant", "opinion.hk",
        "community.dynamic", "embedding.ae", "embedding.cnn", "embedding.gcn",
        "embedding.gat", "text.extract", "export.graph",
    }
    registry = get_registry()
    by_key = {spec["key"]: spec for spec in registry}

    assert set(by_key) == required
    for spec in registry:
        assert spec["supported_graph_types"]
        assert isinstance(spec["parameters"], dict)
        assert spec["limits"]["max_nodes"] > 0
        assert spec["formula"].strip()
        assert spec["explanation"].strip()
        assert spec["advantages"]
        assert spec["limitations"]


@pytest.mark.parametrize("algorithm", [
    "graph.validate", "topology.summary", "paths.floyd", "clustering.coefficient",
    "centrality.degree", "centrality.closeness", "centrality.betweenness",
    "centrality.eigenvector", "centrality.pagerank", "centrality.hits",
    "centralization.degree", "community.kernighan_lin", "community.agglomerative",
    "community.divisive", "community.girvan_newman", "community.fast_newman",
    "community.louvain", "community.leiden", "community.lpa", "community.cpm",
    "community.lfm", "community.slpa", "robustness.attack",
    "link_prediction.common_neighbors", "link_prediction.jaccard",
    "link_prediction.adamic_adar", "link_prediction.resource_allocation",
    "opinion.degroot", "opinion.friedkin_johnsen", "opinion.deffuant", "opinion.hk",
    "community.dynamic", "embedding.ae", "embedding.cnn", "text.extract", "export.graph",
])
def test_every_bundled_algorithm_id_returns_a_real_uniform_result(algorithm):
    parameters = {
        "opinion.degroot": {"opinions": {"a": 0, "b": 0.5, "c": 1}},
        "opinion.friedkin_johnsen": {"opinions": {"a": 0, "b": 0.5, "c": 1}},
        "opinion.deffuant": {"opinions": {"a": 0, "b": 0.5, "c": 1}, "steps": 20},
        "opinion.hk": {"opinions": {"a": 0, "b": 0.5, "c": 1}},
        "community.dynamic": {"snapshots": [TWO_TRIANGLES, TWO_TRIANGLES]},
        "embedding.ae": {"clusters": 2, "epochs": 8},
        "embedding.cnn": {"clusters": 2, "epochs": 8},
        "text.extract": {"text": "华为与比亚迪签署合作协议。"},
        "export.graph": {"format": "json"},
    }.get(algorithm, {})
    result = execute_algorithm(algorithm, TWO_TRIANGLES if algorithm.startswith(("community", "embedding")) else PATH3, parameters, seed=11)

    assert_uniform_result(result, algorithm)
    if algorithm != "graph.validate":
        assert result["tables"] or result["charts"] or result["overlays"]


@pytest.mark.parametrize("algorithm", ["model.er", "model.ws", "model.ba"])
def test_random_graph_models_return_reproducible_structural_evidence(algorithm):
    params = {
        "model.er": {"n": 12, "p": 0.3},
        "model.ws": {"n": 12, "p": 0.3, "k": 4},
        "model.ba": {"n": 12, "m": 2},
    }[algorithm]
    first = execute_algorithm(algorithm, graph([], []), params, seed=23)
    second = execute_algorithm(algorithm, graph([], []), params, seed=23)

    assert first == second
    evidence = next(table for table in first["tables"] if table["key"] == "evidence")["rows"][0]
    assert evidence["node_count"] == 12
    assert evidence["edge_count"] >= 0
    assert 0 <= evidence["density"] <= 1
    assert first["overlays"][0]["nodes"]


def test_topology_floyd_and_clustering_match_a_hand_checkable_path_and_triangle():
    topology = execute_algorithm("topology.summary", PATH3, {}, seed=1)
    floyd = execute_algorithm("paths.floyd", PATH3, {}, seed=1)
    clustering = execute_algorithm("clustering.coefficient", TRIANGLE, {}, seed=1)

    summary = topology["tables"][0]["rows"][0]
    assert summary["node_count"] == 3
    assert summary["edge_count"] == 2
    assert summary["density"] == pytest.approx(2 / 3)
    assert summary["components"] == 1
    distances = {(row["source"], row["target"]): row["distance"] for row in table_rows(floyd, "distances")}
    assert distances[("a", "c")] == 2
    assert all(row["coefficient"] == pytest.approx(1) for row in table_rows(clustering))


def test_floyd_represents_disconnected_distance_without_invalid_json_infinity():
    disconnected = graph(["a", "b", "c"], [("a", "b", 1)])
    result = execute_algorithm("paths.floyd", disconnected, {}, seed=1)
    row = next(row for row in table_rows(result, "distances") if row["source"] == "a" and row["target"] == "c")

    assert row["distance"] is None
    assert any("不可达" in warning for warning in result["warnings"])


def test_centralities_match_path3_and_disconnected_eigenvector_is_explicit():
    degree = execute_algorithm("centrality.degree", PATH3, {}, seed=2)
    closeness = execute_algorithm("centrality.closeness", PATH3, {}, seed=2)
    betweenness = execute_algorithm("centrality.betweenness", PATH3, {}, seed=2)
    deg = {row["node"]: row["value"] for row in table_rows(degree)}
    close = {row["node"]: row["value"] for row in table_rows(closeness)}
    between = {row["node"]: row["value"] for row in table_rows(betweenness)}

    assert deg == pytest.approx({"a": 0.5, "b": 1.0, "c": 0.5})
    assert close == pytest.approx({"a": 2 / 3, "b": 1.0, "c": 2 / 3})
    assert between == pytest.approx({"a": 0, "b": 1, "c": 0})
    disconnected = graph(["a", "b", "c"], [("a", "b", 1)])
    eigen = execute_algorithm("centrality.eigenvector", disconnected, {}, seed=2)
    assert len(table_rows(eigen)) == 3
    assert any("非连通" in warning for warning in eigen["warnings"])


def test_iterative_library_failure_is_translated_to_a_stable_engine_error():
    with pytest.raises(AlgorithmInputError) as exc:
        execute_algorithm(
            "centrality.eigenvector", TWO_TRIANGLES,
            {"max_iterations": 1, "tolerance": 1e-12}, seed=2,
        )

    assert exc.value.code == "algorithm_failure"
    assert "未收敛" in str(exc.value)


@pytest.mark.parametrize("algorithm", [
    "community.kernighan_lin", "community.agglomerative", "community.divisive",
    "community.girvan_newman", "community.fast_newman", "community.louvain",
    "community.leiden", "community.lpa", "community.cpm", "community.lfm", "community.slpa",
])
def test_community_methods_find_two_dense_groups_reproducibly(algorithm):
    first = execute_algorithm(algorithm, TWO_TRIANGLES, {}, seed=7)
    second = execute_algorithm(algorithm, TWO_TRIANGLES, {}, seed=7)

    assert first == second
    rows = table_rows(first, "communities")
    assert {row["node"] for row in rows} == {"a", "b", "c", "d", "e", "f"}
    assert len({row["community"] for row in rows}) >= 2
    assert first["overlays"][0]["node_styles"]


def test_cpm_clique_percolation_preserves_overlapping_bridge_membership():
    bow_tie = graph(
        ["a", "b", "c", "d", "e"],
        [("a", "b", 1), ("b", "c", 1), ("c", "a", 1), ("c", "d", 1), ("d", "e", 1), ("e", "c", 1)],
    )
    result = execute_algorithm("community.cpm", bow_tie, {"clique_size": 3}, seed=1)
    bridge = next(row for row in table_rows(result, "communities") if row["node"] == "c")

    assert len(bridge["memberships"]) == 2
    assert result["provenance"]["overlapping"] is True


def test_leiden_dependency_fallback_is_visible_and_never_silent():
    result = execute_algorithm("community.leiden", TWO_TRIANGLES, {}, seed=7)

    if result["provenance"].get("implementation") == "leidenalg":
        assert result["provenance"]["fallback"] is None
    else:
        assert result["provenance"]["fallback"] == "louvain"
        assert any("Louvain" in warning for warning in result["warnings"])


def test_community_detection_handles_disconnected_edgeless_graph_explicitly():
    result = execute_algorithm("community.girvan_newman", graph(["a", "b", "c"], []), {}, seed=1)

    assert len({row["community"] for row in table_rows(result, "communities")}) == 3
    assert any("无边图" in warning for warning in result["warnings"])


def test_undirected_only_algorithm_rejects_directed_input_and_limits_are_enforced():
    directed = graph(["a", "b"], [("a", "b", 1)], directed=True)
    with pytest.raises(AlgorithmInputError, match="无向图"):
        execute_algorithm("community.kernighan_lin", directed, {}, seed=1)
    too_many = graph([str(i) for i in range(501)], [])
    with pytest.raises(AlgorithmInputError, match="500"):
        execute_algorithm("paths.floyd", too_many, {}, seed=1)


def test_graph_engine_rejects_malformed_graph_and_non_finite_weights():
    with pytest.raises(AlgorithmInputError, match="不存在"):
        execute_algorithm("topology.summary", {
            "directed": False, "nodes": [{"id": "a"}],
            "edges": [{"source": "a", "target": "missing", "weight": 1}],
        }, {}, seed=1)
    with pytest.raises(AlgorithmInputError, match="有限"):
        execute_algorithm("topology.summary", graph(["a"], [("a", "a", math.inf)]), {}, seed=1)
    with pytest.raises(AlgorithmInputError, match="parameters"):
        execute_algorithm("graph.validate", graph(["a"], []), [], seed=1)


def test_robustness_random_and_targeted_attacks_return_sq_and_normalized_r():
    random_result = execute_algorithm("robustness.attack", PATH3, {"strategy": "random"}, seed=9)
    targeted = execute_algorithm("robustness.attack", PATH3, {"strategy": "degree"}, seed=9)

    random_rows = table_rows(random_result, "robustness")
    assert [row["removed_fraction"] for row in random_rows] == pytest.approx([0, 1 / 3, 2 / 3, 1])
    assert random_rows[0]["S_q"] == 1
    assert random_rows[-1]["S_q"] == 0
    assert 0 <= random_result["provenance"]["R"] <= 1
    assert random_result != targeted


@pytest.mark.parametrize("algorithm, expected", [
    ("link_prediction.common_neighbors", 1),
    ("link_prediction.jaccard", 1),
    ("link_prediction.adamic_adar", 1 / math.log(2)),
    ("link_prediction.resource_allocation", 0.5),
])
def test_link_prediction_scores_path_endpoints_and_auc_hides_test_edges(algorithm, expected):
    result = execute_algorithm(algorithm, PATH3, {"test_fraction": 0.5}, seed=5)
    scores = table_rows(result, "predictions")
    endpoint = next(row for row in scores if {row["source"], row["target"]} == {"a", "c"})

    assert endpoint["score"] == pytest.approx(expected)
    audit = result["provenance"]["evaluation"]
    assert 0 <= audit["auc"] <= 1
    assert audit["test_edges_hidden_before_scoring"] is True
    assert not set(map(tuple, audit["test_edges"])) & set(map(tuple, audit["training_edges"]))


@pytest.mark.parametrize("algorithm, params", [
    ("opinion.degroot", {"opinions": {"a": 0, "b": 0.5, "c": 1}, "tolerance": 1e-8}),
    ("opinion.friedkin_johnsen", {"opinions": {"a": 0, "b": 0.5, "c": 1}, "stubbornness": 0}),
    ("opinion.deffuant", {"opinions": {"a": 0, "b": 0.5, "c": 1}, "confidence": 1, "steps": 500}),
    ("opinion.hk", {"opinions": {"a": 0, "b": 0.5, "c": 1}, "confidence": 1}),
])
def test_opinion_models_converge_reproducibly_on_connected_path(algorithm, params):
    first = execute_algorithm(algorithm, PATH3, params, seed=17)
    second = execute_algorithm(algorithm, PATH3, params, seed=17)
    values = [row["opinion"] for row in table_rows(first, "opinions")]

    assert first == second
    assert max(values) - min(values) < 1e-3
    assert first["provenance"]["converged"] is True
    assert len(first["charts"][0]["series"]) >= 2


def test_dynamic_community_matching_emits_birth_death_split_merge_and_continuation():
    first = graph(["a", "b", "c", "d"], [("a", "b", 1), ("c", "d", 1)])
    second = graph(["a", "b", "c", "d", "e", "f", "g"], [("a", "b", 1), ("b", "c", 1), ("c", "d", 1), ("d", "e", 1), ("f", "g", 1)])
    third = graph(["a", "b", "c", "f", "g"], [("a", "b", 1), ("b", "c", 1), ("c", "a", 1), ("f", "g", 1)])
    result = execute_algorithm(
        "community.dynamic", first,
        {"snapshots": [first, second, third], "snapshot_communities": [["a|b", "c|d"], ["a|b|c", "d|e", "f|g"], ["a|b|c", "f|g"]], "threshold": 0.2},
        seed=3,
    )

    events = {row["event"] for row in table_rows(result, "events")}
    assert {"continuation", "birth", "death"} <= events
    assert {"split", "merge"} & events
    assert result["charts"][0]["type"] == "timeline"


@pytest.mark.parametrize("algorithm", ["embedding.ae", "embedding.cnn"])
def test_cpu_embedding_clustering_trains_and_returns_nonconstant_embeddings(algorithm):
    result = execute_algorithm(algorithm, TWO_TRIANGLES, {"clusters": 2, "epochs": 20, "embedding_dim": 2}, seed=19)
    repeated = execute_algorithm(algorithm, TWO_TRIANGLES, {"clusters": 2, "epochs": 20, "embedding_dim": 2}, seed=19)
    rows = table_rows(result, "embeddings")

    assert result == repeated
    assert result["provenance"]["device"] == "cpu"
    assert result["provenance"]["trained"] is True
    assert len(rows) == 6
    assert len({tuple(row["embedding"]) for row in rows}) > 1
    assert len({row["cluster"] for row in rows}) == 2
    assert result["charts"][0]["series"]
    losses = table_rows(result, "training")
    assert losses[-1]["loss"] < losses[0]["loss"]


@pytest.mark.parametrize("algorithm, dependency", [("embedding.gcn", "torch"), ("embedding.gat", "torch_geometric")])
def test_optional_gnn_adapters_fail_with_explicit_capability_error(algorithm, dependency):
    with pytest.raises(AlgorithmInputError) as exc:
        execute_algorithm(algorithm, PATH3, {"clusters": 2}, seed=1)

    assert exc.value.code == "capability_unavailable"
    assert dependency in str(exc.value)


def test_chinese_preprocessing_and_rule_extraction_are_deterministic_and_correction_friendly():
    text = "华为与比亚迪签署合作协议。比亚迪投资了星辰科技！"
    assert preprocess_chinese(text) == preprocess_chinese(text)
    extracted = extract_chinese_graph(text, method="rule", embedding="cosine", seed=4)

    assert [node["id"] for node in extracted["graph"]["nodes"]] == sorted(node["id"] for node in extracted["graph"]["nodes"])
    assert {"entity", "start", "end", "confidence", "editable"} <= set(extracted["entities"][0])
    assert {"source", "target", "relation", "evidence", "confidence", "editable"} <= set(extracted["relations"][0])
    assert all(0 <= edge["weight"] <= 1 for edge in extracted["graph"]["edges"])
    assert json.loads(json.dumps(extracted, ensure_ascii=False)) == extracted


@pytest.mark.parametrize("method, dependency", [("paddlenlp", "paddlenlp"), ("bge", "sentence-transformers")])
def test_absent_text_models_raise_explicit_capability_errors(method, dependency):
    with pytest.raises(AlgorithmInputError) as exc:
        extract_chinese_graph("华为与比亚迪合作。", method=method)

    assert exc.value.code == "capability_unavailable"
    assert dependency in str(exc.value)


@pytest.mark.parametrize("format_name", ["json", "csv", "graphml", "gexf", "gml", "pajek", "edgelist", "adjacency"])
def test_standard_graph_exports_are_deterministic_and_parseable(format_name):
    first = export_graph(PATH3, format_name)
    second = export_graph(PATH3, format_name)

    assert first == second
    assert first["content"]
    if format_name == "json":
        assert json.loads(first["content"])["nodes"][0]["id"] == "a"
    elif format_name in {"csv", "adjacency"}:
        assert list(csv.reader(io.StringIO(first["content"])))
    elif format_name in {"graphml", "gexf"}:
        import xml.etree.ElementTree as ET
        ET.fromstring(first["content"])
    else:
        assert "a" in first["content"]
