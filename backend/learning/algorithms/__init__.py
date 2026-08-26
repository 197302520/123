from __future__ import annotations

from typing import Any

import networkx as nx

from .classical import run_classical
from .community import run_community
from .dynamics import run_dynamic, run_opinion
from .embeddings import run_embedding
from .errors import AlgorithmInputError
from .exports import export_graph
from .graph import coerce_finite_float, normalize_graph
from .prediction import run_link_prediction, run_robustness
from .registry import REGISTRY_BY_KEY, get_registry
from .results import overlay, result, table
from .text import extract_chinese_graph


CLASSICAL = {
    "graph.validate", "topology.summary", "paths.floyd", "clustering.coefficient",
    "model.er", "model.ws", "model.ba", "centrality.degree", "centrality.closeness",
    "centrality.betweenness", "centrality.eigenvector", "centrality.pagerank",
    "centrality.hits", "centralization.degree",
}
COMMUNITIES = {
    "community.kernighan_lin", "community.agglomerative", "community.divisive",
    "community.girvan_newman", "community.fast_newman", "community.louvain",
    "community.leiden", "community.lpa", "community.cpm", "community.lfm", "community.slpa",
}
LINK_PREDICTION = {
    "link_prediction.common_neighbors", "link_prediction.jaccard",
    "link_prediction.adamic_adar", "link_prediction.resource_allocation",
}
OPINION = {"opinion.degroot", "opinion.friedkin_johnsen", "opinion.deffuant", "opinion.hk"}
EMBEDDINGS = {"embedding.ae", "embedding.cnn", "embedding.gcn", "embedding.gat"}


def _networkx_guard(function: Any, *args: Any) -> dict[str, Any]:
    try:
        return function(*args)
    except AlgorithmInputError:
        raise
    except nx.PowerIterationFailedConvergence as exc:
        raise AlgorithmInputError(f"迭代算法未收敛：{exc}", code="algorithm_failure", path="parameters.max_iterations") from exc
    except nx.NetworkXException as exc:
        raise AlgorithmInputError(f"图结构无法由该算法处理：{exc}", code="algorithm_failure", path="graph") from exc


def _resolve_parameters(spec: dict[str, Any], supplied: Any) -> dict[str, Any]:
    if not isinstance(supplied, dict):
        raise AlgorithmInputError("parameters 必须是 JSON 对象。", path="parameters")
    definitions = spec["parameters"]
    unknown = sorted(set(supplied) - set(definitions))
    if unknown:
        raise AlgorithmInputError(f"未知参数：{', '.join(unknown)}。", path=f"parameters.{unknown[0]}")
    resolved = {name: supplied.get(name, definition["default"]) for name, definition in definitions.items()}
    for name, value in resolved.items():
        definition = definitions[name]
        kind = definition["type"]
        finite_number = coerce_finite_float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None
        valid = {
            "integer": isinstance(value, int) and not isinstance(value, bool),
            "number": finite_number is not None,
            "string": isinstance(value, str),
            "object": isinstance(value, dict),
            "array": isinstance(value, list),
        }.get(kind, True)
        if not valid:
            message = f"参数 {name} 必须是有限数值。" if kind == "number" else f"参数 {name} 必须是 {kind} 类型。"
            raise AlgorithmInputError(message, path=f"parameters.{name}")
        if "minimum" in definition and value < definition["minimum"]:
            raise AlgorithmInputError(f"参数 {name} 不得小于 {definition['minimum']}。", path=f"parameters.{name}")
        if "maximum" in definition and value > definition["maximum"]:
            raise AlgorithmInputError(f"参数 {name} 不得大于 {definition['maximum']}。", path=f"parameters.{name}")
        if "choices" in definition and value not in definition["choices"]:
            raise AlgorithmInputError(f"参数 {name} 必须是 {definition['choices']} 之一。", path=f"parameters.{name}")
    return resolved


