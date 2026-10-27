"""`python -m macro.measure --out FILE`: ghi kết quả kiểm chứng lịch sử ra JSON.

Cho gate chỉ số nghiệp vụ của Proofline (docs/09 của Proofline, mục 3): spec khai báo đường dẫn
tới tỷ lệ sai số, vd `by_series["vn.exports_yoy"].ratio`. `data_snapshot` là lần lấy dữ liệu
mới nhất, để chỉ so base với nhánh khi cả hai đo trên cùng dữ liệu.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from macro.backtest import run_backtest
from macro.config import load_settings
from macro.db import connect, init_schema


def measure(database_url: str) -> dict[str, object]:
    with connect(database_url) as conn:
        init_schema(conn)
        result = run_backtest(conn)
        row = conn.execute("SELECT max(id) AS id FROM fetch_runs WHERE status = 'ok'").fetchone()
    payload = result.model_dump(mode="json")
    return {
        "data_snapshot": f"fetch_run:{row['id']}" if row and row["id"] is not None else None,
        "by_series": {o["series_id"]: o for o in payload["outcomes"]},
        **payload,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m macro.measure")
    parser.add_argument("--out", type=Path, required=True, help="File JSON ghi kết quả.")
    args = parser.parse_args(argv)
    data = measure(load_settings().database_url)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
