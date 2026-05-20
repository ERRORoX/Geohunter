"""Разбор GPS-координат из EXIF / ExifTool (десятичные, DMS, составные поля)."""
from __future__ import annotations

import re
from typing import Any

_DMS_EXIFTOOL = re.compile(
    r"(?P<deg>[-+]?\d+(?:\.\d+)?)\s*deg\s*"
    r"(?P<min>\d+(?:\.\d+)?)['\u2032]\s*"
    r"(?P<sec>\d+(?:\.\d+)?)[\"\u2033]?\s*"
    r"(?P<ref>[NSEW])?",
    re.IGNORECASE,
)
_DMS_REF_SUFFIX = re.compile(r"^(.+?)\s*([NSEW])\s*$", re.IGNORECASE)
_GPS_POSITION = re.compile(
    r"^\s*([-+]?\d+(?:\.\d+)?)\s*[,;]\s*([-+]?\d+(?:\.\d+)?)\s*$"
)


def _apply_ref(deg: float, ref: Any) -> float:
    r = str(ref or "").strip().upper()[:1]
    if r in ("S", "W"):
        return -abs(deg)
    if r in ("N", "E"):
        return abs(deg)
    return deg


def _dms_parts_to_decimal(deg: float, minutes: float, seconds: float, ref: Any) -> float:
    val = abs(deg) + abs(minutes) / 60.0 + abs(seconds) / 3600.0
    if deg < 0 or minutes < 0 or seconds < 0:
        val = -val
    return round(_apply_ref(val, ref), 6)


def parse_gps_scalar(value: Any, ref: Any = None) -> float | None:
    """Одна координата: float, DMS-кортеж, строка ExifTool «55 deg 30' 0.00\" N»."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return round(_apply_ref(float(value), ref), 6)
    if isinstance(value, (tuple, list)):
        if len(value) >= 3:
            try:
                d = float(value[0])
                m = float(value[1])
                s = float(value[2])
                return _dms_parts_to_decimal(d, m, s, ref)
            except (TypeError, ValueError):
                pass
        if len(value) == 1:
            return parse_gps_scalar(value[0], ref)
        if len(value) == 2:
            try:
                return round(float(value[0]) / float(value[1]) if float(value[1]) else float(value[0]), 6)
            except (TypeError, ValueError, ZeroDivisionError):
                return None
    text = str(value).strip()
    if not text or text in ("—", "-", "null"):
        return None

    m_ref = _DMS_REF_SUFFIX.match(text)
    if m_ref and ref is None:
        text = m_ref.group(1).strip()
        ref = m_ref.group(2)

    m_dms = _DMS_EXIFTOOL.search(text)
    if m_dms:
        d = float(m_dms.group("deg"))
        mi = float(m_dms.group("min"))
        se = float(m_dms.group("sec"))
        r = m_dms.group("ref") or ref
        return _dms_parts_to_decimal(d, mi, se, r)

    cleaned = text.replace(",", ".")
    try:
        return round(_apply_ref(float(cleaned), ref), 6)
    except ValueError:
        return None


def parse_gps_position(value: Any) -> tuple[float, float] | None:
    """Composite:GPSPosition — «lat, lon»."""
    if value is None:
        return None
    text = str(value).strip()
    m = _GPS_POSITION.match(text)
    if not m:
        return None
    try:
        lat = float(m.group(1))
        lon = float(m.group(2))
        if abs(lat) <= 90 and abs(lon) <= 180:
            return round(lat, 6), round(lon, 6)
    except ValueError:
        pass
    return None


def coords_from_gps_dict(gps: dict[str, Any] | None) -> tuple[float, float] | None:
    if not isinstance(gps, dict):
        return None
    try:
        lat = float(gps["latitude"])
        lon = float(gps["longitude"])
        if abs(lat) <= 90 and abs(lon) <= 180:
            return round(lat, 6), round(lon, 6)
    except (KeyError, TypeError, ValueError):
        pass
    lat = parse_gps_scalar(gps.get("latitude") or gps.get("lat"), gps.get("GPSLatitudeRef") or gps.get("latitude_ref"))
    lon = parse_gps_scalar(
        gps.get("longitude") or gps.get("lon"),
        gps.get("GPSLongitudeRef") or gps.get("longitude_ref"),
    )
    if lat is not None and lon is not None:
        return lat, lon
    pos = parse_gps_position(gps.get("GPSPosition") or gps.get("position"))
    if pos:
        return pos
    return None


def enrich_gps_dict(gps: dict[str, Any] | None) -> dict[str, Any] | None:
    """Дополняет gps нормализованными latitude/longitude, если их можно вывести."""
    if not isinstance(gps, dict):
        return gps
    pair = coords_from_gps_dict(gps)
    if not pair:
        return gps
    out = dict(gps)
    out["latitude"], out["longitude"] = pair
    return out
