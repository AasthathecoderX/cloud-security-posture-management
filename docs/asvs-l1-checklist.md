# OWASP ASVS L1 Checklist — Wave C (Phase 8)

Owner: Member 4 (Security Hardening + Verification). Each line cites the actual
test or code that satisfies it — not a bare checkbox. Where a control can't be
verified yet, it's marked **BLOCKED** with the specific gap from
`guides/wave C/Wave_C_Detailed_Execution_Plan.md`'s "Status check" table, not left
silently unchecked.

**Update (re-verified after M1's and M3's follow-up commits):** all three
previously-blocked controls are now closed — re-read directly against the merged
code (`routes.py`, `auth/routes.py`, `auth/rbac.py`, `auth/dependencies.py`), not
assumed from a commit message, and confirmed by the now-passing (no longer
`xfail`) tests in `backend/tests/test_security.py`. One new, unrelated gap turned
up while re-verifying (see V14) and is fixed below. One item remains genuinely
operational, not a code gap (see V14's last line).

**This checklist is signed off for everything except that one operational item.**

---

## V2 — Authentication

| Control | Status | Evidence |
| --- | --- | --- |
| Passwords hashed with a memory-hard algorithm (Argon2id), never plaintext/reversible | ✅ | `auth/hashing.py` (`pwdlib` `PasswordHash.recommended()`); `auth/tests/test_hashing.py` |
| Generic error message on login failure — doesn't reveal whether the account exists | ✅ | `auth/routes.py::login()` returns the same `401 Invalid email or password.` for both cases; `auth/tests/test_routes.py::test_wrong_password_returns_generic_error` |
| Credential stuffing / brute-force defense — rate limiting on login and signup | ✅ | `auth/routes.py` (`@limiter.limit("5/minute")`); `backend/tests/test_security.py::test_login_rate_limit_returns_429_after_five_attempts`, `test_signup_rate_limit_returns_429_after_five_attempts` |
| JWTs use a pinned algorithm; `alg: none` and algorithm confusion are rejected | ✅ | `auth/jwt.py::decode_token()` checks the unverified header's `alg` before trusting it; `backend/tests/test_security.py::test_jwt_rejects_none_algorithm` |
| Tampered token signatures are rejected | ✅ | `backend/tests/test_security.py::test_jwt_rejects_tampered_signature` |
| Short-lived access tokens, rotating refresh tokens, reuse-after-rotation rejected | ✅ | `auth/jwt.py` (15 min access / 7 day refresh, JTI tracked); `auth/tests/test_jwt.py`, `test_old_refresh_token_cannot_be_used_twice` |

## V3 — Session Management

| Control | Status | Evidence |
| --- | --- | --- |
| Session tokens delivered via `httpOnly` cookies, never in a JSON body or `localStorage` | ✅ | `auth/schemas.py` docstring: *"JWTs are deliberately NOT represented in these response schemas"*; `auth/routes.py::_set_auth_cookies()` |
| Session cookies marked `Secure` (prod) and `SameSite` | ✅ *(was BLOCKED, now fixed)* | `_set_auth_cookies()` now sets `secure=SECURE_COOKIES` (env-driven, defaults to `IS_PRODUCTION`) and `samesite="strict"` on both `access_token` and `refresh_token` — closes Status check #3 |
| Logout actually invalidates the session, not just clears the client cookie | ✅ | `auth/jwt.py::revoke_refresh_token()` adds the JTI to the used-token set; `auth/tests/test_routes.py::test_logout_clears_authentication` |
| CSRF protection on state-changing requests | ✅ | Double-submit cookie/header pattern, `auth/dependencies.py::require_csrf()` / `auth/routes.py::_verify_csrf()`, constant-time comparison (`hmac.compare_digest` in `auth/jwt.py::verify_csrf_token()`) |
| CSRF token is issued once per session, not regenerated on every read | ✅ *(was Status check #4, now fixed)* | `auth/dependencies.py::ensure_csrf_cookie()` now returns early if a `csrf_token` cookie already exists, instead of unconditionally calling `generate_csrf_token()` on every `GET /auth/me` |

## V4 — Access Control

| Control | Status | Evidence |
| --- | --- | --- |
| Every request to a protected endpoint requires a valid session | ✅ *(was BLOCKED, now fixed)* | `routes.py` now does a clean `from auth.dependencies import get_current_user` with no shadowing redefinition underneath it — confirmed by reading the file (no second `def get_current_user` remains) and by `backend/tests/test_security.py::test_scans_without_a_cookie_is_401`, which now passes outright (no longer `xfail`) |
| Role-based restriction on privileged actions (Admin vs. Viewer) | ✅ *(was BLOCKED, now fixed)* | `auth/rbac.py::require_role()` — denies with 403 (not 404, intentionally: the user knows their own role, so there's nothing to hide the way there is for scan ownership) and audit-logs the denial. Admin bootstrap via `ADMIN_EMAIL` env var at signup (`auth/routes.py`). `backend/tests/test_security.py::test_viewer_cannot_upload_a_scan` |
| Cross-user data access is denied (IDOR) | ✅ *(was blocked on Status check #1, now verified under real auth)* | `_load_owned_scan` (unchanged logic, predates Wave C) now provably scoped per *real* signed-up user, not the old shared placeholder: `backend/tests/test_security.py::test_real_admin_scan_is_hidden_from_second_real_user` signs up two distinct real accounts, confirms the second can't reach the first's scan (404), and confirms an audit row (`scan_access_denied`) was written |

## V5 — Validation, Sanitization

| Control | Status | Evidence |
| --- | --- | --- |
| Untrusted file uploads: size limits, extension allowlist, safe YAML/JSON parsing | ✅ (predates Wave C) | `parser.py` (`SecureParser`, `yaml.safe_load` only), `routes.py::upload_scan()`; `backend/tests/test_rules.py` |
| Request body size capped at the edge, before buffering | ✅ (predates Wave C) | `main.py::limit_request_body_size()` middleware |

## V7 — Error Handling and Logging

| Control | Status | Evidence |
| --- | --- | --- |
| Unhandled exceptions never leak internals (stack traces, SQL, file paths) to the client | ✅ (predates Wave C) | Upload/parse errors return a clean 400, not a 500; `backend/tests/test_api.py::test_upload_rejects_malformed_json` et al. |
| Rate-limit responses don't leak whether the limit is per-IP or per-account | ✅ | `slowapi`'s default 429 body is generic; not customized to add detail |
| Security-relevant events are logged (login/signup, role-check denial, IDOR denial) | ✅ | `auth/audit.py::log_event()`, writing to the existing `AuditLog` table; a failed audit write is caught and logged, never allowed to break the request it's auditing; `backend/tests/test_security.py::test_real_admin_scan_is_hidden_from_second_real_user` checks for `scan_access_denied` and `signup_success` rows |

## V9 — Communications

| Control | Status | Evidence |
| --- | --- | --- |
| CORS is off by default; opt-in per environment; never wildcard with credentials | ✅ | `main.py::validate_cors_origins()` raises at startup if `"*"` is configured alongside `allow_credentials=True`; `backend/tests/test_security.py::test_cors_rejects_wildcard_origin` |
| No long-lived real-AWS credentials stored; temporary credentials only for a real deployment | ✅ (documented + gated, not built against LocalStack) | `cloud/localstack.py` — `AWS_AUTH_MODE` defaults to `"static"` (LocalStack's dummy `test`/`test` creds); the `"assume_role"` path exists for a future real-AWS deployment, requires a mandatory `AWS_ASSUME_ROLE_EXTERNAL_ID` (confused-deputy defense), and is never exercised against LocalStack today — see the module docstring for why a real AssumeRole flow can't be verified in this project's current environment |

## V14 — Configuration

| Control | Status | Evidence |
| --- | --- | --- |
| No secret committed to git; `.env` gitignored, `.env.example` documents shape only | ✅ | `.gitignore` (`.env`, `.envrc`); manual grep pass found no real credentials in tracked files (one hit was a test fixture password string, `auth/tests/test_hashing.py`); ongoing enforcement via `.github/workflows/gitleaks.yml` on every PR and push |
| The old placeholder secret is explicitly rejected, not just replaced | ✅ | `auth/jwt.py::_get_secret()` raises if `JWT_SECRET` equals the literal Phase 0 placeholder string |
| Every `.env.example` variable name actually matches what the code reads | ✅ *(new finding, fixed during this re-verification)* | `backend/.env.example` (added alongside M1's latest commits) documented `JWT_SECRET_KEY`, but `auth/jwt.py::_get_secret()` only ever reads `JWT_SECRET` — anyone following that file literally would hit `RuntimeError: JWT_SECRET is not configured` at runtime. Fixed to `JWT_SECRET` in `backend/.env.example`. Worth a standing habit: this project has now hit the same "two files disagree, nobody notices until it crashes for real" shape three times (LocalStack's endpoint allowlist, `networkx` missing from prod `requirements.txt`, and now this) |
| The real `JWT_SECRET` is actually rotated in the environment that runs the app | **Operational, not code — still not done** | Status check #6, unchanged — the local `.env` still has the Phase 0 placeholder value, and now also has neither `ADMIN_EMAIL` nor `SECURE_COOKIES` set at all (both silently default to safe-for-dev values, so nothing breaks, but no one can bootstrap an Admin account against *this* local `.env` until `ADMIN_EMAIL` is set). The code correctly refuses to run signup/login on the placeholder secret; someone still has to actually replace it |

---

## Summary

- **Verified now:** 20 controls, each with a cited test or code reference — up
  from 15, since the three previously-blocked controls (session cookie flags,
  full access-control enforcement, IDOR under real sessions) plus the CSRF-
  rotation and audit-logging controls are now all closed and confirmed, not
  assumed.
- **`xfail(strict=True)` did its job.** The three tests written specifically to
  fail loudly until M1/M3 fixed the underlying gaps (`test_scans_without_a_cookie_is_401`,
  `test_viewer_cannot_upload_a_scan`, and the IDOR test) are no longer `xfail` —
  they're real, unconditional passes now. `pytest backend -q` is fully green
  (108 passed) with no `xfail`/`xpass` markers left in the suite.
- **One new gap found and fixed while re-verifying:** `backend/.env.example`
  documented the wrong variable name (`JWT_SECRET_KEY` instead of `JWT_SECRET`).
- **Still open, operational only:** the real local `.env`'s `JWT_SECRET` is
  still the Phase 0 placeholder, and `ADMIN_EMAIL`/`SECURE_COOKIES` aren't set
  in it at all. No code change needed — someone just has to actually set them
  before testing the full flow against a real running instance locally.

Re-run `pytest backend/tests/test_security.py -v` after any future auth-related
change — if an `xfail` ever reappears, or a currently-passing test starts
failing, that's this checklist's actual regression signal, not something to
discover by re-reading code by hand again.
