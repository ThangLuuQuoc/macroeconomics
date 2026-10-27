"""Chuẩn hoá kỳ: tháng và quý lưu bằng ngày cuối kỳ."""

from __future__ import annotations

import calendar
from datetime import date


def month_end(year: int, month: int) -> date:
    return date(year, month, calendar.monthrange(year, month)[1])


def to_month_end(day: date) -> date:
    return month_end(day.year, day.month)
