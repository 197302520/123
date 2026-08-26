"""Public learning and anonymous laboratory APIs."""
from __future__ import annotations

import logging
from typing import Any

from celery import current_app
from django.conf import settings
from django.db import transaction
from django.http import Http404, HttpResponse, JsonResponse
from django.db.models import Q
from django.utils import timezone
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .algorithms import AlgorithmInputError, prepare_algorithm_request
from .algorithms.graph import coerce_finite_float, normalize_graph
from .contracts import ALGORITHM_REGISTRY, GraphSpec, RunResult
from .models import Case, CourseModule, PublishStatus, Run
from .logging_utils import log_sanitized_exception
from .reports import build_report_bundle, render_report_html
from .run_service import active_cached_run, build_cache_key
from .safe_imports import UnsafeUploadError, parse_uploaded_graph
from .tasks import execute_run_job, queue_for_algorithm
from .throttles import (
    AlgorithmIPThrottle, AlgorithmSessionThrottle,
    PublicOperationIPThrottle, PublicOperationSessionThrottle,
)


logger = logging.getLogger(__name__)


def health(_request):
    """Lightweight liveness probe that traverses the deployed HTTP application stack."""
    return JsonResponse({"status": "ok"})


def public_modules():
    return CourseModule.objects.filter(status=PublishStatus.PUBLISHED)


def public_cases():
    return Case.objects.filter(
        status=PublishStatus.PUBLISHED,
        module__status=PublishStatus.PUBLISHED,
    ).filter(
        Q(dataset__isnull=True) | Q(dataset__status=PublishStatus.PUBLISHED)
    )


def active_runs():
    """Expired anonymous inputs are never visible while queued cleanup catches up."""
    return Run.objects.filter(expires_at__gt=timezone.now())


def module_payload(module: CourseModule, *, detail: bool) -> dict[str, Any]:
    payload = {"slug": module.slug, "title": module.title, "summary": module.summary, "order": module.order}
    if detail:
        payload["content"] = module.content
    return payload


def case_payload(case: Case, *, detail: bool) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "slug": case.slug,
        "title": case.title,
        "summary": case.summary,
        "module": case.module.slug,
    }
    if detail:
        payload["content"] = case.content
        payload["dataset"] = None if case.dataset is None else {
            "slug": case.dataset.slug,
            "title": case.dataset.title,
            "provenance": case.dataset.provenance,
            "metadata": case.dataset.metadata,
        }
    return payload


