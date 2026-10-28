"""Bản đồ ảnh hưởng (spec influence-map): yếu tố nào đang đẩy lên, kéo xuống biến trung tâm.

Với tháng đang xem m và yếu tố s (mô hình v1, ước lượng riêng từng yếu tố trên toàn bộ dữ liệu):

- diễn biến của yếu tố: Σ_{t=m−11..m} x_t (đơn vị cú sốc, vd tổng thay đổi log %);
- đóng góp vào trung tâm: Σ_{t=m−11..m−1} β_{m−t}·x_t — cùng công thức với trang kiểm chứng
  (mốc cắt m − 12, tầm 1..11), β là phản ứng của trang giả lập với cú sốc 1 đơn vị;
- "chưa chắc" khi khoảng tin cậy 90% của phản ứng tại tầm 12 chứa 0.

Màu theo tác động lên trung tâm (dấu của đóng góp), không theo hướng của yếu tố. Các đóng góp
không cộng lại được: mỗi yếu tố ước lượng riêng nên có thể đếm trùng.
"""

from __future__ import annotations

import math
from typing import Literal

import numpy as np
import pandas as pd
import psycopg
from pydantic import BaseModel

from macro.numbers import vn_number, vn_signed
from macro.scenario import (
    HORIZONS,
    MIN_OBSERVATIONS,
    OUTCOMES,
    SHOCKS,
    Z90,
    has_data,
    listed_shocks,
    load_monthly,
    local_projection,
    outcome_series,
)

H = 12
R_MIN, R_MAX = 12.0, 48.0  # bán kính bong bóng (đơn vị SVG); diện tích tỷ lệ với |đóng góp|
NOT_ADDITIVE = "Ảnh hưởng riêng của từng yếu tố, không cộng lại được."
LOOKBACK = (
    "Nhìn lại bằng mô hình hôm nay (ước lượng trên toàn bộ dữ liệu), không phải dự báo lúc đó."
)
DEFAULT_CENTERS = ("vn.gdp_yoy", "vn.vnindex")

Effect = Literal["up", "down", "uncertain", "missing"]
EFFECT_TEXT = {
    "up": "đẩy lên",
    "down": "kéo xuống",
    "uncertain": "chưa chắc",
    "missing": "thiếu dữ liệu",
}


class Bubble(BaseModel):
    series_id: str
    name: str
    short_name: str
    unit: str
    scope: str
    default_size: float
    effect: Effect
    effect_text: str
    shock_change: float | None = None
    shock_change_text: str = ""
    contribution: float | None = None
    contribution_text: str = ""
    beta_text: str = ""  # tầm 12, với cú sốc độ lớn mặc định
    radius: float = R_MIN
    link: float = 0.0  # 0..1: độ đậm đường nối, theo |phản ứng tầm 12| chuẩn hoá


class CenterOption(BaseModel):
    series_id: str
    name: str


class InfluenceResult(BaseModel):
    center: str
    center_name: str
    unit: str
    centers: list[CenterOption]
    month: str | None = None  # "YYYY-MM"
    months: list[str] = []
    level: float | None = None
    level_text: str = ""
    change: float | None = None
    change_text: str = ""
    insufficient_text: str | None = None
    bubbles: list[Bubble] = []
    ranking: list[str] = []  # series_id theo |đóng góp| giảm dần
    no_real_data: list[str] = []
    not_additive: str = NOT_ADDITIVE
    lookback: str = LOOKBACK


def _key(month: pd.Period) -> str:
    return f"{month.year:04d}-{month.month:02d}"


def _short(name: str) -> str:
    return name.split(" (")[0]


def default_center(conn: psycopg.Connection[dict]) -> str:
    for series_id in DEFAULT_CENTERS:
        if has_data(conn, series_id):
            return series_id
    return DEFAULT_CENTERS[-1]


def _level_text(series_id: str, y: float, unit: str) -> str:
    if series_id == "vn.vnindex":  # y = 100·log(điểm)
        return f"{vn_number(math.exp(y / 100), 2)} điểm"
    return f"{vn_number(y, 2)} {'%' if unit == 'điểm %' else unit}"


