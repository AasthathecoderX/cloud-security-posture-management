# Wave B — Phase 6 (Attack-Path) + Phase 7 (Compliance)

Goal: show **how findings chain into attack paths**, and map findings to **CIS/NIST controls with remediation guidance**. Team: 4 members. Assumes **Wave A is merged to `main`** (live cloud connector at its Phase-4 scope of S3/IAM/Security Groups, and the ML risk-scoring contract wired end-to-end).

By the end: **scan → findings → attack paths + compliance status + remediation**, with the attack-path backend feeding an interactive graph and the compliance backend feeding a dedicated Compliance tab.

---

### Day 0–2 prerequisite: extend the collector for relationship data

**Owner: M3.** This is additive-only work on top of Wave A's already-merged `backend/src/cloud/` module (Wave A is closed out by the time Wave B starts, so there's no active branch to conflict with — M3 adds new functions, doesn't touch M1's originals).

Add to `backend/src/cloud/collector.py`:
- `collect_ec2_instances()` — `describe_instances()`, normalized to a new `ec2_instance` resource type (public/private IP, security-group attachment, IAM instance-profile ARN if present).
- `collect_iam_role_attachments()` — for each role, `list_attached_role_policies()` / `list_instance_profiles_for_role()`, producing the **edges** (`ASSUMES`, `HAS_PERMISSION`) the graph needs, not just more nodes.

Add corresponding mappers to `backend/src/cloud/resource_mapper.py` (`map_ec2_instance`, `map_role_attachment`) following the existing `map_s3_bucket` / `map_security_group` pattern, and wire both into `CloudCollector.collect()`.

