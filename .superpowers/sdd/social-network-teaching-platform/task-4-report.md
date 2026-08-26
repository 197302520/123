# Task 4 Report — Integration, cases, reports, security, and deployment

## Status

Implemented the complete Task 4 scope on `feature/social-network-teaching-platform`. The anonymous path now loads a published runnable case, submits its real graph/algorithm/default-resolved parameters to the worker contract, observes queue state, retrieves a nonempty real result, and downloads a server-generated reproducibility ZIP. Staff teachers have a CSRF-protected draft/create/edit/publish path and Django-admin mutations are audited. No student account or durable student profile was added.

## Seven-case inventory and provenance

The seed command uses `update_or_create`, remains idempotent, and leaves exactly these seven task seed cases in a clean database. Every dataset records nonempty `source`, `license`, `cleaning`, `version`, `graph`, `algorithm`, `parameters`, and `seed` fields. The end-to-end test executes all seven through the production algorithm registry and requires a nonempty result plus real graph and parameter hashes.

| Case | Data/provenance | Runnable contract |
| --- | --- | --- |
| `zachary-karate` | NetworkX 3.x bundled `karate_club_graph`, Wayne W. Zachary (1977) attribution; NetworkX BSD-3-Clause noted; node IDs normalized to strings and faction attributes retained separately. | `community.louvain`, resolution 1.0, seed 7. |
| `dolphins` | Deterministic synthetic two-community dolphin teaching graph, inspired by but not copied from Lusseau et al. (2003); project-generated CC0-1.0. | `community.lpa`, seed 13. |
| `football-bipartite` | Project-generated CC0 directed player→club bipartite membership graph plus a real NetworkX weighted player projection; node `attributes.kind`, projection graph, and projection method are retained. | `centrality.hits`, seed 5; the advertised runnable input is the bipartite source graph. |
| `enterprise-text` | Project-written fictional Chinese enterprise statements, CC0; NFKC/rule-extraction cleaning and evidence-offset policy recorded; no real company claims. | `text.extract` with rule method and normalized relation weights, seed 0. |
| `trade-snapshots` | Three deterministic fictional six-country weighted snapshots, project-generated CC0; stable country names and positive undirected weights. | `community.dynamic`, threshold 0.3, seed 17. |
| `opinion-dynamics` | Generated anonymous classroom-role graph and 0–1 initial opinions, project-generated CC0. | `opinion.degroot`, bounded convergence parameters, seed 23. |
| `cora-citations` | Generated Cora-style directed citation topology with topic and three-dimensional binary node attributes embedded in every GraphSpec node; explicitly does not copy Cora records, labels, or features; CC0. | `embedding.ae` jointly consumes adjacency and the three feature columns, seed 29. |

## Integration and report contracts

- `/api/cases/:slug/` returns the published dataset metadata used by `/lab?case=:slug`; the laboratory loads its graph, advertised algorithm, merged registry defaults, parameters, and seed, then requires server graph validation before enabling the run.
- Run submission returns `pending`, `running`, `completed`, `failed`, or `cancelled`; the frontend polls both nonterminal states and surfaces failed/cancelled/timeout outcomes. Tests use deterministic eager execution; production Compose sets `CELERY_TASK_ALWAYS_EAGER=0` and supplies separate Redis-backed worker and beat services.
- A worker atomically claims only `pending` jobs, writes `running` before computation, and writes `completed` together with the nonempty result. Duplicate delivery cannot re-execute running or terminal jobs. Algorithm/input failures use structured errors; broker-delivery failure marks the row failed and returns a generic 503 without connection details. Public cancellation is available at `POST /api/runs/:id/cancel/`, is idempotent for cancelled rows, revokes an addressable Celery task without force termination, and uses the persisted cancelled state to win both success and error races.
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

python scripts/verify_release.py --timeout 300
full bounded release gate repeated successfully: backend 205 passed; Django, migrations, dependency, and Compose checks green; frontend 92 passed; build green; npm audit found 0 vulnerabilities

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

## Review-fix appendix — 2026-08-26

This appendix records the post-Task-4 review fixes and supersedes older statements above where the contracts changed, especially cancellation and the football/citation runnable methods.

### Corrective scope

