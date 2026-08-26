from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor


GRAPH = {
    "directed": False,
    "nodes": [{"id": "a"}, {"id": "b"}, {"id": "c"}],
    "edges": [{"source": "a", "target": "b"}, {"source": "b", "target": "c"}],
}


def request_json(url: str, *, payload=None, timeout: float = 10.0):
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def one_student(base_url: str, deadline_seconds: float) -> str:
    submitted = request_json(f"{base_url}/api/runs/", payload={"algorithm": "centrality.degree", "graph": GRAPH, "parameters": {}, "seed": 7})
    deadline = time.monotonic() + deadline_seconds
    state = submitted
    while state["status"] in {"pending", "running"} and time.monotonic() < deadline:
        time.sleep(0.25)
        state = request_json(f"{base_url}/api/runs/{submitted['id']}/")
    if state["status"] != "completed":
        raise RuntimeError(f"run ended as {state['status']}")
    result = request_json(f"{base_url}/api/runs/{submitted['id']}/result/")
    if not result.get("tables"):
        raise RuntimeError("completed run returned no tables")
    return submitted["id"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded anonymous classroom load check.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--students", type=int, default=90)
    parser.add_argument("--max-jobs", type=int, default=30)
    parser.add_argument("--deadline", type=float, default=120)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.students <= 90 or not 1 <= args.max_jobs <= 30 or args.deadline <= 0:
        parser.error("students must be 1–90, max-jobs 1–30, and deadline positive")
    print(f"students={args.students} max_jobs={args.max_jobs} deadline={args.deadline:g}s base_url={args.base_url}")
    if args.dry_run:
        return 0
    started = time.monotonic()
    try:
        with ThreadPoolExecutor(max_workers=args.max_jobs) as pool:
            run_ids = list(pool.map(lambda _: one_student(args.base_url.rstrip('/'), args.deadline), range(args.students)))
    except (OSError, urllib.error.URLError, RuntimeError) as exc:
        print(f"load test failed: {exc}")
        return 1
    print(f"completed={len(run_ids)} elapsed={time.monotonic() - started:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
