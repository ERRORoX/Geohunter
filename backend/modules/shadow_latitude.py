"""Расчёт линии возможных широт по углу солнца (анализ теней)."""
from __future__ import annotations

import math
from datetime import datetime
from typing import Any


def _format_lat(deg: float) -> str:
    d = abs(deg)
    hemi = "с.ш." if deg >= 0 else "ю.ш."
    return f"{d:.0f}° {hemi}"


def _format_latitude_summary(lats: list[float]) -> str:
    if not lats:
        return "Нет совпадений для этого угла и времени (солнце под горизонтом или угол недостижим)."
    lo, hi = min(lats), max(lats)
    if abs(hi - lo) < 0.5:
        return f"≈ {_format_lat(lo)}"
    return f"{_format_lat(lo)} — {_format_lat(hi)}"


def compute_shadow_latitude_data(
    object_height: float,
    shadow_length: float,
    dt: datetime,
    *,
    tolerance_deg: float = 3.0,
    lon_step: int = 4,
) -> dict[str, Any]:
    """
    По высоте объекта и длине тени — целевой угол солнца.
    Для каждой долготы ищем широту, где в момент dt высота солнца ближе всего к целевой.
    """
    try:
        from astral import LocationInfo
        from astral.sun import elevation as sun_elevation
    except ImportError as e:
        raise ImportError("Модуль astral не установлен (pip install astral).") from e

    h = max(float(object_height), 0.01)
    l = max(float(shadow_length), 0.01)
    target_el = math.degrees(math.atan2(h, l))

    line_coords: list[list[float]] = []
    matched_lats: list[float] = []

    for lon in range(-180, 181, lon_step):
        best_lat: int | None = None
        best_diff = 999.0
        for lat in range(-66, 67, 1):
            loc = LocationInfo("", "", "UTC", lat, lon)
            try:
                el = float(sun_elevation(loc.observer, dt))
            except Exception:
                continue
            diff = abs(el - target_el)
            if diff < best_diff:
                best_diff = diff
                best_lat = lat
        if best_lat is not None and best_diff <= tolerance_deg:
            line_coords.append([float(lon), float(best_lat)])
            matched_lats.append(float(best_lat))

    geojson: dict[str, Any] | None = None
    if len(line_coords) >= 2:
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"kind": "shadow_sun_locus"},
                    "geometry": {"type": "LineString", "coordinates": line_coords},
                }
            ],
        }

    return {
        "elevation": round(target_el, 2),
        "tolerance_deg": tolerance_deg,
        "latitude_summary": _format_latitude_summary(matched_lats),
        "latitude_min": min(matched_lats) if matched_lats else None,
        "latitude_max": max(matched_lats) if matched_lats else None,
        "match_points": len(line_coords),
        "geojson": geojson,
    }
