"""One-shot algorithm child used by a production Celery supervisor."""
from __future__ import annotations

import json
import logging
from pathlib import Path
import sys

from .algorithms import AlgorithmInputError, execute_algorithm
from .logging_utils import log_sanitized_exception


logger = logging.getLogger(__name__)


def main(request_name: str, result_name: str) -> int:
    request_path = Path(request_name)
    result_path = Path(result_name)
    request = {}
    try:
        request = json.loads(request_path.read_text(encoding="utf-8"))
        result = execute_algorithm(
            request["algorithm"], request["graph"], request["parameters"], seed=request.get("seed"),
        )
        envelope = {"ok": True, "result": result}
    except AlgorithmInputError as exc:
        envelope = {"ok": False, "error": exc.as_dict()}
    except Exception as exc:
        log_sanitized_exception(
            logger,
            "Unexpected isolated algorithm failure run_id=%s task_id=%s algorithm=%s",
            str(request.get("run_id", "unassigned")),
            str(request.get("task_id", "unassigned")),
            str(request.get("algorithm", "unassigned")),
            exc=exc,
        )
        envelope = {
            "ok": False,
            "error": {"code": "algorithm_failure", "message": "算法执行失败，请检查输入或联系教师。", "path": ""},
        }
    result_path.write_text(
        json.dumps(envelope, ensure_ascii=False, separators=(",", ":")), encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
