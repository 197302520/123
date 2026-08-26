from __future__ import annotations

import networkx as nx
from django.core.management.base import BaseCommand
from networkx.algorithms import bipartite

from learning.algorithms.graph import nx_to_graph
from learning.data.sarasota_dolphins import EDGES as DOLPHIN_EDGES, NODES as DOLPHIN_NODES
from learning.models import Case, CourseModule, Dataset, PublishStatus


MODULES = [
    ("network-basics", "模块一：网络基础", "用图表示社会关系。"),
    ("network-measures", "模块二：网络测量", "比较中心性与网络结构。"),
    ("communities", "模块三：社区发现", "识别网络中的群体边界。"),
    ("diffusion", "模块四：扩散与传播", "观察信息与意见的传播。"),
    ("robustness", "模块五：鲁棒性", "分析网络面对攻击时的连通性。"),
    ("link-prediction", "模块六：链接预测", "从结构中推断潜在关系。"),
    ("dynamic-networks", "模块七：动态网络", "追踪关系与社群的时间变化。"),
]


def graph(nodes, edges, *, directed=False):
    return {
        "directed": directed,
        "nodes": [{"id": str(node), "label": str(node)} for node in nodes],
        "edges": [
            {"source": str(edge[0]), "target": str(edge[1]), "weight": float(edge[2] if len(edge) > 2 else 1)}
            for edge in edges
        ],
    }


