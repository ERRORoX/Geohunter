"""Расчёт положения солнца по GPS и дате EXIF."""

from __future__ import annotations

from typing import Any

from modules.exif_datetime import parse_exif_datetime

from .base import ToolBase


class ToolPhotoSun(ToolBase):
    @property
    def tool_id(self) -> str:
        return "photo-sun"

    @property
    def name(self) -> str:
        return "Расчёт солнца"

    @property
    def description(self) -> str:
        return "Азимут и высота солнца по координатам и времени."

    def run(self, params: dict[str, Any]) -> dict[str, Any]:
        try:
            from astral import LocationInfo
            from astral.sun import azimuth, elevation
        except ImportError:
            return {"success": False, "error": "Установите astral: pip install astral"}

        try:
            lat = float(params.get("lat", 0))
            lon = float(params.get("lon", 0))
            dt_str = str(params.get("dt", "")).strip()
            if not dt_str:
                return {"success": False, "error": "Дата съёмки не передана."}

            dt = parse_exif_datetime(dt_str)
            if not dt:
                return {"success": False, "error": f"Неверный формат даты: {dt_str[:30]}"}

            loc = LocationInfo("", "", "UTC", lat, lon)
            az = azimuth(loc.observer, dt)
            el = elevation(loc.observer, dt)

            return {
                "success": True,
                "azimuth": round(az, 2),
                "elevation": round(el, 2),
                "dt": dt.strftime("%Y:%m:%d %H:%M:%S"),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
