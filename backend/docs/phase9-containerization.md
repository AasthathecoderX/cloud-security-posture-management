# Phase 9 — Containerization and Scheduled Self-Scan

## 1. Objective

This phase prepares the CSPM backend for production container execution and automates scheduled cloud-security scans through GitHub Actions.

The implementation covers:

* Running the backend as a non-root Linux user.
* Defining a production Docker Compose configuration.
* Connecting to managed PostgreSQL and hosted LocalStack.
* Automating authentication and live scans through the existing API.
* Keeping production secrets outside the repository.

## 2. Backend Dockerfile Hardening

The existing `backend/Dockerfile` installs Python dependencies, copies the application, and runs Alembic migrations before starting Uvicorn.

A dedicated system user named `cspm` is created and selected through the Dockerfile's `USER` directive.

### Verification

From the repository root:

```bash
docker build -t cspm-backend:phase9 ./backend
```

Verify the configured user:

```bash
docker image inspect cspm-backend:phase9 \
  --format '{{.Config.User}}'
```

Expected output:

```text
cspm
```

The image must also start successfully, complete database migrations, and respond to the `/health` endpoint.

## 3. Production Docker Compose

The production configuration is maintained separately at:

`infra/docker-compose.prod.yml`

It defines:

* `backend`: the FastAPI application.
* `localstack`: the emulated cloud environment used for live scans.
* `localstack_data`: persistent LocalStack storage.

Unlike the development Compose configuration, the production configuration does not create a local PostgreSQL container. The backend connects to managed PostgreSQL using `DATABASE_URL`.

The configuration retains the read-only rules mount:

```text
../rules:/rules:ro
```

Production environment values are supplied through `.env.production` on the deployment host. This file must not be committed to Git.

### Deployment verification

```bash
docker compose \
  -f infra/docker-compose.prod.yml \
  config
```

After configuring the production environment and required services:

```bash
docker compose \
  -f infra/docker-compose.prod.yml \
  up --build -d
```

Check service health and the API endpoint:

```bash
docker compose \
  -f infra/docker-compose.prod.yml \
  ps

curl --fail http://localhost:8000/health
```

Expected API response:

```json
{"status":"ok"}
```

## 4. Scheduled Cloud Security Scan

The workflow is located at:

`.github/workflows/scheduled-scan.yml`

It runs daily at 02:17 UTC and supports manual execution through `workflow_dispatch`.

### Workflow sequence

1. Validate the backend URL and required GitHub Actions configuration.
2. Send `GET /auth/me` to initialize the CSRF cookie.
3. Authenticate using `POST /auth/login`.
4. Preserve the session cookies and CSRF token.
5. Trigger `POST /scans/cloud`.
6. Fail the workflow if authentication or scanning fails.
7. Report the scan result without printing credentials or authentication tokens.

### Required GitHub Actions configuration

* `CSPM_API_BASE_URL`: repository variable containing the deployed backend base URL.
* `CSPM_SCAN_EMAIL`: secret containing the dedicated service account email.
* `CSPM_SCAN_PASSWORD`: secret containing its password.

The account must already exist and have the Admin role. Its email must match the backend's configured `ADMIN_EMAIL`.

The workflow reuses the existing authentication, CSRF, and role-based access-control mechanisms. It does not introduce a new authentication method.

## 5. Security Considerations

* Never commit production secrets or `.env.production`.
* Do not embed database credentials or JWT secrets in Docker image layers.
* Run the backend as a non-root user.
* Preserve the read-only rules mount.
* Keep LocalStack's dummy credentials separate from real AWS credentials.
* Do not bypass authentication, CSRF checks, or Admin authorization to make automation pass.
* Ensure failed scheduled scans produce a failed workflow run.
* Keep the production Compose file separate from the development Compose configuration.

## 6. Verification Checklist

* [ ] Backend image builds successfully.
* [ ] Image runs as the `cspm` user.
* [ ] Database migrations succeed under the non-root user.
* [ ] Backend health endpoint responds successfully.
* [ ] Production Compose configuration validates.
* [ ] Backend connects to managed PostgreSQL.
* [ ] LocalStack becomes healthy and remains reachable.
* [ ] Rules are available through the read-only mount.
* [ ] Scheduled workflow authenticates using the service account.
* [ ] Successful scan results are reported.
* [ ] Invalid credentials cause the workflow to fail.
* [ ] The workflow completes an unattended scheduled run.
* [ ] Production secrets remain outside version control.

## 7. Handoffs

**Member 4 — CI/CD Security Pipeline:** Provide the Docker build command and image tag so the security pipeline can build and scan the image with Trivy.

**Member 3 — Backend and Database Deployment:** Coordinate the production Compose file. Member 1 creates the initial structure; Member 3 subsequently supplies the final Neon database configuration, production CORS origin, and deployment integration.

The scheduled workflow can be developed and tested against the local stack, but final production verification requires the deployed backend and provisioned service account.

## 8. Completion Criteria

Containerization and scheduled self-scan work is complete when the backend runs as a non-root user, the production Compose configuration works without a local PostgreSQL service, and the scheduled workflow successfully authenticates and performs a scan without manual intervention.
