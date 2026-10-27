"""API (FastAPI) và phục vụ bản build tĩnh của web/ (ADR-001)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles

from macro.config import Settings, load_settings
from macro.dashboard import IndicatorCard, build_cards
from macro.db import connect, init_schema


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="macroeconomics")

    with connect(settings.database_url) as conn:
        init_schema(conn)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        with connect(settings.database_url) as conn:
            conn.execute("SELECT 1")
        return {"status": "ok"}

    @app.get("/api/indicators")
    def indicators() -> list[IndicatorCard]:
        with connect(settings.database_url) as conn:
            return build_cards(conn)

    if settings.web_dir.is_dir():
        app.mount("/", StaticFiles(directory=settings.web_dir, html=True), name="web")
    else:

        @app.get("/", response_class=PlainTextResponse)
        def web_missing() -> str:
            return f"Chưa có bản build web tại {settings.web_dir}: chạy `pnpm --dir web build`."

    return app
