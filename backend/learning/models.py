"""Teacher-managed course content and anonymous run records."""
from __future__ import annotations

import uuid

from django.db import models


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
        COMPLETED = "completed", "已完成"
        FAILED = "failed", "失败"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    algorithm = models.CharField(max_length=100)
    graph = models.JSONField()
    parameters = models.JSONField(default=dict)
    seed = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    result = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
