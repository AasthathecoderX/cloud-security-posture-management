# CSPM Platform — Development Execution Guide

> **Purpose:** This is the step-by-step build manual for the AI-Powered CSPM Platform. It explains *what to do, in what order, and why* for every phase. Read it alongside `Major Project Planning.md` (the design/spec). This guide is the **how-to-build**; the planning doc is the **what-and-why**.
>
> **How to use:** Work top to bottom. Each phase has: a goal, prerequisites, detailed numbered steps, the deliverables that mark it "done", and a definition-of-done checklist. Do not start a phase until its prerequisites pass. You can hand this file to any AI assistant and it will understand the full context of what you're building.

---

## Quick Reference

| Phase | Name | Output |
| ----- | ----- | ----- |
| 0 | Planning & Setup | Repo, dev environment, diagrams, schema |
| 1 | Rule-Based Detection Engine | Working misconfiguration detector |
| 2 | Backend API & Database | REST API + persistence |
| 3 | Frontend Dashboard v1 | Upload → see findings |
| 4 | Live Cloud Integration | "Scan my cloud" via LocalStack |
| 5 | AI/ML Risk Scoring | Trained, integrated ML models |
| 6 | Attack-Path Visualization | Interactive attack graph |
| 7 | Compliance Mapping & Remediation | Compliance tab + fixes |
| 8 | Authentication & Secure Design | Hardened multi-user platform |
| 9 | DevOps: CI/CD + Self-Scanning | Automated pipeline + scheduled scans |
| 10 | Deployment | Live public URL |
| 11 | Testing, Docs & Final Report | Submission-ready project |

**Tech stack reminder:** React + Tailwind (frontend) · FastAPI + Pydantic + SQLModel (backend) · PostgreSQL/Neon (DB) · boto3 + LocalStack (cloud) · Scikit-learn + XGBoost (ML) · NetworkX (graph) · Docker + GitHub Actions (DevOps) · Vercel + Oracle Cloud Always Free (hosting). **Everything is free.**

---

## Pre-Flight (Do Before Phase 0)

Complete these once before any phase. They de-risk the whole project.

1. **Verify free accounts work:**
   - Create a **Vercel** account (frontend hosting).
   - Create a **Neon** account and a free Postgres database; save the connection string.
   - Attempt to launch an **Oracle Cloud Always Free** Ampere VM. *If capacity is unavailable in your region, note it now* and plan to use Fly.io/Koyeb as a static-only fallback.
2. **Install local tooling:** Docker Desktop, Python 3.11+, Node.js LTS, Terraform CLI, Git, VS Code.
3. **Smoke-test the riskiest assumption:** Start LocalStack via Docker and confirm `boto3` can create and list an S3 bucket against it. If this works, the "live scan" feature is viable.
4. **Get supervisor sign-off** on `Major Project Planning.md` scope before building.

---

## Phase 0 — Planning & Setup

**Goal:** A working, shared development environment and agreed design, so building can begin with zero ambiguity.

**Prerequisites:** Pre-flight complete.

### Steps

1. **Create the GitHub repository.**
   - Initialize repo with a `README.md`.
   - Add a `.gitignore` that excludes `.env`, `__pycache__/`, `node_modules/`, `*.joblib`, `.venv/`, and IDE folders.
   - Enable **branch protection** on `main`: require a pull request + at least one review before merge.

2. **Enable repository security from day one.**
   - Turn on **Dependabot** (dependency alerts + version updates).
   - Turn on **secret scanning** (GitHub setting).
   - Add **gitleaks** as a step in CI later (Phase 9) — note it now.
   - Add a `SECURITY.md` describing how issues are reported.

3. **Define the folder structure.** Create these directories with a `.gitkeep` placeholder:
   ```
   /backend      → FastAPI app, rule engine, DB models
   /frontend     → React app
   /ml           → dataset scripts, training notebooks, saved models
   /infra        → docker-compose, Dockerfiles, deployment config
   /rules        → declarative YAML rule definitions
   /docs         → architecture diagram, threat model, schema
   ```

4. **Write the development `docker-compose.yml`** (lives in `/infra`). It defines three services:
   - **FastAPI service** — built from a Python 3.11 Dockerfile, exposes a `/health` endpoint returning `{"status": "ok"}`.
   - **Postgres service** — with env-configured user/password/db, a named volume for persistence, port exposed for local tools.
   - **LocalStack service** — with `SERVICES=s3,ec2,iam`, port `4566` exposed.
   - Add a `.env.example` listing every required variable (DB URL, JWT secret placeholder, LocalStack endpoint) — **never commit the real `.env`**.

