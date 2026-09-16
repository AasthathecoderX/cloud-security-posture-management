"""
collector.py

Phase-4
Member-1

Cloud Collector

Responsibilities
----------------
1. Connect to LocalStack.
2. Collect S3 Buckets.
3. Collect IAM Policies.
4. Collect Security Groups.
5. Normalize resources.
6. Return Contract-A for the Rule Engine.

This module is the ONLY public entry point for M2.

M2 will call

    collect_cloud_resources()

and directly feed the output into the existing Rule Engine.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Any

from botocore.exceptions import ClientError

from .localstack import (
    get_s3_client,
    get_iam_client,
    get_ec2_client,
)

from .normalizer import normalize_resource


logger = logging.getLogger(__name__)


class CloudCollector:
    """
    Read-only LocalStack collector.

    Collects

    - S3
    - IAM
    - Security Groups

    and converts them into Rule Engine resources.
    """

    def __init__(self):

        self.s3 = get_s3_client()

        self.iam = get_iam_client()

        self.ec2 = get_ec2_client()

    # =====================================================
    # S3
    # =====================================================

    def collect_s3_resources(self) -> List[Dict[str, Any]]:
        """
        Collect every S3 bucket.

        Returns
        -------
        List[dict]
        """

        logger.info("Collecting S3 buckets...")

        resources = []

        try:

            response = self.s3.list_buckets()

            buckets = response.get("Buckets", [])

        except ClientError as exc:

            logger.exception(
                "Unable to list buckets."
            )

            return resources

        logger.info(

            "Found %d bucket(s).",

            len(buckets)

        )

        for bucket in buckets:

            bucket_name = bucket["Name"]

            logger.info(

                "Reading bucket %s",

                bucket_name

            )

            try:

                acl = self.s3.get_bucket_acl(

                    Bucket=bucket_name

                )

            except ClientError:

                logger.warning(

                    "Could not read ACL for %s",

                    bucket_name

                )

                continue

            resource = normalize_resource(

                "s3_bucket",

                bucket_name,

                acl,

            )

            resources.append(resource)

        logger.info(

            "Collected %d S3 resource(s).",

            len(resources)

        )

        return resources

    # =====================================================
    # IAM
    # =====================================================

    def collect_iam_resources(self) -> List[Dict[str, Any]]:
        """
        Collect customer managed IAM policies.

        Returns
        -------
        List[dict]
        """

        logger.info(

            "Collecting IAM policies..."

        )

        resources = []

        paginator = self.iam.get_paginator(

            "list_policies"

        )

        try:

            for page in paginator.paginate(

                Scope="Local"

            ):

                policies = page.get(

                    "Policies",

                    []

                )

                for policy in policies:

                    arn = policy["Arn"]

                    policy_name = policy["PolicyName"]

                    logger.info(

                        "Reading policy %s",

                        policy_name

                    )

                    # One malformed/unreadable policy should not fail the
                    # whole live scan -- skip it and keep going, matching
                    # collect_s3_resources's per-resource resilience.
                    try:

                        version = self.iam.get_policy(

                            PolicyArn=arn

                        )

                        default_version = version[
                            "Policy"
                        ][
                            "DefaultVersionId"
                        ]

                        document = self.iam.get_policy_version(

                            PolicyArn=arn,

                            VersionId=default_version,

                        )
                        policy_document = document[
                            "PolicyVersion"
                        ][
                            "Document"
                        ]

                        resource = normalize_resource(

                            "iam_policy",

                            policy_name,

                            policy_document,

                        )

                    except (ClientError, ValueError, KeyError) as exc:

                        logger.warning(

                            "Skipping IAM policy %s: %s",

                            policy_name,

                            exc,

                        )

                        continue

                    resources.append(resource)

        except ClientError:

            logger.exception(

                "Unable to collect IAM policies."

            )

        logger.info(

            "Collected %d IAM resource(s).",

            len(resources)

        )

        return resources

    # =====================================================
    # Security Groups
    # =====================================================

    def collect_security_groups(self) -> List[Dict[str, Any]]:
        """
        Collect EC2 Security Groups.

        Returns
        -------
        List[dict]
        """

        logger.info(

            "Collecting Security Groups..."

        )

        resources = []

        try:

            response = self.ec2.describe_security_groups()

            security_groups = response.get(

                "SecurityGroups",

                []

            )

        except ClientError:

            logger.exception(

                "Unable to retrieve Security Groups."

            )

            return resources

        logger.info(

            "Found %d Security Group(s).",

            len(security_groups)

        )

        for group in security_groups:

            resource = normalize_resource(

                "security_group",

                group,

            )

            resources.append(resource)

        logger.info(

            "Collected %d Security Group resource(s).",

            len(resources)

        )

        return resources

    # =====================================================
    # Main Collector
    # =====================================================

    def collect(self) -> List[Dict[str, Any]]:
        """
        Collect every supported cloud resource.

        Returns
        -------
        List[dict]

        Contract A
        """

        logger.info(

            "Starting cloud resource collection."

        )

        resources: List[Dict[str, Any]] = []

        resources.extend(

            self.collect_s3_resources()

        )

        resources.extend(

            self.collect_iam_resources()

        )

        resources.extend(

            self.collect_security_groups()

        )

        logger.info(

            "Collected %d total resources.",

            len(resources)

        )

        return resources


        # =====================================================
# Public Contract (Contract A)
# =====================================================

def collect_cloud_resources() -> List[Dict[str, Any]]:
    """
    Public entry point for the Cloud Connector.

    This is the ONLY function that external modules
    (e.g. M2's Live Cloud Scan API) should call.

    Flow
    ----
    LocalStack
        ↓
    CloudCollector
        ↓
    Normalizer
        ↓
    Rule Engine Contract

    Returns
    -------
    List[dict]

    Example
    -------
    [
        {
            "resource_id": "demo-bucket",
            "resource_type": "s3_bucket",
            "public_read": False,
            "public_write": False,
        },
        {
            "resource_id": "sg-001",
            "resource_type": "security_group",
            "ingress": {
                "cidr": "0.0.0.0/0"
            }
        }
    ]
    """

    logger.info(
        "Cloud Connector started."
    )

    collector = CloudCollector()

    resources = collector.collect()

    logger.info(
        "Cloud Connector finished successfully."
    )

    logger.info(
        "Returning %d normalized resources.",
        len(resources),
    )

    return resources


# =====================================================
# Standalone Testing
# =====================================================

if __name__ == "__main__":

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s | %(message)s",
    )

    print()

    print("=" * 60)
    print(" Phase-4 Cloud Connector ")
    print("=" * 60)
    print()

    try:

        resources = collect_cloud_resources()

        print(f"Collected {len(resources)} resource(s).\n")

        for resource in resources:

            print(resource)

    except Exception as exc:

        logger.exception(
            "Cloud collection failed."
        )

        print(f"\nERROR: {exc}")