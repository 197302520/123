import { render, screen } from '@testing-library/vue'
import userEvent from '@testing-library/user-event'
import { describe, expect, test, vi } from 'vitest'
import HistoryPanel from './HistoryPanel.vue'
import { historyRecord } from '../test/fixtures'

vi.mock('../lab/reproducibility', () => ({ downloadReproducibilityBundle: vi.fn() }))

describe('history comparison and destructive actions', () => {
  test('disables self-comparison for the current result', () => {
    render(HistoryPanel, { props: { records: [historyRecord], currentRunId: historyRecord.id } })

    expect(screen.getByRole('button', { name: '当前结果' })).toBeDisabled()
  })

  test('asks for confirmation before clearing every local record', async () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
    const view = render(HistoryPanel, { props: { records: [historyRecord] } })

    await userEvent.setup().click(screen.getByRole('button', { name: '清空历史' }))

    expect(confirm).toHaveBeenCalled()
    expect(view.emitted('clear')).toBeUndefined()
  })

  test('shows a load error without simultaneously claiming history is empty', () => {
    render(HistoryPanel, { props: { records: [], loading: false, error: '读取失败' } })

    expect(screen.getByRole('alert', { name: '本机历史错误' })).toHaveTextContent('读取失败')
    expect(screen.queryByText('还没有实验记录。完成一次真实运行后，它会出现在这里。')).not.toBeInTheDocument()
  })
})
