"""
Инструмент: Офлайн Геокодер (Offline Geocoder).
Использует локальную базу GeoNames для определения адреса без интернета.
"""

from __future__ import annotations

from typing import Any

import reverse_geocoder as rg

from .base import ToolBase


class ToolPhotoGeocoder(ToolBase):
    @property
    def tool_id(self) -> str:
        return "photo-geocoder"

    @property
    def name(self) -> str:
        return "Офлайн Геокодер"

    @property
    def description(self) -> str:
        return "Определяет ближайший населенный пункт по координатам без интернета."

    def run(self, params: dict[str, Any]) -> dict[str, Any]:
        try:
            lat = float(params.get("lat", 0))
            lon = float(params.get("lon", 0))

            res = rg.search((lat, lon), verbose=False)
            if not res:
                return {"success": False, "error": "Локация не найдена в базе."}

            r = res[0]
            return {
                "success": True,
                "name": r.get("name"),
                "admin1": r.get("admin1"),
                "cc": r.get("cc"),
                "display_name": f"{r.get('name')}, {r.get('admin1')} ({r.get('cc')})"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
