import base64
from io import BytesIO
from unittest.mock import patch
import zipfile

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import identify_hasher
from django.contrib.sessions.backends.db import SessionStore
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, connection
from django.db.models.query import QuerySet
from django.test import RequestFactory, override_settings
from rest_framework.test import APIClient
from openpyxl import Workbook

from learning.models import Case


SIMPLE_GRAPH = {
    "directed": False,
    "nodes": [{"id": "a"}, {"id": "b"}],
    "edges": [{"source": "a", "target": "b"}],
}


def test_forwarded_https_header_is_only_trusted_when_the_reverse_proxy_is_trusted():
    """A direct deployment must not let a client spoof HTTPS with a forwarded header."""
    assert settings.SECURE_PROXY_SSL_HEADER is None or settings.TRUST_PROXY_HEADERS


@override_settings(
    TRUST_PROXY_HEADERS=True,
    SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"),
)
def test_trusted_outer_proxy_headers_preserve_https_and_the_real_client_identity():
    """Overwriting outer TLS/client headers would cause redirects and one shared throttle identity."""
    request = RequestFactory().get(
        "/api/cases/", secure=False, REMOTE_ADDR="172.18.0.1",
        HTTP_X_FORWARDED_PROTO="https", HTTP_X_REAL_IP="203.0.113.25",
    )

    from learning.middleware import client_ip

    assert request.is_secure() is True
    assert client_ip(request) == "203.0.113.25"


@pytest.fixture(autouse=True)
def clear_throttles():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client():
    return APIClient()


def test_graph_validation_rejects_the_global_2000_node_shape_limit(api_client):
    """Removing the public shape cap would allow oversized work before algorithm limits run."""
    graph = {"directed": False, "nodes": [{"id": str(index)} for index in range(2001)], "edges": []}
    response = api_client.post("/api/graphs/validate/", graph, format="json")

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "limit_exceeded"
    assert response.json()["error"]["path"] == "nodes"


@pytest.mark.parametrize("node", [
    {"id": "a\x01", "label": "a"},
    {"id": "a", "label": "unsafe\x01label"},
])
def test_graph_validation_rejects_xml_illegal_node_text_before_report_export(api_client, node):
    """Accepted graph text must always remain serializable as valid GraphML."""
    response = api_client.post("/api/graphs/validate/", {
        "directed": False, "nodes": [node], "edges": [],
    }, format="json")

    assert response.status_code == 400


@pytest.mark.django_db
@override_settings(PUBLIC_ALGORITHM_RATES={"standard": "2/minute", "heavy": "1/minute"})
def test_run_throttles_are_isolated_by_ip_session_and_algorithm_category(api_client):
    """A single undifferentiated or absent throttle would not protect heavy public algorithms."""
    standard = {"algorithm": "centrality.degree", "graph": SIMPLE_GRAPH, "parameters": {}, "seed": 1}
    heavy = {"algorithm": "community.girvan_newman", "graph": SIMPLE_GRAPH, "parameters": {"communities": 2}, "seed": 1}

    assert api_client.post("/api/runs/", standard, format="json").status_code == 201
    assert api_client.post("/api/runs/", standard, format="json").status_code == 201
    assert api_client.post("/api/runs/", standard, format="json").status_code == 429
    assert api_client.post("/api/runs/", heavy, format="json").status_code == 201
    assert api_client.post("/api/runs/", heavy, format="json").status_code == 429


@pytest.mark.django_db
@override_settings(PUBLIC_ALGORITHM_RATES={"standard": "10/minute", "heavy": "1/minute"})
def test_every_link_prediction_algorithm_uses_the_heavy_throttle_bucket(api_client):
    """Quadratic candidate spaces must never receive the permissive standard rate."""
    graph = {
        "directed": False,
        "nodes": [{"id": "a"}, {"id": "b"}, {"id": "c"}],
        "edges": [{"source": "a", "target": "b"}],
    }
    for algorithm in (
        "link_prediction.common_neighbors", "link_prediction.jaccard",
        "link_prediction.adamic_adar", "link_prediction.resource_allocation",
    ):
        cache.clear()
        payload = {"algorithm": algorithm, "graph": graph, "parameters": {}, "seed": 1}
        assert api_client.post("/api/runs/", payload, format="json").status_code == 201
        assert api_client.post("/api/runs/", {**payload, "seed": 2}, format="json").status_code == 429


