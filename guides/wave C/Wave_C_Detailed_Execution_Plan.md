# Wave C — Phase 8 (Authentication & Secure System Design)

Goal: turn the placeholder identity into a real, hardened multi-user platform (target:
OWASP ASVS L1). Team: 4 members. Assumes **Wave B is merged to `main`** — verified:
`backend/src/attack_paths/` and `backend/src/compliance/` are both live, and both
route through the exact same `get_current_user`/`_load_owned_scan` pair `routes.py`
already defines (confirmed by reading both routers' imports). That single choke point
is exactly what makes Wave C viable as a clean swap instead of a scavenger hunt.

By the end: signup/login with hashed passwords and httpOnly JWT cookies, every
endpoint (scans, compliance, attack-paths) enforcing real per-user data scoping and
Admin/Viewer roles, an audit trail of security events, and a hardened, rate-limited,
CORS-locked API passing a written ASVS L1 checklist.

> **This phase is different in shape from A and B.** Waves A and B each split into
> two independent branches that never touched each other's files. Wave C can't work
> that way — auth is cross-cutting by definition, and M3's job is literally to add
> role checks to the endpoints M1/M2/M3-before-now all built. The ownership map and
> sequencing below exist specifically to keep that from turning into four people
> editing `routes.py` at once.

---

## What's already in place (don't rebuild this)

- **`JWT_SECRET`** already exists in the root `.env`, seeded back in Phase 0 —
  currently the literal placeholder value `local-phase-zero-placeholder-change-before-auth-work`.
  M1 rotates this to a real secret; it stays untracked in `.env`, never committed.
- **CORS is already credentials-aware.** `main.py` sets `allow_credentials=True` with
  an explicit comment: *"Credentials are allowed so Phase 3 can use httpOnly auth
  cookies once Phase 8 lands. Phase 8 tightens this to the deployed origin."* M4's
  job here is narrowing `CORS_ALLOW_ORIGINS` for prod, not building this from scratch.
- **`User.role` (Admin/Viewer) and `AuditLog`** already exist in `models.py` — schema
  only, nothing reads or writes them yet. M3 wires both up; no migration needed.
- **The Axios client already sends `withCredentials: true`** (Phase 3) — cookies
  "just work" on the frontend once M1 sets them.
- **Every Wave B endpoint already imports `get_current_user` from `routes.py`**
  rather than rolling its own check — `compliance/routes.py` and
  `attack_paths/routes.py` both do `from routes import _load_owned_scan,
  get_current_user`. This is the fact the whole plan below leans on.

## Status check — M1's first PR landed, but M2/M3 are not clear to start yet

M1's Auth Core PR merged (`backend/src/auth/**`, 94 backend tests passing). A review
against this plan found it's not done — six gaps, two of which are **hard blockers**,
not polish. Nobody else should treat M1 as finished until these close.

| # | Gap | Blocks | Severity |
| --- | --- | --- | --- |
| 1 | `get_current_user` is imported from `auth.dependencies` in `routes.py`, then immediately **shadowed** by the old unchanged dev-user placeholder function defined right below it. Proven live: a real signed-up user's scan ends up owned by a separately auto-created `dev@local` row, not the signed-up user. | **M2, M3 — hard blocker.** Every endpoint still runs on the placeholder; there is no real identity to build a session UI against or RBAC on top of yet. | Critical |
| 2 | `signup()` hardcodes every new user to `role="VIEWER"`. No admin flag, invite code, or bootstrap path exists. | **M3 — hard blocker.** RBAC's entire deliverable is "Admin allowed, Viewer blocked" — untestable with zero accounts able to ever be Admin. | Critical |
| 3 | Auth cookies (`access_token`, `refresh_token`) are set with `httponly=True` only — no `secure`, no `samesite`. The CSRF cookie gets `samesite="strict"`; the session cookies that matter more don't. | M4's ASVS sign-off (can't check this control off); not a hard blocker for M2/M3 to *start*, but needs fixing before anyone demos over a real origin. | High |
| 4 | `GET /auth/me` regenerates the CSRF cookie on **every call**, including for an already-authenticated user just checking their session. | **M2 — soft blocker.** If `useSession` polls `/auth/me` on route changes (the obvious way to build it), an in-flight request holding the previous token can fail for no visible reason. M2 can start, but should know this before debugging a phantom bug. | Medium |
| 5 | A fresh browser has no CSRF cookie at all, so `signup`/`login` 403 until the client first calls `GET /auth/me` to bootstrap one — and `docs/phase8-auth-core.md` never says so. | **M2 — soft blocker**, same reason as #4: known in advance vs. discovered by debugging. | Medium |
| 6 | The real `.env`'s `JWT_SECRET` is still the Phase 0 placeholder. The code correctly refuses to run on it (good) — but nothing runs against a real instance until it's rotated. | Everyone, for any real (non-unit-test) run. | Operational |

**Practical sequencing implication:** M2 can scaffold against mocks today exactly as
planned (Day 0–2 doesn't change), but should not point at the *real* `/auth/*`
endpoints until #1, #4, and #5 are fixed. **M3 should not start at all** — not even
scaffolding `require_role()` against a mock — until M1 confirms #1 and #2 are fixed;
building RBAC logic is fine against a contract mock, but there is no point planning
*how* to test Admin-vs-Viewer against a system that currently cannot produce an Admin.

## What has to be decided before anyone writes code

Two things Wave A/B's guardrail sections would call "ambiguity that caused a bug
later" if left implicit:

1. **What can a Viewer actually do?** The dev placeholder is hardcoded to
   `UserRole.VIEWER`, but nothing currently enforces role at all, so this has never
   been tested against reality. Default policy for M1/M3 to build against unless the
   team overrides it: **Viewer = read-only** (list/view scans, findings, compliance,
   attack-paths); **Admin** additionally uploads files and triggers live scans
   (`POST /scans/upload`, `POST /scans/cloud`). Write this down in Contract 2 (below)
   before M3 starts adding `Depends(require_role(...))` anywhere.
2. **STS AssumeRole is a documentation/guardrail item, not new runtime code.** The
   project stays on LocalStack throughout (per every prior wave's scope), and
   LocalStack doesn't meaningfully emulate cross-account STS AssumeRole. M4's
   deliverable here is: confirm no long-lived real-AWS credentials are ever read from
   anywhere but env vars, document the AssumeRole pattern for a real-AWS deployment,
   and gate any such code behind a flag that's off in the LocalStack-only setup that
   actually ships. Don't let this become a week of building against an API LocalStack
   can't really exercise.

---

## The two rules that prevent conflicts and deadlocks

**1. No conflicts — one owner per folder/file, with one named exception.** Each
member owns a separate implementation area. The one unavoidable shared surface is
`backend/src/routes.py` (and, once M3 starts, `compliance/routes.py` and
`attack_paths/routes.py` too, for role annotations) — see "The shared-file problem,
solved" below for exactly how that stays conflict-free instead of hand-waved away
the way the original Wave B draft once did.

**2. No deadlocks — contract + mocks first.** M1 publishes the auth endpoint contract
and the shape of the authenticated-user object. M2 builds login/signup UI against
that contract. M1 also publishes the `require_role()` dependency's signature before
M3 needs it, so M3 isn't blocked waiting on M1's actual JWT implementation to finish
— only on its declared interface.

> Dependency shape, this wave, is **not** two independent trees — it's a short chain:
>
> - M1 (Auth Core) → M2 (Auth Frontend), in parallel with →
> - M1 (Auth Core) → M3 (RBAC/Scoping/Audit) → M4 (Hardening/Verification), since M4's
>   ASVS checklist needs M3's role enforcement actually in place to verify against.
>
> M2 and M3 can start the same day, both against M1's Day 0–2 contract. M4 starts
> the CORS/rate-limiting/secrets work immediately (no dependency), but the ASVS
> sign-off itself waits on M3.

---

## File-ownership map

| Owner | Folder / files (exclusive) |
| --- | --- |
| **Member 1 — Auth Core** | `backend/src/auth/**` (new), one edit to `routes.py`'s `get_current_user` (see below) |
| **Member 2 — Auth Frontend** | `frontend/src/features/auth/**`, one edit to `App.tsx` (login/signup routes + a protected-route wrapper) |
| **Member 3 — RBAC + Data Scoping + Audit** | `backend/src/auth/rbac.py` and `backend/src/auth/audit.py` (new, inside M1's folder — see below), plus small, explicitly-scheduled edits to `routes.py`, `compliance/routes.py`, `attack_paths/routes.py` to attach `Depends(require_role(...))` |
| **Member 4 — Security Hardening + Verification** | `backend/src/main.py` (rate limiting, CORS tightening), `docs/asvs-l1-checklist.md`, a new `backend/tests/test_security.py` |

### The shared-file problem, solved

`get_current_user` **lives inside `routes.py` today** — unlike Wave B, where new
work got its own router file and never touched the original, Auth's entire job is to
replace something that's already there. Solved the same way Wave B solved its shared
files: by relocation plus sequencing, not by "coordinate before editing."

- **M1** moves the real implementation to `backend/src/auth/dependencies.py`, then
  reduces `routes.py`'s version to a one-line re-export:
  `from auth.dependencies import get_current_user`. Because Python re-imports bind
  the same function object under a new name, `routes.get_current_user` *is*
  `auth.dependencies.get_current_user` — existing tests that do
  `main.app.dependency_overrides[routes.get_current_user] = ...` keep working
  unchanged. This is a single, self-contained PR; nobody else needs to touch
  `routes.py` for this part.
- **M3**, later (after M1 merges), adds `Depends(require_role(...))` to individual
  endpoints in `routes.py`, `compliance/routes.py`, and `attack_paths/routes.py`.
  This genuinely is M3 editing three files M1/others wrote — unavoidable, since RBAC
  is cross-cutting. Kept low-risk by scope: M3's edits are additive decorator-style
  `Depends(...)` annotations on existing endpoint signatures, never a rewrite of
  endpoint logic, and land in **one PR per router** (three small PRs, not one giant
  one) so a reviewer can actually see what role each endpoint now requires.

---

## Order of work

### Day 0–2 — Contracts + scaffolding

**M1**
- Finalize Contract 1 (auth endpoints) and Contract 2 (the `require_role()`
  dependency's signature — published even though the real RBAC logic isn't built
  yet, so M3 isn't blocked).
- Scaffold `backend/src/auth/` (`hashing.py`, `jwt.py`, `dependencies.py`,
  `routes.py`, `schemas.py`).
- Rotate `JWT_SECRET` to a real value in the local `.env` (never committed).

**M2**
- Scaffold `frontend/src/features/auth/` (`LoginPage.tsx`, `SignupPage.tsx`, a
  session hook/context).
- Build page shells against Contract 1's mock responses.

**M3**
- Confirm the Viewer/Admin policy above (or propose changes) — get it written down
  before building against it.
- Scaffold `backend/src/auth/rbac.py` (role-check helper) and `audit.py`
  (`log_event()` helper) against M1's Contract 2 signature + mock.

**M4**
- Start immediately, no dependency: rate-limiting config (`slowapi`), CORS origin
  tightening, a secrets audit (grep the repo for anything that looks like a
  hardcoded credential), and the ASVS L1 checklist skeleton (empty checkboxes, to
  be filled as each control is verified against the real implementation).

### Day 3–6 — Parallel implementation

**M1**
- Signup/login/refresh/logout with Argon2id (`pwdlib[argon2]`) + JWT in httpOnly
  cookies (pinned `alg`, short access-token expiry, rotating refresh token).
- Replace `get_current_user`'s placeholder body with real cookie/JWT validation,
  per the relocation pattern above.

**M2**
- Real login/signup forms against M1's real endpoints as they land; session
  persistence (cookie-based, no token in localStorage); protected-route redirect
  to `/login` when a request comes back 401.

**M3**
- Implement `require_role()` for real; add audit-log writes at the actual security
  events that matter (login success/failure, role-check denial, scan access denial)
  — reusing the existing `AuditLog` model, no schema change.
- **Do not** start adding `Depends(require_role(...))` to the three routers until
  M1's real (not mocked) `get_current_user` has merged — a role check built on a
  contract mock is fine to develop against, but wiring it into production endpoints
  against a mock identity risks locking out the placeholder flow other in-flight
  work still depends on.

**M4**
- Wire `slowapi` onto login/signup (the endpoints that actually need rate limiting)
  and the upload endpoint; lock `CORS_ALLOW_ORIGINS` down per environment; write
  `backend/tests/test_security.py` (see Testing Plan).

### Day 7–8 — Real integration

- M3 lands the three small role-annotation PRs (`routes.py` →
  `compliance/routes.py` → `attack_paths/routes.py`, in that order, one per PR).
- M2 swaps any remaining mock auth calls for the real endpoints.
- M4 runs the ASVS checklist against the now-complete implementation, not the
  scaffold from Day 0–2.

### Day 9–10 — E2E + polish

- Full flow: signup → login → upload a scan (Admin) → a Viewer account confirms it
  can read but not upload → logout → cookie is actually cleared.
- Audit log inspected for a real session's worth of events.
- Security test suite green; ASVS L1 checklist signed off; docs complete.

---

# Shared Contract 1 — Auth API

Member 1 publishes this; Member 2 codes to it. Its own `APIRouter` in
`backend/src/auth/routes.py`, included from `main.py` — same pattern as
Wave B's routers, so `routes.py` itself never gains new endpoints for this.

## Endpoints

```
POST /auth/signup   { email, password }              -> 201, sets auth cookies
POST /auth/login    { email, password }              -> 200, sets auth cookies
POST /auth/refresh  (reads refresh cookie)            -> 200, rotates access cookie
POST /auth/logout   (reads auth cookie)                -> 204, clears cookies
GET  /auth/me       (reads auth cookie)                -> 200, { user_id, email, role }
```

Cookies: `access_token` (short expiry, e.g. 15 min) and `refresh_token` (longer,
rotated on use), both `httpOnly`, `Secure` in production, `SameSite=Strict`. No
token is ever returned in a JSON body — the whole point of the cookie approach is
that frontend JS never touches the token directly.

Error responses reuse the existing `ErrorResponse` shape (`{"detail": "..."}"`) and
**never distinguish "wrong password" from "no such user"** in the message — both
produce the same generic `401 Invalid email or password.`, to avoid user
enumeration (this is an ASVS L1 control, not a nice-to-have).

---

# Shared Contract 2 — `require_role()`

Member 1 publishes this (signature only, Day 0–2); Member 3 implements it and
applies it.

```python
# backend/src/auth/rbac.py
def require_role(*roles: UserRole) -> Callable:
    """FastAPI dependency factory. Usage:

        @router.post(..., dependencies=[Depends(require_role(UserRole.ADMIN))])

    Raises 403 (not 404) if the authenticated user's role isn't in `roles` --
    403 here is correct and intentional, unlike the 404-for-IDOR pattern
    `_load_owned_scan` uses: role denial isn't about hiding whether a resource
    exists, it's about a user knowing their own account can't do this action.
    """
```

**Default policy (confirm or override before M3 builds against it):**

| Endpoint | Admin | Viewer |
| --- | --- | --- |
| `POST /scans/upload`, `POST /scans/cloud` | yes | no |
| `GET /scans`, `GET /scans/{id}`, `GET /scans/{id}/findings` | yes | yes |
| `GET /scans/{id}/compliance`, `GET /scans/{id}/attack-paths` | yes | yes |

---

# Member 1 — Auth Core

**What to do (in plain words):** replace the "always logged in as a dev user"
placeholder with real accounts, real password hashing, and real sessions.

> **Status: first PR merged, not done.** See "Status check" above for the full
> review. The step-by-step and checklist below are updated in place (marked
> ⚠️ FIX) rather than kept as a second, separate list — this *is* the current,
> real checklist, not the original pre-build aspiration.

## Files

```text
backend/src/auth/
├── __init__.py
├── hashing.py       Argon2id via pwdlib -- hash_password(), verify_password()
├── jwt.py            encode/decode, pinned alg, short access + rotating refresh
├── dependencies.py   get_current_user() -- the real implementation lives here now
├── routes.py         signup/login/refresh/logout/me, its own APIRouter
├── schemas.py
└── tests/
    ├── test_hashing.py
    ├── test_jwt.py
    └── test_routes.py
```

## Step-by-step

1. **Hashing** — `pwdlib[argon2]`. Never log a password or a hash. Salt is built
   into Argon2id; no separate salt column needed.
2. **JWT** — pin the algorithm explicitly (e.g. `HS256`) and **reject `alg: none`
   and algorithm-confusion** on decode; this is the single most common JWT
   implementation bug and exactly what ASVS L1 checks for. Short access-token
   expiry (~15 min), longer rotating refresh token.
3. **Cookies, not response bodies.** `Set-Cookie` with `httpOnly`, `Secure` (prod),
   `SameSite=Strict`. CSRF: since cookies are used, add a double-submit CSRF token
   on state-changing requests (`POST /scans/upload`, `POST /scans/cloud`, and the
   auth endpoints themselves).
   ⚠️ **FIX:** shipped with `httponly=True` only — `secure`/`samesite` are missing
   from `_set_auth_cookies()` in `auth/routes.py` entirely (Status check #3).
4. **Replace `get_current_user`** — move the real implementation to
   `auth/dependencies.py`, validating the `access_token` cookie and loading the
   `User` row. `routes.py` keeps a one-line re-export (see File-ownership map) so
   every existing import (`compliance/routes.py`, `attack_paths/routes.py`, and
   `routes.py`'s own endpoints) keeps working with zero changes to their import
   lines.
   ⚠️ **FIX (critical, blocks M2 and M3):** the real implementation was built, but
   `routes.py` still has the *old* placeholder function defined after the import,
   which shadows it. Delete the placeholder's body (routes.py lines ~76–98) —
   don't just add the import next to it (Status check #1).
5. **Remove the dev-user auto-create branch entirely** — not just gate it tighter.
   The current code already refuses to fabricate an identity when
   `CSPM_ENV=production`; Wave C makes that the *only* code path, in every
   environment.
   ⚠️ **FIX:** same shadowing bug as #4 — the branch wasn't removed, it's just
   sitting underneath an import that never gets used.
6. **Generic errors, always** — see Contract 1's note on user enumeration. This one
   actually shipped correctly — `login()` already returns the same message for
   "no such user" and "wrong password."
7. **NEW — add an Admin bootstrap path.** Not in the original plan; found during
   review. `signup()` hardcodes `role="VIEWER"` with no way for any account to
   ever become Admin (Status check #2). Pick one: an env-gated first-admin seed, a
   one-time invite code, or a manual promotion step — then document the choice.
8. **NEW — issue the CSRF cookie once per session, not on every `/auth/me` call.**
   Currently `get_me()` calls `generate_csrf_token()` unconditionally on every
   request, including reads from an already-authenticated session (Status check
   #4). Issue it on login/signup; don't regenerate it on a plain session check.
9. **NEW — document the CSRF-bootstrap requirement** in
   `docs/phase8-auth-core.md`: a client must call `GET /auth/me` once before its
   first `signup`/`login` to receive a CSRF cookie at all, or it 403s with no
   explanation (Status check #5).

## Deliverables & checklist

- [ ] Argon2id hashing, no plaintext/reversible storage anywhere — **done**
- [ ] JWT: pinned alg, `alg: none` rejected, short expiry + rotating refresh — **done**
- [ ] Cookies: httpOnly + Secure (prod) + SameSite=Strict, CSRF double-submit token
      — **partially done; `secure`/`samesite` missing, see step 3**
- [ ] `get_current_user` relocated to `auth/dependencies.py`, re-exported from
      `routes.py` — **not done; real implementation exists but is shadowed, see step 4**
- [ ] Dev-user placeholder removed (not just environment-gated) — **not done, same
      root cause as above**
- [ ] `POST /auth/signup`, `/login`, `/refresh`, `/logout`, `GET /auth/me` — **done**
- [ ] Generic, non-enumerating error messages — **done**
- [ ] Unit tests + a real (non-overridden) login-flow integration test — **the auth
      endpoints are tested in isolation; still missing an integration test that
      signs up a real user and confirms a *feature* endpoint (e.g. `/scans`) scopes
      data to that real user — this is exactly the test that would have caught the
      shadowing bug**
- [ ] Admin bootstrap path exists — **not done (new item, step 7)**
- [ ] CSRF cookie issued once per session, not per `/auth/me` call — **not done (new item, step 8)**
- [ ] `docs/phase8-auth-core.md` documents the CSRF-bootstrap requirement — **not done (new item, step 9)**
- [ ] Real `.env`'s `JWT_SECRET` rotated off the Phase 0 placeholder — **not done (Status check #6, operational, not code)**
- [ ] Documentation

---

# Member 2 — Auth Frontend

**What to do (in plain words):** let a user sign up, log in, stay logged in across a
refresh, and get redirected to log in when a protected request fails.

> **Clear to scaffold now, not clear to integrate yet.** Build against Contract 1's
> mock as planned (Day 0–2 doesn't change). Before pointing at the *real*
> `/auth/*` endpoints, confirm with M1 that Status check #1 (the shadowing bug) is
> fixed — otherwise every real request will resolve to the same dev placeholder
> user regardless of who's logged in, and you'll be debugging M1's bug, not yours.
> Also design `useSession` around two things M1's current build gets wrong, so you
> don't have to redo it later: (a) don't call `GET /auth/me` more often than you
> have to — it currently reissues the CSRF cookie on every call (#4), which can
> invalidate an in-flight request's token; (b) a brand-new session has no CSRF
> cookie at all, so call `GET /auth/me` once up front specifically to bootstrap one
> before the first `signup`/`login` attempt, or it 403s with no explanation (#5).

## Files

```text
frontend/src/features/auth/
├── LoginPage.tsx
├── SignupPage.tsx
├── useSession.ts        session state, derived from GET /auth/me
├── ProtectedRoute.tsx    wraps a route, redirects to /login on no-session
└── index.ts
```

**Also touches `App.tsx`** — adds `/login`, `/signup` routes and wraps the existing
protected routes (`/scans`, `/upload`, `/dashboard`, `/scans/:id`) in
`ProtectedRoute`. Low risk: `App.tsx` has already absorbed one new route per wave
(Dashboard in Wave A, the now-retired Attack-Path route in Wave B) without
conflict, because it's always a small, additive, easily-reviewed diff.

## Step-by-step

1. Login/signup forms — client-side validation only for UX; the server is the real
   authority either way.
2. `useSession` — calls `GET /auth/me` once on load (cookie already sent via
   `withCredentials`); exposes `{ user, isLoading, isAuthenticated }`.
3. `ProtectedRoute` — redirects to `/login` if unauthenticated; preserves the
   originally-requested path so login can return the user there.
4. **401 handling globally** — the Axios client (`api/client.ts`) should redirect
   to `/login` on any `401`, not just inside one page, so a session that expires
   mid-use doesn't strand the user on a page silently failing every request.
5. Logout clears session state and calls `POST /auth/logout`.
6. States: loading, invalid credentials (generic message, matching Contract 1),
   network error.

## Deliverables & checklist

- [ ] Login / signup pages, real API integration
- [ ] `useSession`, `ProtectedRoute`
- [ ] Global 401 → redirect-to-login handling in the Axios client
- [ ] Existing routes wrapped in `ProtectedRoute`
- [ ] Tests (MSW, same pattern as every other feature this project already has)

---

# Member 3 — RBAC + Data Scoping + Audit

**What to do (in plain words):** make sure a Viewer can't do Admin things, a user
can never see another user's scans (already true via `_load_owned_scan`, but now
prove it under real auth instead of the dev-user placeholder), and there's a record
of who did what.

> **Do not start yet — not even scaffolding `require_role()` against a mock.**
> Two of M1's gaps are hard blockers specifically for this role, not just
> inconvenient: Status check #1 (every request still resolves to the same
> placeholder user, so there's no real identity to check a role against) and #2
> (no account can ever be Admin, so "Viewer blocked / Admin allowed" has nothing to
> test against). Confirm both are fixed before doing anything beyond reading this
> plan. Once confirmed, step 2 below (applying `require_role()` to the three
> routers) still only happens after M1's real `get_current_user` is merged — that
> sequencing was always the plan; it's just now a hard gate instead of a formality.

## Files

```text
backend/src/auth/
├── rbac.py    require_role() -- real implementation
└── audit.py   log_event(session, user_id, action, ip_address)
```

## Step-by-step

1. **`require_role()`** — per Contract 2. 403 on denial, not 404 (this is the one
   place in the app where a 404-for-everything IDOR posture is *wrong* — the user
   knows they're logged in and knows their own role, so hiding that isn't a
   meaningful defense here the way it is for scan ownership).
2. **Apply it** per the default policy table, across three small PRs (one per
   router), only after M1's real `get_current_user` is merged.
3. **Re-verify IDOR under real auth.** `_load_owned_scan` already scopes every scan
   query to `user.user_id` — that logic doesn't change. What changes is that
   `user.user_id` now comes from a real JWT instead of the single hardcoded dev
   user, so the existing IDOR tests (`test_idor_other_user_cannot_read_scan`, etc.)
   need a second version that creates two *real* accounts via signup and confirms
   the same 404-not-403 behavior holds end to end.
4. **Audit log** — write an `AuditLog` row for: login success, login failure, signup,
   role-check denial (403), and IDOR denial (404) on someone else's scan. Use the
   existing model as-is; no migration needed.

## Deliverables & checklist

- [ ] `require_role()` implemented and unit-tested
- [ ] Role annotations applied to `routes.py`, `compliance/routes.py`,
      `attack_paths/routes.py` (three PRs)
- [ ] IDOR re-verified against two real (signed-up) accounts, not just the dev
      placeholder
- [ ] Audit log writes at the five events above
- [ ] Tests + documentation

---

# Member 4 — Security Hardening + Verification

**What to do (in plain words):** lock down everything Auth Core, RBAC, and every
prior wave built, then prove it with a checklist and a test suite — not just "it
looks secure."

> Free to start the rate-limiting/CORS/secrets work now, as planned — none of it
> depends on M1/M3. But hold the ASVS L1 sign-off itself open on one line until
> M1 ships Status check #3 (`secure`/`samesite` on the actual session cookies, not
> just the CSRF cookie) — that's a real ASVS control, and it isn't checked off yet.

## Files

```text
backend/src/main.py            (rate limiting + CORS, edited in place)
backend/tests/test_security.py  (new)
docs/asvs-l1-checklist.md       (new)
```

## Step-by-step

1. **Rate limiting** (`slowapi`) on `/auth/login`, `/auth/signup` (brute-force /
   enumeration defense) and `/scans/upload` (abuse defense). Generic 429, no
   detail leaking whether the rate limit was per-IP or per-account.
2. **CORS** — tighten `CORS_ALLOW_ORIGINS` to the exact deployed origin(s) per
   environment; confirm it's never accidentally `*` with `allow_credentials=True`
   (that combination is rejected by browsers anyway, but don't rely on the browser
   to catch a misconfiguration).
3. **Secrets audit** — grep the repo for anything that looks like a credential,
   confirm `.env`/`.env.example` discipline is intact (already established since
   Phase 0 — this is a verification pass, not new process).
4. **STS AssumeRole** — per the "What has to be decided" section above: document +
   flag-gate, don't build a parallel credential path LocalStack can't exercise.
5. **`test_security.py`** — exercises the *attacker's* perspective, not the happy
   path M1/M2/M3 already tested:
   - login with `alg: none` / a forged JWT → rejected
   - Viewer hitting `POST /scans/upload` → 403
   - user A hitting user B's scan → 404 (not 403 — confirms IDOR posture, not just
     RBAC)
   - exceeding the login rate limit → 429
   - missing/expired cookie on a protected endpoint → 401
6. **ASVS L1 checklist** — one line per control, each citing the specific test or
   code that satisfies it (not a bare checkbox with no evidence).

## Deliverables & checklist

- [ ] Rate limiting on auth + upload endpoints
- [ ] CORS locked to real origins per environment
- [ ] Secrets audit clean
- [ ] STS AssumeRole documented + gated, not half-built against LocalStack
- [ ] `backend/tests/test_security.py`, attacker-perspective, all green
- [ ] `docs/asvs-l1-checklist.md`, each line citing evidence

---

# End-to-End Wave C Flow

```text
Signup (Argon2id hash stored) → Login (JWT set as httpOnly cookies)
  → GET /auth/me confirms session → protected routes now reachable
  → Admin: POST /scans/upload succeeds
  → Viewer (separate account): same request → 403 (RBAC), reading it back → 200
  → User A's scan fetched by User B → 404 (IDOR, unchanged since Phase 2)
  → Every one of the above writes an AuditLog row
  → Logout clears cookies, GET /auth/me → 401, redirected to /login
```

---

# GitHub Commit & Merge Order

```text
M1 (auth core) → M2 (auth frontend) ‖ M3 (rbac/audit, starts after M1 merges)
  → M3's three router PRs (routes.py → compliance/routes.py → attack_paths/routes.py)
  → M4 (hardening + ASVS sign-off, last -- needs M3's role enforcement in place to verify)
```

| Step | Action |
|------|--------|
| 1 | M1 pushes Auth Core → PR → Review → Merge |
| 2 | Everyone pulls latest `main` |
| 3 | M2 pushes Auth Frontend → PR → Review → Merge (can start once M1's Contract 1 lands, in parallel with step 4) |
| 4 | M3 pushes `require_role()` + audit → PR → Review → Merge |
| 5 | Everyone pulls latest `main` |
| 6 | M3 pushes role-annotation PR #1 (`routes.py`) → Merge |
| 7 | M3 pushes role-annotation PR #2 (`compliance/routes.py`) → Merge |
| 8 | M3 pushes role-annotation PR #3 (`attack_paths/routes.py`) → Merge |
| 9 | Everyone pulls latest `main` |
| 10 | M4 pushes hardening + `test_security.py` + ASVS checklist → PR → Review → Merge |

---

# Testing Plan

## M1 — Auth Core
Signup (duplicate email rejected) · login (correct / wrong password, both return the
same generic error) · JWT: valid / expired / tampered / `alg: none` · refresh
rotation · logout clears cookies · a real (non-overridden) end-to-end login test.

## M2 — Auth Frontend
Login/signup success and error states · session persists across a reload ·
protected route redirects when unauthenticated · global 401 → redirect.

## M3 — RBAC + Audit
`require_role()` allow/deny per the policy table · IDOR re-verified with two real
accounts · audit rows written for each of the five tracked events · a rule/role
mismatch (e.g. a role that doesn't exist) fails closed, never open.

## M4 — Hardening
Rate limit triggers and recovers · CORS rejects an unlisted origin · forged/`none`-alg
JWT rejected · secrets-audit script finds nothing · every ASVS L1 line has cited
evidence.

---

# Guardrails

## Auth Core
- Argon2id only — no MD5/SHA1/plain, no reversible encryption of passwords.
- Reject `alg: none` and algorithm confusion on every JWT decode.
- Never put a token in a JSON response body or in `localStorage`.
- Generic auth error messages — never confirm whether an email exists.
- The dev-user placeholder is deleted, not just environment-gated tighter.

## RBAC / Scoping / Audit
- Role denial is 403; ownership denial (IDOR) stays 404 — don't blur these, they
  answer different questions ("can you do this at all" vs "does this exist for you").
- Every role-annotation PR is scoped to one router file — no drive-by edits to
  unrelated endpoints while touching a file for this.
- Audit log writes never block the request on failure (log, don't crash, if the
  audit write itself fails) — the audit trail should never become a new way to
  take down the API.

## Hardening
- No secret ever hardcoded or committed — `.env` only, `.env.example` documents the
  shape, never the value.
- Don't build real STS AssumeRole code against LocalStack's incomplete emulation of
  it; document + flag-gate instead.
- CORS credentials + wildcard origin never coexist, even though browsers already
  block it — don't rely on the browser as the only backstop.

## Frontend
- No token handling in JS at all — cookies only, `withCredentials: true` (already
  the case since Phase 3).
- Every existing protected route actually gets wrapped — verify by trying to hit
  one logged out, not by reading the route list.

## Git
- No direct pushes to `main`. One feature per PR — including RBAC's three router
  PRs, which are deliberately three PRs, not one.
- M3 does not start the router role-annotation PRs until M1's real (not mocked)
  auth has merged.
- Pull latest `main` after every merge.

---

# Documentation Deliverables

| Member | File | Includes |
| --- | --- | --- |
| M1 | `docs/phase8-auth-core.md` | hashing choice, JWT design (alg, expiry, refresh rotation), cookie flags, CSRF approach, the `get_current_user` relocation |
| M2 | `docs/auth-ui.md` | session model, protected-route behavior, global 401 handling |
| M3 | `docs/phase8-rbac-audit.md` | role policy table (final, post-decision), IDOR-vs-RBAC status-code rationale, audit event list |
| M4 | `docs/asvs-l1-checklist.md` | one line per control, each citing its test or implementation |

---

# Wave C Definition of Done

## Auth Core
- [ ] Signup/login/refresh/logout work end to end with real cookies.
- [ ] `get_current_user` is the real implementation everywhere — dev-user
      placeholder is gone, not just gated.
- [ ] JWT rejects `alg: none` and tampering; expiry + refresh rotation verified.

## RBAC / Scoping / Audit
- [ ] Viewer blocked from Admin-only endpoints (403); IDOR still 404 for
      cross-user access, re-verified with two real accounts.
- [ ] Audit log has real rows for the five tracked events.

## Hardening
- [ ] Rate limiting live on auth + upload; CORS locked to real origins.
- [ ] `test_security.py` green; ASVS L1 checklist complete with evidence per line.

## Integration
- [ ] The full End-to-End Wave C Flow above works against one real run.
- [ ] Every existing Wave A/B test suite (scans, compliance, attack-paths, ML
      scoring) still passes under real auth, not just the dev-user override.
- [ ] Documentation complete.

---

# Metrics to Record

`docs/phase8-metrics.md`:
- signup/login success & failure counts (from a test run, not production)
- JWT expiry/refresh timings actually used
- number of endpoints now role-gated vs. total
- audit log event counts by type
- rate-limit thresholds chosen and why
- ASVS L1: controls checked vs. total, with evidence links
- test count and pass/fail status (including the "existing suites still pass under
  real auth" regression check)

---

# Quick Summary

- **M1:** Auth Core — Argon2id, JWT-in-httpOnly-cookies, relocates
  `get_current_user` to `auth/dependencies.py` with a one-line re-export from
  `routes.py` so nobody else's imports break.
- **M2:** Auth Frontend — login/signup, session hook, protected routes, global
  401 handling.
- **M3:** RBAC + Audit — `require_role()`, three small router PRs (not one big one),
  re-verifies IDOR under real accounts, wires the already-existing `AuditLog` model.
- **M4:** Hardening + Verification — rate limiting, CORS lockdown, a real
  attacker-perspective test suite, and an ASVS L1 checklist with evidence, not
  just checkboxes.
- Sequencing is a chain, not two independent trees, because auth is cross-cutting:
  M1 first, then M2 ‖ M3, then M3's router PRs, then M4 last (needs M3's real
  enforcement to verify against).
- The Viewer/Admin policy and the STS/LocalStack scope are decided *before* Day 3,
  not improvised mid-wave.
- Every existing test suite from Waves A and B must still pass once the dev-user
  placeholder is gone — that's the real proof this wave didn't just add auth on
  top, it replaced the thing every prior wave was built to tolerate as temporary.
