from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from db import get_session
from models import Finding, Scan, ScanType
from routes import _load_owned_scan, get_current_user
from cloud.collector import collect_cloud_resources

from .graph import build_attack_graph, graph_to_links
from .nodes import build_node
from .path_finder import find_attack_paths
from .schemas import AttackPath, AttackPathResponse


router = APIRouter(
    prefix="/scans",
    tags=["attack-paths"],
)


@router.get(
    "/{scan_id}/attack-paths",
    response_model=AttackPathResponse,
)
def get_attack_paths(
    scan_id: UUID,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
) -> AttackPathResponse:

    # --------------------------------------------------
    # Load and authorize scan
    # --------------------------------------------------

    scan = _load_owned_scan(
        scan_id,
        session,
        user,
    )

    findings = session.exec(
        select(Finding).where(
            Finding.scan_id == scan.scan_id
        )
    ).all()

    finding_by_resource = {
        str(finding.resource_id): finding
        for finding in findings
    }

    # --------------------------------------------------
    # Load resources
    # --------------------------------------------------

    if scan.scan_type == ScanType.LIVE:
        try:
            resources = collect_cloud_resources()
        except Exception:
            # Attack-path generation should not expose
            # cloud-provider/SDK details through the API.
            resources = []

    else:
        # Static scans do not contain normalized cloud
        # relationship data in the database. Do not invent
        # relationships that are not actually stored.
        resources = [
            {
                "resource_id": finding.resource_id,
                "resource_type": finding.resource_type,
            }
            for finding in findings
        ]

    resources = _deduplicate_resources(resources)

    # --------------------------------------------------
    # Build graph
    # --------------------------------------------------

    graph = build_attack_graph(resources)

    # --------------------------------------------------
    # Build API nodes
    # --------------------------------------------------

    nodes = []

    for resource in resources:

        resource_id = str(
            resource.get("resource_id")
        )

        finding = finding_by_resource.get(
            resource_id
        )

        nodes.append(
            build_node(
                resource,
                finding,
            )
        )

    # --------------------------------------------------
    # Build links
    # --------------------------------------------------

    links = graph_to_links(graph)

    # --------------------------------------------------
    # Find bounded attack paths
    # --------------------------------------------------

    raw_paths = find_attack_paths(graph)

    paths = [
        AttackPath(
            id=f"path-{index}",
            nodes=path,
            severity=_path_severity(
                path,
                finding_by_resource,
            ),
        )
        for index, path in enumerate(
            raw_paths,
            start=1,
        )
    ]

    return AttackPathResponse(
        scan_id=str(scan.scan_id),
        nodes=nodes,
        links=links,
        paths=paths,
    )


def _deduplicate_resources(
    resources: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Remove duplicate resources deterministically."""

    seen = set()
    result = []

    for resource in resources:

        resource_id = resource.get(
            "resource_id"
        )

        resource_type = resource.get(
            "resource_type"
        )

        if not resource_id:
            continue

        key = (
            str(resource_id),
            str(resource_type),
        )

        if key in seen:
            continue

        seen.add(key)
        result.append(resource)

    return result


def _path_severity(
    path: List[str],
    finding_by_resource: Dict[str, Finding],
) -> str:
    """Return the highest finding severity present on a path."""

    severity_order = {
        "Critical": 4,
        "High": 3,
        "Medium": 2,
        "Low": 1,
    }

    severities = []

    for resource_id in path:

        finding = finding_by_resource.get(
            resource_id
        )

        if finding is not None:
            severities.append(
                finding.severity.value
            )

    if not severities:
        return "Low"

    return max(
        severities,
        key=lambda value: severity_order.get(
            value,
            0,
        ),
    )