"""Connector `synthetic`: sinh số từ kịch bản, không gọi mạng (spec synthetic-data mục 2.1).

Không nằm trong `CONNECTORS`: chỉ chạy qua `macro.synthetic.load` (công tắc trong app hoặc
`python -m macro.ingest --synthetic`).
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from macro.connectors.base import Observation, SourceError
from macro.series import Series, SeriesStatus
from macro.synthetic.generate import SERIES, observations, output_series
from macro.synthetic.model import Scenario

NAME = "synthetic"
DATA_FILE = "observations.json"
TRUTH_FILE = "truth.json"


class SyntheticConnector:
    name = NAME

    def __init__(self, scenario: Scenario, seed: int, *, fail: bool = False) -> None:
        self.scenario = scenario
        self.seed = seed
        self.fail = fail

    @property
    def label(self) -> str:
        return f"Giả lập ({self.scenario.name})"

    def series(self) -> list[Series]:
        units = {sid: meta.unit for sid, meta in SERIES.items()}
        units["vn.cpi_yoy_imf"] = units["vn.cpi_yoy"] = "%"
        return [
            Series(
                id=sid,
                name=name,
                measures=f"{name} — số giả lập, không phải số liệu thật",
                connector=NAME,
                upstream_provider=self.label,
                frequency="M",
                unit=units[sid],
                transform="level",
                status=SeriesStatus.VERIFIED,
                definition=f"Kịch bản {self.scenario.name}, seed {self.seed}",
                display_order=order,
            )
            for order, (sid, name) in enumerate(output_series(self.scenario).items())
        ]

    def fetch(self, raw_dir: Path) -> None:
        if self.fail:
            raise SourceError(f"Giả lập: nguồn lỗi theo kịch bản {self.scenario.name}")
        rows = [
            [o.series_id, o.period.isoformat(), o.value]
            for o in observations(self.scenario, self.seed)
        ]
        (raw_dir / DATA_FILE).write_text(json.dumps(rows), encoding="utf-8")
        truth = {"relations": [r.model_dump() for r in self.scenario.relations]}
        (raw_dir / TRUTH_FILE).write_text(json.dumps(truth), encoding="utf-8")

    def parse(self, raw_dir: Path) -> list[Observation]:
        rows = json.loads((raw_dir / DATA_FILE).read_text(encoding="utf-8"))
        return [Observation(sid, date.fromisoformat(day), float(v)) for sid, day, v in rows]
