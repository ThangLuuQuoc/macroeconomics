"""Acceptance journey: thẻ thị trường chứng khoán Việt Nam (.proofline/specs/market-cards.md).

Bản gốc của connector `openstock` là `VNINDEX.csv` (time, close, amount) do connector trích từ
stock_db; journey viết bản gốc tổng hợp ngay trong file này và nạp qua `ingest --raw-dir`.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect

from .support import source_failure

VNINDEX = {
    "VNINDEX.csv": (
        b"time,close,amount,foreign_net_value\n"
        b"2026-10-23,1774.15,16942032179200,-350000000000\n"
        b"2026-10-26,1763.55,13528794154180,-120000000000\n"
    )
}


def card(page: Page, series_id: str):
    return page.get_by_test_id(f"indicator-{series_id}")


def test_vnindex_and_turnover_cards(page: Page, macro_app):
    page.goto(macro_app(rounds=[{"openstock": VNINDEX}]))

    vnindex = card(page, "vn.vnindex")
    expect(vnindex.get_by_test_id("value")).to_have_text("1.763,55")
    expect(vnindex.get_by_test_id("period")).to_have_text("26/10/2026")
    expect(vnindex.get_by_test_id("change-prev")).to_contain_text("-10,60 điểm (-0,60%)")
    expect(vnindex.get_by_test_id("change-yoy")).to_have_count(0)
    expect(vnindex.get_by_test_id("source")).to_contain_text("openstock · VNINDEX")

    turnover = card(page, "vn.hose_turnover")
    expect(turnover.get_by_test_id("value")).to_have_text("13,5 nghìn tỷ đồng")
    expect(turnover.get_by_test_id("change-prev")).to_contain_text("-20,1%")

    # Khối ngoại chưa đủ dữ liệu: không có thẻ, dù bản gốc có cột này.
    expect(card(page, "vn.foreign_net")).to_have_count(0)


def test_vnindex_keeps_last_value_when_openstock_fails(page: Page, macro_app):
    page.goto(
        macro_app(
            rounds=[
                {"openstock": VNINDEX},
                {"openstock": source_failure("openstock", "connection refused")},
            ]
        )
    )

    vnindex = card(page, "vn.vnindex")
    expect(vnindex.get_by_test_id("value")).to_have_text("1.763,55")
    expect(vnindex.get_by_test_id("status")).to_contain_text("Nguồn lỗi")
