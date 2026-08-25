import pytest
from datetime import timedelta
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient

from learning.models import Case, CourseModule, Dataset, PublishStatus, Run
from learning.tasks import cleanup_expired_runs


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def published_content(db):
    module = CourseModule.objects.create(
        slug="network-basics",
        title="网络基础",
        summary="用图表示关系。",
        order=1,
        status=PublishStatus.PUBLISHED,
    )
    dataset = Dataset.objects.create(
        slug="zachary-karate",
        title="Zachary 空手道俱乐部",
        provenance="Zachary (1977)",
        status=PublishStatus.PUBLISHED,
    )
    case = Case.objects.create(
        module=module,
        dataset=dataset,
        slug="zachary-karate",
        title="空手道俱乐部网络",
        summary="一个经典的社区发现案例。",
        status=PublishStatus.PUBLISHED,
    )
    return module, case


@pytest.mark.django_db
def test_anonymous_visitors_read_only_published_modules_and_cases(api_client, published_content):
    """A missing published filter would expose draft teaching content."""
    CourseModule.objects.create(
        slug="draft-module", title="草稿", summary="不应公开", order=99, status=PublishStatus.DRAFT
    )
    response = api_client.get("/api/modules/")

    assert response.status_code == 200
    assert response.json() == [{
        "slug": "network-basics", "title": "网络基础", "summary": "用图表示关系。", "order": 1,
    }]
    assert api_client.get("/api/cases/zachary-karate/").json()["dataset"]["slug"] == "zachary-karate"