def graph_validation(payload: Any) -> tuple[GraphSpec | None, list[dict[str, str]]]:
    if not isinstance(payload, dict):
        return None, [{"path": "", "message": "图必须是对象。"}]
    directed = payload.get("directed")
    nodes = payload.get("nodes")
    edges = payload.get("edges")
    if not isinstance(directed, bool):
        return None, [{"path": "directed", "message": "directed 必须是布尔值。"}]
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return None, [{"path": "", "message": "nodes 和 edges 必须是数组。"}]
    normalized_nodes: list[dict[str, Any]] = []
    node_ids: set[str] = set()
    errors: list[dict[str, str]] = []
    for index, node in enumerate(nodes):
        node_id = node.get("id") if isinstance(node, dict) else None
        if not isinstance(node_id, str) or not node_id:
            errors.append({"path": f"nodes[{index}].id", "message": "节点 id 必须是非空字符串。"})
        elif node_id in node_ids:
            errors.append({"path": f"nodes[{index}].id", "message": f"节点 '{node_id}' 重复。"})
        else:
            node_ids.add(node_id)
            label = node.get("label", node_id)
            normalized_node: dict[str, Any] = {"id": node_id, "label": label if isinstance(label, str) else node_id}
            if "attributes" in node:
                if isinstance(node["attributes"], dict):
                    normalized_node["attributes"] = node["attributes"]
                else:
                    errors.append({"path": f"nodes[{index}].attributes", "message": "节点 attributes 必须是对象。"})
            normalized_nodes.append(normalized_node)
    normalized_edges: list[dict[str, Any]] = []
    for index, edge in enumerate(edges):
        source = edge.get("source") if isinstance(edge, dict) else None
        target = edge.get("target") if isinstance(edge, dict) else None
        if not isinstance(source, str) or source not in node_ids:
            errors.append({"path": f"edges[{index}].source", "message": f"节点 '{source}' 不存在。"})
        if not isinstance(target, str) or target not in node_ids:
            errors.append({"path": f"edges[{index}].target", "message": f"节点 '{target}' 不存在。"})
        weight = edge.get("weight", 1) if isinstance(edge, dict) else 1
        if isinstance(weight, bool) or not isinstance(weight, (int, float)):
            errors.append({"path": f"edges[{index}].weight", "message": "边权重必须是数值。"})
        else:
            normalized_weight = coerce_finite_float(weight)
            if normalized_weight is None:
                errors.append({"path": f"edges[{index}].weight", "message": "边权重必须是有限数值。"})
            elif isinstance(source, str) and isinstance(target, str):
                normalized_edges.append({"source": source, "target": target, "weight": normalized_weight})
    if errors:
        return None, errors
    try:
        normalized = normalize_graph({"directed": directed, "nodes": normalized_nodes, "edges": normalized_edges})
    except AlgorithmInputError as exc:
        return None, [{"path": exc.path, "message": str(exc)}]
    return normalized, []


def graph_shape_error(payload: Any) -> dict[str, str] | None:
    if not isinstance(payload, dict):
        return None
    nodes, edges = payload.get("nodes"), payload.get("edges")
    if isinstance(nodes, list) and len(nodes) > int(getattr(settings, "PUBLIC_MAX_NODES", 2_000)):
        return {"code": "limit_exceeded", "message": "公开图最多支持 2,000 个节点。", "path": "nodes"}
    if isinstance(edges, list) and len(edges) > int(getattr(settings, "PUBLIC_MAX_EDGES", 20_000)):
        return {"code": "limit_exceeded", "message": "公开图最多支持 20,000 条边。", "path": "edges"}
    return None


def run_payload(run: Run) -> dict[str, Any]:
    return {"id": str(run.id), "status": run.status, "algorithm": run.algorithm, "seed": run.seed}


class ModuleListView(APIView):
    def get(self, request: Request) -> Response:
        return Response([module_payload(module, detail=False) for module in public_modules()])


class ModuleDetailView(APIView):
    def get(self, request: Request, slug: str) -> Response:
        try:
            module = public_modules().get(slug=slug)
        except CourseModule.DoesNotExist as exc:
            raise Http404 from exc
        return Response(module_payload(module, detail=True))


class CaseListView(APIView):
    def get(self, request: Request) -> Response:
        return Response([case_payload(case, detail=False) for case in public_cases().select_related("module")])


class CaseDetailView(APIView):
    def get(self, request: Request, slug: str) -> Response:
        try:
            case = public_cases().select_related("module", "dataset").get(slug=slug)
        except Case.DoesNotExist as exc:
            raise Http404 from exc
        return Response(case_payload(case, detail=True))


class GraphValidationView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [PublicOperationIPThrottle, PublicOperationSessionThrottle]

    def post(self, request: Request) -> Response:
        limit_error = graph_shape_error(request.data)
        if limit_error:
            return Response({"valid": False, "error": limit_error, "errors": []}, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
        graph, errors = graph_validation(request.data)
        if errors:
            return Response({"valid": False, "errors": errors}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"valid": True, "errors": [], "graph": graph})


class AlgorithmListView(APIView):
    def get(self, request: Request) -> Response:
        return Response(ALGORITHM_REGISTRY)


