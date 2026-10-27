"""Các connector nguồn dữ liệu (T-3: mọi nguồn đi qua adapter).

Thêm một nguồn: viết một lớp theo `Connector` trong `base.py` rồi đưa vào `CONNECTORS`.
"""

from __future__ import annotations

from macro.connectors.base import Connector, Observation, SourceError
from macro.connectors.dautubenvung import DautubenvungConnector
from macro.connectors.fred import FredConnector
from macro.connectors.wb_pinksheet import PinkSheetConnector

CONNECTORS: list[Connector] = [DautubenvungConnector(), FredConnector(), PinkSheetConnector()]

# Tên nguồn hiển thị trên giao diện, theo connector.
SOURCE_LABELS = {
    "dautubenvung": "dautubenvung.vn",
    "fred": "FRED",
    "wb_pinksheet": "World Bank Pink Sheet",
}

__all__ = ["CONNECTORS", "SOURCE_LABELS", "Connector", "Observation", "SourceError"]
