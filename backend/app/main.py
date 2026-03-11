from __future__ import annotations

from collections.abc import Iterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.auth.dependencies import get_session
from backend.app.auth.router import router as auth_router
from backend.app.db import create_session_factory, ensure_database_schema_current, get_engine
from backend.app.market.router import router as market_router
from backend.app.market.service import MarketEngine
from backend.app.users.router import router as users_router
from backend.app.value_engine.router import router as value_engine_router
from backend.app.wallets.router import router as wallets_router


def create_app(
    *,
    engine: Engine | None = None,
    session_factory: sessionmaker[Session] | None = None,
    run_migration_check: bool = True,
) -> FastAPI:
    bound_engine = session_factory.kw.get("bind") if session_factory is not None else None
    database_engine = engine or bound_engine or get_engine()
    database_session_factory = session_factory or create_session_factory(database_engine)

    def get_app_session() -> Iterator[Session]:
        session = database_session_factory()
        try:
            yield session
        finally:
            session.close()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if run_migration_check:
            ensure_database_schema_current(database_engine)
        app.state.market_engine = MarketEngine()
        yield

    app = FastAPI(
        title="Global Talent Exchange API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.dependency_overrides[get_session] = get_app_session

    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(wallets_router)
    app.include_router(market_router)
    app.include_router(value_engine_router)

    @app.get("/health", tags=["health"])
    def read_health(session: Session = Depends(get_app_session)) -> dict[str, str]:
        session.execute(text("SELECT 1"))
        return {"status": "ok"}

    return app


app = create_app()
