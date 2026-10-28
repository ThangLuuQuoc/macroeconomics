"""`python -m macro.synthetic recover`: mô hình có tìm lại được quan hệ đã gài không.

Spec synthetic-data mục 2.6. Nạp kịch bản vào một database tạm (không đụng database giả lập đang
xem), chạy đúng hàm ước lượng của trang giả lập (`simulate`, cú sốc 1 đơn vị) và so với đáp án
thật tính từ kịch bản (`impulse_response`):

- `mean_rel_error` (chỉ số của gate) và `max_rel_error`: trung bình và lớn nhất của
  |ước lượng − thật| / |thật| trên mọi cặp có quan hệ tuyến tính, mọi tầm h = 1..12; bỏ cặp đi
  qua chuỗi `bounded` (phản ứng không tuyến tính). Dùng trung bình vì sai số mẫu ở tầm dài lớn
  (độ lệch chuẩn ~16% ở tầm 12 với mẫu 2005–2036): lớn nhất của 24 con số nhiễu không ổn định;
- `false_positive_share`: với các cặp không có quan hệ, tỷ lệ tầm h mà khoảng tin cậy 90% không
  chứa 0.
"""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo

from macro.config import load_settings
from macro.db import connect
from macro.scenario import HORIZONS, OUTCOMES, listed_shocks, simulate
from macro.synthetic import load as synthetic
from macro.synthetic.generate import bounded_downstream, impulse_response
from macro.synthetic.model import Relation, load_scenario

ZERO = 1e-12


class RecoverError(Exception):
    """Không đo được (vd không ước lượng được một cặp có quan hệ)."""


def recover(
    database_url: str, scenario_name: str, truth: list[Relation] | None = None
) -> dict[str, object]:
    scenario = load_scenario(scenario_name)
    relations = scenario.relations if truth is None else truth
    nonlinear = bounded_downstream(scenario, relations)
    name = f"macro_recover_{uuid.uuid4().hex[:12]}"
    url = make_conninfo(database_url, dbname=name)
    synthetic.ensure_database(url)
    try:
        synthetic.load(url, scenario_name)
        with connect(url) as conn:
            shocks = [s for s in listed_shocks(conn)[0] if s.series_id in scenario.series]
            estimates = {s.series_id: simulate(conn, s.series_id, 1.0) for s in shocks}
    finally:
        with psycopg.connect(make_conninfo(database_url, dbname="postgres"), autocommit=True) as a:
            a.execute(
                sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name))
            )

    pairs: dict[str, object] = {}
    nulls: dict[str, object] = {}
    errors: list[float] = []
    flags: list[bool] = []
    outcome_ids = {o.series_id for o in OUTCOMES}
    for shock_id, result in estimates.items():
        for outcome in result.outcomes:
            if outcome.series_id not in outcome_ids or outcome.series_id not in scenario.series:
                continue
            key = f"{outcome.series_id}<-{shock_id}"
            true = impulse_response(scenario, relations, shock_id, outcome.series_id)
            by_h = {row.h: row for row in outcome.horizons}
            if all(abs(v) < ZERO for v in true):
                if len(by_h) < len(HORIZONS):
                    continue  # không ước lượng được thì không thể báo nhầm
                false = [not by_h[h].includes_zero for h in HORIZONS]
                flags += false
                nulls[key] = {"false_positive_share": sum(false) / len(false)}
                continue
            if outcome.series_id in nonlinear:
                continue
            if len(by_h) < len(HORIZONS):
                raise RecoverError(
                    f"{key}: không ước lượng đủ 12 tầm ({outcome.insufficient_text})"
                )
            rows, rel = [], []
            for h, t in zip(HORIZONS, true, strict=True):
                row = by_h[h]
                e = abs(row.estimate - t) / abs(t) if abs(t) >= ZERO else 0.0
                rel.append(e)
                rows.append(
                    {
                        "h": h,
                        "truth": t,
                        "estimate": row.estimate,
                        "lower": row.lower,
                        "upper": row.upper,
                        "covered": row.lower <= t <= row.upper,
                    }
                )
            errors += rel
            pairs[key] = {
                "truth": true[0],
                "horizons": rows,
                "max_rel_error": max(rel),
                "coverage": sum(r["covered"] for r in rows) / len(rows),
            }
    if not pairs:
        raise RecoverError("kịch bản không có quan hệ tuyến tính nào để đo")
    return {
        "data_snapshot": f"synthetic:{scenario.name}:{scenario.seed}",
        "relations": pairs,
        "mean_rel_error": sum(errors) / len(errors),
        "max_rel_error": max(errors),
        "null_pairs": nulls,
        "false_positive_share": sum(flags) / len(flags) if flags else 0.0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m macro.synthetic recover")
    parser.add_argument("--scenario", required=True, help="Tên kịch bản hoặc tệp YAML")
    parser.add_argument(
        "--truth", type=Path, help='JSON {"relations": [...]} thay đáp án của kịch bản'
    )
    parser.add_argument("--out", type=Path, required=True, help="File JSON ghi kết quả")
    args = parser.parse_args(argv)
    truth = None
    if args.truth:
        data = json.loads(args.truth.read_text(encoding="utf-8"))
        truth = [Relation.model_validate(r) for r in data["relations"]]
    result = recover(load_settings().database_url, args.scenario, truth)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0
