from attack_paths.graph import build_attack_graph, graph_to_links


def test_build_attack_graph():

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
            "resource_id": "demo-policy",
            "resource_type": "iam_policy",
        },
        {
            "resource_id": "sg-001",
            "resource_type": "security_group",
            "ingress": {
                "cidr": "0.0.0.0/0"
            },
        },
    ]

    graph = build_attack_graph(resources)

    assert "i-001" in graph
    assert "demo-role" in graph
    assert "demo-policy" in graph
    assert "sg-001" in graph
    assert "internet" in graph

    assert graph.has_edge(
        "i-001",
        "demo-role",
    )

    assert graph.has_edge(
        "demo-role",
        "demo-policy",
    )

    assert graph.has_edge(
        "internet",
        "i-001",
    )


def test_graph_to_links():

    resources = [
        {
            "resource_id": "i-001",
            "resource_type": "ec2_instance",
            "iam_instance_profile_arn":
                "arn:aws:iam::123456789012:instance-profile/demo-profile",
        },
        {
            "resource_id": "demo-role",
            "resource_type": "iam_role",
            "instance_profile_arns": [
                "arn:aws:iam::123456789012:instance-profile/demo-profile"
            ],
        },
    ]

    graph = build_attack_graph(resources)

    links = graph_to_links(graph)

    assert links == [
        {
            "source": "i-001",
            "target": "demo-role",
            "relationship": "ASSUMES",
        }
    ]