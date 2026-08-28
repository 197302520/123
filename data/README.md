# 实验数据集索引

本文件夹的数据集与《平台说明书》的算法模块一一对应，全部可在**自由实验室**
（`/lab`）通过「导入文件」或「粘贴边表」直接使用。所有数据集均通过平台
导入校验与算法实测（见文末验证记录）。

## 快速使用

1. 打开 <http://localhost:5173/lab>，点「导入文件」选择下面的 CSV / TXT / JSON 文件；
2. TXT / CSV 边表导入后默认为**无向图**——世界杯球员数据集请在编辑器里把图切换为**有向**（球员 → 俱乐部）；贸易数据集用 JSON 格式保存、自带 `directed: true`，导入即有向；
3. JSON 文件自带 `directed` 字段与节点属性，导入即用；
4. 观点模型与动态社区还需要把 `*.params.json` 里对应算法的参数块复制到参数编辑器（文件内有说明）。

## 数据集一览

| 文件 | 内容 | 格式 | 适配算法（说明书章节） |
| --- | --- | --- | --- |
| `karate_club.txt` | Zachary (1977) 空手道俱乐部，34 节点 78 边 | 边表 | 度/接近/中介/特征向量中心性（模块4）；GN、FN、Louvain、Leiden、LPA、KL（模块5）；随机/蓄意攻击（模块6）；拓扑摘要、Floyd、聚类系数（模块3） |
| `dolphins.csv` | Lusseau (2003) 海豚关联网络，62 节点 159 边 | CSV | CPM、LFM、SLPA 重叠社区（模块5）；CN、Jaccard、AA、RA 链路预测与 AUC（模块6）；Louvain/Leiden 对比 |
| `football_worldcup.csv` | 2022 世界杯八强 45 名球员 → 22 家俱乐部（有向二部） | CSV | 二部网表示与投影（模块1/2）；社区发现；度中心性（出/入度） |
| `trade_directed.json` | 14 经济体出口流向与量级（有向加权，单位十亿美元） | GraphSpec JSON | PageRank、HITS（模块4）；Floyd 最短路（模块3）；度中心性出/入度；中心势 |
| `power_grid_mini.csv` | 区域输电网 24 节点，边权 = 线路容量 | CSV | 网络韧性：最大连通子图占比、综合鲁棒性 R、随机 vs 蓄意攻击（模块6） |
| `opinion_classroom.json` | 12 人课堂讨论网（加权无向，两个观点阵营） | GraphML 式 JSON | DeGroot、FJ、Deffuant、HK（模块7），配 `opinion_models.params.json` |
| `opinion_models.params.json` | 四个观点模型的建议参数（含每人初始意见） | 参数 JSON | 同上 |
| `dynamic_alliance.json` | 14 家企业合作网 t1 快照（无向） | JSON | 动态社区（模块5/动态），配 `dynamic_alliance.params.json` |
| `dynamic_alliance.params.json` | t1–t3 三个快照 + Jaccard 匹配阈值 | 参数 JSON | 社区延续 / 分裂 / 合并事件识别 |
| `attributed_network.json` | 20 位研究者合作网：topic 属性 + 4 维特征（无向） | JSON | AE、CNN、GCN、GAT 嵌入聚类（模块5 深度学习社区） |
| `enterprise_relations.txt` | 新能源汽车产业链中文新闻文本 | 中文文本 | 中文实体关系建网：清洗、实体抽取、同指合并、关系频次（模块1）；导出 XLSX/GraphML 等（模块2） |

> 生成器：`python scripts/make_datasets.py` 可重新生成本文件夹（真实数据集
> 来自 NetworkX 与平台内置的 Lusseau 海豚数据）。

## 说明书算法覆盖对照

