"""Background execution and maintenance tasks for anonymous laboratory records."""
from celery import shared_task
from django.db import transaction
from django.utils import timezone

from .algorithms import AlgorithmInputError, execute_algorithm
from .models import Run


@shared_task
def execute_run_job(run_id: str) -> str:
    """Execute one persisted run; terminal completion is written with the result atomically."""
    with transaction.atomic():
        run = Run.objects.select_for_update().get(pk=run_id)
        if run.status != Run.Status.PENDING:
            return run.status
        run.status = Run.Status.RUNNING
        run.started_at = timezone.now()
        run.error = {}
        run.save(update_fields=["status", "started_at", "error"])
    try:
        computed = execute_algorithm(run.algorithm, run.graph, run.resolved_parameters, seed=run.seed)
    except AlgorithmInputError as exc:
        terminal_error = exc.as_dict()
    except Exception:
        terminal_error = {"code": "algorithm_failure", "message": "算法执行失败，请检查输入或联系教师。", "path": ""}
    else:
        with transaction.atomic():
            current = Run.objects.select_for_update().get(pk=run_id)
            if current.status == Run.Status.CANCELLED:
                return current.status
            current.result = computed
            current.status = Run.Status.COMPLETED
            current.finished_at = timezone.now()
            current.save(update_fields=["result", "status", "finished_at"])
        return Run.Status.COMPLETED
    Run.objects.filter(pk=run_id).exclude(status=Run.Status.CANCELLED).update(
        status=Run.Status.FAILED, error=terminal_error, result={}, finished_at=timezone.now(),
    )
    return Run.Status.FAILED


@shared_task
def cleanup_expired_runs() -> int:
    """Permanently remove expired anonymous graph inputs, parameters, and results."""
    deleted, _ = Run.objects.filter(expires_at__lte=timezone.now()).delete()
    return deleted
