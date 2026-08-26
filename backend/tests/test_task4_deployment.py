import subprocess
import sys
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


def test_production_frontend_install_is_lockfile_frozen_and_blocks_dependency_scripts():
    """The release image must not run unreviewed package lifecycle scripts during installation."""
    dockerfile = (ROOT / "frontend" / "Dockerfile.prod").read_text(encoding="utf-8")

    assert "npm ci --ignore-scripts" in dockerfile
