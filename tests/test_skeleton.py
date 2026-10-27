"""Khung walking skeleton: schema, ingest (thành công, lỗi nguồn, bỏ qua), API."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from macro import ingest
from macro.api import create_app
from macro.config import Settings
from macro.connectors.base import Observation
from macro.db import connect, init_schema
from macro.series import Series, SeriesStatus

from .journeys.support import source_failure, write_round


class FakeConnector:
    """Connector giả đọc file `values.txt` (mỗi dòng `YYYY-MM-DD,giá trị`)."""

    name = "fake"

    def series(self) -> list[Series]:
        return [
            Series(
                id="test.fake",
                name="Chuỗi giả",
                measures="Chỉ dùng cho test",
                connector=self.name,
                upstream_provider="test",
                frequency="M",
                unit="điểm",
                transform="level",
                status=SeriesStatus.VERIFIED,
            )
        ]

    def fetch(self, raw_dir: Path) -> None:
        raise AssertionError("test không được gọi mạng")

    def parse(self, raw_dir: Path) -> list[Observation]:
        lines = (raw_dir / "values.txt").read_text(encoding="utf-8").split()
        return [
            Observation("test.fake", date.fromisoformat(day), float(value))
            for day, value in (line.split(",") for line in lines)
        ]


def run_round(database_url: str, tmp_path: Path, name: str, sources: dict[str, object]) -> int:
    raw_dir = tmp_path / name
    write_round(raw_dir, sources)
    args = ["--raw-dir", str(raw_dir), "--database-url", database_url]
    return ingest.main(args, connectors=[FakeConnector()])


def test_ingest_keeps_every_fetch_and_old_values_when_a_source_fails(database_url, tmp_path):
    first = {"fake": {"values.txt": b"2026-08-31,1.5\n2026-09-30,2.0\n"}}
    assert run_round(database_url, tmp_path, "r1", first) == 0
    revised = {"fake": {"values.txt": b"2026-09-30,2.5\n"}}
    assert run_round(database_url, tmp_path, "r2", revised) == 0
    failed = {"fake": source_failure("fake", "HTTP 500")}
    assert run_round(database_url, tmp_path, "r3", failed) == 1

    with connect(database_url) as conn:
        runs = conn.execute("SELECT status, error FROM fetch_runs ORDER BY id").fetchall()
        assert [r["status"] for r in runs] == ["ok", "ok", "error"]
        assert runs[-1]["error"] == "HTTP 500"
        latest = conn.execute(
            "SELECT period, value FROM latest_observations ORDER BY period"
        ).fetchall()
        # Bản sửa lại của 09/2026 thắng; lần lỗi không xoá hay đổi số cũ.
        assert [(r["period"], r["value"]) for r in latest] == [
            (date(2026, 8, 31), 1.5),
            (date(2026, 9, 30), 2.5),
        ]
        versions = conn.execute(
            "SELECT count(*) AS n FROM observations WHERE period = '2026-09-30'"
        ).fetchone()
        assert versions is not None and versions["n"] == 2  # giữ cả hai phiên bản


def test_ingest_skips_connectors_without_raw_files(database_url, tmp_path):
    assert run_round(database_url, tmp_path, "empty", {}) == 0
    with connect(database_url) as conn:
        row = conn.execute("SELECT count(*) AS n FROM fetch_runs").fetchone()
        assert row is not None and row["n"] == 0


def test_schema_is_idempotent(database_url):
    with connect(database_url) as conn:
        init_schema(conn)
        init_schema(conn)


def test_api_health_and_empty_indicators(database_url, tmp_path):
    web = tmp_path / "web"
    web.mkdir()
    (web / "index.html").write_text("<h1>Tổng quan vĩ mô</h1>", encoding="utf-8")
    client = TestClient(create_app(Settings(database_url=database_url, web_dir=web)))
    assert client.get("/api/health").json() == {"status": "ok"}
    assert client.get("/api/indicators").json() == []
    assert "Tổng quan vĩ mô" in client.get("/").text
