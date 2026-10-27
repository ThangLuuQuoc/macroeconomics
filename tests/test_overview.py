"""Bảng tổng quan: định dạng số, tính thay đổi, đọc bản gốc của 3 nguồn, dựng thẻ."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from macro import ingest
from macro.changes import change, previous_period, same_period_last_year, shift_months
from macro.connectors.base import SourceError
from macro.connectors.dautubenvung import DautubenvungConnector
from macro.connectors.fred import FredConnector
from macro.connectors.wb_pinksheet import PinkSheetConnector
from macro.dashboard import build_cards, period_text
from macro.db import connect
from macro.numbers import vn_number, vn_signed

from .journeys.support import (
    dautubenvung_payload,
    fred_csv,
    pink_sheet_xlsx,
    source_failure,
    write_round,
)

# ---- Định dạng số kiểu Việt Nam ----


def test_vietnamese_number_format():
    assert vn_number(5.079999, 2) == "5,08"
    assert vn_number(59477.4 / 1000, 2) == "59,48"
    assert vn_number(690622 / 1000, 1) == "690,6"
    assert vn_number(4319, 0) == "4.319"
    assert vn_number(1234567.891, 2) == "1.234.567,89"


def test_signed_numbers():
    assert vn_signed(5.08 - 4.95, 2) == "+0,13"
    assert vn_signed(-1.5, 1) == "-1,5"
    assert vn_signed(-0.001, 2) == "+0,00"  # Không có "-0,00"


# ---- Tính thay đổi (một hàm cho mọi chỉ số) ----

M = [date(2025, 9, 30), date(2026, 8, 31), date(2026, 9, 30)]


def test_previous_and_same_period_for_months():
    assert shift_months(date(2026, 3, 31), -1) == date(2026, 2, 28)
    assert previous_period("M", date(2026, 9, 30), M) == date(2026, 8, 31)
    assert same_period_last_year("M", date(2026, 9, 30), M) == date(2025, 9, 30)
    # Không đoán: thiếu kỳ thì None.
    assert previous_period("M", date(2026, 8, 31), M) is None
    assert same_period_last_year("M", date(2026, 8, 31), M) is None


def test_previous_observation_for_daily_series_and_no_yoy():
    days = [date(2026, 10, 21), date(2026, 10, 23)]
    assert previous_period("D", date(2026, 10, 23), days) == date(2026, 10, 21)
    assert same_period_last_year("D", date(2026, 10, 23), days) is None


def test_change_kinds():
    assert change("points", 5.08, 4.95) == pytest.approx(0.13)
    assert change("percent", 59477.4, 46000.0) == pytest.approx(29.299, abs=1e-3)
    assert change("percent", 1.0, 0.0) is None


def test_period_text():
    assert period_text("M", date(2026, 9, 30)) == "09/2026"
    assert period_text("Q", date(2026, 9, 30)) == "Q3/2026"
    assert period_text("D", date(2026, 10, 23)) == "23/10/2026"


# ---- Đọc bản gốc ----


def write(tmp_path: Path, files: dict[str, bytes]) -> Path:
    for name, content in files.items():
        (tmp_path / name).write_bytes(content)
    return tmp_path


def test_dautubenvung_parse(tmp_path):
    raw = write(
        tmp_path,
        dautubenvung_payload(
            cpi=[{"time": "30/09/2026", "CPI": 5.08}],
            xuatNhapKhau=[{"time": "30/09/2025", "XK_tong": 42670.3, "NK_tong": None}],
        ),
    )
    rates = {
        "error": False,
        "data": {
            "policyRates": [
                {"date": "2023-05-25", "rediscount": 3.5, "refinance": 5},
                {"date": "2023-06-19", "rediscount": 3, "refinance": 4.5},
                {"date": "2026-10-27", "rediscount": 3, "refinance": 4.5},  # nhắc lại mức hiện hành
            ]
        },
    }
    (raw / "lai-suat-ngan-hang.json").write_text(json.dumps(rates), encoding="utf-8")
    got = {(o.series_id, o.period): o.value for o in DautubenvungConnector().parse(raw)}
    assert got[("vn.cpi_yoy", date(2026, 9, 30))] == 5.08
    assert got[("vn.exports", date(2025, 9, 30))] == 42670.3
    assert ("vn.imports", date(2025, 9, 30)) not in got  # Giá trị trống: bỏ, không điền
    assert [(p, v) for (s, p), v in sorted(got.items()) if s == "vn.refinance_rate"] == [
        (date(2023, 5, 25), 5.0),
        (date(2023, 6, 19), 4.5),
    ]


def test_dautubenvung_rejects_a_failed_response(tmp_path):
    (tmp_path / "data-vi-mo.json").write_text('{"code": "ERROR"}', encoding="utf-8")
    with pytest.raises(SourceError):
        DautubenvungConnector().parse(tmp_path)


def test_fred_parse_skips_blank_days_and_needs_every_file(tmp_path):
    write(tmp_path, fred_csv("DGS10", [("2026-10-22", 4.98), ("2026-10-23", None)]))
    with pytest.raises(SourceError):  # Thiếu DTWEXBGS.csv
        FredConnector().parse(tmp_path)
    write(tmp_path, fred_csv("DTWEXBGS", [("2026-10-23", 121.32)]))
    got = {(o.series_id, o.period): o.value for o in FredConnector().parse(tmp_path)}
    assert got == {
        ("us.ust10y", date(2026, 10, 22)): 4.98,
        ("us.usd_broad", date(2026, 10, 23)): 121.32,
    }


def test_pink_sheet_parse(tmp_path):
    months = {"2026M08": {"Crude oil, Brent": 90.9, "Gold": 4411.0}, "2026M09": {"Gold": 4319.0}}
    write(tmp_path, pink_sheet_xlsx(months))
    got = {(o.series_id, o.period): o.value for o in PinkSheetConnector().parse(tmp_path)}
    assert got == {
        ("global.brent", date(2026, 8, 31)): 90.9,
        ("global.gold", date(2026, 8, 31)): 4411.0,
        ("global.gold", date(2026, 9, 30)): 4319.0,
    }


# ---- Dựng thẻ ----


def load(database_url: str, tmp_path: Path, rounds: list[dict[str, object]]) -> None:
    for index, sources in enumerate(rounds):
        raw = tmp_path / f"round-{index}"
        write_round(raw, sources)
        ingest.main(["--raw-dir", str(raw), "--database-url", database_url])


def test_cards_skip_series_that_are_not_verified(database_url, tmp_path):
    payload = dautubenvung_payload(
        gdpThuc=[
            {"time": "30/09/2025", "gdp_so_sanh": 1696890},
            {"time": "30/09/2026", "gdp_so_sanh": 3004780},  # Chuỗi đứt: không được tính +77%
        ],
        pmi=[{"time": "30/09/2026", "pmi": 51.9}],
    )
    load(database_url, tmp_path, [{"dautubenvung": payload}])
    with connect(database_url) as conn:
        cards = {card.series_id: card for card in build_cards(conn)}
    assert "vn.gdp_real" not in cards
    assert cards["vn.pmi_mfg"].value_text == "51,9"
    assert cards["vn.pmi_mfg"].change_prev_text is None  # Không có kỳ trước


def test_failed_source_status_names_the_last_good_fetch(database_url, tmp_path):
    ust = {"DGS10": fred_csv("DGS10", [("2026-10-23", 5.0)])}
    ust["DTWEXBGS"] = fred_csv("DTWEXBGS", [("2026-10-23", 121.32)])
    load(database_url, tmp_path, [{"fred": ust}, {"fred": source_failure("fred", "HTTP 500")}])
    with connect(database_url) as conn:
        card = next(c for c in build_cards(conn) if c.series_id == "us.ust10y")
    assert card.value_text == "5,00%"
    assert card.status_text is not None
    assert card.status_text.startswith("Nguồn lỗi · số liệu đến 23/10/2026, lấy lần cuối ")
