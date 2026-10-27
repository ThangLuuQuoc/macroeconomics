"""Thay đổi so với kỳ trước và so với cùng kỳ năm trước: một chỗ cho mọi chỉ số (T-1).

Không đoán (T-4): kỳ so sánh phải có đúng trong dữ liệu; thiếu thì trả None, không nội suy.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from macro.connectors.dates import month_end

Frequency = Literal["D", "W", "M", "Q", "A"]
ChangeKind = Literal["points", "percent"]


def shift_months(period: date, months: int) -> date:
    index = period.year * 12 + period.month - 1 + months
    return month_end(index // 12, index % 12 + 1)


def previous_period(frequency: Frequency, period: date, available: list[date]) -> date | None:
    """Kỳ liền trước. Tháng/quý/năm: đúng kỳ lịch liền trước; ngày/tuần: quan sát liền trước."""
    if frequency in ("D", "W"):
        earlier = [p for p in available if p < period]
        return max(earlier) if earlier else None
    step = {"M": 1, "Q": 3, "A": 12}[frequency]
    target = shift_months(period, -step)
    return target if target in available else None


def same_period_last_year(frequency: Frequency, period: date, available: list[date]) -> date | None:
    if frequency not in ("M", "Q"):
        return None
    target = shift_months(period, -12)
    return target if target in available else None


def change(kind: ChangeKind, current: float, previous: float) -> float | None:
    """`points`: chênh lệch tuyệt đối (cho tỷ lệ, chỉ số điểm); `percent`: % thay đổi (cho mức)."""
    if kind == "points":
        return current - previous
    if previous == 0:
        return None
    return (current / previous - 1) * 100
