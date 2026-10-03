"""
localstack.py

Creates secure boto3 clients for the LocalStack environment.

Responsibilities
----------------
1. Connect only to approved endpoints.
2. Create read-only boto3 clients.
3. Share clients across the collector.
4. Prevent accidental SSRF via endpoint allowlisting.

Author:
Member-1 (Phase 4)
"""

from __future__ import annotations

import logging
import os
from typing import Dict

import boto3
from botocore.config import Config


logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# Allowed LocalStack endpoints
# ---------------------------------------------------------------------

_ALLOWED_ENDPOINTS = {
    "http://localhost:4566",
    "http://127.0.0.1:4566",
    # Docker Compose service hostname (see infra/docker-compose.yml and the
    # root .env): containers reach LocalStack by service name, not
    # "localhost" -- that resolves to the backend container itself, not the
    # localstack one. Not user-controlled, so allowlisting it doesn't weaken
    # the SSRF defence this set exists for.
    "http://localstack:4566",
}


# ---------------------------------------------------------------------
# Read endpoint from environment
# ---------------------------------------------------------------------

LOCALSTACK_ENDPOINT = os.getenv(
    "LOCALSTACK_ENDPOINT",
    "http://localhost:4566",
)

# The root .env sets AWS_DEFAULT_REGION (the name boto3/awscli read
# natively); AWS_REGION is accepted too so an explicit override still wins.
AWS_REGION = os.getenv(
    "AWS_REGION",
    os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
)

AWS_ACCESS_KEY_ID = os.getenv(
    "AWS_ACCESS_KEY_ID",
    "test",
)

AWS_SECRET_ACCESS_KEY = os.getenv(
    "AWS_SECRET_ACCESS_KEY",
    "test",
)

# ---------------------------------------------------------------------
# Credential mode (Wave C, Member 4 -- STS AssumeRole guardrail)
# ---------------------------------------------------------------------
#
# This project only ever runs against LocalStack, which does not meaningfully
# emulate cross-account STS AssumeRole -- there is no second account to
# assume a role into, so a real AssumeRole flow can't actually be exercised
# or tested here. Building one anyway would be security-theater: code nobody
# can verify works. Per the Wave C plan ("document + flag-gate, don't half-
# build against LocalStack"), this is implemented, defaults OFF, and is
# intended for a future real-AWS deployment, not for this project's own use.
#
# AWS_AUTH_MODE:
#   "static"      (default) -- AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY above,
#                  i.e. LocalStack's dummy "test"/"test" credentials. Never a
#                  long-lived real-AWS key: nothing in this codebase reads
#                  real AWS credentials from anywhere but environment
#                  variables, and the default value is only ever the
#                  LocalStack placeholder, not a real secret.
#   "assume_role" -- for a real-AWS deployment only. Requires
#                  AWS_ASSUME_ROLE_ARN and AWS_ASSUME_ROLE_EXTERNAL_ID: the
#                  external id defends against the confused-deputy problem
#                  (https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create_for-user_externalid.html),
#                  and is mandatory here, not optional, for exactly that
#                  reason. No long-lived key is stored; the temporary
#                  credentials returned by sts:AssumeRole are used for the
#                  session only, never written to disk or logged.
AWS_AUTH_MODE = os.getenv("AWS_AUTH_MODE", "static").strip().lower()

AWS_ASSUME_ROLE_ARN = os.getenv("AWS_ASSUME_ROLE_ARN", "")
AWS_ASSUME_ROLE_EXTERNAL_ID = os.getenv("AWS_ASSUME_ROLE_EXTERNAL_ID", "")


def _assume_role_credentials() -> dict:
    """
    Exchange the role ARN + external id for temporary STS credentials.

    Only reachable when AWS_AUTH_MODE=assume_role, which is never the case
    against LocalStack in this project today -- see the module-level note.
    """
    if not AWS_ASSUME_ROLE_ARN or not AWS_ASSUME_ROLE_EXTERNAL_ID:
        raise ValueError(
            "AWS_AUTH_MODE=assume_role requires both AWS_ASSUME_ROLE_ARN "
            "and AWS_ASSUME_ROLE_EXTERNAL_ID."
        )

    sts = boto3.client("sts", region_name=AWS_REGION)

    response = sts.assume_role(
        RoleArn=AWS_ASSUME_ROLE_ARN,
        RoleSessionName="cspm-backend",
        ExternalId=AWS_ASSUME_ROLE_EXTERNAL_ID,
    )

    return response["Credentials"]


# ---------------------------------------------------------------------
# Validate endpoint
# ---------------------------------------------------------------------

def validate_endpoint(endpoint: str) -> None:
    """
    Prevent arbitrary URLs.

    Only allow known LocalStack endpoints.

    Raises
    ------
    ValueError
        If endpoint is not trusted.
    """

    if endpoint not in _ALLOWED_ENDPOINTS:
        raise ValueError(
            f"Blocked endpoint '{endpoint}'. "
            "Only approved LocalStack endpoints are allowed."
        )


validate_endpoint(LOCALSTACK_ENDPOINT)


# ---------------------------------------------------------------------
# Shared boto configuration
# ---------------------------------------------------------------------

BOTO_CONFIG = Config(

    retries={
        "max_attempts": 5,
        "mode": "standard",
    },

    connect_timeout=5,

    read_timeout=10,

    region_name=AWS_REGION,
)


# ---------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------

if AWS_AUTH_MODE == "assume_role":
    _creds = _assume_role_credentials()
    _SESSION = boto3.Session(
        aws_access_key_id=_creds["AccessKeyId"],
        aws_secret_access_key=_creds["SecretAccessKey"],
        aws_session_token=_creds["SessionToken"],
        region_name=AWS_REGION,
    )
elif AWS_AUTH_MODE == "static":
    _SESSION = boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )
else:
    raise ValueError(
        f"Unknown AWS_AUTH_MODE '{AWS_AUTH_MODE}'. Use 'static' or 'assume_role'."
    )


# ---------------------------------------------------------------------
# Generic Client Factory
# ---------------------------------------------------------------------

def create_client(service: str):
    """
    Create boto3 client.

    Parameters
    ----------
    service : str

    Returns
    -------
    boto3.client
    """

    logger.info("Creating boto3 client for %s", service)

    return _SESSION.client(

        service,

        endpoint_url=LOCALSTACK_ENDPOINT,

        config=BOTO_CONFIG,
    )


# ---------------------------------------------------------------------
# Individual Service Clients
# ---------------------------------------------------------------------

def get_s3_client():
    """
    S3 client.
    """

    return create_client("s3")


def get_ec2_client():
    """
    EC2 client.

    Security Groups live under EC2.
    """

    return create_client("ec2")


def get_iam_client():
    """
    IAM client.
    """

    return create_client("iam")


# ---------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------

def test_connection() -> Dict:
    """
    Verify LocalStack connectivity.

    Returns
    -------
    dict
    """

    try:

        s3 = get_s3_client()

        response = s3.list_buckets()

        logger.info("LocalStack connection successful.")

        return {

            "connected": True,

            "bucket_count": len(
                response.get("Buckets", [])
            ),
        }

    except Exception as exc:

        logger.exception("LocalStack connection failed.")

        return {

            "connected": False,

            "error": str(exc),
        }