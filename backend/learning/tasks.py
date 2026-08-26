"""Background execution and maintenance tasks for anonymous laboratory records."""
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from datetime import timedelta
from threading import Event, Thread

from celery import shared_task
from django.conf import settings
from django.db import close_old_connections
from django.db.models import F, Q
from django.utils import timezone

from .algorithms import AlgorithmInputError, execute_algorithm
from .models import Run
from .logging_utils import log_sanitized_exception


logger = logging.getLogger(__name__)

ML_ALGORITHMS = {"embedding.gcn", "embedding.gat"}
EXPIRED_STATE = "expired"
_RUNNER_ENV_ALLOWLIST = {
    "PATH", "PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "CONDA_PREFIX",
    "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "TEMP", "TMP", "TMPDIR",
    "HOME", "USERPROFILE", "LANG", "LC_ALL", "LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH",
    "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS",
    "KMP_AFFINITY", "CUDA_VISIBLE_DEVICES", "NVIDIA_VISIBLE_DEVICES",
    "NVIDIA_DRIVER_CAPABILITIES", "PYTORCH_CUDA_ALLOC_CONF", "TORCH_HOME",
}


def queue_for_algorithm(algorithm: str) -> str:
    return "ml" if algorithm in ML_ALGORITHMS else "default"


def _lease_deadline():
    return timezone.now() + timedelta(seconds=float(getattr(settings, "RUN_LEASE_SECONDS", 900)))


def renew_run_lease(run_id: str, task_id: str) -> bool:
    """Renew only the lease owned by the still-running delivery."""
    return bool(Run.objects.filter(
        pk=run_id, task_id=task_id, status=Run.Status.RUNNING,
    ).update(lease_expires_at=_lease_deadline()))


class RunLeaseHeartbeat:
    """Renew a worker lease without retaining graph or parameter content in the thread."""

    def __init__(self, run_id: str, task_id: str):
        self.run_id = run_id
        self.task_id = task_id
        self.stop = Event()
        self.thread: Thread | None = None

    def __enter__(self):
        interval = float(getattr(settings, "RUN_HEARTBEAT_SECONDS", 30))
        if interval > 0:
            self.thread = Thread(
                target=self._loop, args=(interval,), daemon=True,
                name=f"run-lease-{self.run_id}",
            )
            self.thread.start()
        return self

    def _loop(self, interval: float) -> None:
        close_old_connections()
        try:
            while not self.stop.wait(interval):
                if not renew_run_lease(self.run_id, self.task_id):
                    break
        except Exception as exc:
            log_sanitized_exception(
                logger, "Lease heartbeat failed run_id=%s task_id=%s",
                self.run_id, self.task_id or "unassigned", exc=exc,
            )
        finally:
            close_old_connections()

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=2)


def _runner_environment() -> dict[str, str]:
    """Give the algorithm child a usable runtime without application credentials."""
    return {name: value for name, value in os.environ.items() if name.upper() in _RUNNER_ENV_ALLOWLIST}


