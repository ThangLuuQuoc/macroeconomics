"""Bảng tổng quan (spec overview-dashboard): dựng thẻ chỉ số từ dữ liệu chuẩn hoá trong Postgres.

Mọi con số được tính và định dạng ở đây (định dạng số kiểu Việt Nam); web chỉ hiển thị.
Trang không biết dữ liệu đến từ nguồn nào (T-3); nguồn lỗi thì giữ số cũ và gắn nhãn (T-4).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

import psycopg
from pydantic import BaseModel

from macro.changes import ChangeKind, change, previous_period, same_period_last_year
from macro.connectors import SOURCE_LABELS
from macro.numbers import vn_number, vn_signed
from macro.series import DISPLAYABLE

LOCAL_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


class IndicatorCard(BaseModel):
    """Một thẻ trên bảng tổng quan. Mọi con số đã được tính và định dạng sẵn ở backend."""

    series_id: str
    name: str
    value_text: str
    period_text: str
    change_prev_text: str | None = None
    change_yoy_text: str | None = None
    source_text: str
    status_text: str | None = None  # "Nguồn lỗi · …" (T-4); None khi nguồn bình thường


@dataclass(frozen=True)
class Display:
    decimals: int
    suffix: str = ""
    scale: float = 1.0  # vd 1/1000: triệu USD → tỷ USD
    change: ChangeKind = "percent"
    points_unit: str = "điểm %"
    prev_label: str | None = None  # Mặc định theo tần suất


# Các thẻ của bảng tổng quan. Chuỗi không có ở đây hoặc chưa `verified`/`partial` thì không hiện.
DISPLAY: dict[str, Display] = {
    "vn.cpi_yoy": Display(2, "%", change="points"),
    "vn.exports": Display(2, " tỷ USD", scale=1 / 1000),
    "vn.imports": Display(2, " tỷ USD", scale=1 / 1000),
    "vn.fdi_disbursed": Display(2, " tỷ USD", scale=1 / 1000),
    "vn.retail": Display(1, " nghìn tỷ đồng", scale=1 / 1000),
    "vn.iip": Display(2, "%", change="points"),
    "vn.pmi_mfg": Display(1, change="points", points_unit="điểm"),
    "vn.refinance_rate": Display(
        2, "%/năm", change="points", prev_label="so với lần điều chỉnh trước"
    ),
    "us.ust10y": Display(2, "%", change="points"),
    "us.usd_broad": Display(2),
    "global.brent": Display(2, " USD/thùng"),
    "global.gold": Display(0, " USD/ounce"),
}

PREV_LABELS = {
    "D": "so với phiên trước",
    "W": "so với tuần trước",
    "M": "so với tháng trước",
    "Q": "so với quý trước",
    "A": "so với năm trước",
}


def period_text(frequency: str, period: date) -> str:
    if frequency == "M":
        return f"{period.month:02d}/{period.year}"
    if frequency == "Q":
        return f"Q{(period.month - 1) // 3 + 1}/{period.year}"
    if frequency == "A":
        return str(period.year)
    return f"{period.day:02d}/{period.month:02d}/{period.year}"


def change_text(display: Display, value: float | None, label: str) -> str | None:
    if value is None:
        return None
    if display.change == "points":
        return f"{vn_signed(value, display.decimals)} {display.points_unit} {label}"
    return f"{vn_signed(value, 1)}% {label}"


def value_text(display: Display, value: float) -> str:
    return vn_number(value * display.scale, display.decimals) + display.suffix


def source_text(connector: str, source_series_id: str | None) -> str:
    label = SOURCE_LABELS.get(connector, connector)
    return f"{label} · {source_series_id}" if connector == "fred" and source_series_id else label


def _local(moment: datetime) -> str:
    return moment.astimezone(LOCAL_TZ).strftime("%H:%M %d/%m/%Y")


def build_cards(conn: psycopg.Connection[dict]) -> list[IndicatorCard]:
    series_rows = conn.execute(
        "SELECT id, name, connector, source_series_id, frequency FROM series"
        " WHERE status = ANY(%s) ORDER BY display_order, id",
        ([str(s) for s in DISPLAYABLE],),
    ).fetchall()
    wanted = [row for row in series_rows if row["id"] in DISPLAY]
    if not wanted:
        return []
    values: dict[str, dict[date, float]] = defaultdict(dict)
    for row in conn.execute(
        "SELECT series_id, period, value FROM latest_observations WHERE series_id = ANY(%s)",
        ([row["id"] for row in wanted],),
    ).fetchall():
        values[row["series_id"]][row["period"]] = row["value"]
    runs = _latest_runs(conn)

    cards = []
    for row in wanted:
        series_values = values.get(row["id"])
        if not series_values:
            continue
        display = DISPLAY[row["id"]]
        frequency = row["frequency"]
        periods = sorted(series_values)
        latest = periods[-1]
        current = series_values[latest]
        prev = previous_period(frequency, latest, periods)
        yoy = same_period_last_year(frequency, latest, periods)
        prev_label = display.prev_label or PREV_LABELS[frequency]
        cards.append(
            IndicatorCard(
                series_id=row["id"],
                name=row["name"],
                value_text=value_text(display, current),
                period_text=period_text(frequency, latest),
                change_prev_text=change_text(
                    display,
                    change(display.change, current, series_values[prev]) if prev else None,
                    prev_label,
                ),
                change_yoy_text=change_text(
                    display,
                    change(display.change, current, series_values[yoy]) if yoy else None,
                    "so với cùng kỳ",
                ),
                source_text=source_text(row["connector"], row["source_series_id"]),
                status_text=_status(runs.get(row["connector"]), period_text(frequency, latest)),
            )
        )
    return cards


@dataclass(frozen=True)
class _Runs:
    last_status: str
    last_error: str | None
    last_ok_at: datetime | None


def _latest_runs(conn: psycopg.Connection[dict]) -> dict[str, _Runs]:
    rows = conn.execute(
        "SELECT DISTINCT ON (connector) connector, status, error,"
        " (SELECT max(finished_at) FROM fetch_runs ok"
        "   WHERE ok.connector = r.connector AND ok.status = 'ok') AS last_ok_at"
        " FROM fetch_runs r WHERE status <> 'running' ORDER BY connector, id DESC"
    ).fetchall()
    return {r["connector"]: _Runs(r["status"], r["error"], r["last_ok_at"]) for r in rows}


def _status(runs: _Runs | None, latest_period: str) -> str | None:
    if runs is None or runs.last_status != "error":
        return None
    fetched = f", lấy lần cuối {_local(runs.last_ok_at)}" if runs.last_ok_at else ""
    return f"Nguồn lỗi · số liệu đến {latest_period}{fetched}"