@pytest.mark.django_db
@override_settings(PUBLIC_ALGORITHM_RATES={"standard": "2/minute", "heavy": "1/minute"})
def test_rotating_sessions_does_not_bypass_the_source_ip_algorithm_limit():
    """Combining IP and session into one key would let one host reset limits by rotating sessions."""
    first, second = APIClient(), APIClient()
    for client in (first, second):
        session = SessionStore()
        session.create()
        client.cookies["sessionid"] = session.session_key
    payload = {"algorithm": "centrality.degree", "graph": SIMPLE_GRAPH, "parameters": {}, "seed": 1}

    assert first.post("/api/runs/", payload, format="json", REMOTE_ADDR="198.51.100.4").status_code == 201
    assert second.post("/api/runs/", payload, format="json", REMOTE_ADDR="198.51.100.4").status_code == 201
    assert second.post("/api/runs/", payload, format="json", REMOTE_ADDR="198.51.100.4").status_code == 429


@pytest.mark.django_db
@override_settings(MAX_UPLOAD_BYTES=128)
def test_import_rejects_unsafe_macro_archive_xml_and_oversized_files(api_client):
    """Trusting extensions or archive/XML internals would expose unsafe parsers."""
    samples = [
        SimpleUploadedFile("network.xlsm", b"not-an-xlsx", content_type="application/vnd.ms-excel.sheet.macroEnabled.12"),
        SimpleUploadedFile("network.json", b"PK\x03\x04archive", content_type="application/json"),
        SimpleUploadedFile("network.graphml", b'<!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]><graphml>&e;</graphml>', content_type="application/graphml+xml"),
        SimpleUploadedFile("large.json", b"x" * 129, content_type="application/json"),
    ]
    statuses = [api_client.post("/api/graphs/import/", {"file": sample}, format="multipart").status_code for sample in samples]

    assert statuses == [415, 415, 400, 413]


def test_import_accepts_safe_json_and_returns_only_normalized_graph(api_client):
    """Breaking the safe parser would prevent legitimate anonymous imports."""
    uploaded = SimpleUploadedFile(
        "network.json",
        b'{"directed":false,"nodes":[{"id":"a"},{"id":"b"}],"edges":[{"source":"a","target":"b"}]}',
        content_type="application/json",
    )
    response = api_client.post("/api/graphs/import/", {"file": uploaded}, format="multipart")

    assert response.status_code == 200
    assert response.json()["graph"] == {
        "directed": False,
        "nodes": [{"id": "a", "label": "a"}, {"id": "b", "label": "b"}],
        "edges": [{"source": "a", "target": "b", "weight": 1.0}],
    }


@pytest.mark.parametrize("name,content_type,content", [
    ("network.txt", "text/plain", b"a b 1\nb c 2\n"),
    ("network.csv", "text/csv", b"source,target,weight\na,b,1\nb,c,2\n"),
    ("network.graphml", "application/graphml+xml", b'''<?xml version="1.0"?><graphml xmlns="http://graphml.graphdrawing.org/xmlns"><graph edgedefault="undirected"><node id="a"/><node id="b"/><edge source="a" target="b"/></graph></graphml>'''),
    ("network.gexf", "application/gexf+xml", b'''<?xml version="1.0"?><gexf xmlns="http://gexf.net/1.2draft" version="1.2"><graph mode="static" defaultedgetype="undirected"><nodes><node id="a" label="a"/><node id="b" label="b"/></nodes><edges><edge id="0" source="a" target="b"/></edges></graph></gexf>'''),
])
def test_import_accepts_each_safe_text_and_xml_graph_format(api_client, name, content_type, content):
    """Removing any advertised safe parser would make its accepted format unusable."""
    response = api_client.post("/api/graphs/import/", {
        "file": SimpleUploadedFile(name, content, content_type=content_type),
    }, format="multipart")

    assert response.status_code == 200, response.content
    assert response.json()["graph"]["edges"]


