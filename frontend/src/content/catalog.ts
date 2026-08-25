export interface ModuleEditorial { slug: string; numeral: string; question: string; methods: string; accent: string }

export const MODULE_EDITORIAL: ModuleEditorial[] = [
  { slug: 'network-basics', numeral: '一', question: '关系如何成为可计算的图？', methods: '节点 · 边 · 邻接矩阵', accent: '结构语言' },
  { slug: 'network-measures', numeral: '二', question: '谁在网络中更重要？', methods: '中心性 · 路径 · 聚类', accent: '位置测量' },
  { slug: 'communities', numeral: '三', question: '群体边界从何处浮现？', methods: '模块度 · Louvain · LPA', accent: '社区发现' },
  { slug: 'diffusion', numeral: '四', question: '观点怎样扩散与收敛？', methods: 'DeGroot · FJ · 有界信任', accent: '传播动力' },
  { slug: 'robustness', numeral: '五', question: '移除谁会让网络瓦解？', methods: '随机攻击 · 目标攻击', accent: '韧性检验' },
  { slug: 'link-prediction', numeral: '六', question: '下一条关系可能出现在哪里？', methods: 'CN · Jaccard · AA · RA', accent: '关系推断' },
  { slug: 'dynamic-networks', numeral: '七', question: '社群如何随时间诞生与消散？', methods: '快照匹配 · 事件识别', accent: '动态演化' },
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
