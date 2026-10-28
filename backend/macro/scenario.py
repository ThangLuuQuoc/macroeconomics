"""Giả lập kịch bản bằng local projections (spec scenario-simulation).

Với mỗi biến kết quả y và tầm h = 1..12:

    y_{t+h} − y_{t−1} = α_h + β_h·x_t + Σ_{l=1..2} (γ_{h,l}·Δy_{t−l} + δ_{h,l}·x_{t−l}) + ε

Sai số chuẩn HAC (Newey–West, maxlags = h + 1); khoảng tin cậy 90% = β ± 1,645·se. Phản ứng với
cú sốc độ lớn s là s·β_h. Mỗi biến ước lượng trên lịch sử dài nhất của chính nó; thiếu dữ liệu
thì nói thẳng, không đưa ra số (T-4).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Literal

import numpy as np
import pandas as pd
import psycopg
import statsmodels.api as sm
from pydantic import BaseModel

from macro.connectors import SOURCE_LABELS
from macro.numbers import vn_number, vn_signed

HORIZONS = range(1, 13)
LAGS = 2
MIN_OBSERVATIONS = 60
Z90 = 1.645
SPLICE_CHECK_MONTHS = 3
SPLICE_TOLERANCE = 0.1


@dataclass(frozen=True)
class Shock:
    series_id: str
    name: str
    unit: str  # đơn vị độ lớn cú sốc
    default_size: float
    transform: Callable[[pd.Series], pd.Series]  # chuỗi tháng → x_t
    scope: Literal["global", "domestic"] = "global"
    # Yếu tố gốc luôn được liệt kê (thiếu dữ liệu thì nói thẳng); yếu tố mở rộng (spec
    # synthetic-data mục 2.2) chỉ dùng khi database đang xem có dữ liệu của nó.
    core: bool = True


@dataclass(frozen=True)
class Outcome:
    series_id: str
    name: str
    unit: str  # đơn vị phản ứng


def _log_change(monthly: pd.Series) -> pd.Series:
    return 100 * np.log(monthly).diff()


def _diff(monthly: pd.Series) -> pd.Series:
    return monthly.diff()


SHOCKS = {
    s.series_id: s
    for s in [
        Shock("global.brent", "Giá dầu Brent", "%", 20, _log_change),
        Shock("us.ust10y", "Lợi suất trái phiếu Mỹ 10 năm", "điểm %", 0.5, _diff),
        Shock("us.usd_broad", "Chỉ số USD rộng (Fed)", "%", 5, _log_change),
        Shock(
            "global.demand", "Cầu thế giới (SX công nghiệp đối tác)", "điểm %", 2, _diff, core=False
        ),
        Shock(
            "vn.policy_rate",
            "Lãi suất điều hành NHNN",
            "điểm %",
            0.5,
            _diff,
            scope="domestic",
            core=False,
        ),
        Shock("vn.usdvnd", "Tỷ giá USD/VND", "%", 3, _log_change, scope="domestic", core=False),
        Shock(
            "vn.fdi_yoy",
            "FDI giải ngân (so cùng kỳ)",
            "điểm %",
            10,
            _diff,
            scope="domestic",
            core=False,
        ),
        Shock(
            "vn.credit_growth",
            "Tăng trưởng tín dụng (so cùng kỳ)",
            "điểm %",
            2,
            _diff,
            scope="domestic",
            core=False,
        ),
        Shock(
            "vn.public_investment",
            "Giải ngân đầu tư công (so cùng kỳ)",
            "điểm %",
            10,
            _diff,
            scope="domestic",
            core=False,
        ),
    ]
}

OUTCOMES = [
    Outcome("vn.gdp_yoy", "GDP (so cùng kỳ)", "điểm %"),
    Outcome("vn.exports", "Xuất khẩu (tăng trưởng so cùng kỳ)", "điểm %"),
    Outcome("vn.iip", "Sản xuất công nghiệp (IIP, so cùng kỳ)", "điểm %"),
    Outcome("vn.pmi_mfg", "PMI sản xuất", "điểm"),
    Outcome("vn.cpi_yoy_long", "CPI (so cùng kỳ)", "điểm %"),
    Outcome("vn.vnindex", "VN-Index", "%"),
]


class Horizon(BaseModel):
    h: int
    estimate: float
    lower: float
    upper: float
    n: int
    includes_zero: bool
    text: str


class OutcomeResult(BaseModel):
    series_id: str
    name: str
    unit: str
    sample_text: str | None = None
    insufficient_text: str | None = None
    horizons: list[Horizon] = []


class ScenarioResult(BaseModel):
    shock: str
    shock_name: str
    size: float
    unit: str
    outcomes: list[OutcomeResult]


# ---- Dữ liệu tháng ----


def _month(period: date) -> pd.Period:
    return pd.Period(year=period.year, month=period.month, freq="M")


def load_monthly(conn: psycopg.Connection[dict], series_id: str) -> pd.Series:
    """Chuỗi theo tháng: chuỗi ngày lấy trung bình tháng (VN-Index lấy giá cuối tháng)."""
    rows = conn.execute(
        "SELECT o.period, o.value, s.frequency FROM latest_observations o"
        " JOIN series s ON s.id = o.series_id WHERE o.series_id = %s ORDER BY o.period",
        (series_id,),
    ).fetchall()
    if not rows:
        return pd.Series(dtype=float)
    frame = pd.DataFrame(rows)
    frame["month"] = pd.PeriodIndex([_month(p) for p in frame["period"]], freq="M")
    if rows[0]["frequency"] in ("D", "W"):
        how = "last" if series_id == "vn.vnindex" else "mean"
        series = frame.groupby("month")["value"].agg(how)
    else:
        series = frame.groupby("month")["value"].last()
    return _consecutive(series.astype(float))


def _consecutive(series: pd.Series) -> pd.Series:
    if series.empty:
        return series
    full = pd.period_range(series.index.min(), series.index.max(), freq="M")
    return series.reindex(full)


def _label(month: pd.Period) -> str:
    return f"{month.month:02d}/{month.year}"


def outcome_series(
    conn: psycopg.Connection[dict], series_id: str
) -> tuple[pd.Series, str | None, str]:
    """(y_t, lý do không dùng được, ghi chú nguồn)."""
    if series_id == "vn.cpi_yoy_long":
        return splice_cpi(load_monthly(conn, "vn.cpi_yoy_imf"), load_monthly(conn, "vn.cpi_yoy"))
    raw = load_monthly(conn, series_id)
    if series_id == "vn.exports":
        y = (raw / raw.shift(12) - 1) * 100
    elif series_id == "vn.vnindex":
        y = 100 * np.log(raw)
    else:
        y = raw
    source = SOURCE_LABELS.get(_connector(conn, series_id) or "", "")
    return y, None, f"Nguồn: {source}" if source else ""


def has_data(conn: psycopg.Connection[dict], series_id: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM latest_observations WHERE series_id = %s LIMIT 1", (series_id,)
    ).fetchone()
    return row is not None


def listed_shocks(conn: psycopg.Connection[dict]) -> tuple[list[Shock], list[Shock]]:
    """(yếu tố dùng được trên database này, yếu tố mở rộng chưa có dữ liệu)."""
    listed, without = [], []
    for shock in SHOCKS.values():
        if shock.core or has_data(conn, shock.series_id):
            listed.append(shock)
        else:
            without.append(shock)
    return listed, without


def _connector(conn: psycopg.Connection[dict], series_id: str) -> str | None:
    row = conn.execute("SELECT connector FROM series WHERE id = %s", (series_id,)).fetchone()
    return row["connector"] if row else None


def splice_cpi(imf: pd.Series, local: pd.Series) -> tuple[pd.Series, str | None, str]:
    """IMF cho các tháng ≤ tháng cuối của IMF, dautubenvung cho các tháng sau đó (spec mục 3)."""
    imf, local = imf.dropna(), local.dropna()
    if imf.empty:
        return pd.Series(dtype=float), "Chưa có lịch sử CPI từ IMF để nối.", ""
    if local.empty:
        return pd.Series(dtype=float), "Chưa có CPI của dautubenvung.", ""
    last_imf = imf.index.max()
    overlap = sorted(set(imf.index) & set(local[local.index <= last_imf].index))
    check = overlap[-SPLICE_CHECK_MONTHS:]
    if not check:
        return pd.Series(dtype=float), "Chưa nối được lịch sử CPI: không có đoạn trùng.", ""
    gap = max(abs(imf[m] - local[m]) for m in check)
    if gap > SPLICE_TOLERANCE:
        reason = (
            f"Chưa nối được lịch sử CPI: lệch tối đa {vn_number(gap, 2)} điểm % ở đoạn trùng"
            f" ({_label(check[0])}–{_label(check[-1])})."
        )
        return pd.Series(dtype=float), reason, ""
    after = local[local.index > last_imf]
    combined = _consecutive(pd.concat([imf, after]).sort_index())
    note = f"Nguồn: IMF qua DBnomics ({_label(imf.index.min())}–{_label(last_imf)})"
    if not after.empty:
        note += f" + dautubenvung.vn ({_label(after.index.min())}–{_label(after.index.max())})"
    return combined, None, note


# ---- Local projections ----


def _lp_frame(y: pd.Series, x: pd.Series, h: int) -> pd.DataFrame:
    index = y.index.union(x.index)
    y, x = y.reindex(index), x.reindex(index)
    dy = y.diff()
    frame = pd.DataFrame({"lhs": y.shift(-h) - y.shift(1), "x": x})
    for lag in range(1, LAGS + 1):
        frame[f"dy{lag}"] = dy.shift(lag)
        frame[f"x{lag}"] = x.shift(lag)
    return frame.dropna()


def lp_frame(y: pd.Series, x: pd.Series, h: int) -> pd.DataFrame:
    """Bảng hồi quy của tầm h; hàng t chỉ dùng dữ liệu tới tháng t + h."""
    return _lp_frame(y, x, h)


def lp_beta(frame: pd.DataFrame) -> tuple[float, int]:
    """(β_h, số quan sát) trên bảng của `lp_frame`, như `local_projection` nhưng không tính sai
    số chuẩn: nhanh hơn nhiều, dùng cho kiểm chứng lịch sử (ước lượng lại ở mỗi mốc cắt)."""
    if len(frame) < MIN_OBSERVATIONS:
        return float("nan"), len(frame)
    regressors = frame.drop(columns="lhs").to_numpy()
    design = np.column_stack([np.ones(len(frame)), regressors])
    coef, *_ = np.linalg.lstsq(design, frame["lhs"].to_numpy(), rcond=None)
    return float(coef[1]), len(frame)


def local_projection(y: pd.Series, x: pd.Series, h: int) -> tuple[float, float, int, str]:
    """(β_h, se, số quan sát, mẫu "MM/YYYY–MM/YYYY")."""
    frame = _lp_frame(y, x, h)
    if len(frame) < MIN_OBSERVATIONS:
        return float("nan"), float("nan"), len(frame), ""
    regressors = sm.add_constant(frame.drop(columns="lhs"))
    fit = sm.OLS(frame["lhs"], regressors).fit(cov_type="HAC", cov_kwds={"maxlags": h + 1})
    sample = f"{_label(frame.index.min())}–{_label(frame.index.max())}"
    return float(fit.params["x"]), float(fit.bse["x"]), len(frame), sample


def simulate(conn: psycopg.Connection[dict], shock_id: str, size: float) -> ScenarioResult:
    shock = SHOCKS[shock_id]
    x = shock.transform(load_monthly(conn, shock_id))
    results = []
    for outcome in OUTCOMES:
        result = OutcomeResult(series_id=outcome.series_id, name=outcome.name, unit=outcome.unit)
        results.append(result)
        if x.dropna().empty:
            result.insufficient_text = f"Chưa có dữ liệu {shock.name} để làm cú sốc."
            continue
        y, reason, source = outcome_series(conn, outcome.series_id)
        if reason:
            result.insufficient_text = reason
            continue
        if y.dropna().empty:
            result.insufficient_text = "Chưa có dữ liệu."
            continue
        beta, _, n, sample = local_projection(y, x, 1)
        if np.isnan(beta):
            result.insufficient_text = f"Chưa đủ dữ liệu (có {n} tháng, cần ≥ {MIN_OBSERVATIONS})."
            continue
        result.sample_text = " · ".join(filter(None, [f"Mẫu: {sample} · {n} quan sát", source]))
        for h in HORIZONS:
            beta, se, n, _ = local_projection(y, x, h)
            if np.isnan(beta):
                continue
            a, b = size * (beta - Z90 * se), size * (beta + Z90 * se)
            lower, upper = min(a, b), max(a, b)
            estimate = size * beta
            result.horizons.append(
                Horizon(
                    h=h,
                    estimate=estimate,
                    lower=lower,
                    upper=upper,
                    n=n,
                    includes_zero=lower <= 0 <= upper,
                    text=(
                        f"{vn_signed(estimate, 2)} {outcome.unit}"
                        f" [{vn_number(lower, 2)}; {vn_number(upper, 2)}]"
                    ),
                )
            )
    return ScenarioResult(
        shock=shock_id, shock_name=shock.name, size=size, unit=shock.unit, outcomes=results
    )
