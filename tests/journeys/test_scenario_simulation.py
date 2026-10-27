"""Acceptance journey: giả lập kịch bản (.proofline/specs/scenario-simulation.md).

Dữ liệu tổng hợp có quan hệ biết trước (seed cố định): tăng trưởng xuất khẩu so cùng kỳ
g_t = 5 + 0,4·x_{t−1} + u_t, với x_t = 100·Δln(giá Brent). Cú sốc Brent +20% vì vậy phải cho
phản ứng xuất khẩu khoảng +8 điểm % ở tháng 1.
"""

from __future__ import annotations

import calendar
import json
import math
import random
import re

from playwright.sync_api import Page, expect

from .support import dautubenvung_payload, pink_sheet_xlsx

RNG = random.Random(20261027)
MONTHS = [(y, m) for y in range(2007, 2027) for m in range(1, 13) if (y, m) <= (2026, 9)]


def day(y: int, m: int) -> str:
    return f"{calendar.monthrange(y, m)[1]:02d}/{m:02d}/{y}"


# Giá Brent: log-giá đi ngẫu nhiên, x_t ~ N(0, 6) phần trăm.
SHOCK = {ym: RNG.gauss(0, 6) for ym in MONTHS}
BRENT, level = {}, 60.0
for ym in MONTHS:
    level *= math.exp(SHOCK[ym] / 100)
    BRENT[f"{ym[0]}M{ym[1]:02d}"] = {"Crude oil, Brent": level}

# Xuất khẩu: 2007 cố định, sau đó X_t = X_{t−12}·(1 + g_t/100).
EXPORTS: dict[tuple[int, int], float] = {}
for i, ym in enumerate(MONTHS):
    if ym[0] == 2007:
        EXPORTS[ym] = 10000.0
        continue
    growth = 5 + 0.4 * SHOCK[MONTHS[i - 1]] + RNG.gauss(0, 0.5)
    EXPORTS[ym] = EXPORTS[MONTHS[i - 12]] * (1 + growth / 100)

# CPI: IMF 12/2002–03/2025; dautubenvung từ 01/2021 (2021–2024 khác định nghĩa, 01–03/2025 khớp).
IMF_MONTHS = [(2002, 12)] + [(y, m) for y in range(2003, 2026) for m in range(1, 13)]
IMF_MONTHS = [ym for ym in IMF_MONTHS if ym <= (2025, 3)]
IMF_CPI = {ym: round(3 + RNG.gauss(0, 1), 2) for ym in IMF_MONTHS}


def dautubenvung_cpi(offset_on_overlap: float) -> list[dict]:
    rows = []
    for ym in MONTHS:
        if ym < (2021, 1):
            continue
        if ym <= (2024, 12):
            value = IMF_CPI[ym] + 0.7  # định nghĩa khác (bình quân từ đầu năm)
        elif ym in IMF_CPI:
            value = IMF_CPI[ym] + offset_on_overlap
        else:
            value = round(3.5 + RNG.gauss(0, 0.5), 2)
        rows.append({"time": day(*ym), "CPI": value})
    return rows


def imf_cpi_raw() -> dict[str, bytes]:
    periods = [f"{y}-{m:02d}" for y, m in IMF_MONTHS]
    body = {"series": {"docs": [{"period": periods, "value": [IMF_CPI[ym] for ym in IMF_MONTHS]}]}}
    return {"IMF_CPI_M.VN.PCPI_PC_CP_A_PT.json": json.dumps(body).encode("utf-8")}


# VN-Index chỉ 30 tháng: không đủ để ước lượng.
VNINDEX_SHORT = {
    "VNINDEX.csv": (
        "time,close,amount\n"
        + "".join(
            f"{y}-{m:02d}-{calendar.monthrange(y, m)[1]:02d},{1200 + 10 * i},1000000000000\n"
            for i, (y, m) in enumerate(MONTHS[-30:])
        )
    ).encode("utf-8")
}


