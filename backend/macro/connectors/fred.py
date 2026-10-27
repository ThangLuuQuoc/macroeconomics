"""Connector FRED (Fed St. Louis): CSV công khai `fredgraph.csv?id=<mã>`."""

from __future__ import annotations

import csv
import io
from datetime import date
from pathlib import Path

from macro.connectors.base import Observation, SourceError
from macro.connectors.http import download
from macro.series import Series, SeriesStatus

CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={code}"
PAGE_URL = "https://fred.stlouisfed.org/series/{code}"


def _series(id: str, code: str, name: str, measures: str, unit: str, order: int) -> Series:
    return Series(
        id=id,
        name=name,
        measures=measures,
        connector="fred",
        upstream_provider="Federal Reserve Bank of St. Louis (FRED)",
        source_series_id=code,
        frequency="D",
        unit=unit,
        transform="level",
        status=SeriesStatus.VERIFIED,
        source_url=PAGE_URL.format(code=code),
        terms_note="FRED: dữ liệu công khai, ghi nguồn khi dùng.",
        display_order=order,
    )


SERIES = [
    _series(
        "us.ust10y",
        "DGS10",
        "Lợi suất trái phiếu Mỹ 10 năm",
        "Lợi suất Treasury kỳ hạn cố định 10 năm",
        "%",
        110,
    ),
    _series(
        "us.usd_broad",
        "DTWEXBGS",
        "Chỉ số USD rộng (Fed)",
        "Nominal Broad U.S. Dollar Index của Fed; không phải DXY",
        "chỉ số (01/2006 = 100)",
        120,
    ),
]


class FredConnector:
    name = "fred"

    def series(self) -> list[Series]:
        return SERIES

    def fetch(self, raw_dir: Path) -> None:
        for item in SERIES:
            code = item.source_series_id or ""
            download(CSV_URL.format(code=code), raw_dir / f"{code}.csv")

    def parse(self, raw_dir: Path) -> list[Observation]:
        observations = []
        for item in SERIES:
            code = item.source_series_id or ""
            path = raw_dir / f"{code}.csv"
            if not path.is_file():
                raise SourceError(f"thiếu {path.name}")
            reader = csv.DictReader(io.StringIO(path.read_text(encoding="utf-8")))
            if reader.fieldnames is None or code not in reader.fieldnames:
                raise SourceError(f"{path.name}: không có cột {code}")
            for row in reader:
                raw = (row.get(code) or "").strip()
                if raw in ("", "."):  # Ngày nghỉ: FRED để trống
                    continue
                day = date.fromisoformat(row["observation_date"])
                observations.append(Observation(item.id, day, float(raw)))
        return observations
