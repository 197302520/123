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
        assert item["limits"]["max_nodes"] <= 500
        assert item["limits"]["max_edges"] <= 5_000
        assert item["parameters"]["candidate_limit"]["maximum"] <= 50_000
        assert item["parameters"]["top_k"]["maximum"] <= 500
        with pytest.raises(AlgorithmInputError, match="500"):
            prepare_algorithm_request(key, sparse_path(2_000), {}, seed=7)


def test_link_prediction_streams_only_the_candidate_budget_and_persists_top_k(monkeypatch):
    yielded = 0
    real_non_edges = nx.non_edges

    def bounded_non_edges(network):
        nonlocal yielded
        for edge in real_non_edges(network):
            yielded += 1
            if yielded > 17:
                raise AssertionError("candidate iterator was consumed beyond candidate_limit")
            yield edge

    monkeypatch.setattr(prediction.nx, "non_edges", bounded_non_edges)
    result = execute_algorithm(
        "link_prediction.common_neighbors",
        sparse_path(40),
        {"test_fraction": 0, "candidate_limit": 17, "top_k": 5},
        seed=7,
    )

    evaluation = result["provenance"]["evaluation"]
    assert yielded == 17
    assert len(result["tables"][0]["rows"]) == 5
    assert len(result["overlays"][0]["edges"]) <= 5
    assert evaluation["candidates_evaluated"] == 17
    assert evaluation["candidate_pairs_total"] > 17
    assert evaluation["candidate_pairs_truncated"] is True


def test_link_prediction_auc_samples_and_provenance_stay_bounded():
    result = execute_algorithm(
        "link_prediction.jaccard",
        sparse_path(300),
        {"test_fraction": 0.8, "candidate_limit": 1_000, "top_k": 20},
        seed=17,
    )

    evaluation = result["provenance"]["evaluation"]
    assert len(result["tables"][0]["rows"]) <= 20
    assert len(evaluation["test_edges"]) <= 200
    assert len(evaluation["negative_edges"]) <= 200
    assert len(evaluation["training_edges"]) <= 200
    assert evaluation["training_edge_count"] >= len(evaluation["training_edges"])