def sources(cpi_offset: float = 0.0) -> dict[str, object]:
    return {
        "dautubenvung": dautubenvung_payload(
            xuatNhapKhau=[{"time": day(*ym), "XK_tong": EXPORTS[ym]} for ym in MONTHS],
            cpi=dautubenvung_cpi(cpi_offset),
        ),
        "wb_pinksheet": pink_sheet_xlsx(BRENT),
        "dbnomics": imf_cpi_raw(),
        "openstock": VNINDEX_SHORT,
    }


def simulate(page: Page, shock: str, size: str) -> None:
    # Khẳng định trước khi thao tác: thiếu trang giả lập thì fail ở khẳng định, không phải timeout.
    expect(page.get_by_test_id("shock")).to_be_visible()
    page.get_by_test_id("shock").select_option(shock)
    page.get_by_test_id("shock-size").fill(size)
    page.get_by_test_id("run").click()


def month_one(page: Page, series_id: str):
    return page.get_by_test_id(f"response-{series_id}").get_by_test_id("h-1")


def test_scenario_recovers_a_known_effect_and_says_what_it_cannot_estimate(page: Page, macro_app):
    page.goto(macro_app(rounds=[sources()]))
    link = page.get_by_role("link", name="Giả lập kịch bản")
    expect(link).to_be_visible()
    link.click()
    expect(page.get_by_test_id("disclaimer")).to_contain_text("không phải dự báo")

    simulate(page, "global.brent", "20")
    row = month_one(page, "vn.exports")
    expect(row).to_be_visible()
    estimate = float(row.get_attribute("data-estimate") or "nan")
    lower = float(row.get_attribute("data-lower") or "nan")
    upper = float(row.get_attribute("data-upper") or "nan")
    assert abs(estimate - 8) <= 0.5, estimate
    assert lower < estimate < upper
    assert int(row.get_attribute("data-n") or "0") >= 60
    expect(row.get_by_test_id("zero")).to_have_count(0)
    expect(page.get_by_test_id("response-vn.exports").get_by_test_id("sample")).to_contain_text(
        "Mẫu:"
    )

    # CPI: nối IMF (tới 03/2025) với dautubenvung (từ 04/2025), có ghi nguồn từng đoạn.
    cpi = page.get_by_test_id("response-vn.cpi_yoy_long")
    expect(cpi.get_by_test_id("sample")).to_contain_text(
        "IMF qua DBnomics (12/2002–03/2025) + dautubenvung.vn (04/2025–09/2026)"
    )
    expect(cpi.get_by_test_id("h-1")).to_be_visible()

    # VN-Index chỉ có 30 tháng: nói thẳng là chưa đủ, không có số.
    vnindex = page.get_by_test_id("response-vn.vnindex")
    expect(vnindex.get_by_test_id("insufficient")).to_contain_text("Chưa đủ dữ liệu")
    expect(vnindex.get_by_test_id("insufficient")).to_contain_text("cần ≥ 60")
    expect(vnindex.get_by_test_id("h-1")).to_have_count(0)


def test_response_scales_with_shock_size(page: Page, macro_app):
    page.goto(macro_app(rounds=[sources()]) + "kich-ban/")

    simulate(page, "global.brent", "20")
    expect(month_one(page, "vn.exports")).to_have_attribute("data-n", re.compile(r"\d+"))
    raw = month_one(page, "vn.exports").get_attribute("data-estimate") or "nan"
    full = float(raw)

    simulate(page, "global.brent", "10")
    expect(month_one(page, "vn.exports")).not_to_have_attribute("data-estimate", raw)
    half = float(month_one(page, "vn.exports").get_attribute("data-estimate") or "nan")
    assert abs(half - full / 2) < 1e-6, (half, full)


def test_cpi_is_not_spliced_when_sources_disagree(page: Page, macro_app):
    page.goto(macro_app(rounds=[sources(cpi_offset=0.5)]) + "kich-ban/")

    simulate(page, "global.brent", "20")
    cpi = page.get_by_test_id("response-vn.cpi_yoy_long")
    expect(cpi.get_by_test_id("insufficient")).to_contain_text("Chưa nối được lịch sử CPI")
    expect(cpi.get_by_test_id("h-1")).to_have_count(0)
