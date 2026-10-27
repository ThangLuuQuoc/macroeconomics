"""Registry chuỗi số liệu (.proofline/data-sources.md mục 2)."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

import psycopg
from pydantic import BaseModel


class SeriesStatus(StrEnum):
    VERIFIED = "verified"  # Đã lấy được, đúng định nghĩa, lịch sử và độ mới đã kiểm
    PARTIAL = "partial"  # Lấy được nhưng thiếu kỳ / lịch sử ngắn / chưa đủ chi tiết
    NEEDS_MAPPING = "needs_mapping"  # Đã biết nguồn, chưa xác định mã chuỗi hoặc cách đọc
    BLOCKED = "blocked"  # Không có nguồn dùng được


DISPLAYABLE = (SeriesStatus.VERIFIED, SeriesStatus.PARTIAL)


class Series(BaseModel):
    id: str
    name: str
    measures: str
    connector: str
    upstream_provider: str
    source_series_id: str | None = None
    frequency: Literal["D", "W", "M", "Q", "A"]
    unit: str
    transform: Literal["level", "yoy", "mom", "index"]
    seasonal_adjustment: bool = False
    status: SeriesStatus
    is_proxy: bool = False
    definition: str = ""
    source_url: str = ""
    terms_note: str = ""
    display_order: int = 0


def upsert_series(conn: psycopg.Connection[dict], series: Series) -> None:
    fields = series.model_dump(mode="json")
    columns = ", ".join(fields)
    placeholders = ", ".join(f"%({name})s" for name in fields)
    updates = ", ".join(f"{name} = excluded.{name}" for name in fields if name != "id")
    conn.execute(
        f"INSERT INTO series ({columns}) VALUES ({placeholders})"
        f" ON CONFLICT (id) DO UPDATE SET {updates}, updated_at = now()",
        fields,
    )