- **TLS and client identity:** the public frontend remains bound to `127.0.0.1:8080`. Inner Nginx now preserves the outer proxy's validated `X-Forwarded-Proto`, `X-Real-IP`, and normalized `X-Forwarded-For` instead of replacing them with the inner HTTP hop or proxy-container address. Production guidance requires the outer proxy to remove client-supplied forwarding headers and reconstruct them; Django trusts them only when `DJANGO_TRUST_PROXY_HEADERS=1`.
- **Teacher boundary:** teacher session/case APIs explicitly use only DRF `SessionAuthentication`, so Basic authentication cannot mutate teacher content and session mutations remain CSRF-protected. Login counters use atomic cache `add`/`incr`, count failed credential attempts, and reset after a successful admin login. Slug prechecks remain user-friendly while transactional `IntegrityError` handling converts uniqueness races to HTTP 409 without partial audit records.
- **Cancellation and recovery:** `Run.task_id` addresses queued work. Submission selects `default` or `ml`, persists the ID, and calls Celery with the selected queue. Cancellation atomically moves pending/running rows to cancelled, clears results, records a terminal time, requests non-terminating revoke, and is idempotent. Worker success and algorithm-error races both re-read/preserve cancellation. Cleanup marks running rows whose lease exceeds `RUN_LEASE_SECONDS` failed before applying the existing two-hour deletion policy, avoiding permanent running rows.
- **Shared limits:** production Django cache uses `django-redis` at Redis DB 1, shared by Gunicorn/worker processes. Anonymous public operations receive a random, HttpOnly, two-hour session cookie without a profile or server-side identity record. Independent IP and cookie buckets, operation categories, standard/heavy algorithm categories, and failed teacher-login buckets use atomic cache counters. Rate/lease settings are passed through Compose.
- **Runnable data forms:** football now advertises and runs HITS on the genuine directed player→club bipartite graph while preserving a derivable weighted player projection. Cora-style features live inside GraphSpec node attributes; the AE input concatenates normalized adjacency with those attributes and records `node_attribute_dimensions=3` in provenance.
- **Import/export hardening:** the frontend sends TXT, CSV, XLSX, JSON, GraphML, and GEXF files to `/api/graphs/import/` as multipart data and presents backend success/errors. JSON node/edge arrays decode item-by-item and XML uses an event preflight, enforcing caps before retaining a complete attacker-sized graph. Graph normalization rejects XML-illegal IDs, labels, and attribute strings. CSV formula neutralization detects dangerous prefixes after spaces, tabs, CR, LF, vertical tabs, or form feeds. GraphML includes serialized node attributes and is parsed in tests.
- **Operations:** restore resolves both root and source canonically, requires a regular `social-network-*.dump` beneath `/backups`, and uses `pg_restore --clean --if-exists --single-transaction`. The classroom load tool submits 90 distinct real cache keys with at most 30 concurrent jobs and rejects duplicate run IDs. Production CPU workers consume only `default`; optional GNN workers consume `ml`. Unexpected worker/broker exceptions emit a content-free stack plus run/task/algorithm identifiers, while clients receive generic errors.
- **UI naming:** a completed current run downloads the server multi-format ZIP. Historical local records now explicitly download a “浏览器 JSON 快照”, with correspondingly renamed code, avoiding the previous ambiguous “复现包” label.

### Review RED/GREEN evidence

Backend review tests were written first. The first combined run recorded `22 failed, 27 passed`; failures directly covered Basic-auth mutation, login accounting, missing anonymous session, uniqueness races, cancellation/task IDs/races/leases/queue routing, sanitized logs, attributed cases, formula/XML safety, bounded parsers, shared Redis, proxy forwarding, restore, and distinct load jobs. After a final extra cancellation-error-race test, its isolated RED was `1 failed`, followed by `1 passed` after preserving cancelled state on the error path.

Frontend review tests were then written first. Their RED run recorded `6 failed, 21 passed` for missing multipart import, cancellation client/integration, six-format labels/error state, and ambiguous local JSON naming. The same focused set finished GREEN at `28 passed`.

Final focused review suite:

```text
python -m pytest backend/tests/test_task4_security.py backend/tests/test_task4_queue_cache.py backend/tests/test_task4_cases_e2e.py backend/tests/test_task4_deployment.py -q
50 passed in 5.60s
```

### Review final verification