def start_algorithm_subprocess(run: Run, request_path: Path, result_path: Path) -> subprocess.Popen:
    """Start one isolated calculation process; the reusable Celery worker only supervises it."""
    return subprocess.Popen(
        [sys.executable, "-m", "learning.job_runner", str(request_path), str(result_path)],
        cwd=settings.BASE_DIR,
        env=_runner_environment(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
    )


def _current_status(run_id: str) -> str:
    return Run.objects.filter(pk=run_id).values_list("status", flat=True).first() or EXPIRED_STATE


def _complete_run(run_id: str, computed: dict) -> str:
    completed = Run.objects.filter(pk=run_id, status=Run.Status.RUNNING).update(
        result=computed, status=Run.Status.COMPLETED, error={},
        finished_at=timezone.now(), lease_expires_at=None,
    )
    return Run.Status.COMPLETED if completed else _current_status(run_id)


def _fail_run(run_id: str, terminal_error: dict) -> str:
    failed = Run.objects.filter(pk=run_id, status=Run.Status.RUNNING).update(
        status=Run.Status.FAILED, error=terminal_error, result={},
        finished_at=timezone.now(), lease_expires_at=None,
    )
    return Run.Status.FAILED if failed else _current_status(run_id)


def _execute_in_process(run: Run) -> str:
    """Deterministic eager/test path; production delegates computation to an isolated child."""
    with RunLeaseHeartbeat(str(run.id), run.task_id):
        try:
            computed = execute_algorithm(run.algorithm, run.graph, run.resolved_parameters, seed=run.seed)
        except AlgorithmInputError as exc:
            return _fail_run(str(run.id), exc.as_dict())
        except Exception as exc:
            log_sanitized_exception(
                logger,
                "Unexpected algorithm failure run_id=%s task_id=%s algorithm=%s",
                str(run.id), run.task_id or "unassigned", run.algorithm, exc=exc,
            )
            return _fail_run(str(run.id), {
                "code": "algorithm_failure", "message": "算法执行失败，请检查输入或联系教师。", "path": "",
            })
    return _complete_run(str(run.id), computed)


def _terminate_child(child: subprocess.Popen) -> None:
    if child.poll() is not None:
        return
    child.terminate()
    try:
        child.wait(timeout=float(getattr(settings, "RUN_CHILD_TERMINATE_GRACE_SECONDS", 5)))
    except subprocess.TimeoutExpired:
        child.kill()
        child.wait(timeout=2)


def _execute_isolated(run: Run) -> str:
    run_id = str(run.id)
    try:
        with tempfile.TemporaryDirectory(prefix=f"sna-run-{run.id}-") as directory:
            request_path = Path(directory) / "request.json"
            result_path = Path(directory) / "result.json"
            request_path.write_text(json.dumps({
                "run_id": run_id,
                "task_id": run.task_id or "unassigned",
                "algorithm": run.algorithm,
                "graph": run.graph,
                "parameters": run.resolved_parameters,
                "seed": run.seed,
            }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            child = start_algorithm_subprocess(run, request_path, result_path)
            monitor_seconds = max(0.0, float(getattr(settings, "RUN_MONITOR_SECONDS", 1)))
            while True:
                return_code = child.poll()
                current = _current_status(run_id)
                if current != Run.Status.RUNNING:
                    if return_code is None:
                        _terminate_child(child)
                    return current
                if return_code is not None:
                    break
                if not renew_run_lease(run_id, run.task_id):
                    _terminate_child(child)
                    return _current_status(run_id)
                time.sleep(monitor_seconds)
            if _current_status(run_id) != Run.Status.RUNNING:
                return _current_status(run_id)
            if not result_path.is_file():
                raise RuntimeError("isolated algorithm process produced no result envelope")
            envelope = json.loads(result_path.read_text(encoding="utf-8"))
            if envelope.get("ok") is True and isinstance(envelope.get("result"), dict):
                return _complete_run(run_id, envelope["result"])
            terminal_error = envelope.get("error")
            if not isinstance(terminal_error, dict):
                raise RuntimeError("isolated algorithm process produced an invalid result envelope")
            return _fail_run(run_id, terminal_error)
    except Exception as exc:
        log_sanitized_exception(
            logger,
            "Isolated algorithm worker failed run_id=%s task_id=%s algorithm=%s",
            run_id, run.task_id or "unassigned", run.algorithm, exc=exc,
        )
        return _fail_run(run_id, {
            "code": "algorithm_failure", "message": "算法执行失败，请检查输入或联系教师。", "path": "",
        })


@shared_task
def execute_run_job(run_id: str) -> str:
    """Execute one persisted run; terminal completion is written with the result atomically."""
    now = timezone.now()
    claimed = Run.objects.filter(
        pk=run_id, status=Run.Status.PENDING, expires_at__gt=now,
    ).update(
        status=Run.Status.RUNNING, started_at=now, lease_expires_at=_lease_deadline(), error={},
    )
    if not claimed:
        return _current_status(run_id)
    run = Run.objects.get(pk=run_id)
    if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
        return _execute_in_process(run)
    return _execute_isolated(run)


@shared_task
def cleanup_expired_runs() -> int:
    """Permanently remove expired anonymous graph inputs, parameters, and results."""
    now = timezone.now()
    deleted, _ = Run.objects.filter(expires_at__lte=now).delete()
    lease = timedelta(seconds=int(getattr(settings, "RUN_LEASE_SECONDS", 900)))
    Run.objects.filter(status=Run.Status.RUNNING).filter(
        Q(lease_expires_at__lte=now) |
        Q(lease_expires_at__isnull=True, started_at__lte=now - lease)
    ).update(
        status=Run.Status.FAILED,
        error={"code": "worker_lease_expired", "message": "任务执行超时，请重新提交。", "path": ""},
        result={},
        finished_at=now,
        lease_expires_at=None,
    )
    pending_cutoff = now - timedelta(seconds=int(getattr(settings, "PENDING_DELIVERY_SECONDS", 120)))
    stale_ids = list(Run.objects.filter(
        status=Run.Status.PENDING, queued_at__lte=pending_cutoff,
        expires_at__gt=now,
    ).order_by("queued_at").values_list("pk", flat=True)[:100])
    for run_id in stale_ids:
        claimed = Run.objects.filter(
            pk=run_id, status=Run.Status.PENDING, queued_at__lte=pending_cutoff,
            expires_at__gt=now,
        ).update(queued_at=now, requeue_count=F("requeue_count") + 1)
        if not claimed:
            continue
        run = Run.objects.only("id", "task_id", "algorithm").get(pk=run_id)
        try:
            execute_run_job.apply_async(
                args=[str(run.id)], task_id=run.task_id, queue=queue_for_algorithm(run.algorithm),
            )
        except Exception as exc:
            log_sanitized_exception(
                logger, "Pending delivery recovery failed run_id=%s task_id=%s algorithm=%s",
                str(run.id), run.task_id or "unassigned", run.algorithm, exc=exc,
            )
    return deleted
