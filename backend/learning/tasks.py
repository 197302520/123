"""Background maintenance tasks for anonymous laboratory records."""
from celery import shared_task
from django.utils import timezone

from .models import Run


@shared_task
def cleanup_expired_runs() -> int:
    """Permanently remove expired anonymous graph inputs, parameters, and results."""
    deleted, _ = Run.objects.filter(expires_at__lte=timezone.now()).delete()
    return deleted