```text
python -m pip install -e "backend[dev]"
succeeded; django-redis 5.4.0 resolved and installed

python -m pytest backend/tests -q
180 passed in 6.29s

frontend: npm test -- --run
20 test files passed; 87 tests passed

frontend: npm run build
vue-tsc -b && vite build; 661 modules transformed; built in 5.12s

python backend/manage.py check
System check identified no issues (0 silenced).

python backend/manage.py check --deploy  # production TLS/host/origin/proxy env
System check identified no issues (0 silenced).

python backend/manage.py makemigrations --check --dry-run
No changes detected

python -m pip check
No broken requirements found.

python scripts/validate_compose.py compose.prod.yaml
compose contract valid

python scripts/verify_release.py --dry-run
all bounded release commands enumerated successfully

python scripts/load_test.py --dry-run --students 90 --max-jobs 30
students=90 max_jobs=30 distinct_jobs=90 deadline=120s

frontend: npm audit --audit-level=high
found 0 vulnerabilities

git diff --check
no whitespace errors (only repository LF-to-CRLF notices)
```

### Review concerns and file delta

- Docker is unavailable locally, so live outer-proxy, Redis multi-process, Celery revoke/redelivery, PostgreSQL transactional restore, optional ML image, and 90-student capacity behavior remain staging checks; executable settings/header/Compose/script contracts cover them locally and no container execution is claimed.
- Vite still reports the pre-existing nonfatal lazy `ResultsPanel` chunk warning (608.76 kB minified / 207.24 kB gzip).
- Review changes span backend settings/models/migration/auth/throttles/queue/tasks/parsers/graph attributes/embeddings/reports/seeds/tests, frontend API/editor/run cancellation/history naming/tests, and production Nginx/Compose/env/restore/load/docs. Unrelated `extract_docx.py`, `说明书_提取.txt`, and `.mimosa` remain untouched and unstaged.

## Second review-fix appendix — 2026-08-26

This appendix records the queue/link-prediction re-review and supersedes the earlier cancellation/lease wording above.

### Corrective contracts

- **Bounded link prediction:** all four `link_prediction.*` algorithms are heavy-throttle work, registry version 1.1, and accept explicit `candidate_limit` (1–50,000) plus `top_k` (1–500). Their public shape is materially lower at 500 nodes/5,000 edges, so a 2,000-node sparse graph is rejected before the quadratic candidate space is entered. Candidate scoring consumes at most `candidate_limit` nonedges and keeps only `top_k` records with a bounded heap. AUC positives, negatives, and stored training-edge evidence are capped at 200; provenance records total/evaluated/truncated candidate counts and only bounded samples.
- **Renewable queue leases:** a worker claims a run with one conditional `pending`→`running` update, sets `lease_expires_at`, and renews only its matching running row from a content-free heartbeat thread. Success and failure use conditional `running`→terminal writes, so cleanup, cancellation, or another terminal outcome always wins against late completion/error. Beat fails expired leases, boundedly re-enqueues stale pending deliveries with the original task ID/queue and an atomic `queued_at` claim, and ends repeatedly undeliverable jobs after `MAX_PENDING_REQUEUES`. Duplicate deliveries execute the algorithm once.
- **Real cancellation:** cancelling pending work uses non-terminating revoke because the database claim already prevents execution. Cancelling running work persists `cancelled`, clears its lease/result, and asks Celery to revoke with `terminate=True` and configurable safe `SIGTERM`; the worker cannot overwrite the terminal state. A failed broker revoke returns a generic 503, retains `cancel_revoke_pending`, and can be retried idempotently. The laboratory keeps the cancelled run ID/status visible, surfaces cancellation failure, offers “重试取消任务”, and remains reset/re-run capable.
- **Reproducible attributes:** GraphML import now decodes the exporter’s node `attributes` JSON object instead of nesting it as a string. Export→import→AE testing proves citation `features` remain numeric and are consumed as two attribute dimensions.
- **Teacher/admin production boundary:** teacher PATCH parses only controlled fields, then refetches the case with `select_for_update()` inside the mutation transaction, saves only `update_fields`, and writes its audit in that transaction. The production image collects hashed admin static assets with WhiteNoise, and inner Nginx sends `/static/` to Django while preserving validated outer proxy headers. Compose passes `${DJANGO_NUM_PROXIES:-1}` rather than hardcoding the deployment topology.
- **Operational evidence:** sanitized exception records carry the original traceback object through `exc_info`, but preformat only filename/line/function locations and a suppressed detail marker, so neither source lines nor input/exception content enter logs. The load tool gives each simulated student a CookieJar-backed opener reused across submit/status/result requests.

