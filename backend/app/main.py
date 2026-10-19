from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.v1.auth import router as auth_router
from app.api.v1.assets import router as assets_router
from app.api.v1.vulnerabilities import router as vulnerabilities_router
from app.api.v1.users import router as users_router
from app.api.v1.comments import router as comments_router
from app.api.v1.comments import delete_router as comments_delete_router
from app.api.v1.audit_logs import router as audit_logs_router
from app.api.v1.dashboard import router as dashboard_router
from app.db.database import get_db


app = FastAPI(
    title="VulnFlow API",
    description="API for the VulnFlow vulnerability management platform",
    version="0.1.0",
)

app.include_router(
    auth_router,
    prefix="/api/v1",
)


app.include_router(
    assets_router,
    prefix="/api/v1",
)


app.include_router(
    vulnerabilities_router,
    prefix="/api/v1",
)


app.include_router(
    users_router,
    prefix="/api/v1",
)


app.include_router(
    comments_router,
    prefix="/api/v1",
)


app.include_router(
    comments_delete_router,
    prefix="/api/v1",
)


app.include_router(
    audit_logs_router,
    prefix="/api/v1",
)


app.include_router(
    dashboard_router,
    prefix="/api/v1",
)


@app.get("/api/v1/health", tags=["Health"])
def health_check():
    return {
        "status": "ok",
        "service": "vulnflow-api",
    }


@app.get("/api/v1/health/db", tags=["Health"])
def database_health_check(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))

    return {
        "status": "ok",
        "database": "postgresql",
    }