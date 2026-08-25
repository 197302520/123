from __future__ import annotations

import csv
import io
import json
import xml.etree.ElementTree as ET
from typing import Any

from .errors import AlgorithmInputError
from .graph import normalize_graph


FORMATS = {"json", "csv", "graphml", "gexf", "gml", "pajek", "edgelist", "adjacency"}


def _sorted_graph(graph: dict[str, Any]) -> dict[str, Any]:
    return {
        "directed": graph["directed"],
        "nodes": sorted(graph["nodes"], key=lambda node: node["id"]),
        "edges": sorted(graph["edges"], key=lambda edge: (edge["source"], edge["target"], edge["weight"])),
    }


def _csv_edges(graph: dict[str, Any]) -> str:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["source", "target", "weight"])
    for edge in graph["edges"]:
        writer.writerow([edge["source"], edge["target"], edge["weight"]])
    return output.getvalue()


def _adjacency(graph: dict[str, Any]) -> str:
    nodes = [node["id"] for node in graph["nodes"]]
    weights = {(edge["source"], edge["target"]): edge["weight"] for edge in graph["edges"]}
    if not graph["directed"]:
        weights.update({(target, source): value for (source, target), value in list(weights.items())})
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["node", *nodes])
    for source in nodes:
        writer.writerow([source, *[weights.get((source, target), 0.0) for target in nodes]])
    return output.getvalue()


def _graphml(graph: dict[str, Any]) -> str:
    namespace = "http://graphml.graphdrawing.org/xmlns"
    ET.register_namespace("", namespace)
    root = ET.Element(f"{{{namespace}}}graphml")
    ET.SubElement(root, f"{{{namespace}}}key", {"id": "label", "for": "node", "attr.name": "label", "attr.type": "string"})
    ET.SubElement(root, f"{{{namespace}}}key", {"id": "weight", "for": "edge", "attr.name": "weight", "attr.type": "double"})
    graph_element = ET.SubElement(root, f"{{{namespace}}}graph", {"id": "G", "edgedefault": "directed" if graph["directed"] else "undirected"})
    for node in graph["nodes"]:
        element = ET.SubElement(graph_element, f"{{{namespace}}}node", {"id": node["id"]})
        ET.SubElement(element, f"{{{namespace}}}data", {"key": "label"}).text = node["label"]
    for index, edge in enumerate(graph["edges"]):
        element = ET.SubElement(graph_element, f"{{{namespace}}}edge", {"id": f"e{index}", "source": edge["source"], "target": edge["target"]})
        ET.SubElement(element, f"{{{namespace}}}data", {"key": "weight"}).text = format(edge["weight"], ".17g")
    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def _gexf(graph: dict[str, Any]) -> str:
    namespace = "http://gexf.net/1.3"
    ET.register_namespace("", namespace)
    root = ET.Element(f"{{{namespace}}}gexf", {"version": "1.3"})
    graph_element = ET.SubElement(root, f"{{{namespace}}}graph", {"mode": "static", "defaultedgetype": "directed" if graph["directed"] else "undirected"})
    nodes_element = ET.SubElement(graph_element, f"{{{namespace}}}nodes")
    for node in graph["nodes"]:
        ET.SubElement(nodes_element, f"{{{namespace}}}node", {"id": node["id"], "label": node["label"]})
    edges_element = ET.SubElement(graph_element, f"{{{namespace}}}edges")
    for index, edge in enumerate(graph["edges"]):
        ET.SubElement(edges_element, f"{{{namespace}}}edge", {"id": str(index), "source": edge["source"], "target": edge["target"], "weight": format(edge["weight"], ".17g")})
    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def _quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _gml(graph: dict[str, Any]) -> str:
    index = {node["id"]: offset for offset, node in enumerate(graph["nodes"])}
    lines = ["graph [", f"  directed {1 if graph['directed'] else 0}"]
    for node in graph["nodes"]:
        lines.extend(["  node [", f"    id {index[node['id']]}", f"    label {_quote(node['label'])}", "  ]"])
    for edge in graph["edges"]:
        lines.extend(["  edge [", f"    source {index[edge['source']]}", f"    target {index[edge['target']]}", f"    weight {format(edge['weight'], '.17g')}", "  ]"])
    lines.append("]")
    return "\n".join(lines) + "\n"


def _pajek(graph: dict[str, Any]) -> str:
    index = {node["id"]: offset + 1 for offset, node in enumerate(graph["nodes"])}
    lines = [f"*Vertices {len(graph['nodes'])}"]
    lines.extend(f"{index[node['id']]} {_quote(node['label'])}" for node in graph["nodes"])
    lines.append("*Arcs" if graph["directed"] else "*Edges")
    lines.extend(f"{index[edge['source']]} {index[edge['target']]} {format(edge['weight'], '.17g')}" for edge in graph["edges"])
    return "\n".join(lines) + "\n"


def export_graph(graph: dict[str, Any], format_name: str) -> dict[str, str]:
    normalized = _sorted_graph(normalize_graph(graph))
    format_name = format_name.lower()
    if format_name not in FORMATS:
        raise AlgorithmInputError(f"不支持的导出格式：{format_name}。", path="parameters.format")
    if format_name == "json":
        content = json.dumps(normalized, ensure_ascii=False, sort_keys=True, indent=2)
        mime_type = "application/json"
        extension = "json"
    elif format_name == "csv":
        content, mime_type, extension = _csv_edges(normalized), "text/csv", "csv"
    elif format_name == "adjacency":
        content, mime_type, extension = _adjacency(normalized), "text/csv", "adjacency.csv"
    elif format_name == "graphml":
        content, mime_type, extension = _graphml(normalized), "application/graphml+xml", "graphml"
    elif format_name == "gexf":
        content, mime_type, extension = _gexf(normalized), "application/gexf+xml", "gexf"
    elif format_name == "gml":
        content, mime_type, extension = _gml(normalized), "text/plain", "gml"
    elif format_name == "pajek":
        content, mime_type, extension = _pajek(normalized), "text/plain", "net"
    else:
        content = "\n".join(f"{edge['source']} {edge['target']} {format(edge['weight'], '.17g')}" for edge in normalized["edges"]) + ("\n" if normalized["edges"] else "")
        mime_type, extension = "text/plain", "edgelist"
    return {"format": format_name, "mime_type": mime_type, "filename": f"network.{extension}", "content": content}