### Second-review RED/GREEN evidence

Tests were added before the corresponding implementations. The first combined backend RED run recorded `16 failed, 46 passed`; failures covered all four link limits/parameters/heavy buckets, candidate/AUC bounds, running termination and retryable revoke failure, missing lease/delivery fields, heartbeat/cleanup/late-result/duplicate races, sanitized `exc_info`, GraphML attributes, locked PATCH, admin static, proxy-count substitution, and load-test cookies. The frontend RED run recorded `2 failed, 11 passed` for missing retained cancellation status and missing retryable error UI. A further production routing contract was added before the Nginx static route and recorded `1 failed`.

Focused GREEN after implementation:

```text
python -m pytest backend/tests/test_task4_link_prediction.py backend/tests/test_task4_queue_cache.py backend/tests/test_task4_cases_e2e.py backend/tests/test_task4_security.py backend/tests/test_task4_deployment.py -q
62 passed in 7.94s

frontend: npm test -- --run src/views/LabView.test.ts
13 passed in 2.36s
```

### Second-review final verification

```text
python -m pip install -e backend
succeeded; WhiteNoise 6.12.0 resolved and installed

python -m pytest backend/tests -q
192 passed in 16.69s

frontend: npm test -- --run
20 test files passed; 88 tests passed

frontend: npm run build
vue-tsc -b && vite build; 661 modules transformed; built in 7.07s

python backend/manage.py check
System check identified no issues (0 silenced).

python backend/manage.py check --deploy  # production TLS/host/origin/proxy env
System check identified no issues (0 silenced).

python backend/manage.py makemigrations --check --dry-run
No changes detected

python backend/manage.py migrate --plan
0003/0004/0005 operations enumerated; migration 0005 adds queue time, lease, requeue count, and cancellation-delivery fields

python -m pip check
No broken requirements found.

python scripts/validate_compose.py
compose contract valid

python scripts/verify_release.py --dry-run
all bounded release commands enumerated successfully

python scripts/load_test.py --dry-run --students 90 --max-jobs 30
students=90 max_jobs=30 distinct_jobs=90 deadline=120s

frontend: npm audit --audit-level=high
found 0 vulnerabilities

git diff --check
no whitespace errors (only repository LF-to-CRLF notices)
```

### Second-review concerns and self-review

- Docker remains unavailable, so live Redis/Celery revoke signals, prefork heartbeat behavior, proxy/TLS forwarding, PostgreSQL migration/restore, WhiteNoise container delivery, and the 90-student exercise remain staging checks. Conditional database-state tests and executable settings/Compose/Nginx/Docker/load contracts cover the local boundary; no container or browser screenshot is claimed.
- Bash is not installed on this Windows host, so `bash -n` could not run. Existing restore/backup content contract tests remain green.
- Full tests still emit the existing development-only WhiteNoise warning that `backend/staticfiles` is absent before `collectstatic`; production image collection and a temporary-root executable static-serving test are green.
- Vite retains the pre-existing nonfatal lazy `ResultsPanel` chunk warning (608.76 kB minified / 207.24 kB gzip).
- Manual standards/spec self-review found no remaining Task 4 blocker. The available code-review skill normally delegates two independent axes, but the task explicitly prohibited subagents, so both axes were applied locally. Unrelated `extract_docx.py`, `说明书_提取.txt`, and `.mimosa` remain untouched and unstaged.

## Final review-fix appendix — 2026-08-26

This appendix supersedes the second-review statements about candidate truncation, retry-count failure, and Celery worker termination. The seven seeded cases, provenance inventory, anonymous E2E report path, teacher boundary, upload controls, cache key, and prior security controls remain unchanged and green.

### Final corrective contracts

