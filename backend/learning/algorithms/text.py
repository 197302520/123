from __future__ import annotations

import importlib.util
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

from .errors import AlgorithmInputError
from .graph import coerce_finite_float


SENTENCE_PATTERN = re.compile(r"[^。！？!?；;\n]+[。！？!?；;]?", re.UNICODE)
TOKEN_PATTERN = re.compile(r"[\u4e00-\u9fff]+|[A-Za-z]+(?:[-_][A-Za-z0-9]+)*|\d+(?:\.\d+)?", re.UNICODE)
RELATION_PATTERNS = [
    re.compile(r"(?P<source>[\u4e00-\u9fffA-Za-z0-9·]{2,16}?)(?:与|和)(?P<target>[\u4e00-\u9fffA-Za-z0-9·]{2,16}?)(?P<verb>签署|达成|建立|开展|联合)(?P<object>[^。！？!?；;]{0,16})"),
    re.compile(r"(?P<source>[\u4e00-\u9fffA-Za-z0-9·]{2,16}?)(?P<verb>投资了?|收购了?|支持|控股)(?P<target>[\u4e00-\u9fffA-Za-z0-9·]{2,16})(?=$|[。！？!?；;])"),
    re.compile(r"(?P<source>[\u4e00-\u9fffA-Za-z0-9·]{2,16}?)(?:向)(?P<target>[\u4e00-\u9fffA-Za-z0-9·]{2,16}?)(?P<verb>供应|提供|出售)(?P<object>[^。！？!?；;]{0,16})"),
]


def preprocess_chinese(text: str) -> dict[str, Any]:
    if not isinstance(text, str):
        raise AlgorithmInputError("text 必须是字符串。", path="parameters.text")
    normalized = unicodedata.normalize("NFKC", text).replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[\t \u3000]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized).strip()
    sentences = [match.group(0).strip() for match in SENTENCE_PATTERN.finditer(normalized) if match.group(0).strip()]
    tokens = TOKEN_PATTERN.findall(normalized)
    return {"normalized_text": normalized, "sentences": sentences, "tokens": tokens}


def _char_vector(value: str) -> Counter[str]:
    compact = re.sub(r"\s+", "", value)
    grams = [compact[index:index + 2] for index in range(max(1, len(compact) - 1))]
    if len(compact) == 1:
        grams = [compact]
    return Counter(grams)


def _cosine(left: Counter[str], right: Counter[str]) -> float:
    numerator = sum(left[key] * right[key] for key in left.keys() & right.keys())
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    return numerator / (left_norm * right_norm) if left_norm and right_norm else 0.0


def _require_local_model(module: str, package_name: str, model_path: str | None) -> Path:
    if importlib.util.find_spec(module) is None:
        raise AlgorithmInputError(f"模型能力不可用：未安装可选依赖 {package_name}。", code="capability_unavailable", path="parameters.method")
    if not model_path or not Path(model_path).is_dir():
        raise AlgorithmInputError(f"模型能力不可用：{package_name} 已安装，但未提供可用的本地模型目录。", code="capability_unavailable", path="parameters.model_path")
    return Path(model_path)


