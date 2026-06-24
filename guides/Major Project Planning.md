# AI-Powered Cloud Security Posture Management (CSPM) Platform

### Major Project Documentation — v2 (Hardened & Finalized)

---

## 1. Project Description

This project is a full-stack cybersecurity platform that analyzes both live cloud environments (emulated) and uploaded cloud configuration files (JSON/YAML/Terraform plan JSON) to:

1. **Detect misconfigurations** using a declarative, benchmark-mapped rule engine.
2. **Prioritize and score risk** using a defensible machine-learning layer (anomaly + drift detection, plus supervised risk scoring).
3. **Visualize attack paths** — how individual findings chain into real, exploitable routes from public exposure to sensitive data.
4. **Map findings to compliance frameworks** (CIS, NIST CSF) with concrete remediation guidance.
5. **Secure itself** — the platform is built to OWASP ASVS / OWASP Top 10 standards, not just the things it scans.

It demonstrates **end-to-end competency** across cloud computing, cybersecurity, AI/ML, full-stack web development, and DevOps — each domain backed by a real, working component.

---

## 2. SDG Goals Covered

| SDG Goal | How This Project Addresses It |
| ----- | ----- |
| **SDG 9 — Industry, Innovation and Infrastructure** | Builds intelligent tooling that strengthens the resilience and security of digital cloud infrastructure, now foundational to nearly all industries. |
| **SDG 16 — Peace, Justice and Strong Institutions** | Improves cybersecurity posture and reduces unauthorized-access risk, protecting digital systems institutions and governments depend on. |
| **SDG 8 — Decent Work and Economic Growth** | Reduces breach/cyberattack risk that disrupts businesses, protecting jobs and economic activity built on digital infrastructure. |

---

## 3. Complete Tech Stack (Finalized, 100% Free)

| Layer | Technology | Purpose / Notes |
| ----- | ----- | ----- |
| **Frontend** | React.js, Tailwind CSS | Modular dashboard UI |
| **Data Visualization** | Recharts, React Force Graph | Metrics/severity charts; force-directed attack-path canvas |
| **Backend** | Python 3.11+, FastAPI, Pydantic v2 | Async REST API; strict payload validation |
| **AI/ML** | Scikit-learn (Isolation Forest), XGBoost, pandas | Fleet anomaly/drift detection + supervised risk scoring (see §8 for the *defensible* framing) |
| **Graph Logic** | NetworkX | Topological asset modeling, attack-path computation |
| **Database & ORM** | PostgreSQL (Neon free tier) + SQLModel/SQLAlchemy; SQLite for local dev | Users, scans, findings, compliance |
| **Cloud Target** | boto3 + LocalStack Community (S3, EC2/VPC, IAM read) | Zero-cost AWS emulation. Read-only config collection |
| **Auth & Crypto** | PyJWT, **pwdlib[argon2]** (NOT passlib), python-dotenv | JWT sessions, Argon2id password hashing, env-based secrets |
| **Security Tooling (CI)** | Bandit, Semgrep, pip-audit, npm audit, CodeQL, Dependabot, gitleaks, Trivy | Self-scanning the platform (also doubles as a project feature) |
| **DevOps** | Docker, Docker Compose, GitHub Actions | Containerization, CI/CD, scheduled scans |
| **Deployment** | Vercel (frontend) + **Oracle Cloud Always Free VM** (backend + LocalStack) — fallback: Render/Fly.io/Koyeb/HF Spaces for static-only | See §6 deployment strategy |
| **IaC Parsing** | python-hcl2, plus `terraform plan → terraform show -json` | Resolved Terraform state for the ML dataset |
| **Config Parsing** | PyYAML (`safe_load` only), json | Secure parsing of uploaded configs |
| **Compliance Source** | CIS Benchmarks (control IDs only), NIST CSF (public domain) | Rule and compliance mapping |
| **Version Control** | Git, GitHub | Source control, collaboration |

**Cost guarantee:** Every component above has a permanently free tier or is open source. No paid LLM APIs, no paid cloud spend, no trial-expiry dependencies.

---

## 4. What Changed From v1 (and Why)

