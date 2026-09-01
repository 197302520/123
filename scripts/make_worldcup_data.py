# -*- coding: utf-8 -*-
"""把 backend/learning/data/pajek/ 下的世界杯 Pajek 数据转换为 Python 常量模块。

运行：python scripts/make_worldcup_data.py
输出：backend/learning/data/worldcup_football.py（幂等覆盖）。

数据语义：边 (来源国, 东道国, 人数) 表示来源国世界杯阵容中效力东道国联赛的
球员人数；全员在本国踢球的阵容不形成任何边（如 1998 年沙特阿拉伯），因此
该代表队不出现在节点表中。仅作为东道国出现、未参赛的国家（联赛国）在原
文件中同样没有出边。
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "backend" / "learning" / "data"
TARGET = DATA_DIR / "worldcup_football.py"

# 节点代码 -> (中文译名, 大洲)。原文件使用 ISO 3166 三字母码的变体：
# 同一国家在 1998/2002 两份文件里的写法可能不同（如 CHL/CHI、GBR/ENG、
# CMR/CAM、NGA/NIG、GRE/GRC），转换时按原文件保留，不做归一。
CODE_INFO: dict[str, tuple[str, str]] = {
    "ARG": ("阿根廷", "南美洲"), "AUT": ("奥地利", "欧洲"), "BEL": ("比利时", "欧洲"),
    "BGR": ("保加利亚", "欧洲"), "BRA": ("巴西", "南美洲"), "CAM": ("喀麦隆", "非洲"),
    "CHE": ("瑞士", "欧洲"), "CHI": ("智利", "南美洲"), "CHL": ("智利", "南美洲"),
    "CHN": ("中国", "亚洲"), "CMR": ("喀麦隆", "非洲"), "COL": ("哥伦比亚", "南美洲"),
    "CRI": ("哥斯达黎加", "中北美洲"), "CZE": ("捷克", "欧洲"), "DEU": ("德国", "欧洲"),
    "DNK": ("丹麦", "欧洲"), "ECU": ("厄瓜多尔", "南美洲"), "ENG": ("英格兰", "欧洲"),
    "ESP": ("西班牙", "欧洲"), "FRA": ("法国", "欧洲"), "GBR": ("英格兰", "欧洲"),
    "GRC": ("希腊", "欧洲"), "GRE": ("希腊", "欧洲"), "HRV": ("克罗地亚", "欧洲"),
    "IRL": ("爱尔兰", "欧洲"), "IRN": ("伊朗", "亚洲"), "ISR": ("以色列", "亚洲"),
    "ITA": ("意大利", "欧洲"), "JAM": ("牙买加", "中北美洲"), "JPN": ("日本", "亚洲"),
    "KOR": ("韩国", "亚洲"), "MAR": ("摩洛哥", "非洲"), "MEX": ("墨西哥", "中北美洲"),
    "NGA": ("尼日利亚", "非洲"), "NIG": ("尼日利亚", "非洲"), "NLD": ("荷兰", "欧洲"),
    "NOR": ("挪威", "欧洲"), "POL": ("波兰", "欧洲"), "PRT": ("葡萄牙", "欧洲"),
    "PRY": ("巴拉圭", "南美洲"), "ROM": ("罗马尼亚", "欧洲"), "RUS": ("俄罗斯", "欧洲"),
    "SCO": ("苏格兰", "欧洲"), "SDA": ("沙特阿拉伯", "亚洲"), "SEN": ("塞内加尔", "非洲"),
    "SLO": ("斯洛文尼亚", "欧洲"), "SWE": ("瑞典", "欧洲"), "TUN": ("突尼斯", "非洲"),
    "TUR": ("土耳其", "欧洲"), "URU": ("乌拉圭", "南美洲"), "USA": ("美国", "中北美洲"),
    "YUG": ("南斯拉夫", "欧洲"), "ZAF": ("南非", "非洲"),
}

SOURCES = [
    ("WC1998", "football1998.net", "1998 年法国世界杯"),
    ("WC2002", "football2002.net", "2002 年韩日世界杯"),
]

VERTEX_RE = re.compile(r'^\s*(\d+)\s+"([^"]+)"')


def parse(path: Path) -> tuple[list[str], list[tuple[str, str, int]]]:
    section = ""
    nodes: dict[int, str] = {}
    edges: list[tuple[str, str, int]] = []
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        text = raw.strip()
        if not text:
            continue
        lowered = text.lower()
        if lowered.startswith("*vertices"):
            section = "v"
            continue
        if lowered.startswith("*arcs"):
            section = "a"
            continue
        if lowered.startswith("*edges"):
            section = "e"
            continue
        if section == "v":
            match = VERTEX_RE.match(text)
            if not match:
                raise ValueError(f"{path.name}: 无法解析顶点行: {text!r}")
            nodes[int(match.group(1))] = match.group(2)
        elif section in {"a", "e"}:
            parts = text.split()
            edges.append((nodes[int(parts[0])], nodes[int(parts[1])], int(parts[2])))
    missing = {code for edge in edges for code in edge[:2]} - set(CODE_INFO)
    if missing:
        raise ValueError(f"{path.name}: 缺少中文译名的节点代码: {sorted(missing)}")
    ordered = [nodes[index] for index in sorted(nodes)]
    return ordered, edges


def format_tuple(items: list[str], per_line: int = 6) -> str:
    lines = []
    for start in range(0, len(items), per_line):
        lines.append("    " + " ".join(f'"{item}",' for item in items[start:start + per_line]))
    return "(\n" + "\n".join(lines) + "\n)"


def format_edges(edges: list[tuple[str, str, int]]) -> str:
    lines = []
    for source, target, weight in edges:
        lines.append(f'    ("{source}", "{target}", {weight}),')
    return "(\n" + "\n".join(lines) + "\n)"


def main() -> None:
    blocks = [
        '"""世界杯国家队阵容的球员跨国流动网络（Pajek 数据，教学用）。',
        "",
        "边 (来源国, 东道国, 人数) 表示来源国世界杯阵容中效力东道国俱乐部的",
        "球员人数；全部在本国踢球的球员不形成边，因此全员本土踢球的代表队",
        "（如 1998 年沙特阿拉伯）不在节点表中；未参赛但吸纳了外国国脚的",
        "联赛国家只有入边。",
        "",
        "来源：Pajek datasets（V. Batagelj & A. Mrvar），",
        "http://vlado.fmf.uni-lj.si/pub/networks/data/ 的 football.net（1998",
        "法国世界杯）与 football2002.net（2002 韩日世界杯），由任课教师提供。",
        "原始 .net 文件保存在本目录 pajek/ 下；本模块由",
        "scripts/make_worldcup_data.py 幂等生成，请勿手工编辑。",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "# 节点代码 -> (中文译名, 大洲)。1998/2002 两份原文件对同一国家的代码",
        # noqa 注释行由脚本写死，保持生成器与产物一致
        "# 写法可能不同（CHL/CHI、GBR/ENG、CMR/CAM、NGA/NIG、GRE/GRC），按原文件保留。",
        "CODE_INFO: dict[str, tuple[str, str]] = {",
    ]
    for code in sorted(CODE_INFO):
        name, zone = CODE_INFO[code]
        blocks.append(f'    "{code}": ("{name}", "{zone}"),')
    blocks.append("}")
    for prefix, filename, _ in SOURCES:
        nodes, edges = parse(DATA_DIR / "pajek" / filename)
        blocks.append("")
        blocks.append(f"{prefix}_NODES: tuple[str, ...] = {format_tuple(nodes)}")
        blocks.append("")
        blocks.append(f"{prefix}_EDGES: tuple[tuple[str, str, int], ...] = {format_edges(edges)}")
    blocks.append("")
    TARGET.write_text("\n".join(blocks), encoding="utf-8")

    for prefix, filename, _ in SOURCES:
        nodes, edges = parse(DATA_DIR / "pajek" / filename)
        total = sum(weight for _, _, weight in edges)
        print(f"{prefix}: {filename} nodes={len(nodes)} arcs={len(edges)} weight_sum={total}")
    print(f"wrote {TARGET}")


if __name__ == "__main__":
    main()