def _rule_candidates(normalized: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    entities: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    seen_entities: set[tuple[str, int, int]] = set()
    for sentence_match in SENTENCE_PATTERN.finditer(normalized):
        sentence = sentence_match.group(0).strip()
        sentence_start = sentence_match.start()
        for pattern in RELATION_PATTERNS:
            for match in pattern.finditer(sentence):
                source = match.group("source").strip()
                target = match.group("target").strip()
                relation = (match.group("verb") + (match.groupdict().get("object") or "")).strip()
                for role, entity in (("source", source), ("target", target)):
                    start = sentence_start + match.start(role)
                    end = sentence_start + match.end(role)
                    identity = (entity, start, end)
                    if identity not in seen_entities:
                        seen_entities.add(identity)
                        entities.append({
                            "entity": entity,
                            "type": "organization_candidate",
                            "start": start,
                            "end": end,
                            "confidence": 0.9,
                            "evidence": normalized[start:end],
                            "editable": True,
                        })
                relations.append({
                    "source": source,
                    "target": target,
                    "relation": relation,
                    "evidence": sentence,
                    "start": sentence_start + match.start(),
                    "end": sentence_start + match.end(),
                    "confidence": 0.88,
                    "editable": True,
                })
    entities.sort(key=lambda item: (item["start"], item["end"], item["entity"]))
    relations.sort(key=lambda item: (item["start"], item["end"], item["source"], item["target"]))
    return entities, relations


def _load_paddlenlp_extractor(model_path: str) -> Any:
    path = _require_local_model("paddlenlp", "paddlenlp", model_path)
    try:
        from paddlenlp import Taskflow

        return Taskflow(
            "information_extraction",
            schema=[{"组织机构": ["合作方", "被投资方", "被收购方", "供应方", "客户"]}],
            task_path=str(path),
        )
    except Exception as exc:
        raise AlgorithmInputError(f"PaddleNLP 本地模型无法加载：{exc}", code="capability_unavailable", path="parameters.model_path") from exc


def _uie_span(item: Any, normalized: str, *, label: str) -> tuple[str, int, int, float]:
    if not isinstance(item, dict):
        raise AlgorithmInputError(f"PaddleNLP UIE {label} 必须是对象。", code="unsupported_model_schema", path="model_output")
    text = item.get("text")
    start = item.get("start")
    end = item.get("end")
    raw_confidence = item.get("probability") if "probability" in item else item.get("confidence")
    confidence = coerce_finite_float(raw_confidence)
    if (
        not isinstance(text, str) or not text
        or isinstance(start, bool) or not isinstance(start, int)
        or isinstance(end, bool) or not isinstance(end, int)
        or not 0 <= start < end <= len(normalized)
        or normalized[start:end] != text
        or confidence is None or not 0 <= confidence <= 1
    ):
        raise AlgorithmInputError(f"PaddleNLP UIE {label} 缺少可校正的 text/start/end/probability 字段。", code="unsupported_model_schema", path="model_output")
    return text, start, end, confidence


def _transform_paddlenlp_output(normalized: str, raw: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not isinstance(raw, list) or len(raw) != 1 or not isinstance(raw[0], dict) or not raw[0]:
        raise AlgorithmInputError("PaddleNLP UIE 输出必须是单文本对象列表。", code="unsupported_model_schema", path="model_output")
    entity_by_span: dict[tuple[str, int, int], dict[str, Any]] = {}
    relations: list[dict[str, Any]] = []
    for entity_type in sorted(raw[0]):
        sources = raw[0][entity_type]
        if not isinstance(entity_type, str) or not isinstance(sources, list):
            raise AlgorithmInputError("PaddleNLP UIE 顶层实体类型必须是列表。", code="unsupported_model_schema", path="model_output")
        for source_item in sources:
            source, source_start, source_end, source_confidence = _uie_span(source_item, normalized, label="实体")
            entity_by_span[(source, source_start, source_end)] = {
                "entity": source, "type": entity_type, "start": source_start, "end": source_end,
                "confidence": source_confidence, "evidence": normalized[source_start:source_end], "editable": True,
            }
            relation_groups = source_item.get("relations")
            if relation_groups is None:
                continue
            if not isinstance(relation_groups, dict):
                raise AlgorithmInputError("PaddleNLP UIE relations 必须是对象。", code="unsupported_model_schema", path="model_output")
            for relation_name in sorted(relation_groups):
                targets = relation_groups[relation_name]
                if not isinstance(relation_name, str) or not relation_name or not isinstance(targets, list):
                    raise AlgorithmInputError("PaddleNLP UIE 关系类型必须是非空列表。", code="unsupported_model_schema", path="model_output")
                for target_item in targets:
                    target, target_start, target_end, target_confidence = _uie_span(target_item, normalized, label="关系目标")
                    entity_by_span[(target, target_start, target_end)] = {
                        "entity": target, "type": relation_name, "start": target_start, "end": target_end,
                        "confidence": target_confidence, "evidence": normalized[target_start:target_end], "editable": True,
                    }
                    start = min(source_start, target_start)
                    end = max(source_end, target_end)
                    relations.append({
                        "source": source, "target": target, "relation": relation_name,
                        "evidence": normalized[start:end], "start": start, "end": end,
                        "confidence": min(source_confidence, target_confidence), "editable": True,
                    })
    if not relations:
        raise AlgorithmInputError("PaddleNLP UIE 模型输出不含支持的实体关系 schema。", code="unsupported_model_schema", path="model_output")
    entities = sorted(entity_by_span.values(), key=lambda item: (item["start"], item["end"], item["entity"]))
    relations.sort(key=lambda item: (item["start"], item["end"], item["source"], item["target"], item["relation"]))
    return entities, relations


def _paddlenlp_candidates(normalized: str, model_path: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    extractor = _load_paddlenlp_extractor(model_path)
    try:
        raw = extractor(normalized)
    except AlgorithmInputError:
        raise
    except Exception as exc:
        raise AlgorithmInputError(f"PaddleNLP 本地模型推理失败：{exc}", code="capability_unavailable", path="parameters.model_path") from exc
    return _transform_paddlenlp_output(normalized, raw)


def _load_bge_model(model_path: str) -> Any:
    path = _require_local_model("sentence_transformers", "sentence-transformers", model_path)
    try:
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(str(path), local_files_only=True, device="cpu")
    except Exception as exc:
        raise AlgorithmInputError(f"BGE 本地模型无法加载：{exc}", code="capability_unavailable", path="parameters.model_path") from exc


def _bge_weights(relations: list[dict[str, Any]], model: Any) -> list[float]:
    pairs = [[relation["source"], relation["target"]] for relation in relations]
    try:
        embeddings = model.encode(
            [item for pair in pairs for item in pair],
            normalize_embeddings=True,
            show_progress_bar=False,
        )
    except Exception as exc:
        raise AlgorithmInputError(f"BGE 本地模型推理失败：{exc}", code="capability_unavailable", path="parameters.model_path") from exc
    return [max(0.0, min(1.0, float(embeddings[index * 2] @ embeddings[index * 2 + 1]))) for index in range(len(relations))]


def extract_chinese_graph(
    text: str,
    *,
    method: str = "rule",
    embedding: str = "cosine",
    seed: int | None = None,
    model_path: str | None = None,
) -> dict[str, Any]:
    del seed  # Rule extraction and local inference are deterministic by construction.
    processed = preprocess_chinese(text)
    normalized = processed["normalized_text"]
    if method == "bge":
        embedding = "bge"
        method = "rule"
    bge_model = _load_bge_model(str(model_path or "")) if embedding == "bge" else None
    if method == "paddlenlp":
        entities, relations = _paddlenlp_candidates(normalized, str(model_path or ""))
    elif method == "rule":
        entities, relations = _rule_candidates(normalized)
    else:
        raise AlgorithmInputError(f"不支持的文本抽取方法：{method}。", path="parameters.method")
    if not relations:
        raise AlgorithmInputError("未识别到可建网的实体关系候选；请补充关系表达或切换可用模型。", code="no_candidates", path="parameters.text")

    grouped: dict[tuple[str, str], list[int]] = {}
    for index, relation in enumerate(relations):
        grouped.setdefault((relation["source"], relation["target"]), []).append(index)
    maximum_count = max(len(indices) for indices in grouped.values())
    if embedding == "bge":
        occurrence_weights = _bge_weights(relations, bge_model)
    elif embedding not in {"normalized", "cosine"}:
        raise AlgorithmInputError(f"不支持的边权方法：{embedding}。", path="parameters.embedding")

    node_ids = sorted({relation["source"] for relation in relations} | {relation["target"] for relation in relations})
    edges = []
    for (source, target), indices in sorted(grouped.items()):
        if embedding == "normalized":
            weight = len(indices) / maximum_count
        elif embedding == "cosine":
            shared = "".join(relations[index]["evidence"] for index in indices)
            weight = _cosine(_char_vector(source + shared), _char_vector(target + shared))
        else:
            weight = sum(occurrence_weights[index] for index in indices) / len(indices)
        edges.append({
            "source": source,
            "target": target,
            "weight": float(max(0.01, min(1.0, weight))),
            "relations": sorted({relations[index]["relation"] for index in indices}),
            "occurrence_count": len(indices),
            "candidate_indices": indices,
        })
    return {
        "preprocessing": processed,
        "entities": entities,
        "relations": relations,
        "graph": {"directed": True, "nodes": [{"id": node, "label": node} for node in node_ids], "edges": edges},
        "weight_method": embedding,
        "correction_schema": {
            "entity_fields": ["entity", "type", "start", "end", "confidence"],
            "relation_fields": ["source", "target", "relation", "evidence", "confidence"],
            "operations": ["accept", "edit", "delete", "add"],
        },
    }
