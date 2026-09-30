from attack_paths.edges import build_edges


def test_build_supported_edges():

    resources = [
        {
            "resource_id": "i-001",
            "resource_type": "ec2_instance",
            "iam_instance_profile_arn":
                "arn:aws:iam::123456789012:instance-profile/demo-profile",
            "security_groups": ["sg-001"],
        },
        {
            "resource_id": "demo-role",
            "resource_type": "iam_role",
            "instance_profile_arns": [
                "arn:aws:iam::123456789012:instance-profile/demo-profile"
            ],
            "attached_policy_arns": [
                "arn:aws:iam::123456789012:policy/demo-policy"
            ],
        },
        {
            "resource_id": "sg-001",
            "resource_type": "security_group",
            "ingress": {
                "cidr": "0.0.0.0/0"
            },
        },
    ]

    edges = build_edges(resources)

    assert {
        "source": "i-001",
        "target": "demo-role",
        "relationship": "ASSUMES",
    } in edges

    assert {
        "source": "demo-role",
        "target": "demo-policy",
        "relationship": "HAS_PERMISSION",
    } in edges

    assert {
        "source": "internet",
        "target": "i-001",
        "relationship": "EXPOSES",
    } in edges


def test_private_security_group_does_not_create_exposes_edge():

    resources = [
        {
            "resource_id": "i-001",
            "resource_type": "ec2_instance",
            "security_groups": ["sg-001"],
        },
        {
            "resource_id": "sg-001",
            "resource_type": "security_group",
            "ingress": {
                "cidr": "10.0.0.0/16"
            },
        },
    ]

    edges = build_edges(resources)

    assert not any(
        edge["relationship"] == "EXPOSES"
        for edge in edges
    )


def test_duplicate_edges_are_removed():

    resources = [
        {
            "resource_id": "role-1",
            "resource_type": "iam_role",
            "attached_policy_arns": [
                "arn:aws:iam::123456789012:policy/demo"
            ],
        },
        {
            "resource_id": "role-1",
            "resource_type": "iam_role",
            "attached_policy_arns": [
                "arn:aws:iam::123456789012:policy/demo"
            ],
        },
    ]

    edges = build_edges(resources)

    matching = [
        edge
        for edge in edges
        if edge["source"] == "role-1"
        and edge["target"] == "demo"
        and edge["relationship"] == "HAS_PERMISSION"
    ]

    assert len(matching) == 1