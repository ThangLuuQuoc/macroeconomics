"""Acceptance journey: kiểm chứng lịch sử (.proofline/specs/backtest.md).

Dữ liệu tổng hợp (seed cố định), chỉ có cú sốc Brent x_t = 100·Δln(giá):
- PMI có quan hệ thật và bền: y_t = y_{t−1} + 0,2·x_{t−1} + u_t → mô hình phải tốt hơn "không đổi".
- IIP chỉ là nhiễu quanh 8 → mô hình không được tốt hơn "không đổi".
"""

from __future__ import annotations

import calendar
import math
import random

from playwright.sync_api import Page, expect

from .support import dautubenvung_payload, pink_sheet_xlsx

RNG = random.Random(20261028)
MONTHS = [(y, m) for y in range(2007, 2027) for m in range(1, 13) if (y, m) <= (2026, 9)]
SHOCK = [RNG.gauss(0, 6) for _ in MONTHS]

BRENT, price = {}, 60.0
for (y, m), x in zip(MONTHS, SHOCK, strict=True):
    price *= math.exp(x / 100)
    BRENT[f"{y}M{m:02d}"] = {"Crude oil, Brent": price}

PMI = [50.0]
for i in range(1, len(MONTHS)):
    PMI.append(PMI[-1] + 0.2 * SHOCK[i - 1] + RNG.gauss(0, 0.3))
IIP = [8 + RNG.gauss(0, 2) for _ in MONTHS]


def day(y: int, m: int) -> str:
    return f"{calendar.monthrange(y, m)[1]:02d}/{m:02d}/{y}"


SOURCES = {
    "dautubenvung": dautubenvung_payload(
        pmi=[{"time": day(*ym), "pmi": v} for ym, v in zip(MONTHS, PMI, strict=True)],
        iip=[{"time": day(*ym), "iip": v} for ym, v in zip(MONTHS, IIP, strict=True)],
    ),
    "wb_pinksheet": pink_sheet_xlsx(BRENT),
}


def test_backtest_shows_where_the_model_beats_no_change_and_where_it_does_not(
    page: Page, macro_app
):
    page.goto(macro_app(rounds=[SOURCES]))
    link = page.get_by_role("link", name="Kiểm chứng lịch sử")
    expect(link).to_be_visible()
    link.click()

    pmi = page.get_by_test_id("backtest-vn.pmi_mfg")
    expect(pmi.get_by_test_id("verdict")).to_have_text("Tốt hơn đoán 'không đổi'")
    summary = pmi.get_by_test_id("summary")
    expect(summary).to_be_visible()
    ratio = float(summary.get_attribute("data-ratio") or "nan")
    mae_model = float(summary.get_attribute("data-mae-model") or "nan")
    mae_naive = float(summary.get_attribute("data-mae-naive") or "nan")
    assert ratio <= 0.8, ratio
    assert abs(ratio - mae_model / mae_naive) < 1e-6
    episodes = int(summary.get_attribute("data-episodes") or "0")
    assert episodes >= 10
    rows = pmi.locator("[data-testid^='episode-']")
    expect(rows).to_have_count(episodes)
    first = rows.first
    assert first.get_attribute("data-actual") is not None
    assert first.get_attribute("data-predicted") is not None
    # Mốc đầu tiên chỉ khi đã có đủ 60 quan sát ở mọi tầm: không trước 12/2012.
    assert (first.get_attribute("data-testid") or "") >= "episode-2012-12"

    iip = page.get_by_test_id("backtest-vn.iip")
    expect(iip.get_by_test_id("verdict")).to_have_text("Không tốt hơn đoán 'không đổi'")

    cpi = page.get_by_test_id("backtest-vn.cpi_yoy_long")
    expect(cpi.get_by_test_id("insufficient")).to_contain_text("Chưa đủ dữ liệu để kiểm chứng")
    expect(cpi.get_by_test_id("summary")).to_have_count(0)

    missing = page.get_by_test_id("missing-shocks")
    expect(missing).to_contain_text("Lợi suất trái phiếu Mỹ 10 năm")
    expect(missing).to_contain_text("Chỉ số USD rộng (Fed)")
