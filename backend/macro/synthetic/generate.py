"""Sinh dữ liệu giả lập từ kịch bản (spec synthetic-data mục 2.1–2.2).

1. Sinh từng chuỗi trong không gian mô hình, tháng theo tháng, theo thứ tự khai báo; quan hệ gài
   vào dùng giá trị (đã sinh) của chuỗi nguồn ở tháng t − lag.
2. Đổi ngược về chuỗi gốc theo đơn vị của nguồn thật, để mọi trang chạy trên dữ liệu giả như
   trên số thật: phép biến đổi của mô hình áp lên chuỗi gốc cho lại đúng chuỗi đã sinh.

`impulse_response` tính đáp án thật cho phép đo `recover`: phản ứng của y_{t+h} − y_{t−1} khi
phần nhiễu của cú sốc ở tháng t tăng 1 đơn vị — đúng đại lượng local projections ước lượng.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from macro.connectors.base import Observation
from macro.connectors.dates import month_end
from macro.synthetic.model import Relation, Scenario

Kind = Literal["log_change", "diff", "level", "yoy_level", "log100", "cpi"]


@dataclass(frozen=True)
class Meta:
    name: str
    unit: str
    kind: Kind  # cách đổi từ không gian mô hình về chuỗi gốc
    base: float = 0.0  # mức gốc của tháng đầu (log_change, diff, yoy_level)


# Chuỗi giả lập dùng được và cách đổi về chuỗi gốc; khớp phép biến đổi trong `macro.scenario`.
SERIES: dict[str, Meta] = {
    "global.brent": Meta("Giá dầu Brent", "USD/thùng", "log_change", 60),
    "us.ust10y": Meta("Lợi suất trái phiếu Mỹ 10 năm", "%", "diff", 3),
    "us.usd_broad": Meta("Chỉ số USD rộng (Fed)", "chỉ số", "log_change", 100),
    "global.demand": Meta("Cầu thế giới (SX công nghiệp đối tác, so cùng kỳ)", "%", "diff", 3),
    "vn.policy_rate": Meta("Lãi suất điều hành NHNN", "%/năm", "diff", 6),
    "vn.usdvnd": Meta("Tỷ giá USD/VND", "đồng", "log_change", 23000),
    "vn.fdi_yoy": Meta("FDI giải ngân (so cùng kỳ)", "%", "diff", 10),
    "vn.credit_growth": Meta("Tăng trưởng tín dụng (so cùng kỳ)", "%", "diff", 14),
    "vn.public_investment": Meta("Giải ngân đầu tư công (so cùng kỳ)", "%", "diff", 10),
    "vn.gdp_yoy": Meta("GDP (so cùng kỳ)", "%", "level"),
    "vn.exports": Meta("Xuất khẩu", "triệu USD", "yoy_level", 10000),
    "vn.iip": Meta("Sản xuất công nghiệp (IIP, so cùng kỳ)", "%", "level"),
    "vn.pmi_mfg": Meta("PMI sản xuất", "điểm", "level"),
    "vn.vnindex": Meta("VN-Index", "điểm", "log100"),
    "vn.cpi_yoy_long": Meta("CPI (so cùng kỳ)", "%", "cpi"),
}

# Hai chuỗi thành phần của CPI (spec scenario-simulation: nối IMF với dautubenvung).
CPI_PARTS = {"vn.cpi_yoy_imf": "CPI (so cùng kỳ, IMF)", "vn.cpi_yoy": "CPI (so cùng kỳ)"}
CPI_IMF_ENDS_BEFORE_END = 24  # tháng: IMF dừng 24 tháng trước cuối kịch bản


def months(scenario: Scenario) -> pd.PeriodIndex:
    return pd.period_range(scenario.start, scenario.end, freq="M")


def model_space(scenario: Scenario, seed: int | None = None) -> pd.DataFrame:
    """Các chuỗi trong không gian mô hình, mỗi cột một chuỗi, chỉ mục là tháng."""
    for sid in scenario.series:
        if sid not in SERIES:
            raise ValueError(f"Chuỗi giả lập chưa hỗ trợ: {sid}")
    index = months(scenario)
    ids = list(scenario.series)
    rng = np.random.default_rng(scenario.seed if seed is None else seed)
    noise = rng.standard_normal((len(index), len(ids)))
    incoming: dict[str, list[Relation]] = {sid: [] for sid in ids}
    for r in scenario.relations:
        incoming[r.outcome].append(r)
    events = {(e.series, pd.Period(e.period, freq="M")): e.add for e in scenario.events}
    values = {sid: np.zeros(len(index)) for sid in ids}
    state = {sid: 0.0 for sid in ids}  # z_t của bounded

    for t, month in enumerate(index):
        for j, sid in enumerate(ids):
            p = scenario.series[sid]
            push = sum(r.beta * values[r.shock][t - r.lag] for r in incoming[sid] if t - r.lag >= 0)
            e = noise[t, j]
            if p.process == "noise":
                v = p.mean + p.sd * e + push
            elif p.process == "ar1":
                prev = values[sid][t - 1] if t else p.mean
                v = p.mean + p.phi * (prev - p.mean) + p.sd * e + push
            elif p.process == "random_walk":
                v = (values[sid][t - 1] if t else p.start) + p.sd * e + push
            else:  # bounded
                assert p.before is not None and p.lower is not None and p.upper is not None
                z = p.before.phi * state[sid] + p.before.sd * e + push
                state[sid] = z
                if month < pd.Period(p.from_, freq="M"):
                    v = p.before.mean + z
                else:
                    v = p.lower + (p.upper - p.lower) / (1 + math.exp(-z))
            values[sid][t] = v + events.get((sid, month), 0.0)
    return pd.DataFrame(values, index=index)


def _to_source(sid: str, y: pd.Series) -> pd.Series:
    meta = SERIES[sid]
    if meta.kind == "log_change":
        x = y.copy()
        x.iloc[0] = 0.0
        return meta.base * np.exp(x.cumsum() / 100)
    if meta.kind == "diff":
        x = y.copy()
        x.iloc[0] = 0.0
        return meta.base + x.cumsum()
    if meta.kind == "log100":
        return np.exp(y / 100)
    if meta.kind == "yoy_level":
        level = np.empty(len(y))
        for t in range(len(y)):
            level[t] = meta.base if t < 12 else level[t - 12] * (1 + y.iloc[t] / 100)
        return pd.Series(level, index=y.index)
    return y


def observations(scenario: Scenario, seed: int | None = None) -> list[Observation]:
    """Chuỗi gốc theo `series_id` của nguồn thật, kỳ là ngày cuối tháng."""
    frame = model_space(scenario, seed)
    out: list[Observation] = []

    def emit(series_id: str, values: pd.Series) -> None:
        if series_id in scenario.missing:
            return
        for month, value in values.items():
            assert isinstance(month, pd.Period)
            out.append(Observation(series_id, month_end(month.year, month.month), float(value)))

    for sid in frame.columns:
        if sid in scenario.missing:
            continue
        if SERIES[sid].kind != "cpi":
            emit(sid, _to_source(sid, frame[sid]))
            continue
        y = frame[sid]
        imf_end = y.index[-1] - CPI_IMF_ENDS_BEFORE_END
        local_start = imf_end - scenario.cpi.overlap_months + 1
        emit("vn.cpi_yoy_imf", y[y.index <= imf_end])
        local = y[y.index >= local_start].copy()
        local[local.index <= imf_end] += scenario.cpi.offset
        emit("vn.cpi_yoy", local)
    return out


def output_series(scenario: Scenario) -> dict[str, str]:
    """`series_id` → tên, của các chuỗi kịch bản này ghi vào database."""
    names: dict[str, str] = {}
    for sid in scenario.series:
        if sid in scenario.missing:
            continue
        if SERIES[sid].kind == "cpi":
            names.update({k: v for k, v in CPI_PARTS.items() if k not in scenario.missing})
        else:
            names[sid] = SERIES[sid].name
    return names


def impulse_response(
    scenario: Scenario, relations: list[Relation], shock: str, outcome: str, horizons: int = 12
) -> list[float]:
    """Phản ứng cộng dồn của `outcome` tại h = 1..horizons với một đơn vị nhiễu của `shock`.

    Chỉ đúng cho các quá trình tuyến tính (không có `bounded` trên đường truyền).
    """
    ids = list(scenario.series)
    dev = {sid: np.zeros(horizons + 1) for sid in ids}
    incoming: dict[str, list[Relation]] = {sid: [] for sid in ids}
    for r in relations:
        if r.outcome in incoming and r.shock in incoming:
            incoming[r.outcome].append(r)
    for t in range(horizons + 1):
        for sid in ids:
            p = scenario.series[sid]
            prev = dev[sid][t - 1] if t else 0.0
            own = {"noise": 0.0, "ar1": p.phi * prev, "random_walk": prev}.get(p.process)
            if own is None:  # bounded: phi của z
                own = (p.before.phi if p.before else 0.0) * prev
            push = sum(r.beta * dev[r.shock][t - r.lag] for r in incoming[sid] if t - r.lag >= 0)
            dev[sid][t] = own + push + (1.0 if sid == shock and t == 0 else 0.0)
    return [float(dev[outcome][h]) for h in range(1, horizons + 1)]


def bounded_downstream(scenario: Scenario, relations: list[Relation]) -> set[str]:
    """Chuỗi `bounded` và chuỗi nhận tác động qua chúng: phản ứng không tuyến tính."""
    tainted = {sid for sid, p in scenario.series.items() if p.process == "bounded"}
    changed = True
    while changed:
        changed = False
        for r in relations:
            if r.shock in tainted and r.outcome not in tainted:
                tainted.add(r.outcome)
                changed = True
    return tainted
