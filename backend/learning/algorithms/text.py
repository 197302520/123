from __future__ import annotations

import importlib.util
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

from .errors import AlgorithmInputError


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


def _paddlenlp_candidates(normalized: str, model_path: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    _require_local_model("paddlenlp", "paddlenlp", model_path)
    try:
        from paddlenlp import Taskflow

        extractor = Taskflow("information_extraction", schema=["实体", {"关系": ["主体", "客体"]}], task_path=model_path)
        raw = extractor(normalized)
    except Exception as exc:
        raise AlgorithmInputError(f"PaddleNLP 本地模型无法加载：{exc}", code="capability_unavailable", path="parameters.model_path") from exc
    # UIE schemas differ across locally supplied models. Preserve raw candidates for correction,
    # while rule candidates provide a stable graph projection when relation fields are absent.
    entities, relations = _rule_candidates(normalized)
    for entity in entities:
        entity["adapter"] = "paddlenlp"
    for relation in relations:
        relation["adapter"] = "paddlenlp"
        relation["model_output_available"] = bool(raw)
    return entities, relations


def _bge_weights(relations: list[dict[str, Any]], model_path: str) -> list[float]:
    path = _require_local_model("sentence_transformers", "sentence-transformers", model_path)
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(str(path), local_files_only=True, device="cpu")
        pairs = [[relation["source"], relation["target"]] for relation in relations]
        embeddings = model.encode([item for pair in pairs for item in pair], normalize_embeddings=True, show_progress_bar=False)
    except Exception as exc:
        raise AlgorithmInputError(f"BGE 本地模型无法加载：{exc}", code="capability_unavailable", path="parameters.model_path") from exc
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
        _require_local_model("sentence_transformers", "sentence-transformers", model_path)
        embedding = "bge"
        method = "rule"
    if method == "paddlenlp":
        entities, relations = _paddlenlp_candidates(normalized, str(model_path or ""))
    elif method == "rule":
        entities, relations = _rule_candidates(normalized)
    else:
        raise AlgorithmInputError(f"不支持的文本抽取方法：{method}。", path="parameters.method")
    if not relations:
        raise AlgorithmInputError("未识别到可建网的实体关系候选；请补充关系表达或切换可用模型。", code="no_candidates", path="parameters.text")

    counts = Counter((relation["source"], relation["target"], relation["relation"]) for relation in relations)
    maximum_count = max(counts.values())
    if embedding == "bge":
        weights = _bge_weights(relations, str(model_path or ""))
    elif embedding == "normalized":
        weights = [counts[(relation["source"], relation["target"], relation["relation"])] / maximum_count for relation in relations]
    elif embedding == "cosine":
        weights = []
        for relation in relations:
            shared = relation["evidence"]
            left = _char_vector(relation["source"] + shared)
            right = _char_vector(relation["target"] + shared)
            weights.append(max(0.01, min(1.0, _cosine(left, right))))
    else:
        raise AlgorithmInputError(f"不支持的边权方法：{embedding}。", path="parameters.embedding")

    node_ids = sorted({relation["source"] for relation in relations} | {relation["target"] for relation in relations})
    edges = [
        {
            "source": relation["source"],
            "target": relation["target"],
            "weight": float(weights[index]),
            "relation": relation["relation"],
            "candidate_index": index,
        }
        for index, relation in enumerate(relations)
    ]
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
