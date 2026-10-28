"""Kịch bản giả lập: tệp YAML trong `scenarios/` (spec synthetic-data mục 2.1).

Quá trình sinh và quan hệ gài vào được khai báo trong KHÔNG GIAN MÔ HÌNH DÙNG: với cú sốc là x_t
sau phép biến đổi của `SHOCKS`, với biến kết quả là y_t của `outcome_series`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, model_validator

SCENARIO_DIR = Path(__file__).parent / "scenarios"


class Before(BaseModel):
    mean: float
    phi: float = 0.0
    sd: float


class Process(BaseModel):
    process: Literal["noise", "ar1", "random_walk", "bounded"]
    mean: float = 0.0
    phi: float = 0.0
    sd: float = 0.0
    start: float = 0.0  # random_walk: giá trị tháng đầu
    # bounded: trước `from` là before.mean + z_t, từ `from` là lower + (upper − lower)·sigmoid(z_t)
    before: Before | None = None
    from_: str | None = Field(default=None, alias="from")
    lower: float | None = None
    upper: float | None = None

    @model_validator(mode="after")
    def _bounded_is_complete(self) -> Process:
        if self.process == "bounded":
            if self.before is None or self.from_ is None:
                raise ValueError("bounded cần `before` và `from`")
            if self.lower is None or self.upper is None or self.lower >= self.upper:
                raise ValueError("bounded cần lower < upper")
        return self


class Relation(BaseModel):
    outcome: str
    shock: str
    beta: float
    lag: int = Field(ge=1)


class Event(BaseModel):
    series: str
    period: str  # "YYYY-MM"
    add: float


class Cpi(BaseModel):
    overlap_months: int = Field(default=24, ge=1)
    offset: float = 0.0


class Scenario(BaseModel):
    name: str
    title: str = ""
    seed: int
    start: str
    end: str
    series: dict[str, Process]
    relations: list[Relation] = []
    events: list[Event] = []
    missing: list[str] = []
    cpi: Cpi = Cpi()
    source_failure: bool = False  # lần lấy thứ hai ghi lỗi (T-4)

    @model_validator(mode="after")
    def _references_exist(self) -> Scenario:
        for r in self.relations:
            for sid in (r.outcome, r.shock):
                if sid not in self.series:
                    raise ValueError(f"quan hệ nhắc tới chuỗi chưa khai báo: {sid}")
        for e in self.events:
            if e.series not in self.series:
                raise ValueError(f"sự kiện nhắc tới chuỗi chưa khai báo: {e.series}")
        return self


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _raw(name_or_path: str, seen: tuple[str, ...] = ()) -> dict[str, Any]:
    path = Path(name_or_path)
    if not path.suffix:
        path = SCENARIO_DIR / f"{name_or_path}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"Không có kịch bản giả lập: {name_or_path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    parent = data.pop("extends", None)
    if parent is None:
        return data
    if parent in seen:
        raise ValueError(f"kịch bản kế thừa vòng: {' → '.join((*seen, parent))}")
    return _merge(_raw(parent, (*seen, parent)), data)


def load_scenario(name_or_path: str) -> Scenario:
    """Đọc kịch bản theo tên (trong `scenarios/`) hoặc đường dẫn tệp; xử lý `extends`."""
    return Scenario.model_validate(_raw(name_or_path))


def preset_names() -> list[str]:
    return sorted(p.stem for p in SCENARIO_DIR.glob("*.yaml"))
