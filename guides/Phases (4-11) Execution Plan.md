# Remaining Phases (4–11) — Team Execution Plan

This plan takes the project from **Phase 3 complete** to **final delivery** by
running the eight remaining phases as **four parallel waves** instead of eight
sequential phases — roughly halving the calendar time without raising error
risk. Testing & documentation (Phase 11) run **continuously** inside every wave.

**Team:** 4 members.

---

## Guiding principles (what kept Phase 3 clean — we keep all of it)

1. **Contract-first + mocks.** Before a wave starts, we agree the new API shapes
   (request/response JSON). Frontend builds against mocks; backend builds the
   real thing; we flip one flag to integrate. Nobody is ever blocked.
2. **One owner per folder/file.** No two people edit the same file. Shared types
   are written once and imported read-only.
3. **Small PRs + CI green before merge + a rotating reviewer.**
4. **Integrate as you go.** Each wave ends with a real end-to-end check (like the
   Phase 3 real-backend run), never a big-bang integration at the end.
5. **Equal ownership.** Every member owns a headline deliverable each wave;
   review/test duties rotate and are shared, never one person's job.

---

## The four waves at a glance

| Wave | Phases (run in parallel) | Theme | Duration |
| --- | --- | --- | --- |
| **A** | Phase 4 (Live Cloud) ‖ Phase 5 (ML) | "Real data + intelligence" | ~2 weeks |
| **B** | Phase 6 (Attack-Path) ‖ Phase 7 (Compliance) | "Insight & standards" | ~2 weeks |
| **C** | Phase 8 (Auth & Secure System) | "Hardening" | ~1.5 weeks |
| **D** | Phase 9 (DevOps/CI-CD) + Phase 10 (Deploy) | "Ship it" | ~1.5 weeks |
| **cont.** | Phase 11 (Testing / Docs / Report) | continuous → final polish | throughout + ~1 week |

**Indicative timeline (~8 weeks):**

| Week | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Wave | A | A | B | B | C | D | D | Final |

---

## Workload balance (every member leads 4 marquee features)

| Member | Wave A | Wave B | Wave C | Wave D |
| --- | --- | --- | --- | --- |
| **M1** | Cloud Connector (boto3) | Compliance Engine (backend) | Auth Core (JWT/Argon2id) | Containerization + Self-Scan |
| **M2** | Live-Scan API + UI | Compliance Tab (frontend) | Auth Frontend (login/session) | Frontend Deployment |
| **M3** | ML Models (XGBoost + IF) | Attack-Path Graph (backend) | RBAC + Data Scoping + Audit | Backend + DB Deployment |
| **M4** | Risk Intelligence in Product | Attack-Path Visualization | Security Hardening + ASVS | CI/CD Security Pipeline |

Each cell is a **lead/owner** role. Everyone leads exactly one backend-heavy,
one frontend-heavy, one ML/data, and one security/ops marquee across the project.
Every member also reviews and tests **one peer's** work each wave (rotating).

---

# Wave A — Phase 4 (Live Cloud) ‖ Phase 5 (ML)

**Goal:** scan a *real* (emulated) cloud account, and add a genuine ML risk layer
on top of every finding.

### Member assignments

**M1 — Cloud Connector (Phase 4 backend).**
- Builds a read-only `boto3` collector against LocalStack: pulls S3 ACLs/policies,
  security groups, IAM policies; **normalizes them into the exact resource schema
  the Phase 1 rule engine already consumes** (`{resource_id, resource_type, …}`).
- SSRF defense: endpoint allowlisting; read-only credentials.
- **Delivers →** a `collect_cloud_resources()` module producing normalized
  resource JSON. *This JSON is the input to M2's endpoint and flows straight into
  the existing rule engine.*

**M2 — Live-Scan API + UI (Phase 4 API + frontend).**
- New `POST /scans/cloud` endpoint that calls M1's collector → rule engine →
  stores a scan (reusing the Phase 2 scan pipeline).
- Frontend "**Scan Cloud Account**" flow next to Upload (reuses Phase 3 patterns);
  live scans appear in the same Scans list/detail.
