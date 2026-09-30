"""
Unit tests for Phase-4 Cloud Connector.

Member-1 / Member-3

Tests:
1. Resource Mapper
2. Normalizer
3. Cloud Collector
4. Contract A
5. Wave B EC2 and IAM Role collection
"""

import json
import urllib.parse
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError

from src.cloud.collector import (
    CloudCollector,
    collect_cloud_resources,
)

from src.cloud.localstack import validate_endpoint

from src.cloud.normalizer import (
    normalize_resource,
)


# ==========================================================
# S3
# ==========================================================

def test_normalize_s3_bucket():

    acl = {
        "Grants": [
            {
                "Permission": "READ",
                "Grantee": {
                    "URI": "http://acs.amazonaws.com/groups/global/AllUsers"
                }
            }
        ]
    }

    resource = normalize_resource(
        "s3_bucket",
        "demo-bucket",
        acl,
    )

    assert resource["resource_id"] == "demo-bucket"
    assert resource["resource_type"] == "s3_bucket"
    assert resource["public_read"] is True
    assert resource["public_write"] is False


# ==========================================================
# IAM
# ==========================================================

def test_normalize_iam_policy():

    document = {
        "Statement": [
            {
                "Action": "s3:*"
            }
        ]
    }

    resource = normalize_resource(
        "iam_policy",
        "AdminPolicy",
        document,
    )

    assert resource["resource_type"] == "iam_policy"
    assert resource["action"] == "s3:*"


# ==========================================================
# Security Group
# ==========================================================

def test_normalize_security_group():

    group = {
        "GroupId": "sg-001",
        "IpPermissions": [
            {
                "IpRanges": [
                    {
                        "CidrIp": "0.0.0.0/0"
                    }
                ]
            }
        ]
    }

    resource = normalize_resource(
        "security_group",
        group,
    )

    assert resource["resource_type"] == "security_group"
    assert resource["ingress"]["cidr"] == "0.0.0.0/0"


# ==========================================================
# Collector
# ==========================================================

@patch("src.cloud.collector.get_ec2_client")
@patch("src.cloud.collector.get_iam_client")
@patch("src.cloud.collector.get_s3_client")
def test_collector_initialization(
    mock_s3,
    mock_iam,
    mock_ec2,
):

    CloudCollector()

    mock_s3.assert_called_once()
    mock_iam.assert_called_once()
    mock_ec2.assert_called_once()


# ==========================================================
# Contract A
# ==========================================================

@patch.object(
    CloudCollector,
    "collect",
)
def test_collect_cloud_resources(
    mock_collect,
):

    expected = [
        {
            "resource_id": "bucket-1",
            "resource_type": "s3_bucket",
            "public_read": False,
            "public_write": False,
        }
    ]

    mock_collect.return_value = expected

    resources = collect_cloud_resources()

    assert resources == expected
    mock_collect.assert_called_once()


# ==========================================================
# Empty Collection
# ==========================================================

@patch.object(
    CloudCollector,
    "collect_iam_role_attachments",
)
@patch.object(
    CloudCollector,
    "collect_ec2_instances",
)
@patch.object(
    CloudCollector,
    "collect_security_groups",
)
@patch.object(
    CloudCollector,
    "collect_iam_resources",
)
@patch.object(
    CloudCollector,
    "collect_s3_resources",
)
def test_empty_collection(
    mock_s3,
    mock_iam,
    mock_sg,
    mock_ec2,
    mock_roles,
):

    mock_s3.return_value = []
    mock_iam.return_value = []
    mock_sg.return_value = []
    mock_ec2.return_value = []
    mock_roles.return_value = []

    collector = CloudCollector()

    resources = collector.collect()

    assert resources == []


# ==========================================================
# Multiple Resources
# ==========================================================

@patch.object(
    CloudCollector,
    "collect_iam_role_attachments",
)
@patch.object(
    CloudCollector,
    "collect_ec2_instances",
)
@patch.object(
    CloudCollector,
    "collect_security_groups",
)
@patch.object(
    CloudCollector,
    "collect_iam_resources",
)
@patch.object(
    CloudCollector,
    "collect_s3_resources",
)
def test_multiple_resources(
    mock_s3,
    mock_iam,
    mock_sg,
    mock_ec2,
    mock_roles,
):

    mock_s3.return_value = [
        {
            "resource_id": "bucket",
            "resource_type": "s3_bucket",
            "public_read": False,
            "public_write": False,
        }
    ]

    mock_iam.return_value = [
        {
            "resource_id": "policy",
            "resource_type": "iam_policy",
            "action": "s3:*",
        }
    ]

    mock_sg.return_value = [
        {
            "resource_id": "sg-1",
            "resource_type": "security_group",
            "ingress": {
                "cidr": "0.0.0.0/0"
            }
        }
    ]

    mock_ec2.return_value = [
        {
            "resource_id": "i-001",
            "resource_type": "ec2_instance",
        }
    ]

    mock_roles.return_value = [
        {
            "resource_id": "role-1",
            "resource_type": "iam_role",
        }
    ]

    collector = CloudCollector()

    resources = collector.collect()

    assert len(resources) == 5

    assert resources[0]["resource_type"] == "s3_bucket"
    assert resources[1]["resource_type"] == "iam_policy"
    assert resources[2]["resource_type"] == "security_group"
    assert resources[3]["resource_type"] == "ec2_instance"
    assert resources[4]["resource_type"] == "iam_role"


# ==========================================================
# Wave B - EC2 Collector
# ==========================================================

