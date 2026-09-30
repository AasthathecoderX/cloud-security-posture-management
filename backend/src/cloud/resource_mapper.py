"""
resource_mapper.py

Converts raw AWS(LocalStack) responses into the resource schema
expected by the existing Phase-1 Rule Engine.

Rule Engine Contract
--------------------

S3 Bucket
{
    "resource_id": "...",
    "resource_type": "s3_bucket",
    "public_read": True,
    "public_write": False
}

Security Group
{
    "resource_id": "...",
    "resource_type": "security_group",
    "ingress": {
        "cidr": "0.0.0.0/0"
    }
}

IAM Policy
{
    "resource_id": "...",
    "resource_type": "iam_policy",
    "action": "s3:*"
}
"""

from __future__ import annotations

import json
from typing import Any, Dict, List
from urllib.parse import unquote


# ==========================================================
# S3
# ==========================================================

def map_s3_bucket(
    bucket_name: str,
    acl: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Convert S3 bucket ACL into Rule Engine format.
    """

    public_read = False
    public_write = False

    grants = acl.get("Grants", [])

    for grant in grants:

        grantee = grant.get("Grantee", {})

        uri = grantee.get("URI", "")

        permission = grant.get("Permission", "")

        if "AllUsers" not in uri:
            continue

        if permission in ("READ", "FULL_CONTROL"):

            public_read = True

        if permission in ("WRITE", "FULL_CONTROL"):

            public_write = True

    return {

        "resource_id": bucket_name,

        "resource_type": "s3_bucket",

        "public_read": public_read,

        "public_write": public_write,
    }


# ==========================================================
# IAM
# ==========================================================

def map_iam_policy(
    policy_name: str,
    document: Dict[str, Any] | str,
) -> Dict[str, Any]:
    """
    Extract first IAM Action.

    Example

    Action:

        s3:*

    or

        ec2:DescribeInstances

    ``document`` is normally the raw ``PolicyVersion.Document`` from
    boto3's ``get_policy_version`` -- which IAM returns as a **URL-encoded
    JSON string**, not a parsed dict (this is documented AWS/boto3 IAM API
    behavior, mirrored by LocalStack). Decode it before treating it as a
    dict; a caller that already has a parsed dict (e.g. a hand-built test
    fixture) still works unchanged.
    """

    if isinstance(document, str):
        document = json.loads(unquote(document))

    action = ""

    statements = document.get("Statement", [])

    if not isinstance(statements, list):

        statements = [statements]

    for statement in statements:

        value = statement.get("Action")

        if value is None:
            continue

        if isinstance(value, list):

            action = value[0]

        else:

            action = value

        break

    return {

        "resource_id": policy_name,

        "resource_type": "iam_policy",

        "action": action,
    }


# ==========================================================
# Security Groups
# ==========================================================

def map_security_group(
    group: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Only the first CIDR is needed for Phase-1 rules.
    """

    cidr = ""

    permissions: List = group.get("IpPermissions", [])

    if permissions:

        ranges = permissions[0].get("IpRanges", [])

        if ranges:

            cidr = ranges[0].get("CidrIp", "")

    return {

        "resource_id": group["GroupId"],

        "resource_type": "security_group",

        "ingress": {

            "cidr": cidr
        }
    }


# ==========================================================
# Generic Dispatcher
# ==========================================================

RESOURCE_MAPPERS = {

    "s3_bucket": map_s3_bucket,

    "iam_policy": map_iam_policy,

    "security_group": map_security_group,
}

# ==========================================================
# EC2 Instances - Wave B
# ==========================================================

def map_ec2_instance(
    instance: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Convert an EC2 instance into the normalized resource format.

    Includes:
    - public/private IP
    - security group attachments
    - IAM instance profile ARN
    """

    security_groups = [
        group.get("GroupId")
        for group in instance.get("SecurityGroups", [])
        if group.get("GroupId")
    ]

    iam_profile = instance.get("IamInstanceProfile") or {}

    return {
        "resource_id": instance.get("InstanceId", ""),
        "resource_type": "ec2_instance",
        "public_ip": instance.get("PublicIpAddress"),
        "private_ip": instance.get("PrivateIpAddress"),
        "security_groups": security_groups,
        "iam_instance_profile_arn": iam_profile.get("Arn"),
    }


# ==========================================================
# IAM Role Attachments - Wave B
# ==========================================================

def map_role_attachment(
    role: Dict[str, Any],
    attached_policies: List[Dict[str, Any]],
    instance_profiles: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Convert IAM role attachment information into graph relationships.

    Produces:
    - ASSUMES relationship information
    - HAS_PERMISSION relationship information
    """

    role_name = role.get("RoleName", "")
    role_arn = role.get("Arn", "")

    policy_arns = [
        policy.get("PolicyArn")
        for policy in attached_policies
        if policy.get("PolicyArn")
    ]

    profile_arns = [
        profile.get("InstanceProfileArn")
        for profile in instance_profiles
        if profile.get("InstanceProfileArn")
    ]

    return {
        "resource_id": role_name,
        "resource_type": "iam_role",
        "role_arn": role_arn,
        "attached_policy_arns": policy_arns,
        "instance_profile_arns": profile_arns,
        "relationships": [
            *[
                {
                    "source": role_name,
                    "target": policy_arn,
                    "relationship": "HAS_PERMISSION",
                }
                for policy_arn in policy_arns
            ],
            *[
                {
                    "source": profile_arn,
                    "target": role_name,
                    "relationship": "ASSUMES",
                }
                for profile_arn in profile_arns
            ],
        ],
    }
    
    # ==========================================================
# Wave B mapper registration
# ==========================================================

RESOURCE_MAPPERS.update({
    "ec2_instance": map_ec2_instance,
    "iam_role": map_role_attachment,
})

def map_resource(
    resource_type: str,
    *args,
    **kwargs,
):
    """
    Generic dispatcher.

    Example

    map_resource("s3_bucket", bucket_name, acl)
    """

    mapper = RESOURCE_MAPPERS.get(resource_type)

    if mapper is None:

        raise ValueError(
            f"No mapper found for {resource_type}"
        )

    return mapper(*args, **kwargs)