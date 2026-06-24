# Phase 0 Threat Model

## Scope and assets

This sketch covers the browser, FastAPI service, PostgreSQL database, and the cloud-target boundary represented locally by LocalStack. Assets include user credentials, session tokens, uploaded cloud configuration, scan results, cloud-role metadata, audit logs, and service secrets.

## Trust boundaries

1. **Browser ↔ API:** untrusted clients and uploads cross into the application. Production traffic must use HTTPS, strict request validation, locked-down CORS, and secure httpOnly cookies.
2. **API ↔ Database:** the API crosses into persistent storage. Use TLS, parameterized queries, a least-privilege database role, and ownership filters on every user-scoped query.
3. **API ↔ Cloud target:** boto3 calls cross into LocalStack or AWS. Use read-only operations, an allowlisted endpoint, and short-lived STS credentials for real AWS.

## Primary threats and required controls

| Threat | Impact | Required control / acceptance condition |
| --- | --- | --- |
| Malicious JSON/YAML upload | Parser RCE, memory/CPU exhaustion | `yaml.safe_load` only; 2 MB size cap; content-type, extension, schema, nesting-depth, alias, and timeout limits |
| Broken access control / IDOR | One user reads or changes another user’s scans | Server-side RBAC and every data query scoped by authenticated `user_id`/`org_id`; test cross-user access |
| JWT theft or algorithm abuse | Account takeover | Pinned algorithm, short-lived access token, rotating refresh token, Secure/HttpOnly/SameSite cookies, CSRF protection; no localStorage tokens |
| Credential leakage | Database or cloud compromise | `.env` ignored, no secrets in logs or source, GitHub secret scanning and gitleaks, STS AssumeRole with external ID, dummy LocalStack keys only |
| SSRF through a cloud endpoint | Access to internal or metadata services | Endpoint allowlist; reject link-local, loopback, and private ranges except the explicitly configured LocalStack host |
| CORS misconfiguration | Unauthorized credentialed browser requests | Exact frontend origin; never combine wildcard origins with credentials |
| SQL injection | Data loss or disclosure | SQLModel/SQLAlchemy parameterization; no SQL string concatenation |
| Brute force and upload abuse | Account compromise or denial of service | Rate limits, generic login errors, bounded uploads, and audit events |
| Dependency or container compromise | Build/runtime takeover | Dependabot, pinned dependencies, CodeQL, Bandit, Semgrep, pip/npm audit, Trivy, and gitleaks in later CI |

## Security acceptance baseline

Before production deployment, verify the planning document’s security acceptance checklist: safe parsing and upload limits; server-side RBAC and tenant scoping; hardened JWT cookies and CSRF protection; no stored long-lived cloud keys; strict CORS and SSRF controls; parameterized queries; security scanning in CI; and TLS on all external connections.

## Out of scope for Phase 0

Phase 0 documents controls but does not implement authentication, uploads, rule evaluation, database models, or real AWS access. Those controls become testable as their features are introduced in later phases.
