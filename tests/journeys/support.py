"""Dựng bản ghi nguồn tổng hợp theo đúng định dạng gốc, để kịch bản người dùng nạp qua đường
`ingest --raw-dir` mà không gọi mạng.

Định dạng đã đối chiếu với nguồn thật (2026-10-27):
- dautubenvung `/api/data-vi-mo`:
  {"code", "message", "data": {<bộ>: {<bộ>: [hàng], "header": [...]}}},
  ngày dạng `DD/MM/YYYY` ở trường `time`.
- FRED `fredgraph.csv?id=<mã>`: header `observation_date,<mã>`, ngày `YYYY-MM-DD`.
- World Bank `CMO-Historical-Data-Monthly.xlsx`: sheet "Monthly Prices", 4 dòng tiêu đề, dòng 5 tên
  cột (vd "Crude oil, Brent", "Gold"), dòng 6 đơn vị, dữ liệu từ dòng 7 với kỳ dạng `2026M09`.
"""

from __future__ import annotations

import io
import json
from dataclasses import dataclass
from pathlib import Path

from openpyxl import Workbook

from macro.connectors.base import FAILURE_FILE

RawFiles = dict[str, bytes]

PINK_SHEET_UNITS = {"Crude oil, Brent": "($/bbl)", "Gold": "($/troy oz)"}


@dataclass(frozen=True)
class SourceFailure:
    connector: str
    error: str


def dautubenvung_payload(**datasets: list[dict]) -> RawFiles:
    data = {}
    for name, rows in datasets.items():
        columns = sorted({key for row in rows for key in row if key != "time"})
        data[name] = {name: rows, "header": columns}
    body = {"code": "SUCCESS", "message": "Get macroeconomic data successfully", "data": data}
    return {"data-vi-mo.json": json.dumps(body, ensure_ascii=False).encode("utf-8")}


def fred_csv(series_id: str, rows: list[tuple[str, float | None]]) -> RawFiles:
    lines = [f"observation_date,{series_id}"]
    lines += [f"{day},{'' if value is None else value}" for day, value in rows]
    return {f"{series_id}.csv": ("\n".join(lines) + "\n").encode("utf-8")}


def pink_sheet_xlsx(months: dict[str, dict[str, float]]) -> RawFiles:
    columns = sorted({name for values in months.values() for name in values})
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.title = "Monthly Prices"
    sheet.append(["World Bank Commodity Price Data (The Pink Sheet)"])
    sheet.append(["monthly prices in nominal US dollars, 1960 to present"])
    sheet.append(["(monthly series are available only in nominal US dollars)"])
    sheet.append(["Updated on (journey fixture)"])
    sheet.append([None, *columns])
    sheet.append([None, *(PINK_SHEET_UNITS.get(name, "") for name in columns)])
    for period, values in sorted(months.items()):
        sheet.append([period, *(values.get(name) for name in columns)])
    buffer = io.BytesIO()
    workbook.save(buffer)
    return {"CMO-Historical-Data-Monthly.xlsx": buffer.getvalue()}


def source_failure(connector: str, error: str) -> SourceFailure:
    return SourceFailure(connector, error)


def write_round(raw_dir: Path, sources: dict[str, object]) -> None:
    """Ghi một vòng bản ghi nguồn: `{connector: RawFiles | {tên: RawFiles} | SourceFailure}`."""
    for connector, payload in sources.items():
        folder = raw_dir / connector
        folder.mkdir(parents=True, exist_ok=True)
        if isinstance(payload, SourceFailure):
            marker = {"error": payload.error}
            (folder / FAILURE_FILE).write_text(json.dumps(marker), encoding="utf-8")
            continue
        assert isinstance(payload, dict), f"bản ghi nguồn không hợp lệ cho {connector}"
        for name, content in _flatten(payload).items():
            (folder / name).write_bytes(content)


def _flatten(payload: dict) -> RawFiles:
    files: RawFiles = {}
    for key, value in payload.items():
        if isinstance(value, bytes):
            files[key] = value
        else:
            files.update(_flatten(value))
    return files
