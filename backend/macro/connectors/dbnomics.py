"""Connector DBnomics: chuỗi quốc tế, hiện chỉ dùng IMF CPI của Việt Nam làm lịch sử
(spec scenario-simulation mục 3; .proofline/data-sources.md, connector 5)."""

from __future__ import annotations

import json
from pathlib import Path

from macro.connectors.base import Observation, SourceError
from macro.connectors.dates import month_end
from macro.connectors.http import download
from macro.series import Series, SeriesStatus

API_URL = "https://api.db.nomics.world/v22/series/{code}?observations=1"
PAGE_URL = "https://db.nomics.world/{code}"

# series_id → mã DBnomics provider/dataset/series
CODES = {"vn.cpi_yoy_imf": "IMF/CPI/M.VN.PCPI_PC_CP_A_PT"}

SERIES = [
    Series(
        id="vn.cpi_yoy_imf",
        name="CPI (so cùng kỳ, IMF)",
        measures="CPI Việt Nam, tháng, % so với cùng kỳ năm trước (IMF)",
        connector="dbnomics",
        upstream_provider="IMF qua DBnomics",
        source_series_id=CODES["vn.cpi_yoy_imf"],
        frequency="M",
        unit="% so cùng kỳ",
        transform="yoy",
        status=SeriesStatus.PARTIAL,
        definition="Dừng ở 03/2025; chỉ dùng làm lịch sử để nối với CPI của dautubenvung.",
        source_url=PAGE_URL.format(code=CODES["vn.cpi_yoy_imf"]),
        terms_note="DBnomics/IMF: dữ liệu công khai, ghi nguồn khi dùng.",
        display_order=900,
    )
]


def raw_filename(code: str) -> str:
    return code.replace("/", "_") + ".json"


class DbnomicsConnector:
    name = "dbnomics"

    def series(self) -> list[Series]:
        return SERIES

    def fetch(self, raw_dir: Path) -> None:
        for code in CODES.values():
            download(API_URL.format(code=code), raw_dir / raw_filename(code))

    def parse(self, raw_dir: Path) -> list[Observation]:
        observations = []
        for series_id, code in CODES.items():
            path = raw_dir / raw_filename(code)
            if not path.is_file():
                raise SourceError(f"thiếu {path.name}")
            try:
                doc = json.loads(path.read_text(encoding="utf-8"))["series"]["docs"][0]
            except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
                raise SourceError(f"{path.name}: cấu trúc không như mong đợi") from exc
            for period, value in zip(doc["period"], doc["value"], strict=True):
                if value in (None, "NA"):
                    continue
                year, month = (int(part) for part in period.split("-")[:2])
                observations.append(Observation(series_id, month_end(year, month), float(value)))
        return observations
