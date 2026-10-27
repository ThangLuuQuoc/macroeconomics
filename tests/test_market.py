"""Thẻ thị trường: connector openstock, đọc `.env`, thay đổi dạng "điểm (%)"."""

from __future__ import annotations

from datetime import date

import pytest

from macro.config import read_env_file
from macro.connectors.base import SourceError
from macro.connectors.openstock import OpenstockConnector
from macro.dashboard import Display, build_cards, change_text
from macro.db import connect

from .test_overview import load


def test_openstock_parse_reads_close_and_amount(tmp_path):
    (tmp_path / "VNINDEX.csv").write_text(
        "time,close,amount\n2026-10-23,1774.15,16942032179200\n2026-10-26,1763.55,\n",
        encoding="utf-8",
    )
    got = {(o.series_id, o.period): o.value for o in OpenstockConnector().parse(tmp_path)}
    assert got == {
        ("vn.vnindex", date(2026, 10, 23)): 1774.15,
        ("vn.hose_turnover", date(2026, 10, 23)): 16942032179200.0,
        ("vn.vnindex", date(2026, 10, 26)): 1763.55,
    }


def test_openstock_fetch_needs_a_connection_string(tmp_path, monkeypatch):
    monkeypatch.setenv("MACRO_OPENSTOCK_URL", "")
    with pytest.raises(SourceError, match="MACRO_OPENSTOCK_URL"):
        OpenstockConnector().fetch(tmp_path)


def test_env_file(tmp_path):
    env = tmp_path / ".env"
    env.write_text(
        "# chú thích\n\nMACRO_OPENSTOCK_URL = postgresql://a:b@h/db\nX=1=2\n", encoding="utf-8"
    )
    assert read_env_file(env) == {"MACRO_OPENSTOCK_URL": "postgresql://a:b@h/db", "X": "1=2"}
    assert read_env_file(tmp_path / "missing") == {}


def test_points_and_percent_change():
    display = Display(2, change="points_percent", points_unit="điểm")
    text = change_text(display, 1763.55, 1774.15, "so với phiên trước")
    assert text == "-10,60 điểm (-0,60%) so với phiên trước"
    assert change_text(display, 1.0, None, "so với phiên trước") is None


def test_foreign_flows_are_registered_but_never_shown(database_url, tmp_path):
    raw = {"VNINDEX.csv": b"time,close,amount\n2026-10-26,1763.55,13528794154180\n"}
    load(database_url, tmp_path, [{"openstock": raw}])
    with connect(database_url) as conn:
        status = conn.execute("SELECT status FROM series WHERE id = 'vn.foreign_net'").fetchone()
        cards = {card.series_id for card in build_cards(conn)}
    assert status is not None and status["status"] == "blocked"
    assert "vn.foreign_net" not in cards
    assert {"vn.vnindex", "vn.hose_turnover"} <= cards