5. **Verify the environment end-to-end.** Run `docker compose up`. Confirm:
   - The FastAPI `/health` endpoint responds.
   - Postgres accepts a connection.
   - LocalStack is reachable and a test S3 bucket can be created via a small boto3 seed script.

6. **Create the architecture diagram** (in draw.io or Excalidraw, export to `/docs`). It must show: React frontend → HTTPS/JWT → FastAPI → (rule engine, ML scorer, NetworkX graph) → Postgres, and FastAPI → boto3 → LocalStack. Mark the **trust boundaries** (browser↔API, API↔DB, API↔cloud) and label uploaded files as "untrusted input".

7. **Finalize the database schema** (document in `/docs/schema.md`). Define all six tables from the planning doc §10: `users`, `scans`, `findings`, `compliance_map`, `audit_log` — with field names, types, primary keys, foreign keys, and enums. Draw the ER relationships.

8. **Write the threat-model sketch** (`/docs/threat-model.md`). List the trust boundaries and the top risks: untrusted file uploads (YAML RCE/DoS), broken access control (IDOR), JWT abuse, credential theft, CORS/SSRF. Reference the §16 acceptance checklist in the planning doc.

9. **Write the project README.** Cover: what the project is, the tech stack, prerequisites, and exact steps to run `docker compose up` and reach the app locally.

### Deliverables
- Live GitHub repo with branch protection + Dependabot + secret scanning on.
- `docker-compose.yml` bringing up FastAPI + Postgres + LocalStack successfully.
- Architecture diagram, finalized schema doc, threat-model doc in `/docs`.
- README with working setup instructions.

### Definition of Done
- [ ] Any team member can clone the repo and run the full stack locally with one command.
- [ ] `/health` works; Postgres connects; LocalStack creates a test bucket.
- [ ] Diagram, schema, threat model, README all merged to `main`.

---

## Phase 1 — Core Rule-Based Detection Engine

**Goal:** A standalone Python module that takes a parsed cloud config and returns a list of findings, each mapped to a CIS control. This is the heart of the product.

**Prerequisites:** Phase 0 done.

### Steps

1. **Design the declarative rule format** (YAML, stored in `/rules`). Each rule file specifies: `rule_id`, `name`, `severity`, `compliance` (CIS + NIST IDs), a `condition` block (resource type + path/operator checks), and `remediation` text. Use the example in planning doc §11 as the template.

2. **Build a secure config parser.** Accept JSON and YAML input.
   - Parse YAML with **`yaml.safe_load` only** — never `yaml.load` (prevents arbitrary-object/RCE attacks).
   - Enforce **limits before parsing**: max file size (~2 MB), max nesting depth, and a parse timeout — to stop YAML bombs / billion-laughs / deep-JSON DoS.
   - Reject anything that isn't valid JSON/YAML with a clean error.

3. **Build the rule-evaluation engine.** Write a function that:
   - Loads all rule YAML files from `/rules`.
   - Takes a parsed config (a dict/list of resources).
   - For each resource, evaluates every applicable rule's `condition` against the resource's fields (path lookups + operators like `equals`, `contains`).
   - Emits a finding object for each match: `resource_id`, `resource_type`, `severity`, `rule_id`.

4. **Author the starter rule set** (5–8 rules to begin). Examples:
   - S3 bucket public read (`Effect: Allow` + `Principal: *`).
   - Security group ingress open to `0.0.0.0/0`.
   - IAM policy with wildcard action (`Action: *`) or wildcard principal.
   - S3 bucket without encryption.
   - Each mapped to its real CIS control ID.

5. **Create test fixtures.** Build a set of **known-good** configs (should produce zero findings) and **known-bad** configs (should trigger specific rules). Store under `/backend/tests/fixtures`.

6. **Write unit tests** (pytest) that assert: good configs → no findings; each bad config → the exact expected finding(s). This is your regression safety net for every later phase.

### Deliverables
- `/rules` with the declarative rule files.
- An importable rule-engine module (parser + evaluator).
- Good/bad test fixtures + passing pytest suite.

### Definition of Done
- [ ] Engine parses JSON and YAML securely (`safe_load` + limits).
- [ ] Each starter rule correctly flags its bad fixture and ignores good ones.
- [ ] `pytest` passes on the full fixture set.

