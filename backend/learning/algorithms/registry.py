from __future__ import annotations

from copy import deepcopy
from typing import Any


def parameter(
    kind: str,
    default: Any,
    description: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
    choices: list[Any] | None = None,
) -> dict[str, Any]:
    value: dict[str, Any] = {"type": kind, "default": default, "description": description}
    if minimum is not None:
        value["minimum"] = minimum
    if maximum is not None:
        value["maximum"] = maximum
    if choices is not None:
        value["choices"] = choices
    return value


def spec(
    key: str,
    name: str,
    formula: str,
    explanation: str,
    advantages: list[str],
    limitations: list[str],
    *,
    graph_types: list[str] | None = None,
    parameters: dict[str, Any] | None = None,
    max_nodes: int = 5_000,
    max_edges: int = 50_000,
    version: str = "1.0",
) -> dict[str, Any]:
    return {
        "key": key,
        "name": name,
        "supported_graph_types": graph_types or ["directed", "undirected"],
        "parameters": parameters or {},
        "version": version,
        "description": explanation,
        "limits": {"max_nodes": max_nodes, "max_edges": max_edges},
        "formula": formula,
        "explanation": explanation,
        "advantages": advantages,
        "limitations": limitations,
    }


ITERATION_PARAMETERS = {
    "max_iterations": parameter("integer", 200, "最大迭代次数。", minimum=1, maximum=10_000),
    "tolerance": parameter("number", 1e-6, "收敛容差。", minimum=1e-12, maximum=0.1),
}
COMMUNITY_PARAMETERS = {
    "resolution": parameter("number", 1.0, "社区分辨率。", minimum=0.01, maximum=10),
    "communities": parameter("integer", 2, "目标社区数。", minimum=2, maximum=100),
}


ALGORITHM_REGISTRY: list[dict[str, Any]] = [
    spec("graph.validate", "图结构验证", "G=(V,E,w)", "验证图结构是否可用于后续分析。", ["错误定位到具体字段"], ["不评估数据的学科语义"]),
    spec("topology.summary", "网络拓扑摘要", "D=2m/[n(n-1)]", "计算规模、密度、连通分量、直径与平均路径。", ["快速建立整体印象"], ["聚合值会遮蔽局部差异"]),
    spec("paths.floyd", "Floyd 全源最短路", "d_ij=min(d_ij,d_ik+d_kj)", "用动态规划计算所有节点对最短路。", ["可同时观察全部节点对"], ["时间复杂度 O(n^3)"], max_nodes=500, max_edges=20_000),
    spec("clustering.coefficient", "聚类系数", "C_i=2T_i/[k_i(k_i-1)]", "衡量节点邻居彼此相连的程度。", ["易解释局部三角闭包"], ["低度节点信息有限"]),
    spec("model.er", "ER 随机图", "P((i,j)∈E)=p", "以独立连边概率生成 ER 网络并返回结构证据。", ["基准清晰、可复现"], ["不产生真实网络的高聚类和重尾"], graph_types=["undirected"], parameters={"n": parameter("integer", 30, "节点数。", minimum=1, maximum=2_000), "p": parameter("number", 0.1, "连边概率。", minimum=0, maximum=1)}),
    spec("model.ws", "WS 小世界图", "P(rewire)=p", "从规则环开始按概率重连，展示小世界证据。", ["兼具高聚类与短路径"], ["度分布不是幂律"], graph_types=["undirected"], parameters={"n": parameter("integer", 30, "节点数。", minimum=3, maximum=2_000), "k": parameter("integer", 4, "环上邻居数（偶数）。", minimum=2, maximum=100), "p": parameter("number", 0.1, "重连概率。", minimum=0, maximum=1)}),
    spec("model.ba", "BA 无标度图", "Π_i=k_i/Σ_j k_j", "按度比例优先连接，返回度分布等证据。", ["能生成枢纽与重尾"], ["忽略节点适应度和衰老"], graph_types=["undirected"], parameters={"n": parameter("integer", 30, "节点数。", minimum=2, maximum=2_000), "m": parameter("integer", 2, "新节点连边数。", minimum=1, maximum=100)}),
]


