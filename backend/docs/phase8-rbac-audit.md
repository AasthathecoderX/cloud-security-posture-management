# Phase 8 — RBAC, Data Scoping, and Audit (Member 3)

## Role policy

| Endpoint/action | Admin | Viewer | Denial behavior |
|---|---:|---:|---|
| `POST /scans/upload` | Allow | Deny | `403 Forbidden` |
| `POST /scans/cloud` | Allow | Deny | `403 Forbidden` |
| `GET /scans` | Allow | Allow | Authentication required |
| `GET /scans/{scan_id}` | Own scans only | Own scans only | `404 Not Found` for missing or another user's scan |
| `GET /scans/{scan_id}/findings` | Own scans only | Own scans only | `404 Not Found` for missing or another user's scan |
| `GET /scans/{scan_id}/compliance` | Own scans only | Own scans only | `404 Not Found` for missing or another user's scan |
| `GET /scans/{scan_id}/attack-paths` | Own scans only | Own scans only | `404 Not Found` for missing or another user's scan |

## Implementation

- `src/auth/rbac.py` implements `require_role(*roles)` as a FastAPI dependency factory. It fails closed when no allowed roles are supplied and returns HTTP 403 when the authenticated user has no permitted role.
- Scan upload and live cloud scan endpoints require `UserRole.ADMIN`. Read endpoints allow `ADMIN` and `VIEWER`.
- `src/routes.py::_load_owned_scan` checks ownership before returning scan data. It intentionally returns the same 404 for a nonexistent scan and a scan owned by someone else, avoiding resource-existence disclosure.
- Compliance and attack-path endpoints reuse `_load_owned_scan`; they do not implement a separate ownership check.

## Audit events

The existing `AuditLog` table is used without a schema migration. `auth.audit.log_event()` records an action, optional user ID, optional IP address, and the model's timestamp. Audit-write failures are logged and rolled back rather than intentionally crashing the protected request. Events include:

- `signup_success`
- `login_success` and `login_failure`
- `role_check_denied` (HTTP 403)
- `scan_access_denied` (HTTP 404 for missing/foreign scans)

Passwords, password hashes, JWTs, and cookie values must never be placed in audit actions.

## Verification

Run from `backend/` in the project's configured virtual environment:

```bash
pytest -q src/auth/tests/test_rbac.py
pytest -q tests/test_security.py
pytest -q
```

The security tests exercise Admin bootstrap through the test-only `ADMIN_EMAIL` environment variable, Viewer upload denial, and scan ownership across two separately signed-up users. Run the full suite after merging to catch regressions in existing scans, compliance, and attack-path behavior.

## Merge sequence

Keep role-annotation changes as separate pull requests, one router per PR, in this order: `src/routes.py`, `src/compliance/routes.py`, `src/attack_paths/routes.py`. Do not push directly to `main`. Pull the latest `main` after each merge.
