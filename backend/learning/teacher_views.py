from __future__ import annotations

import re
from typing import Any

from django.db import IntegrityError, transaction
from django.http import Http404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAdminUser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .middleware import client_ip
from .models import AuditRecord, Case, CourseModule, Dataset, PublishStatus


@method_decorator(ensure_csrf_cookie, name="dispatch")
class TeacherSessionView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]

    def get(self, request: Request) -> Response:
        return Response({"authenticated": True, "username": request.user.get_username()})


def _teacher_case_payload(case: Case) -> dict[str, Any]:
    return {
        "slug": case.slug, "title": case.title, "summary": case.summary, "content": case.content,
        "module": case.module.slug, "dataset": case.dataset.slug if case.dataset else None, "status": case.status,
    }


def _case_fields(data: Any, *, partial: bool) -> tuple[dict[str, Any], dict[str, str]]:
    if not isinstance(data, dict):
        return {}, {"detail": "请求体必须是 JSON 对象。"}
    values: dict[str, Any] = {}
    errors: dict[str, str] = {}
    for name, maximum in (("slug", 50), ("title", 160), ("summary", 10_000), ("content", 100_000)):
        if name in data:
            value = data[name]
            if not isinstance(value, str) or (name != "content" and not value.strip()) or len(value) > maximum:
                errors[name] = f"{name} 必须是有效文本。"
            else:
                values[name] = value.strip() if name != "content" else value
        elif not partial and name in {"slug", "title", "summary"}:
            errors[name] = f"{name} 为必填项。"
    if "slug" in values and not re.fullmatch(r"[-a-zA-Z0-9_]+", values["slug"]):
        errors["slug"] = "slug 只能包含字母、数字、连字符和下划线。"
    if "status" in data:
        if data["status"] not in PublishStatus.values:
            errors["status"] = "status 必须是 draft 或 published。"
        else:
            values["status"] = data["status"]
    elif not partial:
        values["status"] = PublishStatus.DRAFT
    if "module" in data:
        try:
            values["module"] = CourseModule.objects.get(slug=data["module"])
        except (CourseModule.DoesNotExist, TypeError):
            errors["module"] = "课程模块不存在。"
    elif not partial:
        errors["module"] = "module 为必填项。"
    if "dataset" in data:
        if data["dataset"] in (None, ""):
            values["dataset"] = None
        else:
            try:
                values["dataset"] = Dataset.objects.get(slug=data["dataset"])
            except (Dataset.DoesNotExist, TypeError):
                errors["dataset"] = "数据集不存在。"
    return values, errors


class TeacherCaseListView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]

    def post(self, request: Request) -> Response:
        values, errors = _case_fields(request.data, partial=False)
        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)
        if Case.objects.filter(slug=values["slug"]).exists():
            return Response({"errors": {"slug": "slug 已存在。"}}, status=status.HTTP_400_BAD_REQUEST)
        try:
            with transaction.atomic():
                case = Case.objects.create(**values)
                AuditRecord.objects.create(
                    actor=request.user, action="create", entity_type="case", entity_id=case.slug,
                    changes={"changed_fields": sorted(values), "status": case.status}, source_ip=client_ip(request),
                )
        except IntegrityError:
            return Response({"errors": {"slug": "slug 已存在。"}}, status=status.HTTP_409_CONFLICT)
        return Response(_teacher_case_payload(case), status=status.HTTP_201_CREATED)


class TeacherCaseDetailView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]

    def patch(self, request: Request, slug: str) -> Response:
        values, errors = _case_fields(request.data, partial=True)
        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)
        try:
            with transaction.atomic():
                try:
                    case = Case.objects.select_for_update().select_related("module", "dataset").get(slug=slug)
                except Case.DoesNotExist as exc:
                    raise Http404 from exc
                if "slug" in values and values["slug"] != slug and Case.objects.filter(slug=values["slug"]).exists():
                    return Response({"errors": {"slug": "slug 已存在。"}}, status=status.HTTP_400_BAD_REQUEST)
                for name, value in values.items():
                    setattr(case, name, value)
                if values:
                    case.save(update_fields=sorted(values))
                    AuditRecord.objects.create(
                        actor=request.user, action="update", entity_type="case", entity_id=case.slug,
                        changes={"changed_fields": sorted(values), "status": case.status}, source_ip=client_ip(request),
                    )
        except IntegrityError:
            return Response({"errors": {"slug": "slug 已存在。"}}, status=status.HTTP_409_CONFLICT)
        return Response(_teacher_case_payload(case))
