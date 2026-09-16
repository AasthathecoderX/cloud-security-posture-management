# Wave A Execution Guide
## Phase 4 (Live Cloud Integration) + Phase 5 (AI/ML Risk Scoring)

---

## 1. What Wave A Delivers

By the end of Wave A, the platform can:

- Scan a LocalStack-emulated AWS environment (S3, IAM, Security Groups)
- Normalize collected resources into a common schema
- Run them through the existing rule engine
- Persist scan results and findings to the database
- Score every finding with ML (risk score 0–100 + anomaly flag)
- Display Risk Score and Anomaly badges on the dashboard

This is a **4-person parallel workstream** with two frozen contracts acting as the seam between them.

---

## 2. Golden Rules (Why This Won't Deadlock)

1. **One owner per folder** — nobody edits another member's files. Shared interfaces are defined once and imported everywhere else.
2. **Contract before implementation** — the schemas below are frozen *before* coding starts. Members build against the contract, not against each other's progress.

---

## 3. The Two Frozen Contracts

### Contract A — M1 → M2: `collect_cloud_resources()`

```json
[
  {
    "resource_id": "",
    "resource_type": "",
    "configuration": {},
    "metadata": {}
  }
]
```
Used by M2 to feed the rule engine with normalized cloud resources.

### Contract B — M3 → M4: `score_findings(findings)`

```json
{
  "risk_score": 92,
  "is_anomaly": false
}
```
Used by M4 to populate `risk_score` and `is_anomaly` on each finding.

---

## 4. File Ownership Map

| Owner | Exclusive Ownership |
|-------|----------------------|
| **M1** | `backend/cloud/**` |
| **M2** | `backend/api/live_scan.py`, frontend live-scan UI |
| **M3** | `ml/**` |
| **M4** | `backend/ml/**`, dashboard risk UI |

No cross-folder edits. If a shared interface needs to change, it's a conversation, not a silent edit.

---

## 5. Member-by-Member Breakdown

### 🟦 Member 1 — Cloud Connector (Lead)

**Mission:** Build the full cloud collection layer — connect to LocalStack via boto3 and convert raw AWS resources into the common schema the rule engine already understands.

**Owns:**
```
backend/cloud/
├── collector.py
├── normalizer.py
├── localstack.py
└── resource_mapper.py
```

**Steps:**
1. Configure boto3 client
2. Connect to LocalStack
3. Read S3 resources
4. Read IAM resources
5. Read Security Groups
6. Normalize every resource into the common schema
7. Return standardized JSON (Contract A)
8. Write unit tests

**Deliverables:**
- Working collector
- Resource normalizer
- Unit tests
- Documentation

**Hands off to:** M2, via `collect_cloud_resources()` (Contract A)

---

### 🟩 Member 2 — Live Scan API + Frontend (Lead)

**Mission:** Turn M1's collector into an actual user-facing feature — an endpoint that scans, evaluates, stores, and a frontend page that surfaces it.

**Owns:**
```
backend/api/live_scan.py
backend/services/live_scan_service.py
frontend/src/features/live_scan/
```

**Steps:**
1. Create `POST /scans/cloud`
2. Call M1's collector
3. Run the existing rule engine on returned resources
4. Store the scan record
5. Store findings
6. Return scan response to frontend
7. Build the "Scan Cloud" page
8. Show scan history

**Deliverables:**
- Live Scan endpoint
- Frontend scan flow
- Database integration (scans + findings)

**Depends on:** M1's Contract A output
**Hands off to:** M3/M4 pipeline — findings stored in DB become the input for ML scoring

---

### 🟨 Member 3 — ML Models (Lead)

**Mission:** Build and train the AI models that will score findings for risk and flag anomalies.

**Owns:**
```
ml/
├── simulate_resources.py
├── mutate_iac.py
├── feature_engineering.py
├── train_xgboost.py
├── train_isolation_forest.py
├── benchmark.ipynb
└── model.joblib
```

> **Constraint (evaluator requirement):** no external dataset or third-party IaC module source may be used — not even as an unlabeled baseline. The full fleet, normal and anomalous, must come from our own generator code. See `Major Project Planning.md` §8.3.

