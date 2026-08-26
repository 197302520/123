# Task 4 Report — Integration, cases, reports, security, and deployment

## Status

Implemented the complete Task 4 scope on `feature/social-network-teaching-platform`. The anonymous path now loads a published runnable case, submits its real graph/algorithm/default-resolved parameters to the worker contract, observes queue state, retrieves a nonempty real result, and downloads a server-generated reproducibility ZIP. Staff teachers have a CSRF-protected draft/create/edit/publish path and Django-admin mutations are audited. No student account or durable student profile was added.

## Seven-case inventory and provenance

The seed command uses `update_or_create`, remains idempotent, and leaves exactly these seven task seed cases in a clean database. Every dataset records nonempty `source`, `license`, `cleaning`, `version`, `graph`, `algorithm`, `parameters`, and `seed` fields. The end-to-end test executes all seven through the production algorithm registry and requires a nonempty result plus real graph and parameter hashes.

| Case | Data/provenance | Runnable contract |
| --- | --- | --- |
| `zachary-karate` | NetworkX 3.x bundled `karate_club_graph`, Wayne W. Zachary (1977) attribution; NetworkX BSD-3-Clause noted; node IDs normalized to strings and faction attributes retained separately. | `community.louvain`, resolution 1.0, seed 7. |
| `dolphins` | Deterministic synthetic two-community dolphin teaching graph, inspired by but not copied from Lusseau et al. (2003); project-generated CC0-1.0. | `community.lpa`, seed 13. |
| `football-bipartite` | Project-generated CC0 player–club membership graph plus a real NetworkX weighted player projection; source bipartite graph and projection method are retained. | `centrality.degree`, seed 5. |
| `enterprise-text` | Project-written fictional Chinese enterprise statements, CC0; NFKC/rule-extraction cleaning and evidence-offset policy recorded; no real company claims. | `text.extract` with rule method and normalized relation weights, seed 0. |
| `trade-snapshots` | Three deterministic fictional six-country weighted snapshots, project-generated CC0; stable country names and positive undirected weights. | `community.dynamic`, threshold 0.3, seed 17. |
| `opinion-dynamics` | Generated anonymous classroom-role graph and 0–1 initial opinions, project-generated CC0. | `opinion.degroot`, bounded convergence parameters, seed 23. |
| `cora-citations` | Generated Cora-style directed citation topology with topic and three-dimensional binary node attributes; explicitly does not copy Cora records, labels, or features; CC0. | `centrality.pagerank`, alpha/tolerance/iteration parameters, seed 29. |

## Integration and report contracts

- `/api/cases/:slug/` returns the published dataset metadata used by `/lab?case=:slug`; the laboratory loads its graph, advertised algorithm, merged registry defaults, parameters, and seed, then requires server graph validation before enabling the run.
- Run submission returns `pending`, `running`, `completed`, `failed`, or `cancelled`; the frontend polls both nonterminal states and surfaces failed/cancelled/timeout outcomes. Tests use deterministic eager execution; production Compose sets `CELERY_TASK_ALWAYS_EAGER=0` and supplies separate Redis-backed worker and beat services.
- A worker atomically claims only `pending` jobs, writes `running` before computation, and writes `completed` together with the nonempty result. Duplicate delivery cannot re-execute running or terminal jobs. Algorithm/input failures use structured errors; broker-delivery failure marks the row failed and returns a generic 503 without connection details. No cancellation endpoint was added because Tasks 1–3 expose no public cancellation operation; the state remains recognized end-to-end.
- Cache keys are SHA-256 over the normalized graph hash, algorithm key and registry version, parsed/default-resolved parameters, and supplied seed. Node/edge ordering and undirected endpoint order are canonicalized. Only nonempty, completed, unexpired runs can be reused; a cache hit records `cached_from` and gets its own two-hour expiry.
- `POST /api/reports/` returns a standalone escaped HTML report and bundle URL. The ZIP endpoint returns `application/zip`, a fixed UUID-based filename, and `nosniff`; it contains `report.html`, `result.json`, `nodes.csv`, `edges.csv`, `graph.graphml`, `parameters.json`, `provenance.json`, one CSV per result table, and a MIME-bearing `manifest.json`. CSV formula prefixes are neutralized and all HTML cells, node labels, and provenance are escaped.

