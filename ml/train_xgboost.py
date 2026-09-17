"""
train_xgboost.py

Member 3 - Supervised ML Model

Trains an XGBoost classifier using the generated cloud-security
features and anomaly labels.

Output:
    ml/xgboost_model.joblib
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier


BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = BASE_DIR / "features.json"
MODEL_FILE = BASE_DIR / "xgboost_model.joblib"


# Features used by the supervised model.
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

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y,
    )

    model = XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.08,
        subsample=0.9,
        colsample_bytree=0.9,
        objective="binary:logistic",
        eval_metric="logloss",
        random_state=42,
        n_jobs=2,
    )

    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    accuracy = accuracy_score(
        y_test,
        predictions,
    )

    precision = precision_score(
        y_test,
        predictions,
        zero_division=0,
    )

    recall = recall_score(
        y_test,
        predictions,
        zero_division=0,
    )

    f1 = f1_score(
        y_test,
        predictions,
        zero_division=0,
    )

    print("\nXGBoost training completed successfully.")
    print("----------------------------------------")
    print(f"Training samples : {len(X_train)}")
    print(f"Testing samples  : {len(X_test)}")
    print(f"Accuracy         : {accuracy:.4f}")
    print(f"Precision        : {precision:.4f}")
    print(f"Recall           : {recall:.4f}")
    print(f"F1 Score         : {f1:.4f}")

    print("\nClassification Report:")
    print(
        classification_report(
            y_test,
            predictions,
            target_names=[
                "Normal",
                "Anomalous",
            ],
            zero_division=0,
        )
    )

    print("Feature Importance:")
    importance = model.feature_importances_

    sorted_features = sorted(
        zip(FEATURE_COLUMNS, importance),
        key=lambda item: item[1],
        reverse=True,
    )

    for feature, value in sorted_features:
        print(
            f"{feature:25s}: {value:.4f}"
        )

    model_package = {
        "model": model,
        "feature_columns": FEATURE_COLUMNS,
        "model_type": "XGBoost",
    }

    joblib.dump(
        model_package,
        MODEL_FILE,
    )

    print("\nModel saved successfully:")
    print(MODEL_FILE)


if __name__ == "__main__":
    main()