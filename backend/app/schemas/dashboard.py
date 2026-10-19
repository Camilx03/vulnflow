
from pydantic import BaseModel, Field


class DashboardStatsResponse(BaseModel):
    total_assets: int = Field(ge=0)
    total_vulnerabilities: int = Field(ge=0)
    affected_assets: int = Field(ge=0)
    unassigned_vulnerabilities: int = Field(ge=0)
    active_vulnerabilities: int = Field(ge=0)
    by_severity: dict[str, int]
    by_status: dict[str, int]
