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

_SESSION = boto3.Session(

    aws_access_key_id=AWS_ACCESS_KEY_ID,

    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,

    region_name=AWS_REGION,
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