- **Input ←** M1's collector. **Delivers →** live scans in the shared scan store
  (which M4's risk layer then scores).

**M3 — ML Models (Phase 5 core).**
- Generates the synthetic dataset (mutation of resolved Terraform state), trains
  **Isolation Forest** (anomaly/drift) + **XGBoost** (risk prioritization),
  produces a composite **0–100 risk score** per resource.
- **Delivers →** a serialized model + a `score_findings(findings) -> {risk_score,
  is_anomaly}` module, plus a benchmark report (precision/recall, feature
  importance). *This scorer is the input to M4's integration.*

**M4 — Risk Intelligence in the Product (Phase 5 integration + frontend).**
- Wires M3's scorer into the scan pipeline so `risk_score`/`is_anomaly` (already
  stubbed in the schema + UI since Phase 2/3) get populated.
- Surfaces it: **risk-score column + sort**, **anomaly badge** in `FindingsTable`,
  and a **"top risks" panel** on the dashboard.
- **Input ←** M3's model, and scores both uploaded **and** M2's live scans.

### Wave A handoff flow
```
M1 collector ──normalized resources──▶ M2 /scans/cloud ──▶ shared scan store
                                   └──▶ rule engine (existing)
M3 model ──score_findings()──▶ M4 pipeline+UI ──scores──▶ all scans (upload + live)
```

### Wave A "done"
Live cloud scan works end-to-end; every finding shows a real risk score + anomaly
flag on both scan types; ML benchmark report written.

---

# Wave B — Phase 6 (Attack-Path) ‖ Phase 7 (Compliance)

**Goal:** show how findings chain into attack paths, and map everything to
CIS/NIST with remediation guidance. Full detail: `guides/wave B/Wave_B_Detailed_Execution_Plan.md`.

> **Prerequisite, not automatic from Wave A finishing:** Wave A's cloud connector
> only ever collects S3 / IAM / Security Groups — no EC2 instances, no IAM role
> attachments. Attack-Path's `instance → role → permission → data store` chain
> needs relationship data that doesn't exist yet even once Wave A is fully merged,
> so Wave B opens with a Day 0–2 task (M3) extending the collector before any
> graph work starts. If it slips, Phase 6 descopes to whatever relationships are
> actually collectable rather than shipping a graph UI with nothing real to render.

### Member assignments

**M3 — Attack-Path Graph (Phase 6 backend).**
- Days 0–2: extends the existing collector (`backend/src/cloud/`) with EC2
  instances and IAM role/policy attachments — additive only, no Wave A files
  are modified, just new functions added.
- Models resources/relationships as a graph in **NetworkX** (instance → role →
  permission → data store); computes **bounded** paths (cutoff + max-paths, to
  avoid `all_simple_paths` blowing up) from public exposure to sensitive assets.
- **Delivers →** `GET /scans/{id}/attack-paths` (its own router, doesn't touch
  the existing `routes.py`) returning node/link JSON. *This JSON is the input
  to M4's visualization.*

**M4 — Attack-Path Visualization (Phase 6 frontend).**
- Interactive graph view with **React Force Graph**: nodes colored by severity
  (reusing the Phase 3 severity palette), highlighted exploit paths, click-through
  to the finding.
- **Input ←** M3's node/link JSON.

**M1 — Compliance Engine (Phase 7 backend).**
- Findings already carry their controls via the existing `Finding.compliance`
  FK relationship (`cis_aws`/`nist_csf` IDs on the rule, `seed_compliance_map`
  migration) — no new mapping logic, just aggregation + remediation content.
  Status is **rule-level** ("no violation found in this scan"), not a claim
  that every resource was individually verified.
- **Delivers →** `GET /scans/{id}/compliance` (its own router; framework status
  + remediation). *Input to M2's tab.*

**M2 — Compliance Tab (Phase 7 frontend).**
- New **Compliance** tab: per-framework pass/fail summary, control-by-control
  status, and remediation text per finding.
- Also builds the shared tab nav on `ScanDetailPage.tsx` (`Findings / Attack
  Paths / Compliance`) — M4 rebases onto it afterward, per the merge order.
- **Input ←** M1's compliance API.

### Wave B handoff flow
```
M3 graph builder ──node/link JSON──▶ M4 force-graph view
M1 compliance engine ──framework status JSON──▶ M2 compliance tab
```

### Wave B "done"
Attack-path view renders real paths for a scan; Compliance tab shows CIS/NIST
pass/fail + fixes for the same scan.

---

# Wave C — Phase 8 (Authentication & Secure System Design)

**Goal:** turn the placeholder identity into a real, hardened multi-user platform
(target: OWASP ASVS L1). This phase touches every endpoint, so we split it into
four independent, clearly-bounded security domains.

### Member assignments

