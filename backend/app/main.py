from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .db import Base, make_engine, make_session_factory
from .errors import install_handlers
from .routers import activities, auth, comments, meetings, teams, todos


def create_app(database_url: str | None = None, docs: bool | None = None) -> FastAPI:
    """docs 를 비우면 DATABASE_URL 유무로 정한다: 로컬은 Swagger UI 를 켜고 배포는 끈다."""
    show_docs = (not config.is_deployed()) if docs is None else docs
    engine = make_engine(database_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        Base.metadata.create_all(engine)
        yield

    app = FastAPI(
        title="MeetingNote Pro",
        lifespan=lifespan,
        docs_url="/docs" if show_docs else None,
        redoc_url=None,
        openapi_url="/openapi.json" if show_docs else None,
    )
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)
    install_handlers(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for r in (auth, teams, meetings, todos, comments, activities):
        app.include_router(r.router, prefix="/api")

    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse("/login.html")

    if config.FRONTEND_DIR.exists():
        app.mount("/", StaticFiles(directory=config.FRONTEND_DIR, html=True), name="frontend")
    return app


app = create_app()
