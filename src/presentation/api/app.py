from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import contextlib
from pathlib import Path

from ..api.middleware.rate_limit import RateLimitMiddleware
from ..api.routers import auth, links, redirect, projects
from ..errors import application_error_handler
from ...application.errors.errors import ApplicationError
from ...infrastructure.cache.redis_client import redis_client
from ...infrastructure.db.engine import engine
from ...infrastructure.settings import settings
from ...infrastructure.jobs.purge_expired_links_job import PurgeExpiredLinksJob
from ...infrastructure.cache.link_cache import LinkCache
from ...infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork


def create_app() -> FastAPI:
    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI):
        await redis_client.connect()
        cache = LinkCache()
        uow_factory = SqlAlchemyUnitOfWork
        app.state.purge_job = PurgeExpiredLinksJob(
            uow_factory=uow_factory,
            cache=cache,
            interval_sec=settings.PURGE_INTERVAL_SEC,
        )
        await app.state.purge_job.start()
        yield
        if hasattr(app.state, "purge_job"):
            await app.state.purge_job.stop()
        await redis_client.disconnect()
        await engine.dispose()

    app = FastAPI(
        title="Link Shortener Service",
        description="Link shortener service",
        version="0.1.0",
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    if settings.CORS_ORIGINS:
        origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.add_middleware(RateLimitMiddleware)

    app.add_exception_handler(ApplicationError, application_error_handler)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    static_dir = Path(__file__).parent.parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(str(static_dir / "index.html"))

    app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
    app.include_router(links.router, prefix="/links", tags=["Links"])
    app.include_router(projects.router, prefix="/projects", tags=["Projects"])
    app.include_router(redirect.router, prefix=f"/{settings.SHORT_LINK_PREFIX}", tags=["Redirect"])

    return app


app = create_app()
