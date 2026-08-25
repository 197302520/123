# Task 3 Report — Case-oriented anonymous student frontend

## Status

Implemented the complete Task 3 student frontend on `feature/social-network-teaching-platform`. Public learning routes are anonymous and consume the existing Django content, graph-validation, algorithm-registry, run-status, and result APIs. No production fixtures or canned algorithm results were added.

## Feature map

| Requirement | Implementation |
| --- | --- |
| Distinctive home | Editorial landing page with case/method/evidence narrative, real module/case API content, strong projection-scale hierarchy, and warm paper/ink/oxide design tokens. |
| Seven-module course library | `/courses` ledger plus `/courses/:slug` detail, driven by the real seven-module API; frontend editorial metadata is keyed to backend slugs. |
| Filterable case library | `/cases` supports keyword + module filtering, live result count, clear action, and loading/empty/error states. |
| Six-section case detail | `/cases/:slug` implements 提出问题、认识数据、选择方法、运行分析、解释发现、反思迁移 with ARIA tabs and arrow/Home/End keyboard navigation. |
| Presentation mode | `/present/:slug` supplies classroom-scale scenes, six-step progress, visible previous/next controls, and Arrow/Page/Space keys. |
| Graph import/paste/validation | JSON and whitespace/CSV-like edge-list parsing, 5 MB file guard, precise local errors, server `/graphs/validate/` normalization, Cytoscape preview, and explicit “教学示例（非算法结果）” labelling. |
| Registry controls | `/api/algorithms/` supplies algorithm name, version, formula, explanation, supported graph types, limits, and parameter schemas. Boolean/number/choice/string/array/object controls derive from those schemas and reset to registry defaults. |
| Run/status/results | Real `/api/runs/` submission plus pending polling and result retrieval; live idle/submitting/polling/completed/error states; duplicate submit disabled. Tables, Cytoscape overlays, ECharts bar/line/scatter/heatmap/gauge/timeline views, warnings, and provenance render from `RunResult`. KaTeX renders registry formulas. |
| Compare/reset | A current run can be compared side-by-side with any local historical run. Parameter-only and whole-experiment reset paths are explicit. |
| Anonymous local history | Real IndexedDB database `sna-learning-history`, newest-first listing, delete/clear controls, and no user/account identifier. |
| Reproducibility bundle | JSON Blob download includes schema, input graph, parameters, random seed, algorithm key/name/version, full result, and backend provenance/hashes. |
| No student login gate | `/`, `/courses`, `/courses/:slug`, `/cases`, `/cases/:slug`, `/lab`, and `/present/:slug` have no authentication metadata or redirect. Only a quiet footer link points to `/admin/`. |

## Test-first evidence

### RED

Initial command:

```text
cd frontend
npm test -- --reporter=verbose
```

Observed before production implementation:

```text
Test Files 14 failed (14)
Tests      2 failed (2)
```

Failures were the expected missing behavior: unresolved router/views/components/lab modules and absent `fetchAlgorithms` / `validateGraph` client functions. After self-review identified backend heatmap/gauge/timeline shapes, a second focused RED was captured:

```text
npm test -- src/components/chartOptions.test.ts --reporter=verbose
Test Files 1 failed (1)
Error: Failed to resolve import "./chartOptions"
```

### GREEN

Final frontend command and output:

```text
npm test -- --reporter=default
Test Files 15 passed (15)
Tests      25 passed (25)
Duration   6.01s
```

Coverage includes case filtering, six-section/keyboard navigation, anonymous route registration, presentation keyboard control, parameter and whole-experiment reset, graph parse/validation errors, immediate/polled/error run states, result tables/charts/overlays/warnings/provenance, empty results, compare, IndexedDB ordering/delete/clear, reproducibility bundle content, reduced-motion behavior, and heatmap/timeline/gauge conversion.

## Final verification

```text
frontend: npm run build
vue-tsc -b && vite build
✓ 661 modules transformed
✓ built in 4.76s

backend: python -m pytest backend/tests -q
130 passed in 3.50s

python backend/manage.py check
System check identified no issues (0 silenced).

frontend: npm audit --omit=dev
found 0 vulnerabilities

git diff --check
no whitespace errors
```

ECharts was upgraded to 6.1.0 after `npm audit` identified the fixed 5.x XSS advisory. The modular chart registration and the existing chart tests/build passed after the upgrade.

## Accessibility review