for key, name, formula, explanation, advantages, limitations in [
    ("centrality.degree", "度中心性", "C_D(i)=k_i/(n-1)", "衡量直接联系数量。", ["直观、计算快"], ["忽略间接关系"]),
    ("centrality.closeness", "接近中心性", "C_C(i)=(n-1)/Σ_j d(i,j)", "衡量节点到其他节点的平均距离。", ["反映传播效率"], ["非连通图需修正"]),
    ("centrality.betweenness", "中介中心性", "C_B(v)=Σ_st σ_st(v)/σ_st", "衡量节点位于最短路上的比例。", ["识别桥梁与经纪人"], ["大图计算开销高"]),
    ("centrality.eigenvector", "特征向量中心性", "Ax=λx", "与高分节点相连会获得更高分数。", ["考虑邻居质量"], ["非连通图可集中于主分量"]),
    ("centrality.pagerank", "PageRank", "r=αP^T r+(1-α)/n", "用随机游走稳态概率衡量影响力。", ["适用有向网络且抗死端"], ["结果受阻尼系数影响"]),
    ("centrality.hits", "HITS 枢纽-权威", "a=A^T h, h=Aa", "同时估计权威值与枢纽值。", ["区分引用与被引用角色"], ["对紧密子图敏感"]),
    ("centralization.degree", "度中心势", "C_D=Σ_i(C_D^*-C_D(i))/max", "衡量整体网络围绕最中心节点的程度。", ["便于跨网络比较"], ["不描述多中心结构"]),
]:
    params = {"alpha": parameter("number", 0.85, "阻尼系数。", minimum=0, maximum=1), **ITERATION_PARAMETERS} if key == "centrality.pagerank" else (ITERATION_PARAMETERS if key in {"centrality.eigenvector", "centrality.hits"} else {})
    ALGORITHM_REGISTRY.append(spec(key, name, formula, explanation, advantages, limitations, parameters=params))


community_metadata = [
    ("community.kernighan_lin", "Kernighan–Lin 二分", "min cut(A,B)", "交换节点以降低两组间割边。", ["快速二分"], ["仅直接产生两组"]),
    ("community.agglomerative", "凝聚层次社区", "ΔQ=max merge(C_i,C_j)", "从单节点社区逐步合并模块度增益最大的社区。", ["可解释合并路径"], ["贪心合并不可回退"]),
    ("community.divisive", "分裂层次社区", "remove argmax e_B(e)", "逐步移除边中介性最高的边形成分裂层次。", ["能显示桥边"], ["大图上计算较慢"]),
    ("community.girvan_newman", "Girvan–Newman", "remove argmax e_B(e)", "用边中介性递归分裂社区。", ["层次结果直观"], ["需反复计算边中介性"]),
    ("community.fast_newman", "Fast Newman 贪心模块度", "ΔQ=max merge(C_i,C_j)", "贪心合并使模块度增益最大的社区。", ["无需预设社区数"], ["存在分辨率极限"]),
    ("community.louvain", "Louvain", "Q=(1/2m)Σ_ij[A_ij-γk_ik_j/(2m)]δ(c_i,c_j)", "交替局部移动与社区聚合优化模块度。", ["大图上高效"], ["可产生内部不连通社区"]),
    ("community.leiden", "Leiden", "refine(Louvain,Q)", "在 Louvain 基础上加入精炼保证更好的社区连通性。", ["社区连通性与收敛性更好"], ["需要 igraph/leidenalg；缺失时明示回退 Louvain"]),
    ("community.lpa", "标签传播 LPA", "c_i=mode{c_j:j∈N(i)}", "节点反复采用邻居中最常见的标签。", ["近线性、无需社区数"], ["随机顺序会影响结果"]),
    ("community.cpm", "CPM 派系渗透法", "C_i∼C_j iff |C_i∩C_j|=k-1", "将共享 k-1 个节点的 k-派系连成允许重叠的社区。", ["自然表示重叠社区"], ["结果对派系大小 k 敏感"]),
    ("community.lfm", "LFM 重叠社区", "f_G=k_in/(k_in+k_out)^α", "从种子出发扩展局部适应度社区。", ["允许节点属于多个社区"], ["对种子与参数敏感"]),
    ("community.slpa", "SLPA 话者-听者标签传播", "P(l|i)=count_i(l)/T", "节点在多轮交互中积累标签记忆并阈值化。", ["自然支持重叠社区"], ["阈值与迭代次数影响结果"]),
]
for key, name, formula, explanation, advantages, limitations in community_metadata:
    if key in {"community.agglomerative", "community.divisive", "community.girvan_newman"}:
        params = {"communities": deepcopy(COMMUNITY_PARAMETERS["communities"])}
    elif key in {"community.fast_newman", "community.louvain", "community.leiden"}:
        params = {"resolution": deepcopy(COMMUNITY_PARAMETERS["resolution"])}
    elif key == "community.lfm":
        params = {"alpha": parameter("number", 1.0, "LFM 局部适应度指数。", minimum=0.1, maximum=10)}
    else:
        params = {}
    if key == "community.cpm":
        params["clique_size"] = parameter("integer", 3, "渗透派系大小 k。", minimum=2, maximum=20)
    if key == "community.slpa":
        params.update({"iterations": parameter("integer", 50, "传播轮数。", minimum=1, maximum=1_000), "threshold": parameter("number", 0.1, "标签保留频率。", minimum=0, maximum=1)})
    ALGORITHM_REGISTRY.append(spec(key, name, formula, explanation, advantages, limitations, graph_types=["undirected"], parameters=params, max_nodes=2_000, max_edges=20_000))


