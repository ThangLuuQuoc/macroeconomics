"""Acceptance journey: dữ liệu giả lập (.proofline/specs/synthetic-data.md).

App chạy trên một bộ số "thật" nạp sẵn (PMI, IIP, Brent), rồi người dùng bật Giả lập ngay trong
app. Database giả lập của mỗi test có tên riêng (`Settings.synthetic_database_url`), chưa tồn tại
khi bắt đầu, để kiểm app tự tạo nó.
"""

from __future__ import annotations

import calendar
import json
import math
import os
import random
import socket
import subprocess
import sys
import threading
import time
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path

import httpx
import psycopg
import pytest
import uvicorn
from playwright.sync_api import Browser, Page, expect
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from macro import ingest
from macro.api import create_app
from macro.config import DEFAULT_WEB_DIR, REPO_ROOT, Settings

from ..conftest import ADMIN_URL
from .support import dautubenvung_payload, pink_sheet_xlsx, write_round

LOAD_TIMEOUT = 120_000  # ms: nạp lại database giả lập
SCENARIOS = REPO_ROOT / "backend" / "macro" / "synthetic" / "scenarios"
SIMULATED_ONLY = ["Cầu thế giới", "Lãi suất điều hành"]

# --- Bộ số "thật" (định dạng nguồn thật, nạp qua `ingest --raw-dir`) -------------------------

RNG = random.Random(20261028)
MONTHS = [(y, m) for y in range(2019, 2027) for m in range(1, 13) if (y, m) <= (2026, 9)]
BRENT, price = {}, 70.0
for y, m in MONTHS:
    price *= math.exp(RNG.gauss(0, 6) / 100)
    BRENT[f"{y}M{m:02d}"] = {"Crude oil, Brent": price}


def day(y: int, m: int) -> str:
    return f"{calendar.monthrange(y, m)[1]:02d}/{m:02d}/{y}"


REAL = {
    "dautubenvung": dautubenvung_payload(
        pmi=[{"time": day(*ym), "pmi": round(50 + RNG.gauss(0, 1), 1)} for ym in MONTHS],
        iip=[{"time": day(*ym), "iip": round(8 + RNG.gauss(0, 2), 1)} for ym in MONTHS],
    ),
    "wb_pinksheet": pink_sheet_xlsx(BRENT),
}

# --- Hạ tầng -----------------------------------------------------------------------------------


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _with_db(url: str, name: str) -> str:
    return make_conninfo(url, dbname=name)


def _db_exists(name: str) -> bool:
    with psycopg.connect(ADMIN_URL, autocommit=True) as admin:
        return (
            admin.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,)).fetchone()
            is not None
        )


@pytest.fixture
def fresh_db() -> Iterator[Callable[[], str]]:
    """Tạo thêm database trống; xoá hết khi test xong."""
    names: list[str] = []

    def create() -> str:
        name = f"macro_test_{uuid.uuid4().hex[:12]}"
        with psycopg.connect(ADMIN_URL, autocommit=True) as admin:
            admin.execute(f'CREATE DATABASE "{name}"')
        names.append(name)
        return _with_db(ADMIN_URL, name)

    yield create
    with psycopg.connect(ADMIN_URL, autocommit=True) as admin:
        for name in names:
            admin.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')


