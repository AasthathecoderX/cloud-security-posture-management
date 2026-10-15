# Wave D — Phase 9 (DevOps/CI-CD) + Phase 10 (Deployment)

Goal: one-command setup, security-gated CI/CD, and a live public URL. Team: 4
members. Assumes **Wave C is merged to `main`** — verified: `pytest backend -q`
is 108/108 green with zero `xfail` remaining, `docker build` on `backend/Dockerfile`
succeeds with every Wave B/C dependency present, and a live end-to-end run (real
Postgres, real signup, real RBAC denial, real IDOR denial, real audit rows) was
proven against the actual running stack, not just test fixtures.

By the end: production container images, a CI pipeline that actually gates merges
on tests *and* a real security-scanner suite (not just `gitleaks`, which is the
only one that exists today), a deployed frontend (Vercel) and backend+DB (Oracle
Cloud + Neon) talking to each other over locked-down CORS, and a scheduled
self-scan job — all behind one real public URL.

> **This wave is a chain, not a tree.** Unlike Wave A/B's two independent
> branches, Wave D's own handoff diagram in the master plan is linear:
> `M1 images → M4 CI/CD gates → deploy → M2 frontend ⇄ M3 backend+DB`. M2 and M3
> are the only two members who run in parallel, and even they aren't fully
> independent — M3's CORS lockdown needs M2's deployed URL, and M2's
> `VITE_API_BASE_URL` needs M3's. That exchange is Contract 3 below, not an
> afterthought.

---

## What's already in place (don't rebuild this)

- **`backend/Dockerfile`** exists, builds cleanly, and was just verified against
  every current dependency (`networkx`, `pwdlib[argon2]`, `pyjwt`, `argon2-cffi`,
  `slowapi`). It has no production hardening yet (see Status check below) — the
  image itself is real, just not hardened.
- **Dependabot is already configured** (`.github/dependabot.yml`) for `pip`,
  `docker` (backend), `docker-compose` (infra), and `github-actions` ecosystems,
  weekly. M4 doesn't need to set this up — it already produces the
  `docker_compose in /infra - Update #...` style PRs you've seen land on `main`.
- **`gitleaks.yml`** already runs secret scanning on every PR and push — this is
  1 of the ~6 scanners Phase 9 calls for, already done.
- **CORS is already env-driven and fails closed** — `main.py::validate_cors_origins()`
  refuses to start if `CORS_ALLOW_ORIGINS` contains `*` alongside credentials.
  M3's "lock CORS" deliverable is setting the right *value* in production, not
  building the mechanism.
- **"No stored cloud keys" is largely already true.** Wave C's `AWS_AUTH_MODE`
  flag-gate (`cloud/localstack.py`) defaults to `static` — LocalStack's dummy
  `test`/`test` credentials, which aren't secrets at all (LocalStack doesn't
  validate them). Since this project's live-scan target stays **hosted
  LocalStack**, not real AWS (see the decision below), M3 does not need to wire
  up real STS AssumeRole for this deployment — the flag-gated path exists,
  stays dormant, and is already documented as such.
- **The frontend already code-splits per route** (`lazy()` imports since Wave A) —
  M2's "bundle optimization" starting point is already reasonable; verify, don't
  rebuild.

## Status check — what's actually missing (verified by reading the repo, not assumed)

| Gap | Owner | Why it matters |
| --- | --- | --- |
| No frontend Dockerfile exists at all | M1 *(see decision below — may not be needed)* | The master plan says "production images for frontend + backend," but see the Vercel decision — this may be dead work |
| `backend/Dockerfile` runs entirely as root — no `USER` directive | M1 | Confirmed via the build log (`pip` warns about running as root). A production image should drop privileges. |
| No production `docker-compose` variant exists — only the dev one (local `postgres` + `localstack` + `backend`, dev `.env`) | M1 | Production points at Neon (managed Postgres), not a local `postgres` container, and needs production secrets, not `.env.example` placeholders |
| No scheduled-scan workflow exists | M1 | The "Scheduled" runs you've seen in Actions are Dependabot's own built-in check, not a project-authored cron job — nothing like this exists yet |
| Only `gitleaks` runs in CI — no Bandit, Semgrep, pip-audit, npm audit, CodeQL, or Trivy | M4 | Phase 9's whole point is a security-gated pipeline; 5 of 6 scanners are missing |
| No branch protection enforcing any check as *required* | M4 | A scanner workflow nobody's required to pass is noise, not a gate — this is a GitHub repo-settings change, not just a workflow file |
| No deployment config anywhere (no `vercel.json`, no Oracle/Neon wiring, no CI deploy step) | M2, M3 | Confirmed — nothing in the repo targets a real host yet |