- **Truthful pending recovery:** a failed initial broker submission remains `pending` with an empty result/error and a stable task ID. Beat atomically advances `queued_at` and re-enqueues at `PENDING_DELIVERY_SECONDS`; it never converts a healthy backlog to a fabricated failure based on retry count. Broker errors are sanitized and wait for the next bounded interval. Expired rows are deleted before recovery selection and are also excluded in both the selection and atomic claim. A nine-minute/99-requeue backlog, lost delivery followed by broker recovery, duplicate delivery, and expired pending exclusion are tested.
- **Safe running cancellation:** production (`CELERY_TASK_ALWAYS_EAGER=False`) Celery workers supervise `python -m learning.job_runner` as a one-shot process with a private request/result directory. The child receives no broker/database/application secret environment variables. The supervisor polls database state, renews the lease, and terminates only that child after cancellation; it never calls Celery `terminate=True`. Pending cancellation uses non-terminating revoke and never launches a child. Success/error writes remain conditional on `running`, so cancellation, lease failure, and expiry win every race and late output is discarded. Two-hour deletion stops the child and returns an internal `expired` outcome without recreating the row. Eager tests retain deterministic in-process execution.
- **Operational logging:** both eager and isolated unexpected failures log the real traceback object with run/task/algorithm identifiers through the sanitizer; exception/input text and graph content are suppressed. The isolated child inherits only stderr for this content-free operational trace while stdout is discarded.
- **Long-job UI:** polling exhaustion now raises a typed `RunStillActiveError`, sets the Chinese background state “任务仍在后台运行，可继续查询状态或取消任务。”, and retains the run ID plus immutable request context. Explicit “继续查询状态” resumes the same ID through completion; “取消后台任务” reports server failure without silently losing the capability; whole reset remains deliberate. Tests cover timeout→resume→nonempty completed result and timeout→cancel.
- **GraphML envelope:** exports identify platform files with graph marker `sna_graphspec_v1` and node key `sna_attributes_json`. Only that positive marker enables JSON decoding. Third-party scalar data named `attributes` imports as an ordinary attribute. Export→import preserves citation feature vectors, the display label, and an independent GraphSpec attribute also named `label`; AE consumes the round-tripped features.
- **Global bounded link prediction:** registry version 1.2 limits all four public methods to 300 nodes/5,000 edges, `candidate_limit≤50,000`, and `top_k≤500`; all remain in the heavy throttle bucket. Candidate count is an admission check: oversized candidate spaces fail with a parameter-path error. Admitted runs traverse every nonedge, retain only the global `top_k` through a bounded heap, keep AUC samples bounded, and report the exact evaluated/total count with `candidate_pairs_truncated=false`. Tests reject the old lexicographic-prefix behavior and place the best pair late in node-ID order.
- **Executable Web liveness:** `/api/health/` returns only `{"status":"ok"}`. Compose now performs a real HTTP request to Gunicorn, using the first configured allowed host and the trusted HTTPS forwarded-protocol header so production host validation and SSL redirect do not turn the probe into a false failure.

### Final RED/GREEN evidence

The first focused backend RED run was `11 failed, 19 passed`, covering broker truthfulness, running cancellation without Celery termination, healthy backlog retention, expired-pending ordering, isolated-child cancellation, GraphML envelope/collisions, lower link limits/global admission, and HTTP health. The focused frontend RED run was `4 failed, 5 passed`, covering typed background timeout, resume, retained controls, and explicit cancellation. Additional isolated RED runs recorded `1 failed` each for child traceback identifiers, trusted Host/HTTPS health headers, stopping an isolated child when two-hour cleanup deletes its row, and replacing a credential denylist with a runtime environment allowlist.

Focused GREEN:

```text
python -m pytest backend/tests/test_task4_security.py backend/tests/test_task4_queue_cache.py backend/tests/test_task4_link_prediction.py backend/tests/test_task4_deployment.py backend/tests/test_task4_cases_e2e.py -q
75 passed in 8.56s

frontend: npm test -- --run src/lab/runMachine.test.ts src/views/LabView.background.test.ts
9 passed
```

### Final verification

