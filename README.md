# 社会网络分析智能教学平台（关系研习室）

面向高校《社会网络分析》课程的一体化智能教学平台。学生**无需注册登录**即可完成从"一段自然语言文本"到"完整网络分析报告"的全流程实验；教师通过 Django 管理后台维护课程内容。所有算法在服务端真实计算，相同输入（图 + 参数 + 算法版本 + 随机种子）结果完全可复现。

完整业务链路：**输入文本 → 文本清洗与实体关系抽取 → 关联权重计算 → 生成标准网络文件 → 网络可视化 → 最短路径 → 中心性测算 → 链路预测 → 社区划分 → 网络韧性评估 → 观点演化仿真 → 标准化报告**。

技术栈：Django 5.2 + DRF + Celery（后端）、Vue 3 + TypeScript + Vite + Cytoscape.js + ECharts + KaTeX（前端）、PostgreSQL / Redis（生产）。

---

## 1. 平台是干什么的

这是一个**案例式的社会网络分析教学与实验平台**，覆盖课程教学、课堂案例、课程实验与课程设计的完整场景：

- **学**：七个课程模块，每个算法都配有数学公式、文字解释、参数释义、优缺点说明（前端 KaTeX 渲染）。
- **练**：内置教学案例库（Zachary 空手道俱乐部、海豚社群、球员—俱乐部二部网络、企业关系文本、贸易时间快照、课堂意见网络、论文引用网络），每个案例按"提出问题 → 认识数据 → 选择方法 → 运行分析 → 解释发现 → 反思迁移"六步组织。
- **算**：自由实验室提供 41 个真实算法，输入自己的网络数据即可运行，输出指标表格、可视化图表、网络叠加层、警告与溯源信息。
- **交**：每次运行可下载 HTML 分析报告和 ZIP 复现包（含结果 JSON、参数、种子、图数据、GraphML、全部结果表 CSV）。
- **教**：教师登录后台发布/下架模块、案例、数据集；另有课堂演示模式，适合投影逐节讲解。

## 2. 功能清单（7 大模块 / 41 个算法）

| 模块 | 功能 | 算法/指标 |
|---|---|---|
| 模块一 网络基础 | 中文文本预处理建网、图校验、文件导入导出 | 规则实体关系抽取（可选 PaddleNLP/BGE 本地模型）、共现余弦权重、频次归一化权重；导出 JSON/CSV/TXT 边表/邻接矩阵/GraphML/GEXF/GML/Pajek |
| 模块二 网络测量 | 拓扑、路径、中心性、经典网络模型 | 拓扑摘要（密度/直径/平均路径/平均度/聚类）、Floyd 全源最短路、聚类系数、度/接近/中介/特征向量中心性、PageRank、HITS、度中心势、ER/WS/BA 生成器（含结构证据） |
| 模块三 社区发现 | 非重叠、重叠、动态、深度学习社区 | 非重叠：KL、凝聚层次、分裂层次、Girvan–Newman、Fast Newman、Louvain、Leiden*、LPA；重叠：CPM、LFM、SLPA；动态社区事件（延续/新生/消亡/分裂/合并）；深度学习：AE、CNN（CPU）、GCN、GAT（需可选依赖） |
| 模块四 扩散与传播 | 观点动力学仿真 | DeGroot、Friedkin–Johnsen（固执度）、Deffuant（有界信任）、Hegselmann–Krause，输出观点轨迹图 |
| 模块五 韧性 | 网络鲁棒性 | 最大连通子图占比 S(q) 曲线、综合鲁棒性 R；随机攻击、按度蓄意攻击、按介数蓄意攻击 |
| 模块六 链路预测 | 潜在关系推断 | 共同邻居 CN、Jaccard、Adamic–Adar、资源分配 RA，均带防泄漏 AUC 评估（先隐藏测试边再评分） |
| 模块七 动态网络 | 时序社群演化 | 多快照 Jaccard 匹配、社区事件时间线 |

\* Leiden 在未安装 `igraph/leidenalg` 时明示回退为 Louvain；GCN/GAT 在未安装 `torch`/`torch_geometric` 时明示报"能力不可用"——平台绝不伪造结果。

每次运行的输出统一为：**表格（tables）+ 图表（charts）+ 网络叠加层（overlays，节点大小映射指标值、边粗细映射权重、节点颜色映射社区）+ 警告（warnings）+ 溯源（provenance：算法版本、参数哈希、图哈希、随机种子）**。

安全与运维内建：匿名限流（标准算法 120 次/小时、重算法 30 次/小时/IP 与会话双通道）、上传文件类型/大小/内容安全校验（TXT/CSV/XLSX/JSON/GraphML/GEXF，最大 20 MB，XLSX 防宏/防外部链接）、匿名运行数据 2 小时自动清理、教师操作审计记录、按图+算法+参数哈希的结果缓存。

## 3. 如何运行

### 3.1 本地开发（最简方式，无需 Docker）

后端（Python 3.10+）：

```powershell
python -m pip install -e "backend[dev]"
python backend/manage.py migrate
python backend/manage.py seed_learning_content
python backend/manage.py runserver        # http://127.0.0.1:8000
```

前端（Node 20+）：

```powershell
cd frontend
npm install
npm run dev                               # http://localhost:5173
```

浏览器访问 **http://localhost:5173**（Vite 会把 `/api` 代理到 8000 端口）。本地默认 `CELERY_TASK_ALWAYS_EAGER=1`，任务同步执行，**不需要** Redis/PostgreSQL（SQLite 即可）。

