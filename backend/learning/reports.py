from __future__ import annotations

import csv
import html
import io
import json
import re
import zipfile
from typing import Any

from .algorithms.exports import export_graph
from .models import Run


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, default=str)


def _safe_name(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-.")
    return (cleaned[:80] or fallback)


def _csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def _csv_bytes(columns: list[str], rows: list[dict[str, Any]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(columns)
    for row in rows:
        writer.writerow([_csv_value(row.get(column, "")) for column in columns])
    return ("\ufeff" + stream.getvalue()).encode("utf-8")


def render_report_html(run: Run) -> str:
    provenance = run.result.get("provenance", {})
    table_sections = []
    for table in run.result.get("tables", []):
        columns = table.get("columns", [])
        head = "".join(f"<th>{html.escape(str(column))}</th>" for column in columns)
        body = "".join(
            "<tr>" + "".join(f"<td>{html.escape(str(row.get(column, '')))}</td>" for column in columns) + "</tr>"
            for row in table.get("rows", [])
        )
        table_sections.append(f"<section><h2>{html.escape(str(table.get('name', '结果表')))}</h2><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></section>")
    labels = "、".join(html.escape(str(node.get("label", node.get("id", "")))) for node in run.graph.get("nodes", []))
    return """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>社会网络分析复现报告</title><style>body{font:16px/1.6 system-ui;max-width:980px;margin:40px auto;padding:0 24px;color:#17211d}table{border-collapse:collapse;width:100%%}th,td{border:1px solid #ccd5cf;padding:8px;text-align:left}code{overflow-wrap:anywhere}</style></head><body><h1>社会网络分析复现报告</h1><p>运行编号：<code>%s</code></p><p>算法：%s（v%s）</p><p>节点：%s</p>%s<h2>复现信息</h2><pre>%s</pre></body></html>""" % (
        html.escape(str(run.id)), html.escape(run.algorithm), html.escape(run.algorithm_version), labels,
        "".join(table_sections), html.escape(_json(provenance)),
    )


def build_report_bundle(run: Run) -> bytes:
    graphml = export_graph(run.graph, "graphml")["content"]
    files: dict[str, tuple[str, bytes]] = {
        "report.html": ("text/html; charset=utf-8", render_report_html(run).encode("utf-8")),
        "result.json": ("application/json", _json({"run_id": str(run.id), "status": run.status, **run.result}).encode("utf-8")),
        "parameters.json": ("application/json", _json({"supplied": run.parameters, "resolved": run.resolved_parameters, "seed": run.seed}).encode("utf-8")),
        "provenance.json": ("application/json", _json(run.result.get("provenance", {})).encode("utf-8")),
        "nodes.csv": ("text/csv; charset=utf-8", _csv_bytes(["id", "label"], run.graph.get("nodes", []))),
        "edges.csv": ("text/csv; charset=utf-8", _csv_bytes(["source", "target", "weight"], run.graph.get("edges", []))),
        "graph.graphml": ("application/graphml+xml", graphml.encode("utf-8")),
    }
    for index, table in enumerate(run.result.get("tables", []), start=1):
        name = _safe_name(str(table.get("key", "table")), f"table-{index}")
        files[f"tables/{index:02d}-{name}.csv"] = (
            "text/csv; charset=utf-8",
            _csv_bytes(list(table.get("columns", [])), list(table.get("rows", []))),
        )
    manifest = {
        "schema": "sna-teaching-reproducibility/v1",
        "run_id": str(run.id),
        "files": [{"path": path, "mime_type": mime_type} for path, (mime_type, _) in sorted(files.items())],
    }
    files["manifest.json"] = ("application/json", _json(manifest).encode("utf-8"))
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path, (_, content) in sorted(files.items()):
            archive.writestr(path, content)
    return output.getvalue()
