# -*- coding: utf-8 -*-
"""对 data/ 数据集执行导入校验与代表性算法实测。

验证 README 中「验证记录」表的每一行。运行：python scripts/verify_datasets.py
（需要后端已在 127.0.0.1:8000 运行。）

网络边界：脚本只允许访问固定的本机回环地址 127.0.0.1:8000，
所有请求 URL 先经 allowlist 校验，且禁用 HTTP 重定向跟随。
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

ALLOWED_ORIGIN = "http://127.0.0.1:8000"
ALLOWED_HOSTS = {"127.0.0.1"}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ARG002
        raise urllib.error.HTTPError(newurl, code, "重定向已被禁用", headers, fp)


OPENER = urllib.request.build_opener(_NoRedirect)


def safe_url(path_or_url: str) -> str:
    url = path_or_url if path_or_url.startswith("http://") else ALLOWED_ORIGIN + path_or_url
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "http" or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError(f"仅允许访问本机回环服务 {ALLOWED_ORIGIN}，拒绝: {url}")
    return url


def request_bytes(url: str, data: bytes | None, content_type: str, timeout: float = 60) -> bytes:
    target = safe_url(url)
    request = urllib.request.Request(target, data=data, method="POST" if data is not None else "GET")
    if data is not None:
        request.add_header("Content-Type", content_type)
    with OPENER.open(request, timeout=timeout) as response:
        return response.read()


def post_json(path: str, payload: dict) -> dict:
    raw = request_bytes(path, json.dumps(payload).encode("utf-8"), "application/json")
    return json.loads(raw.decode("utf-8"))


def get_json(path: str) -> dict:
    raw = request_bytes(path, None, "")
    return json.loads(raw.decode("utf-8"))


def upload(filename: str) -> dict:
    boundary = "----verifyboundary"
    body = b""
    with open(DATA / filename, "rb") as handle:
        body += (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
            f"filename=\"{filename}\"\r\nContent-Type: application/octet-stream\r\n\r\n"
        ).encode("utf-8") + handle.read() + b"\r\n"
    body += f"--{boundary}--\r\n".encode("utf-8")
    raw = request_bytes("/api/graphs/import/", body, f"multipart/form-data; boundary={boundary}")
    return json.loads(raw.decode("utf-8"))


def run_algorithm(algorithm: str, graph: dict, parameters: dict, seed: int | None = 20260827) -> dict:
    status = post_json("/api/runs/", {"algorithm": algorithm, "graph": graph, "parameters": parameters, "seed": seed})
    run_id = status["id"]
    for _ in range(120):
        if status["status"] in {"completed", "failed"}:
            break
        time.sleep(0.5)
        status = get_json(f"/api/runs/{run_id}/")
    if status["status"] != "completed":
        raise RuntimeError(f"{algorithm} 状态 {status['status']}")
    return get_json(f"/api/runs/{run_id}/result/")


results: list[str] = []


def record(message: str) -> None:
    results.append(message)
    print("  " + message)


def check_import(filename: str, expect_nodes: int | None = None) -> dict:
    response = upload(filename)
    assert response.get("valid"), f"{filename} 导入失败: {response}"
    graph = response["graph"]
    if expect_nodes is not None:
        assert len(graph["nodes"]) == expect_nodes, f"{filename} 节点数 {len(graph['nodes'])} != {expect_nodes}"
    record(f"{filename} → 导入 {len(graph['nodes'])} 节点 {len(graph['edges'])} 边")
    return graph


print("== 导入校验 ==")
karate = check_import("实验03_基础拓扑与最短路/空手道俱乐部网络.txt", 34)
dolphins = check_import("实验06_社区发现_重叠/海豚社群网络.csv", 62)
football = check_import("实验04_中心性测度/世界杯球员俱乐部.csv")
trade = check_import("实验04_中心性测度/国际贸易流向.json")
grid = check_import("实验08_网络韧性攻击/区域输电网.csv", 24)

# TXT/CSV 导入为无向：世界杯球员实验时需在实验室切换为有向。
football_directed = {"directed": True, "nodes": football["nodes"], "edges": football["edges"]}

opinion = json.loads((DATA / "实验10_观点动力学/课堂意见网络.json").read_text(encoding="utf-8"))
dynamic_t1 = json.loads((DATA / "实验11_动态社区演化/企业联盟网络.json").read_text(encoding="utf-8"))
attributed = json.loads((DATA / "实验07_深度学习社区/研究者合作属性网络.json").read_text(encoding="utf-8"))
opinion_params = json.loads((DATA / "实验10_观点动力学/观点模型参数.json").read_text(encoding="utf-8"))
dynamic_params = json.loads((DATA / "实验11_动态社区演化/联盟三期快照参数.json").read_text(encoding="utf-8"))
enterprise_text = (DATA / "实验01_文本抽取建网/企业关系新闻文本.txt").read_text(encoding="utf-8")

print("== 算法实测 ==")

result = run_algorithm("community.louvain", karate, {})
communities = next(t for t in result["tables"] if t["key"] == "communities")
groups = {str(row["community"]) for row in communities["rows"]}
record(f"karate + community.louvain → {len(groups)} 个社区（表：{communities['name']}）")

result = run_algorithm("robustness.attack", karate, {"strategy": "degree"})
record("karate + robustness.attack(degree 蓄意攻击) → 坍缩曲线完成")

result = run_algorithm("centrality.betweenness", karate, {})
rows = result["tables"][0]["rows"]
score_key = next(k for k in rows[0] if isinstance(rows[0][k], (int, float)))
top = max(rows, key=lambda row: float(row[score_key]))
node_key = next(k for k in ("node", "节点", "id") if k in top)
record(f"karate + centrality.betweenness → 最高节点 {top[node_key]}（{score_key}={top[score_key]:.3f}）")

algorithms = {item["key"]: item for item in get_json("/api/algorithms/")}
cpm_params = {key: value.get("default") for key, value in algorithms["community.cpm"]["parameters"].items()}
result = run_algorithm("community.cpm", dolphins, cpm_params)
record(f"dolphins + community.cpm → 重叠社区完成（参数 {cpm_params}）")

result = run_algorithm("link_prediction.adamic_adar", dolphins, {})
auc_table = next((t for t in result["tables"] if "auc" in json.dumps(t, ensure_ascii=False).lower()), result["tables"][0])
record(f"dolphins + link_prediction.adamic_adar → {auc_table['name']} 完成")

result = run_algorithm("centrality.pagerank", trade, {})
record("trade(有向) + centrality.pagerank → 完成")

result = run_algorithm("centrality.degree", football_directed, {})
record("football(有向二部) + centrality.degree → 出/入度完成")

result = run_algorithm("robustness.attack", grid, {"strategy": "random"})
record("power_grid + robustness.attack(random) → 完成")

degroot_params = {k: v for k, v in opinion_params["opinion.degroot"].items() if not k.startswith("_")}
result = run_algorithm("opinion.degroot", opinion, degroot_params)
record(f"opinion + opinion.degroot → 收敛方差 {result['provenance'].get('final_variance')}")

hk_params = {k: v for k, v in opinion_params["opinion.hk"].items() if not k.startswith("_")}
result = run_algorithm("opinion.hk", opinion, hk_params)
record(f"opinion + opinion.hk → 最终极差 {result['provenance'].get('final_range')}")

snapshots = {k: v for k, v in dynamic_params["community.dynamic"].items() if not k.startswith("_")}
result = run_algorithm("community.dynamic", dynamic_t1, snapshots)
events = next(t for t in result["tables"] if "event" in t["key"] or "事件" in t["name"])
kinds = sorted({str(row.get("event")) for row in events["rows"]})
record(f"dynamic_alliance + community.dynamic → 事件类型 {kinds}")

gcn_params = {key: value.get("default") for key, value in algorithms["embedding.gcn"]["parameters"].items()}
gcn_params["epochs"] = 60
result = run_algorithm("embedding.gcn", attributed, gcn_params)
record("attributed + embedding.gcn → 嵌入聚类完成")

result = run_algorithm("text.extract", {"directed": True, "nodes": [], "edges": []}, {"text": enterprise_text, "merge_threshold": 0.6})
entities = next(t for t in result["tables"] if t["key"] == "entities")
relations = next(t for t in result["tables"] if t["key"] == "relations")
merges = next(t for t in result["tables"] if t["key"] == "entity_merges")
record(f"enterprise_text + text.extract → {len(entities['rows'])} 实体 / {len(relations['rows'])} 关系 / {len(merges['rows'])} 组同指合并")

print(f"\n全部 {len(results)} 项验证通过。")
