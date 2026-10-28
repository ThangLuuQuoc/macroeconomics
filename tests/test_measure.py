"""`python -m macro.measure`: JSON cho gate chỉ số nghiệp vụ của Proofline."""

from __future__ import annotations

import json

import pytest

from macro import measure


def test_writes_backtest_by_series_with_data_snapshot(database_url, tmp_path, monkeypatch):
    monkeypatch.setenv("MACRO_DATABASE_URL", database_url)
    out = tmp_path / "m.json"
    measure.main(["--out", str(out)])
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["data_snapshot"] is None  # chưa lấy dữ liệu lần nào
    assert set(data["by_series"]) == {o["series_id"] for o in data["outcomes"]}
    assert all(o["ratio"] is None for o in data["by_series"].values())  # chưa đủ dữ liệu


def test_out_is_required():
    with pytest.raises(SystemExit):
        measure.main([])
