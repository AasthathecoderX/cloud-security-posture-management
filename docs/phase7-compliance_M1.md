# Phase 7 — Compliance Engine

## Overview

The Phase 7 Compliance Engine aggregates security findings into CIS and NIST control status and provides remediation guidance.

The compliance engine does not create a second mapping system.

The existing database relationship is:

```text
Finding.rule_id
      |
      v
ComplianceMap.rule_id
      |
      +---- cis_control_id
      |
      +---- nist_id
      |
      +---- remediation_steps
```

This existing relationship is reused directly by the compliance engine.

## API Endpoint

`GET /scans/{scan_id}/compliance`

The endpoint is implemented using a dedicated FastAPI APIRouter in:

`backend/src/compliance/routes.py`

It is registered from:

`backend/main.py`

### Response Example

```json
{
  "scan_id": "123",
  "frameworks": {
    "CIS": {
      "passed": 3,
      "failed": 2,
      "total": 5
    },
    "NIST": {
      "passed": 3,
      "failed": 2,
      "total": 5
    }
  },
  "controls": [
    {
      "control_id": "2.1.5",
      "framework": "CIS",
      "rule_id": "CIS-AWS-001",
      "status": "FAIL",
      "title": "S3 Bucket Public Read Access",
      "finding_ids": [
        "finding-1"
      ],
      "remediation": "Disable public read access and enable S3 Block Public Access on the bucket."
    }
  ]
}
```

## Status Semantics

Compliance status is rule-level. The rule engine records violations. It does not record a separate successful evaluation for every resource.

Therefore:
- **FAIL** means the rule produced one or more findings in this scan.
- **PASS** means no finding was produced for that rule in this scan.

`PASS` does not mean that every individual resource was verified against the control. This distinction prevents the API from making a stronger claim than the underlying scan data supports.

## Framework Aggregation

For each framework:
- `total` = number of distinct controls in `compliance_map`
- `failed` = controls whose `rule_id` appears in the scan findings
- `passed` = `total - failed`

Both CIS and NIST controls are represented. A single compliance-map row can therefore produce:
- **CIS** -> one control
- **NIST** -> one control

## Existing Compliance Mapping

The project already contains:

`backend/src/models.py`

with:

`ComplianceMap`
- `rule_id`
- `cis_control_id`
- `nist_id`
- `remediation_steps`

and:

`Finding.rule_id` -> `compliance_map.rule_id`

The compliance engine uses this existing foreign-key relationship. No additional finding-to-control mapping table or mapper is introduced.

## Rule Seed Completeness

All current rule files under `rules/` are checked against the compliance-map seed. The documentation-only `rules/spec.yaml` is excluded.

The current rules are:
- `CIS-AWS-001`
- `CIS-AWS-002`
- `CIS-AWS-003`
- `CIS-AWS-004`
- `CIS-AWS-005`

Every current rule has a corresponding compliance-map seed row.

The completeness test is located at:

`backend/src/compliance/tests/test_engine.py`

## Remediation

Remediation text is stored in the existing `compliance_map.remediation_steps` column.

The existing seed migration already contains remediation guidance for the current five rules.

The compliance API exposes this value as `remediation` in every control response.

## Error Handling

### Unknown Scan
An unknown scan returns:

`404 Scan not found.`

The existing `_load_owned_scan()` helper is reused. This also preserves the existing IDOR protection: a scan belonging to another user is treated as not found.

### Zero Findings
A scan with zero findings is valid. All seeded controls are returned with:

`status = PASS`

### Missing Compliance Relationship
If a finding has no compliance relationship, the engine logs the condition and does not fail the entire compliance request.

This is defensive handling. The foreign-key constraint and seed-completeness test are intended to prevent the situation.

## File Structure

```text
backend/src/compliance/
├── __init__.py
├── engine.py
├── routes.py
├── schemas.py
├── mock_data.py
└── tests/
    ├── __init__.py
    ├── test_engine.py
    └── test_routes.py
```

## Frontend Handoff

The compliance API is consumed by the Phase 7 Compliance Tab.

The frontend receives:
- CIS summary
- NIST summary
- control IDs
- framework
- rule ID
- PASS/FAIL status
- related finding IDs
- remediation text

The mock response is available from:

`backend/src/compliance/mock_data.py`