from __future__ import annotations

import networkx as nx
from django.core.management.base import BaseCommand

from learning.algorithms.graph import nx_to_graph
from learning.data.sarasota_dolphins import EDGES as DOLPHIN_EDGES, NODES as DOLPHIN_NODES
from learning.data.worldcup_football import (
    CODE_INFO as FOOTBALL_CODE_INFO,
    WC1998_EDGES,
    WC1998_NODES,
    WC2002_EDGES,
    WC2002_NODES,
)
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


def football_network(nodes, edges):
    return {
        "directed": True,
        "nodes": [
            {
                "id": code,
                "label": FOOTBALL_CODE_INFO[code][0],
                "attributes": {"code": code, "continent": FOOTBALL_CODE_INFO[code][1]},
            }
            for code in nodes
        ],
        "edges": [
            {"source": source, "target": target, "weight": float(weight)}
            for source, target, weight in edges
        ],
    }


def case_definitions():
    karate_network = nx.karate_club_graph()
    karate = nx_to_graph(karate_network)
    karate_attributes = {str(node): {"faction": values["club"]} for node, values in karate_network.nodes(data=True)}

    dolphins = graph(DOLPHIN_NODES, ((*edge, 1) for edge in DOLPHIN_EDGES))

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
            "metadata": {"source": "Zachary (1977)；NetworkX 3.x karate_club_graph", "license": "NetworkX BSD-3-Clause；原始事实拓扑按论文完整署名", "cleaning": "节点转为稳定字符串 ID；无向边权保留为数值", "version": "2026.08-v1", "graph": karate, "node_attributes": karate_attributes, "algorithm": "community.louvain", "parameters": {"resolution": 1.0}, "seed": 7,
                "demos": [
                    {"algorithm": "community.compare", "label": "多算法社区发现对比", "focus": "看哪种算法的模块度 Q 最高；社区划分是否接近俱乐部真实的两派分裂？", "seed": 7},
                    {"algorithm": "centrality.betweenness", "label": "中介中心性：找出桥梁人物", "focus": "谁的度不高却占据大量最短路？他是不是校长与教官之间的桥梁？", "seed": 7},
                    {"algorithm": "robustness.attack", "label": "蓄意攻击下的网络韧性", "focus": "按度删点时 S(q) 曲线何时断崖？换随机攻击再对比一次", "parameters": {"strategy": "degree"}, "seed": 7},
                ]},
        },
        {
            "slug": "dolphins", "title": "Sarasota 海豚社群网络（Lusseau 数据）", "case_title": "海豚社群重叠社区划分",
            "summary": "在真实海豚关联网络上用 CPM 派系渗透与 SLPA 划分重叠社区，并配合链路预测算法做对比实验。",
            "module": "communities",
            "provenance": "D. Lusseau, K. Schneider, O. J. Boisseau, P. Haase, E. Slooten & S. M. Dawson (2003), The bottlenose dolphin community of Doubtful Sound features a large proportion of long-lasting associations, Behavioral Ecology and Sociobiology 54:396-405；经 M. E. J. Newman 网络数据仓库（dolphins.gml）分发。野外观测地点为新西兰 Doubtful Sound，教学说明书沿用 Sarasota 海豚社群称谓。",
            "metadata": {"source": "Lusseau et al. (2003)；Newman 网络数据仓库 dolphins.gml", "license": "学术引用使用：课堂教学须引用 Lusseau et al. (2003) 原文", "cleaning": "保留原始个体名称作为节点 ID；GML 节点编号映射为海豚名；边权统一为 1", "version": "2026.08-v2", "graph": dolphins, "algorithm": "community.cpm", "parameters": {"clique_size": 3}, "seed": 13,
                "demos": [
                    {"algorithm": "community.cpm", "label": "CPM 派系过滤：重叠社区", "focus": "哪些海豚同时出现在两个社区？把 clique_size 改成 4 社区怎么变？", "parameters": {"clique_size": 3}, "seed": 13},
                    {"algorithm": "link_prediction.adamic_adar", "label": "链路预测与防泄漏 AUC", "focus": "最可能新出现的海豚关联是哪几对？AUC 离 1 有多远？", "seed": 13},
                ]},
        },
        {
            "slug": "football-wc1998", "title": "1998 法国世界杯球员流动网络", "case_title": "世界杯国脚的跨国流动（1998）",
            "summary": "把每支国家队阵容按球员效力俱乐部的所在国连成有向加权网络：谁是球员输出国，哪个联赛吸纳了全世界。",
            "module": "network-basics",
            "provenance": "Pajek datasets（V. Batagelj & A. Mrvar，http://vlado.fmf.uni-lj.si/pub/networks/data/）的 football.net（1998 法国世界杯；SuiteSparse 收录名 World Soccer, Paris 1998）：35 个国家/地区、118 条弧。边权为该届世界杯阵容中效力东道国联赛的球员人数，全员本土踢球的阵容不形成边（如沙特阿拉伯，故无节点）；未参赛但吸纳外国国脚的联赛国家只有入边。由任课教师提供的课堂数据文件转换，可用 scripts/make_worldcup_data.py 复现。",
            "metadata": {"source": "任课教师课堂数据：Pajek datasets football.net（Batagelj & Mrvar）", "license": "学术引用使用：课堂教学须注明 Batagelj & Mrvar Pajek datasets 出处", "cleaning": "保留原文件节点代码、弧方向与权重；节点附中文译名与大洲属性；节点按原文件编号顺序排列", "version": "2026.09-v1", "graph": football_network(WC1998_NODES, WC1998_EDGES), "algorithm": "centrality.hits", "parameters": {"max_iterations": 200, "tolerance": 1e-6}, "seed": 5,
                "demos": [
                    {"algorithm": "centrality.degree", "label": "度中心性：球员流动中的枢纽国家", "focus": "总度数高的国家是单纯输出、单纯吸纳，还是两者兼备？对照有向边的方向读出净流出与净流入。", "seed": 5},
                    {"algorithm": "centrality.hits", "label": "HITS 枢纽-权威：输出国对阵东道国", "focus": "枢纽值高＝大量向外输送国脚的国家，权威值高＝吸纳各国国脚的联赛强国——1998 年的权威榜首是谁？", "parameters": {"max_iterations": 200, "tolerance": 1e-6}, "seed": 5},
                    {"algorithm": "centrality.pagerank", "label": "PageRank：联赛影响力榜单", "focus": "把 PageRank 排名与 HITS 权威榜对照：前几名一致吗？为什么亚非国家的国脚几乎只流向同一批欧洲联赛？", "seed": 5},
                ]},
        },
        {
            "slug": "football-wc2002", "title": "2002 韩日世界杯球员流动网络", "case_title": "世界杯国脚的跨国流动（2002）",
            "summary": "同一套球员流动网络推进到韩日世界杯：44 个国家/地区、147 条流动关系，看四年之间联赛格局的变化。",
            "module": "network-basics",
            "provenance": "Pajek datasets（V. Batagelj & A. Mrvar，http://vlado.fmf.uni-lj.si/pub/networks/data/）的 football2002.net（2002 韩日世界杯）：44 个国家/地区、147 条弧。边权为该届世界杯阵容中效力东道国联赛的球员人数，全员本土踢球的阵容不形成边；未参赛但吸纳外国国脚的联赛国家（如荷兰、克罗地亚）只有入边。由任课教师提供的课堂数据文件转换，可用 scripts/make_worldcup_data.py 复现。",
            "metadata": {"source": "任课教师课堂数据：Pajek datasets football2002.net（Batagelj & Mrvar）", "license": "学术引用使用：课堂教学须注明 Batagelj & Mrvar Pajek datasets 出处", "cleaning": "保留原文件节点代码、弧方向与权重；节点附中文译名与大洲属性；节点按原文件编号顺序排列", "version": "2026.09-v1", "graph": football_network(WC2002_NODES, WC2002_EDGES), "algorithm": "centrality.hits", "parameters": {"max_iterations": 200, "tolerance": 1e-6}, "seed": 5,
                "demos": [
                    {"algorithm": "centrality.degree", "label": "度中心性：球员流动中的枢纽国家", "focus": "总度数高的国家是单纯输出、单纯吸纳，还是两者兼备？对照有向边的方向读出净流出与净流入。", "seed": 5},
                    {"algorithm": "centrality.hits", "label": "HITS 枢纽-权威：输出国对阵东道国", "focus": "枢纽值高＝大量向外输送国脚的国家，权威值高＝吸纳各国国脚的联赛强国——2002 年的权威榜首换成了谁？", "parameters": {"max_iterations": 200, "tolerance": 1e-6}, "seed": 5},
                    {"algorithm": "centrality.pagerank", "label": "PageRank：联赛影响力榜单", "focus": "塞内加尔 21 名国脚全部效力法甲，这样的『全队流向一条边』会怎样抬高法国的分数？和 1998 年的榜单比一比。", "seed": 5},
                ]},
        },
        {
            "slug": "enterprise-text", "title": "生成式企业关系文本", "case_title": "从企业文本抽取关系网络",
            "summary": "用可校正规则从中文企业叙述生成实体关系候选。", "module": "network-basics",
            "provenance": "本项目编写的虚构企业语句。",
            "metadata": {"source": generated, "license": cc0, "cleaning": "NFKC 规范化；保留证据偏移；不含真实企业事实", "version": "2026.08-v1", "graph": empty_graph, "algorithm": "text.extract", "parameters": {"text": enterprise_text, "method": "rule", "embedding": "normalized", "model_path": ""}, "seed": 0,
                "demos": [
                    {"algorithm": "text.extract", "label": "文本抽取：实体、关系与同指合并", "focus": "数一数抽出多少家公司？『华为』和『华为公司』有没有被合并成一个节点？", "parameters": {"text": enterprise_text, "method": "rule", "embedding": "normalized", "merge_threshold": 0.6, "model_path": ""}, "seed": 0},
                ]},
        },
        {
            "slug": "trade-snapshots", "title": "生成式贸易时间快照", "case_title": "贸易网络中的动态社群",
            "summary": "比较三个时间快照中的社群延续、分裂与合并。", "module": "dynamic-networks",
            "provenance": "本项目生成的六国贸易教学快照；权重为虚构课堂数值。",
            "metadata": {"source": generated, "license": cc0, "cleaning": "统一国家名称；快照均为无向正权图", "version": "2026.08-v1", "graph": trade_snapshots[0], "algorithm": "community.dynamic", "parameters": {"snapshots": trade_snapshots, "snapshot_communities": [], "threshold": 0.3}, "seed": 17,
                "demos": [
                    {"algorithm": "community.dynamic", "label": "三期快照：社群的延续与合并", "focus": "时间线里出现了哪几类事件？把阈值 0.3 改成 0.6 事件怎么变？", "parameters": {"snapshots": trade_snapshots, "snapshot_communities": [], "threshold": 0.3}, "seed": 17},
                    {"algorithm": "community.louvain", "label": "基线快照的静态社区", "focus": "先看 t1 时刻有几个圈子，再对照动态事件理解‘从哪来、到哪去’", "seed": 17},
                ]},
        },
        {
            "slug": "opinion-dynamics", "title": "生成式课堂意见网络", "case_title": "意见如何在关系中趋同",
            "summary": "运行 DeGroot 模型观察初始分歧的收敛轨迹。", "module": "diffusion",
            "provenance": "本项目生成的匿名角色网络与初始意见。",
            "metadata": {"source": generated, "license": cc0, "cleaning": "角色使用甲乙丙丁戊己；意见缩放到 0–1", "version": "2026.08-v1", "graph": opinion_graph, "algorithm": "opinion.degroot", "parameters": {"opinions": {"甲": 0.1, "乙": 0.2, "丙": 0.35, "丁": 0.7, "戊": 0.85, "己": 0.95}, "max_iterations": 200, "tolerance": 1e-6}, "seed": 23,
                "demos": [
                    {"algorithm": "opinion.degroot", "label": "DeGroot：走向全体共识", "focus": "轨迹图上六条线最终汇聚了吗？观点方差归零了吗？", "parameters": {"opinions": {"甲": 0.1, "乙": 0.2, "丙": 0.35, "丁": 0.7, "戊": 0.85, "己": 0.95}, "max_iterations": 200, "tolerance": 1e-6}, "seed": 23},
                    {"algorithm": "opinion.deffuant", "label": "Deffuant：有界信任与极化", "focus": "把信任阈值 confidence 调小到 0.15 再跑一次——班级分裂成几派？", "parameters": {"opinions": {"甲": 0.1, "乙": 0.2, "丙": 0.35, "丁": 0.7, "戊": 0.85, "己": 0.95}, "confidence": 0.15, "mu": 0.5, "steps": 500, "tolerance": 1e-6}, "seed": 23},
                ]},
        },
        {
            "slug": "cora-citations", "title": "生成式 Cora 风格属性引用网络", "case_title": "属性论文引用与影响力",
            "summary": "在小型有向引用图上联合结构与主题特征生成属性嵌入。", "module": "network-measures",
            "provenance": "本项目生成的 Cora 风格结构；不复制 Cora 原始论文、标签或特征。",
            "metadata": {"source": generated, "license": cc0, "cleaning": "虚构 paper ID；三维二值特征与主题标签嵌入节点 attributes", "version": "2026.08-v2", "graph": citation_graph, "algorithm": "embedding.ae", "parameters": {"clusters": 3, "embedding_dim": 2, "epochs": 40, "learning_rate": 0.03}, "seed": 29,
                "demos": [
                    {"algorithm": "embedding.ae", "label": "自编码器嵌入聚类", "focus": "聚类结果和论文的主题标签一致吗？结构与属性各起了多大作用？", "parameters": {"clusters": 3, "embedding_dim": 2, "epochs": 40, "learning_rate": 0.03}, "seed": 29},
                    {"algorithm": "centrality.pagerank", "label": "PageRank 引用影响力", "focus": "被高质量论文引用最多的‘核心文献’是哪篇？", "seed": 29},
                ]},
        },
    ]


class Command(BaseCommand):
    help = "Idempotently seed seven modules and runnable, provenance-recorded cases."

    def handle(self, *args, **options):
        modules: dict[str, CourseModule] = {}
        for order, (slug, title, summary) in enumerate(MODULES, start=1):
            module, _ = CourseModule.objects.update_or_create(
                slug=slug,
                defaults={"title": title, "summary": summary, "order": order, "status": PublishStatus.PUBLISHED},
            )
            modules[slug] = module
        # 教师以真实世界杯球员流动数据替换了生成式二部图案例，历史种子记录一并下线。
        retired = Dataset.objects.filter(slug="football-bipartite")
        if retired.exists():
            Case.objects.filter(dataset=retired.first()).delete()
            retired.delete()
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
        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(MODULES)} modules and {len(case_definitions())} runnable case records."
        ))
