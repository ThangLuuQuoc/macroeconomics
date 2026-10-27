"""Kiểm chứng lịch sử (spec backtest): mô hình giả lập v1 đoán đúng tới đâu.

Tại mỗi mốc cắt c (tháng 12), mô hình chỉ học dữ liệu ≤ c, nhận các cú sốc thật của
c+1 … c+11 và dự đoán Δŷ = ŷ_{c+12} − y_c; so với thực tế và với đoán "không đổi" (Δŷ = 0).
Dùng chung chuỗi và hàm ước lượng với trang giả lập (T-1).
"""

from __future__ import annotations

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
    load_monthly,
    local_projection,
    outcome_series,
)

H = 12
VERDICT_THRESHOLD = 0.8
BETTER = "Tốt hơn đoán 'không đổi'"
NOT_BETTER = "Không tốt hơn đoán 'không đổi'"


class Episode(BaseModel):
    cut: str  # "YYYY-MM"
    label: str  # "12/2014 → 12/2015"
    actual: float
    predicted: float
    error: float
    text: str


class OutcomeBacktest(BaseModel):
    series_id: str
    name: str
    unit: str
    insufficient_text: str | None = None
    verdict: str | None = None
    mae_model: float | None = None
    mae_naive: float | None = None
    ratio: float | None = None
    hit_rate: float | None = None
    summary_text: str | None = None
    episodes: list[Episode] = []


class BacktestResult(BaseModel):
    missing_shocks: list[str]
    note: str
    outcomes: list[OutcomeBacktest]


NOTE = (
    "Mô hình v1 ước lượng từng cú sốc riêng rồi cộng các đóng góp; khi các cú sốc liên quan"
    " nhau, cách cộng này có thể đếm trùng. Mỗi mốc chỉ dùng dữ liệu tới mốc đó."
)


def _label(month: pd.Period) -> str:
    return f"{month.month:02d}/{month.year}"


def _betas(y: pd.Series, x: pd.Series, cut: pd.Period) -> dict[int, float] | None:
    betas = {}
    for h in HORIZONS:
        beta, _, n, _ = local_projection(y[:cut], x[:cut], h)
        if np.isnan(beta) or n < MIN_OBSERVATIONS:
            return None
        betas[h] = beta
    return betas


def backtest_outcome(
    y: pd.Series, shocks: dict[str, pd.Series], name: str, series_id: str, unit: str
) -> OutcomeBacktest:
    result = OutcomeBacktest(series_id=series_id, name=name, unit=unit)
    y = y.dropna()
    if y.empty or not shocks:
        result.insufficient_text = "Chưa đủ dữ liệu để kiểm chứng."
        return result
    episodes = []
    for cut in (p for p in y.index if p.month == 12):
        end = cut + H
        if end not in y.index or cut not in y.index:
            continue
        predicted, used = 0.0, False
        for x in shocks.values():
            betas = _betas(y, x, cut)
            if betas is None:
                continue
            used = True
            for t in pd.period_range(cut + 1, end - 1, freq="M"):
                value = x.get(t)
                if value is not None and not np.isnan(value):
                    predicted += betas[(end - t).n] * float(value)
        if not used:
            continue
        actual = float(y[end] - y[cut])
        episodes.append(
            Episode(
                cut=str(cut),
                label=f"{_label(cut)} → {_label(end)}",
                actual=actual,
                predicted=predicted,
                error=predicted - actual,
                text=(
                    f"thực tế {vn_signed(actual, 2)} · dự đoán {vn_signed(predicted, 2)}"
                    f" · sai số {vn_number(abs(predicted - actual), 2)} {unit}"
                ),
            )
        )
    if not episodes:
        result.insufficient_text = (
            f"Chưa đủ dữ liệu để kiểm chứng (cần ≥ {MIN_OBSERVATIONS} quan sát trước mốc cắt"
            f" và số thực tế 12 tháng sau)."
        )
        return result
    mae_model = float(np.mean([abs(e.error) for e in episodes]))
    mae_naive = float(np.mean([abs(e.actual) for e in episodes]))
    ratio = mae_model / mae_naive if mae_naive > 0 else float("inf")
    hit_rate = float(np.mean([np.sign(e.predicted) == np.sign(e.actual) for e in episodes]))
    result.episodes = episodes
    result.mae_model, result.mae_naive, result.ratio, result.hit_rate = (
        mae_model,
        mae_naive,
        ratio,
        hit_rate,
    )
    result.verdict = BETTER if ratio <= VERDICT_THRESHOLD else NOT_BETTER
    result.summary_text = (
        f"Sai số trung bình: mô hình {vn_number(mae_model, 2)}, 'không đổi'"
        f" {vn_number(mae_naive, 2)} {unit} (tỷ lệ {vn_number(ratio, 2)}) · đúng hướng"
        f" {vn_number(hit_rate * 100, 0)}% · {len(episodes)} mốc"
    )
    return result


def run_backtest(conn: psycopg.Connection[dict]) -> BacktestResult:
    shocks, missing = {}, []
    for shock_id, shock in SHOCKS.items():
        x = shock.transform(load_monthly(conn, shock_id))
        if x.dropna().empty:
            missing.append(shock.name)
        else:
            shocks[shock_id] = x
    outcomes = []
    for outcome in OUTCOMES:
        y, reason, _ = outcome_series(conn, outcome.series_id)
        if reason:
            outcomes.append(
                OutcomeBacktest(
                    series_id=outcome.series_id,
                    name=outcome.name,
                    unit=outcome.unit,
                    insufficient_text=f"Chưa đủ dữ liệu để kiểm chứng: {reason}",
                )
            )
            continue
        outcomes.append(backtest_outcome(y, shocks, outcome.name, outcome.series_id, outcome.unit))
    return BacktestResult(missing_shocks=missing, note=NOTE, outcomes=outcomes)
