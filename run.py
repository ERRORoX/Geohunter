#!/usr/bin/env python3
"""Запуск GeoHunter: python3 run.py (лучше системный /usr/bin/python3.13)."""
from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.join(_ROOT, "backend")
_TOOLS = os.path.join(_ROOT, "tools")


def _is_cursor_shim() -> bool:
    try:
        exe = os.path.realpath(sys.executable)
    except OSError:
        exe = sys.executable or ""
    low = exe.lower()
    return "cursor" in low or "appimage" in low or exe.endswith("electron")


def _warn_if_cursor_shim() -> None:
    if not _is_cursor_shim():
        return
    for candidate in (
        os.environ.get("GEOHUNTER_PYTHON", "").strip(),
        "/usr/bin/python3.13",
        "/usr/bin/python3",
    ):
        if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            low = candidate.lower()
            if "cursor" not in low and "appimage" not in low:
                os.execv(candidate, [candidate, *sys.argv])
    print(
        "Ошибка: python3 в этом терминале ведёт на Cursor, а не на системный Python.\n"
        "Запустите: /usr/bin/python3.13 run.py",
        file=sys.stderr,
    )
    sys.exit(1)


_warn_if_cursor_shim()

for path in (_BACKEND, _ROOT, _TOOLS):
    if path not in sys.path:
        sys.path.insert(0, path)


def main() -> None:
    import geohunter_blueprint as gh

    port = int(os.environ.get("PORT", "5050"))
    host = os.environ.get("HOST", "0.0.0.0")
    debug_env = os.environ.get("FLASK_DEBUG", "1").strip().lower()
    debug = debug_env not in ("0", "false", "no", "off")
    use_reloader = debug and os.environ.get("FLASK_USE_RELOADER", "0").strip().lower() in (
        "1",
        "true",
        "yes",
    )

    print(f"GeoHunter → http://127.0.0.1:{port}/photo/")
    print(f"Python: {sys.executable}")
    gh.app.run(host=host, port=port, debug=debug, use_reloader=use_reloader)


if __name__ == "__main__":
    main()