def _bubble(
    shock_id: str, y: pd.Series, month: pd.Period, conn: psycopg.Connection[dict]
) -> Bubble:
    shock = SHOCKS[shock_id]
    bubble = Bubble(
        series_id=shock_id,
        name=shock.name,
        short_name=_short(shock.name),
        unit=shock.unit,
        scope=shock.scope,
        default_size=shock.default_size,
        effect="missing",
        effect_text=EFFECT_TEXT["missing"],
    )
    x = shock.transform(load_monthly(conn, shock_id))
    if x.dropna().empty:
        return bubble
    estimates = {h: local_projection(y, x, h) for h in HORIZONS}
    if any(np.isnan(e[0]) or e[2] < MIN_OBSERVATIONS for e in estimates.values()):
        return bubble

    def value(t: pd.Period) -> float:
        v = x.get(t)
        return 0.0 if v is None or np.isnan(v) else float(v)

    change = sum(value(month - k) for k in range(H))
    contribution = sum(estimates[k][0] * value(month - k) for k in range(1, H))
    beta, se = estimates[H][0], estimates[H][1]
    uncertain = beta - Z90 * se <= 0 <= beta + Z90 * se
    effect: Effect = "uncertain" if uncertain else ("up" if contribution > 0 else "down")
    arrow = "▲" if change > 0 else ("▼" if change < 0 else "■")
    size = shock.default_size
    bubble.effect = effect
    bubble.effect_text = EFFECT_TEXT[effect]
    bubble.shock_change = change
    bubble.shock_change_text = f"{arrow} {vn_signed(change, 1)} {shock.unit} trong 12 tháng"
    bubble.contribution = contribution
    bubble.contribution_text = vn_signed(contribution, 2)
    bubble.beta_text = (
        f"Cú sốc {vn_signed(size, 1)} {shock.unit} → sau 12 tháng {vn_signed(size * beta, 2)}"
        f" [{vn_number(size * (beta - Z90 * se), 2)}; {vn_number(size * (beta + Z90 * se), 2)}]"
        f" · {estimates[H][2]} quan sát"
    )
    bubble.link = abs(size * beta)
    return bubble


def influence(
    conn: psycopg.Connection[dict],
    center: str | None = None,
    month: str | None = None,
    *,
    real: bool = True,
) -> InfluenceResult:
    outcomes = {o.series_id: o for o in OUTCOMES}
    center = center if center in outcomes else default_center(conn)
    outcome = outcomes[center]
    listed, without = listed_shocks(conn)
    result = InfluenceResult(
        center=center,
        center_name=outcome.name,
        unit=outcome.unit,
        centers=[CenterOption(series_id=o.series_id, name=o.name) for o in OUTCOMES],
        no_real_data=[s.name for s in without] if real else [],
    )
    insufficient = f"Chưa đủ dữ liệu cho {outcome.name}."
    y, reason, _ = outcome_series(conn, center)
    observed = y.dropna() if reason is None else pd.Series(dtype=float)
    if len(observed) < MIN_OBSERVATIONS + H:
        result.insufficient_text = insufficient
        return result
    result.months = [_key(p) for p in observed.index]
    chosen = pd.Period(month, freq="M") if month in result.months else observed.index[-1]
    result.month = _key(chosen)
    current = float(observed.to_dict()[chosen])
    result.level = current
    result.level_text = _level_text(center, current, outcome.unit)
    before = observed.get(chosen - H)
    if before is not None:
        result.change = current - float(before)
        result.change_text = f"{vn_signed(result.change, 2)} {outcome.unit} trong 12 tháng"

    bubbles = [_bubble(s.series_id, y, chosen, conn) for s in listed if s.series_id != center]
    sized = [b for b in bubbles if b.contribution is not None]
    largest = max((abs(b.contribution or 0.0) for b in sized), default=0.0)
    strongest = max((b.link for b in sized), default=0.0)
    for b in sized:
        share = abs(b.contribution or 0.0) / largest if largest > 0 else 0.0
        b.radius = R_MIN + (R_MAX - R_MIN) * math.sqrt(share)
        b.link = b.link / strongest if strongest > 0 else 0.0
    result.bubbles = bubbles
    result.ranking = [
        b.series_id for b in sorted(sized, key=lambda b: abs(b.contribution or 0.0), reverse=True)
    ]
    return result
