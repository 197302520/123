import networkx as nx
import pytest

from learning.algorithms import AlgorithmInputError, execute_algorithm, get_registry, prepare_algorithm_request
from learning.algorithms import prediction


LINK_ALGORITHMS = {
    "link_prediction.common_neighbors",
    "link_prediction.jaccard",
    "link_prediction.adamic_adar",
    "link_prediction.resource_allocation",
}


def sparse_path(size: int) -> dict:
    return {
        "directed": False,
        "nodes": [{"id": str(index)} for index in range(size)],
        "edges": [{"source": str(index), "target": str(index + 1)} for index in range(size - 1)],
    }


def test_link_prediction_registry_rejects_public_2000_node_sparse_graphs_and_bounds_outputs():
    specs = {item["key"]: item for item in get_registry() if item["key"] in LINK_ALGORITHMS}

    assert set(specs) == LINK_ALGORITHMS
    for key, item in specs.items():
        assert item["limits"]["max_nodes"] <= 300
        assert item["limits"]["max_edges"] <= 5_000
        assert item["parameters"]["candidate_limit"]["maximum"] <= 50_000
        assert item["parameters"]["top_k"]["maximum"] <= 500
        with pytest.raises(AlgorithmInputError, match="300"):
            prepare_algorithm_request(key, sparse_path(2_000), {}, seed=7)


def test_link_prediction_scores_every_permitted_candidate_and_persists_global_top_k(monkeypatch):
    yielded = 0
    real_non_edges = nx.non_edges

    def bounded_non_edges(network):
        nonlocal yielded
        for edge in real_non_edges(network):
            yielded += 1
            if yielded > 741:
                raise AssertionError("candidate iterator exceeded the complete path-graph candidate set")
            yield edge

    monkeypatch.setattr(prediction.nx, "non_edges", bounded_non_edges)
    result = execute_algorithm(
        "link_prediction.common_neighbors",
        sparse_path(40),
        {"test_fraction": 0, "candidate_limit": 1_000, "top_k": 5},
        seed=7,
    )

    evaluation = result["provenance"]["evaluation"]
    assert yielded == 741
    assert len(result["tables"][0]["rows"]) == 5
    assert len(result["overlays"][0]["edges"]) <= 5
    assert evaluation["candidates_evaluated"] == 741
    assert evaluation["candidate_pairs_total"] == 741
    assert evaluation["candidate_pairs_truncated"] is False


def test_link_prediction_rejects_partial_lexicographic_candidate_prefixes():
    """A candidate cap is an admission limit, never a biased first-N scoring shortcut."""
    with pytest.raises(AlgorithmInputError, match="候选") as raised:
        execute_algorithm(
            "link_prediction.common_neighbors",
            sparse_path(40),
            {"test_fraction": 0, "candidate_limit": 17, "top_k": 5},
            seed=7,
        )

    assert raised.value.path == "parameters.candidate_limit"


def test_link_prediction_top_k_is_global_and_not_biased_toward_early_node_ids():
    graph = {
        "directed": False,
        "nodes": [{"id": node} for node in ("a", "b", "x", "y", "z")],
        "edges": [{"source": "x", "target": "y"}, {"source": "x", "target": "z"}],
    }
    result = execute_algorithm(
        "link_prediction.common_neighbors", graph,
        {"test_fraction": 0, "candidate_limit": 10, "top_k": 1}, seed=7,
    )

    assert result["tables"][0]["rows"][0] == {"source": "y", "target": "z", "score": 1.0}
    assert result["provenance"]["evaluation"]["candidates_evaluated"] == 8


def test_link_prediction_auc_samples_and_provenance_stay_bounded():
    result = execute_algorithm(
        "link_prediction.jaccard",
        sparse_path(300),
        {"test_fraction": 0.8, "candidate_limit": 50_000, "top_k": 20},
        seed=17,
    )

    evaluation = result["provenance"]["evaluation"]
    assert len(result["tables"][0]["rows"]) <= 20
    assert len(evaluation["test_edges"]) <= 200
    assert len(evaluation["negative_edges"]) <= 200
    assert len(evaluation["training_edges"]) <= 200
    assert evaluation["training_edge_count"] >= len(evaluation["training_edges"])
