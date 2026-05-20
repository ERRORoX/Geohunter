"""Детекция лиц (OpenCV Haar, один каскад, фильтр ложных срабатываний)."""

from __future__ import annotations

import base64
import io
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

from .base import ToolBase


def _strip_data_url(s: str) -> str:
    s = (s or "").strip()
    if s.startswith("data:"):
        comma = s.find(",")
        if comma != -1:
            return s[comma + 1 :]
    return s


def _iou(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    x1, y1 = max(ax, bx), max(ay, by)
    x2, y2 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    if x2 <= x1 or y2 <= y1:
        return 0.0
    inter = (x2 - x1) * (y2 - y1)
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0


def _merge_boxes(boxes: list[tuple[int, int, int, int]], iou_thresh: float = 0.45) -> list[tuple[int, int, int, int]]:
    merged: list[tuple[int, int, int, int]] = []
    for box in sorted(boxes, key=lambda b: b[2] * b[3], reverse=True):
        if any(_iou(box, kept) > iou_thresh for kept in merged):
            continue
        merged.append(box)
    return merged


def _filter_faces(
    boxes: list[tuple[int, int, int, int]],
    img_w: int,
    img_h: int,
) -> list[tuple[int, int, int, int]]:
    img_area = float(img_w * img_h)
    out: list[tuple[int, int, int, int]] = []
    for x, y, w, h in boxes:
        area = w * h
        if area < img_area * 0.008:
            continue
        if area > img_area * 0.85:
            continue
        ratio = w / float(h) if h else 0
        if ratio < 0.55 or ratio > 1.8:
            continue
        out.append((x, y, w, h))
    merged = _merge_boxes(out)
    if len(merged) <= 6:
        return merged
    return sorted(merged, key=lambda b: b[2] * b[3], reverse=True)[:6]


class ToolPhotoFaces(ToolBase):
    @property
    def tool_id(self) -> str:
        return "photo-faces"

    @property
    def name(self) -> str:
        return "Лица"

    @property
    def description(self) -> str:
        return "Поиск лиц на снимке (OpenCV)."

    def run(self, params: dict[str, Any]) -> dict[str, Any]:
        try:
            import cv2
        except ImportError:
            return {
                "success": False,
                "error": "OpenCV не установлен: pip install opencv-python-headless",
            }

        try:
            b64 = _strip_data_url(str(params.get("image_base64") or ""))
            if not b64:
                return {"success": False, "error": "Загрузите изображение."}

            raw = base64.b64decode(b64, validate=False)
            nparr = np.frombuffer(raw, np.uint8)
            bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if bgr is None:
                return {"success": False, "error": "Не удалось декодировать изображение."}

            h_img, w_img = bgr.shape[:2]
            max_side = 1600
            if max(h_img, w_img) > max_side:
                s = max_side / float(max(h_img, w_img))
                bgr = cv2.resize(bgr, (int(w_img * s), int(h_img * s)), interpolation=cv2.INTER_AREA)
                h_img, w_img = bgr.shape[:2]

            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            gray = clahe.apply(gray)

            path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            cascade = cv2.CascadeClassifier(path)
            if cascade.empty():
                return {"success": False, "error": "Модель детекции лиц не загружена."}

            raw_faces = cascade.detectMultiScale(
                gray,
                scaleFactor=1.08,
                minNeighbors=7,
                minSize=(48, 48),
                flags=cv2.CASCADE_SCALE_IMAGE,
            )
            boxes = _filter_faces(
                [(int(x), int(y), int(w), int(h)) for x, y, w, h in raw_faces],
                w_img,
                h_img,
            )

            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            pil = Image.fromarray(rgb)
            draw = ImageDraw.Draw(pil)
            face_list: list[dict[str, int]] = []
            for x, y, w, h in boxes:
                face_list.append({"x": x, "y": y, "w": w, "h": h})
                draw.rectangle([x, y, x + w, y + h], outline=(16, 185, 129), width=2)

            buf = io.BytesIO()
            pil.save(buf, format="PNG")
            ann_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            count = len(face_list)

            return {
                "success": True,
                "face_count": count,
                "faces": face_list,
                "annotated_image": f"data:image/png;base64,{ann_b64}",
                "image_width": w_img,
                "image_height": h_img,
                "verdict": f"Найдено лиц: {count}" if count else "Лица не обнаружены",
                "note": "Фронтальный детектор Haar. Профиль и очень мелкие лица могут не находиться.",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