ALGORITHM_REGISTRY.extend([
    spec("robustness.attack", "网络鲁棒性攻击", "S(q)=|GCC_q|/N, R=(1/(N+1))Σ_q S(q)", "在随机或针对性删节点下跟踪最大连通分量。", ["直接比较攻击策略"], ["只用连通性表示功能"], graph_types=["undirected"], parameters={"strategy": parameter("string", "random", "删除策略。", choices=["random", "degree", "betweenness"])}),
])


for key, name, formula, limitation in [
    ("link_prediction.common_neighbors", "共同邻居 CN", "s(x,y)=|Γ(x)∩Γ(y)|", "偏好高度节点"),
    ("link_prediction.jaccard", "Jaccard 链路预测", "s=|Γ(x)∩Γ(y)|/|Γ(x)∪Γ(y)|", "小邻域可产生高方差"),
    ("link_prediction.adamic_adar", "Adamic–Adar", "s=Σ_z 1/log k_z", "度为 1 的共同邻居无法贡献"),
    ("link_prediction.resource_allocation", "资源分配 RA", "s=Σ_z 1/k_z", "只利用二阶局部结构"),
]:
    ALGORITHM_REGISTRY.append(spec(key, name, formula, "对尚未相连的节点对计算局部相似度，并用先隐藏测试边的 AUC 评估。", ["无监督、可解释"], [limitation], graph_types=["undirected"], parameters={"test_fraction": parameter("number", 0.2, "AUC 留出边比例。", minimum=0, maximum=0.8)}))


opinion_specs = [
    ("opinion.degroot", "DeGroot 意见模型", "x(t+1)=Wx(t)", "行随机影响矩阵下的线性平均。", ["简洁且可分析收敛"], ["不表示固执与有界信任"]),
    ("opinion.friedkin_johnsen", "Friedkin–Johnsen", "x(t+1)=Λx(0)+(I-Λ)Wx(t)", "将初始意见的固执度加入 DeGroot。", ["能表示持续分歧"], ["需估计固执度"]),
    ("opinion.deffuant", "Deffuant 有界信任", "|x_i-x_j|≤ε ⇒ x_i+=μ(x_j-x_i)", "随机边上的成对交互只在意见距离足够小时发生。", ["能生成意见簇"], ["对交互时序敏感"]),
    ("opinion.hk", "Hegselmann–Krause", "x_i(t+1)=mean{x_j:|x_j-x_i|≤ε}", "同步平均有界信任邻居的意见。", ["簇形成过程直观"], ["同步更新是强假设"]),
]
for key, name, formula, explanation, advantages, limitations in opinion_specs:
    params = {
        "opinions": parameter("object", {}, "节点初始意见（0–1）。"),
        **ITERATION_PARAMETERS,
        "confidence": parameter("number", 0.3, "有界信任阈值。", minimum=0, maximum=1),
        "stubbornness": parameter("number", 0.3, "FJ 固执度。", minimum=0, maximum=1),
        "mu": parameter("number", 0.5, "Deffuant 妥协速率。", minimum=0, maximum=0.5),
        "steps": parameter("integer", 500, "Deffuant 交互次数。", minimum=1, maximum=100_000),
    }
    ALGORITHM_REGISTRY.append(spec(key, name, formula, explanation, advantages, limitations, parameters=params, max_nodes=2_000))


