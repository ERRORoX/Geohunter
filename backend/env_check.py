"""Проверка локальных зависимостей GeoHunter (без загрузки всего реестра инструментов)."""
from __future__ import annotations

import logging
import os
import shutil
from typing import Any

logger = logging.getLogger(__name__)


def _tesseract_found() -> bool:
    if shutil.which("tesseract"):
        return True
    for p in ("/usr/bin/tesseract", "/usr/local/bin/tesseract", "/snap/bin/tesseract", "/opt/homebrew/bin/tesseract"):
        if os.path.isfile(p):
            return True
    env = (os.environ.get("TESSERACT_CMD") or "").strip()
    return bool(env and os.path.isfile(env))


def get_environment_status() -> dict[str, Any]:
    """Сводка для UI (лёгкая, не вызывает load_tools)."""
    st: dict[str, Any] = {
        "exiftool": bool(shutil.which("exiftool")),
        "tesseract_binary": _tesseract_found(),
        "pytesseract": False,
        "pyzbar": False,
        "numpy": False,
        "scipy": False,
        "astral": False,
        "opencv": False,
    }
    try:
        import pytesseract  # noqa: F401

        st["pytesseract"] = True
    except Exception as e:
        st["pytesseract_error"] = str(e)[:120]
    try:
        import pyzbar  # noqa: F401

        st["pyzbar"] = True
    except Exception as e:
        st["pyzbar_error"] = str(e)[:120]
    try:
        import numpy  # noqa: F401

        st["numpy"] = True
    except Exception as e:
        st["numpy_error"] = str(e)[:120]
    try:
        import scipy  # noqa: F401

        st["scipy"] = True
    except Exception as e:
        st["scipy_error"] = str(e)[:120]
    try:
        import astral  # noqa: F401

        st["astral"] = True
    except Exception as e:
        st["astral_error"] = str(e)[:120]
    try:
        import cv2  # noqa: F401

        st["opencv"] = True
    except Exception as e:
        st["opencv_error"] = str(e)[:120]
    return st


def log_startup_checks() -> None:
    st = get_environment_status()
    if not st.get("exiftool"):
        logger.warning("exiftool не найден в PATH.")
    if not st.get("tesseract_binary"):
        logger.warning("tesseract не найден — apt install tesseract-ocr tesseract-ocr-rus")
    if not st.get("pytesseract"):
        logger.warning("pip install pytesseract")
    if not st.get("pyzbar"):
        logger.warning("pip install pyzbar; apt install libzbar0")
    if not st.get("scipy") or not st.get("numpy"):
        logger.warning("numpy/scipy недоступны — анализ шума ограничен.")
    if not st.get("astral"):
        logger.warning("astral недоступен — анализ теней ограничен.")
    if not st.get("opencv"):
        logger.warning("opencv недоступен — модуль «Лица» недоступен.")