---

## Phase 2 — Backend API & Database

**Goal:** Expose the rule engine over HTTP and persist scans/findings to the database.

**Prerequisites:** Phase 1 done.

### Steps

1. **Define data models with SQLModel** for all tables (§10): `users`, `scans`, `findings`, `compliance_map`, `audit_log`. Use enums for `role`, `scan_type`, `status`, `severity`.

2. **Set up database migrations with Alembic.** Generate the initial migration that creates all tables. Use **parameterized queries only** (SQLModel/SQLAlchemy handle this) — never build SQL by string concatenation.

3. **Build the upload endpoint** (`POST /scans/upload`):
   - Validate `Content-Type` and file extension allowlist (`.json/.yaml/.yml`).
   - Enforce the size/depth limits from Phase 1.
   - Parse → run the rule engine → create a `scans` row and `findings` rows → return the scan result.
   - Wrap all request/response bodies in **Pydantic models** for strict validation.

4. **Build the results endpoints:**
   - `GET /scans` — list the caller's scans.
   - `GET /scans/{scan_id}` — one scan with its findings.
   - `GET /scans/{scan_id}/findings` — findings detail.
   - **Every query must be scoped to the authenticated user** (foundation for IDOR prevention in Phase 8 — design for it now even if auth lands later).

5. **Seed `compliance_map`** with the CIS/NIST mappings + remediation text for your starter rules.

6. **Enable Swagger/OpenAPI docs** (FastAPI provides this automatically at `/docs`). **Publish this contract to the team** — the frontend and ML work build against it.

7. **Write API tests** with httpx/pytest covering upload → store → retrieve.

### Deliverables
- FastAPI app with upload + results endpoints.
- Alembic migrations + connected Postgres (Neon or local).
- Swagger docs published; API tests passing.

### Definition of Done
- [ ] Uploading a bad config via the API creates a scan + findings in the DB.
- [ ] Results endpoints return stored findings.
- [ ] All bodies validated by Pydantic; queries parameterized and user-scoped.

---

## Phase 3 — Frontend Dashboard v1

**Goal:** A working UI: upload a config, see findings rendered with severity and basic charts.

**Prerequisites:** Phase 2 API contract published (frontend can mock until live).

### Steps

1. **Scaffold the React app** with Tailwind CSS. Set up routing (e.g., Login placeholder, Dashboard, Scan Detail) and a base layout (nav + content).

2. **Build an API client layer** that talks to the FastAPI endpoints (base URL from env). While the API is being finished, use **mock JSON** matching the Swagger schema so frontend isn't blocked.

3. **Build the Upload UI** — file picker, client-side validation (type/size), submit to `/scans/upload`, handle success/error states.

4. **Build the Findings List** — a table/cards view showing each finding's resource, type, rule, and a **severity badge** (color-coded Low/Medium/High/Critical).

5. **Add charts with Recharts** — findings by severity (bar/pie) and by category/resource type. Wire to the scan results.

6. **Connect end-to-end** once Phase 2 is live: real upload → real findings on the dashboard.

### Deliverables
- React + Tailwind dashboard with upload, findings list, severity badges, charts.
- Working end-to-end flow against the real API.

### Definition of Done
- [ ] Uploading a file in the UI shows real findings from the backend.
- [ ] Severity badges and charts render correctly.
- [ ] No tokens in `localStorage` (prepare for httpOnly cookie auth in Phase 8).

---

## Phase 4 — Live Cloud Integration

**Goal:** Scan an emulated live AWS account (LocalStack), not just uploaded files — making the "cloud computing" claim real.

**Prerequisites:** Phase 1 engine + Phase 2 API done; LocalStack running.

### Steps

1. **Seed LocalStack with realistic resources** via a setup script: create S3 buckets (some public, some private), security groups (some open), IAM policies (some over-privileged). This is your live test target.

2. **Build read-only boto3 collectors** that connect to LocalStack and pull current state:
   - S3 bucket ACLs and policies.
   - EC2/VPC security groups.
   - IAM policies and roles.
   - Use **read-only operations only** (Get/Describe/List). For real AWS later, this maps to the `SecurityAudit` managed policy via STS AssumeRole — **never store long-lived keys**.

3. **Normalize collected state** into the same resource shape the rule engine already consumes, so the *exact same rules* run against live data and uploaded files.

