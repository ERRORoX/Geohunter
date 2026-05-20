"""Business logic for GeoHunter EXIF and geocoding."""
from __future__ import annotations

import logging
from typing import Any

import requests

from config import settings
from exceptions import ProcessingError
from modules.exif_datetime import parse_exif_datetime
from modules.gps_coords import enrich_gps_dict
from tools import run_tool

logger = logging.getLogger(__name__)

__all__ = ["parse_exif_datetime"]


def process_exif_data(
    image_b64: str,
    filename: str | None,
    exiftool_enabled: bool,
    geocode_enabled: bool,
) -> dict[str, Any]:
    res = run_tool(
        "photo-search",
        {
            "image_base64": image_b64,
            "filename": filename,
            "exiftool": exiftool_enabled,
            "geocode": geocode_enabled,
        },
    )
    if not res.get("success"):
        raise ProcessingError(res.get("error") or "Ошибка разбора EXIF")
    return res


def _nominatim_reverse(lat: float, lon: float) -> dict[str, Any] | None:
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"format": "json", "lat": lat, "lon": lon, "zoom": 16, "addressdetails": 1},
            headers={"User-Agent": settings.user_agent},
            timeout=settings.nominatim_timeout,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        if not isinstance(data, dict):
            return None
        addr = data.get("address") if isinstance(data.get("address"), dict) else {}
        return {
            "display_name": (data.get("display_name") or "").strip(),
            "address": addr,
        }
    except Exception as e:
        logger.warning("Nominatim: %s", e)
        return None


def build_gps_response(res: dict[str, Any], *, geocode_enabled: bool = True) -> dict[str, Any] | None:
    gps = enrich_gps_dict(res.get("gps") if isinstance(res.get("gps"), dict) else None)
    if not gps:
        return None
    try:
        lat = float(gps["latitude"])
        lon = float(gps["longitude"])
    except (KeyError, TypeError, ValueError):
        return gps

    out = dict(gps)
    out["latitude"] = lat
    out["longitude"] = lon

    if not geocode_enabled:
        return out

    geo = _nominatim_reverse(lat, lon)
    if geo:
        out["display_name"] = geo.get("display_name") or out.get("display_name")
        if geo.get("address"):
            out["address"] = geo["address"]
        return out

    try:
        off = run_tool("photo-geocoder", {"lat": lat, "lon": lon})
        if off.get("success") and off.get("display_name"):
            out["offline_location"] = off["display_name"]
    except Exception:
        pass

    return out


def extract_dates(exif_summary: dict[str, Any]) -> dict[str, Any]:
    keys = ("DateTime", "DateTimeOriginal", "DateTimeDigitized")
    return {k: exif_summary.get(k) for k in keys if exif_summary.get(k) not in (None, "")}


def extract_camera_info(exif_summary: dict[str, Any]) -> dict[str, Any]:
    keys = ("Make", "Model", "LensModel", "BodySerialNumber")
    return {k: exif_summary.get(k) for k in keys if exif_summary.get(k) not in (None, "")}


def extract_software_info(exif_summary: dict[str, Any]) -> dict[str, Any]:
    keys = ("Software", "Artist", "Copyright")
    return {k: exif_summary.get(k) for k in keys if exif_summary.get(k) not in (None, "")}


def extract_shooting_params(exif_summary: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "ExposureTime",
        "FNumber",
        "ISOSpeedRatings",
        "PhotographicSensitivity",
        "FocalLength",
        "Flash",
        "WhiteBalance",
        "Orientation",
    )
    out: dict[str, Any] = {}
    for k in keys:
        v = exif_summary.get(k)
        if v not in (None, ""):
            out[k] = v
    return out


def exif_has_metadata(
    *,
    camera: dict[str, Any],
    dates: dict[str, Any],
    shooting: dict[str, Any],
    software: dict[str, Any],
    gps: dict[str, Any] | None,
    exiftool_tag_count: int | None,
) -> bool:
    if gps and gps.get("latitude") is not None:
        return True
    if exiftool_tag_count and exiftool_tag_count > 0:
        return True
    return bool(camera or dates or shooting or software)


def extract_privacy_warnings(exif_summary: dict[str, Any], gps: dict[str, Any] | None) -> list[str]:
    warnings: list[str] = []
    if gps and gps.get("latitude") is not None:
        warnings.append("В файле есть GPS — место съёмки может быть определено.")
    if exif_summary.get("Artist") or exif_summary.get("Copyright"):
        warnings.append("Указан автор или copyright в метаданных.")
    return warnings


def compute_sun_position(
    gps: dict[str, Any] | None,
    dates: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not gps or not dates:
        return None
    try:
        lat = float(gps["latitude"])
        lon = float(gps["longitude"])
    except (KeyError, TypeError, ValueError):
        return None
    dt_str = (
        dates.get("DateTimeOriginal")
        or dates.get("DateTime")
        or dates.get("DateTimeDigitized")
        or ""
    ).strip()
    if not dt_str:
        return None
    res = run_tool("photo-sun", {"lat": lat, "lon": lon, "dt": dt_str})
    if not res.get("success"):
        return {"error": res.get("error") or "Расчёт солнца недоступен"}
    return {
        "azimuth": res.get("azimuth"),
        "elevation": res.get("elevation"),
        "dt": res.get("dt"),
    }
