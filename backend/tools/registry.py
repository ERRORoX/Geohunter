"""Реестр инструментов GeoHunter с ленивой загрузкой и опциональными зависимостями."""
from __future__ import annotations

import importlib
import logging
import re
import time
from typing import Any
from urllib.parse import urlparse

from .base import ToolBase

logger = logging.getLogger(__name__)

_URL_RE = re.compile(r"https?://[^\s<>'\"]+", re.I)

# (tool_id, module, class, required)
_TOOL_SPECS: list[tuple[str, str, str, bool]] = [
    ("photo-search", "tool_photo_search", "ToolPhotoSearch", True),
    ("photo-ocr", "tool_photo_ocr", "ToolPhotoOCR", True),
    ("photo-qr", "tool_photo_qr", "ToolPhotoQR", True),
    ("photo-forensics", "tool_photo_forensics", "ToolPhotoForensics", True),
    ("photo-geocoder", "tool_photo_geocoder", "ToolPhotoGeocoder", False),
    ("photo-noise", "tool_photo_noise", "ToolPhotoNoise", False),
    ("photo-sun", "tool_photo_sun", "ToolPhotoSun", False),
    ("photo-stego", "tool_photo_stego", "ToolPhotoStego", False),
    ("photo-faces", "tool_photo_faces", "ToolPhotoFaces", False),
]

_tools_cache: list[ToolBase] | None = None
_load_errors: dict[str, str] = {}


def _normalize_tool_result(result: dict[str, Any]) -> dict[str, Any]:
    out = dict(result)
    if "output" not in out:
        out["output"] = ""
    else:
        out["output"] = str(out["output"])
    out["success"] = bool(out.get("success"))
    sec = out.get("sections")
    if sec is not None:
        if not isinstance(sec, list):
            out.pop("sections", None)
        else:
            cleaned: list[dict[str, str]] = []
            for item in sec:
                if isinstance(item, dict):
                    cleaned.append(
                        {
                            "title": str(item.get("title") or ""),
                            "body": str(item.get("body") or ""),
                        }
                    )
            if cleaned:
                out["sections"] = cleaned
            else:
                out.pop("sections", None)
    return out


def _stats_from_text(text: str) -> dict[str, int]:
    raw = _URL_RE.findall(text or "")
    cleaned: list[str] = []
    for u in raw:
        u = re.sub(r"[),.;]+$", "", u)
        cleaned.append(u)
    uniq_urls = {u.lower() for u in cleaned}
    hosts: set[str] = set()
    for u in uniq_urls:
        try:
            h = urlparse(u).hostname
            if h:
                hosts.add(h.lower())
        except Exception:
            continue
    return {
        "http_url_count": len(cleaned),
        "unique_urls": len(uniq_urls),
        "unique_hosts": len(hosts),
    }


def _instantiate_tool(module_name: str, class_name: str) -> ToolBase:
    mod = importlib.import_module(f".{module_name}", package=__package__)
    cls = getattr(mod, class_name)
    return cls()


def load_tools(*, force: bool = False) -> list[ToolBase]:
    """Загружает инструменты один раз; опциональные пропускаются при ImportError."""
    global _tools_cache
    if _tools_cache is not None and not force:
        return _tools_cache

    loaded: list[ToolBase] = []
    _load_errors.clear()

    for tool_id, module_name, class_name, required in _TOOL_SPECS:
        try:
            loaded.append(_instantiate_tool(module_name, class_name))
        except Exception as e:
            msg = str(e)
            _load_errors[tool_id] = msg
            if required:
                logger.error("Обязательный инструмент %s не загружен: %s", tool_id, msg)
                raise
            logger.warning("Опциональный инструмент %s недоступен: %s", tool_id, msg)

    _tools_cache = loaded
    return loaded


def get_load_errors() -> dict[str, str]:
    load_tools()
    return dict(_load_errors)


def list_tool_ids() -> list[str]:
    return [t.tool_id for t in load_tools()]


def _get_tool(tool_id: str) -> ToolBase | None:
    tid = (tool_id or "").strip()
    for t in load_tools():
        if t.tool_id == tid:
            return t
    return None


def run_tool(tool_id: str, params: dict[str, Any]) -> dict[str, Any]:
    tool_id = (tool_id or "").strip()
    tool = _get_tool(tool_id)
    if not tool:
        err = _load_errors.get(tool_id) or f"Unknown tool: {tool_id}"
        return {
            "success": False,
            "error": err,
            "output": err,
            "stats": {"duration_ms": 0, "http_url_count": 0, "unique_urls": 0, "unique_hosts": 0},
        }
    t0 = time.perf_counter()
    try:
        result = tool.run(params)
        result = _normalize_tool_result(result if isinstance(result, dict) else {"success": False, "output": ""})
        if not result.get("success") and result.get("error") and not str(result.get("output") or "").strip():
            result["output"] = str(result["error"])
    except Exception as e:
        err = str(e)
        elapsed = int((time.perf_counter() - t0) * 1000)
        st = _stats_from_text(err)
        st["duration_ms"] = elapsed
        return {"success": False, "error": err, "output": err, "stats": st}
    elapsed = int((time.perf_counter() - t0) * 1000)
    tool_supplied_stats = result.pop("stats", None)
    blob = (result.get("output") or "") + "\n" + (result.get("error") or "")
    st = _stats_from_text(blob)
    if isinstance(tool_supplied_stats, dict):
        for key in ("finding_count", "hit_count"):
            if key not in tool_supplied_stats:
                continue
            try:
                st[key] = int(tool_supplied_stats[key])
            except (TypeError, ValueError):
                continue
    st["duration_ms"] = elapsed
    result["stats"] = st
    return result
