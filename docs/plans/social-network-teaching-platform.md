# Implementation Plan: 社会网络分析案例式智能教学平台

## Global constraints

- Students use all public learning, case, and laboratory pages anonymously; only teachers authenticate.
- The product follows a course + case + practice information architecture without copying CORIDM branding or assets.
- Anonymous experiment history is stored in browser IndexedDB. Uploaded student data is temporary and must not become a durable student profile.
- Every exposed algorithm runs real computations. Unsupported input shapes return a clear validation error, never fabricated output.
- Identical graph, parameters, algorithm version, and random seed must be reproducible.
- The public product is Chinese-first, desktop-first, responsive, and usable without installing software.
- Use a Vue 3 + TypeScript frontend and Django 5.2 + DRF backend. PostgreSQL/Redis/Celery are production services; tests may use SQLite and eager/synchronous execution.
- Development follows test-first red/green/refactor. Generated scaffolding and static editorial copy do not require behavior tests.

## Task 1: Project foundation and public content API

Create the runnable monorepo foundation: Django/DRF backend, Vue/Vite frontend shell, Docker Compose, environment templates, and developer documentation. Add teacher-only Django admin models for course modules, cases, datasets, and publish status. Add anonymous public endpoints for module and case listing/detail, graph validation, algorithm registry, run submission/status/result, and report generation. Define shared GraphSpec, AlgorithmSpec, RunRequest, and RunResult contracts. Seed seven modules and at least Zachary and dolphins case metadata.

Acceptance criteria:

- Backend tests first demonstrate public read access, unpublished-content exclusion, teacher-only mutation, graph validation, and stable API shapes.
- `pytest` passes and Django system checks are clean.
- The frontend builds and can call the public API through a development proxy.
- Docker Compose defines web, worker, postgres, redis, and frontend services with health checks or dependency readiness.

## Task 2: Tested social-network algorithm engine

Implement a registry-driven Python algorithm engine with real results and a uniform RunResult. Cover graph construction/validation; topology and Floyd paths; clustering coefficients and ER/WS/BA evidence; degree/closeness/betweenness/eigenvector/PageRank/HITS/centralization; KL, agglomerative/divisive hierarchy, GN, Fast Newman greedy modularity, Louvain, Leiden with documented fallback, LPA, CPM, LFM, SLPA; robustness S(q)/R under random and targeted attack; CN/Jaccard/AA/RA and leakage-safe AUC; DeGroot, FJ, Deffuant, HK; dynamic-community matching/events. Provide CPU implementations for AE/CNN embedding clustering and optional-dependency adapters for GCN/GAT. Implement deterministic Chinese text preprocessing, rule/entity/relation candidates, cosine/normalized weights, correction-friendly output, and all standard graph exports; optional PaddleNLP/BGE adapters must degrade explicitly when models are absent.

Acceptance criteria:

- Tests are written and observed failing before implementation, using hand-checkable graphs and deterministic seeds.
- Every registry entry declares supported graph types, parameters, limits, formula, explanation, advantages, and limitations.
- Algorithms return actual tables/overlays/charts/warnings/provenance and never canned results.
- `pytest` covers malformed graphs, disconnected graphs, directed/undirected constraints, stochastic reproducibility, link-prediction leakage, and opinion-model convergence.

## Task 3: Case-oriented anonymous student frontend

Build a distinctive editorial-scientific Vue interface with home, seven-module course library, filterable case library, six-section case detail, free laboratory, and teacher presentation mode. Use Cytoscape.js for graph interaction, ECharts for results, KaTeX for formulas, and IndexedDB for local history. Students can import/paste graph data, validate it, choose algorithms, edit parameters, run, inspect results, compare runs, reset defaults, and download a reproducibility bundle. No public page may require login.

Acceptance criteria:

- Frontend component tests first cover case filtering, six-section navigation, parameter reset, anonymous history, graph validation errors, run status, and result rendering.
- Accessibility includes keyboard-visible controls, semantic headings, sufficient contrast, reduced-motion handling, and meaningful empty/error/loading states.
- The production frontend build succeeds without TypeScript errors.
- The visual system is original, Chinese-first, responsive, and suitable for classroom projection.

## Task 4: Integration, cases, reports, security, and deployment

Connect frontend and backend end-to-end. Add runnable Zachary, dolphins, football player-club, enterprise text, trade snapshots, opinion dynamics, and attributed citation cases using bundled or generated/licensed data with provenance. Implement downloadable HTML/JSON/CSV/GraphML bundles and a report endpoint. Add anonymous rate limiting, upload size/shape limits, two-hour temporary cleanup, safe file handling, teacher login protections, audit records, caching by graph/algorithm/parameter hash, and worker queue status. Add production documentation, backup/restore notes, and verification scripts.

Acceptance criteria:

- End-to-end tests cover anonymous case-to-result flow and teacher publish flow.
- Security tests cover unpublished content, unsafe upload types, oversized graphs, rate limits, and cross-boundary teacher/public actions.
- Seed cases run through their advertised algorithms with no fabricated results.
- Full backend tests, frontend tests, frontend build, Django checks, and Docker configuration validation pass.