---

## What has to be decided before anyone writes code

Three decisions, same spirit as every prior wave's "decide this before Day 3" list:

1. **Does the frontend actually need a Docker image?** The master plan assigns M1
   "production Docker images for frontend + backend," but Major Project
   Planning's own deployment strategy names **Vercel** for the frontend — and
   Vercel builds directly from the git repo (`npm run build`), consuming no
   Dockerfile at all for a standard static/SPA deployment. Building one anyway is
   either dead work or implies a different frontend host than the plan already
   named. **Default: skip the frontend Dockerfile.** M1 spends that time
   hardening the backend image instead (non-root user, see Status check). If the
   team wants a container-hosted frontend instead of Vercel, that's a real scope
   change to flag now, not discover at deploy time.
2. **Registry-push or build-on-VM?** Two ways to get M1's backend image onto the
   Oracle VM: (a) CI builds and pushes to a registry (e.g. GHCR), the VM pulls a
   tag; (b) the VM does `git pull && docker compose up --build -d`, same as local
   dev, just on a server. **Default: (b), build-on-VM.** It's what this project
   has done since Phase 0, needs no registry auth wiring, and Trivy can still scan
   the image CI builds for the PR gate — it just doesn't need to go anywhere
   after. Revisit only if deploy latency on the VM becomes a real problem.
