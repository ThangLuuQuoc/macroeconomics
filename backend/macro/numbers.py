"""Định dạng số kiểu Việt Nam: dấu chấm phân cách nghìn, dấu phẩy thập phân (`1.234,56`)."""

from __future__ import annotations


def vn_number(value: float, decimals: int) -> str:
    text = f"{value:,.{decimals}f}"
    return text.replace(",", "\0").replace(".", ",").replace("\0", ".")


def vn_signed(value: float, decimals: int) -> str:
    """Có dấu `+` cho số dương hoặc bằng 0 sau khi làm tròn (vd `+0,13`, `-1,5`)."""
    text = vn_number(value, decimals)
    if text.startswith("-") and set(text) <= set("-0,."):
        text = text[1:]  # -0,00 → 0,00
    return text if text.startswith("-") else "+" + text
