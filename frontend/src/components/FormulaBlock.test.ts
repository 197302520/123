import { render, screen } from '@testing-library/vue'
import { describe, expect, test, vi } from 'vitest'

vi.mock('katex', () => ({ default: { renderToString: vi.fn(() => { throw new Error('renderer failure') }) } }))
import FormulaBlock from './FormulaBlock.vue'


describe('formula fallback safety', () => {
  test('escapes formula text when the renderer unexpectedly fails', () => {
    const { container } = render(FormulaBlock, { props: { formula: '<img src=x onerror=alert(1)>' } })

    expect(screen.getByLabelText('算法公式')).toHaveTextContent('<img src=x onerror=alert(1)>')
    expect(container.querySelector('img')).toBeNull()
  })
})
