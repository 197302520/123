import subprocess
import sys
import os
import io
import http.cookiejar
import urllib.request
import urllib.response
from email.message import Message
from pathlib import Path

import pytest
import yaml
from django.core.management import call_command
from django.test import Client, override_settings


ROOT = Path(__file__).resolve().parents[2]


def test_production_compose_separates_worker_scheduler_and_declares_optional_ml_and_ops_services():
    """Running beat inside every worker or omitting production profiles would duplicate jobs."""
    compose = yaml.safe_load((ROOT / "compose.prod.yaml").read_text(encoding="utf-8"))["services"]

    assert {"postgres", "redis", "web", "worker", "beat", "frontend", "backup", "ml-worker"} <= set(compose)
    assert "gunicorn" in compose["web"]["command"]
    assert "--beat" not in compose["worker"]["command"]
    assert "beat" in compose["beat"]["command"]
    assert "ml" in compose["ml-worker"]["profiles"]
    assert compose["backup"]["environment"]["BACKUP_RETENTION_DAYS"] == "14"
    assert compose["web"]["environment"]["DJANGO_TRUST_PROXY_HEADERS"] == "1"
    assert compose["web"]["environment"]["DJANGO_NUM_PROXIES"] == "${DJANGO_NUM_PROXIES:-1}"
    assert compose["frontend"]["ports"] == ["127.0.0.1:8080:80"]
    assert compose["web"]["environment"]["CACHE_URL"] == "redis://redis:6379/1"
    assert "--queues=default" in compose["worker"]["command"]
    healthcheck = " ".join(compose["web"]["healthcheck"]["test"])
    assert "/api/health/" in healthcheck
    assert "urllib.request" in healthcheck
    assert "DJANGO_ALLOWED_HOSTS" in healthcheck
    assert "X-Forwarded-Proto" in healthcheck and "https" in healthcheck
    assert "manage.py check" not in healthcheck


def test_health_endpoint_proves_the_django_http_stack_is_listening():
    response = Client().get("/api/health/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_release_and_load_verification_scripts_are_bounded_and_executable_in_dry_run():
    """An unbounded or non-runnable checklist would not be usable without local Docker."""
    release = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_release.py"), "--dry-run"],
        cwd=ROOT, text=True, capture_output=True, timeout=10,
    )
    load = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "load_test.py"), "--dry-run", "--students", "90", "--max-jobs", "30"],
        cwd=ROOT, text=True, capture_output=True, timeout=10,
    )

    assert release.returncode == 0 and "pytest" in release.stdout and "npm" in release.stdout
    assert load.returncode == 0 and "students=90" in load.stdout and "max_jobs=30" in load.stdout
    assert "distinct_jobs=90" in load.stdout


def test_production_frontend_install_is_lockfile_frozen_and_blocks_dependency_scripts():
    """The release image must not run unreviewed package lifecycle scripts during installation."""
    dockerfile = (ROOT / "frontend" / "Dockerfile.prod").read_text(encoding="utf-8")

    assert "npm ci --ignore-scripts" in dockerfile


def test_inner_nginx_preserves_outer_proxy_tls_and_client_identity_headers():
    """Replacing outer HTTPS/client headers with the inner hop causes redirect loops and shared limits."""
    nginx = (ROOT / "frontend" / "nginx.conf").read_text(encoding="utf-8")

    assert "proxy_set_header X-Forwarded-Proto $http_x_forwarded_proto;" in nginx
    assert "proxy_set_header X-Real-IP $http_x_real_ip;" in nginx
    assert "proxy_set_header X-Forwarded-For $http_x_forwarded_for;" in nginx
    assert "proxy_set_header X-Forwarded-Proto $scheme;" not in nginx
    assert "proxy_set_header X-Real-IP $remote_addr;" not in nginx


def test_cache_url_selects_shared_redis_backend_in_production_settings():
    """Per-process memory caches cannot enforce limits across multiple Gunicorn workers."""
    environment = os.environ.copy()
    environment["CACHE_URL"] = "redis://redis:6379/1"
    check = subprocess.run(
        [sys.executable, "-c", "from config.settings import CACHES; print(CACHES['default']['BACKEND']); print(CACHES['default']['LOCATION'])"],
        cwd=ROOT / "backend", env=environment, text=True, capture_output=True, timeout=10,
    )

    assert check.returncode == 0
    assert check.stdout.splitlines() == ["django_redis.cache.RedisCache", "redis://redis:6379/1"]


def test_restore_contract_uses_canonical_backup_path_and_single_transaction():
    """A traversal/symlink target or partial destructive restore must be rejected by the operations contract."""
    restore = (ROOT / "ops" / "restore.sh").read_text(encoding="utf-8")

    assert 'BACKUP_ROOT="${BACKUP_ROOT:-/backups}"' in restore
    assert 'readlink -f -- "$1"' in restore
    assert '[ -f "$source" ]' in restore
    assert "--single-transaction" in restore


def test_load_plan_assigns_a_distinct_real_cache_key_to_every_student():
    """The capacity exercise must not turn 90 submissions into cache hits of one request."""
    from scripts import load_test

    student_payload = getattr(load_test, "student_payload", None)
    assert callable(student_payload)
    payloads = [student_payload(index) for index in range(90)]
    assert len({payload["seed"] for payload in payloads}) == 90
    assert all(payload["algorithm"] == "centrality.degree" and payload["graph"]["edges"] for payload in payloads)


@pytest.mark.django_db
def test_production_image_collects_and_serves_styled_django_admin_static(tmp_path):
    """The teacher admin must not ship as an unstyled page in the production image."""
    dockerfile = (ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")
    nginx = (ROOT / "frontend" / "nginx.conf").read_text(encoding="utf-8")
    assert "collectstatic --noinput" in dockerfile
    assert "location /static/" in nginx
    assert "proxy_pass http://web:8000;" in nginx.split("location /static/", 1)[1].split("}", 1)[0]

    with override_settings(
        DEBUG=False,
        STATIC_ROOT=tmp_path,
        STORAGES={
            "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
        },
    ):
        call_command("collectstatic", "--noinput", verbosity=0)
        response = Client().get("/static/admin/css/base.css")

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/css")
    assert len(b"".join(response.streaming_content)) > 1_000


def test_load_student_keeps_one_anonymous_session_cookie_for_submit_status_and_result(monkeypatch):
    """A new cookie on every request would not exercise the production session throttle realistically."""
    from scripts import load_test

    observed_cookies: list[str] = []

    class InMemoryHttpTransport(urllib.request.BaseHandler):
        handler_order = 100

        def http_open(self, request):
            headers = Message()
            headers["Content-Type"] = "application/json"
            if request.data is not None:
                payload = {"id": "run-cookie", "status": "completed"}
                headers["Set-Cookie"] = "sessionid=student-session; Path=/"
                status_code = 201
            else:
                observed_cookies.append(request.get_header("Cookie", ""))
                payload = {"tables": [{"key": "result"}]}
                status_code = 200
            encoded = __import__("json").dumps(payload).encode()
            headers["Content-Length"] = str(len(encoded))
            response = urllib.response.addinfourl(io.BytesIO(encoded), headers, request.full_url, status_code)
            response.msg = "OK"
            return response

    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()), InMemoryHttpTransport(),
    )
    monkeypatch.setattr(load_test.urllib.request, "build_opener", lambda *_handlers: opener)
    run_id = load_test.one_student("http://127.0.0.1", 2, 0)

    assert run_id == "run-cookie"
    assert observed_cookies == ["sessionid=student-session"]
