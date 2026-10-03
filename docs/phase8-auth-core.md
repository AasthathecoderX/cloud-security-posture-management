# Phase 8 — Authentication Core

## Member

Member 1 — Auth Core

## Objective

Replace the temporary development identity with real multi-user authentication.

The authentication system provides:

- user signup
- user login
- authenticated sessions
- JWT access tokens
- rotating refresh tokens
- password hashing with Argon2id
- httpOnly authentication cookies
- CSRF protection
- authenticated-user dependency
- logout/session clearing

---

# 1. Authentication Architecture

```text
Client
  |
  | POST /auth/login
  v
auth/routes.py
  |
  v
User lookup
  |
  v
verify_password()
  |
  v
Argon2id
  |
  v
create_access_token()
create_refresh_token()
  |
  v
httpOnly cookies