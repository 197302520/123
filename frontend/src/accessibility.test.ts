import { describe, expect, test, vi } from 'vitest'
import { allowsMotion } from './accessibility'

describe('reduced motion preference', () => {
  test('disables animated chart transitions when the learner requests reduced motion', () => {
    vi.spyOn(window, 'matchMedia').mockReturnValue({ matches: true } as MediaQueryList)
    expect(allowsMotion()).toBe(false)
    expect(window.matchMedia).toHaveBeenCalledWith('(prefers-reduced-motion: reduce)')
  })
})
