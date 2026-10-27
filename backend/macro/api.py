"""API (FastAPI) và phục vụ bản build tĩnh của web/ (ADR-001)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from macro.config import Settings, load_settings
from macro.db import connect, init_schema


class IndicatorCard(BaseModel):
    """Một thẻ trên bảng tổng quan. Mọi con số đã được tính và định dạng sẵn ở backend."""

    series_id: str
    name: str
    value_text: str
    period_text: str
    change_prev_text: str | None = None
    change_yoy_text: str | None = None
    source_text: str
    status_text: str | None = None  # vd "Nguồn lỗi · …" (T-4); None khi nguồn bình thường


def build_cards(settings: Settings) -> list[IndicatorCard]:
    """Các thẻ của bảng tổng quan (tính năng overview-dashboard, chưa làm)."""
    return []


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
        return build_cards(settings)

    if settings.web_dir.is_dir():
        app.mount("/", StaticFiles(directory=settings.web_dir, html=True), name="web")
    else:

        @app.get("/", response_class=PlainTextResponse)
        def web_missing() -> str:
            return f"Chưa có bản build web tại {settings.web_dir}: chạy `pnpm --dir web build`."

    return app
