from __future__ import annotations

import argparse
from pathlib import Path

import yaml


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Compose contracts without requiring Docker.")
    parser.add_argument("path", nargs="?", default="compose.prod.yaml")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    services = yaml.safe_load((root / args.path).read_text(encoding="utf-8"))["services"]
    required = {"postgres", "redis", "web", "worker", "beat", "frontend", "backup", "ml-worker"}
    missing = required - set(services)
    if missing:
        raise SystemExit(f"missing services: {sorted(missing)}")
    if "--beat" in str(services["worker"].get("command", "")):
        raise SystemExit("worker must not embed beat")
    if services["web"].get("environment", {}).get("CELERY_TASK_ALWAYS_EAGER") != "0":
        raise SystemExit("production web must enqueue Celery jobs")
    print("compose contract valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
