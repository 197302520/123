from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMMANDS = [
    ([sys.executable, "-m", "pytest", "backend/tests", "-q"], ROOT),
    ([sys.executable, "backend/manage.py", "check"], ROOT),
    ([sys.executable, "backend/manage.py", "makemigrations", "--check", "--dry-run"], ROOT),
    ([sys.executable, "-m", "pip", "check"], ROOT),
    ([sys.executable, "scripts/validate_compose.py"], ROOT),
    (["npm", "test", "--", "--run"], ROOT / "frontend"),
    (["npm", "run", "build"], ROOT / "frontend"),
    (["npm", "audit", "--audit-level=high"], ROOT / "frontend"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run bounded release verification.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--timeout", type=int, default=300, help="seconds allowed per command")
    args = parser.parse_args()
    for command, cwd in COMMANDS:
        print(f"[{cwd.name}] {' '.join(command)}")
        if not args.dry_run:
            completed = subprocess.run(command, cwd=cwd, timeout=args.timeout)
            if completed.returncode:
                return completed.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