```text
python -m pip install -e "backend[dev]"
succeeded; all constrained backend/runtime/test dependencies resolved

python -m pytest backend/tests -q
205 passed in 9.71s

frontend: npm ci --ignore-scripts
267 packages installed; 0 vulnerabilities

frontend: npm test -- --run
21 test files passed; 92 tests passed

frontend: npm run build
vue-tsc -b && vite build; 661 modules transformed; built in 8.53s

python backend/manage.py check
System check identified no issues (0 silenced).

python backend/manage.py check --deploy  # production TLS/host/origin/proxy env
System check identified no issues (0 silenced).

python backend/manage.py makemigrations --check --dry-run
No changes detected

python backend/manage.py migrate --plan
0003/0004/0005 operations enumerated

python -m pip check
No broken requirements found.

python scripts/validate_compose.py compose.prod.yaml
compose contract valid

python scripts/verify_release.py --dry-run
all bounded release commands enumerated successfully

python scripts/load_test.py --dry-run --students 90 --max-jobs 30
students=90 max_jobs=30 distinct_jobs=90 deadline=120s

frontend: npm audit --audit-level=high
found 0 vulnerabilities

git diff --check
no whitespace errors (only repository LF-to-CRLF notices)
```

### Final files and concerns

- Backend runtime changes: `learning/tasks.py`, new `learning/job_runner.py`, `learning/views.py`, `learning/urls.py`, and `config/settings.py`.
- Algorithm/import changes: `algorithms/prediction.py`, `algorithms/registry.py`, `algorithms/exports.py`, and `safe_imports.py`.
- Frontend changes: `lab/runMachine.ts`, `components/RunStatus.vue`, `views/LabView.vue`, and their focused tests, including new `LabView.background.test.ts`.
- Production/tests/docs: `compose.prod.yaml`, `.env.production.example`, `docs/deployment.md`, `scripts/verify_release.py`, and four Task 4 backend test modules. No migration is needed.
- Docker is still unavailable locally, so live Redis/Celery process supervision, outer-proxy TLS, PostgreSQL restore, optional ML image, and the 90-student/30-job capacity run remain staging checks; executable subprocess, HTTP, settings, Compose, and script contracts are green locally. No browser screenshot or Docker run is claimed.
- Vite retains the existing nonfatal lazy `ResultsPanel` chunk warning (608.76 kB minified / 207.24 kB gzip). Frozen npm installation still warns about dev-only transitive `glob@10.5.0` and `whatwg-encoding`; the resolved tree reports zero vulnerabilities.
- A Windows-only localhost socket teardown flake in the load-tool cookie contract was removed by exercising the same `HTTPCookieProcessor` through an in-memory HTTP opener transport; this still proves Set-Cookie propagation across submit/result without an irrelevant operating-system socket dependency. Final full backend verification is green.
- Unrelated `extract_docx.py`, `说明书_提取.txt`, and `.mimosa` remain untouched and will not be staged.

## Isolated-child lifecycle appendix — 2026-08-26

### Contract and implementation

- Every successfully launched algorithm child is finalized from an inner `finally` block before its temporary directory is removed, regardless of monitor/database failure, cancellation, lease loss, missing or malformed output, result-read failure, or terminal-state races.
- Finalization polls the child, terminates it only while live, always performs a bounded wait/join, and falls back to kill plus a second bounded reap attempt after termination or wait failure.
- Cleanup failures are logged with sanitized tracebacks and only the run ID, task ID, algorithm ID, and cleanup stage. Cleanup performs no database transition, so it cannot overwrite completed, failed, cancelled, or expired state.
- Request serialization happens before launch; therefore a request-write failure has no child to reap. A temporary-directory exit failure occurs only after the launched child has already been finalized.

### RED → GREEN evidence

```text
RED: python -m pytest backend/tests/test_task4_queue_cache.py -q -k "monitor_failure_still or malformed_child_result or cleanup_failure_is_sanitized"
3 failed, 25 deselected

GREEN: python -m pytest backend/tests/test_task4_queue_cache.py -q
30 passed, 12 warnings

python -m pytest backend/tests/test_task4_security.py backend/tests/test_task4_queue_cache.py backend/tests/test_task4_link_prediction.py backend/tests/test_task4_deployment.py backend/tests/test_task4_cases_e2e.py -q
80 passed, 42 warnings in 8.69s

python -m pytest backend/tests -q
210 passed, 61 warnings in 9.64s

python backend/manage.py check
System check identified no issues (0 silenced).

python backend/manage.py makemigrations --check --dry-run
No changes detected

git diff --check
No whitespace errors; only repository LF-to-CRLF notices.
```

Frontend files were not touched in this follow-up, so the frontend suite/build were not repeated. Changed scope is limited to `backend/learning/tasks.py`, its Task 4 queue/lifecycle tests, and this report. The unrelated extraction files remain untouched and unstaged.