**M1 — Auth Core.**
- Signup/login, **Argon2id** hashing, **JWT in httpOnly cookies** (pinned alg,
  short expiry + refresh). Replaces the `get_current_user` placeholder with a real
  authenticated dependency.
- **Delivers →** the auth dependency every endpoint now uses. *Input to M2 (UI),
  M3 (RBAC), M4 (hardening).*

**M2 — Auth Frontend.**
- Login/signup screens, session handling, protected routes/redirects. The Axios
  client already sends `withCredentials` (built in Phase 3), so cookies "just
  work."
- **Input ←** M1's auth endpoints.

**M3 — RBAC + Data Scoping + Audit.**
- Server-side role enforcement (Admin/Viewer), hardens per-user data scoping
  (IDOR defense across all scan endpoints), and adds an **audit log** of security
  events.
- **Input ←** M1's authenticated identity; secures the endpoints built in Phases
  2/4/6/7.

**M4 — Security Hardening + Verification.**
- Rate limiting (**slowapi**), **CORS lockdown**, env-based secrets, **STS
  AssumeRole + external ID** (no stored cloud keys), and drives the **OWASP ASVS
  L1 checklist** + security test suite.
- **Input ←** everyone's endpoints; produces the sign-off checklist.

### Wave C handoff flow
```
M1 auth core ──authenticated identity──▶ M2 login UI
                                     ├──▶ M3 RBAC + scoping + audit
                                     └──▶ M4 rate-limit/CORS/STS + ASVS sign-off
```

### Wave C "done"
Real login works; roles enforced server-side; ASVS L1 checklist passes; no stored
cloud keys; audit log populated.

---

# Wave D — Phase 9 (DevOps/CI-CD) + Phase 10 (Deployment)

**Goal:** one-command setup, security-gated CI/CD, and a live public URL.

### Member assignments

**M1 — Containerization + Scheduled Self-Scan.**
- Production Docker images for frontend + backend; a production `docker-compose`;
  a **cron scheduled scan** job against hosted LocalStack.
- **Delivers →** the container images the deploy jobs consume.

**M4 — CI/CD Security Pipeline.**
- GitHub Actions running tests + the **security scanner suite** (Bandit, Semgrep,
  pip-audit, npm audit, CodeQL, Trivy, gitleaks) as merge gates, then deploy.
  (Builds on the Phase 3 CI workflow M4 already owns.)
- **Input ←** M1's images; gates every deploy.

**M2 — Frontend Deployment.**
- Deploy the React app (Vercel), production env config, TLS, build/bundle
  optimization.
- **Input ←** M1's frontend image / build.

**M3 — Backend + DB Deployment.**
- Deploy the backend (Oracle Cloud Always Free), **Neon** production DB,
  migrations in prod, **locked CORS**, wire frontend ↔ backend in production.
- **Input ←** M1's backend image; connects to M2's deployed frontend.

### Wave D handoff flow
```
M1 images ──▶ M4 CI/CD gates ──deploy──▶ M2 frontend (Vercel) ⇄ M3 backend+DB (Oracle+Neon)
```

### Wave D "done"
Live public URL; every merge runs security scans + tests; scheduled scan job
running.

---

# Phase 11 — Testing, Documentation & Final Report (continuous)

Not a final scramble — folded into every wave:

- **Every wave:** each member writes unit/integration tests **and** docs for the
  feature they led (CI keeps them green). Each member also reviews + tests **one**
  peer's wave deliverable.
- **Final week — report split (equal sections):**
  - **M1:** architecture + DevOps/deployment write-up.
  - **M2:** frontend/UX + compliance walkthrough.
  - **M3:** backend + data + ML-integration + attack-path write-up.
  - **M4:** security (threat model, ASVS, CI security gates) + test strategy.
  - **Shared:** demo script + slide deck (each presents their own tracks).

---

## Dependency map (why there are no deadlocks)

- Within a wave, the two parallel phases are **independent** (different folders,
  different data) — e.g., Wave A's cloud connector and ML models never touch the
  same files.
- Handoffs are a **one-way tree** (collector → API; model → integration; graph →
  viz; auth → RBAC/UI), never a cycle — same property that made Phase 3
  deadlock-free.
- The only cross-wave dependency is **Auth (Wave C) should land before public
  Deployment (Wave D)** — already ordered that way.

# GitHub Commit & Merge Order (Phases 4–11)

