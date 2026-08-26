# 社会网络分析智能教学平台（关系研习室）

面向高校《社会网络分析》课程的一体化智能教学平台。学生**无需注册登录**即可完成从"一段自然语言文本"到"完整网络分析报告"的全流程实验；教师通过 Django 管理后台维护课程内容。所有算法在服务端真实计算，相同输入（图 + 参数 + 算法版本 + 随机种子）结果完全可复现。

完整业务链路：**输入文本 → 文本清洗与实体关系抽取 → 关联权重计算 → 生成标准网络文件 → 网络可视化 → 最短路径 → 中心性测算 → 链路预测 → 社区划分 → 网络韧性评估 → 观点演化仿真 → 标准化报告**。

技术栈：Django 5.2 + DRF + Celery（后端）、Vue 3 + TypeScript + Vite + Cytoscape.js + ECharts + KaTeX（前端）、PostgreSQL / Redis（生产）。

---

## 1. 平台是干什么的

这是一个**案例式的社会网络分析教学与实验平台**，覆盖课程教学、课堂案例、课程实验与课程设计的完整场景：

- **学**：七个课程模块，每个算法都配有数学公式、文字解释、参数释义、优缺点说明（前端 KaTeX 渲染）。
- **练**：内置教学案例库（Zachary 空手道俱乐部、海豚社群、球员—俱乐部二部网络、企业关系文本、贸易时间快照、课堂意见网络、论文引用网络），每个案例按"提出问题 → 认识数据 → 选择方法 → 运行分析 → 解释发现 → 反思迁移"六步组织。
- **算**：自由实验室提供 42 个真实算法，输入自己的网络数据即可运行，输出指标表格、可视化图表、网络叠加层、警告与溯源信息。
- **交**：每次运行可下载 HTML 分析报告和 ZIP 复现包（含结果 JSON、参数、种子、图数据、GraphML、全部结果表 CSV）。
- **视**：暖白学术风界面（参考扣子的留白与衬线大标题、新东方的教育绿）：单行白色玻璃导航、衬线大标题、七模块学习路径节点连线、墨绿品牌色 + 橙色点缀、浅色页脚；首页 three.js 三维关系网络（白玻璃面板、墨绿/紫/金节点）随视线旋转。
- **教**：教师登录后台发布/下架模块、案例、数据集；另有课堂演示模式，适合投影逐节讲解。

## 2. 功能清单（7 大模块 / 42 个算法）

| 模块 | 功能 | 算法/指标 |
|---|---|---|
| 模块一 网络基础 | 中文文本预处理建网、图校验、文件导入导出 | 规则实体关系抽取（可选 PaddleNLP/BGE 本地模型）、共现余弦权重、频次归一化权重；导出 XLSX 工作簿（节点编号清单/邻接矩阵/边列表）/JSON/CSV/TXT 边表/邻接矩阵/GraphML/GEXF/GML/Pajek；同指实体按语义相似度自动合并 |
| 模块二 网络测量 | 拓扑、路径、中心性、经典网络模型 | 拓扑摘要（密度/直径/平均路径/平均度/聚类）、Floyd 全源最短路（含任意两点完整路径节点序列与平均路径）、聚类系数、度/接近/中介/特征向量中心性、PageRank、HITS、度中心势、ER/WS/BA 生成器（含结构证据） |
| 模块三 社区发现 | 非重叠、重叠、动态、深度学习社区 | 非重叠：KL、凝聚层次、分裂层次、Girvan–Newman、Fast Newman、Louvain、Leiden*、LPA；重叠：CPM、LFM、SLPA；多算法模块度对比（含强/弱社区与密度判定）；动态社区事件（延续/新生/消亡/分裂/合并）；深度学习：AE、CNN（CPU）、GCN、GAT（需可选依赖） |
| 模块四 扩散与传播 | 观点动力学仿真 | DeGroot、Friedkin–Johnsen（固执度）、Deffuant（有界信任）、Hegselmann–Krause，输出观点轨迹图 |
| 模块五 韧性 | 网络鲁棒性 | 最大连通子图占比 S(q) 曲线、综合鲁棒性 R；随机攻击、按度蓄意攻击、按介数蓄意攻击 |
| 模块六 链路预测 | 潜在关系推断 | 共同邻居 CN、Jaccard、Adamic–Adar、资源分配 RA，均带防泄漏 AUC 评估（先隐藏测试边再评分） |
| 模块七 动态网络 | 时序社群演化 | 多快照 Jaccard 匹配、社区事件时间线 |

\* Leiden 在未安装 `igraph/leidenalg` 时明示回退为 Louvain；GCN/GAT 在未安装 `torch`/`torch_geometric` 时明示报"能力不可用"——平台绝不伪造结果。

每次运行的输出统一为：**表格（tables）+ 图表（charts）+ 网络叠加层（overlays，节点大小映射指标值、边粗细映射权重、节点颜色映射社区）+ 警告（warnings）+ 溯源（provenance：算法版本、参数哈希、图哈希、随机种子）**。

安全与运维内建：匿名限流（标准算法 120 次/小时、重算法 30 次/小时/IP 与会话双通道）、上传文件类型/大小/内容安全校验（TXT/CSV/XLSX/JSON/GraphML/GEXF，最大 20 MB，XLSX 防宏/防外部链接）、匿名运行数据 2 小时自动清理、教师操作审计记录、按图+算法+参数哈希的结果缓存。

## 3. 如何运行

### 3.0 一键启动（Windows，推荐）

