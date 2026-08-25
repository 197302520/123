import { render, screen } from '@testing-library/vue'
import userEvent from '@testing-library/user-event'
import { describe, expect, test, vi } from 'vitest'
import PresentationView from './PresentationView.vue'

vi.mock('../api/client', () => ({
  fetchCase: vi.fn().mockResolvedValue({ slug: 'karate', title: '空手道俱乐部网络', summary: '社区分裂', module: 'communities', content: '', dataset: null }),
}))

describe('presentation keyboard controls', () => {
  test('moves between the six lesson scenes with arrow keys', async () => {
    const user = userEvent.setup()
    render(PresentationView, { props: { slug: 'karate' }, global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } } })

    expect(await screen.findByText('01 / 06')).toBeVisible()
    await user.keyboard('{ArrowRight}')
    expect(screen.getByText('02 / 06')).toBeVisible()
    await user.keyboard('{ArrowLeft}')
    expect(screen.getByText('01 / 06')).toBeVisible()
  })
})