def test_import_accepts_macro_free_xlsx_edge_table(api_client):
    """Rejecting all ZIP containers would accidentally reject legitimate macro-free XLSX files."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["source", "target", "weight"])
    sheet.append(["a", "b", 1])
    output = BytesIO()
    workbook.save(output)
    response = api_client.post("/api/graphs/import/", {
        "file": SimpleUploadedFile(
            "network.xlsx", output.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
    }, format="multipart")

    assert response.status_code == 200, response.content
    assert response.json()["graph"]["edges"] == [{"source": "a", "target": "b", "weight": 1.0}]


@override_settings(PUBLIC_MAX_EDGES=2)
def test_delimited_import_stops_at_the_edge_limit_before_parsing_more_rows(api_client):
    """A large delimited upload must be rejected incrementally instead of materialized in memory."""
    response = api_client.post("/api/graphs/import/", {
        "file": SimpleUploadedFile(
            "network.csv",
            b"source,target,weight\na,b,1\nb,c,1\nc,d,not-a-number\n",
            content_type="text/csv",
        ),
    }, format="multipart")

    assert response.status_code == 413


@override_settings(MAX_UPLOAD_BYTES=1024)
def test_import_rejects_xlsx_with_excessive_decompressed_size(api_client):
    """A tiny compressed XLSX must not expand without a bound inside the parser."""
    output = BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("xl/worksheets/sheet1.xml", b"x" * 5000)
    response = api_client.post("/api/graphs/import/", {
        "file": SimpleUploadedFile(
            "network.xlsx", output.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
    }, format="multipart")

    assert response.status_code == 413


@override_settings(PUBLIC_MAX_NODES=2)
def test_json_import_stops_at_the_node_cap_before_validating_later_items(api_client):
    """A JSON parser must stop at the cap rather than materialize and validate attacker-sized arrays."""
    uploaded = SimpleUploadedFile(
        "network.json",
        b'{"directed":false,"nodes":[{"id":"a"},{"id":"b"},{"id":null}],"edges":[]}',
        content_type="application/json",
    )

    response = api_client.post("/api/graphs/import/", {"file": uploaded}, format="multipart")

    assert response.status_code == 413


@override_settings(PUBLIC_MAX_NODES=2)
def test_xml_import_stops_at_the_node_cap_before_parsing_the_trailing_document(api_client):
    """XML graph parsing must reject over-limit input before building a complete document tree."""
    uploaded = SimpleUploadedFile(
        "network.graphml",
        b'<graphml xmlns="http://graphml.graphdrawing.org/xmlns"><graph edgedefault="undirected"><node id="a"/><node id="b"/><node id="c"/><broken',
        content_type="application/graphml+xml",
    )

    response = api_client.post("/api/graphs/import/", {"file": uploaded}, format="multipart")

    assert response.status_code == 413


@pytest.mark.django_db
def test_public_and_nonstaff_users_cannot_cross_teacher_mutation_boundary(api_client):
    """Weak permission classes would allow anonymous or ordinary users to author cases."""
    payload = {"slug": "intrusion", "title": "越权", "summary": "越权", "module": "communities"}
    anonymous = api_client.post("/api/teacher/cases/", payload, format="json")
    student = get_user_model().objects.create_user(username="student", password="Student-Passphrase-2026!")
    api_client.force_authenticate(student)
    nonstaff = api_client.post("/api/teacher/cases/", payload, format="json")
    public_mutation = api_client.put("/api/cases/zachary-karate/", payload, format="json")

    assert anonymous.status_code in {401, 403}
    assert nonstaff.status_code == 403
    assert public_mutation.status_code == 405


@pytest.mark.django_db
def test_teacher_api_rejects_basic_authentication_even_for_staff(api_client):
    """Basic auth bypasses CSRF, so the teacher mutation boundary must accept sessions only."""
    from django.core.management import call_command

    call_command("seed_learning_content")
    teacher = get_user_model().objects.create_user(
        username="basic-teacher", password="Strong-Teacher-Passphrase-2026!", is_staff=True,
    )
    token = base64.b64encode(b"basic-teacher:Strong-Teacher-Passphrase-2026!").decode("ascii")
    client = APIClient(enforce_csrf_checks=True)

    response = client.post("/api/teacher/cases/", {
        "slug": "basic-bypass", "title": "Basic 越权", "summary": "不得创建", "module": "communities",
    }, format="json", HTTP_AUTHORIZATION=f"Basic {token}")

    assert response.status_code in {401, 403}
    assert not Case.objects.filter(slug="basic-bypass").exists()


@pytest.mark.django_db
@override_settings(TEACHER_LOGIN_ATTEMPTS=2, TEACHER_LOGIN_WINDOW_SECONDS=900)
def test_teacher_login_is_throttled_by_source_ip_after_repeated_failures(api_client):
    """Removing login throttling would leave the teacher boundary open to brute force."""
    responses = [
        api_client.post("/admin/login/", {"username": "teacher", "password": "wrong"}, REMOTE_ADDR="203.0.113.9")
        for _ in range(3)
    ]
    assert [response.status_code for response in responses] == [200, 200, 429]


@pytest.mark.django_db
@override_settings(
    TEACHER_LOGIN_ATTEMPTS=1,
    TEACHER_LOGIN_WINDOW_SECONDS=900,
    TRUST_PROXY_HEADERS=True,
)
def test_teacher_login_throttle_uses_validated_real_ip_behind_trusted_proxy(api_client):
    """Production proxying must not collapse every teacher into one shared login bucket."""
    first = api_client.post(
        "/admin/login/", {"username": "teacher", "password": "wrong"},
        REMOTE_ADDR="172.18.0.6", HTTP_X_REAL_IP="203.0.113.10",
    )
    second = api_client.post(
        "/admin/login/", {"username": "teacher", "password": "wrong"},
        REMOTE_ADDR="172.18.0.6", HTTP_X_REAL_IP="203.0.113.11",
    )
    repeated = api_client.post(
        "/admin/login/", {"username": "teacher", "password": "wrong"},
        REMOTE_ADDR="172.18.0.6", HTTP_X_REAL_IP="203.0.113.11",
    )

    assert [first.status_code, second.status_code, repeated.status_code] == [200, 200, 429]


@pytest.mark.django_db
@override_settings(TEACHER_LOGIN_ATTEMPTS=1, TEACHER_LOGIN_WINDOW_SECONDS=900)
def test_successful_teacher_login_does_not_consume_the_failed_attempt_budget():
    """A successful credential check must reset the source bucket instead of locking teachers out."""
    get_user_model().objects.create_superuser(
        username="login-teacher", password="Strong-Admin-Passphrase-2026!",
    )
    statuses = []
    for _ in range(2):
        client = APIClient()
        response = client.post(
            "/admin/login/", {"username": "login-teacher", "password": "Strong-Admin-Passphrase-2026!"},
            REMOTE_ADDR="203.0.113.44",
        )
        statuses.append(response.status_code)

    assert statuses == [302, 302]


@pytest.mark.django_db
@override_settings(PUBLIC_OPERATION_RATES={"public": "1/minute"})
def test_public_operation_creates_anonymous_session_and_session_throttle_survives_ip_rotation():
    """Both non-identifying session and IP buckets must be active for anonymous public work."""
    client = APIClient()
    first = client.post("/api/graphs/validate/", SIMPLE_GRAPH, format="json", REMOTE_ADDR="198.51.100.10")
    second = client.post("/api/graphs/validate/", SIMPLE_GRAPH, format="json", REMOTE_ADDR="198.51.100.11")

    assert first.status_code == 200
    assert "sessionid" in first.cookies
    assert second.status_code == 429


@pytest.mark.django_db
def test_teacher_passwords_use_the_memory_hard_scrypt_default():
    """Falling back to a fast password hash would weaken the authenticated teacher boundary."""
    teacher = get_user_model().objects.create_user(
        username="teacher-hash", password="Strong-Teacher-Passphrase-2026!",
    )

    assert identify_hasher(teacher.password).algorithm == "scrypt"


@pytest.mark.django_db
def test_teacher_case_slug_is_rejected_before_exceeding_the_database_contract(api_client):
    """SQLite must not mask a slug length that would fail against PostgreSQL in production."""
    from django.core.management import call_command

    call_command("seed_learning_content")
    teacher = get_user_model().objects.create_user(
        username="teacher-slug", password="Strong-Teacher-Passphrase-2026!", is_staff=True,
    )
    api_client.force_authenticate(teacher)
    response = api_client.post("/api/teacher/cases/", {
        "slug": "s" * 51, "title": "越界 slug", "summary": "应在边界拒绝", "module": "communities",
    }, format="json")

    assert response.status_code == 400
    assert "slug" in response.json()["errors"]


@pytest.mark.django_db
def test_teacher_case_uniqueness_race_returns_conflict_without_partial_audit(api_client):
    """A concurrent slug insert must become a controlled conflict rather than a 500 or partial audit."""
    from django.core.management import call_command

    call_command("seed_learning_content")
    teacher = get_user_model().objects.create_user(
        username="teacher-race", password="Strong-Teacher-Passphrase-2026!", is_staff=True,
    )
    api_client.force_authenticate(teacher)
    api_client.raise_request_exception = False
    with patch("learning.teacher_views.Case.objects.create", side_effect=IntegrityError("unique slug")):
        response = api_client.post("/api/teacher/cases/", {
            "slug": "racing-case", "title": "并发案例", "summary": "冲突", "module": "communities",
        }, format="json")

    assert response.status_code == 409
    assert response.json()["errors"]["slug"] == "slug 已存在。"
    assert not Case.objects.filter(slug="racing-case").exists()


@pytest.mark.django_db
def test_teacher_patch_locks_and_refetches_inside_transaction_with_controlled_update_fields(api_client, monkeypatch):
    """A stale object fetched before the transaction can lose another teacher's update."""
    from django.core.management import call_command

    call_command("seed_learning_content")
    teacher = get_user_model().objects.create_user(
        username="locked-teacher", password="Strong-Teacher-Passphrase-2026!", is_staff=True,
    )
    api_client.force_authenticate(teacher)
    lock_states: list[bool] = []
    saved_fields: list[set[str] | None] = []
    original_lock = QuerySet.select_for_update
    original_save = Case.save

    def tracked_lock(queryset, *args, **kwargs):
        if queryset.model is Case:
            lock_states.append(connection.in_atomic_block)
        return original_lock(queryset, *args, **kwargs)

    def tracked_save(instance, *args, **kwargs):
        if instance.slug == "zachary-karate":
            update_fields = kwargs.get("update_fields")
            saved_fields.append(set(update_fields) if update_fields is not None else None)
        return original_save(instance, *args, **kwargs)

    monkeypatch.setattr(QuerySet, "select_for_update", tracked_lock)
    monkeypatch.setattr(Case, "save", tracked_save)
    response = api_client.patch("/api/teacher/cases/zachary-karate/", {
        "summary": "并发安全的摘要", "module_id": 999, "unexpected": "ignored",
    }, format="json")

    assert response.status_code == 200
    assert lock_states == [True]
    assert saved_fields == [{"summary"}]
    case = Case.objects.get(slug="zachary-karate")
    assert case.summary == "并发安全的摘要"
