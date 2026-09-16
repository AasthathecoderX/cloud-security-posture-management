"""
Tests for the Wave A Member 4 scoring layer (backend/src/ml/scorer.py).

Exercises Contract B directly: score_findings(findings) -> one
{"risk_score": int, "is_anomaly": bool} per input finding, same order.
"""

from ml.scorer import score_findings


def _finding(severity, resource_id="r1", rule_id="RULE-1"):
    return {
        "resource_id": resource_id,
        "resource_type": "s3_bucket",
        "severity": severity,
        "rule_id": rule_id,
        "message": "fix it",
    }


def test_empty_input_returns_empty_output():
    assert score_findings([]) == []


def test_output_shape_matches_input_length_and_order():
    findings = [_finding("Critical"), _finding("Low", "r2", "RULE-2")]
    scores = score_findings(findings)
    assert len(scores) == 2
    for s in scores:
        assert set(s.keys()) == {"risk_score", "is_anomaly"}
        assert 0 <= s["risk_score"] <= 100
        assert isinstance(s["is_anomaly"], bool)


def test_higher_severity_scores_higher():
    critical = score_findings([_finding("Critical", "r1", "R1")])[0]
    low = score_findings([_finding("Low", "r1", "R1")])[0]
    assert critical["risk_score"] > low["risk_score"]


def test_deterministic_for_the_same_finding():
    finding = _finding("High", "aws_s3_bucket.x", "S3-001")
    assert score_findings([finding]) == score_findings([finding])


def test_unknown_severity_does_not_crash():
    scores = score_findings([_finding("Unknown-severity")])
    assert 0 <= scores[0]["risk_score"] <= 100