ALGORITHM_REGISTRY.extend([
    spec("community.dynamic", "动态社区事件", "J(C_t,C_{t+1})=|A∩B|/|A∪B|", "用 Jaccard 匹配跨快照社区，识别延续、出生、消亡、分裂与合并。", ["事件可追溯"], ["匹配结果受阈值影响"], graph_types=["undirected"], parameters={"snapshots": parameter("array", [], "按时间排序的图快照。"), "snapshot_communities": parameter("array", [], "可选的已知社区。"), "threshold": parameter("number", 0.3, "Jaccard 匹配阈值。", minimum=0, maximum=1)}, max_nodes=2_000),
    spec("embedding.ae", "AE 自编码嵌入聚类", "Z=tanh(XW_e), X̂=ZW_d", "在 CPU 上训练邻接重构自编码，对嵌入做 k-means。", ["非线性压缩结构特征"], ["未显式利用卷积局部性"], graph_types=["undirected"], parameters={"clusters": parameter("integer", 2, "聚类数。", minimum=1, maximum=50), "embedding_dim": parameter("integer", 2, "嵌入维数。", minimum=1, maximum=64), "epochs": parameter("integer", 100, "训练轮数。", minimum=1, maximum=2_000), "learning_rate": parameter("number", 0.05, "学习率。", minimum=1e-5, maximum=1)}, max_nodes=1_000),
    spec("embedding.cnn", "CNN 卷积嵌入聚类", "Z=pool(ReLU(X*K)), X̂=ZW_d", "在 CPU 上训练一维卷积邻接重构器，再对嵌入聚类。", ["捕捉邻接序列的局部模式"], ["对节点排序敏感"], graph_types=["undirected"], parameters={"clusters": parameter("integer", 2, "聚类数。", minimum=1, maximum=50), "embedding_dim": parameter("integer", 2, "卷积核数/嵌入维数。", minimum=1, maximum=64), "epochs": parameter("integer", 100, "训练轮数。", minimum=1, maximum=2_000), "learning_rate": parameter("number", 0.03, "学习率。", minimum=1e-5, maximum=1)}, max_nodes=1_000),
    spec("embedding.gcn", "GCN 嵌入适配器", "H'=σ(D̃^-1/2 Ã D̃^-1/2 HW)", "在可选 PyTorch 能力存在时执行 CPU GCN 邻接重构聚类。", ["显式聚合图邻域"], ["需可选 torch 模型运行时"], graph_types=["undirected"], parameters={"clusters": parameter("integer", 2, "聚类数。", minimum=1, maximum=50), "embedding_dim": parameter("integer", 2, "嵌入维数。", minimum=1, maximum=64), "epochs": parameter("integer", 100, "训练轮数。", minimum=1, maximum=2_000), "learning_rate": parameter("number", 0.03, "学习率。", minimum=1e-5, maximum=1)}, max_nodes=1_000),
    spec("embedding.gat", "GAT 嵌入适配器", "h'_i=σ(Σ_j α_ij Wh_j)", "在可选 PyTorch Geometric 能力存在时执行 CPU 注意力嵌入。", ["可学习邻居权重"], ["需可选 torch-geometric 模型运行时"], graph_types=["undirected"], parameters={"clusters": parameter("integer", 2, "聚类数。", minimum=1, maximum=50), "embedding_dim": parameter("integer", 2, "嵌入维数。", minimum=1, maximum=64), "epochs": parameter("integer", 100, "训练轮数。", minimum=1, maximum=2_000), "learning_rate": parameter("number", 0.03, "学习率。", minimum=1e-5, maximum=1)}, max_nodes=1_000),
    spec("text.extract", "中文实体关系建网", "w_ij=cos(v_i,v_j) or normalize(count_ij)", "确定性预处理后生成可校正的实体/关系候选与归一化边权。", ["证据、偏移与置信度可校正"], ["规则模弋可漏掉隐含关系；模型适配器需本地能力"], parameters={"text": parameter("string", "", "待抽取中文文本。"), "method": parameter("string", "rule", "实体/关系方法。", choices=["rule", "paddlenlp"]), "embedding": parameter("string", "cosine", "边权方法。", choices=["cosine", "normalized", "bge"]), "model_path": parameter("string", "", "可选本地模型路径。")}, max_nodes=10_000),
    spec("export.graph", "标准图导出", "serialize(G,format)", "以确定顺序导出 JSON、CSV、GraphML、GEXF、GML、Pajek、边表或邻接矩阵。", ["格式广泛且可复现"], ["部分文本格式不保留复杂属性"], parameters={"format": parameter("string", "json", "导出格式。", choices=["json", "csv", "graphml", "gexf", "gml", "pajek", "edgelist", "adjacency"])}),
])


REGISTRY_BY_KEY = {item["key"]: item for item in ALGORITHM_REGISTRY}


def get_registry() -> list[dict[str, Any]]:
    return deepcopy(ALGORITHM_REGISTRY)
