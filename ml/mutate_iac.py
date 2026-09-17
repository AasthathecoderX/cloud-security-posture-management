"""
mutate_iac.py

Member 3 - ML Dataset Generation

Creates labeled security anomalies from the self-generated
resources.json dataset.

No external dataset is used.

Output:
    ml/mutated_resources.json

Each resource receives:
    label = 0  -> normal
    label = 1  -> anomalous
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = BASE_DIR / "resources.json"
OUTPUT_FILE = BASE_DIR / "mutated_resources.json"

RANDOM_SEED = 42
ANOMALY_RATE = 0.30


def mutate_s3_bucket(resource: dict[str, Any]) -> None:
    """Introduce security anomalies into an S3 bucket."""

    configuration = resource.setdefault("configuration", {})

    mutation = random.choice(
        [
            "public_read",
            "encryption",
            "versioning",
        ]
    )

    if mutation == "public_read":
        configuration["public_read"] = True

    elif mutation == "encryption":
        configuration["encryption"] = False

    elif mutation == "versioning":
        configuration["versioning"] = False


def mutate_iam_policy(resource: dict[str, Any]) -> None:
    """Introduce security anomalies into an IAM policy."""

    configuration = resource.setdefault("configuration", {})

    mutation = random.choice(
        [
            "action",
            "principal",
        ]
    )

    if mutation == "action":
        configuration["action"] = "*"

    elif mutation == "principal":
        configuration["principal"] = "*"


def mutate_security_group(resource: dict[str, Any]) -> None:
    """Introduce an open-ingress security group anomaly."""

    configuration = resource.setdefault("configuration", {})

    configuration["ingress"] = {
        "cidr": "0.0.0.0/0"
    }


def mutate_resource(resource: dict[str, Any]) -> None:
    """Apply one security mutation according to resource type."""

    resource_type = resource.get("resource_type")

    if resource_type == "s3_bucket":
        mutate_s3_bucket(resource)

    elif resource_type == "iam_policy":
        mutate_iam_policy(resource)

    elif resource_type == "security_group":
        mutate_security_group(resource)


def main() -> None:
    random.seed(RANDOM_SEED)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}"
        )

    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        resources = json.load(file)

    if not isinstance(resources, list):
        raise ValueError(
            "resources.json must contain a list of resources."
        )

    total_resources = len(resources)

    anomaly_count = int(total_resources * ANOMALY_RATE)

    anomaly_indices = set(
        random.sample(
            range(total_resources),
            anomaly_count,
        )
    )

    mutated_resources = []

    for index, resource in enumerate(resources):
        resource_copy = json.loads(
            json.dumps(resource)
        )

        if index in anomaly_indices:
            mutate_resource(resource_copy)
            resource_copy["label"] = 1
        else:
            resource_copy["label"] = 0

        mutated_resources.append(resource_copy)

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            mutated_resources,
            file,
            indent=2,
        )

    normal_count = total_resources - anomaly_count

    print("Mutation completed successfully.")
    print(f"Total resources : {total_resources}")
    print(f"Normal resources: {normal_count}")
    print(f"Anomalous resources: {anomaly_count}")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()