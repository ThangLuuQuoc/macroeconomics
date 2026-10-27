"""Các connector nguồn dữ liệu (T-3: mọi nguồn đi qua adapter).

Thêm một nguồn: viết một lớp theo `Connector` trong `base.py` rồi đưa vào `CONNECTORS`.
"""

from __future__ import annotations

from macro.connectors.base import Connector, Observation, SourceError

CONNECTORS: list[Connector] = []

__all__ = ["CONNECTORS", "Connector", "Observation", "SourceError"]