@pytest.mark.django_db
def test_anonymous_visitors_cannot_open_unpublished_case(api_client, published_content):
    """Changing detail lookup to ignore publish status would leak a draft case."""
    module, _ = published_content
    Case.objects.create(
        module=module, slug="draft-case", title="草稿案例", summary="不应公开", status=PublishStatus.DRAFT
    )

    response = api_client.get("/api/cases/draft-case/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_only_staff_teacher_has_django_admin_write_access():
    """Dropping the staff check would let a student change course content."""
    user_model = get_user_model()
    student = user_model.objects.create_user(username="student", password="test-password")
    teacher = user_model.objects.create_user(username="teacher", password="test-password", is_staff=True)

    assert admin.site.has_permission(APIClient().request().wsgi_request) is False
    request = APIClient().request().wsgi_request
    request.user = student
    assert admin.site.has_permission(request) is False
    request.user = teacher
    assert admin.site.has_permission(request) is True


def test_graph_validation_rejects_edges_that_name_unknown_nodes(api_client):
    """Omitting endpoint validation would allow algorithms to receive dangling edges."""
    response = api_client.post("/api/graphs/validate/", {
        "directed": False,
        "nodes": [{"id": "a"}],
        "edges": [{"source": "a", "target": "missing"}],
    }, format="json")

    assert response.status_code == 400
    assert response.json() == {
        "valid": False,
        "errors": [{"path": "edges[0].target", "message": "节点 'missing' 不存在。"}],
    }


def test_graph_validation_returns_a_stable_normalized_graph_shape(api_client):
    """Removing normalisation would make browser-submitted graph contracts unstable."""
    response = api_client.post("/api/graphs/validate/", {
        "directed": True,
        "nodes": [{"id": "a", "label": "甲"}, {"id": "b"}],
        "edges": [{"source": "a", "target": "b", "weight": 2}],
    }, format="json")

    assert response.status_code == 200
    assert response.json() == {
        "valid": True,
        "errors": [],
        "graph": {
            "directed": True,
            "nodes": [{"id": "a", "label": "甲"}, {"id": "b", "label": "b"}],
            "edges": [{"source": "a", "target": "b", "weight": 2.0}],
        },
    }


@pytest.mark.django_db
def test_public_algorithm_and_run_routes_expose_stable_contracts(api_client):
    """Changing route payloads would break the anonymous laboratory client."""
    algorithms = api_client.get("/api/algorithms/")
    submission = api_client.post("/api/runs/", {
        "algorithm": "graph.validate",
        "graph": {"directed": False, "nodes": [{"id": "a"}], "edges": []},
        "parameters": {},
        "seed": 7,
    }, format="json")

    assert algorithms.status_code == 200
    assert algorithms.json()[0] == {
        "key": "graph.validate", "name": "图结构验证", "supported_graph_types": ["directed", "undirected"],
        "parameters": {}, "version": "1.0", "description": "验证图结构是否可用于后续分析。",
    }
    assert submission.status_code == 201
    assert submission.json() == {
        "id": submission.json()["id"], "status": "completed", "algorithm": "graph.validate", "seed": 7,
    }
    run_id = submission.json()["id"]
    assert api_client.get(f"/api/runs/{run_id}/").json()["status"] == "completed"
    assert api_client.get(f"/api/runs/{run_id}/result/").json() == {
        "run_id": run_id, "status": "completed", "tables": [], "charts": [], "warnings": [],
        "provenance": {"algorithm": "graph.validate", "version": "1.0", "seed": 7},
        "validation": {
            "valid": True,
            "errors": [],
            "graph": {"directed": False, "nodes": [{"id": "a", "label": "a"}], "edges": []},
        },
    }
    run = Run.objects.get(pk=run_id)
    assert run.result["validation"]["graph"]["nodes"] == [{"id": "a", "label": "a"}]
    assert timezone.now() < run.expires_at <= timezone.now() + timedelta(hours=2, seconds=1)
    report = api_client.post("/api/reports/", {"run_id": run_id}, format="json")
    assert report.status_code == 201
    assert report.json()["run_id"] == run_id
    assert report.json()["format"] == "html"


@pytest.mark.django_db
def test_seed_command_creates_seven_modules_and_core_case_metadata():
    """Removing seed definitions would leave a new classroom deployment empty."""
    call_command("seed_learning_content")

    assert CourseModule.objects.filter(status=PublishStatus.PUBLISHED).count() == 7
    assert set(Case.objects.values_list("slug", flat=True)) >= {"zachary-karate", "dolphins"}


@pytest.mark.django_db
def test_expired_anonymous_runs_are_removed_by_cleanup_task():
    """Removing expiry cleanup would retain anonymous graph data indefinitely."""
    expired = Run.objects.create(
        algorithm="graph.validate", graph={}, expires_at=timezone.now() - timedelta(seconds=1)
    )
    retained = Run.objects.create(
        algorithm="graph.validate", graph={}, expires_at=timezone.now() + timedelta(hours=1)
    )

    removed = cleanup_expired_runs()

    assert removed == 1
    assert not Run.objects.filter(pk=expired.pk).exists()
    assert Run.objects.filter(pk=retained.pk).exists()


@pytest.mark.django_db
def test_run_and_report_reject_json_arrays_with_structured_errors(api_client):
    """Calling dict methods on an array request body would turn a client error into a 500."""
    run_response = api_client.post("/api/runs/", [], format="json")
    report_response = api_client.post("/api/reports/", [], format="json")

    assert run_response.status_code == 400
    assert report_response.status_code == 400
    assert run_response.json() == {"detail": "请求体必须是 JSON 对象。"}
    assert report_response.json() == {"detail": "请求体必须是 JSON 对象。"}


@pytest.mark.django_db
def test_expired_anonymous_runs_are_not_available_before_cleanup(api_client):
    """A direct primary-key lookup would expose graph data past its two-hour retention window."""
    expired = Run.objects.create(
        algorithm="graph.validate", graph={}, expires_at=timezone.now() - timedelta(seconds=1)
    )

    status_response = api_client.get(f"/api/runs/{expired.id}/")
    result_response = api_client.get(f"/api/runs/{expired.id}/result/")
    report_response = api_client.post("/api/reports/", {"run_id": str(expired.id)}, format="json")

    assert status_response.status_code == 404
    assert result_response.status_code == 404
    assert report_response.status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize("parameters", [[], "not-an-object"])
def test_run_rejects_non_object_parameters(api_client, parameters):
    """Persisting an array or string would violate the RunRequest parameters contract."""
    response = api_client.post("/api/runs/", {
        "algorithm": "graph.validate",
        "graph": {"directed": False, "nodes": [{"id": "a"}], "edges": []},
        "parameters": parameters,
    }, format="json")

    assert response.status_code == 400
    assert response.json() == {"detail": "parameters 必须是 JSON 对象。"}