@pytest.fixture
def app(database_url: str, tmp_path: Path) -> Iterator[Callable[[], tuple[str, str]]]:
    """Nạp bộ số thật rồi khởi chạy app; trả (URL trang chủ, URL database giả lập chưa tạo)."""
    if not (DEFAULT_WEB_DIR / "index.html").is_file():
        pytest.fail(f"Chưa có bản build web ở {DEFAULT_WEB_DIR}: chạy `pnpm --dir web build`.")
    synthetic_name = f"macro_syn_{uuid.uuid4().hex[:12]}"
    servers: list[tuple[uvicorn.Server, threading.Thread]] = []

    def start() -> tuple[str, str]:
        write_round(tmp_path / "real", REAL)
        assert (
            ingest.main(["--raw-dir", str(tmp_path / "real"), "--database-url", database_url]) == 0
        )
        synthetic_url = _with_db(database_url, synthetic_name)
        settings = Settings(
            database_url=database_url, web_dir=DEFAULT_WEB_DIR, synthetic_database_url=synthetic_url
        )
        port = _free_port()
        server = uvicorn.Server(
            uvicorn.Config(create_app(settings), host="127.0.0.1", port=port, log_level="warning")
        )
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        servers.append((server, thread))
        url = f"http://127.0.0.1:{port}/"
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            try:
                if httpx.get(f"{url}api/health", timeout=2).status_code == 200:
                    return url, synthetic_url
            except httpx.HTTPError:
                pass
            time.sleep(0.1)
        pytest.fail(f"App không khởi chạy được ở {url}")

    yield start
    for server, thread in servers:
        server.should_exit = True
        thread.join(timeout=10)
    with psycopg.connect(ADMIN_URL, autocommit=True) as admin:
        admin.execute(f'DROP DATABASE IF EXISTS "{synthetic_name}" WITH (FORCE)')


