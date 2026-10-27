"""API (FastAPI) và phục vụ bản build tĩnh của web/ (ADR-001)."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles

from macro.config import Settings, load_settings
from macro.dashboard import IndicatorCard, build_cards
from macro.db import connect, init_schema
from macro.scenario import SHOCKS, ScenarioResult, simulate


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

    @app.get("/api/scenario")
    def scenario(shock: str, size: float | None = None) -> ScenarioResult:
        if shock not in SHOCKS:
            raise HTTPException(400, f"Cú sốc không hợp lệ: {shock}")
        with connect(settings.database_url) as conn:
            return simulate(conn, shock, SHOCKS[shock].default_size if size is None else size)

    @app.get("/api/scenario/shocks")
    def shocks() -> list[dict[str, object]]:
        return [
            {"id": s.series_id, "name": s.name, "unit": s.unit, "default_size": s.default_size}
            for s in SHOCKS.values()
        ]

    if settings.web_dir.is_dir():
        app.mount("/", StaticFiles(directory=settings.web_dir, html=True), name="web")
    else:

        @app.get("/", response_class=PlainTextResponse)
        def web_missing() -> str:
            return f"Chưa có bản build web tại {settings.web_dir}: chạy `pnpm --dir web build`."

    return app
