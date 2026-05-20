"""Обратный поиск изображений: ссылки по публичному URL или страницы загрузки."""
from __future__ import annotations

from typing import Any
from urllib.parse import quote


def reverse_links_for_url(image_url: str) -> dict[str, str]:
    q = quote(image_url, safe="")
    return {
        "googleLens": f"https://lens.google.com/uploadbyurl?url={q}",
        "yandexImages": f"https://yandex.ru/images/search?rpt=imageview&url={q}",
        "bingVisual": f"https://www.bing.com/images/search?q=imgurl:{q}&view=detailv2&iss=sbi",
        "tineye": f"https://tineye.com/search?url={q}",
        "baidu": f"https://image.baidu.com/n/pc_search?queryImageUrl={q}",
    }


def reverse_upload_pages() -> dict[str, str]:
    """Когда нет публичного URL — открыть сервисы с ручной загрузкой файла."""
    return {
        "googleLens": "https://lens.google.com/",
        "yandexImages": "https://yandex.ru/images/",
        "bingVisual": "https://www.bing.com/visualsearch",
        "tineye": "https://tineye.com/",
        "baidu": "https://image.baidu.com/",
    }


def build_reverse_response(image_url: str | None) -> dict[str, Any]:
    url = (image_url or "").strip()
    is_http = url.startswith("http://") or url.startswith("https://")
    if is_http:
        return {
            "success": True,
            "mode": "url",
            "imageUrl": url,
            "links": reverse_links_for_url(url),
            "uploadPages": None,
            "note": "Ссылки открывают обратный поиск с вашим публичным URL изображения.",
        }
    return {
        "success": True,
        "mode": "upload",
        "imageUrl": None,
        "links": None,
        "uploadPages": reverse_upload_pages(),
        "note": (
            "Для автоматического поиска по URL нужна публичная ссылка на картинку "
            "(поле «URL изображения»). Иначе откройте сервис ниже и загрузите файл вручную."
        ),
    }