**Deliverable:** `collect_cloud_resources()` Contract A output now includes `ec2_instance` nodes and attachment edges, in the same flat list shape the rule engine already consumes. Unit tests follow the existing `test_cloud_connector.py` per-resource-type pattern (including a per-policy-style resilience test — one unreadable instance/role shouldn't kill the whole collection, matching the fix already made to `collect_iam_resources`).

If this slips, **descope Phase 6 to what's actually collectable** (e.g., security-group → exposure edges only) rather than let M3/M4 build a graph UI with nothing real to render — this is a go/no-go check at the end of Day 2, not a hope.

---

## The two rules that prevent conflicts and deadlocks

**1. No conflicts — one owner per folder/file.** Each member owns a separate implementation area. No two members edit the same implementation file. Shared contracts are created once and imported read-only.

**2. No deadlocks — contract + mocks first.** M1 publishes the compliance API contract and mock response. M3 publishes the attack-path API contract and mock response. M2 and M4 build against those contracts rather than waiting for the backend.

> Dependency shape is a tree, not a cycle:
>
> - M1 → M2 for Compliance
> - M3 → M4 for Attack Path
>
> The two branches are independent. **Compliance doesn't depend on the Day 0–2 prerequisite above at all** — M1/M2 can start immediately.

---

## File-ownership map

> **Changed from the original draft:** paths corrected to match the real repo layout — backend code lives under `backend/src/` (bare imports like `from db import get_session`, not `from src.db import`), the same deviation Wave A's M1 already made once (`backend/cloud/` in that plan vs. the actual `backend/src/cloud/`). Written correctly up front this time instead of drifting silently again.

| Owner | Folder / files (exclusive) |
| --- | --- |
| **Member 1 — Compliance Engine** | `backend/src/compliance/**`, extending the existing `seed_compliance_map` migration, compliance tests |
| **Member 2 — Compliance Tab** | `frontend/src/features/compliance/**` |
| **Member 3 — Attack-Path Graph** | `backend/src/cloud/collector.py` / `resource_mapper.py` (additive, Day 0–2 only), `backend/src/attack_paths/**`, attack-path tests |
| **Member 4 — Attack-Path Visualization** | `frontend/src/features/attack_paths/**` |

> **Frontend convention, declared explicitly:** Phase 3 kept `frontend/src/pages/` for the original list/detail/upload flows (its own "Structure note" says so), and Dashboard was the first feature built under `frontend/src/features/<name>/`. Compliance and Attack-Path are the same kind of thing Dashboard is — a new visual/interactive view layered onto existing scan data, not a CRUD list/detail page — so they continue the `features/` convention Dashboard started, on purpose rather than by accident.

### Two files are genuinely shared — here's how they stay conflict-free

The original draft said *"if a shared routing or registration file must change, designate one owner before editing it"* without saying which file or who. Concretely, two files are touched by two different members each:

**`backend/src/main.py`** — M1 and M3 each add one `app.include_router(...)` line for their own feature's router (see Shared Contracts below — each feature gets its **own** `APIRouter`, so `routes.py` itself is never touched by Wave B at all). The commit order (M1 → M3 → M2 → M4, unchanged from the original) already sequences these as two independent single-line additions, not a simultaneous edit — no conflict as long as everyone rebases after each merge, per the existing workflow.

**`frontend/src/pages/ScanDetailPage.tsx`** — needs a tab nav (`Findings / Attack Paths / Compliance`) both M2 and M4 hook into. **M2 builds the shared tab-nav shell** as part of adding the Compliance tab (M2 merges third in the existing order); **M4 rebases onto that and adds its own tab entry** afterward (M4 merges fourth). Same sequencing solves it — M4 should not start this file until M2's PR is in `main`.

---

# Order of work

### Day 0–2 — Prerequisite + contracts + scaffolding

**M3**
- Collector extension (above).
- Finalize Attack-Path node/link schema once instance/role data exists.
- Create mock attack-path responses.

**M1**
- Finalize Compliance response schema.
- Confirm CIS/NIST mapping fields against the existing `compliance_map` table.
- Create mock compliance responses.

**M2 + M4**
- Scaffold feature folders under `frontend/src/features/`.
- Build page shells against mocks.

### Day 3–6 — Parallel implementation

**M3**
- Build the NetworkX graph from the now-extended resource data.
- Derive attack paths with a bounded search (see Guardrails).
- Implement `GET /scans/{id}/attack-paths` as its own router.

**M1**
- Build the compliance aggregation query (see Contract 1 — this reuses the existing `Finding.compliance` relationship, it does not re-derive the mapping).
- Add the missing-seed-row acceptance check (see Guardrails).
- Populate `remediation_steps` content for every seeded rule.

**M2**
- Build the Compliance tab (+ shared `ScanDetailPage` tab nav) against M1's mocks.

**M4**
- Build the Force Graph against M3's mocks.

### Day 7–8 — Real integration

- Replace mocks with real APIs.
- Test real scan IDs, including a scan with EC2 + role data present.
- Fix contract drift.

### Day 9–10 — E2E + polish

- Attack-path E2E.
- Compliance E2E.
- Accessibility/UI pass.
- Tests and documentation.
- Final Wave B sign-off.

---

# Shared Contract 1 — Compliance API

Member 1 publishes this contract; Member 2 codes to it. Implemented as its own `APIRouter` in `backend/src/compliance/routes.py`, included from `main.py` — never edits the existing `routes.py`.

## Endpoint

`GET /scans/{scan_id}/compliance`

## Response

```json
{
  "scan_id": "123",
  "frameworks": {
    "CIS": { "passed": 3, "failed": 2, "total": 5 },
    "NIST": { "passed": 3, "failed": 2, "total": 5 }
  },
  "controls": [
    {
      "control_id": "CIS-2.1.5",
      "framework": "CIS",
      "rule_id": "CIS-AWS-001",
      "status": "FAIL",
      "title": "S3 Bucket Public Read Access",
      "finding_ids": ["finding-1"],
      "remediation": "Disable public read access and enable S3 Block Public Access on the bucket."
    }
  ]
}
```

> **Status semantics, stated precisely (this is the fix for the biggest ambiguity in the original draft):** the rule engine only ever records *violations* — there is no "rule evaluated this resource and it passed" record anywhere in the system, live scan or static upload. So `status` here is **rule-level, not resource-level**: every rule in `compliance_map` is `FAIL` if it produced 1+ findings in this scan, otherwise `PASS`. This does **not** mean "every resource was individually verified against this control" — it means "no violation of this rule was found in this scan." State it exactly that way in the UI copy too (M2). This keeps the endpoint's only inputs as **findings + rule metadata**, matching the original plan — no need to also load the full resource list.

The implementation must remain aligned with the project's existing schema and the existing `cis_aws` / `nist_csf` rule metadata.

---

# Shared Contract 2 — Attack-Path API

Member 3 publishes this contract; Member 4 codes to it. Implemented as its own `APIRouter` in `backend/src/attack_paths/routes.py`, included from `main.py`.

## Endpoint

`GET /scans/{scan_id}/attack-paths`

## Response

```json
{
  "scan_id": "123",
  "nodes": [
    {
      "id": "resource-1",
      "type": "instance",
      "label": "Public EC2",
      "severity": "High",
      "risk_score": 92,
      "finding_id": "finding-1"
    }
  ],
  "links": [
    { "source": "resource-1", "target": "role-1", "relationship": "ASSUMES" }
  ],
  "paths": [
    { "id": "path-1", "nodes": ["resource-1", "role-1", "bucket-1"], "severity": "High" }
  ]
}
```

> **Added `risk_score`** (optional, nullable) — Wave A's ML scoring now populates `Finding.risk_score`/`is_anomaly`, so the graph can surface it alongside severity for free. Not required for Wave B's Definition of Done, but wire it through if the data's already there; it's a one-field addition to `nodes`, not new work.

---

# Member 1 — Compliance Engine (Phase 7 backend)

**What to do (in plain words):** aggregate findings into per-framework pass/fail using the mapping that **already exists**, and attach remediation text.

The project already has a strong starting point: YAML rules carry `cis_aws` / `nist_csf` IDs, `models.py` already defines `ComplianceMap` (`cis_control_id`, `nist_id`, `remediation_steps`) with a **live foreign key** from `Finding.rule_id → compliance_map.rule_id`, and a `seed_compliance_map` migration already seeds it.

> **Changed from the original draft:** dropped the dedicated `mapper.py` module. "Mapping a finding to its controls" is already `finding.compliance` via the existing SQLAlchemy relationship — there's no new mapping logic to write. The actual new work is the aggregation query and the remediation *content*, not a mapping *engine*.

## What M1 receives

```text
Scan
 ↓
Findings (each already carries .compliance via the existing FK relationship)
```

Do not rebuild the rule engine, and do not build a second way to associate a finding with its controls.

## Files

```text
backend/src/compliance/
├── __init__.py
├── engine.py      # aggregation: per-framework passed/failed/total
├── routes.py      # GET /scans/{scan_id}/compliance, its own APIRouter
├── schemas.py
└── tests/
    ├── test_engine.py
    └── test_routes.py
```

## Step-by-step

### 1. Confirm the existing rule ↔ control data is complete

For every file in `rules/*.yaml`, confirm its `rule_id` has a matching row in the `compliance_map` seed data. **This is not optional cleanup — `Finding.rule_id` is a hard foreign key with `PRAGMA foreign_keys=ON` enforced in tests.** If a rule ever ships without a seed row, the *next scan that triggers it* fails at `Finding` insert time with a 500, not at compliance-read time. Add this as an explicit check (a small test that diffs `rules/*.yaml` rule_ids against `compliance_map` seed rows) — see Guardrails.

### 2. Build framework aggregation

For each framework (CIS, NIST):
- `total` = count of distinct controls in `compliance_map` for that framework.
- `failed` = count of those controls whose `rule_id` appears in this scan's findings.
- `passed` = `total - failed`.

(See Contract 1 for the precise, non-overclaiming meaning of "passed.")

### 3. Populate remediation content

Extend the **existing** `seed_compliance_map` migration's `remediation_steps` values — this is data entry against an existing column, not a new remediation storage system. Keep it:
- actionable, accurate, understandable, tied to the actual finding/control.

### 4. Implement the API

`GET /scans/{scan_id}/compliance` on its own `APIRouter`:

```text
validate scan (reuse the existing IDOR-safe _load_owned_scan pattern from routes.py)
→ load scan.findings (relationship already gives each finding.compliance)
→ aggregate per framework
→ serialize controls + remediation
→ return JSON
```

### 5. Handle edge cases

- unknown scan → 404 (same pattern as the existing endpoints)
- zero findings → all controls `PASS`, not an error
- a finding whose `compliance` relationship is somehow null → treat as unmapped, log it, don't crash (should be prevented by step 1, but don't trust that alone)