def run_cli(*args: str, database_url: str | None = None) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    if database_url:
        env["MACRO_DATABASE_URL"] = database_url
    return subprocess.run(
        [sys.executable, "-m", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        cwd=REPO_ROOT,
        timeout=600,
    )


def observations(url: str) -> list[tuple]:
    with psycopg.connect(url) as conn:
        return conn.execute(
            "SELECT series_id, period, value FROM latest_observations ORDER BY series_id, period"
        ).fetchall()


def connectors(url: str) -> set[str]:
    with psycopg.connect(url) as conn:
        return {r[0] for r in conn.execute("SELECT DISTINCT connector FROM fetch_runs").fetchall()}


def switch_to_synthetic(page: Page, scenario: str, seed: str | None = None) -> None:
    # Khẳng định trước khi thao tác: thiếu công tắc thì fail ở khẳng định, không phải timeout.
    expect(page.get_by_test_id("data-mode-switch")).to_be_visible()
    page.get_by_test_id("mode-synthetic").click()
    page.get_by_test_id("scenario-select").select_option(scenario)
    if seed is not None:
        page.get_by_test_id("seed-input").fill(seed)
    page.get_by_test_id("load-synthetic").click()
    expect(page.get_by_test_id("synthetic-banner")).to_have_attribute(
        "data-scenario", scenario, timeout=LOAD_TIMEOUT
    )
    expect(page.get_by_test_id("synthetic-loading")).to_have_count(0)


def switch_to_real(page: Page) -> None:
    page.get_by_test_id("mode-real").click()
    expect(page.get_by_test_id("synthetic-banner")).to_have_count(0)


def cards_text(page: Page) -> list[str]:
    cards = page.locator("[data-testid^='indicator-']")
    expect(cards.first).to_be_visible()
    return cards.all_inner_texts()


def simulate(page: Page, shock: str, size: str) -> None:
    expect(page.get_by_test_id("shock")).to_be_visible()
    page.get_by_test_id("shock").select_option(shock)
    page.get_by_test_id("shock-size").fill(size)
    page.get_by_test_id("run").click()


# --- Kịch bản người dùng -----------------------------------------------------------------------


def test_switch_to_synthetic_and_back_without_touching_real_data(page: Page, app):
    url, synthetic_url = app()
    synthetic_name = conninfo_to_dict(synthetic_url)["dbname"]
    assert not _db_exists(synthetic_name)

    page.goto(url)
    real_cards = cards_text(page)
    expect(page.get_by_test_id("synthetic-banner")).to_have_count(0)

    # 1. Bật giả lập: database riêng được tự tạo, mọi trang có dải cảnh báo và nhãn nguồn giả lập.
    switch_to_synthetic(page, "baseline")
    assert _db_exists(synthetic_name)
    banner = page.get_by_test_id("synthetic-banner")
    expect(banner).to_contain_text("DỮ LIỆU GIẢ LẬP")
    expect(banner).to_contain_text("Không phải số liệu thật")
    expect(banner).to_have_attribute("data-seed", "42")
    expect(page.get_by_test_id("indicator-vn.pmi_mfg").get_by_test_id("source")).to_contain_text(
        "Giả lập (baseline)"
    )
    for path in ["kich-ban/", "kiem-chung/"]:
        page.goto(url + path)
        expect(page.get_by_test_id("synthetic-banner")).to_have_attribute(
            "data-scenario", "baseline"
        )

    # 2. Về số thật: trang tổng quan giống hệt lúc trước (database thật: test kế tiếp).
    page.goto(url)
    switch_to_real(page)
    assert cards_text(page) == real_cards

    # 10. Số thật: các yếu tố chỉ có trong giả lập không được chọn, và được nói rõ.
    page.goto(url + "kich-ban/")
    expect(page.get_by_test_id("shock")).to_be_visible()
    options = page.get_by_test_id("shock").locator("option").all_inner_texts()
    for name in SIMULATED_ONLY:
        assert not any(name in o for o in options), options
        expect(page.get_by_test_id("no-real-data")).to_contain_text(name)


def test_real_database_never_gets_synthetic_runs(page: Page, app, database_url: str):
    url, _ = app()
    page.goto(url)
    switch_to_synthetic(page, "baseline")
    switch_to_real(page)
    assert connectors(database_url) <= {"dautubenvung", "wb_pinksheet"}


def test_each_browser_keeps_its_own_mode(browser: Browser, app):
    url, _ = app()
    alice, bob = browser.new_page(), browser.new_page()  # mỗi trang một context, cookie riêng
    alice.goto(url)
    bob.goto(url)
    switch_to_synthetic(alice, "baseline")
    bob.reload()
    expect(bob.get_by_test_id("indicator-vn.pmi_mfg")).to_be_visible()
    expect(bob.get_by_test_id("synthetic-banner")).to_have_count(0)
    expect(bob.get_by_test_id("indicator-vn.pmi_mfg").get_by_test_id("source")).not_to_contain_text(
        "Giả lập"
    )


def test_same_seed_same_numbers_and_no_mixing_with_real_data(fresh_db, database_url: str, tmp_path):
    first, second, third = fresh_db(), fresh_db(), fresh_db()

    # 4. Cùng kịch bản, cùng seed: giống hệt; đổi seed: khác.
    for target in (first, second):
        done = run_cli("macro.ingest", "--synthetic", "baseline", "--database-url", target)
        assert done.returncode == 0, done.stderr
    assert observations(first) == observations(second)
    assert len(observations(first)) > 0
    done = run_cli(
        "macro.ingest", "--synthetic", "baseline", "--seed", "7", "--database-url", third
    )
    assert done.returncode == 0, done.stderr
    assert observations(third) != observations(first)

    # 5. Không trộn, theo cả hai chiều.
    write_round(tmp_path / "real", REAL)
    assert ingest.main(["--raw-dir", str(tmp_path / "real"), "--database-url", database_url]) == 0
    before = observations(database_url)
    refused = run_cli("macro.ingest", "--synthetic", "baseline", "--database-url", database_url)
    assert refused.returncode != 0 and "Từ chối:" in refused.stderr + refused.stdout, refused.stderr
    assert observations(database_url) == before

    before = observations(first)
    refused = run_cli("macro.ingest", "--raw-dir", str(tmp_path / "real"), "--database-url", first)
    assert refused.returncode != 0 and "Từ chối:" in refused.stderr + refused.stdout, refused.stderr
    assert observations(first) == before


def test_model_recovers_planted_effects_on_baseline(page: Page, app):
    url, synthetic_url = app()
    page.goto(url + "kich-ban/")
    switch_to_synthetic(page, "baseline")

    # 6. PMI ← Brent gài β = 0,2 (bước ngẫu nhiên, trễ 1): phản ứng cộng dồn 0,2 ở mọi tầm.
    options = page.get_by_test_id("shock").locator("option").all_inner_texts()
    for name in SIMULATED_ONLY:
        assert any(name in o for o in options), options
    simulate(page, "global.brent", "1")
    pmi = page.get_by_test_id("response-vn.pmi_mfg")
    expect(pmi.get_by_test_id("h-12")).to_be_visible()
    for h in range(1, 13):
        row = pmi.get_by_test_id(f"h-{h}")
        lower = float(row.get_attribute("data-lower") or "nan")
        upper = float(row.get_attribute("data-upper") or "nan")
        assert lower <= 0.2 <= upper, (h, lower, upper)
        assert lower > 0, (h, lower)
    # IIP không gài quan hệ: khoảng tin cậy chứa 0.
    iip = page.get_by_test_id("response-vn.iip")
    expect(iip.get_by_test_id("h-1").get_by_test_id("zero")).to_be_visible()

    # 8. CPI nối được từ hai chuỗi thành phần giả lập.
    expect(page.get_by_test_id("response-vn.cpi_yoy_long").get_by_test_id("h-1")).to_be_visible()

    # 7. GDP: từ 01/2026 tới 12/2036 luôn tăng 9%–15%.
    with psycopg.connect(synthetic_url) as conn:
        rows = conn.execute(
            "SELECT value FROM latest_observations WHERE series_id = 'vn.gdp_yoy'"
            " AND period >= '2026-01-01' AND period < '2037-01-01'"
        ).fetchall()
    assert len(rows) == 132, len(rows)
    assert all(9 <= v <= 15 for (v,) in rows), (min(rows), max(rows))


def test_cpi_splice_failure_missing_data_and_source_failure(page: Page, app):
    url, _ = app()

    # 8. Hai chuỗi CPI lệch nhau: không nối, như với số thật.
    page.goto(url + "kich-ban/")
    switch_to_synthetic(page, "cpi-mismatch")
    simulate(page, "global.brent", "20")
    cpi = page.get_by_test_id("response-vn.cpi_yoy_long")
    expect(cpi.get_by_test_id("insufficient")).to_contain_text("Chưa nối được lịch sử CPI")

    # 9. Thiếu CPI và USD.
    page.goto(url + "kiem-chung/")
    switch_to_synthetic(page, "missing-data")
    cpi = page.get_by_test_id("backtest-vn.cpi_yoy_long")
    expect(cpi.get_by_test_id("insufficient")).to_contain_text("Chưa đủ dữ liệu để kiểm chứng")
    expect(page.get_by_test_id("missing-shocks")).to_contain_text("Chỉ số USD rộng (Fed)")

    # 9. Lần lấy sau lỗi: giữ số cũ, báo rõ.
    page.goto(url)
    switch_to_synthetic(page, "source-failure")
    pmi = page.get_by_test_id("indicator-vn.pmi_mfg")
    expect(pmi.get_by_test_id("value")).not_to_be_empty()
    expect(pmi.get_by_test_id("status")).to_contain_text("Nguồn lỗi")


def test_recovery_metric_meets_threshold_and_catches_a_wrong_answer(database_url: str, tmp_path):
    # 11. Phép đo cho gate chỉ số.
    out = tmp_path / "recover.json"
    done = run_cli(
        "macro.synthetic",
        "recover",
        "--scenario",
        "baseline",
        "--out",
        str(out),
        database_url=database_url,
    )
    assert done.returncode == 0, done.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["data_snapshot"] == "synthetic:baseline:42"
    assert data["max_rel_error"] <= 0.25, data["max_rel_error"]
    assert data["false_positive_share"] <= 0.2, data["false_positive_share"]
    assert "vn.pmi_mfg<-global.brent" in data["relations"]
    assert all(not k.startswith("vn.gdp_yoy<-") for k in data["relations"])  # quan hệ bị chặn

    # Đáp án sai (gấp đôi mọi β): phép đo phải vượt ngưỡng.
    import yaml  # phụ thuộc của tính năng (đọc kịch bản), chưa có trước khi làm

    relations = yaml.safe_load((SCENARIOS / "baseline.yaml").read_text(encoding="utf-8"))[
        "relations"
    ]
    wrong = tmp_path / "wrong-truth.json"
    wrong.write_text(
        json.dumps({"relations": [{**r, "beta": 2 * r["beta"]} for r in relations]}),
        encoding="utf-8",
    )
    done = run_cli(
        "macro.synthetic",
        "recover",
        "--scenario",
        "baseline",
        "--truth",
        str(wrong),
        "--out",
        str(out),
        database_url=database_url,
    )
    assert done.returncode == 0, done.stderr
    assert json.loads(out.read_text(encoding="utf-8"))["max_rel_error"] > 0.25
