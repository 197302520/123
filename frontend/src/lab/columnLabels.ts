/**
 * 结果表列名的中文对照。
 * 原始英文字段名仍是导出文件（CSV/XLSX）与复现包里的规范名称，
 * 因此表格里用中文表头辅助阅读，悬停可查看原始字段名。
 */
const COLUMN_LABELS: Record<string, string> = {
  // 通用
  node: '节点',
  label: '名称',
  value: '数值',
  rank: '排名',
  score: '得分',
  weight: '权重',
  status: '状态',
  key: '算法键',
  name: '名称',
  time: '快照',
  step: '步数',

  // 拓扑摘要与结构证据
  node_count: '节点数',
  edge_count: '边数',
  density: '密度',
  components: '连通分量数',
  average_degree: '平均度',
  average_clustering: '平均聚类系数',
  diameter: '直径',
  average_path_length: '平均路径长度',
  average_shortest_path_length: '平均最短路径长度',
  reachable_pairs: '可达节点对',
  unreachable_pairs: '不可达节点对',

  // 路径与距离
  source: '起点',
  target: '终点',
  distance: '距离',
  path: '路径节点序列',

  // 中心性
  coefficient: '聚类系数',
  hub: '枢纽分 Hub',
  authority: '权威分 Authority',
  centralization: '度中心势',
  numerator: '分子',
  denominator: '分母',

  // 社区发现
  community: '社区编号',
  size: '成员数',
  memberships: '所属社区（可重叠）',
  internal_degree_sum: '内部度数之和',
  boundary_degree_sum: '边界度数之和',
  internal_edge_pairs: '内部节点对',
  boundary_edge_pairs: '跨界节点对',
  internal_density: '内部密度',
  cross_density: '跨群密度',
  strong_community: '强社区',
  weak_community: '弱社区',
  density_criterion: '密度判据',
  verdict: '判定结论',
  modularity: '模块度 Q',
  community_count: '社区数量',
  overlapping: '允许重叠社区',
  comparable: '可比较模块度',
  runtime_ms: '耗时 (ms)',
  algorithm: '算法',
  left: '合并侧',
  right: '被并侧',
  gain: '模块度增益',
  edge_betweenness: '边中介数',

  // 网络韧性
  removed_fraction: '已移除比例 q',
  remaining_nodes: '剩余节点数',
  largest_component: '最大连通子图',
  S_q: 'S(q) 最大连通占比',
  removed_node: '本步移除节点',

  // 链路预测
  auc: 'AUC',

  // 意见动力学
  initial_opinion: '初始观点',
  opinion: '最终观点',
  variance: '观点方差',
  delta_from_previous: '与前一步之差',
  converged: '已收敛',
  iteration: '迭代轮次',

  // 动态社区
  event: '事件',
  similarity: '重叠度 Jaccard',

  // 文本抽取
  entity: '实体',
  type: '类型',
  start: '起始偏移',
  end: '结束偏移',
  confidence: '置信度',
  evidence: '证据文本',
  relation: '关系',
  occurrence_count: '出现次数',
  canonical_entity: '合并后实体',
  representative: '代表实体',
  members: '成员',
  editable: '可编辑',

  // 节点嵌入
  embedding: '嵌入向量',
  cluster: '聚类编号',
  epoch: '训练轮次',
  loss: '损失',

  // 图导出（export 表走下载卡片，仅兜底）
  format: '格式',
  mime_type: 'MIME 类型',
  filename: '文件名',
  encoding: '编码',
}

/** 中文表头；未收录的列回退为原始字段名。 */
export function columnLabel(column: string): string {
  return COLUMN_LABELS[column] ?? column
}