| 说明书模块 | 说明书要求 | 平台实现（42 种算法全部可运行） | 推荐数据集 |
| --- | --- | --- | --- |
| 模块1 文本预处理建网 | 清洗、实体识别、同指合并、关系抽取、频次统计 | `text.extract`（规则 + 可选本地模型；余弦/频次权重；语义合并） | `enterprise_relations.txt` |
| 模块2 数据导出 | XLSX/JSON/CSV/TXT/GraphML/GEXF/GML/Pajek | `export.graph`（8 种格式 + 邻接矩阵） | 任一数据集运行后导出 |
| 模块3 基础拓扑 | 度/平均度、Floyd、聚类系数、ER/WS/BA 判别 | `topology.summary`、`paths.floyd`、`clustering.coefficient`、`model.er/ws/ba`、`graph.validate` | `karate_club.txt`；ER/WS/BA 用平台生成器 |
| 模块4 中心性 | 度、接近、中介、特征向量、PageRank、HITS、中心势 | `centrality.*` 六种 + `centralization.degree` | `trade_directed.csv`（有向）、`karate_club.txt` |
| 模块5 社区发现 | 模块度、KL、层次、GN、FN、Louvain、Leiden、LPA、CPM、LFM、SLPA、GCN、GAT、AE、CNN、动态社区 | `community.*` 十四种 + `embedding.*` 四种 + `community.compare` 多算法对比 | `karate_club.txt`、`dolphins.csv`、`attributed_network.json`、`dynamic_alliance.*` |
| 模块6 韧性 + 链路预测 | 连通子图占比、R、随机/蓄意攻击；CN、Jaccard、AA、RA、AUC | `robustness.attack`；`link_prediction.*` 四种（内置 AUC 留出验证） | `power_grid_mini.csv`、`karate_club.txt`；`dolphins.csv` |
| 模块7 观点动力学 | DeGroot、FJ、Deffuant、HK、观点方差 | `opinion.*` 四种（轨迹图 + 方差曲线） | `opinion_classroom.json` |

## 验证记录（2026-08-27，`python scripts/verify_datasets.py` 实测）

全部 18 项通过：

- `karate_club.txt` → 导入 34 节点 78 边；`community.louvain` 完成（4 社区）；`robustness.attack(degree 蓄意攻击)` 完成；`centrality.betweenness` 完成（最高节点 0，0.438）
- `dolphins.csv` → 导入 62 节点 159 边；`community.cpm(clique_size=3)` 重叠社区完成；`link_prediction.adamic_adar` 完成
- `football_worldcup.csv` → 导入 71 节点 45 边；切有向后 `centrality.degree` 出/入度完成
- `trade_directed.json` → 导入 14 节点 41 边（有向）；`centrality.pagerank` 完成
- `power_grid_mini.csv` → 导入 24 节点 33 边；`robustness.attack(random)` 完成
- `opinion_classroom.json` + `opinion_models.params.json` → `opinion.degroot` 收敛（方差 6.1e-07）；`opinion.hk` 极化（最终极差 0.59）
- `dynamic_alliance.json` + `dynamic_alliance.params.json` → `community.dynamic` 识别出**延续 / 分裂 / 合并**三类事件（快照拓扑已按 Louvain 自动检测校准）
- `attributed_network.json` → `embedding.gcn` 嵌入聚类完成（`embedding.ae/cnn/gat` 参数结构相同）
- `enterprise_relations.txt` → `text.extract` 抽出 24 个实体、12 条关系、1 组同指合并（华为/华为公司）

## 数据来源与引用

- 空手道俱乐部：W. W. Zachary (1977). An information flow model for conflict and fission in small groups. *J. Anthropol. Res.* 33, 452–473（NetworkX BSD-3 内置）。
- 海豚社群：D. Lusseau, K. Schneider et al. (2003). The bottlenose dolphin community of Doubtful Sound features a large proportion of long-lasting associations. *Behav. Ecol. Sociobiol.* 54, 396–405。
- 世界杯球员效力关系依据公开报道整理（2022 卡塔尔世界杯八强大名单）。
- 贸易权重依据 2023 年公开贸易统计的量级整理，用于教学演示，非精确值。
- 电网、课堂意见、企业联盟、研究者合作网络为按教学目标构造的合成数据。
