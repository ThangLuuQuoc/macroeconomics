# ruff: noqa: F811  (fixture `app` lấy từ test_synthetic_data)
"""Acceptance journey: bản đồ ảnh hưởng (.proofline/specs/influence-map.md).

Chạy trên kịch bản giả lập `influence-demo`, gài sẵn với trung tâm VN-Index: Brent (β < 0) tăng
mạnh, USD (β < 0) giảm mạnh, tín dụng (β > 0) tăng mạnh ở 12 tháng cuối; lợi suất Mỹ không gài
quan hệ; không có CPI. Hạ tầng (app, công tắc giả lập) dùng chung với journey synthetic-data.
"""

from __future__ import annotations

import math

import psycopg
import yaml
from playwright.sync_api import Page, expect

from .test_synthetic_data import SCENARIOS, app, switch_to_synthetic  # noqa: F401 (fixture app)

DEMO = "influence-demo"
FACTORS = [
    "global.brent",
    "us.ust10y",
    "us.usd_broad",
    "global.demand",
    "vn.policy_rate",
    "vn.usdvnd",
    "vn.fdi_yoy",
    "vn.credit_growth",
    "vn.public_investment",
]
GLOBAL = {"global.brent", "us.ust10y", "us.usd_broad", "global.demand"}


def planted_beta(outcome: str, shock: str) -> float:
    data = yaml.safe_load((SCENARIOS / f"{DEMO}.yaml").read_text(encoding="utf-8"))
    return next(
        r["beta"] for r in data["relations"] if (r["outcome"], r["shock"]) == (outcome, shock)
    )


def number(locator, attribute: str) -> float:
    return float(locator.get_attribute(attribute) or "nan")


def open_map(page: Page, url: str) -> None:
    page.goto(url)
    link = page.get_by_role("link", name="Bản đồ ảnh hưởng")
    expect(link).to_be_visible()
    link.click()
    expect(page.get_by_test_id("center")).to_be_visible()


def choose_center(page: Page, series_id: str) -> None:
    page.get_by_test_id("center-select").select_option(series_id)
    expect(page.get_by_test_id("center")).to_have_attribute("data-series", series_id)


def bubble(page: Page, series_id: str):
    return page.get_by_test_id(f"bubble-{series_id}")