双击仓库根目录的 **`start.bat`** 即可：自动检查/安装依赖 → 初始化数据库并载入案例 → 启动后端与前端（各自弹出一个命令行窗口）→ 自动打开浏览器访问 http://localhost:5173。已支持重复运行（服务已在跑时自动跳过，不会重复启动）。停止服务双击 **`stop.bat`**。

前提：本机已安装 Python 3.10+ 与 Node.js 20+（首次运行会自动安装依赖，之后秒开）。

### 3.1 本地开发（手动方式，无需 Docker）

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

1. **首页**：了解平台理念，快速进入课程、案例或实验室；顶部为 three.js 三维关系网络动画。
2. **课程**（/courses）：七个模块，点进任一模块（/courses/:slug）即见"本模块如何推进 → 可运行算法卡片 → 配套案例"三层结构；每个算法卡片显示公式、版本与图类型，点击**直接进入该算法的实验**（/lab?algorithm=…）。
3. **案例库**（/cases）：按模块筛选案例；进入案例详情按六步研习标签页学习；点击"开始分析"自动把案例图载入实验室。
4. **自由实验室**（/lab）三步走：
   - **第一步 准备网络**：粘贴 GraphSpec JSON 或"起点 终点 [权重]"边表，或点"导入文件"上传 TXT/CSV/XLSX/JSON/GraphML/GEXF；点"校验图数据"，通过后右侧显示网络预览。
   - **第二步 选择算法**：42 个算法按模块分组下拉选择（也可由模块页/案例页跳转自动选中）；查看公式与说明；按需调整参数（可一键恢复默认值）、设置随机种子。
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
curl http://127.0.0.1:8000/api/algorithms/       # 应返回 42 个算法
```

再在浏览器走一遍：首页 → 案例库 → Zachary 案例 → "开始分析" → 校验 → 运行 Louvain → 查看结果 → 下载复现包。若某算法缺可选依赖（如 GCN），应看到明确的"能力不可用"提示而不是假结果。

## 6. 已知不足（对照《社会网络分析智能教学平台说明书》）

2026-08 复查：此前审查确认的 8 项差距已全部修复——

1. ✅ 可视化布局补齐 **FR 力导向（cose）/ Circular 环形 / 分层树形** 三类，输入预览与结果叠加层均可切换（说明书 3.2）。
2. ✅ Floyd 输出**任意两点完整路径节点序列**、平均最短路径长度，与距离矩阵同源自洽；可按 `path_pair_limit` 控制输出上限（说明书 4.2）。
3. ✅ 实体合并支持**语义相似度匹配**（字符二元组余弦 + 包含关系），"阿里"与"阿里巴巴"自动合并为统一节点，阈值 `merge_threshold` 可调、0 关闭（说明书 2.1(3)）。
4. ✅ 海豚案例替换为 **Lusseau et al. (2003) 真实海豚关联网络（62 节点/159 边）**，预设算法为 **CPM 派系渗透**（k=3 展示重叠归属），SLPA 及链路预测算法可在实验室直接对比运行（说明书 9）。
5. ✅ 每个社区划分输出**强社区/弱社区/密度判定标准表**：逐点内部度>外部度、总量比较、内外边密度对比全网密度（说明书 6.1）。
6. ✅ 新增**多算法模块度对比**（community.compare）：一次聚合 FN/Louvain/Leiden/LPA 等算法的模块度排名表、对比柱状图与最优算法筛选结论；小网络额外纳入二分/层次/重叠方法（说明书 6.7）。
7. ✅ 观点动力学输出**逐轮观点方差轨迹表+曲线**与稳态判定（final_variance/steady_state）（说明书 8.4）。
8. ✅ 导出新增**原生 .xlsx 工作簿**：节点编号清单、完整邻接矩阵、边列表三个工作表，前端一键下载（说明书 2.3）。

仍存在的事项：

9. ✅ **可选依赖已全部落地**：`igraph`/`leidenalg` 已列入正式依赖（`pip install -e "backend[dev]"` 即得真 Leiden）；`torch`/`torch-geometric` 经 `pip install -e "backend[ml]"` 安装后 GCN/GAT 真实训练（当前开发环境已装 CPU 版并验证）。依赖缺失时仍保留明示回退/能力不可用提示，绝不伪造结果。
10. ✅ **前端体验升级**：信息架构调整为「课程模块 → 模块内算法卡片 → 一键进入实验 → 案例库贯穿」；首页引入 three.js 三维关系网络英雄区（WebGL 不可用时自动回退静态插画）；实验室算法下拉按模块分组，支持 `/lab?algorithm=<key>` 深链直达实验。
11. **PaddleNLP / BGE 文本抽取**需要用户自备本地模型目录（`model_path`），平台不随仓库分发模型权重；未配置时返回明确的"能力不可用"提示。

## 7. 目录结构

```
backend/    Django + DRF：learning/algorithms 算法引擎（42 个）、views 公共 API、
            teacher_views 教师 API、tasks/run_service Celery 与运行服务、
            reports 报告生成、safe_imports 安全导入、tests 测试
frontend/   Vue 3：views 页面（首页/课程/案例/实验室/演示）、components
            （GraphEditor/GraphCanvas/ResultsPanel 等）、lab 状态机与本机历史
docs/       deployment.md 生产部署、plans 实施计划
scripts/    verify_release.py / validate_compose.py / load_test.py
compose.yaml / compose.prod.yaml   本地与生产容器编排
```
