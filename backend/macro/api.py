"""API (FastAPI) và phục vụ bản build tĩnh của web/ (ADR-001).

Chế độ dữ liệu theo từng trình duyệt (cookie `macro_data`, spec synthetic-data mục 2.3): mọi API
đọc số liệu dùng database giả lập khi cookie là `synthetic` và database đó đã nạp một kịch bản;
còn lại là số thật.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Cookie, FastAPI, HTTPException, Response
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from macro.backtest import BacktestResult, run_backtest
from macro.config import Settings, load_settings
from macro.dashboard import IndicatorCard, build_cards
from macro.db import connect, init_schema
from macro.scenario import SHOCKS, ScenarioResult, listed_shocks, simulate
from macro.synthetic import load as synthetic
from macro.synthetic.model import load_scenario, preset_names

MODE_COOKIE = "macro_data"
# Ở mức module: FastAPI đọc chú thích kiểu (chuỗi, do `from __future__`) theo globals của module.
ModeCookie = Annotated[str | None, Cookie(alias=MODE_COOKIE)]


class ScenarioPreset(BaseModel):
    name: str
    title: str
    seed: int


class DataMode(BaseModel):
    mode: str  # "real" | "synthetic"
    scenario: str | None = None
    seed: int | None = None
    scenarios: list[ScenarioPreset]


class LoadRequest(BaseModel):
    scenario: str
    seed: int | None = None


class ShockOption(BaseModel):
    id: str
    name: str
    unit: str
    default_size: float
    scope: str


class ShockList(BaseModel):
    shocks: list[ShockOption]
    no_real_data: list[str]  # yếu tố mở rộng chưa có số thật (chỉ khi xem số thật)


def _presets() -> list[ScenarioPreset]:
    presets = []
    for name in preset_names():
        scenario = load_scenario(name)
        presets.append(ScenarioPreset(name=name, title=scenario.title or name, seed=scenario.seed))
    return presets


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="macroeconomics")

    with connect(settings.database_url) as conn:
        init_schema(conn)

    def synthetic_state(cookie: str | None) -> tuple[str, int] | None:
        if cookie != "synthetic":
            return None
        return synthetic.loaded(settings.synthetic_database_url)

    def database(cookie: str | None) -> str:
        if synthetic_state(cookie) is not None:
            return settings.synthetic_database_url
        return settings.database_url

    @app.get("/api/health")
    def health() -> dict[str, str]:
        with connect(settings.database_url) as conn:
            conn.execute("SELECT 1")
        return {"status": "ok"}

    @app.get("/api/data-mode")
    def data_mode(macro_data: ModeCookie = None) -> DataMode:
        state = synthetic_state(macro_data)
        if state is None:
            return DataMode(mode="real", scenarios=_presets())
        return DataMode(mode="synthetic", scenario=state[0], seed=state[1], scenarios=_presets())

    @app.post("/api/synthetic/load")
    def load_synthetic(request: LoadRequest, response: Response) -> DataMode:
        if request.scenario not in preset_names():
            raise HTTPException(400, f"Không có kịch bản giả lập: {request.scenario}")
        if settings.synthetic_database_url == settings.database_url:
            raise HTTPException(409, "Từ chối: database giả lập trùng database số thật.")
        try:
            scenario, seed = synthetic.load(
                settings.synthetic_database_url, request.scenario, request.seed
            )
        except synthetic.Refused as exc:
            raise HTTPException(409, str(exc)) from exc
        response.set_cookie(MODE_COOKIE, "synthetic", path="/", samesite="lax")
        return DataMode(mode="synthetic", scenario=scenario.name, seed=seed, scenarios=_presets())

    @app.get("/api/indicators")
    def indicators(macro_data: ModeCookie = None) -> list[IndicatorCard]:
        with connect(database(macro_data)) as conn:
            return build_cards(conn)

    @app.get("/api/scenario")
    def scenario(
        shock: str, size: float | None = None, macro_data: ModeCookie = None
    ) -> ScenarioResult:
        if shock not in SHOCKS:
            raise HTTPException(400, f"Cú sốc không hợp lệ: {shock}")
        with connect(database(macro_data)) as conn:
            return simulate(conn, shock, SHOCKS[shock].default_size if size is None else size)

    @app.get("/api/backtest")
    def backtest(macro_data: ModeCookie = None) -> BacktestResult:
        with connect(database(macro_data)) as conn:
            return run_backtest(conn)

    @app.get("/api/scenario/shocks")
    def shocks(macro_data: ModeCookie = None) -> ShockList:
        real = synthetic_state(macro_data) is None
        with connect(database(macro_data)) as conn:
            listed, without = listed_shocks(conn)
        return ShockList(
            shocks=[
                ShockOption(
                    id=s.series_id,
                    name=s.name,
                    unit=s.unit,
                    default_size=s.default_size,
                    scope=s.scope,
                )
                for s in listed
            ],
            no_real_data=[s.name for s in without] if real else [],
        )

    if settings.web_dir.is_dir():
        app.mount("/", StaticFiles(directory=settings.web_dir, html=True), name="web")
    else:

        @app.get("/", response_class=PlainTextResponse)
        def web_missing() -> str:
            return f"Chưa có bản build web tại {settings.web_dir}: chạy `pnpm --dir web build`."

    return app