创建教师账号：`python backend/manage.py createsuperuser`，然后访问 `/admin/`。

### 3.2 Docker Compose（完整服务）

```powershell
copy .env.example .env
docker compose up --build
```

包含 PostgreSQL、Redis、Django web、Celery worker 和前端开发服务器。

### 3.3 生产部署

生产 Compose、HTTPS、迁移/种子、14 天备份恢复、监控、两小时清理、可选 ML worker（`backend/Dockerfile.ml`，安装 torch/torch-geometric/igraph/leidenalg 后 GCN、GAT、真 Leiden 可用）与容量演练详见 [`docs/deployment.md`](docs/deployment.md)。

## 4. 如何使用

### 4.1 学生（免登录）

1. **首页**：了解平台理念，快速进入课程、案例或实验室。
2. **课程**（/courses）：七个模块，每模块说明核心问题与方法族。
3. **案例库**（/cases）：按模块筛选案例；进入案例详情按六步研习标签页学习；点击"开始分析"自动把案例图载入实验室。
4. **自由实验室**（/lab）三步走：
   - **第一步 准备网络**：粘贴 GraphSpec JSON 或"起点 终点 [权重]"边表，或点"导入文件"上传 TXT/CSV/XLSX/JSON/GraphML/GEXF；点"校验图数据"，通过后右侧显示网络预览。
   - **第二步 选择算法**：41 个算法下拉选择；查看公式与说明；按需调整参数（可一键恢复默认值）、设置随机种子。
   - **第三步 运行**：点"运行真实算法"；查看表格/图表/网络叠加；左侧"本机实验历史"保存全部运行（仅存本机浏览器，不关联身份），可将历史记录"加入对比"，或下载复现 ZIP 包。
5. **课堂演示模式**（/present/案例名）：全屏逐节讲解，适合投影。
6. **报告下载**：对任意完成的运行，可获取 HTML 报告和 ZIP 复现包（report.html、result.json、parameters.json、provenance.json、nodes.csv、edges.csv、graph.graphml、各结果表 CSV、manifest.json）。

### 4.2 教师

- 登录 `/admin/`（需 `is_staff`），管理课程模块、案例、数据集及发布状态（草稿/已发布，未发布内容对学生不可见）。
- 教师专属内容 API 带登录保护与操作审计。

## 5. 如何测试

自动化验证（当前全部通过：后端 192 个、前端 88 个测试）：

```powershell
# 后端单元/集成/API/安全/E2E 测试
python -m pytest backend/tests -q

# Django 系统检查
python backend/manage.py check

# 前端组件测试与生产构建
cd frontend
npm run test
npm run build
```

发布级验证（带超时的完整链路；无 Docker 时仅校验生产 Compose 合同）：

```powershell
python scripts/verify_release.py
python scripts/validate_compose.py
python scripts/load_test.py        # 容量压测
```

手工冒烟（服务启动后）：

```powershell
curl http://127.0.0.1:8000/api/modules/          # 应返回 7 个模块
curl http://127.0.0.1:8000/api/cases/            # 应返回 7 个案例
curl http://127.0.0.1:8000/api/algorithms/       # 应返回 41 个算法
```

再在浏览器走一遍：首页 → 案例库 → Zachary 案例 → "开始分析" → 校验 → 运行 Louvain → 查看结果 → 下载复现包。若某算法缺可选依赖（如 GCN），应看到明确的"能力不可用"提示而不是假结果。

## 6. 已知不足（对照《社会网络分析智能教学平台说明书》）

1. **可视化布局只有 1 种**（力导向 cose）；说明书 3.2 要求 3 类：FR 力导向、Circular 环形、分层树形。
2. **Floyd 不输出任意两点的完整路径节点序列**，只有距离矩阵与热力图（说明书 4.2）。
3. **实体合并无语义相似度匹配**："阿里"与"阿里巴巴"等同指实体不会自动合并（说明书 2.1(3)）；BGE 嵌入仅用于边权。
4. **海豚案例为 12 节点合成网络**，非说明书指定的 Sarasota 真实海豚数据；且预设算法是 LPA 而非 CPM/SLPA 重叠社区对比（说明书 9）。
5. **强社区/弱社区/密度判定标准**未实现（说明书 6.1）。
6. **多算法模块度对比表与最优算法筛选结论**无聚合输出，仅能手动两两对比（说明书 6.7）；层次聚类以"层次步骤表"呈现而非树状图。
7. **观点方差指标缺失**：输出极差（final_range）而非逐轮方差轨迹与稳态判定（说明书 8.4）。
8. **导出无原生 .xlsx**（邻接矩阵/节点清单为 CSV，Excel 可直接打开）；导入端支持 XLSX。
9. **Leiden 依赖未安装时回退 Louvain**（有明示警告）；需 `pip install igraph leidenalg` 才是真 Leiden。
10. **GCN/GAT 需安装 torch/torch-geometric 才能运行**（默认环境报"能力不可用"）。

## 7. 目录结构

```
backend/    Django + DRF：learning/algorithms 算法引擎（41 个）、views 公共 API、
            teacher_views 教师 API、tasks/run_service Celery 与运行服务、
            reports 报告生成、safe_imports 安全导入、tests 测试
frontend/   Vue 3：views 页面（首页/课程/案例/实验室/演示）、components
            （GraphEditor/GraphCanvas/ResultsPanel 等）、lab 状态机与本机历史
docs/       deployment.md 生产部署、plans 实施计划
scripts/    verify_release.py / validate_compose.py / load_test.py
compose.yaml / compose.prod.yaml   本地与生产容器编排
```
