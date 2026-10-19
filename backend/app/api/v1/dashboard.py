
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.database import get_db
from app.models.asset import Asset
from app.models.user import User
from app.models.vulnerability import (
    Vulnerability,
    VulnerabilitySeverity,
    VulnerabilityStatus,
)
from app.schemas.dashboard import DashboardStatsResponse


router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)


@router.get(
    "/stats",
    response_model=DashboardStatsResponse,
)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total_assets = db.scalar(
        select(func.count(Asset.id))
    ) or 0

    total_vulnerabilities = db.scalar(
        select(func.count(Vulnerability.id))
    ) or 0

    affected_assets = db.scalar(
        select(func.count(func.distinct(Vulnerability.asset_id)))
    ) or 0

    unassigned_vulnerabilities = db.scalar(
        select(func.count(Vulnerability.id)).where(
            Vulnerability.assigned_user_id.is_(None)
        )
    ) or 0

    active_vulnerabilities = db.scalar(
        select(func.count(Vulnerability.id)).where(
            Vulnerability.status.in_([
                VulnerabilityStatus.OPEN,
                VulnerabilityStatus.IN_PROGRESS,
            ])
        )
    ) or 0

    severity_counts = db.execute(
        select(
            Vulnerability.severity,
            func.count(Vulnerability.id),
        ).group_by(Vulnerability.severity)
    ).all()

    status_counts = db.execute(
        select(
            Vulnerability.status,
            func.count(Vulnerability.id),
        ).group_by(Vulnerability.status)
    ).all()

    by_severity = {
        severity.value: 0
        for severity in VulnerabilitySeverity
    }

    for severity, count in severity_counts:
        by_severity[severity.value] = count

    by_status = {
        vulnerability_status.value: 0
        for vulnerability_status in VulnerabilityStatus
    }

    for vulnerability_status, count in status_counts:
        by_status[vulnerability_status.value] = count

    return DashboardStatsResponse(
        total_assets=total_assets,
        total_vulnerabilities=total_vulnerabilities,
        affected_assets=affected_assets,
        unassigned_vulnerabilities=unassigned_vulnerabilities,
        active_vulnerabilities=active_vulnerabilities,
        by_severity=by_severity,
        by_status=by_status,
    )