## Security controls

- Public validation/import/report/run operations use separate IP and session throttles; algorithm submission has independent standard/heavy categories. Rotating sessions cannot bypass the IP bucket. Teacher admin login POSTs have a separate bounded IP window.
- Request/upload caps are 20 MB; public shapes are at most 2,000 nodes and 20,000 edges, followed by stricter registry limits for heavy algorithms. Delimited/XLSX edge parsing stops incrementally at the edge cap; XLSX entry count and expanded size are bounded.
- Import accepts only TXT, CSV, macro-free XLSX, JSON, GraphML, and GEXF. It rejects unsupported extensions, archive masquerading, XLSM/macros, XLSX external links/path traversal, DTD/entities, invalid UTF-8/binary text, multigraph GraphML, invalid weights, and malformed content. Upload contents and enterprise text are not logged.
- Anonymous run rows retain inputs/parameters/results for two hours. Reads filter expired rows immediately and Celery beat deletes expired records every minute.
- Staff authoring uses Django session authentication, `IsAdminUser`, CSRF enforcement, field/type/length validation, draft-by-default behavior, and atomic mutation+audit writes. Public and ordinary authenticated users cannot cross the teacher boundary; unpublished modules/cases/datasets remain invisible.
- Password storage defaults to scrypt with PBKDF2 migration fallback; Django strong password validators and deployment guidance require long password-manager-generated teacher credentials. Session/CSRF secure cookies, HTTPS redirect, HSTS, trusted origins, CSP, `nosniff`, referrer policy, and frame denial are configured for production.
- Proxy headers are trusted only when explicitly enabled. Production exposes only nginx on loopback, fixes the trusted proxy count to one, validates `X-Real-IP` for teacher audit/throttling, and documents that direct Web access must remain blocked.
- Formula fallback HTML is escaped even if KaTeX unexpectedly fails. Dependency installation uses the committed npm lockfile with lifecycle scripts disabled; npm audit and registry-signature verification pass.

## Production and operations

- `compose.prod.yaml` defines PostgreSQL, Redis, Gunicorn Web, Celery worker, separate Celery beat, nginx frontend, an `ops` backup profile, and an optional `ml` worker/image. Required secrets/origins are fail-closed environment substitutions and eager execution is disabled.
- `.env.production.example` covers host/origin/TLS/proxy/rate/shape settings. `docs/deployment.md` covers build, migration, idempotent seed, HTTPS/domain and China ICP/public-security filing note, proxy trust, monitoring, content-free logging, two-hour cleanup, optional ML, backup/restore, encrypted off-host copies, quarterly restore drills, and 14-day retention.
- Backup/restore scripts use PostgreSQL custom-format dumps and constrain restore inputs to named files under `/backups`. The release verifier gives each command a timeout; the classroom load tool is bounded to 90 students, 30 concurrent real jobs, and a caller-supplied deadline.
- Local Docker is unavailable as stated in the task brief, so no image build or container startup is claimed. The production YAML/Docker contract is covered by executable tests and `scripts/validate_compose.py`.

## Test-first evidence

### Initial RED

Production behavior tests were created before the implementation. The initial focused backend run reported `14 failed`; the initial focused frontend run reported `3 failed`. Failures covered missing seven-case runtime metadata, anonymous case-to-result/report ZIP, teacher draft/publish/audit, file import safety, shape/rate/authorization/expiry controls, queue/result/cache semantics, production Compose, backend bundle download, and case loading.

### Corrective RED/GREEN cycles

Focused tests were added before each corrective implementation. Recorded RED evidence included: admin bulk-delete audit plus scrypt default (`2 failed`); trusted-proxy login identity (`1 failed`); cache endpoint canonicalization and broker-delivery handling (`2 behavioral failures`); corrected PostgreSQL slug-boundary test (`1 failed`, observed 201 instead of 400); incremental delimited parsing (`1 failed`, observed 400 instead of the cap-first 413); forwarded-protocol trust (`1 failed`); and lifecycle-script blocking in the production frontend image (`1 failed`). Earlier focused cycles also captured running-state polling, duplicate queue delivery, GEXF import, rotating-session throttling, XLSX expansion limits, and formula fallback escaping before their implementations.