class RunListView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AlgorithmIPThrottle, AlgorithmSessionThrottle]

    def post(self, request: Request) -> Response:
        if not isinstance(request.data, dict):
            return Response({"detail": "请求体必须是 JSON 对象。"}, status=status.HTTP_400_BAD_REQUEST)
        algorithm = request.data.get("algorithm")
        raw_graph = request.data.get("graph")
        limit_error = graph_shape_error(raw_graph)
        if limit_error:
            return Response({"error": limit_error}, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
        graph, errors = graph_validation(raw_graph)
        parameters = request.data.get("parameters", {})
        if errors:
            return Response({"valid": False, "errors": errors}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(parameters, dict):
            return Response({"detail": "parameters 必须是 JSON 对象。"}, status=status.HTTP_400_BAD_REQUEST)
        seed = request.data.get("seed")
        if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
            return Response({"detail": "seed 必须是整数。"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            normalized, resolved, spec, _ = prepare_algorithm_request(algorithm, graph, parameters, seed=seed)
        except AlgorithmInputError as exc:
            return Response({"error": exc.as_dict()}, status=status.HTTP_400_BAD_REQUEST)
        cache_key = build_cache_key(
            algorithm=algorithm, version=spec["version"], graph=normalized,
            parameters=resolved, seed=seed,
        )
        cached = active_cached_run(cache_key)
        now = timezone.now()
        run = Run.objects.create(
            algorithm=algorithm,
            algorithm_version=spec["version"],
            graph=normalized,
            parameters=parameters,
            resolved_parameters=resolved,
            seed=seed,
            cache_key=cache_key,
            cached_from=cached,
            status=Run.Status.COMPLETED if cached else Run.Status.PENDING,
            result=cached.result if cached else {},
            started_at=now if cached else None,
            finished_at=now if cached else None,
        )
        if not cached:
            run.task_id = f"run-{run.id}"
            run.save(update_fields=["task_id"])
            if settings.CELERY_TASK_ALWAYS_EAGER:
                execute_run_job(str(run.id))
                run.refresh_from_db()
                if run.status == Run.Status.FAILED:
                    return Response({"error": run.error}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:
                    execute_run_job.apply_async(
                        args=[str(run.id)], task_id=run.task_id, queue=queue_for_algorithm(algorithm),
                    )
                except Exception as exc:
                    log_sanitized_exception(
                        logger,
                        "Queue submission failed run_id=%s task_id=%s algorithm=%s",
                        str(run.id), run.task_id, run.algorithm, exc=exc,
                    )
                    # Keep a truthful pending state. Beat retries this same task id after the
                    # bounded delivery interval, so a transient broker outage is recoverable.
        return Response(run_payload(run), status=status.HTTP_201_CREATED)


class RunCancelView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [PublicOperationIPThrottle, PublicOperationSessionThrottle]

    def post(self, request: Request, run_id: str) -> Response:
        try:
            with transaction.atomic():
                run = Run.objects.select_for_update().filter(expires_at__gt=timezone.now()).get(pk=run_id)
                if run.status == Run.Status.CANCELLED:
                    if not run.cancel_revoke_pending or not run.task_id:
                        return Response(run_payload(run))
                elif run.status not in {Run.Status.PENDING, Run.Status.RUNNING}:
                    return Response(run_payload(run), status=status.HTTP_409_CONFLICT)
                else:
                    needs_pending_revoke = run.status == Run.Status.PENDING and bool(run.task_id)
                    run.status = Run.Status.CANCELLED
                    run.result = {}
                    run.error = {"code": "cancelled", "message": "任务已取消。", "path": ""}
                    run.finished_at = timezone.now()
                    run.lease_expires_at = None
                    run.cancel_revoke_pending = needs_pending_revoke
                    run.save(update_fields=[
                        "status", "result", "error", "finished_at", "lease_expires_at", "cancel_revoke_pending",
                    ])
                task_id = run.task_id
                needs_pending_revoke = run.cancel_revoke_pending
        except (Run.DoesNotExist, ValueError) as exc:
            raise Http404 from exc
        if task_id and needs_pending_revoke:
            try:
                current_app.control.revoke(task_id, terminate=False)
            except Exception as exc:
                log_sanitized_exception(
                    logger, "Queue revoke failed run_id=%s task_id=%s algorithm=%s",
                    str(run.id), task_id, run.algorithm, exc=exc,
                )
                return Response({
                    **run_payload(run),
                    "error": {"code": "cancel_delivery_failed", "message": "任务已标记取消，但未能联系队列，请重试取消。"},
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            Run.objects.filter(pk=run.id, status=Run.Status.CANCELLED).update(cancel_revoke_pending=False)
            run.cancel_revoke_pending = False
        return Response(run_payload(run))


class RunStatusView(APIView):
    def get(self, request: Request, run_id: str) -> Response:
        try:
            run = active_runs().get(pk=run_id)
        except (Run.DoesNotExist, ValueError) as exc:
            raise Http404 from exc
        return Response(run_payload(run))


class RunResultView(APIView):
    def get(self, request: Request, run_id: str) -> Response:
        try:
            run = active_runs().get(pk=run_id)
        except (Run.DoesNotExist, ValueError) as exc:
            raise Http404 from exc
        if run.status != Run.Status.COMPLETED or not run.result:
            return Response({"id": str(run.id), "status": run.status, "error": run.error}, status=status.HTTP_409_CONFLICT)
        stored = run.result
        result: RunResult = {
            "run_id": str(run.id),
            "status": run.status,
            "tables": stored.get("tables", []),
            "overlays": stored.get("overlays", []),
            "charts": stored.get("charts", []),
            "warnings": stored.get("warnings", []),
            "provenance": stored.get("provenance", {"algorithm": run.algorithm, "version": "1.0", "seed": run.seed}),
            "validation": stored.get("validation", {"valid": False, "errors": [], "graph": run.graph}),
        }
        return Response(result)


class ReportView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [PublicOperationIPThrottle, PublicOperationSessionThrottle]

    def post(self, request: Request) -> Response:
        if not isinstance(request.data, dict):
            return Response({"detail": "请求体必须是 JSON 对象。"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            run = active_runs().get(pk=request.data.get("run_id"))
        except (Run.DoesNotExist, ValueError, TypeError) as exc:
            raise Http404 from exc
        if run.status != Run.Status.COMPLETED or not run.result:
            return Response({"run_id": str(run.id), "status": run.status}, status=status.HTTP_409_CONFLICT)
        return Response({
            "run_id": str(run.id),
            "format": "html",
            "content": render_report_html(run),
            "download_url": f"/api/reports/{run.id}/bundle/",
        }, status=status.HTTP_201_CREATED)


class ReportBundleView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [PublicOperationIPThrottle, PublicOperationSessionThrottle]

    def get(self, request: Request, run_id: str) -> HttpResponse:
        try:
            run = active_runs().get(pk=run_id, status=Run.Status.COMPLETED)
        except (Run.DoesNotExist, ValueError) as exc:
            raise Http404 from exc
        if not run.result:
            return HttpResponse(status=409)
        response = HttpResponse(build_report_bundle(run), content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="sna-report-{run.id}.zip"'
        response["X-Content-Type-Options"] = "nosniff"
        return response


class GraphImportView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser]
    throttle_classes = [PublicOperationIPThrottle, PublicOperationSessionThrottle]

    def post(self, request: Request) -> Response:
        uploaded = request.FILES.get("file")
        if uploaded is None:
            return Response({"detail": "请选择要导入的图文件。"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            graph = parse_uploaded_graph(uploaded)
        except UnsafeUploadError as exc:
            return Response({"detail": str(exc)}, status=exc.status_code)
        limit_error = graph_shape_error(graph)
        if limit_error:
            return Response({"error": limit_error}, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
        return Response({"valid": True, "graph": graph, "errors": []})