| v1 Problem | v2 Fix |
| ----- | ----- |
| **ML claim was circular** — anomalies were injected using the exact patterns the rules already catch, so "ML catches what rules miss" was tautological and indefensible. | Reframed ML into **(a) supervised risk *prioritization*** and **(b) unsupervised fleet anomaly/drift detection** on features that are *not* direct rule triggers. See §8. |
| **Live scan couldn't run in the free hosted deployment** (LocalStack needs Docker; Vercel/Render free tiers can't host it). | Backend + LocalStack run on **Oracle Cloud Always Free VM** (24/7 Docker). Hosted demo does live scan end-to-end; static upload works everywhere. See §6. |
| **`passlib` is unmaintained** and broke with bcrypt 4.x. | Switched to **`pwdlib` with Argon2id**. |
| **Security section was thin** — no defense against YAML RCE, IDOR, JWT abuse, credential theft, SSRF, CORS. | Full hardened security design in §9, mapped to OWASP. |
| **HCL parsing gave unresolved variables**, breaking dataset realism. | Use **`terraform plan → terraform show -json`** for resolved state. See §8. |
| **Stored long-lived AWS credentials** (huge breach risk). | **No stored keys.** STS AssumeRole + external ID + read-only `SecurityAudit` policy. LocalStack uses dummy creds. |
| Scheduled scans had **no hosted target**. | Cron targets the **hosted LocalStack on the Oracle VM**. |

---

## 5. Refined Core System Architecture

```
                 +---------------------------------------+
                 |           React Frontend              |
                 |  (Tailwind + Recharts +               |
                 |        React Force Graph)             |
                 +-------------------+-------------------+
                                     |
                          HTTPS      |  JSON + JWT (httpOnly cookie)
                       REST Calls    |  CORS locked to frontend origin
                                     v
                 +---------------------------------------+
                 |         FastAPI Backend Engine        |
                 |  PyJWT Auth + RBAC + Rate Limiting    |
                 |  Pydantic validation on every route   |
                 +---------+-------------------+---------+
                           |                   |
       Read / Write        |                   | Invoke Scan /
       Scan Data           |                   | Parse Data
                           v                   v
+-----------------------------+     +---------------------------------------+
|      Neon PostgreSQL        |     |        Core Processing Layer          |
| (Users, Scans, Findings,    |     |  1. Config Parser & Rule Engine       |
|  Compliance, Audit Log)     |     |     (yaml.safe_load, CIS-mapped YAML) |
+-----------------------------+     |  2. ML Risk Scorer & Anomaly Detector |
                                    |     (XGBoost + Isolation Forest)      |
                                    |  3. Graph Engine (NetworkX)           |
                                    +-----------------+---------------------+
                                                      | boto3 (read-only)
                                                      v
                                    +---------------------------------------+
                                    |   Cloud Target Layer                  |
                                    | AWS Emulation via LocalStack/Docker   |
                                    | (S3, EC2/VPC, IAM read)               |
                                    +---------------------------------------+
```

**Trust boundaries:** (1) Browser↔API over HTTPS with httpOnly cookies; (2) API↔DB over TLS with least-privilege DB user; (3) API↔Cloud over read-only STS role / dummy LocalStack creds. Uploaded files are treated as **fully untrusted** at the parser boundary.

---

## 6. Deployment Strategy (Resolves the Live-Scan Gap)

**Primary (full feature) deployment:**
- **Frontend:** Vercel (free, global CDN, auto HTTPS).
- **Backend + LocalStack + scheduled cron:** **Oracle Cloud Always Free** VM (Ampere ARM, 24 GB RAM free — easily runs Docker Compose with FastAPI + LocalStack + Postgres). Caddy/nginx for TLS via Let's Encrypt.
- **Database:** Neon free tier (managed Postgres) or Postgres container on the same VM.

**Fallback (static-upload-only) deployment** (if Oracle VM is unavailable):
- Frontend on Vercel, backend on **Fly.io / Koyeb / Hugging Face Spaces** (free). Live LocalStack scan is then **demoed locally**; document this clearly. Static config upload still works fully in the hosted version.

**Result:** The "live cloud scan" feature works end-to-end in at least one fully-free hosted configuration, and the scheduled-scan ("the *continuous* in CSPM") has a real target.

---

## 7. Phase-Wise Development Plan

### Phase 0 — Planning & Setup
**Goal:** Lock scope, design architecture, set up environment.
**Features:** Requirement doc, architecture diagram, DB schema, GitHub repo with branch protection + secret scanning (gitleaks) enabled from day one.
**Tech:** Git, GitHub, draw.io/Excalidraw.
**Output:** Architecture doc, repo skeleton, README, `.gitignore` (with `.env`), threat-model sketch.

