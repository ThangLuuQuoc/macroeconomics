"""Các connector nguồn dữ liệu (T-3: mọi nguồn đi qua adapter).

Thêm một nguồn: viết một lớp theo `Connector` trong `base.py` rồi đưa vào `CONNECTORS`.
"""

from __future__ import annotations

from macro.connectors.base import Connector, Observation, SourceError
from macro.connectors.dautubenvung import DautubenvungConnector
from macro.connectors.dbnomics import DbnomicsConnector
from macro.connectors.fred import FredConnector
from macro.connectors.openstock import OpenstockConnector
from macro.connectors.wb_pinksheet import PinkSheetConnector

CONNECTORS: list[Connector] = [
    DautubenvungConnector(),
    FredConnector(),
    PinkSheetConnector(),
    OpenstockConnector(),
    DbnomicsConnector(),
]

# Tên nguồn hiển thị trên giao diện, theo connector.
SOURCE_LABELS = {
    "dautubenvung": "dautubenvung.vn",
    "fred": "FRED",
    "wb_pinksheet": "World Bank Pink Sheet",
    "openstock": "openstock",
    "dbnomics": "IMF qua DBnomics",
}

# Connector có mã chuỗi riêng cho từng chỉ số: hiện kèm mã, vd "FRED · DGS10".
SHOW_SERIES_CODE = {"fred", "openstock"}

__all__ = [
    "CONNECTORS",
    "SHOW_SERIES_CODE",
    "SOURCE_LABELS",
    "Connector",
    "Observation",
    "SourceError",
]
