"""``create_app()`` and the module-level ``app``: htmx pages plus a small /api, one process under Granian."""

import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.exceptions import HTTPException as StarletteHTTPException

from opportunity_radar.config import DATABASE_SCHEMA, LOG_DIR, LOG_LEVEL
from opportunity_radar.db import scalar, transaction
from opportunity_radar.pages.static_files import STATIC_DIR, CachedStaticFiles
from opportunity_radar.pages.templating import templates
from opportunity_radar.pages.urls import register_routes


def configure_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(sys.stderr, level=LOG_LEVEL)
    logger.add(LOG_DIR / "opportunity_radar.log", level=LOG_LEVEL, rotation="10 MB", retention=5)
    logger.add(LOG_DIR / "opportunity_radar_errors.log", level="ERROR", rotation="10 MB", retention=5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    with transaction() as connection:
        profiles = scalar(connection, "SELECT count(*) FROM user_profile")
    if not profiles:
        raise RuntimeError("No user profile. Run: python load_data.py")
    logger.info(f"opportunity_radar ready: schema {DATABASE_SCHEMA}")
    yield


def _wants_html(request: Request) -> bool:
    return not request.url.path.startswith("/api/") and "text/html" in request.headers.get("accept", "")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Opportunity Radar",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    app.mount("/static", CachedStaticFiles(directory=str(STATIC_DIR)), name="static")
    register_routes(app)

    def _error(request: Request, message: str, status: int):
        if _wants_html(request):
            return templates.TemplateResponse(request, "error.html", {"message": message}, status_code=status)
        return JSONResponse({"success": False, "error": message}, status_code=status)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        return _error(request, str(exc.detail), exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        return JSONResponse({"success": False, "error": exc.errors()}, status_code=422)

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        logger.exception(f"unhandled error on {request.method} {request.url.path}: {exc}")
        return _error(request, f"{type(exc).__name__}: {exc}", 500)

    return app


app = create_app()