4. **Add the live-scan endpoint** (`POST /scans/live`): trigger collection → normalize → run rule engine → persist as a `scan` with `scan_type = Live`.

5. **Prevent SSRF.** If the LocalStack endpoint URL is configurable, **allowlist it**; block internal/link-local/RFC1918 ranges except the intended host.

6. **Add a "Scan my cloud account" button** in the frontend that calls the live-scan endpoint and shows results alongside upload scans.

### Deliverables
- LocalStack seed script + read-only boto3 collectors.
- Live-scan endpoint reusing the rule engine.
- Frontend live-scan trigger.

### Definition of Done
- [ ] A live scan against seeded LocalStack returns findings matching the planted misconfigurations.
- [ ] Live and static scans share the same rule engine and finding schema.
- [ ] Only read-only cloud operations are used; endpoint is allowlisted.

---

## Phase 5 — AI/ML Risk Scoring & Anomaly Detection

**Goal:** A genuine, *defensible* ML layer. **Two distinct jobs** (see planning doc §8) — do not conflate them, and do not make the circular "ML relearns the rules" mistake.

**Prerequisites:** Phases 1–4 done; Terraform CLI installed.

### Steps

1. **Build the Golden Baseline dataset (the "normal" 90%).**
   - Take production-grade `terraform-aws-modules` (VPC, S3, IAM, Security Groups).
   - Run **`terraform plan -out=tfplan` then `terraform show -json tfplan`** to get **fully resolved** resource state (NOT raw HCL — raw HCL leaves variables unresolved and breaks realism).
   - Parse the JSON into per-resource records.

2. **Generate the mutated anomalies (the "bad" 10%).** Write `mutate_iac.py` (in `/ml`) that programmatically injects misconfigurations into the resolved baseline: swap CIDRs to `0.0.0.0/0`, flip bucket privacy flags, insert wildcard IAM. **These labeled anomalies are for the supervised XGBoost model only.**

3. **Build the feature matrix.** Convert each resource into a numeric row, splitting features by purpose:
   - **Rule-correlated features** (for XGBoost): `open_ports_count`, `has_wildcard_principal`, `is_publicly_accessible`.
   - **Behavioral/structural features** (for Isolation Forest): `attached_policies_count`, `tag_entropy`, `relationship_degree` (from the NetworkX graph), `policy_statement_count`. These are **not direct rule triggers** — this is what makes anomaly detection defensible.
   - Output a CSV with features (X) and a binary label (y: 0=Normal, 1=Anomaly).

4. **Train XGBoost (Job A — risk *prioritization*).** Train on labeled data with `scale_pos_weight` to handle the 90/10 imbalance. Output: a calibrated **0–100 risk score** per resource plus **feature-importance** explanations. This ranks and explains findings even when rules already fired.

5. **Train Isolation Forest (Job B — fleet anomaly/drift).** Drop the label; train only on **behavioral features**. It flags resources that are statistically unusual versus the fleet baseline **even when no rule fires** — the honest version of "catches what rules miss."

6. **Evaluate honestly** (produce a benchmark report):
   - XGBoost: precision/recall/F1 + feature importance.
   - Isolation Forest: complementarity analysis — how many non-rule-violating resources it flags that a human agrees are anomalous (hand-label a small validation set).

7. **Integrate into the API.** Persist trained models (`joblib`). On each scan, compute `risk_score` (XGBoost) and `is_anomaly` (Isolation Forest) and store them on each `findings` row. Train models in **Google Colab (free)**; load them in the backend.

### Deliverables
- `/ml` with dataset scripts, training notebook, saved models.
- Models integrated into the scan pipeline (risk_score + is_anomaly populated).
- Benchmark report (the defensible evidence for your viva).

### Definition of Done
- [ ] Dataset built from resolved Terraform state, not raw HCL.
- [ ] XGBoost outputs a 0–100 risk score with feature importance.
- [ ] Isolation Forest flags anomalies based on non-rule features.
- [ ] Benchmark report documents the value-add without circular claims.

---

## Phase 6 — Attack-Path Visualization

**Goal:** Show how individual findings chain into exploitable paths from public exposure to sensitive data — the most distinctive CSPM feature.

**Prerequisites:** Phase 4 (resource data) + Phase 2 (API) done.

### Steps

1. **Model resources as a graph with NetworkX.** Nodes = resources (internet gateway, EC2, IAM role, S3 bucket). Edges = relationships (network ingress, IAM access, attachment).