## Deliverables & checklist

- [ ] Seed-completeness check (every rule has a compliance_map row)
- [ ] Framework aggregation (`engine.py`)
- [ ] Remediation content populated for every existing rule
- [ ] `GET /scans/{scan_id}/compliance` on its own router
- [ ] Mock response published to M2
- [ ] Unit tests
- [ ] Documentation

## Handoff

```text
Compliance Engine → API + schema + mock → M2 Compliance Tab
```

---

# Member 2 — Compliance Tab (Phase 7 frontend)

**What to do (in plain words):** build the screen where a user can understand CIS/NIST compliance and what needs fixing.

## What M2 receives

API contract, framework summary, control status, finding IDs, remediation text, mock response.

## Files

```text
frontend/src/features/compliance/
├── CompliancePage.tsx
├── FrameworkSummary.tsx
├── ControlTable.tsx
├── RemediationPanel.tsx
├── ComplianceFilters.tsx
└── index.ts
```

**Also touches `frontend/src/pages/ScanDetailPage.tsx`** — adds the shared tab-nav shell (`Findings / Attack Paths / Compliance`) plus its own Compliance tab. M4 rebases onto this after it merges (see File-ownership map above).

## Step-by-step

### 1. Add the shared tab nav to Scan Detail + the Compliance tab