3. **How does the scheduled self-scan authenticate?** `/scans/cloud` is now
   Admin-gated (Wave C) and CSRF-protected — a cron job can't interactively log
   in. **Decide now:** the scheduled workflow logs in as a dedicated service
   account (its own `ADMIN_EMAIL`-matching address, credentials stored as a GitHub
   Actions secret, never the human admin's own login) via the same
   `POST /auth/login` + CSRF-bootstrap flow a browser uses, captures the cookies,
   then calls `/scans/cloud`. This is **M1's job to build**, not a new auth
   mechanism for M1/M3 to invent — reuse exactly what exists.

---

## The two rules that prevent conflicts and deadlocks

**1. No conflicts — one owner per folder/file, with one named, sequenced exception.**
`infra/docker-compose.prod.yml` is touched by both M1 (creates the production
container structure) and M3 (fills in the real Neon connection string env var
name and the production CORS origin once M2's URL exists) — same pattern Wave
C used for RBAC: sequenced, not simultaneous. See File-ownership map.

**2. No deadlocks — contracts before implementation.** M1 publishes the image
build process and the backend's expected production env var names before M3
needs them. M4 publishes which checks will be required (and their names) before
M2/M3 wire up anything that depends on "CI passed." M2 and M3 publish their
deployed URLs to each other the moment each is live — neither waits for a
polished deploy, just a reachable one.

> Dependency shape is a chain: **M1 → M4 → (M2 ‖ M3, with a CORS/URL handshake
> between them)**. Nobody is positioned the way Wave A/B's two fully independent
> branches were — budget for that; M2 and M3 genuinely cannot finish in
> isolation from each other the way Wave B's Compliance and Attack-Path branches
> could.

---

## File-ownership map

| Owner | Folder / files (exclusive) |
| --- | --- |
| **Member 1 — Containerization + Self-Scan** | `backend/Dockerfile` (hardening edits), `infra/docker-compose.prod.yml` (creates), `.github/workflows/scheduled-scan.yml` |
| **Member 4 — CI/CD Security Pipeline** | `.github/workflows/security-scan.yml` (new), branch-protection configuration (GitHub repo settings, not a file) |
| **Member 2 — Frontend Deployment** | `frontend/vercel.json` (if needed), Vercel dashboard env config, `docs/frontend-deployment.md` |
| **Member 3 — Backend + DB Deployment** | `infra/docker-compose.prod.yml` (extends, after M1 — see below), `.github/workflows/deploy-backend.yml`, `docs/backend-deployment.md` |

### The one shared file, and how it stays conflict-free

`infra/docker-compose.prod.yml`: **M1 creates it** (production image references,
no local `postgres`/`localstack` dev services, reads secrets from the production
environment instead of a committed `.env`) as part of the Day 0–2 scaffolding.
**M3 extends it** once Neon's connection string and M2's deployed frontend URL
(for `CORS_ALLOW_ORIGINS`) actually exist — which is necessarily later, since
those values don't exist until M2 has deployed something. Same sequencing fix
Wave C used for RBAC's three router edits: one owner creates the file, a second,
later owner fills in values that couldn't have existed yet, never two people
editing it in the same window.

---

## Order of work

### Day 0–2 — Decisions + scaffolding

**Whole team:** settle the three decisions above before anything else.

**M1**
- Harden `backend/Dockerfile`: add a non-root `USER`, confirm image size is
  reasonable (no multi-stage build needed — the current image installs from
  wheels only, no compiler toolchain required, confirmed by the plain `pip
  install` build log with no `gcc`/`make` steps).
- Scaffold `infra/docker-compose.prod.yml`: `backend` (+ `localstack`, since the
  live-scan target stays hosted LocalStack) pointed at production env vars; no
  local `postgres` service.
- Draft the scheduled-scan workflow's auth flow (decision #3) as a short script,
  testable against the local dev stack before it ever touches production.

**M4**
- Add Bandit + pip-audit (Python), npm audit (frontend), CodeQL (both languages),
  and Trivy (the image M1's Dockerfile now builds) as separate CI jobs.
- Decide which checks become *required* in branch protection — recommend: all
  existing Phase 1–3 test workflows plus Bandit/pip-audit/npm-audit/Trivy at
  minimum; CodeQL and Semgrep can start as advisory (non-blocking) since they're
  the two most prone to noisy first-run false positives, and flip to required
  once a baseline pass is clean.

**M2**
- Create a Vercel project from the repo; confirm a build succeeds against
  `VITE_USE_MOCKS=false` with a placeholder `VITE_API_BASE_URL` (swapped for
  real once M3 deploys).

**M3**
- Provision the Neon database; run `alembic upgrade head` against it once, by
  hand, to confirm the migration chain (including the Wave C auth tables) applies
  cleanly to a fresh managed Postgres instance, not just SQLite/local Postgres.
- Provision the Oracle Cloud Always Free VM; confirm Docker + Docker Compose are
  installed there.

### Day 3–6 — Parallel implementation

**M1** — finish the hardened image, the scheduled-scan workflow (using the
decided auth flow), and `docker-compose.prod.yml`'s structure (values TBD, filled
by M3).

**M4** — finish the full scanner suite as CI jobs; get a first clean (or
triaged) run on `main`.

**M2** — real Vercel deployment live at a real (if placeholder-backend) URL;
production build settings finalized.

**M3** — SSH-deploy workflow to the Oracle VM (`git pull && docker compose -f
docker-compose.prod.yml up --build -d`); backend live at a real URL, still with
permissive CORS for now (tightened once M2's final URL is confirmed).

### Day 7–8 — Real integration

- M2 and M3 exchange real URLs (Contract 3): M2 sets `VITE_API_BASE_URL` to M3's
  backend; M3 sets `CORS_ALLOW_ORIGINS` to M2's frontend. Redeploy both.
- M1's scheduled-scan workflow points at the real deployed backend, with its
  service account provisioned there.
- Full login → upload/live-scan → findings → compliance → attack-paths flow
  re-verified against the real deployed stack, the same way it was verified
  locally against Docker for Wave C sign-off — this time over the real public
  URL.

### Day 9–10 — E2E + polish

- Confirm branch protection actually blocks a PR with a failing required check
  (don't just confirm the workflow runs — confirm it *gates*).
- Confirm the scheduled scan actually runs unattended once, on its real schedule,
  not just via manual `workflow_dispatch`.
- Docs complete; Wave D sign-off.

---

# Shared Contract 1 — Image / build artifact (M1 → M4)

M1 publishes: the exact `docker build` command and image tag name M4's Trivy job
scans. No registry push required (see decision #2) — CI builds the same image
fresh, scans it, and discards it; the artifact that matters for the deploy side
is the Dockerfile + compose file in the repo, not a pushed image.

# Shared Contract 2 — Required checks (M4 → M2, M3)

M4 publishes the final list of check names branch protection requires, before
M2/M3 wire anything to "merge to `main` triggers deploy." Both deploy workflows
should only run on pushes to `main` — which, once branch protection is
configured, already implies the required checks passed. Neither M2 nor M3 needs
its own redundant `needs:` gate on M4's job names as long as that's true.

# Shared Contract 3 — Production URLs (M2 ⇄ M3)

The one genuinely two-way handoff in this wave:

```json
{
  "frontend_url": "https://<project>.vercel.app",
  "backend_url": "https://<oracle-vm-host-or-domain>"
}
```

M2 sets `VITE_API_BASE_URL` to `backend_url`. M3 sets `CORS_ALLOW_ORIGINS` to
`frontend_url`. Neither value can be finalized before both sides have deployed
*something* — placeholder-then-swap, not a frozen contract published up front
the way Contracts 1 and 2 are.

---

# Member 1 — Containerization + Self-Scan

**What to do (in plain words):** make the backend image production-grade, define
how production is composed, and build the scheduled live-scan job.

## Files

```text
backend/Dockerfile                          (hardening edits)
infra/docker-compose.prod.yml               (new)
.github/workflows/scheduled-scan.yml        (new)
```

## Step-by-step

1. **Non-root user.** Add a dedicated user in the Dockerfile and `USER` before
   the `CMD`; confirm the app still starts and passes its healthcheck running as
   that user (file permissions on anything the app writes — none currently, it's
   stateless aside from the DB — should already be fine).
2. **`docker-compose.prod.yml`.** `backend` + `localstack` only (per the decision
   above: the live-scan target stays hosted LocalStack, not real AWS). Backend's
   `DATABASE_URL` comes from the production environment's Neon connection string,
   not a local `postgres` service. No bind-mount of a local `.env` — production
   secrets are injected by whatever the Oracle VM's deploy mechanism uses (env
   file placed directly on the VM, never committed, same `.env` discipline as
   local dev — just a different, non-`.env.example`-derived file).
3. **Scheduled-scan workflow.** A `schedule:` cron trigger. The job: log in as
   the service account (decision #3) using the exact flow a browser uses —
   `GET /auth/me` to bootstrap CSRF, `POST /auth/login` with the CSRF header,
   then `POST /scans/cloud` with the session cookie and a fresh CSRF token.
   Store the service account's password as a GitHub Actions secret, never in the
   workflow file. Fail the job loudly (not silently) if login fails — a silently
   broken scheduled scan is worse than an alerting one.
4. **Keep rules/ working exactly as today.** The backend image's `COPY . .`
   build context is `backend/` only — `rules/` is NOT baked into the image, it's
   only available via `docker-compose.yml`'s `../rules:/rules:ro` bind mount
   (already true today, and already correct, since Phase 3 fixed exactly this
   once before). This still works in production *only* because the whole repo
   checkout lives on the Oracle VM and `docker compose up` runs from there (per
   decision #2, build-on-VM) — don't change this pattern without re-solving that
   problem.

## Deliverables & checklist

- [ ] Non-root user in `backend/Dockerfile`, confirmed working
- [ ] `infra/docker-compose.prod.yml` (backend + localstack, no local postgres,
      production secrets, not `.env.example` values)
- [ ] Scheduled-scan workflow, service-account auth, fails loudly on login failure
- [ ] Confirmed the scheduled scan actually runs unattended, not just via manual dispatch
- [ ] Documentation

---

# Member 4 — CI/CD Security Pipeline

**What to do (in plain words):** turn "tests pass" into "tests pass *and* nothing
scanned comes back dangerous," and make that actually block a bad merge instead
of just reporting on one.

## Files

```text
.github/workflows/security-scan.yml   (new: Bandit, Semgrep, pip-audit, npm audit, CodeQL, Trivy)
```

(`gitleaks.yml` already exists and already runs — leave it, don't duplicate it.)

## Step-by-step

1. **Bandit** (Python SAST) over `backend/src`.
2. **pip-audit** over `backend/requirements.txt` (the one that ships, not
   `-dev` — a vulnerable dev-only tool matters less than a vulnerable production
   dependency).
3. **npm audit** over `frontend/` — `--audit-level=high` or similar, so routine
   low-severity transitive findings don't block every PR the way strict mode
   would (this project's own `npm install` log has already shown moderate/high
   advisories in transitive graph-library dependencies; triage once, don't let
   noise become the reason required checks get quietly disabled later).
4. **Semgrep** — community ruleset is enough; start advisory per the Day 0–2
   decision.
5. **CodeQL** — GitHub's native `github/codeql-action`, language matrix
   `python` + `javascript-typescript`. Needs `security-events: write` permission.
6. **Trivy** — scans the image M1's Dockerfile builds (Contract 1). Build it in
   this job (no registry needed, per decision #2), scan, discard.
7. **Branch protection.** This is a GitHub repository-settings change, not a
   workflow file — without it, every scanner above is purely informational.
   Require: Phase 1/2/3 tests, Bandit, pip-audit, npm audit, Trivy at minimum.

## Deliverables & checklist

- [ ] Bandit, pip-audit, npm audit, CodeQL, Trivy all running in CI
- [ ] Each scanner's first real run triaged (not just "it ran") — genuine
      findings fixed or explicitly suppressed with a reason, not ignored
- [ ] Branch protection actually configured and confirmed to block a failing PR
- [ ] Documentation

---

# Member 2 — Frontend Deployment

**What to do (in plain words):** get the dashboard live on a real URL, served
over TLS, talking to the real backend once it exists.

## Step-by-step

1. Connect the repo to Vercel; confirm the build command (`npm run build`) and
   output directory (`dist/`) are auto-detected correctly (standard Vite setup —
   should be zero-config).
2. Set `VITE_USE_MOCKS=false` and a placeholder `VITE_API_BASE_URL` in Vercel's
   project environment variables (never committed — this is exactly what
   `.env`/`.env.example` discipline already established, just in Vercel's
   dashboard instead of a local file).
3. TLS is automatic on Vercel — nothing to build, just confirm the deployed URL
   is actually `https://`.
4. **Contract 3:** once M3's backend is live, update `VITE_API_BASE_URL` to the
   real URL and redeploy.
5. Bundle check: the production build already code-splits per route
   (`DashboardPage`'s chunk is the largest, ~107 KB gzipped, mostly Recharts) —
   confirm this is still true after any Wave D changes rather than re-architecting
   it; it was already reasonable before this wave started.

## Deliverables & checklist

- [ ] Live Vercel URL, TLS confirmed
- [ ] `VITE_API_BASE_URL` pointed at the real deployed backend (Contract 3)
- [ ] Production env vars set in Vercel's dashboard, not committed
- [ ] Documentation (`docs/frontend-deployment.md`)

---

# Member 3 — Backend + DB Deployment

**What to do (in plain words):** get the API live on a real server, backed by a
real managed database, reachable only from the real frontend's origin.

## Step-by-step

1. **Neon.** Provision the production database; set `DATABASE_URL` to Neon's
   connection string (`postgresql+psycopg2://...?sslmode=require`, already
   exactly the pattern the root `.env.example` documents as the production
   option). Run migrations once by hand first to confirm the whole chain —
   including Wave C's `users`/`audit_log` tables — applies cleanly; after that,
   the Dockerfile's existing `alembic upgrade head` on container start handles
   it automatically, same as local dev.
2. **Oracle Cloud VM.** Deploy via `git pull && docker compose -f
   infra/docker-compose.prod.yml up --build -d` (decision #2). Confirm
   `/health` responds over the public URL.
3. **Production secrets on the VM**, not `.env.example` values: a real
   `JWT_SECRET`, a real `ADMIN_EMAIL`, `SECURE_COOKIES=true` (this is now
   genuinely production — the cookie flag Wave C built actually matters here),
   and (once M2's URL exists) `CORS_ALLOW_ORIGINS` set to it, not left permissive.
4. **Contract 3:** once M2's frontend URL exists, set `CORS_ALLOW_ORIGINS` to it
   and redeploy; confirm a real cross-origin request from the deployed frontend
   actually succeeds (not just that the backend is reachable directly).
5. No real AWS credentials anywhere — confirmed already true by design (see
   "What's already in place"); this step is verification, not new work.

## Deliverables & checklist

- [ ] Neon database live, migrations applied, confirmed against the full chain
- [ ] Backend live on the Oracle VM, `/health` reachable publicly
- [ ] `SECURE_COOKIES=true`, real `JWT_SECRET`/`ADMIN_EMAIL` on the VM, never committed
- [ ] `CORS_ALLOW_ORIGINS` locked to the real frontend origin (Contract 3),
      verified with an actual cross-origin request, not just a reachability check
- [ ] Documentation (`docs/backend-deployment.md`)

---

# End-to-End Wave D Flow

```text
M1: hardened image + docker-compose.prod.yml + scheduled-scan workflow
      │
      ▼
M4: Bandit/pip-audit/npm-audit/CodeQL/Trivy + gitleaks, all required checks
      │
      ▼ (merge to main now means something)
      ├──▶ M2: Vercel deploy ──┐
      │                        │  Contract 3: URL exchange
      └──▶ M3: Oracle+Neon ────┘
                  │
                  ▼
     Full login → scan → findings → compliance → attack-paths flow,
     re-verified over the real public URL
```

---

# GitHub Commit & Merge Order

```text
M1 → M4 → M2 ‖ M3 (M2 and M3 exchange URLs once both have deployed something)
```

| Step | Action |
|------|--------|
| 1 | M1 pushes hardened Dockerfile + `docker-compose.prod.yml` scaffold + scheduled-scan workflow → PR → Merge |
| 2 | Everyone pulls latest `main` |
| 3 | M4 pushes the scanner suite + branch protection config → PR → Merge |
| 4 | Everyone pulls latest `main` (required checks now active) |
| 5 | M2 pushes Vercel config/docs → deploys (placeholder backend URL) |
| 6 | M3 pushes `docker-compose.prod.yml` completion + deploy workflow → deploys (permissive CORS, temporarily) |
| 7 | M2 and M3 exchange real URLs (Contract 3); both redeploy with final values |
| 8 | M1's scheduled-scan workflow re-pointed at the real deployed backend |

---

# Testing Plan

## M1 — Containerization + Self-Scan
Image builds and runs as non-root · healthcheck passes · `docker-compose.prod.yml`
starts backend+localstack with no local postgres · scheduled-scan workflow's
login flow tested against local dev stack before touching production · a forced
login failure fails the job loudly, doesn't fail silently.

## M4 — CI/CD Security Pipeline
Each scanner actually runs and produces a result (not just "step completed") ·
a deliberately-introduced vulnerable dependency/pattern gets caught at least once
during setup (prove the gate actually gates, don't just trust a green run) ·
branch protection confirmed to block a PR with a failing required check.

## M2 — Frontend Deployment
Production build succeeds on Vercel · deployed site reachable over HTTPS ·
`VITE_API_BASE_URL` swap-and-redeploy actually takes effect (not cached).

## M3 — Backend + DB Deployment
Migrations apply cleanly to a fresh Neon database · `/health` reachable
publicly · a cross-origin request from the real deployed frontend succeeds
after `CORS_ALLOW_ORIGINS` is set (not just a same-origin curl check) ·
`SECURE_COOKIES=true` confirmed by inspecting a real `Set-Cookie` header from
the deployed instance, not assumed from config.

## Integration
Full signup → login → scan/live-scan → findings → compliance → attack-paths
flow works end to end over the real public URL, by the same real-request method
used to sign off Wave C — not re-validated only against local Docker.

---

# Guardrails

## Containerization
- No real secret ever baked into an image layer or committed to
  `docker-compose.prod.yml` — production secrets live only on the host
  (Oracle VM), the same way `.env` already works locally.
- Don't change the `rules/` bind-mount pattern without re-solving how the image
  gets its rules in whatever new deployment shape is being considered.
- The scheduled-scan job's service account is a real, separate Admin account —
  never the human operator's own login credentials in a GitHub secret.

## CI/CD
- A scanner that's merely present but not a required check isn't a gate — verify
  branch protection, don't just verify the workflow file exists.
- Triage real findings before flipping a scanner to required; a required check
  nobody can ever pass gets disabled out of necessity within a week, which is
  worse than never adding it.
- Don't push images to a registry unless build-on-VM (decision #2) genuinely
  becomes a bottleneck — added complexity with no current need.

## Deployment
- `SECURE_COOKIES=true` and a real `CORS_ALLOW_ORIGINS` are not optional in
  production — Wave C built both specifically for this moment.
- CORS lockdown is verified with an actual cross-origin browser-equivalent
  request, not just "the backend responds to curl."
- No real AWS credentials, ever — the live-scan target is hosted LocalStack,
  not real AWS; don't let "production" quietly imply switching that.

## Git
- No direct pushes to `main`. One feature per PR.
- `infra/docker-compose.prod.yml`: M1 creates, M3 extends — never both in the
  same window (see File-ownership map).
- Pull latest `main` after every merge — branch protection changes especially,
  since those affect what "green" means for everyone after M4's PR lands.

---

# Documentation Deliverables

| Member | File | Includes |
| --- | --- | --- |
| M1 | `docs/phase9-containerization.md` | Dockerfile hardening, production compose structure, scheduled-scan auth flow and schedule |
| M4 | `docs/phase9-ci-cd.md` | each scanner's purpose and config, which checks are required vs. advisory and why, how to triage a new finding |
| M2 | `docs/frontend-deployment.md` | Vercel project setup, env vars, the `VITE_API_BASE_URL` swap step |
| M3 | `docs/backend-deployment.md` | Neon provisioning, Oracle VM setup, the deploy command, the production secret list (names, not values) |

---

# Wave D Definition of Done

## Containerization + Self-Scan
- [ ] Backend image runs as non-root.
- [ ] `docker-compose.prod.yml` exists, backend+localstack only, no committed secrets.
- [ ] Scheduled scan runs unattended on its real schedule, with its own service account.

## CI/CD
- [ ] Bandit, pip-audit, npm audit, CodeQL, Trivy, and the existing `gitleaks` all run.
- [ ] Branch protection requires the agreed set of checks, confirmed to actually block a bad PR.
- [ ] Every scanner's first-run findings triaged, not ignored.

## Deployment
- [ ] Frontend live on Vercel, HTTPS confirmed.
- [ ] Backend live on Oracle Cloud, backed by Neon, migrations confirmed against a fresh instance.
- [ ] `CORS_ALLOW_ORIGINS` locked to the real frontend origin, verified with a real cross-origin request.
- [ ] `SECURE_COOKIES=true` confirmed via a real response header, not assumed.
- [ ] No real AWS credentials anywhere.

## Integration
- [ ] Full signup → auth → scan → findings → compliance → attack-paths flow verified over the real public URL.
- [ ] One real public URL, reachable by anyone, TLS everywhere.

---

# Metrics to Record

`docs/phase9-10-metrics.md`:
- image size before/after hardening
- scanner run time per workflow, and finding counts (before triage / after)
- which checks are required vs. advisory, and why
- deploy time (push to `main` → live) for frontend and backend separately
- scheduled-scan job: success rate over its first week of real runs
- uptime / `/health` reachability over the verification window

---

# Quick Summary

- **M1:** hardens the backend image (non-root user), defines
  `docker-compose.prod.yml`, builds the scheduled self-scan job — including
  solving how an unattended cron job authenticates against Wave C's now-real
  auth system (a dedicated service account, not a new auth mechanism).
- **M4:** turns `gitleaks`-only CI into a real security-gated pipeline (Bandit,
  Semgrep, pip-audit, npm audit, CodeQL, Trivy) and — the part that's easy to
  skip — actually makes those checks *required* in branch protection.
- **M2:** deploys the frontend to Vercel — mostly configuration, since Vercel
  builds from source and needs no Dockerfile.
- **M3:** deploys the backend to Oracle Cloud against a real Neon database,
  locks CORS to the real frontend origin, and turns on `SECURE_COOKIES`.
- Three decisions made explicit before Day 3, not improvised mid-wave: skip the
  frontend Docker image (Vercel doesn't need it), build-on-VM instead of a
  registry push, and a dedicated service account for the scheduled scan.
- M2 and M3 are the only parallel branch in this wave, and even they share one
  real handoff (Contract 3, the URL exchange) — this wave is a chain, budget
  for that instead of expecting Wave A/B's full independence.
- Nothing here reduces the live-scan target to real AWS, and nothing here
  stores a real cloud credential — "production" means a real public URL and a
  real database, not a bigger security surface than Wave C already hardened.
