import subprocess
import sys
import os
from pathlib import Path

import yaml


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
    assert compose["web"]["environment"]["DJANGO_NUM_PROXIES"] == "1"
    assert compose["frontend"]["ports"] == ["127.0.0.1:8080:80"]
    assert compose["web"]["environment"]["CACHE_URL"] == "redis://redis:6379/1"
    assert "--queues=default" in compose["worker"]["command"]


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
