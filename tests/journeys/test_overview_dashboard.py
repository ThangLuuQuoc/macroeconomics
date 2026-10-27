"""Acceptance journey: Bảng tổng quan vĩ mô (.proofline/specs/overview-dashboard.md).

Người dùng mở trang chủ và đọc các thẻ chỉ số. Dữ liệu vào là bản ghi nguồn tổng hợp viết ngay
trong file này, nạp qua đúng đường ingest của app (không gọi mạng). Hạ tầng (`macro_app`,
các hàm dựng bản ghi nguồn) thuộc walking skeleton: tests/journeys/conftest.py, support.py.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect

from .support import dautubenvung_payload, fred_csv, pink_sheet_xlsx, source_failure

VIETNAM = dautubenvung_payload(
    cpi=[
        {"time": "31/08/2026", "CPI": 4.95},
        {"time": "30/09/2026", "CPI": 5.08},
    ],
    pmi=[
        {"time": "31/08/2026", "pmi": 50.4},
        {"time": "30/09/2026", "pmi": 51.9},
    ],
    xuatNhapKhau=[
        {"time": "30/09/2025", "XK_tong": 46000.0},
        {"time": "31/08/2026", "XK_tong": 58000.0, "NK_tong": 55000.0},
        {"time": "30/09/2026", "XK_tong": 59477.4, "NK_tong": 58206.6},
    ],
)
UST10Y = fred_csv("DGS10", [("2026-10-22", 4.98), ("2026-10-23", 5.00)])
USD_BROAD = fred_csv("DTWEXBGS", [("2026-10-22", 121.10), ("2026-10-23", 121.32)])
COMMODITIES = pink_sheet_xlsx(
    {
        "2026M08": {"Crude oil, Brent": 80.14, "Gold": 2510.0},
        "2026M09": {"Crude oil, Brent": 82.30, "Gold": 2575.5},
    }
)
ALL_SOURCES = {
    "dautubenvung": VIETNAM,
    "fred": {"DGS10": UST10Y, "DTWEXBGS": USD_BROAD},
    "wb_pinksheet": COMMODITIES,
}


def card(page: Page, series_id: str):
    return page.get_by_test_id(f"indicator-{series_id}")


def test_cards_show_latest_value_period_and_source(page: Page, macro_app):
    page.goto(macro_app(rounds=[ALL_SOURCES]))

    cpi = card(page, "vn.cpi_yoy")
    expect(cpi.get_by_test_id("value")).to_have_text("5,08%")
    expect(cpi.get_by_test_id("period")).to_have_text("09/2026")
    expect(cpi.get_by_test_id("change-prev")).to_contain_text("+0,13 điểm %")
    expect(cpi.get_by_test_id("source")).to_contain_text("dautubenvung.vn")

    pmi = card(page, "vn.pmi_mfg")
    expect(pmi.get_by_test_id("value")).to_have_text("51,9")
    expect(pmi.get_by_test_id("change-prev")).to_contain_text("+1,5 điểm")

    ust = card(page, "us.ust10y")
    expect(ust.get_by_test_id("value")).to_have_text("5,00%")
    expect(ust.get_by_test_id("period")).to_have_text("23/10/2026")
    expect(ust.get_by_test_id("source")).to_contain_text("FRED · DGS10")

    brent = card(page, "global.brent")
    expect(brent.get_by_test_id("value")).to_have_text("82,30 USD/thùng")
    expect(brent.get_by_test_id("period")).to_have_text("09/2026")
    expect(brent.get_by_test_id("change-prev")).to_contain_text("+2,7%")

    # Đúng tên thứ được đo: chỉ số USD rộng của Fed không phải DXY.
    expect(card(page, "us.usd_broad")).to_contain_text("Chỉ số USD rộng (Fed)")
    expect(page.get_by_text("DXY")).to_have_count(0)

    # Không có thẻ nào mang nhãn nguồn lỗi khi mọi nguồn đều lấy được.
    expect(page.get_by_text("Nguồn lỗi")).to_have_count(0)


def test_changes_vs_previous_and_same_period_without_guessing(page: Page, macro_app):
    page.goto(macro_app(rounds=[ALL_SOURCES]))

    exports = card(page, "vn.exports")
    expect(exports.get_by_test_id("period")).to_have_text("09/2026")
    expect(exports.get_by_test_id("change-prev")).to_contain_text("+2,5%")
    expect(exports.get_by_test_id("change-yoy")).to_contain_text("+29,3%")

    # Nhập khẩu không có số 09/2025: không hiện dòng so cùng kỳ (không đoán).
    imports = card(page, "vn.imports")
    expect(imports.get_by_test_id("change-prev")).to_contain_text("+5,8%")
    expect(imports.get_by_test_id("change-yoy")).to_have_count(0)


def test_failed_source_keeps_last_value_and_says_so(page: Page, macro_app):
    page.goto(
        macro_app(
            rounds=[
                ALL_SOURCES,
                {**ALL_SOURCES, "fred": source_failure("fred", "HTTP 500")},
            ]
        )
    )

    ust = card(page, "us.ust10y")
    expect(ust.get_by_test_id("value")).to_have_text("5,00%")
    expect(ust.get_by_test_id("period")).to_have_text("23/10/2026")
    expect(ust.get_by_test_id("status")).to_contain_text("Nguồn lỗi")

    # Chỉ nguồn lỗi mới bị gắn nhãn.
    expect(card(page, "vn.cpi_yoy").get_by_test_id("status")).not_to_contain_text("Nguồn lỗi")
    expect(card(page, "global.brent").get_by_test_id("status")).not_to_contain_text("Nguồn lỗi")
