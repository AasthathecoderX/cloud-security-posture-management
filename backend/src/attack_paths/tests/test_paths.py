import networkx as nx

from attack_paths.path_finder import find_attack_paths


def test_find_attack_path():

    graph = nx.DiGraph()

    graph.add_edge(
        "internet",
        "i-001",
    )

    graph.add_edge(
        "i-001",
        "role-1",
    )

    graph.add_edge(
        "role-1",
        "policy-1",
    )

    graph.add_edge(
        "policy-1",
        "bucket-1",
    )

    graph.nodes["i-001"]["resource_type"] = "ec2_instance"
    graph.nodes["role-1"]["resource_type"] = "iam_role"
    graph.nodes["policy-1"]["resource_type"] = "iam_policy"
    graph.nodes["bucket-1"]["resource_type"] = "s3_bucket"

    paths = find_attack_paths(
        graph,
        cutoff=5,
        max_paths=100,
    )

    assert paths == [
        [
            "internet",
            "i-001",
            "role-1",
            "policy-1",
            "bucket-1",
        ]
    ]


def test_no_attack_path():

    graph = nx.DiGraph()

    graph.add_node(
        "bucket-1",
        resource_type="s3_bucket",
    )

    paths = find_attack_paths(graph)

    assert paths == []


def test_path_cutoff_is_respected():

    graph = nx.DiGraph()

    graph.add_edge("internet", "i-001")
    graph.add_edge("i-001", "role-1")
    graph.add_edge("role-1", "policy-1")
    graph.add_edge("policy-1", "bucket-1")
    graph.add_edge("bucket-1", "extra-1")

    graph.nodes["i-001"]["resource_type"] = "ec2_instance"
    graph.nodes["role-1"]["resource_type"] = "iam_role"
    graph.nodes["policy-1"]["resource_type"] = "iam_policy"
    graph.nodes["bucket-1"]["resource_type"] = "s3_bucket"

    paths = find_attack_paths(
        graph,
        cutoff=3,
        max_paths=100,
    )

    assert paths == []

def test_max_paths_is_respected():

    graph = nx.DiGraph()

    # Create several different routes from the Internet
    # to separate sensitive S3 buckets.
    for index in range(10):

        instance = f"i-{index}"
        role = f"role-{index}"
        policy = f"policy-{index}"
        bucket = f"bucket-{index}"

        graph.add_edge(
            "internet",
            instance,
        )

        graph.add_edge(
            instance,
            role,
        )

        graph.add_edge(
            role,
            policy,
        )

        graph.add_edge(
            policy,
            bucket,
        )

        graph.nodes[instance][
            "resource_type"
        ] = "ec2_instance"

        graph.nodes[role][
            "resource_type"
        ] = "iam_role"

        graph.nodes[policy][
            "resource_type"
        ] = "iam_policy"

        graph.nodes[bucket][
            "resource_type"
        ] = "s3_bucket"

    paths = find_attack_paths(
        graph,
        cutoff=5,
        max_paths=3,
    )

    assert len(paths) == 3