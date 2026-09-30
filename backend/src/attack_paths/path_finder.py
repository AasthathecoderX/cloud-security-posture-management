from typing import Dict, List

import networkx as nx


DEFAULT_CUTOFF = 5
DEFAULT_MAX_PATHS = 100


def find_attack_paths(
    graph: nx.DiGraph,
    cutoff: int = DEFAULT_CUTOFF,
    max_paths: int = DEFAULT_MAX_PATHS,
) -> List[List[str]]:
    """
    Find bounded attack paths.

    Paths start from the derived Internet entry point and end at
    terminal sensitive resources.

    The search is bounded by:
    - cutoff: maximum number of edges in a path
    - max_paths: maximum number of returned paths
    """

    if "internet" not in graph:
        return []

    targets = _find_targets(graph)

    if not targets:
        return []

    paths: List[List[str]] = []

    for target in sorted(targets):

        try:
            target_paths = nx.all_simple_paths(
                graph,
                source="internet",
                target=target,
                cutoff=cutoff,
            )

            for path in target_paths:

                if len(paths) >= max_paths:
                    return paths

                paths.append(
                    [str(node) for node in path]
                )

        except nx.NetworkXNoPath:
            continue

    return paths


def _find_targets(
    graph: nx.DiGraph,
) -> List[str]:
    """
    Identify terminal sensitive resources.

    A sensitive resource is considered a target only when it has
    no supported downstream relationships in the graph.

    This prevents intermediate resources such as IAM roles from
    being reported as completed attack paths when a path continues
    to a more downstream sensitive resource.
    """

    targets = []

    for node, data in graph.nodes(data=True):

        if node == "internet":
            continue

        resource_type = data.get("resource_type")

        if resource_type not in {
            "iam_role",
            "s3_bucket",
        }:
            continue

        # Only terminal sensitive resources are targets.
        if graph.out_degree(node) == 0:
            targets.append(str(node))

    return targets