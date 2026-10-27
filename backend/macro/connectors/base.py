"""Interface chung của connector: tải bản gốc (raw) tách khỏi đọc và chuẩn hoá."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Protocol

from macro.series import Series

# Bản ghi một lần lấy thất bại, nằm trong thư mục raw của connector (vd khi nạp lại hoặc kiểm thử).
FAILURE_FILE = "_failure.json"


class SourceError(Exception):
    """Nguồn không lấy được hoặc không đọc được (T-4: giữ số cũ, báo rõ)."""


@dataclass(frozen=True)
class Observation:
    series_id: str
    period: date
    value: float


class Connector(Protocol):
    name: str

    def series(self) -> list[Series]:
        """Các chuỗi connector này cung cấp (ghi vào registry)."""
        ...

    def fetch(self, raw_dir: Path) -> None:
        """Tải bản gốc từ nguồn về `raw_dir` (có gọi mạng)."""
        ...

    def parse(self, raw_dir: Path) -> list[Observation]:
        """Đọc bản gốc trong `raw_dir` thành quan sát chuẩn hoá (không gọi mạng)."""
        ...


def raise_if_failure_recorded(raw_dir: Path) -> None:
    marker = raw_dir / FAILURE_FILE
    if marker.is_file():
        error = json.loads(marker.read_text(encoding="utf-8")).get("error", "lỗi không rõ")
        raise SourceError(str(error))
