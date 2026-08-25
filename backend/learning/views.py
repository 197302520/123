"""Anonymous read-only course API plus anonymous laboratory job contracts."""
from __future__ import annotations

from typing import Any

from django.http import Http404
from django.db.models import Q
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .algorithms import AlgorithmInputError, execute_algorithm
from .algorithms.graph import normalize_graph
from .contracts import ALGORITHM_REGISTRY, GraphSpec, RunResult
from .models import Case, CourseModule, PublishStatus, Run


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
    normalized_nodes: list[dict[str, str]] = []
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
            normalized_nodes.append({"id": node_id, "label": label if isinstance(label, str) else node_id})
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
        elif isinstance(source, str) and isinstance(target, str):
            normalized_edges.append({"source": source, "target": target, "weight": float(weight)})
    if errors:
        return None, errors
    try:
        normalized = normalize_graph({"directed": directed, "nodes": normalized_nodes, "edges": normalized_edges})
    except AlgorithmInputError as exc:
        return None, [{"path": exc.path, "message": str(exc)}]
    return normalized, []


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

    def post(self, request: Request) -> Response:
        graph, errors = graph_validation(request.data)
        if errors:
            return Response({"valid": False, "errors": errors}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"valid": True, "errors": [], "graph": graph})


class AlgorithmListView(APIView):
    def get(self, request: Request) -> Response:
        return Response(ALGORITHM_REGISTRY)


class RunListView(APIView):
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        if not isinstance(request.data, dict):
            return Response({"detail": "请求体必须是 JSON 对象。"}, status=status.HTTP_400_BAD_REQUEST)
        algorithm = request.data.get("algorithm")
        graph, errors = graph_validation(request.data.get("graph"))
        parameters = request.data.get("parameters", {})
        if errors:
            return Response({"valid": False, "errors": errors}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(parameters, dict):
            return Response({"detail": "parameters 必须是 JSON 对象。"}, status=status.HTTP_400_BAD_REQUEST)
        seed = request.data.get("seed")
        if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
            return Response({"detail": "seed 必须是整数。"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            result = execute_algorithm(algorithm, graph, parameters, seed=seed)
        except AlgorithmInputError as exc:
            return Response({"error": exc.as_dict()}, status=status.HTTP_400_BAD_REQUEST)
        run = Run.objects.create(
            algorithm=algorithm,
            graph=graph,
            parameters=parameters,
            seed=seed,
            status=Run.Status.COMPLETED,
            result=result,
        )
        return Response({"id": str(run.id), "status": run.status, "algorithm": run.algorithm, "seed": run.seed}, status=status.HTTP_201_CREATED)


class RunStatusView(APIView):
    def get(self, request: Request, run_id: str) -> Response:
        try:
            run = active_runs().get(pk=run_id)
        except (Run.DoesNotExist, ValueError) as exc:
            raise Http404 from exc
        return Response({"id": str(run.id), "status": run.status, "algorithm": run.algorithm, "seed": run.seed})


class RunResultView(APIView):
    def get(self, request: Request, run_id: str) -> Response:
        try:
            run = active_runs().get(pk=run_id)
        except (Run.DoesNotExist, ValueError) as exc:
            raise Http404 from exc
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

    def post(self, request: Request) -> Response:
        if not isinstance(request.data, dict):
            return Response({"detail": "请求体必须是 JSON 对象。"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            run = active_runs().get(pk=request.data.get("run_id"))
        except (Run.DoesNotExist, ValueError, TypeError) as exc:
            raise Http404 from exc
        return Response({
            "run_id": str(run.id),
            "format": "html",
            "content": f"<h1>社会网络分析报告</h1><p>算法：{run.algorithm}</p>",
        }, status=status.HTTP_201_CREATED)
