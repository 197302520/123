import pytest
from rest_framework.test import APIClient

from learning.algorithms import embeddings as embedding_module


@pytest.fixture
def api_client():
    return APIClient()


PATH3 = {
    "directed": False,
    "nodes": [{"id": "a"}, {"id": "b"}, {"id": "c"}],
    "edges": [{"source": "a", "target": "b"}, {"source": "b", "target": "c"}],
}


@pytest.mark.parametrize("edges, expected_path", [
    ([{"source": "a", "target": "b"}, {"source": "b", "target": "a"}], "edges[1]"),
    ([{"source": "a", "target": "b", "weight": 0}], "edges[0].weight"),
])
def test_public_graph_validation_rejects_duplicate_or_nonpositive_edges(api_client, edges, expected_path):
    response = api_client.post("/api/graphs/validate/", {
        "directed": False, "nodes": [{"id": "a"}, {"id": "b"}], "edges": edges,
    }, format="json")

    assert response.status_code == 400
    assert response.json()["valid"] is False
    assert response.json()["errors"][0]["path"] == expected_path


def test_public_graph_validation_handles_huge_numeric_weight_without_500(api_client):
    response = api_client.post("/api/graphs/validate/", {
        "directed": False,
        "nodes": [{"id": "a"}, {"id": "b"}],
        "edges": [{"source": "a", "target": "b", "weight": 10 ** 400}],
    }, format="json")

    assert response.status_code == 400
    assert response.json() == {
        "valid": False,
        "errors": [{"path": "edges[0].weight", "message": "边权重必须是有限数值。"}],
    }


@pytest.mark.django_db
def test_run_api_handles_huge_numeric_parameter_without_500(api_client):
    response = api_client.post("/api/runs/", {
        "algorithm": "model.er",
        "graph": {"directed": False, "nodes": [], "edges": []},
        "parameters": {"n": 3, "p": 10 ** 400},
        "seed": 1,
    }, format="json")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_input"
    assert "有限数值" in response.json()["error"]["message"]


@pytest.mark.django_db
def test_run_api_handles_huge_nested_opinion_value_without_500(api_client):
    response = api_client.post("/api/runs/", {
        "algorithm": "opinion.degroot",
        "graph": PATH3,
        "parameters": {"opinions": {"a": 10 ** 400}},
        "seed": 1,
    }, format="json")

    assert response.status_code == 400
    assert response.json()["error"] == {
        "code": "invalid_input",
        "message": "节点 'a' 的意见必须在 0–1 之间。",
        "path": "parameters.opinions.a",
    }


def test_registry_api_preserves_foundation_fields_and_adds_complete_teaching_metadata(api_client):
    response = api_client.get("/api/algorithms/")
    first = response.json()[0]

    assert response.status_code == 200
    assert {key: first[key] for key in ["key", "name", "supported_graph_types", "parameters", "version", "description"]} == {
        "key": "graph.validate",
        "name": "图结构验证",
        "supported_graph_types": ["directed", "undirected"],
        "parameters": {},
        "version": "1.0",
        "description": "验证图结构是否可用于后续分析。",
    }
    assert {"limits", "formula", "explanation", "advantages", "limitations"} <= set(first)
    assert len(response.json()) == 41


@pytest.mark.django_db
def test_run_api_executes_selected_algorithm_and_persists_real_result(api_client):
    submission = api_client.post("/api/runs/", {
        "algorithm": "centrality.degree",
        "graph": PATH3,
        "parameters": {},
        "seed": 7,
    }, format="json")

    assert submission.status_code == 201
    result = api_client.get(f"/api/runs/{submission.json()['id']}/result/").json()
    assert result["status"] == "completed"
    assert result["overlays"]
    assert {row["node"]: row["value"] for row in result["tables"][0]["rows"]} == {"a": 0.5, "b": 1.0, "c": 0.5}
    assert result["provenance"]["algorithm"] == "centrality.degree"
    assert len(result["provenance"]["graph_hash"]) == 64
    assert len(result["provenance"]["parameter_hash"]) == 64


@pytest.mark.django_db
def test_run_api_returns_structured_algorithm_validation_and_capability_errors(api_client, monkeypatch):
    original_find_spec = embedding_module.importlib.util.find_spec
    monkeypatch.setattr(
        embedding_module.importlib.util,
        "find_spec",
        lambda name: None if name == "torch" else original_find_spec(name),
    )
    directed = {**PATH3, "directed": True}
    wrong_shape = api_client.post("/api/runs/", {
        "algorithm": "community.louvain", "graph": directed, "parameters": {}, "seed": 1,
    }, format="json")
    missing_capability = api_client.post("/api/runs/", {
        "algorithm": "embedding.gcn", "graph": PATH3, "parameters": {"clusters": 2}, "seed": 1,
    }, format="json")

    assert wrong_shape.status_code == 400
    assert wrong_shape.json()["error"]["code"] == "unsupported_graph_type"
    assert "无向图" in wrong_shape.json()["error"]["message"]
    assert missing_capability.status_code == 400
    assert missing_capability.json()["error"]["code"] == "capability_unavailable"
    assert "torch" in missing_capability.json()["error"]["message"]


@pytest.mark.django_db
def test_api_runs_are_reproducible_for_same_graph_parameters_version_and_seed(api_client):
    payload = {
        "algorithm": "community.lpa",
        "graph": {
            "directed": False,
            "nodes": [{"id": value} for value in "abcdef"],
            "edges": [
                {"source": "a", "target": "b"}, {"source": "b", "target": "c"},
                {"source": "c", "target": "a"}, {"source": "d", "target": "e"},
                {"source": "e", "target": "f"}, {"source": "f", "target": "d"},
                {"source": "c", "target": "d", "weight": 0.2},
            ],
        },
        "parameters": {},
        "seed": 31,
    }
    first = api_client.post("/api/runs/", payload, format="json").json()
    second = api_client.post("/api/runs/", payload, format="json").json()
    first_result = api_client.get(f"/api/runs/{first['id']}/result/").json()
    second_result = api_client.get(f"/api/runs/{second['id']}/result/").json()

    first_result.pop("run_id")
    second_result.pop("run_id")
    assert first_result == second_result