2. **Build relationship extraction.** From collected/parsed state, derive edges: which security group allows public ingress to which instance; which instance assumes which role; which role can access which data store.

3. **Compute attack paths.** Identify paths from **public entry points** (e.g., `0.0.0.0/0` ingress) to **sensitive resources** (e.g., data stores). Use NetworkX path algorithms; annotate each node with its severity/risk score.

4. **Output the node-link JSON** in the format the frontend graph expects (planning doc §13): `nodes` (id, label, type, severity_score) + `links` (source, target, relation).

5. **Add a graph endpoint** (`GET /scans/{scan_id}/graph`) returning this JSON.

6. **Render in the frontend with React Force Graph** — an interactive, force-directed canvas. Color nodes by severity; show relations on edges; make nodes clickable to reveal finding detail.

### Deliverables
- NetworkX graph builder + path computation.
- Graph endpoint returning node-link JSON.
- Interactive attack-path view in the dashboard.

### Definition of Done
- [ ] Graph correctly links a public entry point through to a sensitive resource.
- [ ] Frontend renders the interactive graph with severity coloring.
- [ ] Clicking a node shows its associated finding(s).

---

## Phase 7 — Compliance Mapping & Remediation

**Goal:** Turn findings into standards-based, actionable guidance.

**Prerequisites:** Phases 1–2 done; `compliance_map` seeded.

### Steps

1. **Complete the compliance knowledge base.** For every rule, ensure `compliance_map` has the correct CIS control ID, NIST CSF ID, and **self-authored remediation text** (no paid LLM). **Reference CIS control IDs only — do not copy CIS benchmark text** (licensing). NIST CSF is public domain.

2. **Build a compliance-status calculator.** For a given scan, compute per-framework pass/fail: group findings by their mapped controls and report which controls passed vs failed.

3. **Add a compliance endpoint** (`GET /scans/{scan_id}/compliance`) returning per-framework status and the failed controls with remediation.

4. **Build the Compliance tab in the frontend** — show framework (CIS/NIST) pass/fail summary, a list of failed controls, and the remediation text for each finding.

### Deliverables
- Fully populated `compliance_map`.
- Compliance-status endpoint.
- Compliance tab in the dashboard with remediation guidance.

### Definition of Done
- [ ] Every finding maps to a CIS + NIST control with remediation text.
- [ ] Compliance tab shows accurate per-framework pass/fail.
- [ ] No CIS benchmark text is redistributed (IDs only).

---

## Phase 8 — Authentication & Secure System Design

**Goal:** Make the platform itself secure — a hardened, multi-user system. This is the "iron-clad" core (planning doc §9).

**Prerequisites:** Phases 2–3 done.

### Steps