```text
Scan Detail
 ├── Findings   (existing)
 ├── Attack Paths  (placeholder — M4 fills in after this merges)
 └── Compliance
```

### 2. Framework summary — CIS and NIST: passed / failed / total, from the API. Word it per Contract 1's semantics ("no violations found for this rule in this scan"), not "every resource individually verified."

### 3. Control table — framework, control ID, title, status, related findings. Support failed-only and framework filtering.

### 4. Remediation panel — for a selected failed control/finding: what failed, why it matters, remediation guidance.

### 5. States — loading, API error, scan not found, no compliance data, no controls mapped.

### 6. Mock integration — must work against M1's mock response before the real API is ready, using the same MSW pattern already established in `frontend/src/mocks/`.

## Deliverables & checklist

- [ ] Shared `ScanDetailPage` tab nav
- [ ] Compliance page, CIS/NIST summary, control table, filters, remediation panel
- [ ] Loading/empty/error states
- [ ] Mock integration → real API integration

---

# Member 3 — Attack-Path Graph (Phase 6 backend)

**What to do (in plain words):** after the Day 0–2 collector extension lands, turn cloud resources and their relationships into a NetworkX graph and identify paths from public exposure toward sensitive assets.

## What M3 receives

Scan resources (now including `ec2_instance` nodes and `ASSUMES`/`HAS_PERMISSION` edges from the Day 0–2 work), findings, severity, resource types.

## Files

```text
backend/src/attack_paths/
├── __init__.py
├── graph.py
├── nodes.py
├── edges.py
├── path_finder.py
├── routes.py      # GET /scans/{scan_id}/attack-paths, its own APIRouter
├── schemas.py
└── tests/
    ├── test_graph.py
    ├── test_edges.py
    └── test_paths.py
```

## Step-by-step

### 1. Define graph nodes

`ec2_instance`, `iam_role`, `iam_policy`, `s3_bucket`, `security_group` — each links back to its original resource/finding. If the Day 0–2 extension didn't land in time, node types are limited to what actually exists; do not add placeholder node types for data that isn't there.

### 2. Define relationships

```text
instance --ASSUMES--> role
role --HAS_PERMISSION--> policy
policy --ACCESSES--> bucket
internet --EXPOSES--> instance   (derived from the security group's existing 0.0.0.0/0 check)
```

Keep the relationship vocabulary consistent with the API contract.

### 3. Build the NetworkX graph

```python
graph = nx.DiGraph()
graph.add_node(...)
graph.add_edge(...)
```

Do not expose NetworkX internals directly through the API.

### 4/5. Identify entry points and sensitive targets from relationships actually supported by the data — do not invent a path when a required relationship is missing.

### 6. Compute paths — **bounded.** `nx.all_simple_paths` can blow up combinatorially on any graph with cycles or fan-out; cap it with a `cutoff` (max hops, e.g. 4–5, matching the instance→role→permission→store chain length) and a max-paths limit per scan so a dense demo graph can't hang the endpoint.

### 7. Preserve context — each path retains severity, affected findings, resources, relationship types.

### 8. Implement the API — `GET /scans/{scan_id}/attack-paths` on its own router:

```text
validate scan → load resources/findings → build graph → calculate paths (bounded) → serialize → return
```

## Deliverables & checklist

- [ ] Day 0–2 collector extension merged
- [ ] NetworkX graph, node/edge models
- [ ] Bounded path discovery
- [ ] Finding/resource linkage, severity/context
- [ ] `GET /scans/{scan_id}/attack-paths` on its own router
- [ ] Mock response published to M4
- [ ] Unit tests (including a no-real-path case — this should be an *expected*, tested outcome, not a bug, if a scan's resources genuinely don't chain)
- [ ] Documentation