def test_collect_ec2_instances():

    collector = CloudCollector.__new__(CloudCollector)

    collector.ec2 = MagicMock()

    collector.ec2.describe_instances.return_value = {
        "Reservations": [
            {
                "Instances": [
                    {
                        "InstanceId": "i-001",
                        "InstanceType": "t2.micro",
                        "State": {
                            "Name": "running"
                        },
                    }
                ]
            }
        ]
    }

    with patch(
        "src.cloud.collector.normalize_resource"
    ) as mock_normalize:

        mock_normalize.return_value = {
            "resource_id": "i-001",
            "resource_type": "ec2_instance",
        }

        resources = collector.collect_ec2_instances()

    assert len(resources) == 1
    assert resources[0]["resource_id"] == "i-001"
    assert resources[0]["resource_type"] == "ec2_instance"

    mock_normalize.assert_called_once()


# ==========================================================
# Wave B - IAM Role Attachments
# ==========================================================

def test_collect_iam_role_attachments():

    collector = CloudCollector.__new__(CloudCollector)

    collector.iam = MagicMock()

    paginator = MagicMock()

    paginator.paginate.return_value = [
        {
            "Roles": [
                {
                    "RoleName": "TestRole",
                    "Arn": "arn:aws:iam::123456789012:role/TestRole",
                }
            ]
        }
    ]

    collector.iam.get_paginator.return_value = paginator

    collector.iam.list_attached_role_policies.return_value = {
        "AttachedPolicies": [
            {
                "PolicyName": "TestPolicy",
                "PolicyArn": "arn:aws:iam::aws:policy/TestPolicy",
            }
        ]
    }

    collector.iam.list_instance_profiles_for_role.return_value = {
        "InstanceProfiles": [
            {
                "InstanceProfileName": "TestProfile",
                "Arn": "arn:aws:iam::123456789012:instance-profile/TestProfile",
            }
        ]
    }

    with patch(
        "src.cloud.collector.normalize_resource"
    ) as mock_normalize:

        mock_normalize.return_value = {
            "resource_id": "TestRole",
            "resource_type": "iam_role",
        }

        resources = collector.collect_iam_role_attachments()

    assert len(resources) == 1
    assert resources[0]["resource_id"] == "TestRole"
    assert resources[0]["resource_type"] == "iam_role"

    mock_normalize.assert_called_once()


# ==========================================================
# Wave B - EC2 Resilience
# ==========================================================

def test_collect_ec2_instances_skips_bad_instance():

    collector = CloudCollector.__new__(CloudCollector)

    collector.ec2 = MagicMock()

    collector.ec2.describe_instances.return_value = {
        "Reservations": [
            {
                "Instances": [
                    {
                        "InstanceId": "bad-instance"
                    },
                    {
                        "InstanceId": "good-instance"
                    },
                ]
            }
        ]
    }

    def normalize(resource_type, instance):

        if instance["InstanceId"] == "bad-instance":
            raise ValueError("invalid instance")

        return {
            "resource_id": instance["InstanceId"],
            "resource_type": "ec2_instance",
        }

    with patch(
        "src.cloud.collector.normalize_resource",
        side_effect=normalize,
    ):

        resources = collector.collect_ec2_instances()

    assert len(resources) == 1
    assert resources[0]["resource_id"] == "good-instance"


# ==========================================================
# IAM policy document decoding
# ==========================================================

def test_normalize_iam_policy_decodes_url_encoded_document():

    raw = {
        "Statement": [
            {
                "Action": "s3:*"
            }
        ]
    }

    document = urllib.parse.quote(
        json.dumps(raw)
    )

    resource = normalize_resource(
        "iam_policy",
        "AdminPolicy",
        document,
    )

    assert resource["resource_type"] == "iam_policy"
    assert resource["action"] == "s3:*"


# ==========================================================
# IAM collection resilience
# ==========================================================

def test_collect_iam_resources_skips_unreadable_policy_and_continues():

    collector = CloudCollector.__new__(CloudCollector)

    collector.iam = MagicMock()

    paginator = MagicMock()

    paginator.paginate.return_value = [
        {
            "Policies": [
                {
                    "Arn": "arn:aws:iam::000000000000:policy/Bad",
                    "PolicyName": "Bad",
                },
                {
                    "Arn": "arn:aws:iam::000000000000:policy/Good",
                    "PolicyName": "Good",
                },
            ]
        }
    ]

    collector.iam.get_paginator.return_value = paginator

    good_document = urllib.parse.quote(
        json.dumps(
            {
                "Statement": [
                    {
                        "Action": "s3:*"
                    }
                ]
            }
        )
    )

    def get_policy(PolicyArn):

        if PolicyArn.endswith("Bad"):

            raise ClientError(
                {
                    "Error": {
                        "Code": "NoSuchEntity",
                        "Message": "gone",
                    }
                },
                "GetPolicy",
            )

        return {
            "Policy": {
                "DefaultVersionId": "v1"
            }
        }

    collector.iam.get_policy.side_effect = get_policy

    collector.iam.get_policy_version.return_value = {
        "PolicyVersion": {
            "Document": good_document
        }
    }

    resources = collector.collect_iam_resources()

    assert len(resources) == 1
    assert resources[0]["resource_id"] == "Good"


# ==========================================================
# Endpoint allowlist
# ==========================================================

def test_validate_endpoint_accepts_known_localstack_hosts():

    validate_endpoint("http://localhost:4566")
    validate_endpoint("http://127.0.0.1:4566")
    validate_endpoint("http://localstack:4566")


def test_validate_endpoint_rejects_arbitrary_urls():

    try:

        validate_endpoint(
            "http://evil.example.com:4566"
        )

    except ValueError:

        pass

    else:

        raise AssertionError(
            "expected ValueError for an unapproved endpoint"
        )