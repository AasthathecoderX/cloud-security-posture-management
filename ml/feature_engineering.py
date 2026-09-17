"""
feature_engineering.py

Member 3 - ML Feature Engineering

Converts mutated cloud resources into numerical ML features.

Produces:
    ml/features.json

The features are designed for:
    1. XGBoost     -> supervised risk prediction
    2. Isolation Forest -> unsupervised anomaly detection
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = BASE_DIR / "mutated_resources.json"
OUTPUT_FILE = BASE_DIR / "features.json"


def safe_bool(value: Any) -> int:
    """Convert a value into a 0/1 feature."""
    return 1 if value is True else 0


def extract_features(resource: dict[str, Any]) -> dict[str, Any]:
    """Extract security-related numerical features."""

    resource_type = resource.get("resource_type", "")
    configuration = resource.get("configuration", {})
    metadata = resource.get("metadata", {})

    if not isinstance(configuration, dict):
        configuration = {}

    if not isinstance(metadata, dict):
        metadata = {}

    # -------------------------
    # Resource type features
    # -------------------------

    is_s3 = int(resource_type == "s3_bucket")
    is_iam = int(resource_type == "iam_policy")
    is_security_group = int(resource_type == "security_group")

    # -------------------------
    # S3 security features
    # -------------------------

    public_read = safe_bool(
        configuration.get("public_read", False)
    )

    encryption = safe_bool(
        configuration.get("encryption", True)
    )

    versioning = safe_bool(
        configuration.get("versioning", True)
    )

    # -------------------------
    # IAM security features
    # -------------------------

    action = str(
        configuration.get("action", "")
    )

    principal = str(
        configuration.get("principal", "")
    )

    wildcard_action = int(action == "*")
    wildcard_principal = int(principal == "*")

    # -------------------------
    # Security group features
    # -------------------------

    ingress = configuration.get("ingress", {})

    if not isinstance(ingress, dict):
        ingress = {}

    cidr = str(
        ingress.get("cidr", "")
    )

    open_ingress = int(
        cidr == "0.0.0.0/0"
    )

    # -------------------------
    # Environment features
    # -------------------------

    environment = str(
        metadata.get("environment", "")
    ).lower()

    is_production = int(
        environment == "production"
    )

    is_testing = int(
        environment == "testing"
    )

    # -------------------------
    # Rule-correlated risk
    # -------------------------

    rule_risk = (
        public_read
        + wildcard_action
        + wildcard_principal
        + open_ingress
        + (is_s3 * (1 - encryption))
    )

    # -------------------------
    # Structural feature
    # -------------------------

    configuration_size = len(configuration)

    return {
        "resource_id": resource.get("resource_id"),
        "resource_type": resource_type,

        "is_s3": is_s3,
        "is_iam": is_iam,
        "is_security_group": is_security_group,

        "public_read": public_read,
        "encryption": encryption,
        "versioning": versioning,

        "wildcard_action": wildcard_action,
        "wildcard_principal": wildcard_principal,

        "open_ingress": open_ingress,

        "is_production": is_production,
        "is_testing": is_testing,

        "rule_risk": rule_risk,
        "configuration_size": configuration_size,

        "label": int(
            resource.get("label", 0)
        ),
    }


def main() -> None:
    """Generate ML features from mutated resources."""

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}"
        )

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8",
    ) as file:
        resources = json.load(file)

    if not isinstance(resources, list):
        raise ValueError(
            "mutated_resources.json must contain a list."
        )

    features = [
        extract_features(resource)
        for resource in resources
    ]

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            features,
            file,
            indent=2,
        )

    print("Feature engineering completed successfully.")
    print(f"Total samples : {len(features)}")
    print(
        f"Normal samples: "
        f"{sum(item['label'] == 0 for item in features)}"
    )
    print(
        f"Anomalous samples: "
        f"{sum(item['label'] == 1 for item in features)}"
    )
    print(f"Features per sample: {len(features[0]) - 3}")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()