def test_bubbles_show_push_and_pull_on_the_centre(page: Page, app):
    url, synthetic_url = app()
    page.goto(url)
    # Khẳng định trước: chưa có trang thì fail ở đây, không phải khi chọn kịch bản.
    expect(page.get_by_role("link", name="Bản đồ ảnh hưởng")).to_be_visible()
    switch_to_synthetic(page, DEMO)
    open_map(page, url)

    # 1. Trung tâm mặc định là GDP; đủ 9 yếu tố, chia nhóm ngoài nước / trong nước.
    expect(page.get_by_test_id("synthetic-banner")).to_have_attribute("data-scenario", DEMO)
    expect(page.get_by_test_id("center")).to_have_attribute("data-series", "vn.gdp_yoy")
    expect(page.locator("[data-testid^='bubble-']")).to_have_count(len(FACTORS))
    for sid in FACTORS:
        scope = "global" if sid in GLOBAL else "domestic"
        expect(bubble(page, sid)).to_have_attribute("data-scope", scope)

    # 2. Trung tâm VN-Index: màu theo tác động lên trung tâm, không theo hướng của yếu tố.
    choose_center(page, "vn.vnindex")
    assert planted_beta("vn.vnindex", "global.brent") < 0
    assert planted_beta("vn.vnindex", "us.usd_broad") < 0
    assert planted_beta("vn.vnindex", "vn.credit_growth") > 0
    brent, usd, credit = (
        bubble(page, s) for s in ("global.brent", "us.usd_broad", "vn.credit_growth")
    )
    expect(brent).to_have_attribute("data-effect", "down")
    assert number(brent, "data-shock-change") > 0 and number(brent, "data-contribution") < 0
    expect(brent).to_contain_text("kéo xuống")
    expect(usd).to_have_attribute("data-effect", "up")
    assert number(usd, "data-shock-change") < 0 and number(usd, "data-contribution") > 0
    expect(usd).to_contain_text("đẩy lên")
    expect(credit).to_have_attribute("data-effect", "up")
    assert number(credit, "data-shock-change") > 0
    expect(bubble(page, "us.ust10y")).to_have_attribute("data-effect", "uncertain")
    expect(bubble(page, "us.ust10y")).to_contain_text("chưa chắc")
    expect(page.get_by_test_id("not-additive")).to_contain_text("không cộng lại được")

    # 3. Bán kính tăng theo |đóng góp|; bảng xếp hạng theo |đóng góp| giảm dần.
    sized = []
    for sid in FACTORS:
        b = bubble(page, sid)
        if b.get_attribute("data-effect") != "missing":
            sized.append((abs(number(b, "data-contribution")), number(b, "data-radius"), sid))
    sized.sort()
    for (c1, r1, s1), (c2, r2, s2) in zip(sized, sized[1:], strict=False):
        assert r1 <= r2 or math.isclose(c1, c2), (s1, c1, r1, s2, c2, r2)
    ranked = [
        (
            page.get_by_test_id("ranking")
            .locator("[data-testid^='rank-']")
            .nth(i)
            .get_attribute("data-testid")
            or ""
        ).removeprefix("rank-")
        for i in range(len(sized))
    ]
    assert ranked == [sid for _, _, sid in sorted(sized, reverse=True)], ranked

    # 4. Đóng góp của Brent = Σ_{t=m−11..m−1} β_{m−t}·x_t, β từ /api/scenario (cú sốc 1 đơn vị).
    month = page.get_by_test_id("month-select").input_value()  # "YYYY-MM"
    year, mon = (int(p) for p in month.split("-"))
    scenario = page.request.get(f"{url}api/scenario?shock=global.brent&size=1").json()
    betas = {
        row["h"]: row["estimate"]
        for o in scenario["outcomes"]
        if o["series_id"] == "vn.vnindex"
        for row in o["horizons"]
    }
    with psycopg.connect(synthetic_url) as conn:
        rows = conn.execute(
            "SELECT period, value FROM latest_observations WHERE series_id = 'global.brent'"
            " ORDER BY period"
        ).fetchall()
    level = {(p.year, p.month): v for p, v in rows}

    def x(k: int) -> float:  # 100·Δln(Brent) của tháng m − k
        y, m = divmod(year * 12 + mon - 1 - k, 12)
        py, pm = divmod(year * 12 + mon - 1 - k - 1, 12)
        return 100 * math.log(level[(y, m + 1)] / level[(py, pm + 1)])

    expected = sum(betas[k] * x(k) for k in range(1, 12))
    assert abs(number(brent, "data-contribution") - expected) <= 0.01, (expected,)

    # 5. Bấm Brent, đặt độ lớn 10%: phản ứng sau 12 tháng khớp trang giả lập.
    brent.click()
    panel = page.get_by_test_id("simulate-global.brent")
    expect(panel).to_be_visible()
    panel.get_by_test_id("shock-size").fill("10")
    response = panel.get_by_test_id("simulated-response")
    expect(response).to_have_attribute("data-size", "10")
    same = page.request.get(f"{url}api/scenario?shock=global.brent&size=10").json()
    h12 = next(
        row
        for o in same["outcomes"]
        if o["series_id"] == "vn.vnindex"
        for row in o["horizons"]
        if row["h"] == 12
    )
    assert abs(number(response, "data-estimate") - h12["estimate"]) < 1e-6
    assert abs(number(response, "data-lower") - h12["lower"]) < 1e-6
    assert abs(number(response, "data-upper") - h12["upper"]) < 1e-6

    # 6. Chọn tháng khác: số đổi theo; năm 2030 GDP trong khoảng 9%–15%.
    before = brent.get_attribute("data-contribution")
    page.get_by_test_id("month-select").select_option("2030-06")
    expect(brent).not_to_have_attribute("data-contribution", before or "")
    choose_center(page, "vn.gdp_yoy")
    level_2030 = number(page.get_by_test_id("center"), "data-level")
    assert 9 <= level_2030 <= 15, level_2030

    # 7. CPI không có dữ liệu: nói thẳng, không vẽ bong bóng.
    choose_center(page, "vn.cpi_yoy_long")
    expect(page.get_by_test_id("insufficient")).to_contain_text("Chưa đủ dữ liệu cho CPI")
    expect(page.locator("[data-testid^='bubble-']")).to_have_count(0)


def test_map_fits_a_phone_screen(page: Page, app):
    url, _ = app()
    page.goto(url)
    expect(page.get_by_role("link", name="Bản đồ ảnh hưởng")).to_be_visible()
    switch_to_synthetic(page, DEMO)
    page.set_viewport_size({"width": 375, "height": 812})
    open_map(page, url)

    # 9. Bề ngang 375 px: không cuộn ngang, đủ 9 bong bóng và bảng xếp hạng.
    expect(page.locator("[data-testid^='bubble-']")).to_have_count(len(FACTORS))
    for sid in FACTORS:
        expect(bubble(page, sid)).to_be_visible()
    expect(page.get_by_test_id("ranking")).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth") <= 375


def test_real_data_shows_only_factors_that_have_data(page: Page, app):
    url, _ = app()  # số thật nạp sẵn: PMI, IIP, Brent

    # 8. Số thật: chưa có GDP nên trung tâm là VN-Index; yếu tố chưa có nguồn được nói rõ.
    open_map(page, url)
    expect(page.get_by_test_id("synthetic-banner")).to_have_count(0)
    expect(page.get_by_test_id("center")).to_have_attribute("data-series", "vn.vnindex")
    expect(page.get_by_test_id("insufficient")).to_contain_text("Chưa đủ dữ liệu cho VN-Index")
    expect(page.get_by_test_id("no-real-data")).to_contain_text("Cầu thế giới")

    choose_center(page, "vn.pmi_mfg")
    expect(page.locator("[data-testid^='bubble-']")).to_have_count(3)
    expect(bubble(page, "us.ust10y")).to_have_attribute("data-effect", "missing")
    expect(bubble(page, "global.brent")).not_to_have_attribute("data-effect", "missing")
