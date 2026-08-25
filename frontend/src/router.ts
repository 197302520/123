import { createMemoryHistory, createRouter, createWebHistory, type RouterHistory } from 'vue-router'

const HomeView = () => import('./views/HomeView.vue')
const CourseLibraryView = () => import('./views/CourseLibraryView.vue')
const ModuleDetailView = () => import('./views/ModuleDetailView.vue')
const CaseLibraryView = () => import('./views/CaseLibraryView.vue')
const CaseDetailView = () => import('./views/CaseDetailView.vue')
const LabView = () => import('./views/LabView.vue')
const PresentationView = () => import('./views/PresentationView.vue')

export function createStudentRouter(mode: 'web' | 'memory' = 'web') {
  const history: RouterHistory = mode === 'memory' ? createMemoryHistory() : createWebHistory()
  return createRouter({
    history,
    scrollBehavior: () => ({ top: 0 }),
    routes: [
      { path: '/', name: 'home', component: HomeView },
      { path: '/courses', name: 'courses', component: CourseLibraryView },
      { path: '/courses/:slug', name: 'module', component: ModuleDetailView, props: true },
      { path: '/cases', name: 'cases', component: CaseLibraryView },
      { path: '/cases/:slug', name: 'case', component: CaseDetailView, props: true },
      { path: '/lab', name: 'lab', component: LabView },
      { path: '/present/:slug', name: 'presentation', component: PresentationView, props: true, meta: { presentation: true } },
    ],
  })
}

export const router = createStudentRouter()
