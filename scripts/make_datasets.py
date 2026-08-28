# -*- coding: utf-8 -*-
"""生成实验数据集到项目根目录 data/ 文件夹。

数据集与《平台说明书》的算法模块一一对应，全部可直接在自由实验室
通过「导入文件」或「粘贴边表」使用。运行：python scripts/make_datasets.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

import networkx as nx  # noqa: E402

from learning.data.sarasota_dolphins import EDGES as DOLPHIN_EDGES  # noqa: E402

DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)


def write(name: str, text: str) -> None:
    (DATA / name).write_text(text, encoding="utf-8", newline="\n")
    print(f"  {name}: {len(text.splitlines())} 行")


def graph_json(directed: bool, edges: list, attributes: dict | None = None) -> dict:
    node_ids: list[str] = []
    seen: set[str] = set()
    for edge in edges:
        for node in edge[:2]:
            if node not in seen:
                seen.add(node)
                node_ids.append(node)
    nodes = []
    for node in node_ids:
        item = {"id": node, "label": node}
        if attributes and node in attributes:
            item["attributes"] = attributes[node]
        nodes.append(item)
    return {
        "directed": directed,
        "nodes": nodes,
        "edges": [{"source": a, "target": b, "weight": w} for a, b, w in edges],
    }


# ---------------------------------------------------------------- 1. 空手道
# Zachary (1977) 空手道俱乐部网络：34 节点 78 边，社区发现经典基准。
karate = nx.karate_club_graph()
lines = [f"{u} {v}" for u, v in karate.edges()]
write("karate_club.txt", "\n".join(lines) + "\n")

# ---------------------------------------------------------------- 2. 海豚
# Lusseau (2003) 海豚关联网络：62 节点 159 边，重叠社区与链路预测常用。
write("dolphins.csv", "source,target\n" + "\n".join(f"{a},{b}" for a, b in DOLPHIN_EDGES) + "\n")

# ---------------------------------------------------------------- 3. 世界杯球员→俱乐部
# 2022 卡塔尔世界杯八强球队核心球员与其效力俱乐部（投影后可做二部网、
# 社区发现与中心性；导入后建议切换为有向：球员 → 俱乐部）。
football = [
    ("梅西", "巴黎圣日耳曼"), ("迪马利亚", "尤文图斯"), ("劳塔罗", "国际米兰"),
    ("恩佐", "本菲卡"), ("阿尔瓦雷斯", "曼城"), ("马丁内斯", "阿斯顿维拉"),
    ("姆巴佩", "巴黎圣日耳曼"), ("格列兹曼", "马德里竞技"), ("吉鲁", "AC米兰"),
    ("琼阿梅尼", "皇家马德里"), ("特奥", "AC米兰"), ("于帕梅卡诺", "拜仁慕尼黑"),
    ("莫德里奇", "皇家马德里"), ("佩里西奇", "托特纳姆热刺"), ("格瓦尔迪奥尔", "莱比锡"),
    ("利瓦科维奇", "萨格勒布迪纳摩"), ("布罗佐维奇", "国际米兰"), ("科瓦西奇", "切尔西"),
    ("贝林厄姆", "多特蒙德"), ("萨卡", "阿森纳"), ("凯恩", "托特纳姆热刺"),
    ("福登", "曼城"), ("赖斯", "西汉姆联"), ("斯通斯", "曼城"),
    ("布努", "塞维利亚"), ("齐耶赫", "切尔西"), ("恩内斯里", "塞维利亚"),
    ("阿姆拉巴特", "佛罗伦萨"), ("马兹拉维", "拜仁慕尼黑"), ("阿什拉夫", "巴黎圣日耳曼"),
    ("奥纳纳", "国际米兰"), ("德保罗", "马德里竞技"), ("麦卡利斯特", "布莱顿"),
    ("范戴克", "利物浦"), ("加克波", "埃因霍温"), ("德容", "巴塞罗那"),
    ("阿克", "曼城"), ("诺珀特", "海伦芬"), ("内马尔", "巴黎圣日耳曼"),
    ("维尼修斯", "皇家马德里"), ("罗德里戈", "皇家马德里"), ("卡塞米罗", "曼联"),
    ("理查利森", "托特纳姆热刺"), ("安东尼", "曼联"), ("阿尔维斯", "美洲狮"),
]
write(
    "football_worldcup.csv",
    "source,target,weight\n" + "\n".join(f"{p},{c},1" for p, c in football) + "\n",
)

# ---------------------------------------------------------------- 4. 国际贸易
# 14 个经济体之间的货物出口流向与量级（依据 2023 年公开贸易数据量级整理，
# 权重单位：十亿美元，量级示意）。互惠边（A→B 与 B→A 并存）在无向导入下
# 会被判重，因此用自带 directed:true 的 JSON GraphSpec 保存。
trade = [
    ("中国", "美国", 50), ("中国", "欧盟", 51), ("中国", "东盟", 59),
    ("中国", "日本", 16), ("中国", "韩国", 15),
    ("美国", "欧盟", 36), ("美国", "加拿大", 35), ("美国", "墨西哥", 32),
    ("美国", "日本", 8), ("美国", "韩国", 7),
    ("欧盟", "美国", 46), ("欧盟", "英国", 34), ("欧盟", "中国", 24),
    ("欧盟", "俄罗斯", 10),
    ("日本", "中国", 12), ("日本", "美国", 13), ("日本", "欧盟", 8),
    ("韩国", "中国", 15), ("韩国", "美国", 11), ("韩国", "欧盟", 6),
    ("东盟", "中国", 21), ("东盟", "美国", 18), ("东盟", "欧盟", 14),
    ("俄罗斯", "中国", 11), ("俄罗斯", "欧盟", 6), ("俄罗斯", "印度", 9),
    ("印度", "美国", 8), ("印度", "欧盟", 7), ("印度", "中国", 3),
    ("英国", "美国", 6), ("英国", "欧盟", 15), ("英国", "中国", 4),
    ("加拿大", "美国", 43), ("墨西哥", "美国", 47),
    ("澳大利亚", "中国", 16), ("澳大利亚", "日本", 8),
    ("巴西", "中国", 12), ("巴西", "美国", 8), ("巴西", "欧盟", 9),
    ("沙特", "中国", 10), ("沙特", "欧盟", 8),
]
write("trade_directed.json", json.dumps(graph_json(True, trade), ensure_ascii=False, indent=2) + "\n")

# ---------------------------------------------------------------- 5. 区域电网
# 合成的区域输电网：24 个节点（电厂 G*、变电站 T*、城市 C*），边权为
# 线路传输容量（百 MW）。适合网络韧性：随机/蓄意攻击下的坍缩曲线。
grid_edges = [
    ("G1", "T1", 12), ("G2", "T3", 10), ("G3", "T7", 8), ("G4", "T9", 6),
    ("T1", "T2", 10), ("T1", "C1", 8), ("T2", "C2", 6), ("T2", "T3", 9),
    ("T3", "T4", 8), ("T3", "C3", 7), ("T4", "C4", 5), ("T4", "T5", 7),
    ("T5", "C5", 6), ("T5", "T6", 6), ("T6", "C6", 5), ("T6", "T7", 8),
    ("T7", "C7", 6), ("T7", "T8", 7), ("T8", "C8", 5), ("T8", "T9", 6),
    ("T9", "C9", 5), ("T9", "T10", 6), ("T10", "C10", 6),
    ("T1", "T6", 7), ("T4", "T9", 5), ("T2", "T8", 4), ("T5", "T10", 4),
    ("C1", "C2", 2), ("C3", "C4", 2), ("C5", "C6", 2), ("C7", "C8", 2),
    ("C9", "C10", 2), ("C1", "C10", 2),
]
write("power_grid_mini.csv", "source,target,weight\n" + "\n".join(f"{a},{b},{w}" for a, b, w in grid_edges) + "\n")


# ---------------------------------------------------------------- 6. 课堂意见网
# 12 人课堂讨论网络：两个观点阵营（S1–S6 偏保守、S7–S12 偏激进），
# 两名桥接者 S6/S7 弱连接。边权 = 每周有效讨论次数。
opinion_edges = [
    ("S1", "S2", 3), ("S1", "S3", 2), ("S2", "S3", 3), ("S2", "S4", 2),
    ("S3", "S5", 2), ("S4", "S5", 3), ("S4", "S6", 2), ("S5", "S6", 3),
    ("S6", "S7", 1),
    ("S7", "S8", 3), ("S7", "S9", 2), ("S8", "S9", 3), ("S8", "S10", 2),
    ("S9", "S11", 2), ("S10", "S11", 3), ("S10", "S12", 2), ("S11", "S12", 3),
]
write("opinion_classroom.json", json.dumps(graph_json(False, opinion_edges), ensure_ascii=False, indent=2) + "\n")

opinions = {
    "S1": 0.15, "S2": 0.2, "S3": 0.1, "S4": 0.25, "S5": 0.2, "S6": 0.35,
    "S7": 0.65, "S8": 0.8, "S9": 0.75, "S10": 0.9, "S11": 0.8, "S12": 0.85,
}
opinion_params = {
    "_说明": "配合 opinion_classroom.json：导入图后按算法复制对应参数块到「参数」编辑器；opinions 是每个节点的初始意见（0–1）。",
    "opinion.degroot": {"opinions": opinions, "max_iterations": 200, "tolerance": 1e-06},
    "opinion.friedkin_johnsen": {"opinions": opinions, "stubbornness": 0.35, "max_iterations": 200, "tolerance": 1e-06},
    "opinion.deffuant": {"opinions": opinions, "confidence": 0.3, "mu": 0.5, "steps": 500, "tolerance": 1e-06},
    "opinion.hk": {"opinions": opinions, "confidence": 0.25, "max_iterations": 200, "tolerance": 1e-06},
}
write("opinion_models.params.json", json.dumps(opinion_params, ensure_ascii=False, indent=2) + "\n")

# ---------------------------------------------------------------- 7. 动态联盟网
# 14 家企业的合作网络，三个年度快照。拓扑按 Louvain 自动检测校准：
# t1 两大阵营各成一体 → t2 B 联盟断裂（分裂事件）→ t3 六条强跨边把
# B1 组并入 A 联盟（合并事件）。
def snap(edges: list) -> dict:
    return graph_json(False, edges)


A_CAMP = [
    ("A1", "A2", 3), ("A2", "A3", 3), ("A3", "A4", 3), ("A4", "A5", 3),
    ("A5", "A6", 3), ("A1", "A3", 3), ("A2", "A4", 3), ("A3", "A5", 3),
    ("A4", "A6", 3), ("A1", "A6", 3),
]
B123 = [("B1", "B2", 3), ("B1", "B3", 3), ("B2", "B3", 3)]
B4567 = [
    ("B4", "B5", 3), ("B4", "B6", 3), ("B4", "B7", 2), ("B5", "B6", 3),
    ("B5", "B7", 3), ("B6", "B7", 3),
]
BRIDGE_A6_B7 = [("A6", "B7", 1)]

t1 = A_CAMP + B123 + B4567 + [
    # B 联盟两组之间的多条强边：t1 时整个 B 是一个社区
    ("B1", "B4", 3), ("B2", "B5", 3), ("B3", "B6", 2), ("B2", "B4", 2), ("B3", "B5", 2),
] + BRIDGE_A6_B7
t2 = A_CAMP + B123 + B4567 + BRIDGE_A6_B7  # 组间桥边全部中断 → 分裂
t3 = A_CAMP + B123 + B4567 + [
    # 六条强跨边：B1 组被 A 联盟吸收 → 合并
    ("A1", "B1", 4), ("A2", "B2", 4), ("A3", "B3", 4),
    ("A4", "B1", 4), ("A5", "B2", 4), ("A6", "B3", 4),
] + BRIDGE_A6_B7
write("dynamic_alliance.json", json.dumps(snap(t1), ensure_ascii=False, indent=2) + "\n")
dynamic_params = {
    "_说明": "配合 dynamic_alliance.json：导入基线图后，把 snapshots 与 threshold 复制到 community.dynamic 的参数编辑器。",
    "community.dynamic": {"snapshots": [snap(t1), snap(t2), snap(t3)], "threshold": 0.3},
}
write("dynamic_alliance.params.json", json.dumps(dynamic_params, ensure_ascii=False, indent=2) + "\n")

# ---------------------------------------------------------------- 8. 属性网络
# 20 位研究者的合作网络：两个主题社群（topic: A/B），每人带 4 维研究
# 兴趣特征。适合 embedding.ae / embedding.cnn / embedding.gcn / embedding.gat。
attr_edges = [
    ("P01", "P02", 2), ("P01", "P03", 3), ("P02", "P03", 2), ("P03", "P04", 2),
    ("P04", "P05", 3), ("P04", "P06", 1), ("P05", "P06", 2), ("P05", "P07", 2),
    ("P06", "P08", 1), ("P07", "P08", 2), ("P07", "P09", 3), ("P08", "P09", 2),
    ("P09", "P10", 2),
    ("P10", "P11", 1),
    ("P11", "P12", 2), ("P11", "P13", 3), ("P12", "P13", 2), ("P13", "P14", 2),
    ("P14", "P15", 3), ("P14", "P16", 1), ("P15", "P16", 2), ("P15", "P17", 2),
    ("P16", "P18", 1), ("P17", "P18", 2), ("P17", "P19", 3), ("P18", "P19", 2),
    ("P19", "P20", 2),
]
rng = __import__("random").Random(20260827)
attributes = {}
for index in range(1, 21):
    topic = "A" if index <= 10 else "B"
    attributes[f"P{index:02d}"] = {
        "topic": topic,
        "features": [round(rng.uniform(0, 1), 3) for _ in range(4)],
    }
write("attributed_network.json", json.dumps(graph_json(False, attr_edges, attributes), ensure_ascii=False, indent=2) + "\n")

# ---------------------------------------------------------------- 9. 企业文本
# 句式严格对齐规则抽取引擎的三类模式：A与B+签署/达成/建立/开展/联合、
# A投资了B（句末）、A向B供应/提供/出售。“华为”与“华为公司”故意并存，
# 用于演示同指实体自动合并。
enterprise_text = """华为公司与宁德时代签署战略合作协议。
比亚迪与丰田达成合资协议。
华为与长安汽车开展换电合作。
宁德时代与上汽集团建立电池工厂。
丰田投资了小鹏汽车。
高通向小鹏汽车供应车载芯片。
赣锋锂业向宁德时代供应锂盐。
天齐锂业向比亚迪供应电池原料。
博世向上汽集团提供底盘系统。
采埃孚向小鹏汽车提供自动驾驶部件。
宁德时代与特斯拉达成供货协议。
华为公司与比亚迪建立智能驾驶合作。
"""
write("enterprise_relations.txt", enterprise_text)

print("\n全部数据集已生成到 data/ 文件夹。")
