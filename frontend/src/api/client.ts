import type { CourseModule } from './contracts'

export async function fetchModules(): Promise<CourseModule[]> {
  const response = await fetch('/api/modules/')
  if (!response.ok) throw new Error('无法加载课程模块。')
  return response.json() as Promise<CourseModule[]>
}
