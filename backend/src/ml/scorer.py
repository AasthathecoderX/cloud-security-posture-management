"""
ML risk-scoring layer (Wave A, Member 4).

Implements Contract B (see ``guides/wave A/Wave_A_Detailed_Execution_Plan.md``):

    score_findings(findings: list[dict]) -> list[dict]

Returns one ``{"risk_score": int, "is_anomaly": bool}`` per input finding, in
the same order, so callers (``routes.py``) never depend on *how* the score is
produced.

Member 3's trained models (``ml/model.joblib``, ``ml/feature_engineering.py``)
don't exist yet, so this scores with a deterministic heuristic derived from
each finding's own severity/rule_id/resource_id. When M3 lands the trained
model and its feature-engineering interface, replace the body of
``score_findings`` with a call into it -- the ``{"risk_score", "is_anomaly"}``
return shape is the only thing the rest of the app (DB, API, dashboard)
depends on, so nothing downstream needs to change.
"""

from __future__ import annotations

import hashlib
from typing import Any

_SEVERITY_BASE_SCORE = {
    "Critical": 90,
    "High": 70,
    "Medium": 45,
    "Low": 20,
}
_ANOMALY_THRESHOLD = 85


def _stable_jitter(finding: dict[str, Any], spread: int = 8) -> int:
    """Deterministic +/-spread nudge so same-severity findings don't tie.

    Derived from the finding's own identity (resource_id + rule_id), not
    randomness, so a given finding always scores the same way -- keeps tests
    and the dashboard's Top Risks ordering stable across requests.
    """
    key = f"{finding.get('resource_id', '')}:{finding.get('rule_id', '')}"
    digest = hashlib.sha256(key.encode()).digest()
    return (digest[0] % (2 * spread + 1)) - spread


def score_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Score each finding for risk (0-100) and fleet-anomaly status.

    Contract B, frozen in guides/wave A: one ``{"risk_score", "is_anomaly"}``
    dict per input finding, same order as ``findings``. See the module
    docstring for the swap-in point once M3's trained model is available.
    """
    scored = []
    for finding in findings:
        base = _SEVERITY_BASE_SCORE.get(finding.get("severity"), 30)
        risk_score = max(0, min(100, base + _stable_jitter(finding)))
        scored.append(
            {
                "risk_score": risk_score,
                "is_anomaly": risk_score >= _ANOMALY_THRESHOLD,
            }
        )
    return scored