All focused Task 4 tests are now green:

```text
python -m pytest backend/tests/test_task4_cases_e2e.py backend/tests/test_task4_security.py backend/tests/test_task4_queue_cache.py backend/tests/test_task4_deployment.py -q
31 passed in 9.71s
```

The seven-case test calls the real API and real registry implementations; it rejects empty/canned output by requiring tables/overlays/charts plus algorithm, graph-hash, and parameter-hash provenance.

## Exact final verification

```text
python -m pip install -e "backend[dev]"
dependency resolution/install succeeded (including gunicorn 23.0.0 and existing openpyxl 3.1.5)

python -m pytest backend/tests -q
161 passed in 10.92s

frontend: npm ci --ignore-scripts
added 267 packages; found 0 vulnerabilities

frontend: npm test -- --run
20 test files passed; 82 tests passed

frontend: npm run build
vue-tsc -b && vite build; 661 modules transformed; built in 7.16s

python backend/manage.py check
System check identified no issues (0 silenced).

python backend/manage.py check --deploy  # production TLS/host/origin/proxy env
System check identified no issues (0 silenced).

python backend/manage.py makemigrations --check --dry-run
No changes detected

python -m pip check
No broken requirements found.

python scripts/validate_compose.py
compose contract valid

python scripts/verify_release.py --dry-run
all bounded release commands enumerated successfully

python scripts/load_test.py --dry-run --students 90 --max-jobs 30 --deadline 120
students=90 max_jobs=30 deadline=120s

frontend: npm audit --audit-level=high
found 0 vulnerabilities

frontend: npm audit signatures
267 packages have verified registry signatures; 51 have verified attestations

git diff --check
no whitespace errors (Git printed only the repository's LF-to-CRLF conversion notices)
```

## Files changed

- Backend data/state: `learning/models.py`, migration `0003_task4_runs_and_audit.py`, and `seed_learning_content.py`.
- Backend execution: `algorithms/__init__.py`, `algorithms/graph.py`, `run_service.py`, `tasks.py`, `views.py`, `teacher_views.py`, `urls.py`.
- Backend security/reporting: `middleware.py`, `throttles.py`, `safe_imports.py`, `reports.py`, `admin.py`, `config/settings.py`.
- Backend tests/dependencies: the four `backend/tests/test_task4_*.py` suites and `backend/pyproject.toml`.
- Frontend integration: API client/tests, `LabView`/tests, run machine/tests, graph-editor limit messaging, and formula fallback/test.
- Deployment/operations: `.env.production.example`, `compose.prod.yaml`, `backend/Dockerfile.ml`, `frontend/Dockerfile.prod`, `frontend/nginx.conf`, `ops/backup.sh`, `ops/restore.sh`, three bounded scripts, `docs/deployment.md`, and README links.

## Concerns and self-review

1. Docker is unavailable locally, so production images, PostgreSQL/Redis/Celery networking, backup restore, and the live 90-student/30-job exercise remain deployment-environment checks. Static Compose/Docker contracts and bounded dry-runs are green.
2. Vite retains the existing nonfatal async `ResultsPanel` chunk warning: 608.76 kB minified / 207.24 kB gzip. The panel is already lazy-loaded after results exist.
3. The frozen npm install reports deprecation notices for dev-only transitive `glob@10.5.0` (through testing utilities) and `whatwg-encoding`; npm reports zero vulnerabilities and all registry signatures verify. Review these when upstream test dependencies release replacements.
4. Browser screenshots were not required for Task 4 and none are claimed.
5. The security-and-hardening review directly led to scrypt defaults, validated/trusted proxy identity, proxy-conditional forwarded-protocol trust, atomic/bulk admin audit coverage, bounded decompressed/delimited parsing, safe formula fallback, broker-error sanitization, CSP, and lifecycle-script blocking. The five-axis code review found no remaining Task 4 blocker.
6. Unrelated `extract_docx.py`, `说明书_提取.txt`, and `.mimosa` content were neither edited nor staged.