### Phase 1 — Core Rule-Based Detection Engine
**Goal:** Build the misconfiguration detector.
**Features:** Securely parse JSON/YAML (`yaml.safe_load`, size/depth/timeout limits); detect public storage access, open security-group rules (`0.0.0.0/0`), wildcard IAM principals/actions, weak policies — each mapped to a CIS control ID via a **declarative YAML rule format** (§11).
**Tech:** Python, PyYAML, json, declarative rules.
**Output:** Importable rule-engine module + good/bad test fixtures + unit tests.

### Phase 2 — Backend API & Database
**Goal:** Expose the engine and persist results securely.
**Features:** Upload endpoint (with file validation), scan-results endpoint, findings history, user/org model. **Every endpoint enforces auth + RBAC + per-user data scoping** (no IDOR).
**Tech:** FastAPI, Pydantic, SQLModel, Neon/SQLite, slowapi (rate limiting).
**Output:** REST API with Swagger docs, migrations (Alembic), connected DB.

### Phase 3 — Frontend Dashboard (v1)
**Goal:** Visualize findings.
**Features:** Upload UI, findings list, severity badges, charts (by severity/category). Tokens stored in **httpOnly cookies**, not localStorage.
**Tech:** React, Tailwind, Recharts.
**Output:** End-to-end flow: upload → findings on dashboard.

### Phase 4 — Live Cloud Integration
**Goal:** Real (emulated) cloud scanning.
**Features:** Connect to LocalStack via boto3 (read-only); pull S3 ACLs/policies, security groups, IAM policies; run the same rule engine. Endpoint allowlisting to prevent SSRF.
**Tech:** boto3, LocalStack, Docker.
**Output:** "Scan my cloud account" feature alongside upload.

### Phase 5 — AI/ML Risk Scoring & Anomaly Detection
**Goal:** A genuine, measurable, **defensible** ML layer (see §8 for the full strategy).
**Features:** Synthetic dataset via mutation of resolved Terraform state; train Isolation Forest (fleet anomaly/drift) + XGBoost (risk prioritization); composite 0–100 risk score per resource.
**Tech:** Scikit-learn, XGBoost, pandas, Google Colab (free training).
**Output:** Model integrated into API + benchmark report (precision/recall, feature importance, anomaly-vs-rules complementarity analysis).

### Phase 6 — Attack-Path Visualization
**Goal:** Show how findings chain into exploitable paths.
**Features:** Model resources/relationships as a graph (instance → role → permission → data store); compute paths from public exposure to sensitive assets; interactive render.
**Tech:** NetworkX (backend), React Force Graph (frontend).
**Output:** Interactive attack-path view (node/link JSON in §13).

### Phase 7 — Compliance Mapping & Remediation
**Goal:** Standards-based, actionable guidance.
**Features:** Map findings to CIS/NIST controls; per-framework pass/fail status; remediation text from a **self-authored static knowledge base** (no paid LLM).
**Tech:** CIS control IDs, NIST CSF, curated remediation dataset.
**Output:** Compliance tab with framework-mapped status + fixes.

### Phase 8 — Authentication & Secure System Design
**Goal:** Make the platform itself secure (see §9).
**Features:** Signup/login, Argon2id hashing, JWT (httpOnly cookies, pinned alg, short expiry + refresh), RBAC (Admin/Viewer) enforced server-side, env-based secrets, **no stored cloud keys** (STS AssumeRole + external ID), audit logging, rate limiting, CORS lockdown.
**Tech:** PyJWT, pwdlib[argon2], python-dotenv, slowapi.
**Output:** Hardened multi-user platform passing an OWASP ASVS L1 checklist.

### Phase 9 — DevOps: Containerization & CI/CD + Self-Scanning
**Goal:** Deployable, continuously scanning, continuously self-audited.
**Features:** Dockerize frontend/backend; GitHub Actions for tests + **security scans (Bandit, Semgrep, pip-audit, npm audit, CodeQL, Trivy, gitleaks)** + deploy; scheduled scans via cron against hosted LocalStack.
**Tech:** Docker, Docker Compose, GitHub Actions.
**Output:** One-command setup, CI/CD with security gates, scheduled scan job.

