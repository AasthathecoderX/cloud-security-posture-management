from typing import Any, Dict, List


def build_edges(resources: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Build supported attack-path relationships.

    Supported relationships:
    EC2 -> IAM Role        ASSUMES
    IAM Role -> IAM Policy HAS_PERMISSION
    IAM Policy -> S3       ACCESSES
    Internet -> EC2        EXPOSES
    """

    edges: List[Dict[str, str]] = []

    # --------------------------------------------------
    # Build instance-profile -> role lookup
    # --------------------------------------------------

    profile_to_role = {}

    for resource in resources:
        if resource.get("resource_type") != "iam_role":
            continue

        role_id = resource.get("resource_id")

        for profile_arn in resource.get("instance_profile_arns", []):
            if role_id and profile_arn:
                profile_to_role[str(profile_arn)] = str(role_id)

    # --------------------------------------------------
    # Build relationships
    # --------------------------------------------------

    for resource in resources:

        resource_type = resource.get("resource_type")
        resource_id = resource.get("resource_id")

        if not resource_id:
            continue

        # --------------------------------------------------
        # EC2 -> IAM Role
        # --------------------------------------------------

        if resource_type == "ec2_instance":

            profile_arn = resource.get(
                "iam_instance_profile_arn"
            )

            if profile_arn:

                role_id = profile_to_role.get(
                    str(profile_arn)
                )

                if role_id:
                    edges.append(
                        {
                            "source": str(resource_id),
                            "target": role_id,
                            "relationship": "ASSUMES",
                        }
                    )

        # --------------------------------------------------
        # IAM Role -> IAM Policy
        # --------------------------------------------------

        elif resource_type == "iam_role":

            policies = resource.get(
                "attached_policy_arns",
                [],
            )

            for policy_arn in policies:

                if not policy_arn:
                    continue

                edges.append(
                    {
                        "source": str(resource_id),
                        "target": _extract_name(
                            str(policy_arn)
                        ),
                        "relationship": "HAS_PERMISSION",
                    }
                )

        # --------------------------------------------------
        # IAM Policy -> S3 Bucket
        # --------------------------------------------------

        elif resource_type == "iam_policy":

            buckets = resource.get(
                "accessed_buckets",
                [],
            )

            for bucket in buckets:

                if isinstance(bucket, dict):
                    bucket_id = bucket.get(
                        "resource_id"
                    )
                else:
                    bucket_id = bucket

                if bucket_id:
                    edges.append(
                        {
                            "source": str(resource_id),
                            "target": str(bucket_id),
                            "relationship": "ACCESSES",
                        }
                    )

        # --------------------------------------------------
        # Internet -> EC2
        # --------------------------------------------------

        elif resource_type == "security_group":

            if not _is_public_security_group(resource):
                continue

            for instance in resources:

                if instance.get(
                    "resource_type"
                ) != "ec2_instance":
                    continue

                security_groups = instance.get(
                    "security_groups",
                    [],
                )

                if resource_id in security_groups:

                    edges.append(
                        {
                            "source": "internet",
                            "target": str(
                                instance["resource_id"]
                            ),
                            "relationship": "EXPOSES",
                        }
                    )

    return _deduplicate_edges(edges)


def _extract_name(value: str) -> str:
    """Extract the final name from an ARN."""

    value = str(value)

    if "/" in value:
        return value.rsplit("/", 1)[-1]

    if ":" in value:
        return value.rsplit(":", 1)[-1]

    return value


def _is_public_security_group(
    resource: Dict[str, Any],
) -> bool:
    """Return True when the security group allows 0.0.0.0/0."""

    ingress = resource.get("ingress", {})

    if isinstance(ingress, dict):
        return ingress.get("cidr") == "0.0.0.0/0"

    return False


def _deduplicate_edges(
    edges: List[Dict[str, str]],
) -> List[Dict[str, str]]:
    """Remove duplicate relationships deterministically."""

    seen = set()
    result = []

    for edge in edges:

        key = (
            edge["source"],
            edge["target"],
            edge["relationship"],
        )

        if key in seen:
            continue

        seen.add(key)
        result.append(edge)

    return result