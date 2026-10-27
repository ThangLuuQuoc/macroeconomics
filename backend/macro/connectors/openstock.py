"""Connector openstock: thị trường chứng khoán Việt Nam từ `stock_db` (.proofline/data-sources.md,
connector 4; spec market-cards).

Đọc bằng role chỉ đọc `macro_reader` (chỉ SELECT trên `stock_prices`), chuỗi kết nối ở
`MACRO_OPENSTOCK_URL`. Bản gốc lưu thành `VNINDEX.csv` (time, close, amount).
"""

from __future__ import annotations

import csv
import io
from datetime import date
from pathlib import Path

import psycopg

from macro.config import load_settings
from macro.connectors.base import Observation, SourceError
from macro.series import Series, SeriesStatus

SYMBOL = "VNINDEX"
FILENAME = f"{SYMBOL}.csv"
TERMS = "Dữ liệu nội bộ của openstock; đọc bằng role chỉ đọc macro_reader."


def _series(
    id: str,
    name: str,
    measures: str,
    unit: str,
    order: int,
    status: SeriesStatus = SeriesStatus.VERIFIED,
    definition: str = "",
) -> Series:
    return Series(
        id=id,
        name=name,
        measures=measures,
        connector="openstock",
        upstream_provider="openstock (stock_db.stock_prices)",
        source_series_id=SYMBOL,
        frequency="D",
        unit=unit,
        transform="level",
        status=status,
        definition=definition,
        source_url="openstock: stock_db.stock_prices",
        terms_note=TERMS,
        display_order=order,
    )


SERIES = [
    _series("vn.vnindex", "VN-Index", "Chỉ số VN-Index, giá đóng cửa phiên", "điểm", 90),
    _series(
        "vn.hose_turnover",
        "Giá trị giao dịch HOSE",
        "Tổng giá trị giao dịch phiên trên HOSE (cột amount của VNINDEX)",
        "đồng",
        95,
    ),
    _series(
        "vn.foreign_net",
        "Khối ngoại mua/bán ròng",
        "Giá trị mua ròng của nhà đầu tư nước ngoài, toàn thị trường",
        "đồng",
        97,
        status=SeriesStatus.BLOCKED,
        definition=(
            "stock_db chỉ có stock_prices.foreign_net_value từ 24/06 đến 28/08/2026 và quotes là"
            " ảnh chụp trong ngày của một phần mã; cộng lại sẽ ra số sai. Mở lại khi openstock lưu"
            " đủ lịch sử khối ngoại."
        ),
    ),
]


class OpenstockConnector:
    name = "openstock"

    def series(self) -> list[Series]:
        return SERIES

    def fetch(self, raw_dir: Path) -> None:
        url = load_settings().openstock_url
        if not url:
            raise SourceError("chưa đặt MACRO_OPENSTOCK_URL (tài khoản chỉ đọc vào stock_db)")
        try:
            with psycopg.connect(url, connect_timeout=10) as conn:
                rows = conn.execute(
                    "SELECT time::date, close, amount FROM stock_prices"
                    " WHERE symbol = %s ORDER BY time",
                    (SYMBOL,),
                ).fetchall()
        except psycopg.Error as exc:
            raise SourceError(f"stock_db: {exc}") from exc
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(["time", "close", "amount"])
        writer.writerows(rows)
        (raw_dir / FILENAME).write_text(buffer.getvalue(), encoding="utf-8")

    def parse(self, raw_dir: Path) -> list[Observation]:
        path = raw_dir / FILENAME
        if not path.is_file():
            raise SourceError(f"thiếu {FILENAME}")
        observations = []
        for row in csv.DictReader(io.StringIO(path.read_text(encoding="utf-8"))):
            day = date.fromisoformat(row["time"][:10])
            if row.get("close"):
                observations.append(Observation("vn.vnindex", day, float(row["close"])))
            if row.get("amount"):
                observations.append(Observation("vn.hose_turnover", day, float(row["amount"])))
        return observations
