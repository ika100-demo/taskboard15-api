"""FastAPI entry point for taskboard15-api."""

from __future__ import annotations

import asyncio
import os

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel

from . import __version__
from .db import Database, DatabaseUnavailable
from .logging_config import configure_logging
from .metrics import MetricsMiddleware
from .tasks import TaskStore
from .tasks import router as tasks_router
from .tracing import configure_tracing, tracing_enabled

configure_logging(level=os.environ.get("LOG_LEVEL", "INFO"))
if tracing_enabled():
    configure_tracing()

log = structlog.get_logger()


class HealthResponse(BaseModel):
    status: str


def create_app(database_url: str | None = None) -> FastAPI:
    """Build the application; `None` reads `DATABASE_URL` from the environment."""
    url = database_url if database_url is not None else os.environ.get("DATABASE_URL")
    if not url:
        log.warning("database_url_missing")

    app = FastAPI(title="taskboard15-api", version=__version__)
    app.add_middleware(MetricsMiddleware)
    if tracing_enabled():
        FastAPIInstrumentor.instrument_app(app)
    db = Database(url)
    task_store = TaskStore(db)
    app.state.db = db
    app.state.task_store = task_store
    app.include_router(tasks_router)

    @app.exception_handler(DatabaseUnavailable)
    async def _database_unavailable(request: Request, exc: DatabaseUnavailable) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": "database unavailable"})

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        """Liveness probe — returns 200 as long as the process is responding."""
        return HealthResponse(status="ok")

    def _check_database() -> None:
        task_store.ensure_schema()
        db.ping()

    @app.get("/ready", response_model=HealthResponse)
    async def ready() -> HealthResponse | JSONResponse:
        """Readiness probe — 200 when the database answers and the schema exists."""
        try:
            await asyncio.wait_for(asyncio.to_thread(_check_database), timeout=1.0)
        except (DatabaseUnavailable, TimeoutError):
            return JSONResponse(status_code=503, content={"status": "not ready"})
        return HealthResponse(status="ready")

    @app.get("/ping")
    def ping() -> dict[str, str]:
        """Simple ping endpoint."""
        return {"pong": "taskboard15-api"}

    @app.get("/metrics")
    def metrics() -> Response:
        """Prometheus scrape endpoint."""
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


app = create_app()