- Semantic `header`, labelled `nav`, `main`, sections/articles/asides, tables with captions, headings, and footer landmarks.
- Skip link, text-labelled actions (no mystery icon-only controls), native form labels, visible `:focus-visible` outline, and tab roving focus.
- Loading and run progress use `role="status"` / `aria-live`; graph/run/content errors and warnings use `role="alert"`; empty states explain the next action.
- Presentation and case navigation are keyboard operable; disabled controls remain visible and understandable.
- `prefers-reduced-motion: reduce` disables CSS animation/transition and Cytoscape/ECharts animation. This is covered by an executable test.
- Core contrast ratios were calculated from production tokens: ink/paper 13.88:1, soft ink/paper 6.23:1, oxide-dark/paper 7.82:1, and light text/oxide button 5.56:1, all above WCAG AA normal-text thresholds.
- Responsive rules cover 1050 px and 760 px breakpoints; horizontal section tabs remain scrollable instead of being truncated.

## Visual QA evidence and exact gap

The local integration environment was prepared successfully:

- SQLite migrations completed and seven modules/two core case metadata records were seeded.
- Django started at `127.0.0.1:8000` with system checks clean.
- Vite started at `127.0.0.1:4173`.

Automated viewport screenshots could not be captured. `agent-browser 0.35.0` found no installed Chrome/Chromium. Its standard isolated Chrome-for-Testing 152 download retried three times and ended with `operation timed out`. Both local servers were then stopped. Therefore this report does **not** claim desktop/mobile screenshot review; visual evidence is limited to production rendering/build, component DOM tests, responsive CSS inspection, and the accessibility checks above.

## Files changed

- Frontend entry/config/dependencies: `frontend/index.html`, `package.json`, `package-lock.json`, `vite.config.ts`, `tsconfig.app.json`, `src/main.ts`, `src/App.vue`.
- Typed API: `frontend/src/api/contracts.ts`, `frontend/src/api/client.ts` and client tests.
- Routes/content/views: `frontend/src/router.ts`, `src/content/catalog.ts`, and home/course/module/case/case-detail/lab/presentation views plus tests.
- Laboratory core: `frontend/src/lab/{exampleGraph,graphInput,historyStore,parameters,reproducibility,runMachine}.ts` plus tests.
- Components: app footer, graph editor/canvas, parameter controls, formula, run status, charts/chart adapters, results, history, and teaching-example network plus tests.
- Visual/accessibility: `frontend/src/styles/base.css`, `src/accessibility.ts` and reduced-motion test.
- Test support: `frontend/src/test/setup.ts`, `frontend/src/test/fixtures.ts`.
- Planning/reporting: `docs/superpowers/plans/2026-08-25-anonymous-student-frontend.md` and this report.

## Concerns and self-review

1. The async `ResultsPanel` chunk is 604.62 kB minified (205.56 kB gzip), largely ECharts. It is downloaded only after a result exists; initial shell, route, lab, and Cytoscape chunks are separated. Vite emits a non-fatal >500 kB warning.
2. Real viewport screenshots remain outstanding because the browser runtime could not be downloaded. This is the only requested verification step not completed.
3. Task 1 currently seeds two public case records. The case library handles any number of API cases and explicit empty/filter states; Task 4 is expected to add the broader runnable case set.
4. The current backend completes jobs synchronously, while the frontend also supports future `pending` polling without changing the public workflow.
5. Unrelated untracked `extract_docx.py`, `说明书_提取.txt`, and `.mimosa` content were not edited or staged.

## Post-review corrective pass — 2026-08-26

### Corrected workflow and rendering behavior

- Graph readiness is revoked on the first source-text edit after validation; the run action cannot submit the previously normalized graph. Graph, algorithm, parameters, and seed are deep-cloned before submission and that immutable snapshot now supplies the request, current-result record, IndexedDB history, comparison, provenance display, and reproducibility download.
- Algorithm/graph/parameter/seed controls are disabled while submitting or polling. Poll delays and all run requests receive one `AbortSignal`; reset, replacement, and unmount abort pending work without a terminal-state update or late history write.
- Floyd–Warshall heatmaps now consume the backend's long-form `{source,target,distance}` rows. Result edge overlays merge candidate edges into the validated base network; candidate edges are visibly distinguished as high-contrast dashed edges.
- Comparison now rejects the current run as its own baseline and juxtaposes algorithm/version/seed, every parameter value, and exact backend table rows for the current and selected historical runs.
- Presentation scenes now derive background, data, method, run/result reading, interpretation, and extension content from the selected case title, summary, content, module, dataset provenance, and metadata. Global shortcuts ignore links and form controls, ignore key repeat, and no longer double-advance a focused button on Space.
- IndexedDB load/save/delete/clear failures are caught and announced in the local-history region. A completed backend result remains visibly completed if only local persistence fails. Clear-all now requires confirmation.
- Successful-empty states were added for home modules, home cases, the course library, and an empty algorithm registry. Structured array/object parameters reject malformed or type-mismatched JSON without changing submitted values. Non-object edges receive a controlled Chinese validation issue.
- Module, case-detail, and presentation views reload on route-prop changes. The file-import input remains keyboard focusable and its enclosing label has an explicit `:focus-within` outline.

