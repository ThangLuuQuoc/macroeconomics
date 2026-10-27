"""Kiểm chứng lịch sử: mốc cắt, không nhìn trước, kết luận theo ngưỡng."""

from __future__ import annotations

import random

import pandas as pd

from macro.backtest import BETTER, NOT_BETTER, backtest_outcome


def series(values: list[float], start: str = "2005-01") -> pd.Series:
    return pd.Series(values, index=pd.period_range(start, periods=len(values), freq="M"))


def data(n: int = 240, beta: float = 0.2, seed: int = 3) -> tuple[pd.Series, pd.Series]:
    rng = random.Random(seed)
    x = [rng.gauss(0, 6) for _ in range(n)]
    y = [50.0]
    for t in range(1, n):
        y.append(y[-1] + beta * x[t - 1] + rng.gauss(0, 0.3))
    return series(y), series(x)


def test_model_with_a_real_relation_beats_no_change():
    y, x = data()
    result = backtest_outcome(y, {"s": x}, "PMI", "vn.pmi_mfg", "điểm")
    assert result.verdict == BETTER
    assert result.ratio is not None and result.ratio <= 0.8
    first = result.episodes[0].cut
    assert first.endswith("-12") and first >= "2010-12"  # ≥ 60 quan sát ở mọi tầm trước mốc
    assert all(e.label.count("/") == 2 for e in result.episodes)


def test_noise_does_not_beat_no_change():
    rng = random.Random(9)
    y = series([8 + rng.gauss(0, 2) for _ in range(240)])
    _, x = data()
    assert backtest_outcome(y, {"s": x}, "IIP", "vn.iip", "điểm %").verdict == NOT_BETTER


def test_no_look_ahead():
    y, x = data()
    before = backtest_outcome(y, {"s": x}, "PMI", "vn.pmi_mfg", "điểm").episodes[0]
    # Đổi dữ liệu sau năm của mốc đầu tiên (trừ 12 tháng cú sốc và số thực tế của chính mốc đó).
    end = pd.Period(before.cut, freq="M") + 12
    y2, x2 = y.copy(), x.copy()
    y2[y2.index > end] += 100
    x2[x2.index > end] *= -3
    after = backtest_outcome(y2, {"s": x2}, "PMI", "vn.pmi_mfg", "điểm").episodes[0]
    assert (after.cut, after.predicted, after.actual) == (
        before.cut,
        before.predicted,
        before.actual,
    )


def test_short_history_is_insufficient():
    y, x = data(n=70)
    result = backtest_outcome(y, {"s": x}, "PMI", "vn.pmi_mfg", "điểm")
    assert result.verdict is None and result.episodes == []
    assert result.insufficient_text is not None