1. **Implement signup/login.** Hash passwords with **Argon2id via `pwdlib`** (NOT passlib — it's unmaintained). Never store plaintext.

2. **Implement JWT sessions.**
   - **Pin the algorithm** and reject `alg: none` and HS/RS confusion.
   - Short access-token expiry (~15 min) + a rotating refresh token.
   - JWT secret only in env.
   - Store tokens in **httpOnly + Secure + SameSite=Strict cookies**, NOT `localStorage` (defeats XSS token theft).
   - Add **CSRF protection** (double-submit token) because cookies are used.

3. **Enforce RBAC server-side.** Admin vs Viewer, checked via FastAPI dependencies on **every** protected endpoint — never trust the frontend for authorization.

4. **Prevent IDOR.** Confirm every scan/finding query filters by the authenticated `user_id`/`org_id`. UUIDs are not authorization.

5. **Harden cloud credentials.** No long-lived AWS keys stored. Real AWS → STS AssumeRole + external ID + read-only `SecurityAudit`. LocalStack → dummy creds in env. Never log credentials.

6. **Lock down transport & CORS.** HTTPS enforced; CORS restricted to the exact frontend origin (no `*` with credentials).

7. **Add anti-abuse.** Rate-limit login and upload (`slowapi`); return generic error messages to prevent **user enumeration**.

8. **Add audit logging.** Write to the `audit_log` table on auth events (login success/fail) and admin actions (role changes).

### Deliverables
- Secure signup/login, JWT, RBAC, audit logging.
- All items in the §16 security checklist satisfied.

### Definition of Done
- [ ] Passwords Argon2id-hashed; JWT alg pinned; tokens in httpOnly cookies; CSRF present.
- [ ] RBAC enforced server-side; all queries user-scoped (no IDOR).
- [ ] No stored cloud keys; CORS locked; rate limiting + audit log active.

---

## Phase 9 — DevOps: Containerization, CI/CD & Self-Scanning

**Goal:** A deployable, continuously scanning, continuously self-audited platform.

**Prerequisites:** Phases 1–8 functionally complete.

### Steps

1. **Dockerize both apps.** Production Dockerfiles for the FastAPI backend and the React frontend (multi-stage build for a small frontend image).

2. **Build the CI pipeline (GitHub Actions)** that runs on every PR:
   - Backend tests (pytest) + frontend build.
   - **Security gates:** Bandit (Python SAST), Semgrep, pip-audit, npm audit, CodeQL, Trivy (image CVEs), gitleaks (secret scan).
   - Fail the build if security gates fail — this demonstrates a secure SDLC and doubles as a project feature.

3. **Build the CD pipeline.** On merge to `main`, build and deploy (frontend to Vercel, backend container to the Oracle VM / chosen host).

4. **Add scheduled scans.** A GitHub Actions **cron** job that periodically triggers a live scan against the hosted LocalStack — this is the "**continuous**" in CSPM.

### Deliverables
- Production Dockerfiles + working `docker compose` for the full stack.
- CI/CD pipeline with passing security gates.
- Scheduled scan job.

### Definition of Done
- [ ] One command builds and runs the whole stack in containers.
- [ ] CI is green across all security tools.
- [ ] Scheduled scan runs automatically against the hosted target.

---

## Phase 10 — Deployment

**Goal:** A publicly accessible, working version for demos and evaluation.

**Prerequisites:** Phase 9 done.

### Steps

1. **Deploy the frontend to Vercel** (auto HTTPS, global CDN). Set the API base URL via env.

2. **Deploy the backend + LocalStack to the Oracle Cloud Always Free VM** using Docker Compose. Put a reverse proxy (Caddy/nginx) in front with Let's Encrypt TLS.
   - *Fallback:* if no Oracle VM, deploy backend to Fly.io/Koyeb (static-upload-only) and document that live scan is demoed locally.

3. **Connect the production database** (Neon free tier or a Postgres container on the VM). Run migrations.

4. **Final production hardening.** Confirm HTTPS end-to-end, CORS locked to the Vercel origin, all secrets in env/host secret store, and the §16 checklist passes in production.

### Deliverables
- Live frontend URL + live backend API + production DB.

### Definition of Done
- [ ] The public URL serves the working app over HTTPS.
- [ ] Upload and (where hosted) live scan both work in production.
- [ ] Production passes the security acceptance checklist.

---

## Phase 11 — Testing, Documentation & Final Report

**Goal:** Polish and prepare for submission and defense.

**Prerequisites:** Phase 10 done.

### Steps

1. **End-to-end testing.** Run full user journeys (signup → upload → live scan → view graph → compliance) and fix bugs. Add integration tests covering critical flows.

2. **Security verification.** Walk the §16 acceptance checklist one final time and record evidence (screenshots, CI logs) for each item.

3. **Write the user guide** — how to set up, run, and use the platform.

4. **Write the final project report** — problem, SDG mapping, architecture, each phase, the ML methodology and benchmark results, the security design, results, and future scope.

5. **Prepare the demo.** A demo script + presentation deck walking evaluators through the strongest features (live scan, attack-path graph, ML risk scoring, compliance, self-scanning CI).

### Deliverables
- Passing test suite, user guide, final report, demo script + deck.

### Definition of Done
- [ ] All critical flows tested and green.
- [ ] Security checklist fully evidenced.
- [ ] Report + user guide + demo deck complete and submission-ready.

---

## Global Working Rules (Apply to Every Phase)

- **Branch + PR + review:** no direct commits to `main`; every change reviewed.
- **Tests travel with code:** add/adjust tests in the same PR as the feature.
- **Security is not a phase-8 afterthought:** apply `safe_load`, user-scoped queries, and no-secrets-in-code from the very first line.
- **The API contract (Swagger) is the source of truth** for frontend ↔ backend integration — keep it current.
- **Same rule engine everywhere:** uploaded files and live scans must flow through identical detection logic.
- **Everything stays free:** if a step seems to need a paid service, stop and find the free alternative before proceeding.
- **A phase isn't done until its Definition-of-Done checklist fully passes.**