### Review RED evidence

Tests were added before these production corrections. The first complete run produced the intended failures:

```text
npm test -- --reporter=verbose
Test Files 12 failed | 6 passed (18)
Tests      22 failed | 24 passed (46)
Errors     1 unhandled rejection
```

The unhandled rejection was the deliberate failing IndexedDB-load double, confirming that the prior code leaked local-store failures. Other failures directly exposed stale graph readiness, mutable pending configuration, wrong Floyd and predicted-edge shapes, summary-only comparison, generic presentation content, missing route reactions/empty states, malformed structured-parameter fallback, and absent cancellation.

### Review GREEN and final verification evidence

After the corrections, the expanded suite is green with no unhandled errors:

```text
npm test -- --reporter=default
Test Files 18 passed (18)
Tests      47 passed (47)
Duration   9.28s

npm run build
vue-tsc -b && vite build
✓ 661 modules transformed
✓ built in 6.33s

python -m pytest backend/tests -q
130 passed in 4.32s

python backend/manage.py check
System check identified no issues (0 silenced).

npm audit --omit=dev
found 0 vulnerabilities
```

The final diff check reported no whitespace errors. The build still reports the documented non-fatal async `ResultsPanel` chunk warning (607.03 kB minified / 206.41 kB gzip). Browser viewport QA was not retried: the exact prior gap remains—no installed local Chrome/Chromium, and the Chrome-for-Testing download timed out after three retries—so no screenshot or interactive-browser claim is made for this corrective pass.

## Second post-review corrective pass — 2026-08-26

### Backend-shape and lifecycle corrections

- Overlay rendering now distinguishes full graph replacements from additive evidence. `generated_graph` (ER/WS/BA) and `extracted_graph` (text extraction) render only the backend-returned nodes and edges, including their backend provenance-directedness; `predicted_edges`, centrality, opinion, HITS, robustness, and community overlays retain the validated input graph and add visual evidence to it.
- Every backend overlay key has an explicit classroom-readable caption and executable mapping coverage. HITS uses hub score for node size and authority score for node color plus an `H / A` label. Robustness uses inverse removal order for size/color and labels the exact removal position. Centrality/opinion values control size, all community variants control color, and predicted relations are dashed.
- Floyd heatmaps preserve a zero diagonal, finite path lengths, and `null` unreachable distances as distinct values. The ECharts tooltip reports `不可达` for `null` instead of coercing it to zero; user-provided node labels are escaped before tooltip HTML rendering.
- Graph validation now combines an `AbortController` with a monotonically increasing source revision. Editing, importing, starting a replacement validation, or unmounting invalidates the older request, so late responses cannot normalize the preview or mark stale source text ready.
- Whole-experiment reset remounts the parameter editor, clears structured JSON errors, restores registry defaults, and synchronizes parent validity before the graph is revalidated.
- History error and empty states are mutually exclusive. IndexedDB connections close from `finally` for success, request failure, transaction failure, and synchronous structured-clone failure. File import read failures are caught, invalidate readiness, and announce a controlled Chinese error.
- Module, case, and presentation loaders use request revisions; a slower response for an older route can no longer replace the latest slug content.

### Second review RED / GREEN evidence

The review tests were written against the committed implementation first. The initial targeted RED captured the production failures:

```text
npm test -- <10 review test files> --reporter=dot
Test Files 8 failed | 2 passed (10)
Tests      21 failed | 30 passed (51)
Errors     1 unhandled file-read rejection
```

The route-race tests were then strengthened to wait until the deliberately delayed older response had completed its DOM update; all three failed by displaying the obsolete module/case/presentation. After implementation, the same targeted set passed `51/51`, and expanded Cytoscape schema coverage remained green.

Fresh final verification:

```text
npm test -- --reporter=default
Test Files 19 passed (19)
Tests      75 passed (75)
Duration   8.96s

npm run build
vue-tsc -b && vite build
✓ 661 modules transformed
✓ built in 6.63s

python -m pytest backend/tests -q
130 passed in 3.73s

python backend/manage.py check
System check identified no issues (0 silenced).

npm audit --omit=dev
found 0 vulnerabilities
```

The only build concern remains the non-fatal async `ResultsPanel` chunk warning, now 608.76 kB minified / 207.24 kB gzip. The previously documented browser QA gap is unchanged and no new visual-browser claim is made.
