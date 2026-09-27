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
RANDOM_SEED = 7

ENVIRONMENTS = [
    "development",
    "testing",
    "staging",
    "production",
]

# Realistic, non-wildcard IAM values. None of these trip the wildcard_action /
# wildcard_principal rules -- they exist to keep the "normal" class from being
# the same literal string 100 times over, which was collapsing the dataset
# down to a handful of distinct feature-vectors (see ml/mutate_iac.py).
IAM_ACTIONS = [
    "s3:GetObject",
    "s3:PutObject",
    "s3:ListBucket",
    "ec2:DescribeInstances",
    "logs:PutLogEvents",
    "dynamodb:Query",
]
IAM_PRINCIPALS = [
    "arn:aws:iam::123456789012:user/alice",
    "arn:aws:iam::123456789012:user/bob",
    "arn:aws:iam::123456789012:role/deploy-role",
    "specific-user",
]

# Private/internal CIDR ranges -- none is 0.0.0.0/0, so none trips the
# open-ingress rule regardless of which one a given resource gets.
PRIVATE_CIDRS = [
    "10.0.0.0/24",
    "10.0.1.0/24",
    "172.16.0.0/16",
    "192.168.1.0/24",
    "10.20.30.0/24",
]
INTERNAL_PORTS = [443, 8443, 3306, 5432, 22]


def _metadata():
    """Shared metadata: environment/owner (existing) plus tags_count -- a
    lightweight stand-in for the fleet's tag/ownership richness (structural,
    not rule-correlated), used only by the Isolation Forest's behavioral
    feature set.
    """
    return {
        "environment": random.choice(ENVIRONMENTS),
        "owner": f"team-{random.randint(1, 5)}",
        "tags_count": random.randint(2, 6),
    }


def generate_s3_bucket(index):
    return {
        "resource_id": f"bucket-{index:03d}",
        "resource_type": "s3_bucket",
        "configuration": {
            "public_read": False,
            "encryption": True,
            # Not rule-checked (no versioning rule exists), so it's free to
            # vary within the "normal" class instead of being fixed True.
            "versioning": random.random() < 0.75,
        },
        "metadata": _metadata(),
    }


def generate_iam_policy(index):
    return {
        "resource_id": f"policy-{index:03d}",
        "resource_type": "iam_policy",
        "configuration": {
            "action": random.choice(IAM_ACTIONS),
            "principal": random.choice(IAM_PRINCIPALS),
            "resource": "arn:aws:s3:::example-bucket/*",
        },
        "metadata": _metadata(),
    }


def generate_security_group(index):
    return {
        "resource_id": f"sg-{index:03d}",
        "resource_type": "security_group",
        "configuration": {
            "ingress": {
                "cidr": random.choice(PRIVATE_CIDRS),
                "port": random.choice(INTERNAL_PORTS),
            },
            "egress_allowed": random.random() < 0.8,
        },
        "metadata": _metadata(),
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
    random.seed(RANDOM_SEED)
    resources = generate_resources(count_per_type=100)
    save_resources(resources)


if __name__ == "__main__":
    main()