### Phase 10 — Deployment
**Goal:** Publicly accessible working version.
**Features:** Deploy per §6; production DB; TLS; locked CORS.
**Tech:** Vercel + Oracle Cloud Always Free (+ Neon).
**Output:** Live URL for demo/evaluation.

### Phase 11 — Testing, Documentation & Final Report
**Goal:** Polish and prepare for defense.
**Features:** Unit + integration + security tests; user guide; threat model write-up; final report; demo script.
**Tech:** Pytest, httpx, Markdown/Word.
**Output:** Final report, demo-ready app, presentation deck.

---

## 8. ML Strategy (Defensible — Replaces the Circular v1 Approach)

### 8.1 The problem with v1
v1 generated "anomalies" by injecting the very patterns the rules already detect (wildcard principal, `0.0.0.0/0`, public flags). A rules-vs-ML comparison was therefore meaningless — the ML just relearned the rules. **This must be reframed to survive a viva.**

### 8.2 The two defensible ML jobs

**Job A — Supervised Risk *Prioritization* (XGBoost).**
Rules answer *"is this wrong?"*; XGBoost answers *"how dangerous is this, relative to everything else?"* — producing a calibrated 0–100 score and **feature-importance** breakdowns. This is a real, demonstrable value-add even where rules already fire, because it *ranks* and *explains* findings.

**Job B — Unsupervised Fleet Anomaly / Drift Detection (Isolation Forest).**
Trained on features that are **NOT direct rule triggers** — e.g., `attached_policies_count`, `tag_entropy`, `resource_relationship_degree` (from the NetworkX graph), `policy_statement_count`, `cross_resource_reference_count`. This surfaces resources that are *statistically unusual vs. the fleet baseline* even when **no rule fires** — the honest, defensible version of "catches what rules miss" (configuration drift / odd-combination detection).

### 8.3 Dataset generation (corrected)

1. **Golden Baseline (90%):** Take production-grade `terraform-aws-modules` (VPC, S3, IAM, Security Groups). **Run `terraform plan -out=tfplan` then `terraform show -json tfplan`** to obtain **fully resolved** resource state (NOT raw HCL, which leaves variables unresolved). These form the "Normal" cluster.
2. **Mutated Anomalies (10%):** A `mutate_iac.py` script injects structural variations (swap CIDRs to `0.0.0.0/0`, flip bucket privacy, insert wildcard IAM) — used **only for the supervised XGBoost label set**, never as the sole basis for the unsupervised model.
3. **Feature Matrix:** Convert each resource into numeric rows. Split features into:
   - *Rule-correlated features* (used by XGBoost): `open_ports_count`, `has_wildcard_principal`, `is_publicly_accessible`.
   - *Behavioral/structural features* (used by Isolation Forest): `attached_policies_count`, `tag_entropy`, `relationship_degree`, `policy_statement_count`.

### 8.4 Training & honest evaluation
- **XGBoost:** train on label `y` (0=Normal, 1=Anomaly) with `scale_pos_weight` for the 90/10 imbalance. Report precision/recall/F1 + feature importance.
- **Isolation Forest:** target dropped; train on behavioral features only. Evaluate by **complementarity**: how many *non-rule-violating* resources it flags that a human agrees are unusual (qualitative + a small hand-labeled validation set).
- **Defense narrative:** "Rules catch known-bad; XGBoost prioritizes and explains; Isolation Forest surfaces statistically anomalous configs rules never encoded." No circular claim.

---

## 9. Security Design — Hardened (Closes Every Hole)

Mapped to **OWASP Top 10 / OWASP ASVS L1**. This is the "iron-clad" core.

### 9.1 Input & parser security (untrusted uploads)
- **YAML RCE:** use `yaml.safe_load` ONLY — never `yaml.load`. (Prevents arbitrary object construction / RCE.)
- **DoS protection:** enforce max file size (e.g., 2 MB), max nesting depth, and a parse timeout. Reject YAML aliases/anchors abuse (billion-laughs) and deep JSON (depth-bomb).
- **Validation:** strict `Content-Type`, extension allowlist (`.json/.yaml/.yml`), schema validation via Pydantic before processing.

