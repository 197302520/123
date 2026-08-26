export interface ModuleEditorial {
  slug: string
  numeral: string
  question: string
  methods: string
  accent: string
  /** 「本模块如何推进」正文 */
  lead: string
  /** 「完成后，你应能」三条学习检验 */
  checks: string[]
}

export const MODULE_EDITORIAL: ModuleEditorial[] = [
  {
    slug: 'network-basics', numeral: '一', question: '关系如何成为可计算的图？', methods: '节点 · 边 · 邻接矩阵', accent: '结构语言',
    lead: '从一段真实的关系描述出发，先把行动者与关系分别抽象为节点和边，再决定方向、权重与二部结构等表示选择。你会看到同一份关系数据在不同建网决策下得到不同的图，并理解每种表示能回答什么、不能回答什么。',
    checks: ['把一段关系情境建模为节点、边与属性', '解释有向、加权、二部等表示选择的后果', '读懂邻接矩阵与边表两种数据形式'],
  },
  {
    slug: 'network-measures', numeral: '二', question: '谁在网络中更重要？', methods: '中心性 · 路径 · 聚类', accent: '位置测量',
    lead: '从"谁更重要"这个直觉问题出发，逐一比较度、接近、中介与特征向量中心性各自的假设：它们分别把"重要"定义成什么。配合路径长度与聚类系数，你会学会为一个具体问题选择恰当的指标，而不是把排名当成答案。',
    checks: ['区分四种中心性各自的"重要性"定义', '为具体研究问题选择匹配的结构指标', '说明指标在抽样或缺失边下的敏感性'],
  },
  {
    slug: 'communities', numeral: '三', question: '群体边界从何处浮现？', methods: '模块度 · Louvain · LPA', accent: '社区发现',
    lead: '以空手道俱乐部的分裂为线索，先目测群体，再用模块度把"内部密、外部疏"的直觉形式化。你将运行 Louvain 与标签传播，比较划分结果与真实分裂的对应关系，并讨论分辨率参数如何改变群体的粗细。',
    checks: ['用模块度解释社区划分的质量', '运行并比较 Louvain 与标签传播', '说明分辨率参数对社区数目的影响'],
  },
  {
    slug: 'diffusion', numeral: '四', question: '观点怎样扩散与收敛？', methods: 'DeGroot · FJ · 有界信任', accent: '传播动力',
    lead: '从一个六人课堂意见网络开始，运行 DeGroot 模型观察观点沿关系的平均化过程，再引入固执个体与信任半径，观察共识如何被阻止、极化如何出现。你会把仿真曲线解释回"谁在影响谁"的结构问题。',
    checks: ['解释 DeGroot 迭代中权重矩阵的作用', '识别固执节点对收敛结果的影响', '从轨迹曲线判断共识、极化或僵持'],
  },
  {
    slug: 'robustness', numeral: '五', question: '移除谁会让网络瓦解？', methods: '随机攻击 · 目标攻击', accent: '韧性检验',
    lead: '对同一个网络分别施加随机失效与按中心性排序的目标攻击，追踪最大连通子图的坍缩曲线。你将比较两种策略下网络瓦解速度的差异，理解无标度结构"对随机稳健、对攻击脆弱"的经典论断。',
    checks: ['设计随机与目标两类节点移除实验', '用最大连通子图曲线量化网络韧性', '解释中心节点与结构脆弱性的关系'],
  },
  {
    slug: 'link-prediction', numeral: '六', question: '下一条关系可能出现在哪里？', methods: 'CN · Jaccard · AA · RA', accent: '关系推断',
    lead: '把"谁可能建立联系"转化为对未连边的打分问题：共同邻居、Jaccard、Adamic-Adar 与资源分配各有侧重。你会隐藏一部分真实边作为验证集，评估各指标把潜在关系排在前面的能力。',
    checks: ['说明四种相似度指标的直觉与差异', '用隐藏边验证链路预测的排序质量', '指出稀疏网络中预测失效的情形'],
  },
  {
    slug: 'dynamic-networks', numeral: '七', question: '社群如何随时间诞生与消散？', methods: '快照匹配 · 事件识别', accent: '动态演化',
    lead: '把连续变化的关系切成三个时间快照，分别在每个快照上发现社群，再按重叠度跨快照匹配，识别延续、分裂、合并与消散事件。你会讨论快照粒度这一建模选择如何改变对"演化"的叙述。',
    checks: ['说明快照切分对动态分析的影响', '跨快照匹配社群并识别演化事件', '用案例语言复述社群的生命周期'],
  },
]

export interface CaseSection { id: string; title: string; eyebrow: string; heading: string; body: string; prompts: string[] }

export const CASE_SECTIONS: CaseSection[] = [
  { id: 'question', title: '提出问题', eyebrow: '01 / 从现象出发', heading: '先问一个能被网络回答的问题', body: '不要急着选算法。把案例中的人物、组织或事件放回关系情境，明确你真正想解释的结构现象。', prompts: ['哪些行动者构成网络？', '什么关系被记录，什么关系被遗漏？', '结果应帮助谁作出什么判断？'] },
  { id: 'data', title: '认识数据', eyebrow: '02 / 审视证据', heading: '节点与关系不是自然存在的数据', body: '检查节点、边、方向、权重与时间范围。数据建模的每个选择都会改变后续可以得出的结论。', prompts: ['节点与关系如何操作化？', '网络是有向、无向还是多层？', '缺失边会带来怎样的偏差？'] },
  { id: 'method', title: '选择方法', eyebrow: '03 / 让方法服从问题', heading: '从解释目标倒推算法', body: '比较方法的假设、适用图类型和限制。一个漂亮的数值，若不回答原问题，就不是有效证据。', prompts: ['算法支持当前图类型吗？', '参数改变会影响哪些判断？', '是否需要随机种子保证复现？'] },
  { id: 'run', title: '运行分析', eyebrow: '04 / 留下可复现轨迹', heading: '让每次计算都可检查、可重做', body: '记录输入图、算法版本、参数与随机种子；先处理验证警告，再阅读表格、图表和网络叠加层。', prompts: ['输入是否通过结构校验？', '运行状态与警告说明了什么？', '能否用同一配置得到相同结果？'] },
  { id: 'interpret', title: '解释发现', eyebrow: '05 / 从输出到论证', heading: '把结构信号翻译为案例语言', body: '回到案例语境解释排名、社区或曲线。区分算法发现、数据限制与研究者推断，避免把相关说成因果。', prompts: ['最强信号对应案例中的什么？', '哪些节点或群体是反例？', '还有什么竞争性解释？'] },
  { id: 'reflect', title: '反思迁移', eyebrow: '06 / 带着限制离开', heading: '改变一个条件，结论还成立吗？', body: '比较不同参数、方法与数据边界，将结论迁移到新情境前，先说明哪些假设必须保持。', prompts: ['更换算法后结论是否稳定？', '谁可能被数据排除在外？', '这个分析能迁移到哪个新问题？'] },
]

export const moduleEditorial = (slug: string) => MODULE_EDITORIAL.find((item) => item.slug === slug)
