import io
import json
import zipfile

import pytest
from django.apps import apps
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import RequestFactory
from rest_framework.test import APIClient

from learning.models import Case, CourseModule, Dataset, PublishStatus, Run
from learning.admin import CaseAdmin


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_seed_is_idempotent_and_all_seven_provenanced_cases_run_real_algorithms(api_client):
    """Dropping a graph/algorithm/provenance field would make a seeded case non-runnable."""
    call_command("seed_learning_content")
    call_command("seed_learning_content")

    assert Case.objects.count() == 7
    expected = {
        "zachary-karate", "dolphins", "football-bipartite", "enterprise-text",
        "trade-snapshots", "opinion-dynamics", "cora-citations",
    }
    assert set(Case.objects.values_list("slug", flat=True)) == expected

    for slug in sorted(expected):
        case_response = api_client.get(f"/api/cases/{slug}/")
        assert case_response.status_code == 200
        dataset = case_response.json()["dataset"]
        metadata = dataset["metadata"]
        assert all(metadata[field] for field in ("source", "license", "cleaning", "version"))
        assert isinstance(metadata["graph"], dict)
        assert isinstance(metadata["parameters"], dict)

        submission = api_client.post("/api/runs/", {
            "algorithm": metadata["algorithm"],
            "graph": metadata["graph"],
            "parameters": metadata["parameters"],
            "seed": metadata["seed"],
        }, format="json")
        assert submission.status_code == 201, (slug, submission.json())
        assert submission.json()["status"] == "completed"
        result_response = api_client.get(f"/api/runs/{submission.json()['id']}/result/")
        assert result_response.status_code == 200
        result = result_response.json()
        assert result["tables"] or result["overlays"] or result["charts"]
        assert result["provenance"]["algorithm"] == metadata["algorithm"]
        assert len(result["provenance"]["graph_hash"]) == 64
        assert len(result["provenance"]["parameter_hash"]) == 64


@pytest.mark.django_db
def test_anonymous_case_to_algorithm_to_downloadable_report_bundle_is_end_to_end(api_client):
    """A disconnected report route would break the anonymous reproducibility journey."""
    call_command("seed_learning_content")
    case = api_client.get("/api/cases/zachary-karate/").json()
    dataset = case["dataset"]["metadata"]
    dataset["graph"]["nodes"][0]["label"] = "=2+2<script>alert(1)</script>"
    submission = api_client.post("/api/runs/", {
        "algorithm": dataset["algorithm"], "graph": dataset["graph"],
        "parameters": dataset["parameters"], "seed": dataset["seed"],
    }, format="json")
    run_id = submission.json()["id"]

    status_response = api_client.get(f"/api/runs/{run_id}/")
    result_response = api_client.get(f"/api/runs/{run_id}/result/")
    manifest_response = api_client.post("/api/reports/", {"run_id": run_id}, format="json")
    bundle_response = api_client.get(f"/api/reports/{run_id}/bundle/")

    assert status_response.json()["status"] == "completed"
    assert result_response.json()["tables"]
    assert manifest_response.status_code == 201
    assert manifest_response.json()["download_url"].endswith(f"/api/reports/{run_id}/bundle/")
    assert "<script>" not in manifest_response.json()["content"]
    assert bundle_response.status_code == 200
    assert bundle_response["Content-Type"] == "application/zip"
    assert bundle_response["Content-Disposition"].startswith('attachment; filename="sna-report-')
    with zipfile.ZipFile(io.BytesIO(bundle_response.content)) as archive:
        names = set(archive.namelist())
        assert {"report.html", "result.json", "nodes.csv", "edges.csv", "graph.graphml", "parameters.json", "provenance.json", "manifest.json"} <= names
        assert any(name.startswith("tables/") and name.endswith(".csv") for name in names)
        assert b"<script>" not in archive.read("report.html")
        assert "'=2+2" in archive.read("nodes.csv").decode("utf-8-sig")
        assert json.loads(archive.read("result.json"))["provenance"]["algorithm"] == dataset["algorithm"]


@pytest.mark.django_db
def test_staff_teacher_creates_edits_and_publishes_draft_with_csrf_and_audit(api_client):
    """Missing staff/CSRF/audit checks would let public clients publish unaudited content."""
    call_command("seed_learning_content")
    teacher = get_user_model().objects.create_user(
        username="teacher", password="Strong-Teacher-Passphrase-2026!", is_staff=True,
    )
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(teacher)
    session_response = client.get("/api/teacher/session/")
    csrf_token = session_response.cookies["csrftoken"].value
    dataset = Dataset.objects.get(slug="dolphins")

    rejected = client.post("/api/teacher/cases/", {
        "slug": "teacher-case", "title": "教师案例", "summary": "草稿",
        "module": "communities", "dataset": dataset.slug,
    }, format="json")
    assert rejected.status_code == 403
    created = client.post("/api/teacher/cases/", {
        "slug": "teacher-case", "title": "教师案例", "summary": "草稿",
        "module": "communities", "dataset": dataset.slug,
    }, format="json", HTTP_X_CSRFTOKEN=csrf_token)
    assert created.status_code == 201
    assert created.json()["status"] == "draft"
    assert api_client.get("/api/cases/teacher-case/").status_code == 404

    published = client.patch("/api/teacher/cases/teacher-case/", {
        "summary": "已编辑并发布", "status": "published",
    }, format="json", HTTP_X_CSRFTOKEN=csrf_token)
    assert published.status_code == 200
    assert api_client.get("/api/cases/teacher-case/").json()["summary"] == "已编辑并发布"
    audit_model = apps.get_model("learning", "AuditRecord")
    assert list(audit_model.objects.filter(actor=teacher).values_list("action", flat=True)) == ["create", "update"]


@pytest.mark.django_db
def test_django_admin_case_mutations_also_create_audit_records():
    """Using the admin directly must not bypass the teacher mutation audit trail."""
    call_command("seed_learning_content")
    teacher = get_user_model().objects.create_superuser(
        username="admin-teacher", password="Strong-Admin-Passphrase-2026!",
    )
    request = RequestFactory().post("/admin/learning/case/add/", REMOTE_ADDR="198.51.100.7")
    request.user = teacher
    case_admin = CaseAdmin(Case, admin.site)
    form_class = case_admin.get_form(request)
    form = form_class(data={
        "module": CourseModule.objects.get(slug="communities").pk,
        "dataset": Dataset.objects.get(slug="dolphins").pk,
        "slug": "admin-authored", "title": "后台案例", "summary": "后台草稿", "content": "", "status": "draft",
    })
    assert form.is_valid(), form.errors
    case_admin.save_model(request, form.save(commit=False), form, change=False)

    audit_model = apps.get_model("learning", "AuditRecord")
    audit = audit_model.objects.get(entity_id="admin-authored")
    assert audit.actor == teacher
    assert audit.action == "create"
    assert audit.source_ip == "198.51.100.7"

    case_admin.delete_queryset(request, Case.objects.filter(slug="admin-authored"))
    assert list(audit_model.objects.filter(entity_id="admin-authored").values_list("action", flat=True)) == ["create", "delete"]