### 9.2 AuthN / AuthZ
- **Passwords:** Argon2id via `pwdlib`. Per-user salt (built in). No plaintext, ever.
- **JWT:** pin algorithm (e.g., HS256/RS256) — **reject `alg: none`** and HS/RS confusion. Short access-token expiry (15 min) + rotating refresh token. Secret only in env.
- **Token storage:** **httpOnly + Secure + SameSite=Strict cookies**, NOT localStorage (defeats XSS token theft). Include CSRF protection (double-submit token) since cookies are used.
- **RBAC:** Admin vs Viewer enforced **server-side on every endpoint** via FastAPI dependencies — never trust the frontend.
- **IDOR prevention:** every query filters by the authenticated `user_id`/`org_id`. UUID scan/finding IDs are NOT a substitute for authorization checks.
- **Anti-abuse:** rate-limit login & upload (`slowapi`); generic error messages to prevent **user enumeration**; optional lockout/backoff.

### 9.3 Cloud credential handling
- **No long-lived AWS keys stored.** For real AWS: **STS AssumeRole with an external ID** + read-only managed policy `SecurityAudit`. For LocalStack: dummy creds in env only.
- Credentials/secrets never logged.

### 9.4 Network & transport
- **HTTPS everywhere** (TLS via Vercel / Let's Encrypt).
- **CORS** locked to the exact frontend origin (no `*` with credentials).
- **SSRF protection:** if a scan target endpoint is user-supplied, **allowlist** it; block internal/link-local ranges (169.254.0.0/16, 127.0.0.0/8, RFC1918) unless explicitly the LocalStack host.

### 9.5 Data & query security
- **SQL injection:** SQLModel/SQLAlchemy parameterized queries only; no raw string SQL.
- **Least-privilege DB user**; TLS to Neon.
- **Audit log** table for auth events and admin actions.

### 9.6 Secrets & supply chain
- `.env` gitignored; secrets in **GitHub Actions Secrets**.
- **gitleaks** in CI to block committed secrets.
- **Dependabot + pip-audit + npm audit** for vulnerable deps; **Trivy** for container image CVEs.

### 9.7 Static analysis (dogfooding)
- **Bandit** (Python SAST), **Semgrep**, **CodeQL** run in CI on every PR — the platform's own pipeline demonstrates secure SDLC and feeds the project narrative.

### 9.8 Compliance/licensing hygiene
- Reference **CIS control IDs only** (CIS text is registration-gated and redistribution-restricted). **NIST CSF** is public domain and may be quoted.

---

## 10. Core Database Schema

### users
- `user_id` (UUID, PK)
- `email` (String, Unique)
- `password_hash` (String, Argon2id)
- `role` (Enum: Admin / Viewer)
- `created_at` (DateTime)

### scans
- `scan_id` (UUID, PK)
- `user_id` (FK → users.user_id)
- `scan_type` (Enum: Static / Live)
- `timestamp` (DateTime)
- `status` (Enum: In_Progress / Completed / Failed)

### findings
- `finding_id` (UUID, PK)
- `scan_id` (FK → scans.scan_id)
- `resource_id` (String — e.g., ARN)
- `resource_type` (String — e.g., AWS::S3::Bucket)
- `severity` (Enum: Low / Medium / High / Critical)
- `rule_id` (String → compliance_map.rule_id)
- `risk_score` (Int 0–100 — from XGBoost)
- `is_anomaly` (Boolean — from Isolation Forest)

### compliance_map (Static Metadata)
- `rule_id` (String, PK)
- `cis_control_id` (String)
- `nist_id` (String)
- `remediation_steps` (Text)

### audit_log (Security)
- `event_id` (UUID, PK)
- `user_id` (FK, nullable)
- `action` (String — e.g., LOGIN_SUCCESS, LOGIN_FAIL, ROLE_CHANGE)
- `ip_address` (String)
- `timestamp` (DateTime)

---

## 11. Declarative Rule Engine Format

Rules are data, not code — expand the framework without touching application logic.

```yaml
rule_id: "RULE_AWS_S3_001"
name: "S3 Bucket Public Read Access"
severity: "CRITICAL"
compliance:
  cis_aws: "2.1.1"
  nist_csf: "PR.DS-5"
condition:
  resource_type: "AWS::S3::Bucket"
  eval_path: "Policy.Statement.Effect"
  equals: "Allow"
  and_path: "Policy.Statement.Principal"
  contains: "*"
remediation: "Block public read access or apply S3 Block Public Access settings."
```

---

## 12. ML Dataset Pipeline (Summary)

1. **Resolve:** `terraform plan` → `terraform show -json` on `terraform-aws-modules` → resolved JSON state (Golden Baseline, 90%).
2. **Mutate:** `mutate_iac.py` injects misconfigs → labeled anomalies (10%) for XGBoost.
3. **Featurize:** rule-correlated features → XGBoost; behavioral/structural features → Isolation Forest.
4. **Train:** Colab (free). Persist models (`joblib`) into the API.
5. **Evaluate:** precision/recall/F1 + feature importance (XGBoost); complementarity analysis (Isolation Forest).

---

## 13. Attack-Path Visualization Payload

```json
{
  "nodes": [
    {"id": "node1", "label": "Internet Gateway", "type": "network", "severity_score": 0},
    {"id": "node2", "label": "EC2 Web Server (Open Ingress)", "type": "compute", "severity_score": 85},
    {"id": "node3", "label": "S3 Customer Data Store", "type": "storage", "severity_score": 95}
  ],
  "links": [
    {"source": "node1", "target": "node2", "relation": "Public Traffic Ingress"},
    {"source": "node2", "target": "node3", "relation": "IAM Over-Privileged Access"}
  ]
}
```

---

## 14. Suggested Timeline (14–15 weeks)

| Phase | Focus | Duration |
| ----- | ----- | ----- |
| 0 | Planning & Setup | Week 1 |
| 1 | Rule-Based Engine | Weeks 2–3 |
| 2 | Backend API & DB | Weeks 3–4 |
| 3 | Dashboard v1 | Weeks 4–5 |
| 4 | Cloud Integration | Weeks 6–7 |
| 5 | AI/ML Layer *(buffer-heavy)* | Weeks 7–9 |
| 6 | Attack-Path Visualization *(buffer-heavy)* | Weeks 9–10 |
| 7 | Compliance Mapping | Weeks 10–11 |
| 8 | Auth & Secure Design | Week 11 |
| 9 | DevOps / CI-CD + Self-Scanning | Week 12 |
| 10 | Deployment | Week 13 |
| 11 | Testing & Documentation | Weeks 14–15 |

*Phases 5 and 6 are the hardest — keep slack there.*

---

## 15. Expected Final Outcomes

- Detection of real cloud misconfigurations across emulated live accounts and uploaded configs.
- **Defensible** ML: supervised risk prioritization + unsupervised fleet anomaly detection, with measured, honestly-framed value.
- Interactive dashboard: severity, attack-path, and compliance views.
- CIS/NIST-mapped compliance reporting with remediation guidance.
- Fully deployed, **hardened (OWASP-aligned)**, multi-user, continuously-scanning, self-auditing web application.
- A defensible project spanning cloud, AI/ML, cybersecurity, full-stack, and DevOps — at **zero cost**.

---

## 16. Security Acceptance Checklist (Must All Pass Before "Done")

- [ ] All YAML parsed with `safe_load`; size/depth/timeout limits enforced.
- [ ] Passwords hashed with Argon2id (pwdlib); no plaintext anywhere.
- [ ] JWT algorithm pinned; `alg:none` rejected; tokens in httpOnly+Secure+SameSite cookies; CSRF protection present.
- [ ] RBAC enforced server-side on every endpoint; all queries scoped by `user_id` (no IDOR).
- [ ] No long-lived cloud keys stored; STS AssumeRole + external ID (or LocalStack dummy creds).
- [ ] CORS locked to frontend origin; HTTPS enforced; SSRF allowlist in place.
- [ ] Rate limiting on auth/upload; generic errors (no user enumeration).
- [ ] Parameterized DB queries only; least-privilege DB user; audit log active.
- [ ] `.env` gitignored; secrets in CI secrets; gitleaks passing.
- [ ] CI green on Bandit, Semgrep, CodeQL, pip-audit, npm audit, Trivy, Dependabot.
- [ ] Only CIS control IDs referenced (no benchmark text redistributed).

---

## 17. Possible Future Scope

- Multi-cloud support (Azure, GCP) beyond AWS.
- Real-time alerting (email / Slack webhook on critical findings).
- IaC scanning integration (Terraform plan files in CI).
- Multi-tenant SaaS with org-level dashboards.
- Optional self-hosted open-source LLM (e.g., via Ollama, still free) for natural-language remediation summaries.
