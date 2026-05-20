"""Разбор дат из EXIF (общий для API и инструментов)."""
from __future__ import annotations

from datetime import datetime


def parse_exif_datetime(dt_str: str) -> datetime | None:
    s = (dt_str or "").strip().replace("T", " ")
    if not s:
        return None
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y:%m:%d %H:%M", "%Y:%m:%d"):
        try:
            n = 19 if " " in fmt and "%H" in fmt else 10
            return datetime.strptime(s[:n], fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s.replace("Z", "")[:25])
    except ValueError:
        return None
