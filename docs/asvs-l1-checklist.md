# OWASP ASVS L1 Checklist — Wave C (Phase 8)

Owner: Member 4 (Security Hardening + Verification). Each line cites the actual
test or code that satisfies it — not a bare checkbox. Where a control can't be
verified yet, it's marked **BLOCKED** with the specific gap from
`guides/wave C/Wave_C_Detailed_Execution_Plan.md`'s "Status check" table, not left
silently unchecked.

**This checklist is not signed off.** Three controls are blocked on M1/M3 work in
progress (see the Status check table in the Wave C plan). Do not represent this as
a completed ASVS L1 pass until those three close.

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
| Session cookies marked `Secure` (prod) and `SameSite` | **BLOCKED** | Status check #3 — `_set_auth_cookies()` sets `httponly=True` only; no `secure`, no `samesite`, on the cookies that actually carry the session. (The separate CSRF cookie does set `samesite="strict"` — the session cookies don't.) |
| Logout actually invalidates the session, not just clears the client cookie | ✅ | `auth/jwt.py::revoke_refresh_token()` adds the JTI to the used-token set; `auth/tests/test_routes.py::test_logout_clears_authentication` |
| CSRF protection on state-changing requests | ✅ | Double-submit cookie/header pattern, `auth/dependencies.py::require_csrf()` / `auth/routes.py::_verify_csrf()`, constant-time comparison (`hmac.compare_digest` in `auth/jwt.py::verify_csrf_token()`) |

## V4 — Access Control

| Control | Status | Evidence |
| --- | --- | --- |
| Every request to a protected endpoint requires a valid session | **BLOCKED** | Status check #1 — `routes.py`'s real `get_current_user` import is shadowed by the old dev-user placeholder, so feature endpoints (`/scans`, compliance, attack-paths) currently accept *any* request, session or not. `backend/tests/test_security.py::test_scans_without_a_cookie_is_401` (xfail, tied to this exact gap) |
| Role-based restriction on privileged actions (Admin vs. Viewer) | **BLOCKED** | Status check #2 — no account can ever be Admin (hardcoded `role="VIEWER"` on signup), and `require_role()` (Member 3) isn't built yet. `backend/tests/test_security.py::test_viewer_cannot_upload_a_scan` (xfail, tied to this exact gap) |
| Cross-user data access is denied (IDOR) | **BLOCKED for verification under real auth** | The *logic* (`_load_owned_scan` scoping every query to `user.user_id`, returning 404 not 403) predates Wave C and hasn't changed. But it can't be proven correct under *real* sessions until Status check #1 is fixed — until then, every session resolves to the same placeholder user, so two signed-up accounts can't be distinguished. `backend/tests/test_security.py::test_two_real_users_do_not_share_scan_ownership` (xfail, tied to Status check #1) |

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
| The real `JWT_SECRET` is actually rotated in the environment that runs the app | **Operational, not code — not yet done** | Status check #6 — the local `.env` still has the Phase 0 placeholder value; the code correctly refuses to run on it (`RuntimeError`), but no `/auth/*` request can succeed against a real running instance until someone replaces it |

---

## Summary

- **Verified now:** 15 controls, each with a cited test or code reference.
- **Blocked on Member 1 / Member 3:** 3 controls (cookie flags, full access-control enforcement, IDOR verification under real sessions) — all three already have a written `xfail(strict=True)` test in `backend/tests/test_security.py` that will fail loudly (forcing this checklist to be updated) the moment someone fixes the gap and forgets to flip it.
- **Operational, not a code gap:** rotating the real `.env`'s `JWT_SECRET`.

Re-run `pytest backend/tests/test_security.py -v` after each of M1's remaining fixes lands — an `xfail` flipping to an unexpected pass means strict mode will fail the suite until the corresponding line above is updated from BLOCKED to ✅.