## Handoff

```text
Scan → Collector (extended) → Graph Builder → NetworkX graph → Path calculation → Node/link JSON → M4 Force Graph
```

---

# Member 4 — Attack-Path Visualization (Phase 6 frontend)

**What to do (in plain words):** turn M3's node/link JSON into an interactive graph.

## Files

```text
frontend/src/features/attack_paths/
├── AttackPathPage.tsx
├── AttackPathGraph.tsx
├── AttackPathLegend.tsx
├── AttackPathDetails.tsx
└── index.ts
```

**Also touches `frontend/src/pages/ScanDetailPage.tsx`** — but only to fill in the Attack Paths tab M2 already scaffolded. Start this after M2's PR is merged (see File-ownership map).

## Step-by-step

1. Add the Attack Paths tab content to the shared nav M2 built.
2. Render nodes: resource name/ID, resource type, severity, `risk_score` if present.
3. Render links per the API's relationships.
4. Reuse the existing Phase 3 severity palette.
5. Highlight a selected path's nodes/links.
6. Finding click-through via the API's `finding_id`, into the existing Findings tab.
7. States: loading, API error, invalid scan, empty graph, **and explicitly, a real "no attack paths found for this scan" state** — per M3's guardrail, this is a legitimate result, not an error; word the empty state accordingly rather than implying something's broken.

## Deliverables & checklist

- [ ] Attack Paths tab wired into the shared nav
- [ ] React Force Graph: nodes, links, severity styling, path highlighting, finding click-through
- [ ] Legend
- [ ] Loading/error/empty(-but-valid) states
- [ ] Mock integration → real API integration

---

# End-to-End Wave B Flow

## Attack Path

```text
Existing Scan → Resources (incl. EC2/role data) + Findings → M3 NetworkX Graph
→ Bounded Path Discovery → GET /scans/{id}/attack-paths → M4 React Force Graph
→ Interactive Attack Path
```

## Compliance

```text
Existing Scan → Findings (each carrying .compliance) → M1 Compliance Engine
→ CIS/NIST aggregation + Remediation → GET /scans/{id}/compliance → M2 Compliance Tab
```

---

# GitHub Commit & Merge Order

Unchanged from the original — and it already resolves the two shared-file edits described above, as long as everyone rebases after each merge:

```text
M1 → M3 → M2 → M4
```

