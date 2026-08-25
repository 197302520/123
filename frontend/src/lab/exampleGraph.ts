import type { GraphSpec } from '../api/contracts'

export const LEARNING_EXAMPLE_GRAPH: GraphSpec = {
  directed: false,
  nodes: [
    { id: '阿兰', label: '阿兰' }, { id: '白露', label: '白露' }, { id: '陈默', label: '陈默' },
    { id: '杜若', label: '杜若' }, { id: '方圆', label: '方圆' }, { id: '顾言', label: '顾言' },
  ],
  edges: [
    { source: '阿兰', target: '白露', weight: 1 }, { source: '阿兰', target: '陈默', weight: 1 },
    { source: '白露', target: '陈默', weight: 1 }, { source: '陈默', target: '杜若', weight: 0.4 },
    { source: '杜若', target: '方圆', weight: 1 }, { source: '杜若', target: '顾言', weight: 1 },
    { source: '方圆', target: '顾言', weight: 1 },
  ],
}
