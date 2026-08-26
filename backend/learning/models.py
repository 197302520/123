"""Teacher-managed course content and anonymous run records."""
from __future__ import annotations

import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


def run_expiry_default():
    """Anonymous laboratory inputs are retained for no more than two hours."""
    return timezone.now() + timedelta(hours=2)


class PublishStatus(models.TextChoices):
    DRAFT = "draft", "草稿"
    PUBLISHED = "published", "已发布"


class CourseModule(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=120)
    summary = models.TextField()
    content = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(unique=True)
    status = models.CharField(max_length=16, choices=PublishStatus.choices, default=PublishStatus.DRAFT)

    class Meta:
        ordering = ["order"]

    def __str__(self) -> str:
        return self.title


class Dataset(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=160)
    provenance = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=16, choices=PublishStatus.choices, default=PublishStatus.DRAFT)

    def __str__(self) -> str:
        return self.title


class Case(models.Model):
    module = models.ForeignKey(CourseModule, on_delete=models.PROTECT, related_name="cases")
    dataset = models.ForeignKey(Dataset, on_delete=models.PROTECT, related_name="cases", null=True, blank=True)
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=160)
    summary = models.TextField()
    content = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=PublishStatus.choices, default=PublishStatus.DRAFT)

    def __str__(self) -> str:
        return self.title


class Run(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "等待中"
        RUNNING = "running", "运行中"
        COMPLETED = "completed", "已完成"
        FAILED = "failed", "失败"
        CANCELLED = "cancelled", "已取消"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    algorithm = models.CharField(max_length=100)
    graph = models.JSONField()
    parameters = models.JSONField(default=dict)
    resolved_parameters = models.JSONField(default=dict)
    seed = models.IntegerField(null=True, blank=True)
    algorithm_version = models.CharField(max_length=32, default="1.0")
    cache_key = models.CharField(max_length=64, blank=True, db_index=True)
    task_id = models.CharField(max_length=128, blank=True, db_index=True)
    cached_from = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="cache_hits")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    result = models.JSONField(default=dict, blank=True)
    error = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(default=run_expiry_default, db_index=True)


class AuditRecord(models.Model):
    """Minimal append-only trace for authenticated teacher content mutations."""

    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=32)
    entity_type = models.CharField(max_length=64)
    entity_id = models.CharField(max_length=160)
    changes = models.JSONField(default=dict, blank=True)
    source_ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
