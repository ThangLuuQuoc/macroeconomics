"""Giả lập kịch bản: nối CPI, local projections, tháng hoá chuỗi, connector dbnomics."""

from __future__ import annotations

import json
import random
from datetime import date

import pandas as pd
import pytest

from macro.connectors.base import SourceError
from macro.connectors.dbnomics import DbnomicsConnector
from macro.connectors.wb_pinksheet import PinkSheetConnector
from macro.db import connect
from macro.scenario import MIN_OBSERVATIONS, load_monthly, local_projection, splice_cpi

from .journeys.support import pink_sheet_xlsx
from .test_overview import load


def monthly(start: str, values: list[float]) -> pd.Series:
    return pd.Series(values, index=pd.period_range(start, periods=len(values), freq="M"))


# ---- Nối CPI ----


def test_splice_uses_imf_then_local_and_names_both_sources():
    imf = monthly("2024-10", [3.0, 3.1, 3.2, 3.3, 3.4, 3.5])  # 10/2024–03/2025
    local = monthly("2025-01", [3.3, 3.4, 3.5, 3.6, 3.7])  # 01/2025–05/2025
    series, reason, note = splice_cpi(imf, local)
    assert reason is None
    assert list(series.values) == [3.0, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7]
    assert note == "Nguồn: IMF qua DBnomics (10/2024–03/2025) + dautubenvung.vn (04/2025–05/2025)"


def test_splice_refuses_when_the_overlap_disagrees():
    imf = monthly("2025-01", [3.0, 3.1, 3.2])
    local = monthly("2025-01", [3.0, 3.1, 3.5])
    series, reason, _ = splice_cpi(imf, local)
    assert series.empty
    assert reason is not None and "lệch tối đa 0,30 điểm %" in reason


def test_splice_needs_an_overlap():
    _, reason, _ = splice_cpi(monthly("2020-01", [1.0]), monthly("2025-01", [2.0]))
    assert reason is not None and "không có đoạn trùng" in reason


# ---- Local projections ----


def synthetic(n: int, beta: float) -> tuple[pd.Series, pd.Series]:
    rng = random.Random(7)
    x = [rng.gauss(0, 5) for _ in range(n)]
    y = [0.0] + [beta * x[t - 1] + rng.gauss(0, 0.3) for t in range(1, n)]
    return monthly("2005-01", y), monthly("2005-01", x)


def test_local_projection_recovers_a_known_effect():
    y, x = synthetic(240, 0.5)
    beta, se, n, sample = local_projection(y, x, 1)
    assert beta == pytest.approx(0.5, abs=0.05)
    assert 0 < se < 0.05
    assert n >= MIN_OBSERVATIONS and sample.startswith("04/2005–")
    no_effect, se6, _, _ = local_projection(y, x, 6)
    assert abs(no_effect) < 3 * se6 + 0.05  # Không có quan hệ ở tháng 6


def test_local_projection_refuses_short_samples():
    y, x = synthetic(40, 0.5)
    beta, _, n, _ = local_projection(y, x, 1)
    assert pd.isna(beta) and n < MIN_OBSERVATIONS


# ---- Dữ liệu tháng và connector ----


def test_daily_series_become_monthly(database_url, tmp_path):
    vnindex = b"time,close,amount\n2026-09-01,1700,1\n2026-09-30,1750,1\n2026-10-26,1763.55,1\n"
    load(database_url, tmp_path, [{"openstock": {"VNINDEX.csv": vnindex}}])
    with connect(database_url) as conn:
        series = load_monthly(conn, "vn.vnindex")
    assert series.to_dict() == {
        pd.Period("2026-09", freq="M"): 1750.0,  # VN-Index: giá cuối tháng
        pd.Period("2026-10", freq="M"): 1763.55,
    }


def test_dbnomics_parse_skips_missing_values(tmp_path):
    body = {"series": {"docs": [{"period": ["2025-02", "2025-03"], "value": ["NA", 3.13]}]}}
    (tmp_path / "IMF_CPI_M.VN.PCPI_PC_CP_A_PT.json").write_text(json.dumps(body))
    observations = DbnomicsConnector().parse(tmp_path)
    assert [(o.series_id, o.period, o.value) for o in observations] == [
        ("vn.cpi_yoy_imf", date(2025, 3, 31), 3.13)
    ]
    (tmp_path / "IMF_CPI_M.VN.PCPI_PC_CP_A_PT.json").write_text("{}")
    with pytest.raises(SourceError):
        DbnomicsConnector().parse(tmp_path)


def test_pink_sheet_reads_the_columns_that_are_present(tmp_path):
    for name, content in pink_sheet_xlsx({"2026M09": {"Crude oil, Brent": 116.8}}).items():
        (tmp_path / name).write_bytes(content)
    got = [(o.series_id, o.value) for o in PinkSheetConnector().parse(tmp_path)]
    assert got == [("global.brent", 116.8)]
    for name, content in pink_sheet_xlsx({"2026M09": {"Coal": 1.0}}).items():
        (tmp_path / name).write_bytes(content)
    with pytest.raises(SourceError, match="không có cột nào"):
        PinkSheetConnector().parse(tmp_path)
