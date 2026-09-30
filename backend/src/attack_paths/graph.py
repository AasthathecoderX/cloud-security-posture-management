from typing import Any, Dict, List

import networkx as nx

from .edges import build_edges


def build_attack_graph(
    resources: List[Dict[str, Any]],
) -> nx.DiGraph:
    """
    Build a directed attack-path graph from normalized resources.

    NetworkX is used internally only. API responses should use
    plain dictionaries instead of exposing NetworkX objects.
    """

    graph = nx.DiGraph()

    # Add resource nodes
    for resource in resources:
        resource_id = resource.get("resource_id")

        if not resource_id:
            continue

        graph.add_node(
            str(resource_id),
            resource_type=resource.get(
                "resource_type"
            ),
        )

    # Add Internet as a derived entry point only when needed
    edges = build_edges(resources)

    for edge in edges:

        source = edge["source"]
        target = edge["target"]

        graph.add_node(source)
        graph.add_node(target)

        graph.add_edge(
            source,
            target,
            relationship=edge["relationship"],
        )

    return graph


def graph_to_links(
    graph: nx.DiGraph,
) -> List[Dict[str, str]]:
    """
    Convert graph relationships into API-safe dictionaries.
    """

    links = []

    for source, target, data in graph.edges(
        data=True
    ):
        links.append(
            {
                "source": str(source),
                "target": str(target),
                "relationship": str(
                    data.get("relationship", "")
                ),
            }
        )

    return links