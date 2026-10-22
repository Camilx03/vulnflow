import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
from app.db.database import SessionLocal, get_db
from app.core.config import settings
from app.services.login_rate_limit import cleanup_expired_login_attempts


logger = logging.getLogger(__name__)


LOGIN_CLEANUP_INTERVAL_SECONDS = 1800


def run_login_cleanup() -> int:
    with SessionLocal() as db:
        return cleanup_expired_login_attempts(db)


async def periodic_login_cleanup():
    while True:
        await asyncio.sleep(LOGIN_CLEANUP_INTERVAL_SECONDS)

        try:
            deleted = await asyncio.to_thread(
                run_login_cleanup
            )

            logger.info(
                "Login rate limit cleanup completed: %s records deleted",
                deleted,
            )
        except Exception:
            logger.exception(
                "Login rate limit cleanup failed"
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    cleanup_task = asyncio.create_task(
        periodic_login_cleanup()
    )

    try:
        yield
    finally:
        cleanup_task.cancel()

        with suppress(asyncio.CancelledError):
            await cleanup_task

app = FastAPI(
    title="VulnFlow API",
    description="API for the VulnFlow vulnerability management platform",
    version="0.1.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
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