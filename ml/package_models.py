"""
package_models.py

Member 3 - Final ML Model Package

Combines the trained XGBoost and Isolation Forest models
into the final model.joblib artifact.
"""

from __future__ import annotations

from pathlib import Path

import joblib


BASE_DIR = Path(__file__).resolve().parent

XGBOOST_FILE = BASE_DIR / "xgboost_model.joblib"
ISOLATION_FILE = BASE_DIR / "isolation_forest_model.joblib"
OUTPUT_FILE = BASE_DIR / "model.joblib"


def main() -> None:
    if not XGBOOST_FILE.exists():
        raise FileNotFoundError(
            f"Missing XGBoost model: {XGBOOST_FILE}"
        )

    if not ISOLATION_FILE.exists():
        raise FileNotFoundError(
            f"Missing Isolation Forest model: {ISOLATION_FILE}"
        )

    xgboost_package = joblib.load(XGBOOST_FILE)
    isolation_package = joblib.load(ISOLATION_FILE)

    model_package = {
        "xgboost": xgboost_package,
        "isolation_forest": isolation_package,
        "version": "1.0",
        "description": (
            "Hybrid cloud configuration security "
            "risk and anomaly detection models"
        ),
    }

    joblib.dump(
        model_package,
        OUTPUT_FILE,
    )

    print("Final model package created successfully.")
    print(f"Saved to: {OUTPUT_FILE}")

    print("\nIncluded models:")
    print("- XGBoost")
    print("- Isolation Forest")


if __name__ == "__main__":
    main()