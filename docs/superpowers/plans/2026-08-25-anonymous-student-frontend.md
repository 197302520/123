# Anonymous Student Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the anonymous, Chinese-first case learning experience and registry-driven social-network laboratory described by Task 3.

**Architecture:** Vue Router separates editorial public pages from the laboratory while one API client owns the existing Django contracts. Focused graph, result, parameter, and history modules keep the complex laboratory testable; Cytoscape, ECharts, KaTeX, and IndexedDB remain real runtime dependencies behind small Vue components or typed functions.

**Tech Stack:** Vue 3, TypeScript, Vue Router, Cytoscape.js, ECharts, KaTeX, IndexedDB, Vite, Vitest, Vue Testing Library, jsdom, fake-indexeddb.

**Spec:** `docs/plans/social-network-teaching-platform.md` (Task 3) and `.superpowers/sdd/social-network-teaching-platform/task-3-brief.md`

## Global Constraints

- All home, course, case, laboratory, and presentation routes are anonymous; only a quiet footer link points to Django admin.
- Registry and run data always come from `/api`; static graph data is explicitly labelled as a teaching example.
- The interface is Chinese-first, desktop-first, responsive, keyboard operable, high contrast, and reduced-motion aware.
- Browser history uses real IndexedDB and uploaded graph data is not sent anywhere except the temporary run API.
- Runtime algorithm output is rendered from `RunResult`; no canned algorithm results are introduced.
- Behavior follows test-first red/green/refactor. Static editorial copy and CSS do not require behavioral tests.

---

