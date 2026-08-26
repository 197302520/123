from io import BytesIO
import zipfile

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import identify_hasher
from django.contrib.sessions.backends.db import SessionStore
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APIClient
from openpyxl import Workbook


SIMPLE_GRAPH = {
    "directed": False,
    "nodes": [{"id": "a"}, {"id": "b"}],
    "edges": [{"source": "a", "target": "b"}],
}


def test_forwarded_https_header_is_only_trusted_when_the_reverse_proxy_is_trusted():
    """A direct deployment must not let a client spoof HTTPS with a forwarded header."""
    assert settings.SECURE_PROXY_SSL_HEADER is None or settings.TRUST_PROXY_HEADERS


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