| Step | Action |
|------|--------|
| 1 | M1 pushes Compliance Engine → PR → Review → Merge |
| 2 | Everyone pulls latest `main` |
| 3 | M3 pushes collector extension + Attack-Path Graph Backend → PR → Review → Merge |
| 4 | Everyone pulls latest `main` |
| 5 | M2 pushes Compliance Tab (incl. shared `ScanDetailPage` tab nav) → PR → Review → Merge |
| 6 | Everyone pulls latest `main` |
| 7 | M4 pushes Attack-Path Visualization (rebased onto M2's tab nav) → PR → Review → Merge |
| 8 | Everyone pulls latest `main` |

---

# Testing Plan

## M1 — Compliance
Rule-seed completeness check · framework aggregation (passed/failed/total) · zero-finding scan → all pass · unknown scan → 404 · null `.compliance` doesn't crash.

## M2 — Compliance UI
CIS/NIST summary · failed controls · framework filtering · remediation display · loading/empty/error states.

## M3 — Attack Path
Node/edge creation from the extended collector output · instance→role→permission→store chain · public entry point · sensitive target · a valid multi-hop path · **a no-path case (genuinely expected on sparse data, not a failure)** · path count/length stays bounded on a dense synthetic graph · invalid scan.

## M4 — Attack Path UI
Graph renders · nodes/links render · severity + risk_score styling · path highlighting · finding click-through · empty-but-valid graph state · API error.

---

# Guardrails

## Attack Path
- Do not invent unsupported relationships — if the Day 0–2 extension didn't land, the graph is limited to what was actually collected.
- Do not claim a path is exploitable merely because resources exist.
- Bound path search (cutoff + max-paths) — no unbounded `all_simple_paths`.
- Keep resource IDs linked to original findings.
- Do not expose NetworkX internals through the API.
- Keep graph generation deterministic for the same input.

## Compliance
- `status` is rule-level ("no violation found"), never worded as per-resource verification.
- Every `rules/*.yaml` rule_id must have a `compliance_map` seed row — enforced by a test, not discovered at scan time via a 500.
- Remediation must correspond to the actual control/finding.
- Reuse `Finding.compliance` — do not build a second mapping path.

## Frontend
- Build against agreed contracts; use mocks until the backend is ready.
- Reuse the existing severity palette.
- M4 does not start on `ScanDetailPage.tsx` until M2's tab-nav PR is merged.
- Handle empty/error/loading states — and treat "no attack paths" as a real, non-error state.

## Git
- No direct pushes to `main`. One feature per PR. CI green before merge. Pull latest `main` after every merge.
- `backend/src/main.py`'s two `include_router` lines are the only shared-file touches in Wave B — everything else (including the new endpoints themselves) lives in each feature's own router file.

---

# Documentation Deliverables

| Member | File | Includes |
| --- | --- | --- |
| M1 | `docs/phase7-compliance.md` | architecture, CIS/NIST mapping, the rule-level status semantics, remediation approach, API contract, seed-completeness check |
| M2 | `docs/compliance-ui.md` | page structure, framework summary, filtering, remediation UX |
| M3 | `docs/phase6-attack-path.md` | collector extension, graph model, node/edge types, bounded path algorithm, assumptions, limitations (what's still not collected) |
| M4 | `docs/attack-path-ui.md` | graph visualization, interaction model, severity/risk styling, path highlighting, finding navigation |

---

# Wave B Definition of Done

## Attack Path
- [ ] Collector extension merged and tested.
- [ ] `GET /scans/{id}/attack-paths` works, on its own router.
- [ ] NetworkX graph generated from real scan data (EC2 + role data present in at least one demo scan).
- [ ] Nodes and links returned; paths bounded.
- [ ] React Force Graph renders the returned graph; severity + risk_score represented.
- [ ] Paths can be highlighted; user can navigate to the related finding.
- [ ] A genuinely path-less scan renders a real "no paths" state, not an error.

## Compliance
- [ ] `GET /scans/{id}/compliance` works, on its own router.
- [ ] Every existing rule has a seed row (verified by test).
- [ ] CIS/NIST pass/fail/total shown, worded per the rule-level semantics.
- [ ] Control-level status and remediation shown.
- [ ] Missing mappings don't crash a scan (belt-and-suspenders on top of the seed check).

## Integration
- [ ] Both features work using the same scan.
- [ ] Mock-to-real API swap succeeds.
- [ ] Loading/error/empty states work.
- [ ] Unit + integration tests pass, CI green.
- [ ] Documentation complete.

---

# Metrics to Record

`docs/phase6-7-metrics.md`:
- resources represented in the graph, incl. how many are EC2 instances / role edges from the Day 0–2 extension
- relationships generated · attack paths discovered · longest path found · paths dropped by the bound (if any)
- findings mapped to CIS/NIST · passed/failed controls per framework
- API response time (attack-path, compliance) · frontend render time for a representative graph
- test count and pass/fail status

---

# Final Wave B Demo Flow

```text
Open Scans → select a scan with live EC2/IAM data → Findings
→ Attack Paths → see instance→role→bucket relationships → highlight a path → click a related finding
→ Compliance → CIS summary → NIST summary → select a failed control → read remediation
```

---

# Quick Summary

- **Day 0–2 prerequisite:** M3 extends the collector for EC2 instances + IAM role attachments — Attack-Path has no real data without this, regardless of Wave A's status.
- **M1:** Compliance aggregation on top of the existing `ComplianceMap`/FK relationship — not a new mapping engine.
- **M2:** Compliance Tab, and owns the shared `ScanDetailPage` tab-nav shell.
- **M3:** NetworkX Attack-Path Graph, on the extended resource data, with bounded path search.
- **M4:** Attack-Path Visualization, rebased onto M2's tab nav.
- Both features get their **own** `APIRouter` — Wave B never edits the existing `routes.py`.
- Compliance flows **M1 → M2**; Attack Path flows **M3 → M4**; the two branches run in parallel and neither depends on the other.
- Commit order: **M1 → M3 → M2 → M4** (unchanged — it already resolves the two genuinely shared files).
- A scan with no attack paths, or a control with no violations, is a valid tested outcome — not a bug to code around.