def execute_algorithm(
    algorithm: str,
    graph: Any,
    parameters: Any | None = None,
    *,
    seed: int | None = None,
) -> dict[str, Any]:
    normalized, params, spec, effective_seed = prepare_algorithm_request(
        algorithm, graph, parameters, seed=seed,
    )

    if algorithm in CLASSICAL:
        bundle = _networkx_guard(run_classical, algorithm, normalized, params, effective_seed)
    elif algorithm in COMMUNITIES:
        bundle = _networkx_guard(run_community, algorithm, normalized, params, effective_seed)
    elif algorithm == "robustness.attack":
        bundle = _networkx_guard(run_robustness, normalized, params, effective_seed)
    elif algorithm in LINK_PREDICTION:
        bundle = _networkx_guard(run_link_prediction, algorithm, normalized, params, effective_seed)
    elif algorithm in OPINION:
        bundle = _networkx_guard(run_opinion, algorithm, normalized, params, effective_seed)
    elif algorithm == "community.dynamic":
        bundle = _networkx_guard(run_dynamic, normalized, params, effective_seed, spec["limits"])
    elif algorithm in EMBEDDINGS:
        bundle = _networkx_guard(run_embedding, algorithm, normalized, params, effective_seed)
    elif algorithm == "text.extract":
        extracted = extract_chinese_graph(
            params["text"], method=params["method"], embedding=params["embedding"],
            seed=effective_seed, model_path=params["model_path"] or None,
        )
        bundle = {
            "tables": [table("entities", "实体候选", extracted["entities"]), table("relations", "关系候选", extracted["relations"])],
            "overlays": [overlay("extracted_graph", nodes=extracted["graph"]["nodes"], edges=extracted["graph"]["edges"])],
            "provenance": {"extraction": extracted},
        }
    elif algorithm == "export.graph":
        exported = export_graph(normalized, params["format"])
        bundle = {"tables": [table("export", "图导出", [exported])], "provenance": {"export_format": exported["format"]}}
    else:  # pragma: no cover - registry and dispatch sets are reviewed together.
        raise AlgorithmInputError(f"算法 {algorithm} 尚未绑定执行器。", code="implementation_unavailable", path="algorithm")

    return result(
        algorithm,
        spec["version"],
        normalized,
        params,
        seed,
        tables=bundle.get("tables"),
        overlays=bundle.get("overlays"),
        charts=bundle.get("charts"),
        warnings=bundle.get("warnings"),
        provenance={"effective_seed": effective_seed, **bundle.get("provenance", {})},
    )


def prepare_algorithm_request(
    algorithm: str,
    graph: Any,
    parameters: Any | None = None,
    *,
    seed: int | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], int]:
    """Validate and normalize the exact inputs used by execution and cache keys."""
    if algorithm not in REGISTRY_BY_KEY:
        raise AlgorithmInputError(f"不支持的算法：{algorithm}。", code="unsupported_algorithm", path="algorithm")
    if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
        raise AlgorithmInputError("seed 必须是整数或 null。", path="seed")
    spec = REGISTRY_BY_KEY[algorithm]
    normalized = normalize_graph(graph)
    graph_type = "directed" if normalized["directed"] else "undirected"
    if graph_type not in spec["supported_graph_types"]:
        expected = "无向图" if spec["supported_graph_types"] == ["undirected"] else "/".join(spec["supported_graph_types"])
        raise AlgorithmInputError(f"算法 {algorithm} 仅支持{expected}。", code="unsupported_graph_type", path="graph.directed")
    if len(normalized["nodes"]) > spec["limits"]["max_nodes"]:
        raise AlgorithmInputError(f"算法 {algorithm} 最多支持 {spec['limits']['max_nodes']} 个节点。", code="limit_exceeded", path="graph.nodes")
    if len(normalized["edges"]) > spec["limits"]["max_edges"]:
        raise AlgorithmInputError(f"算法 {algorithm} 最多支持 {spec['limits']['max_edges']} 条边。", code="limit_exceeded", path="graph.edges")
    params = _resolve_parameters(spec, {} if parameters is None else parameters)
    effective_seed = 0 if seed is None else seed
    return normalized, params, spec, effective_seed


__all__ = ["AlgorithmInputError", "execute_algorithm", "get_registry", "prepare_algorithm_request"]