**Steps:**
1. Generate baseline dataset (`simulate_resources.py` — self-generated resource JSON, no Terraform/external modules)
2. Mutate the simulated resources to create labeled anomalies
3. Engineer features (rule-correlated for XGBoost; behavioral/structural for Isolation Forest)
4. Train XGBoost (supervised risk scoring)
5. Train Isolation Forest (unsupervised anomaly/drift detection)
6. Export trained models via joblib
7. Produce a benchmark report (precision/recall/F1, feature importance, complementarity analysis)

**Deliverables:**
- Trained models (`model.joblib`)
- Benchmark report
- `score_findings()` interface (Contract B)

**Hands off to:** M4, via `score_findings(findings)` (Contract B)

---

### 🟧 Member 4 — Product Integration (Lead)

**Mission:** Wire M3's trained models into the live backend and surface the results on the dashboard.

**Owns:**
```
backend/ml/scorer.py
frontend/src/features/dashboard/
```

**Steps:**
1. Load the trained model
2. Score findings using `score_findings()`
3. Populate `risk_score` / `is_anomaly` fields in the database
4. Add a Risk Score column to the findings table/UI
5. Add an Anomaly badge
6. Add a Top Risks panel
7. Enable sorting by risk

**Deliverables:**
- ML fully integrated into the backend
- Dashboard updated with risk score, anomaly badge, and Top Risks panel

**Depends on:** M3's Contract B output + M2's stored findings

---

## 6. End-to-End Integration Flow

```
   M1 (Cloud Collector)
          │  Contract A: collect_cloud_resources()
          ▼
   M2 (Live Scan API)
          │  runs Rule Engine
          ▼
   Database (scans + findings)
          │
          ▼
   M3 (ML Models)
          │  Contract B: score_findings()
          ▼
   M4 (Dashboard Integration)
          │
          ▼
   Risk Score + Anomaly Badge visible in UI
```

**In words:** M1 collects raw cloud resources → normalizes them → hands off to M2, who runs them through the rule engine, stores the scan and findings in the database → those findings flow to M3's trained models for scoring → M4 pulls the scores back in, writes them to the DB, and renders them on the dashboard.

---

## 7. Development Timeline

| Days | Activity |
|------|----------|
| 1–2 | M1 builds collectors · M3 builds the simulated dataset pipeline |
| 3 | M1 publishes normalized schema (Contract A) · M3 publishes scoring interface (Contract B) |
| 4–7 | M2 builds the live scan feature · M4 integrates ML into the dashboard |
| 8–10 | Integration, testing, bug fixes |

Note the sequencing logic: **M1 and M3 front-load** because M2 and M4 are *consumers* of their contracts. Once the contracts are frozen on Day 3, M2 and M4 can build independently without blocking on M1/M3's internal implementation details.

---

## 8. Merge Order & Conflict Avoidance

**Why no merge conflicts happen:**
- Every member has a separate, exclusive folder
- Contracts are frozen before implementation begins
- Single ownership per file — no shared edit surface
- PRs merge in dependency order, and everyone rebases from `main` after each merge

**PR Order:**
1. M1 (collector — foundational, nothing depends on anything before it)
2. M3 (ML models — independent of M1/M2, can merge in parallel conceptually but goes second by convention)
3. M2 (live scan API — depends on M1's contract)
4. M4 (dashboard integration — depends on M3's contract and M2's stored findings)

---

## 9. Definition of Done

- [ ] Live cloud scan works end-to-end
- [ ] Rule engine correctly processes collected resources
- [ ] ML generates a risk score and anomaly flag for every finding
- [ ] Dashboard displays risk score and anomaly badge
- [ ] Unit tests pass (all members)
- [ ] Integration tests pass
- [ ] End-to-end demo succeeds: scan → findings → risk-scored → visible on dashboard

---

## 10. Context Note (from Major Project Plan)

This wave implements **Phase 4** and **Phase 5** of the broader 14–15 week roadmap:
- Phase 4 target output: a "Scan my cloud account" feature (read-only boto3 → LocalStack, feeding the existing rule engine)
- Phase 5 target output: a defensible ML layer — XGBoost for supervised risk prioritization, Isolation Forest for unsupervised fleet anomaly/drift detection — persisted via `risk_score` and `is_anomaly` fields on the `findings` table, integrated into the API and benchmarked (precision/recall/F1 + feature importance + anomaly-vs-rules complementarity).

Both phases are explicitly flagged in the master plan as **buffer-heavy** (Weeks 6–9) — expect ML training/tuning (M3) and cloud-edge-case handling (M1) to be the likely schedule risks.