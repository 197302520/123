import { describe, expect, test } from 'vitest'
import { createStudentRouter } from './router'

describe('anonymous student routes', () => {
  test('registers every public learning route without an authentication gate', () => {
    const router = createStudentRouter('memory')
    const routes = router.getRoutes()
    const paths = routes.map((route) => route.path)

    expect(paths).toEqual(expect.arrayContaining([
      '/', '/courses', '/courses/:slug', '/cases', '/cases/:slug', '/lab', '/present/:slug',
    ]))
    expect(routes.every((route) => route.meta.requiresAuth !== true)).toBe(true)
    expect(paths.some((path) => path.includes('login'))).toBe(false)
  })
})
