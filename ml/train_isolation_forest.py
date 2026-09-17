"""
train_isolation_forest.py

Member 3 - Unsupervised ML Model

Trains an Isolation Forest model to detect unusual cloud
configuration patterns.

Output:
    ml/isolation_forest_model.joblib
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
)


BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = BASE_DIR / "features.json"
MODEL_FILE = BASE_DIR / "isolation_forest_model.joblib"


FEATURE_COLUMNS = [
    "is_s3",
    "is_iam",
    "is_security_group",
    "public_read",
    "encryption",
    "versioning",
    "wildcard_action",
    "wildcard_principal",
    "open_ingress",
    "is_production",
    "is_testing",
    "rule_risk",
    "configuration_size",
]


def main() -> None:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Feature file not found: {INPUT_FILE}"
        )

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    if not isinstance(data, list) or not data:
        raise ValueError(
            "features.json must contain a non-empty list."
        )

    X = np.array(
        [
            [item[column] for column in FEATURE_COLUMNS]
            for item in data
        ],
        dtype=float,
    )

    y = np.array(
        [item["label"] for item in data],
        dtype=int,
    )

    # Train only on normal resources.
    normal_X = X[y == 0]

    model = IsolationForest(
        n_estimators=150,
        contamination=0.30,
        random_state=42,
        n_jobs=2,
    )

    model.fit(normal_X)

    # Isolation Forest:
    # +1 = normal
    # -1 = anomaly
    raw_predictions = model.predict(X)

    predictions = np.where(
        raw_predictions == -1,
        1,
        0,
    )

    precision = precision_score(
        y,
        predictions,
        zero_division=0,
    )

    recall = recall_score(
        y,
        predictions,
        zero_division=0,
    )

    f1 = f1_score(
        y,
        predictions,
        zero_division=0,
    )

    anomaly_count = int(
        np.sum(predictions == 1)
    )

    print("\nIsolation Forest training completed successfully.")
    print("-----------------------------------------------")
    print(f"Normal training samples : {len(normal_X)}")
    print(f"Total evaluated samples: {len(X)}")
    print(f"Detected anomalies     : {anomaly_count}")

    print("\nEvaluation against synthetic labels:")
    print(f"Precision              : {precision:.4f}")
    print(f"Recall                 : {recall:.4f}")
    print(f"F1 Score               : {f1:.4f}")

    model_package = {
        "model": model,
        "feature_columns": FEATURE_COLUMNS,
        "model_type": "Isolation Forest",
    }

    joblib.dump(
        model_package,
        MODEL_FILE,
    )

    print("\nModel saved successfully:")
    print(MODEL_FILE)


if __name__ == "__main__":
    main()