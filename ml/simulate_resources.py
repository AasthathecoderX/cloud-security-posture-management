"""
Synthetic cloud resource generator for ML training.

Member 3 - ML Models
Project: A Hybrid AI Framework for Cloud Configuration Security Assessment
and Risk Prediction
"""

import json
import random
from pathlib import Path


OUTPUT_FILE = Path(__file__).parent / "resources.json"

ENVIRONMENTS = [
    "development",
    "testing",
    "staging",
    "production",
]


def generate_s3_bucket(index):
    return {
        "resource_id": f"bucket-{index:03d}",
        "resource_type": "s3_bucket",
        "configuration": {
            "public_read": False,
            "encryption": True,
            "versioning": True,
        },
        "metadata": {
            "environment": random.choice(ENVIRONMENTS),
            "owner": f"team-{random.randint(1, 5)}",
        },
    }


def generate_iam_policy(index):
    return {
        "resource_id": f"policy-{index:03d}",
        "resource_type": "iam_policy",
        "configuration": {
            "action": "s3:GetObject",
            "principal": "specific-user",
            "resource": "arn:aws:s3:::example-bucket/*",
        },
        "metadata": {
            "environment": random.choice(ENVIRONMENTS),
            "owner": f"team-{random.randint(1, 5)}",
        },
    }


def generate_security_group(index):
    return {
        "resource_id": f"sg-{index:03d}",
        "resource_type": "security_group",
        "configuration": {
            "ingress": {
                "cidr": "10.0.0.0/24",
                "port": 443,
            },
            "egress_allowed": True,
        },
        "metadata": {
            "environment": random.choice(ENVIRONMENTS),
            "owner": f"team-{random.randint(1, 5)}",
        },
    }


def generate_resources(count_per_type=100):
    resources = []

    for index in range(1, count_per_type + 1):
        resources.append(generate_s3_bucket(index))
        resources.append(generate_iam_policy(index))
        resources.append(generate_security_group(index))

    return resources


def save_resources(resources):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(resources, file, indent=2)

    print(f"Generated {len(resources)} resources.")
    print(f"Saved to: {OUTPUT_FILE}")


def main():
    resources = generate_resources(count_per_type=100)
    save_resources(resources)


if __name__ == "__main__":
    main()