def case_definitions():
    karate_network = nx.karate_club_graph()
    karate = nx_to_graph(karate_network)
    karate_attributes = {str(node): {"faction": values["club"]} for node, values in karate_network.nodes(data=True)}

    dolphins = graph(DOLPHIN_NODES, ((*edge, 1) for edge in DOLPHIN_EDGES))

    memberships = {
        "P1": ["C1", "C2"], "P2": ["C1"], "P3": ["C1", "C2"], "P4": ["C2", "C3"],
        "P5": ["C3"], "P6": ["C3", "C4"], "P7": ["C4"], "P8": ["C2", "C4"],
    }
    bipartite_network = nx.Graph()
    bipartite_network.add_nodes_from(memberships, bipartite="player")
    clubs = sorted({club for values in memberships.values() for club in values})
    bipartite_network.add_nodes_from(clubs, bipartite="club")
    bipartite_network.add_edges_from((player, club) for player, values in memberships.items() for club in values)
    projection = bipartite.weighted_projected_graph(bipartite_network, sorted(memberships))
    football_projection = nx_to_graph(projection)
    football_source = {
        "directed": True,
        "nodes": ([{"id": player, "label": player, "attributes": {"kind": "player"}} for player in memberships]
                  + [{"id": club, "label": club, "attributes": {"kind": "club"}} for club in clubs]),
        "edges": [{"source": player, "target": club, "weight": 1.0} for player, values in memberships.items() for club in values],
    }

    empty_graph = {"directed": True, "nodes": [], "edges": []}
    enterprise_text = "云帆科技与星河数据建立联合实验室。青松资本投资云帆科技。星河数据向海岳制造提供数据服务。"

    countries = ["中国", "日本", "韩国", "德国", "法国", "意大利"]
    trade_snapshots = [
        graph(countries, [("中国", "日本", 4), ("中国", "韩国", 3), ("日本", "韩国", 2), ("德国", "法国", 4), ("法国", "意大利", 3), ("德国", "意大利", 2)]),
        graph(countries, [("中国", "日本", 4), ("中国", "韩国", 3), ("日本", "德国", 1), ("德国", "法国", 4), ("法国", "意大利", 3), ("韩国", "意大利", 1)]),
        graph(countries, [("中国", "日本", 3), ("日本", "德国", 2), ("德国", "法国", 4), ("法国", "意大利", 3), ("韩国", "意大利", 2), ("中国", "韩国", 2)]),
    ]

    people = ["甲", "乙", "丙", "丁", "戊", "己"]
    opinion_graph = graph(people, [("甲", "乙"), ("乙", "丙"), ("丙", "丁"), ("丁", "戊"), ("戊", "己"), ("乙", "戊", 0.5)])

    papers = [f"paper-{index}" for index in range(1, 9)]
    citation_graph = graph(papers, [
        ("paper-2", "paper-1"), ("paper-3", "paper-1"), ("paper-3", "paper-2"),
        ("paper-4", "paper-2"), ("paper-5", "paper-2"), ("paper-5", "paper-3"),
        ("paper-6", "paper-3"), ("paper-7", "paper-4"), ("paper-7", "paper-5"),
        ("paper-8", "paper-5"), ("paper-8", "paper-6"),
    ], directed=True)
    citation_attributes = {
        paper: {"topic": ["神经网络", "概率方法", "图学习"][index % 3], "features": [index % 2, (index + 1) % 2, 1]}
        for index, paper in enumerate(papers)
    }
    for node in citation_graph["nodes"]:
        node["attributes"] = citation_attributes[node["id"]]

    generated = "仓库内确定性生成的教学数据；未复制外部个体记录。"
    cc0 = "CC0-1.0（本项目生成数据）"
    return [
        {
            "slug": "zachary-karate", "title": "Zachary 空手道俱乐部", "case_title": "空手道俱乐部网络",
            "summary": "用经典俱乐部关系检验社区边界。", "module": "communities",
            "provenance": "Wayne W. Zachary (1977), An Information Flow Model for Conflict and Fission in Small Groups；由 NetworkX karate_club_graph 打包。",
            "metadata": {"source": "Zachary (1977)；NetworkX 3.x karate_club_graph", "license": "NetworkX BSD-3-Clause；原始事实拓扑按论文完整署名", "cleaning": "节点转为稳定字符串 ID；无向边权保留为数值", "version": "2026.08-v1", "graph": karate, "node_attributes": karate_attributes, "algorithm": "community.louvain", "parameters": {"resolution": 1.0}, "seed": 7},
        },
        {
            "slug": "dolphins", "title": "Sarasota 海豚社群网络（Lusseau 数据）", "case_title": "海豚社群重叠社区划分",
            "summary": "在真实海豚关联网络上用 CPM 派系渗透与 SLPA 划分重叠社区，并配合链路预测算法做对比实验。",
            "module": "communities",
            "provenance": "D. Lusseau, K. Schneider, O. J. Boisseau, P. Haase, E. Slooten & S. M. Dawson (2003), The bottlenose dolphin community of Doubtful Sound features a large proportion of long-lasting associations, Behavioral Ecology and Sociobiology 54:396-405；经 M. E. J. Newman 网络数据仓库（dolphins.gml）分发。野外观测地点为新西兰 Doubtful Sound，教学说明书沿用 Sarasota 海豚社群称谓。",
            "metadata": {"source": "Lusseau et al. (2003)；Newman 网络数据仓库 dolphins.gml", "license": "学术引用使用：课堂教学须引用 Lusseau et al. (2003) 原文", "cleaning": "保留原始个体名称作为节点 ID；GML 节点编号映射为海豚名；边权统一为 1", "version": "2026.08-v2", "graph": dolphins, "algorithm": "community.cpm", "parameters": {"clique_size": 3}, "seed": 13},
        },
        {
            "slug": "football-bipartite", "title": "生成式球员—俱乐部二部网络", "case_title": "球员流动与俱乐部投影",
            "summary": "从球员—俱乐部隶属关系投影出球员共队网络。", "module": "network-basics",
            "provenance": "本项目生成的虚构球员与俱乐部隶属关系。",
            "metadata": {"source": generated, "license": cc0, "cleaning": "二部图方向统一为球员→俱乐部；附带按共同俱乐部数加权的球员投影视图", "version": "2026.08-v2", "graph": football_source, "projection_graph": football_projection, "projection": "networkx weighted_projected_graph(players)", "algorithm": "centrality.hits", "parameters": {"max_iterations": 200, "tolerance": 1e-6}, "seed": 5},
        },
        {
            "slug": "enterprise-text", "title": "生成式企业关系文本", "case_title": "从企业文本抽取关系网络",
            "summary": "用可校正规则从中文企业叙述生成实体关系候选。", "module": "network-basics",
            "provenance": "本项目编写的虚构企业语句。",
            "metadata": {"source": generated, "license": cc0, "cleaning": "NFKC 规范化；保留证据偏移；不含真实企业事实", "version": "2026.08-v1", "graph": empty_graph, "algorithm": "text.extract", "parameters": {"text": enterprise_text, "method": "rule", "embedding": "normalized", "model_path": ""}, "seed": 0},
        },
        {
            "slug": "trade-snapshots", "title": "生成式贸易时间快照", "case_title": "贸易网络中的动态社群",
            "summary": "比较三个时间快照中的社群延续、分裂与合并。", "module": "dynamic-networks",
            "provenance": "本项目生成的六国贸易教学快照；权重为虚构课堂数值。",
            "metadata": {"source": generated, "license": cc0, "cleaning": "统一国家名称；快照均为无向正权图", "version": "2026.08-v1", "graph": trade_snapshots[0], "algorithm": "community.dynamic", "parameters": {"snapshots": trade_snapshots, "snapshot_communities": [], "threshold": 0.3}, "seed": 17},
        },
        {
            "slug": "opinion-dynamics", "title": "生成式课堂意见网络", "case_title": "意见如何在关系中趋同",
            "summary": "运行 DeGroot 模型观察初始分歧的收敛轨迹。", "module": "diffusion",
            "provenance": "本项目生成的匿名角色网络与初始意见。",
            "metadata": {"source": generated, "license": cc0, "cleaning": "角色使用甲乙丙丁戊己；意见缩放到 0–1", "version": "2026.08-v1", "graph": opinion_graph, "algorithm": "opinion.degroot", "parameters": {"opinions": {"甲": 0.1, "乙": 0.2, "丙": 0.35, "丁": 0.7, "戊": 0.85, "己": 0.95}, "max_iterations": 200, "tolerance": 1e-6}, "seed": 23},
        },
        {
            "slug": "cora-citations", "title": "生成式 Cora 风格属性引用网络", "case_title": "属性论文引用与影响力",
            "summary": "在小型有向引用图上联合结构与主题特征生成属性嵌入。", "module": "network-measures",
            "provenance": "本项目生成的 Cora 风格结构；不复制 Cora 原始论文、标签或特征。",
            "metadata": {"source": generated, "license": cc0, "cleaning": "虚构 paper ID；三维二值特征与主题标签嵌入节点 attributes", "version": "2026.08-v2", "graph": citation_graph, "algorithm": "embedding.ae", "parameters": {"clusters": 3, "embedding_dim": 2, "epochs": 40, "learning_rate": 0.03}, "seed": 29},
        },
    ]


class Command(BaseCommand):
    help = "Idempotently seed seven modules and seven runnable, provenance-recorded cases."

    def handle(self, *args, **options):
        modules: dict[str, CourseModule] = {}
        for order, (slug, title, summary) in enumerate(MODULES, start=1):
            module, _ = CourseModule.objects.update_or_create(
                slug=slug,
                defaults={"title": title, "summary": summary, "order": order, "status": PublishStatus.PUBLISHED},
            )
            modules[slug] = module
        for definition in case_definitions():
            dataset, _ = Dataset.objects.update_or_create(
                slug=definition["slug"],
                defaults={
                    "title": definition["title"], "provenance": definition["provenance"],
                    "metadata": definition["metadata"], "status": PublishStatus.PUBLISHED,
                },
            )
            Case.objects.update_or_create(
                slug=definition["slug"],
                defaults={
                    "module": modules[definition["module"]], "dataset": dataset,
                    "title": definition["case_title"], "summary": definition["summary"],
                    "content": "按问题—数据—方法—运行—解释—反思六步完成案例，并下载复现包核验结论。",
                    "status": PublishStatus.PUBLISHED,
                },
            )
        self.stdout.write(self.style.SUCCESS("Seeded seven modules and seven runnable case records."))