> **Workflow for every wave**
>
> 1. Assigned member completes their feature on their feature branch.
> 2. Opens a Pull Request.
> 3. PR is reviewed and merged into `main`.
> 4. Remaining members pull the latest `main`.
> 5. Next dependent member completes their work and repeats the process.

---

# Wave A — Phase 4 (Live Cloud) + Phase 5 (ML)

| Step | Action |
|------|--------|
| 1 | **M1** pushes **Cloud Connector** → PR → Merge |
| 2 | **Everyone pulls latest `main`** |
| 3 | **M3** pushes **ML Models** → PR → Merge |
| 4 | **Everyone pulls latest `main`** |
| 5 | **M2** (depends on M1) pushes **Live Scan API + UI** → PR → Merge |
| 6 | **Everyone pulls latest `main`** |
| 7 | **M4** (depends on M3) pushes **Risk Intelligence Integration + UI** → PR → Merge |
| 8 | **Everyone pulls latest `main`** |

**Commit Order**

```
M1 → M3 → M2 → M4
```

---

# Wave B — Phase 6 (Attack Path) + Phase 7 (Compliance)

| Step | Action |
|------|--------|
| 1 | **M1** pushes **Compliance Engine** → PR → Merge |
| 2 | **Everyone pulls latest `main`** |
| 3 | **M3** pushes **Attack Path Graph Backend** → PR → Merge |
| 4 | **Everyone pulls latest `main`** |
| 5 | **M2** (depends on M1) pushes **Compliance Tab** → PR → Merge |
| 6 | **Everyone pulls latest `main`** |
| 7 | **M4** (depends on M3) pushes **Attack Path Visualization** → PR → Merge |
| 8 | **Everyone pulls latest `main`** |

**Commit Order**

```
M1 → M3 → M2 → M4
```

---

# Wave C — Phase 8 (Authentication & Security)

| Step | Action |
|------|--------|
| 1 | **M1** pushes **Authentication Core (JWT + Argon2id)** → PR → Merge |
| 2 | **Everyone pulls latest `main`** |
| 3 | **M2** pushes **Authentication Frontend** → PR → Merge |
| 4 | **Everyone pulls latest `main`** |
| 5 | **M3** pushes **RBAC + Data Scoping + Audit** → PR → Merge |
| 6 | **Everyone pulls latest `main`** |
| 7 | **M4** pushes **Security Hardening + ASVS Verification** → PR → Merge |
| 8 | **Everyone pulls latest `main`** |

**Commit Order**

```
M1 → M2 → M3 → M4
```

---

# Wave D — Phase 9 (CI/CD) + Phase 10 (Deployment)

| Step | Action |
|------|--------|
| 1 | **M1** pushes **Docker Images + Containerization** → PR → Merge |
| 2 | **Everyone pulls latest `main`** |
| 3 | **M2** pushes **Frontend Deployment** → PR → Merge |
| 4 | **Everyone pulls latest `main`** |
| 5 | **M3** pushes **Backend + Database Deployment** → PR → Merge |
| 6 | **Everyone pulls latest `main`** |
| 7 | **M4** pushes **CI/CD Security Pipeline** → PR → Merge |
| 8 | **Everyone pulls latest `main`** |

**Commit Order**

```
M1 → M2 → M3 → M4
```

---

# General Workflow

For every merge:

1. Complete work on your feature branch.
2. Commit and push your branch.
3. Open a Pull Request.
4. After the PR is merged into `main`, **every team member runs:**

```bash
git checkout main
git pull origin main
git checkout <your-feature-branch>
git merge main
```

5. Continue development only after your branch is up to date with `main`.
6. Repeat the process for the next member in the commit order.

## Risk controls (how we avoid the errors we hit in Phase 3)

- **Define contracts + mocks before coding** each new endpoint (live-scan, risk,
  attack-path, compliance, auth) so frontend/backend never block each other.
- **Verify each integration point live** at the end of its wave (repeat the
  real-backend E2E discipline) — don't defer to the end.
- **CI green (tests + security scans) required to merge.**
- **Auth is the one phase not to rush** — it touches every endpoint; give it its
  own careful wave (Wave C) rather than combining it.

---

## Quick summary

- **8 phases → 4 parallel waves + continuous testing** ≈ halves the timeline.
- **Every member leads 4 marquee features** (one backend, one frontend, one
  ML/data, one security/ops) across the project — fully balanced ownership.
- **Clear one-way handoffs** each wave; no deadlocks, no shared-file conflicts.
- **~8 weeks** to final delivery on the indicative timeline.
