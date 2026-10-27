"""Connector dautubenvung.vn: lõi vĩ mô Việt Nam (.proofline/data-sources.md, connector 1).

API nội bộ, không công khai, có thể đổi; chủ dự án chấp nhận rủi ro và dùng qua adapter này
(T-3). Lấy theo lịch thưa, chỉ dùng cá nhân. Đơn vị đã đối chiếu với số GSO công bố (2026-10-27):
CPI 09/2025 = 3,38% so cùng kỳ; xuất khẩu 09/2025 = 42.670 triệu USD.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from macro.connectors.base import Observation, SourceError
from macro.connectors.dates import to_month_end
from macro.connectors.http import download
from macro.series import Series, SeriesStatus

BASE_URL = "https://dautubenvung.vn"
MACRO_FILE = "data-vi-mo.json"
RATES_FILE = "lai-suat-ngan-hang.json"
FILES = {MACRO_FILE: "/api/data-vi-mo", RATES_FILE: "/api/lai-suat-ngan-hang"}
TERMS = (
    "API nội bộ của dautubenvung.vn, không công khai, có thể đổi, một phần khoá sau gói trả phí;"
    " robots.txt: use=reference. Chỉ dùng cá nhân, không phân phối lại."
)


def _series(
    id: str,
    name: str,
    measures: str,
    unit: str,
    transform: str,
    order: int,
    source_series_id: str,
    *,
    frequency: str = "M",
    status: SeriesStatus = SeriesStatus.VERIFIED,
    definition: str = "",
) -> Series:
    return Series(
        id=id,
        name=name,
        measures=measures,
        connector="dautubenvung",
        upstream_provider="GSO / NHNN qua dautubenvung.vn",
        source_series_id=source_series_id,
        frequency=frequency,  # type: ignore[arg-type]
        unit=unit,
        transform=transform,  # type: ignore[arg-type]
        status=status,
        definition=definition,
        source_url=BASE_URL + "/vi-mo",
        terms_note=TERMS,
        display_order=order,
    )


SERIES = [
    _series(
        "vn.gdp_real",
        "GDP thực (giá so sánh, quý)",
        "GDP theo giá so sánh, tỷ đồng, từng quý",
        "tỷ đồng",
        "level",
        5,
        "gdpThuc.gdp_so_sanh",
        frequency="Q",
        status=SeriesStatus.NEEDS_MAPPING,
        definition=(
            "Chuỗi đứt từ 2026: Q3/2025 = 1,70 triệu tỷ, Q3/2026 = 3,00 triệu tỷ (có thể do đổi"
            " năm gốc). Chưa có hệ số nối nên không tính tăng trưởng so cùng kỳ."
        ),
    ),
    _series(
        "vn.cpi_yoy",
        "CPI (so cùng kỳ)",
        "Lạm phát CPI, % so cùng kỳ năm trước",
        "% so cùng kỳ",
        "yoy",
        10,
        "cpi.CPI",
        status=SeriesStatus.PARTIAL,
        definition=(
            "Không cùng định nghĩa theo thời gian: từ 2025 là CPI tháng so cùng kỳ (01-03/2025"
            " khớp IMF); 2021-2024 phần lớn là CPI bình quân từ đầu năm so cùng kỳ (tháng 12 trùng"
            " lạm phát bình quân cả năm). Mô hình dùng chuỗi nối với IMF"
            " (spec scenario-simulation)."
        ),
    ),
    _series(
        "vn.exports",
        "Xuất khẩu",
        "Kim ngạch xuất khẩu hàng hoá trong tháng",
        "triệu USD",
        "level",
        20,
        "xuatNhapKhau.XK_tong",
    ),
    _series(
        "vn.imports",
        "Nhập khẩu",
        "Kim ngạch nhập khẩu hàng hoá trong tháng",
        "triệu USD",
        "level",
        30,
        "xuatNhapKhau.NK_tong",
    ),
    _series(
        "vn.fdi_disbursed",
        "FDI thực hiện",
        "Vốn FDI giải ngân trong tháng",
        "triệu USD",
        "level",
        40,
        "fdi.von_thuc_hien_fdi",
    ),
    _series(
        "vn.retail",
        "Bán lẻ hàng hoá & dịch vụ",
        "Tổng mức bán lẻ hàng hoá và doanh thu dịch vụ tiêu dùng trong tháng",
        "tỷ đồng",
        "level",
        50,
        "tongMucBanLeDichVu.tong_ban_le_hh_va_dv",
    ),
    _series(
        "vn.iip",
        "Sản xuất công nghiệp (IIP)",
        "Chỉ số sản xuất công nghiệp, % so cùng kỳ",
        "% so cùng kỳ",
        "yoy",
        60,
        "iip.iip",
    ),
    _series(
        "vn.pmi_mfg",
        "PMI sản xuất",
        "PMI ngành sản xuất Việt Nam (S&P Global), điểm",
        "điểm",
        "index",
        70,
        "pmi.pmi",
    ),
    _series(
        "vn.refinance_rate",
        "Lãi suất tái cấp vốn",
        "Lãi suất tái cấp vốn của NHNN",
        "%/năm",
        "level",
        80,
        "lai-suat-ngan-hang.policyRates.refinance",
        frequency="D",
    ),
]

# series_id → (bộ dữ liệu, trường) trong data-vi-mo.json
MACRO_FIELDS = {
    s.id: tuple(s.source_series_id.split(".", 1))  # type: ignore[union-attr]
    for s in SERIES
    if s.id != "vn.refinance_rate"
}


class DautubenvungConnector:
    name = "dautubenvung"

    def series(self) -> list[Series]:
        return SERIES

    def fetch(self, raw_dir: Path) -> None:
        for filename, path in FILES.items():
            download(BASE_URL + path, raw_dir / filename)

    def parse(self, raw_dir: Path) -> list[Observation]:
        macro = _load(raw_dir / MACRO_FILE, required=True)
        if macro.get("code") != "SUCCESS":
            raise SourceError(f"{MACRO_FILE}: code={macro.get('code')!r}")
        observations = []
        datasets = macro.get("data") or {}
        for series_id, (dataset, field) in MACRO_FIELDS.items():
            rows = (datasets.get(dataset) or {}).get(dataset) or []
            for row in rows:
                value = row.get(field)
                if value is None:
                    continue
                day = datetime.strptime(row["time"], "%d/%m/%Y").date()
                period = to_month_end(day)
                observations.append(Observation(series_id, period, float(value)))
        rates = _load(raw_dir / RATES_FILE, required=False)
        observations += _policy_changes(rates)
        return observations


def _load(path: Path, *, required: bool) -> dict[str, Any]:
    if not path.is_file():
        if required:
            raise SourceError(f"thiếu {path.name}")
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SourceError(f"{path.name} không phải JSON hợp lệ: {exc}") from exc
    if not isinstance(data, dict):
        raise SourceError(f"{path.name}: cấu trúc không như mong đợi")
    return data


def _policy_changes(rates: dict[str, Any]) -> list[Observation]:
    """Mỗi lần lãi suất tái cấp vốn đổi là một quan sát (nguồn lặp lại mức hiện hành ở ngày gần
    nhất, nên bỏ các mức trùng mức liền trước)."""
    entries = ((rates.get("data") or {}).get("policyRates")) or []
    observations: list[Observation] = []
    last: float | None = None
    for entry in sorted(entries, key=lambda e: e["date"]):
        value = entry.get("refinance")
        if value is None or float(value) == last:
            continue
        last = float(value)
        observations.append(
            Observation("vn.refinance_rate", date.fromisoformat(entry["date"]), last)
        )
    return observations
