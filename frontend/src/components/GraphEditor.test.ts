import { fireEvent, render, screen } from '@testing-library/vue'
import userEvent from '@testing-library/user-event'
import { describe, expect, test, vi } from 'vitest'
import GraphEditor from './GraphEditor.vue'
import { exampleGraph } from '../test/fixtures'

vi.mock('../api/client', () => ({ validateGraph: vi.fn(), importGraph: vi.fn() }))
import { importGraph, validateGraph } from '../api/client'

describe('graph validation errors', () => {
  test('keeps the hidden file input keyboard-focusable inside its styled label', async () => {
    render(GraphEditor, { props: { modelValue: exampleGraph }, global: { stubs: { GraphCanvas: true } } })
    const input = screen.getByLabelText('导入文件')

    input.focus()

    expect(input).toHaveFocus()
    expect(input.closest('label')).toHaveClass('file-button')
  })

  test('invalidates a previously validated graph as soon as its source text changes', async () => {
    vi.mocked(validateGraph).mockResolvedValue({ valid: true, errors: [], graph: exampleGraph })
    const user = userEvent.setup()
    const view = render(GraphEditor, { props: { modelValue: exampleGraph }, global: { stubs: { GraphCanvas: true } } })

    await user.click(screen.getByRole('button', { name: '校验图数据' }))
    expect(view.emitted('validated')).toHaveLength(1)
    await fireEvent.update(screen.getByRole('textbox', { name: '粘贴图数据' }), 'a b')

    const invalidEvents = view.emitted('invalid') ?? []
    expect(invalidEvents[invalidEvents.length - 1]).toEqual(['图数据已修改，请重新校验。'])
    expect(screen.queryByText(/校验通过/)).not.toBeInTheDocument()
  })

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

  test('ignores an older server validation response after the source text changes', async () => {
    let resolveValidation!: (value: { valid: true; errors: never[]; graph: typeof exampleGraph }) => void
    vi.mocked(validateGraph).mockImplementation(() => new Promise((resolve) => { resolveValidation = resolve }))
    const view = render(GraphEditor, { props: { modelValue: exampleGraph }, global: { stubs: { GraphCanvas: true } } })
    const user = userEvent.setup()

    await user.click(screen.getByRole('button', { name: '校验图数据' }))
    await fireEvent.update(screen.getByRole('textbox', { name: '粘贴图数据' }), '新甲 新乙')
    resolveValidation({ valid: true, errors: [], graph: exampleGraph })
    await Promise.resolve()

    expect(view.emitted('validated')).toBeUndefined()
    expect(screen.queryByText(/校验通过/)).not.toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: '粘贴图数据' })).toHaveValue('新甲 新乙')
  })

  test('imports all advertised formats through the bounded backend parser', async () => {
    vi.mocked(importGraph).mockResolvedValue({ valid: true, errors: [], graph: exampleGraph })
    const file = new File(['binary workbook'], 'network.xlsx', { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const view = render(GraphEditor, { props: { modelValue: exampleGraph }, global: { stubs: { GraphCanvas: true } } })

    await userEvent.setup().upload(screen.getByLabelText('导入文件'), file)

    expect(importGraph).toHaveBeenCalledWith(file, expect.any(AbortSignal))
    expect(validateGraph).not.toHaveBeenCalled()
    expect(await screen.findByRole('status')).toHaveTextContent('导入并校验通过')
    expect(view.emitted('validated')).toHaveLength(1)
    const input = screen.getByLabelText('导入文件')
    expect(input).toHaveAttribute('accept', expect.stringContaining('.graphml'))
    expect(input).toHaveAttribute('accept', expect.stringContaining('.gexf'))
  })

  test('announces backend import errors without accepting the graph', async () => {
    vi.mocked(importGraph).mockRejectedValue(new Error('XLSX 不得包含宏、外部链接或越界路径。'))
    const file = new File(['unsafe'], 'network.xlsx')
    const view = render(GraphEditor, { props: { modelValue: exampleGraph }, global: { stubs: { GraphCanvas: true } } })

    await userEvent.setup().upload(screen.getByLabelText('导入文件'), file)

    expect(await screen.findByRole('alert')).toHaveTextContent('XLSX 不得包含宏')
    const invalidEvents = view.emitted('invalid') ?? []
    expect(invalidEvents[invalidEvents.length - 1]).toEqual(['XLSX 不得包含宏、外部链接或越界路径。'])
  })
})