### Task 1: Frontend test harness and typed public API

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/vite.config.ts`
- Modify: `frontend/src/api/contracts.ts`
- Modify: `frontend/src/api/client.ts`
- Create: `frontend/src/test/setup.ts`
- Test: `frontend/src/api/client.test.ts`

**Interfaces:**
- Consumes: Django endpoints `/modules/`, `/cases/`, `/graphs/validate/`, `/algorithms/`, `/runs/`, `/runs/:id/`, and `/runs/:id/result/`.
- Produces: typed `fetchModules`, `fetchModule`, `fetchCases`, `fetchCase`, `fetchAlgorithms`, `validateGraph`, `submitRun`, `fetchRunStatus`, and `fetchRunResult` functions.

- [ ] Write a failing client test whose fetch double mirrors the real endpoint payload and asserts that a non-2xx structured error becomes its Chinese message.
- [ ] Run `npm test -- src/api/client.test.ts` from `frontend`; expect failure because the expanded client functions and test script do not exist.
- [ ] Install runtime and test dependencies, configure jsdom, define complete API types, and implement a single JSON request helper that extracts `error.message`, `detail`, or validation errors.
- [ ] Re-run the client test; expect all assertions to pass.

### Task 2: Anonymous routing, home, courses, cases, and six-section learning detail

**Files:**
- Modify: `frontend/src/main.ts`
- Modify: `frontend/src/App.vue`
- Create: `frontend/src/router.ts`
- Create: `frontend/src/content/catalog.ts`
- Create: `frontend/src/views/HomeView.vue`
- Create: `frontend/src/views/CourseLibraryView.vue`
- Create: `frontend/src/views/ModuleDetailView.vue`
- Create: `frontend/src/views/CaseLibraryView.vue`
- Create: `frontend/src/views/CaseDetailView.vue`
- Create: `frontend/src/views/PresentationView.vue`
- Create: `frontend/src/components/AppFooter.vue`
- Create: `frontend/src/components/ExampleNetwork.vue`
- Test: `frontend/src/views/CaseLibraryView.test.ts`
- Test: `frontend/src/views/CaseDetailView.test.ts`
- Test: `frontend/src/router.test.ts`

**Interfaces:**
- Consumes: public content API and seven-module metadata keyed by backend slugs.
- Produces: anonymous `/`, `/courses`, `/courses/:slug`, `/cases`, `/cases/:slug`, `/lab`, and `/present/:slug` routes; `CASE_SECTIONS` with exactly six learning sections.

- [ ] Write failing component tests showing that module and text filters hide non-matching cases, and that a clear action restores them.
- [ ] Write a failing case-detail test showing six named section controls, keyboard activation, and visible active-section content.
- [ ] Write failing route tests that navigate to every public route without an authentication redirect and exercise presentation ArrowRight/ArrowLeft navigation.
- [ ] Run the three test files; expect missing router/views and section behavior failures.
- [ ] Implement the router and page components using semantic landmarks, headings, text-labelled controls, loading/empty/error states, and a teacher admin footer link only.
- [ ] Re-run the three test files; expect them to pass.

### Task 3: Graph parsing, import, server validation, algorithm registry, and parameter reset

**Files:**
- Create: `frontend/src/lab/exampleGraph.ts`
- Create: `frontend/src/lab/graphInput.ts`
- Create: `frontend/src/lab/parameters.ts`
- Create: `frontend/src/components/GraphEditor.vue`
- Create: `frontend/src/components/GraphCanvas.vue`
- Create: `frontend/src/components/FormulaBlock.vue`
- Create: `frontend/src/components/ParameterControls.vue`
- Test: `frontend/src/lab/graphInput.test.ts`
- Test: `frontend/src/components/ParameterControls.test.ts`
- Test: `frontend/src/components/GraphEditor.test.ts`

**Interfaces:**
- Consumes: JSON or edge-list text and `AlgorithmSpec.parameters` definitions shaped as `{type, default, description, minimum?, maximum?, choices?}`.
- Produces: `parseGraphText(text): GraphInputSpec`, `validateGraphLocally(graph): ValidationIssue[]`, `defaultsFor(spec): Record<string, unknown>`, and `GraphEditor` events `update:modelValue`, `validated`, `invalid`.

- [ ] Write failing pure tests for malformed JSON, duplicate nodes, missing edge endpoints, non-finite/non-positive weights, and valid whitespace-separated edge lists.
- [ ] Write a failing parameter test proving edited boolean/number/choice values reset to registry defaults.
- [ ] Write a failing graph-editor test proving server validation errors are announced with their paths and invalid input cannot emit a valid graph.
- [ ] Run the three files; expect missing parser/components failures.
- [ ] Implement parsing and validation, file reading, explicit teaching-example loading, Cytoscape rendering, KaTeX formula rendering, and accessible registry-driven form controls.
- [ ] Re-run the three files; expect them to pass.

### Task 4: Anonymous IndexedDB history and reproducibility export

**Files:**
- Create: `frontend/src/lab/historyStore.ts`
- Create: `frontend/src/lab/reproducibility.ts`
- Create: `frontend/src/components/HistoryPanel.vue`
- Test: `frontend/src/lab/historyStore.test.ts`
- Test: `frontend/src/lab/reproducibility.test.ts`

**Interfaces:**
- Produces: `saveHistory(record)`, `listHistory()`, `deleteHistory(id)`, `clearHistory()` and `buildReproducibilityBundle(record): Blob`.
- History records contain `id`, `createdAt`, `algorithm`, `algorithmName`, `parameters`, `seed`, `graph`, and real `result`.

- [ ] Write a failing fake-indexeddb test that saves, lists newest-first, deletes, and clears records without an account identifier.
- [ ] Write a failing export test that reads the Blob and asserts graph, algorithm version/provenance, parameters, seed, and result are preserved.
- [ ] Run both files; expect missing history/export module failures.
- [ ] Implement IndexedDB schema version 1 and deterministic JSON bundle generation; implement the history panel with explicit compare, download, delete, and clear controls.
- [ ] Re-run both files; expect them to pass.

### Task 5: Laboratory run state, real results, charts, overlays, and comparison

**Files:**
- Create: `frontend/src/lab/runMachine.ts`
- Create: `frontend/src/components/RunStatus.vue`
- Create: `frontend/src/components/ResultChart.vue`
- Create: `frontend/src/components/ResultsPanel.vue`
- Create: `frontend/src/views/LabView.vue`
- Test: `frontend/src/lab/runMachine.test.ts`
- Test: `frontend/src/components/ResultsPanel.test.ts`
- Test: `frontend/src/views/LabView.test.ts`

**Interfaces:**
- Consumes: validated graph, selected registry algorithm, registry-derived parameters, run API status/result, and IndexedDB history.
- Produces: `executeRun(request, api, onState)` states `submitting`, `polling`, `completed`, `error`; semantic result tables; ECharts options; Cytoscape overlays; side-by-side comparison.

- [ ] Write failing run-machine tests for immediate completion, queued polling, malformed backend error, and status transitions.
- [ ] Write failing result tests proving tables, chart containers, warnings, overlay headings, provenance, empty output, and comparison labels render from complete `RunResult` fixtures.
- [ ] Write a failing laboratory test proving running disables duplicate submission, completion saves local history, an error remains recoverable, and reset restores graph plus parameter defaults.
- [ ] Run the three files; expect missing run workflow/results failures.
- [ ] Implement the state machine, live status region, ECharts rendering with resize cleanup, result tables/overlays/provenance, comparison, local save, and bundle download.
- [ ] Re-run the three files; expect them to pass.

### Task 6: Editorial-scientific visual system and completion verification

**Files:**
- Create: `frontend/src/styles/base.css`
- Modify: all page/component templates where browser review identifies hierarchy or accessibility defects.
- Create: `.superpowers/sdd/social-network-teaching-platform/task-3-report.md`

**Interfaces:**
- Produces: warm paper/ink/oxide visual tokens, projection-sized typography, responsive layouts, `:focus-visible` treatments, `prefers-reduced-motion` overrides, and print/presentation rules.

- [ ] Add the static visual system with no gradients, glassmorphism, icon-only controls, or decorative card repetition.
- [ ] Run `npm test -- --run`, `npm run build`, `python -m pytest backend/tests -q`, and `python backend/manage.py check`; record exact outputs.
- [ ] Render `/`, `/cases`, `/cases/zachary-karate`, `/lab`, and `/present/zachary-karate` at desktop and mobile widths when local browser tooling is available; record screenshots or the exact unavailable capability.
- [ ] Check keyboard focus, landmark/headings, empty/loading/error/live regions, contrast tokens, reduced-motion CSS, and anonymous routing against the brief.
- [ ] Inspect `git diff --check`, `git status --short`, and the full scoped diff; leave `extract_docx.py`, `说明书_提取.txt`, and `.mimosa` untouched.
- [ ] Write the Task 3 report with feature map, RED/GREEN commands, outputs, visual/accessibility evidence, changed files, and self-review concerns.
- [ ] Commit the complete scoped Task 3 change as one reviewed commit.
