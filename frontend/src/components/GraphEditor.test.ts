import { fireEvent, render, screen } from '@testing-library/vue'
import userEvent from '@testing-library/user-event'
import { describe, expect, test, vi } from 'vitest'
import GraphEditor from './GraphEditor.vue'
import { exampleGraph } from '../test/fixtures'

vi.mock('../api/client', () => ({ validateGraph: vi.fn() }))
import { validateGraph } from '../api/client'

describe('graph validation errors', () => {
  test('announces server paths and does not mark an invalid graph as ready', async () => {
    vi.mocked(validateGraph).mockRejectedValue(new Error("edges[0].target：节点 'z' 不存在。"))
    const user = userEvent.setup()
    const view = render(GraphEditor, { props: { modelValue: exampleGraph }, global: { stubs: { GraphCanvas: true } } })

    await fireEvent.update(screen.getByRole('textbox', { name: '粘贴图数据' }), JSON.stringify({
      directed: false,
      nodes: [{ id: 'a' }],
      edges: [{ source: 'a', target: 'z' }],
    }))
    await user.click(screen.getByRole('button', { name: '校验图数据' }))

    expect(await screen.findByRole('alert')).toHaveTextContent("edges[0].target：节点 'z' 不存在。")
    expect(view.emitted('validated')).toBeUndefined()
  })
})
