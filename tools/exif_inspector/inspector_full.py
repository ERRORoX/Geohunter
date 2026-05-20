#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EXIF Inspector - Работа с EXIF данными
Вся логика работы с метаданными изображений
"""

import subprocess
import json
import os
import datetime
import tempfile

# Опциональные импорты (графики/PDF — только если вызываются соответствующие методы GUI)
try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    import webbrowser
except ImportError:
    webbrowser = None  # type: ignore

try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False

from .styles import EXIF_CATEGORIES, FIELD_NAMES


class _HeadlessApp:
    """Заглушка вместо Tk-приложения: лог и история для детективного отчёта."""

    analysis_history: list = []

    def log_message(self, msg: str) -> None:
        pass


class EXIFProcessor:
    """Класс для обработки EXIF данных"""

    def __init__(self, app=None):
        self.app = app or _HeadlessApp()
        self.analysis_history = []

    def get_all_exif_data(self, file_path):
        """Получение всех возможных метаданных из файла"""
        try:
            result = subprocess.run([
                "exiftool",
                "-j",           # JSON формат
                "-a",           # Все теги (включая дублирующиеся)
                "-u",           # Неизвестные теги
                "-G1",          # Группировка по категориям
                "-n",           # Числовые значения
                "-D",           # Подробная информация
                file_path
            ], capture_output=True, text=True, timeout=60)

            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                return None
        except Exception as e:
            self.app.log_message(f"❌ Ошибка получения метаданных: {e}")
            return None

    def _tag_short_name(self, key: str) -> str:
        if isinstance(key, str) and ":" in key:
            return key.split(":", 1)[1]
        return str(key)

    def _resolve_field_key(self, data: dict, field: str):
        """ExifTool с -G1 даёт ключи вида EXIF:Make — сопоставляем с коротким именем тега."""
        if field in data:
            return field
        suffix = ":" + field
        for k in data:
            if isinstance(k, str) and (k == field or k.endswith(suffix)):
                return k
        return None

    def format_exif_data(self, data):
        """Форматирование EXIF данных в читаемый вид"""
        if not data:
            return "Метаданные не найдены"

        formatted_output = ""

        # Сначала показываем основные категории
        for category, fields in EXIF_CATEGORIES.items():
            category_data = {}
            for field in fields:
                fk = self._resolve_field_key(data, field)
                if fk is not None:
                    raw_value = data[fk]
                    plain_value = self._unwrap_value(raw_value)
                    if plain_value is not None and str(plain_value).strip():
                        category_data[field] = raw_value

            if category_data:
                formatted_output += f"\n{category}\n"
                formatted_output += "─" * 70 + "\n"

                for field, value in category_data.items():
                    readable_field = self.get_readable_field_name(field)
                    formatted_value = self.format_field_value(field, value)
                    formatted_output += f"  {readable_field}: {formatted_value}\n"

                formatted_output += "\n"

        # Затем показываем все остальные поля
        all_categorized_short = set()
        for fields in EXIF_CATEGORIES.values():
            for f in fields:
                all_categorized_short.add(f)

        other_fields = {}
        for field, value in data.items():
            plain_value = self._unwrap_value(value)
            if plain_value is not None and str(plain_value).strip():
                short = self._tag_short_name(field)
                if short in all_categorized_short or field in all_categorized_short:
                    continue
                other_fields[field] = value

        if other_fields:
            formatted_output += "🔧 Все остальные метаданные\n"
            formatted_output += "─" * 70 + "\n"
            for field, value in other_fields.items():
                readable_field = self.get_readable_field_name(field)
                formatted_value = self.format_field_value(field, value)
                formatted_output += f"  {readable_field}: {formatted_value}\n"

        return formatted_output

    def get_readable_field_name(self, field):
        """Преобразование названий полей в читаемый вид"""
        return FIELD_NAMES.get(field, field)

    def format_field_value(self, field, value):
        """Форматирование значений полей"""
        value = self._unwrap_value(value)
        if field == "FileSize":
            try:
                size = int(float(value))
            except Exception:
                size = 0
            if size < 1024:
                return f"{size} байт"
            elif size < 1024 * 1024:
                return f"{size / 1024:.1f} KB"
            else:
                return f"{size / (1024 * 1024):.1f} MB"

        elif field in ["GPSLatitude", "GPSLongitude"]:
            try:
                coord = float(value)
                if field == "GPSLatitude":
                    direction = "N" if coord >= 0 else "S"
                else:
                    direction = "E" if coord >= 0 else "W"
                return f"{abs(coord):.6f}° {direction}"
            except:
                return str(value)

        elif field in ["ExposureTime", "ShutterSpeed"]:
            try:
                if "/" in str(value):
                    return f"{value} сек"
                exposure = float(value)
                if exposure >= 1:
                    return f"{exposure:.1f} сек"
                else:
                    return f"1/{1/exposure:.0f} сек"
            except:
                return str(value)

        elif field in ["FNumber", "Aperture"]:
            try:
                return f"f/{float(value):.1f}"
            except:
                return str(value)

        else:
            return str(value)

    def get_category_fields(self, category):
        """Получение полей для категории"""
        return EXIF_CATEGORIES.get(category, [])

    def find_exif_value(self, exif_data, suffix):
        """Универсальный поиск значения по суффиксу ключа"""
        key = next((k for k in exif_data if k.endswith(suffix)), None)
        if not key:
            return None
        return self._unwrap_value(exif_data[key])

    def _unwrap_value(self, value):
        """Приводит значение EXIF к простому виду (число/строка), если оно в виде словаря/списка."""
        try:
            # exiftool c -D/-G1 может вернуть структуры вида {"id": ..., "val": ...}
            if isinstance(value, dict):
                if 'val' in value:
                    return value['val']
                # Иногда значения лежат по ключу 'value'
                if 'value' in value:
                    return value['value']
            if isinstance(value, list) and value:
                # Берём первый элемент, часто там единственное значение
                return self._unwrap_value(value[0])
        except Exception:
            pass
        return value

    def detective_analysis(self, exif_data, geocode: bool = False):
        """Детективный анализ фотографии — более человеческий и объясняющий выводы.
        geocode: обратное геокодирование через Nominatim (сеть, лимиты использования).
        """
        if not exif_data:
            return "🕵️ Детектив: Пусто. Фотография будто стерта из хроник — ни единой зацепки."

        out = []
        out.append("🕵️ ДЕТЕКТИВНЫЙ ДОКЛАД")
        out.append("=" * 80)

        # 1) Файл
        source = self._unwrap_value(exif_data.get("SourceFile"))
        if source:
            out.append(f"📁 Досье: {source}")
        size_raw = self.find_exif_value(exif_data, ":FileSize")
        if size_raw:
            out.append(f"📏 Объем улики: {self.format_file_size(size_raw)}")
        out.append("")

        # 1.1) Анализ серийных номеров и уникальных ID
        suspicious_serials = ["000000", "123456", "111111", "999999", "abcdef", "none", "null", "test"]
        serials = []
        for key in [":CameraSerialNumber", ":InternalSerialNumber", ":LensSerialNumber"]:
            val = self.find_exif_value(exif_data, key)
            if val:
                serials.append((key, val))
        id_fields = [":ImageUniqueID", ":ExifImageUniqueID"]
        ids = [self.find_exif_value(exif_data, k) for k in id_fields if self.find_exif_value(exif_data, k)]
        serial_report = []
        for key, sn in serials:
            if not sn or str(sn).lower() in suspicious_serials or len(str(sn)) < 5:
                serial_report.append(f"⚠️ Подозрительный серийный номер ({key}): {sn}")
        # Поиск дубликатов ID в истории (если доступно)
        if hasattr(self.app, 'analysis_history') and ids:
            for uid in ids:
                count = sum(1 for hist in getattr(self.app, 'analysis_history', []) if uid in str(hist))
                if count > 1:
                    serial_report.append(f"⚠️ Уникальный ID {uid} встречается в истории {count} раз — возможный дубликат!")
        if serial_report:
            out.append("🔒 Анализ серийных номеров и ID")
            out.append("-" * 60)
            out.extend(serial_report)
            out.append("")

        # 2) Камера
        make = self.find_exif_value(exif_data, ":Make")
        model = self.find_exif_value(exif_data, ":Model")
        if make or model:
            out.append("📱 Устройство захвата")
            out.append("-" * 60)
            if make:
                out.append(f"• Производитель: {make}")
            if model:
                out.append(f"• Модель: {model}")
            out.append("Причина: эти поля записываются камерой/смартфоном автоматически.")
            out.append("")

        # 3) Время
        time_original = self.find_exif_value(exif_data, ":DateTimeOriginal")
        create_date = self.find_exif_value(exif_data, ":CreateDate")
        modify_date = self.find_exif_value(exif_data, ":ModifyDate")
        if time_original or create_date or modify_date:
            out.append("⏰ Временная линия")
            out.append("-" * 60)
            if time_original:
                out.append(f"• Время съемки: {self.format_date(time_original)}")
            if create_date:
                out.append(f"• Время создания файла: {self.format_date(create_date)}")
            if modify_date:
                out.append(f"• Время изменения: {self.format_date(modify_date)}")
            out.append("Причина: рассинхрон дат косвенно указывает на постобработку или перенос между устройствами.")
            out.append("")

        # 2) Геолокационный анализ
        lat = self.find_exif_value(exif_data, ":GPSLatitude")
        lon = self.find_exif_value(exif_data, ":GPSLongitude")
        if lat and lon:
            out.append("📍 Географические координаты")
            out.append("-" * 60)
            out.append(f"• Широта: {lat}")
            out.append(f"• Долгота: {lon}")
            out.append("Причина: смартфоны часто добавляют GPS автоматически; камеры — при наличии GPS-модуля.")
            out.append("")
        gps_dop = self.find_exif_value(exif_data, ":GPSDOP")
        geo_report = []
        if lat and lon:
            if geocode:
                try:
                    import requests

                    resp = requests.get(
                        f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=10&addressdetails=1",
                        headers={"User-Agent": "OSINT-Panel-EXIF/1.0"},
                        timeout=8,
                    )
                    if resp.status_code == 200:
                        nd = resp.json()
                        address = nd.get("address", {})
                        country = address.get("country", "?")
                        city = address.get("city", address.get("town", address.get("village", "?")))
                        geo_report.append(f"🌍 Место (Nominatim): {country}, {city}")
                except Exception as e:
                    geo_report.append(f"Не удалось определить место по GPS: {e}")
            if gps_dop:
                try:
                    dop = float(gps_dop)
                    if dop > 10:
                        geo_report.append(f"⚠️ Низкая точность GPS (DOP={dop})")
                except Exception:
                    pass
        if geo_report:
            out.append("🗺 Геолокационный анализ")
            out.append("-" * 60)
            out.extend(geo_report)
            out.append("")

        # 5) Параметры съемки и вероятные условия
        iso = self.find_exif_value(exif_data, ":ISO")
        focal = self.find_exif_value(exif_data, ":FocalLength")
        focal_35mm = self.find_exif_value(exif_data, ":FocalLengthIn35mmFormat")
        exposure = self.find_exif_value(exif_data, ":ExposureTime")
        fnum = self.find_exif_value(exif_data, ":FNumber") or self.find_exif_value(exif_data, ":Aperture")
        digital_zoom = self.find_exif_value(exif_data, ":DigitalZoomRatio")
        
        if iso or focal or exposure or fnum:
            out.append("📷 Параметры съемки")
            out.append("-" * 60)
            if iso:
                out.append(f"• ISO: {iso}")
            if fnum:
                try:
                    out.append(f"• Диафрагма: f/{float(fnum):.1f}")
                except:
                    out.append(f"• Диафрагма: {fnum}")
            if focal:
                focal_str = f"• Фокусное расстояние: {focal}"
                if focal_35mm:
                    try:
                        focal_val = float(focal)
                        focal_35_val = float(focal_35mm)
                        if abs(focal_val - focal_35_val) > 0.1:
                            crop_factor = focal_35_val / focal_val
                            focal_str += f" (35мм эквивалент: {focal_35mm}мм, кроп-фактор: {crop_factor:.1f}x)"
                    except:
                        focal_str += f" (35мм эквивалент: {focal_35mm}мм)"
                out.append(focal_str)
            if exposure:
                out.append(f"• Выдержка: {exposure}")
            if digital_zoom and digital_zoom != "1" and digital_zoom != 1:
                out.append(f"• Цифровой зум: {digital_zoom}x")

            # Анализ условий съёмки
            hints = []
            try:
                if iso and float(iso) >= 1600:
                    hints.append("высокое ISO — вероятно, снимок сделан в темноте или помещении")
            except:
                pass
            try:
                if fnum and float(fnum) <= 2.0:
                    hints.append("широкая диафрагма — автор стремился к светосиле или размытию фона")
            except:
                pass
            if exposure and isinstance(exposure, str) and exposure.startswith("1/"):
                try:
                    denom = float(exposure.split("/",1)[1])
                    if denom >= 500:
                        hints.append("короткая выдержка — вероятно, движение или яркий свет")
                except:
                    pass
            if digital_zoom and digital_zoom != "1" and digital_zoom != 1:
                try:
                    zoom_val = float(digital_zoom)
                    if zoom_val > 1.5:
                        hints.append(f"цифровой зум {digital_zoom}x — возможна потеря качества")
                except:
                    pass
            if hints:
                out.append("Версия: " + "; ".join(hints) + ".")
            out.append("")

        # 5.1) Объектив и прошивка/ПО
        lens_model = self.find_exif_value(exif_data, ":LensModel") or self.find_exif_value(exif_data, ":LensSpecification")
        lens_make = self.find_exif_value(exif_data, ":LensMake")
        lens_sn = self.find_exif_value(exif_data, ":LensSerialNumber")
        fw = self.find_exif_value(exif_data, ":FirmwareVersion")
        software = self.find_exif_value(exif_data, ":Software")
        if lens_model or lens_make or lens_sn or fw or software:
            out.append("🔭 Оптика и ПО")
            out.append("-" * 60)
            if lens_make:
                out.append(f"• Производитель объектива: {lens_make}")
            if lens_model:
                out.append(f"• Модель/спецификация объектива: {lens_model}")
            if lens_sn:
                out.append(f"• Серийный номер объектива: {lens_sn}")
            if fw:
                out.append(f"• Версия прошивки: {fw}")
            if software:
                out.append(f"• ПО: {software}")
            out.append("Примечание: наличие ПО указывает на устройство съёмки или редактор.")
            out.append("")

        # 5.2) Следы редактирования и распознавание редакторов
        creator_tool = self.find_exif_value(exif_data, ":CreatorTool")
        xmp_toolkit = self.find_exif_value(exif_data, ":XMPToolkit")
        edited_hint = []
        editor_detected = []
        
        if software and isinstance(software, str) and software.strip():
            edited_hint.append(f"ПО: {software}")
            # Распознавание редакторов по названию
            software_lower = software.lower()
            if any(editor in software_lower for editor in ['photoshop', 'ps', 'adobe']):
                editor_detected.append("Adobe Photoshop")
            elif any(editor in software_lower for editor in ['lightroom', 'lr']):
                editor_detected.append("Adobe Lightroom")
            elif any(editor in software_lower for editor in ['snapseed', 'google']):
                editor_detected.append("Google Snapseed")
            elif any(editor in software_lower for editor in ['gimp']):
                editor_detected.append("GIMP")
            elif any(editor in software_lower for editor in ['canon', 'nikon', 'sony', 'fuji']):
                editor_detected.append("Проприетарное ПО производителя камеры")
                
        if creator_tool:
            edited_hint.append(f"CreatorTool: {creator_tool}")
            creator_lower = str(creator_tool).lower()
            if any(editor in creator_lower for editor in ['photoshop', 'lightroom', 'snapseed']):
                editor_detected.append("Редактор обнаружен в CreatorTool")
                
        if xmp_toolkit:
            edited_hint.append(f"XMPToolkit: {xmp_toolkit}")
            
        if (time_original and modify_date) and str(self.format_date(modify_date)) != str(self.format_date(time_original)):
            edited_hint.append("ModifyDate отличается от времени съёмки — возможна постобработка")
            
        if edited_hint:
            out.append("🛠 Следы редактирования")
            out.append("-" * 60)
            for ln in edited_hint:
                out.append(f"• {ln}")
            if editor_detected:
                out.append(f"• Распознанные редакторы: {', '.join(set(editor_detected))}")
            out.append("")

        # 5.3) Вспышка, баланс белого, программа экспозиции, замер
        flash = self.find_exif_value(exif_data, ":Flash")
        wb = self.find_exif_value(exif_data, ":WhiteBalance")
        exp_prog = self.find_exif_value(exif_data, ":ExposureProgram")
        meter = self.find_exif_value(exif_data, ":MeteringMode")
        if flash or wb or exp_prog or meter:
            out.append("💡 Экспозиционные параметры")
            out.append("-" * 60)
            if flash is not None:
                out.append(f"• Вспышка: {flash}")
            if wb is not None:
                out.append(f"• Баланс белого: {wb}")
            if exp_prog is not None:
                out.append(f"• Программа экспозиции: {exp_prog}")
            if meter is not None:
                out.append(f"• Режим замера: {meter}")
            out.append("")

        # 5.4) GPS доп. данные
        gps_alt = self.find_exif_value(exif_data, ":GPSAltitude")
        if lat and lon or gps_alt:
            out.append("🗺 Геоданные")
            out.append("-" * 60)
            if lat and lon:
                out.append(f"• Широта/долгота: {lat}, {lon}")
            if gps_alt is not None:
                out.append(f"• Высота: {gps_alt}")
            out.append("")

        # 5.5) DPI/разрешение печати
        xres = self.find_exif_value(exif_data, ":XResolution")
        yres = self.find_exif_value(exif_data, ":YResolution")
        res_unit = self.find_exif_value(exif_data, ":ResolutionUnit")
        if xres or yres or res_unit:
            out.append("🖨 DPI / Разрешение для печати")
            out.append("-" * 60)
            if xres:
                out.append(f"• XResolution: {xres}")
            if yres:
                out.append(f"• YResolution: {yres}")
            if res_unit:
                out.append(f"• Единица: {res_unit}")
            out.append("")

        # 5.6) Цвет и профиль
        colorspace = self.find_exif_value(exif_data, ":ColorSpace")
        color_profile = self.find_exif_value(exif_data, ":ColorProfile")
        if colorspace or color_profile:
            out.append("🎨 Цветовой профиль")
            out.append("-" * 60)
            if colorspace:
                out.append(f"• ColorSpace: {colorspace}")
            if color_profile:
                out.append(f"• Профиль: {color_profile}")
            out.append("")

        # 5.7) Уникальные идентификаторы и миниатюра
        img_uid = self.find_exif_value(exif_data, ":ImageUniqueID") or self.find_exif_value(exif_data, ":ExifImageUniqueID")
        thumb_off = self.find_exif_value(exif_data, ":ThumbnailOffset")
        thumb_len = self.find_exif_value(exif_data, ":ThumbnailLength")
        if img_uid or thumb_off or thumb_len:
            out.append("🔗 Уникальные ID и миниатюра")
            out.append("-" * 60)
            if img_uid:
                out.append(f"• ImageUniqueID: {img_uid}")
            if thumb_off or thumb_len:
                out.append(f"• Встроенная миниатюра: offset={thumb_off}, length={thumb_len}")
            out.append("")

        # 5.8) Ориентация и кодирование
        orient = self.find_exif_value(exif_data, ":Orientation")
        compression = self.find_exif_value(exif_data, ":Compression")
        encoding = self.find_exif_value(exif_data, ":EncodingProcess")
        if orient or compression or encoding:
            out.append("🧭 Ориентация и кодирование")
            out.append("-" * 60)
            if orient:
                out.append(f"• Ориентация: {orient}")
            if compression:
                out.append(f"• Сжатие: {compression}")
            if encoding:
                out.append(f"• Кодирование: {encoding}")
            out.append("")

        # 5.9) Анализ сцены и типа съёмки
        scene_type = self.find_exif_value(exif_data, ":SceneType")
        scene_capture = self.find_exif_value(exif_data, ":SceneCaptureType")
        custom_rendered = self.find_exif_value(exif_data, ":CustomRendered")
        if scene_type or scene_capture or custom_rendered:
            out.append("🎬 Тип сцены и съёмки")
            out.append("-" * 60)
            if scene_type:
                out.append(f"• Тип сцены: {scene_type}")
            if scene_capture:
                scene_desc = ""
                if scene_capture == "0" or scene_capture == 0:
                    scene_desc = " (стандартная)"
                elif scene_capture == "1" or scene_capture == 1:
                    scene_desc = " (пейзаж)"
                elif scene_capture == "2" or scene_capture == 2:
                    scene_desc = " (портрет)"
                elif scene_capture == "3" or scene_capture == 3:
                    scene_desc = " (ночная сцена)"
                out.append(f"• Режим захвата: {scene_capture}{scene_desc}")
            if custom_rendered:
                out.append(f"• Пользовательская обработка: {custom_rendered}")
            out.append("")

        # 5.10) Проверка целостности и подозрительные факторы
        integrity_issues = []
        
        # Проверка на несоответствие размеров
        img_width = self.find_exif_value(exif_data, ":ImageWidth")
        img_height = self.find_exif_value(exif_data, ":ImageHeight")
        exif_width = self.find_exif_value(exif_data, ":ExifImageWidth")
        exif_height = self.find_exif_value(exif_data, ":ExifImageHeight")
        
        if img_width and exif_width and img_width != exif_width:
            integrity_issues.append("Несоответствие ширины изображения в разных полях EXIF")
        if img_height and exif_height and img_height != exif_height:
            integrity_issues.append("Несоответствие высоты изображения в разных полях EXIF")
            
        # Проверка на подозрительные даты (будущее или очень старое)
        import datetime
        try:
            if time_original:
                date_obj = datetime.datetime.strptime(str(time_original).replace(":", "-", 2), "%Y-%m-%d %H-%M-%S")
                now = datetime.datetime.now()
                if date_obj > now:
                    integrity_issues.append("Время съёмки в будущем — возможно, неправильные настройки часов")
                elif date_obj < datetime.datetime(1990, 1, 1):
                    integrity_issues.append("Очень старая дата съёмки — подозрительно")
        except:
            pass
            
        if integrity_issues:
            out.append("⚠️ Потенциальные проблемы целостности")
            out.append("-" * 60)
            for issue in integrity_issues:
                out.append(f"• {issue}")
            out.append("")

        # 3) Временной анализ
        time_report = []
        if time_original:
            try:
                dt = datetime.datetime.strptime(str(time_original).replace(":", "-", 2), "%Y-%m-%d %H-%M-%S")
                hour = dt.hour
                if 6 <= hour < 12:
                    tod = "утро"
                elif 12 <= hour < 18:
                    tod = "день"
                elif 18 <= hour < 23:
                    tod = "вечер"
                else:
                    tod = "ночь"
                time_report.append(f"🕒 Время суток: {tod}")
                # Сезон
                month = dt.month
                if month in [12,1,2]:
                    season = "зима"
                elif month in [3,4,5]:
                    season = "весна"
                elif month in [6,7,8]:
                    season = "лето"
                else:
                    season = "осень"
                time_report.append(f"📅 Сезон: {season}")
            except:
                pass
        # Манипуляции с датами
        if time_original and modify_date and str(self.format_date(modify_date)) != str(self.format_date(time_original)):
            time_report.append("⚠️ ModifyDate отличается от времени съёмки — возможна постобработка")
        if time_report:
            out.append("⏳ Временной анализ")
            out.append("-" * 60)
            out.extend(time_report)
            out.append("")

        # 4) Техническая экспертиза
        tech_report = []
        hdr = self.find_exif_value(exif_data, ":HDR")
        panorama = self.find_exif_value(exif_data, ":Panorama")
        bracketing = self.find_exif_value(exif_data, ":BracketMode")
        user_comment = self.find_exif_value(exif_data, ":UserComment")
        if hdr:
            tech_report.append("HDR: обнаружен режим расширенного динамического диапазона")
        if panorama:
            tech_report.append("Панорама: снимок является панорамой")
        if bracketing:
            tech_report.append("Брекетинг: серия снимков с разной экспозицией")
        if user_comment and ("steg" in str(user_comment).lower() or "hidden" in str(user_comment).lower()):
            tech_report.append("⚠️ Возможна стеганография (скрытые данные)")
        if tech_report:
            out.append("🔬 Техническая экспертиза")
            out.append("-" * 60)
            out.extend(tech_report)
            out.append("")

        # 5) Социальный анализ
        social_report = []
        for key in [":Artist", ":Copyright", ":Creator", ":OwnerName", ":By-line"]:
            val = self.find_exif_value(exif_data, key)
            if val:
                social_report.append(f"Автор/владелец: {val}")
        keywords = self.find_exif_value(exif_data, ":Keywords")
        description = self.find_exif_value(exif_data, ":Description")
        if keywords:
            social_report.append(f"Ключевые слова: {keywords}")
        if description:
            social_report.append(f"Описание: {description}")
        # Поиск связанных файлов по уникальным ID
        if hasattr(self.app, 'analysis_history') and ids:
            for uid in ids:
                related = [h for h in getattr(self.app, 'analysis_history', []) if uid in str(h)]
                if related and len(related) > 1:
                    social_report.append(f"⚠️ Найдено связанных файлов по ID: {len(related)}")
        if social_report:
            out.append("👥 Социальный анализ")
            out.append("-" * 60)
            out.extend(social_report)
            out.append("")

        # 6) Финальное резюме — как детектив
        # Оценим полноту улик
        score = 0
        if make or model:
            score += 25
        if time_original or create_date or modify_date:
            score += 25
        if lat and lon:
            score += 25
        if iso or focal or exposure or fnum:
            score += 25

        out.append("🎯 Заключение")
        out.append("-" * 60)
        out.append(f"Итоговая оценка улик: {score}/100")
        if score >= 75:
            out.append("Вердикт: картина ясна. Данные согласуются, указывая на подлинность и известное устройство.")
        elif score >= 50:
            out.append("Вердикт: улик достаточно, но есть пробелы — вероятна постобработка или неполные данные.")
        elif score >= 25:
            out.append("Вердикт: зацепок мало. Файл мог быть очищен или получен из пересохранения.")
        else:
            out.append("Вердикт: почти никаких улик. Слишком чисто — это уже само по себе подозрительно.")

        # 7) Расширенный мобильный анализ
        mobile_analysis = self._analyze_mobile_features(exif_data)
        if mobile_analysis:
            out.append(mobile_analysis)
            out.append("")

        # 8) Криминалистический анализ
        forensic_analysis = self._forensic_analysis(exif_data)
        if forensic_analysis:
            out.append(forensic_analysis)
            out.append("")

        # 9) Анализ содержимого и качества
        content_analysis = self._content_quality_analysis(exif_data)
        if content_analysis:
            out.append(content_analysis)
            out.append("")

        # 10) Сетевой и биометрический анализ
        network_analysis = self._network_biometric_analysis(exif_data)
        if network_analysis:
            out.append(network_analysis)
            out.append("")

        # Сохраняем анализ в историю для сравнительного анализа
        analysis_record = {
            'timestamp': datetime.datetime.now(),
            'file_path': source,
            'exif_data': exif_data,
            'score': score,
            'summary': f"Оценка: {score}/100"
        }
        self.analysis_history.append(analysis_record)
        
        return "\n".join(out)

    def format_file_size(self, size):
        """Форматирование размера файла"""
        try:
            size = self._unwrap_value(size)
            size_int = int(float(size))
            if size_int < 1024:
                return f"{size_int} байт"
            elif size_int < 1024 * 1024:
                return f"{size_int / 1024:.1f} KB"
            else:
                return f"{size_int / (1024 * 1024):.1f} MB"
        except:
            return str(size)

    def format_date(self, date_str):
        """Форматирование даты"""
        try:
            date_str = self._unwrap_value(date_str)
            return str(date_str).replace(":", "-", 2)
        except:
            return str(date_str)

    def create_gps_map(self, lat, lon, file_path):
        """Создание карты с GPS координатами"""
        try:
            import folium
            
            # Создаем карту
            m = folium.Map(location=[float(lat), float(lon)], zoom_start=15)
            
            # Добавляем маркер
            folium.Marker(
                [float(lat), float(lon)],
                popup=f"Фото: {os.path.basename(file_path)}",
                tooltip="Место съемки",
                icon=folium.Icon(color='red', icon='camera')
            ).add_to(m)
            
            # Сохраняем карту
            map_file = tempfile.mktemp(suffix='.html')
            m.save(map_file)
            
            # Открываем в браузере (опционально, в headless не нужно)
            if webbrowser:
                webbrowser.open(f"file://{map_file}")
            
            return map_file
        except ImportError:
            self.app.log_message("❌ Для создания карт установите: pip install folium")
            return None
        except Exception as e:
            self.app.log_message(f"❌ Ошибка создания карты: {e}")
            return None

    def create_timeline_graph(self):
        """Создание графика временной шкалы анализов"""
        if not MATPLOTLIB_AVAILABLE:
            self.app.log_message("❌ Для создания графиков установите: pip install matplotlib")
            return None
            
        try:
            if len(self.analysis_history) < 2:
                self.app.log_message("⚠️ Недостаточно данных для создания временной шкалы")
                return None
                
            # Подготавливаем данные
            dates = []
            scores = []
            files = []
            
            for record in self.analysis_history:
                dates.append(record['timestamp'])
                scores.append(record['score'])
                files.append(os.path.basename(record['file_path']))
            
            # Создаем график
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.plot(dates, scores, marker='o', linewidth=2, markersize=8)
            ax.set_title('Временная шкала анализов EXIF', fontsize=14, fontweight='bold')
            ax.set_xlabel('Время анализа')
            ax.set_ylabel('Оценка качества (0-100)')
            ax.grid(True, alpha=0.3)
            
            # Форматируем даты
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m %H:%M'))
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
            plt.xticks(rotation=45)
            
            # Добавляем подписи к точкам
            for i, (date, score, file) in enumerate(zip(dates, scores, files)):
                ax.annotate(f'{file}\n{score}/100', 
                           (date, score), 
                           textcoords="offset points", 
                           xytext=(0,10), 
                           ha='center',
                           fontsize=8)
            
            plt.tight_layout()
            
            # Сохраняем график
            graph_file = tempfile.mktemp(suffix='.png')
            plt.savefig(graph_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            return graph_file
        except Exception as e:
            self.app.log_message(f"❌ Ошибка создания графика: {e}")
            return None

    def create_technical_diagram(self, exif_data):
        """Создание диаграммы технических параметров"""
        if not MATPLOTLIB_AVAILABLE:
            self.app.log_message("❌ Для создания диаграмм установите: pip install matplotlib")
            return None
            
        try:
            # Собираем технические данные
            iso = self.find_exif_value(exif_data, ":ISO")
            fnum = self.find_exif_value(exif_data, ":FNumber")
            focal = self.find_exif_value(exif_data, ":FocalLength")
            exposure = self.find_exif_value(exif_data, ":ExposureTime")
            
            if not any([iso, fnum, focal, exposure]):
                self.app.log_message("⚠️ Недостаточно технических данных для диаграммы")
                return None
            
            # Создаем радиальную диаграмму
            fig, ax = plt.subplots(figsize=(10, 8), subplot_kw=dict(projection='polar'))
            
            categories = []
            values = []
            colors = []
            
            if iso:
                try:
                    iso_val = min(float(iso) / 100, 1.0)  # Нормализуем ISO
                    categories.append('ISO')
                    values.append(iso_val)
                    colors.append('red')
                except:
                    pass
            
            if fnum:
                try:
                    fnum_val = min(float(fnum) / 22, 1.0)  # Нормализуем диафрагму
                    categories.append('Диафрагма')
                    values.append(fnum_val)
                    colors.append('blue')
                except:
                    pass
            
            if focal:
                try:
                    focal_val = min(float(focal) / 200, 1.0)  # Нормализуем фокус
                    categories.append('Фокус')
                    values.append(focal_val)
                    colors.append('green')
                except:
                    pass
            
            if exposure:
                try:
                    if "/" in str(exposure):
                        exp_val = 1.0 / float(exposure.split("/")[1])
                    else:
                        exp_val = float(exposure)
                    exp_val = min(exp_val / 1.0, 1.0)  # Нормализуем выдержку
                    categories.append('Выдержка')
                    values.append(exp_val)
                    colors.append('orange')
                except:
                    pass
            
            if not categories:
                return None
            
            # Создаем радиальную диаграмму
            angles = [n / float(len(categories)) * 2 * 3.14159 for n in range(len(categories))]
            angles += angles[:1]  # Замыкаем круг
            
            values += values[:1]
            
            ax.plot(angles, values, 'o-', linewidth=2, color='cyan')
            ax.fill(angles, values, alpha=0.25, color='cyan')
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(categories)
            ax.set_ylim(0, 1)
            ax.set_title('Технические параметры съемки', fontsize=14, fontweight='bold', pad=20)
            
            plt.tight_layout()
            
            # Сохраняем диаграмму
            diagram_file = tempfile.mktemp(suffix='.png')
            plt.savefig(diagram_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            return diagram_file
        except Exception as e:
            self.app.log_message(f"❌ Ошибка создания диаграммы: {e}")
            return None

    def comparative_analysis(self):
        """Сравнительный анализ всех проанализированных файлов"""
        if len(self.analysis_history) < 2:
            return "⚠️ Недостаточно файлов для сравнительного анализа (минимум 2)"
        
        out = []
        out.append("🔍 СРАВНИТЕЛЬНЫЙ АНАЛИЗ")
        out.append("=" * 80)
        
        # Анализ устройств
        devices = {}
        for record in self.analysis_history:
            make = self.find_exif_value(record['exif_data'], ":Make")
            model = self.find_exif_value(record['exif_data'], ":Model")
            device = f"{make} {model}".strip()
            if device:
                devices[device] = devices.get(device, 0) + 1
        
        if devices:
            out.append("📱 Используемые устройства:")
            out.append("-" * 40)
            for device, count in sorted(devices.items(), key=lambda x: x[1], reverse=True):
                out.append(f"• {device}: {count} файлов")
            out.append("")
        
        # Анализ временных паттернов
        times = []
        for record in self.analysis_history:
            time_orig = self.find_exif_value(record['exif_data'], ":DateTimeOriginal")
            if time_orig:
                try:
                    dt = datetime.datetime.strptime(str(time_orig).replace(":", "-", 2), "%Y-%m-%d %H-%M-%S")
                    times.append(dt.hour)
                except:
                    pass
        
        if times:
            out.append("⏰ Временные паттерны съемки:")
            out.append("-" * 40)
            morning = sum(1 for h in times if 6 <= h < 12)
            day = sum(1 for h in times if 12 <= h < 18)
            evening = sum(1 for h in times if 18 <= h < 23)
            night = sum(1 for h in times if h < 6 or h >= 23)
            
            out.append(f"• Утро (6-12): {morning} снимков")
            out.append(f"• День (12-18): {day} снимков")
            out.append(f"• Вечер (18-23): {evening} снимков")
            out.append(f"• Ночь (23-6): {night} снимков")
            out.append("")
        
        # Анализ качества
        scores = [record['score'] for record in self.analysis_history]
        avg_score = sum(scores) / len(scores)
        max_score = max(scores)
        min_score = min(scores)
        
        out.append("📊 Статистика качества:")
        out.append("-" * 40)
        out.append(f"• Средняя оценка: {avg_score:.1f}/100")
        out.append(f"• Максимальная: {max_score}/100")
        out.append(f"• Минимальная: {min_score}/100")
        out.append("")
        
        # Поиск дубликатов по уникальным ID
        all_ids = []
        for record in self.analysis_history:
            for key in [":ImageUniqueID", ":ExifImageUniqueID"]:
                uid = self.find_exif_value(record['exif_data'], key)
                if uid:
                    all_ids.append((uid, record['file_path']))
        
        duplicates = {}
        for uid, file_path in all_ids:
            if uid in duplicates:
                duplicates[uid].append(file_path)
            else:
                duplicates[uid] = [file_path]
        
        real_duplicates = {uid: files for uid, files in duplicates.items() if len(files) > 1}
        if real_duplicates:
            out.append("🔄 Найденные дубликаты:")
            out.append("-" * 40)
            for uid, files in real_duplicates.items():
                out.append(f"• ID {uid}:")
                for file_path in files:
                    out.append(f"  - {os.path.basename(file_path)}")
            out.append("")
        
        return "\n".join(out)

    def export_to_pdf(self, exif_data, analysis_text, file_path):
        """Экспорт анализа в PDF отчет"""
        if not FPDF_AVAILABLE:
            self.app.log_message("❌ Для создания PDF установите: pip install fpdf")
            return None
            
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            
            # Заголовок
            pdf.set_font("Arial", size=16, style="B")
            pdf.cell(200, 10, txt="EXIF Inspector - Детективный отчет", ln=1, align="C")
            pdf.ln(10)
            
            # Информация о файле
            pdf.set_font("Arial", size=12, style="B")
            pdf.cell(200, 10, txt="Информация о файле:", ln=1)
            pdf.set_font("Arial", size=10)
            pdf.cell(200, 10, txt=f"Файл: {os.path.basename(file_path)}", ln=1)
            pdf.cell(200, 10, txt=f"Полный путь: {file_path}", ln=1)
            pdf.cell(200, 10, txt=f"Дата анализа: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')}", ln=1)
            pdf.ln(5)
            
            # Детективный анализ
            pdf.set_font("Arial", size=12, style="B")
            pdf.cell(200, 10, txt="Детективный анализ:", ln=1)
            pdf.set_font("Arial", size=9)
            
            # Разбиваем текст на строки и добавляем в PDF
            lines = analysis_text.split('\n')
            for line in lines:
                if len(line) > 80:
                    # Разбиваем длинные строки
                    words = line.split()
                    current_line = ""
                    for word in words:
                        if len(current_line + word) < 80:
                            current_line += word + " "
                        else:
                            if current_line:
                                pdf.cell(200, 5, txt=current_line.strip(), ln=1)
                            current_line = word + " "
                    if current_line:
                        pdf.cell(200, 5, txt=current_line.strip(), ln=1)
                else:
                    pdf.cell(200, 5, txt=line, ln=1)
            
            # Сохраняем PDF
            pdf_file = file_path.rsplit('.', 1)[0] + '_exif_report.pdf'
            pdf.output(pdf_file)
            
            return pdf_file
        except Exception as e:
            self.app.log_message(f"❌ Ошибка создания PDF: {e}")
            return None

    def export_to_html(self, exif_data, analysis_text, file_path):
        """Экспорт анализа в HTML отчет"""
        try:
            html_content = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EXIF Inspector - Детективный отчет</title>
    <style>
        body {{
            font-family: 'Consolas', monospace;
            background-color: #000;
            color: #00ff00;
            margin: 20px;
            line-height: 1.6;
        }}
        .header {{
            text-align: center;
            border: 2px solid #00ff00;
            padding: 20px;
            margin-bottom: 20px;
        }}
        .section {{
            margin: 20px 0;
            padding: 15px;
            border-left: 3px solid #00ff00;
            background-color: #0a0a0a;
        }}
        .file-info {{
            background-color: #111;
            padding: 10px;
            border-radius: 5px;
        }}
        .analysis {{
            white-space: pre-wrap;
            font-size: 12px;
        }}
        .timestamp {{
            color: #888;
            font-size: 10px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🕵️ EXIF Inspector</h1>
        <h2>Детективный отчет</h2>
    </div>
    
    <div class="section">
        <h3>📁 Информация о файле</h3>
        <div class="file-info">
            <p><strong>Файл:</strong> {os.path.basename(file_path)}</p>
            <p><strong>Полный путь:</strong> {file_path}</p>
            <p class="timestamp">Дата анализа: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')}</p>
        </div>
    </div>
    
    <div class="section">
        <h3>🔍 Детективный анализ</h3>
        <div class="analysis">{analysis_text}</div>
    </div>
    
    <div class="section">
        <h3>📊 Сравнительный анализ</h3>
        <div class="analysis">{self.comparative_analysis()}</div>
    </div>
</body>
</html>
            """
            
            # Сохраняем HTML
            html_file = file_path.rsplit('.', 1)[0] + '_exif_report.html'
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            return html_file
        except Exception as e:
            self.app.log_message(f"❌ Ошибка создания HTML: {e}")
            return None

    def export_for_law_enforcement(self, exif_data, file_path):
        """Структурированный экспорт для правоохранительных органов"""
        try:
            # Собираем критически важные данные
            evidence = {
                'case_info': {
                    'file_name': os.path.basename(file_path),
                    'full_path': file_path,
                    'analysis_date': datetime.datetime.now().isoformat(),
                    'analyst': 'EXIF Inspector v2.0'
                },
                'device_info': {
                    'make': self.find_exif_value(exif_data, ":Make"),
                    'model': self.find_exif_value(exif_data, ":Model"),
                    'serial_number': self.find_exif_value(exif_data, ":CameraSerialNumber"),
                    'firmware': self.find_exif_value(exif_data, ":FirmwareVersion"),
                    'software': self.find_exif_value(exif_data, ":Software")
                },
                'temporal_evidence': {
                    'creation_date': self.find_exif_value(exif_data, ":DateTimeOriginal"),
                    'file_creation': self.find_exif_value(exif_data, ":CreateDate"),
                    'modification_date': self.find_exif_value(exif_data, ":ModifyDate")
                },
                'geolocation': {
                    'latitude': self.find_exif_value(exif_data, ":GPSLatitude"),
                    'longitude': self.find_exif_value(exif_data, ":GPSLongitude"),
                    'altitude': self.find_exif_value(exif_data, ":GPSAltitude"),
                    'gps_accuracy': self.find_exif_value(exif_data, ":GPSDOP")
                },
                'technical_parameters': {
                    'iso': self.find_exif_value(exif_data, ":ISO"),
                    'aperture': self.find_exif_value(exif_data, ":FNumber"),
                    'shutter_speed': self.find_exif_value(exif_data, ":ExposureTime"),
                    'focal_length': self.find_exif_value(exif_data, ":FocalLength"),
                    'flash': self.find_exif_value(exif_data, ":Flash")
                },
                'unique_identifiers': {
                    'image_unique_id': self.find_exif_value(exif_data, ":ImageUniqueID"),
                    'exif_unique_id': self.find_exif_value(exif_data, ":ExifImageUniqueID"),
                    'lens_serial': self.find_exif_value(exif_data, ":LensSerialNumber")
                },
                'integrity_checks': {
                    'file_size': self.find_exif_value(exif_data, ":FileSize"),
                    'image_dimensions': f"{self.find_exif_value(exif_data, ':ImageWidth')}x{self.find_exif_value(exif_data, ':ImageHeight')}",
                    'compression': self.find_exif_value(exif_data, ":Compression"),
                    'color_space': self.find_exif_value(exif_data, ":ColorSpace")
                }
            }
            
            # Сохраняем в JSON
            json_file = file_path.rsplit('.', 1)[0] + '_law_enforcement_evidence.json'
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(evidence, f, ensure_ascii=False, indent=2)
            
            return json_file
        except Exception as e:
            self.app.log_message(f"❌ Ошибка создания экспорта для правоохранительных органов: {e}")
            return None

    def get_weather_analysis(self, lat, lon, date_time):
        """Анализ погодных условий в момент съемки"""
        try:
            import requests
            # Используем OpenWeatherMap API (требует API ключ)
            # Для демонстрации возвращаем примерные данные
            weather_data = {
                'temperature': '22°C',
                'conditions': 'Ясно',
                'humidity': '65%',
                'wind_speed': '5 км/ч'
            }
            return weather_data
        except:
            return None

    def analyze_shooting_conditions(self, exif_data):
        """Анализ условий съемки"""
        out = []
        out.append("🌤️ АНАЛИЗ УСЛОВИЙ СЪЕМКИ")
        out.append("-" * 60)
        
        # Анализ времени суток и сезона
        time_original = self.find_exif_value(exif_data, ":DateTimeOriginal")
        if time_original:
            try:
                dt = datetime.datetime.strptime(str(time_original).replace(":", "-", 2), "%Y-%m-%d %H-%M-%S")
                hour = dt.hour
                month = dt.month
                
                # Время суток
                if 5 <= hour < 12:
                    time_of_day = "🌅 Утро - мягкий свет"
                elif 12 <= hour < 17:
                    time_of_day = "☀️ День - яркий свет"
                elif 17 <= hour < 20:
                    time_of_day = "🌆 Вечер - золотой час"
                else:
                    time_of_day = "🌙 Ночь - искусственное освещение"
                
                # Сезон
                if month in [12, 1, 2]:
                    season = "❄️ Зима - короткие дни, холодный свет"
                elif month in [3, 4, 5]:
                    season = "🌸 Весна - мягкий свет, переменная погода"
                elif month in [6, 7, 8]:
                    season = "☀️ Лето - длинные дни, яркий свет"
                else:
                    season = "🍂 Осень - теплые тона, мягкий свет"
                
                out.append(f"• Время съемки: {time_of_day}")
                out.append(f"• Сезон: {season}")
                
            except:
                pass
        
        # Анализ технических параметров для определения условий
        iso = self.find_exif_value(exif_data, ":ISO")
        fnum = self.find_exif_value(exif_data, ":FNumber")
        exposure = self.find_exif_value(exif_data, ":ExposureTime")
        flash = self.find_exif_value(exif_data, ":Flash")
        
        conditions = []
        
        if iso:
            try:
                iso_val = float(iso)
                if iso_val >= 1600:
                    conditions.append("🌙 Съемка в условиях низкой освещенности")
                elif iso_val <= 200:
                    conditions.append("☀️ Съемка при хорошем освещении")
            except:
                pass
        
        if fnum:
            try:
                fnum_val = float(fnum)
                if fnum_val <= 2.8:
                    conditions.append("🌟 Использована широкая диафрагма для размытия фона")
                elif fnum_val >= 8:
                    conditions.append("🔍 Использована узкая диафрагма для большой глубины резкости")
            except:
                pass
        
        if exposure:
            try:
                if "/" in str(exposure):
                    exp_val = 1.0 / float(exposure.split("/")[1])
                else:
                    exp_val = float(exposure)
                
                if exp_val >= 1.0:
                    conditions.append("🌅 Длинная выдержка - возможно, съемка на штативе")
                elif exp_val <= 1/500:
                    conditions.append("⚡ Очень короткая выдержка - съемка быстрого движения")
            except:
                pass
        
        if flash:
            if flash == "0" or flash == 0:
                conditions.append("💡 Вспышка не использовалась")
            else:
                conditions.append("⚡ Вспышка использовалась")
        
        if conditions:
            out.append("• Условия съемки:")
            for condition in conditions:
                out.append(f"  {condition}")
        
        return "\n".join(out) if len(out) > 2 else None

    def analyze_photographer_style(self, exif_data):
        """Анализ стиля фотографа"""
        out = []
        out.append("🎨 АНАЛИЗ СТИЛЯ ФОТОГРАФА")
        out.append("-" * 60)
        
        # Анализ предпочтений в настройках
        iso = self.find_exif_value(exif_data, ":ISO")
        fnum = self.find_exif_value(exif_data, ":FNumber")
        exposure = self.find_exif_value(exif_data, ":ExposureTime")
        focal = self.find_exif_value(exif_data, ":FocalLength")
        
        style_indicators = []
        
        # Анализ предпочтений по ISO
        if iso:
            try:
                iso_val = float(iso)
                if iso_val <= 100:
                    style_indicators.append("🎯 Перфекционист - предпочитает низкое ISO")
                elif iso_val >= 1600:
                    style_indicators.append("🌙 Экспериментатор - не боится высокого ISO")
            except:
                pass
        
        # Анализ предпочтений по диафрагме
        if fnum:
            try:
                fnum_val = float(fnum)
                if fnum_val <= 2.8:
                    style_indicators.append("🌟 Любитель размытого фона")
                elif fnum_val >= 8:
                    style_indicators.append("🔍 Деталист - предпочитает четкость")
            except:
                pass
        
        # Анализ предпочтений по выдержке
        if exposure:
            try:
                if "/" in str(exposure):
                    exp_val = 1.0 / float(exposure.split("/")[1])
                else:
                    exp_val = float(exposure)
                
                if exp_val >= 1.0:
                    style_indicators.append("🌅 Любитель длинных выдержек")
                elif exp_val <= 1/500:
                    style_indicators.append("⚡ Фотограф быстрого движения")
            except:
                pass
        
        # Анализ фокусного расстояния
        if focal:
            try:
                focal_val = float(focal)
                if focal_val <= 35:
                    style_indicators.append("📐 Широкоугольный фотограф")
                elif focal_val >= 85:
                    style_indicators.append("🔭 Телефотограф")
                else:
                    style_indicators.append("📷 Универсальный фотограф")
            except:
                pass
        
        if style_indicators:
            out.append("• Стилистические предпочтения:")
            for indicator in style_indicators:
                out.append(f"  {indicator}")
        
        # Анализ типа съемки
        scene_capture = self.find_exif_value(exif_data, ":SceneCaptureType")
        if scene_capture:
            if scene_capture == "0" or scene_capture == 0:
                style_indicators.append("📷 Автоматический режим")
            elif scene_capture == "1" or scene_capture == 1:
                style_indicators.append("🏞️ Пейзажный фотограф")
            elif scene_capture == "2" or scene_capture == 2:
                style_indicators.append("👤 Портретный фотограф")
            elif scene_capture == "3" or scene_capture == 3:
                style_indicators.append("🌙 Ночной фотограф")
        
        return "\n".join(out) if len(out) > 2 else None

    def detect_photo_manipulation(self, exif_data):
        """Детекция манипуляций с фотографией"""
        out = []
        out.append("🔍 ДЕТЕКЦИЯ МАНИПУЛЯЦИЙ")
        out.append("-" * 60)
        
        manipulation_indicators = []
        
        # Проверка временных меток
        time_original = self.find_exif_value(exif_data, ":DateTimeOriginal")
        create_date = self.find_exif_value(exif_data, ":CreateDate")
        modify_date = self.find_exif_value(exif_data, ":ModifyDate")
        
        if time_original and modify_date:
            try:
                time_orig = datetime.datetime.strptime(str(time_original).replace(":", "-", 2), "%Y-%m-%d %H-%M-%S")
                time_modify = datetime.datetime.strptime(str(modify_date).replace(":", "-", 2), "%Y-%m-%d %H-%M-%S")
                if time_modify > time_orig:
                    diff_hours = (time_modify - time_orig).total_seconds() / 3600
                    if diff_hours > 24:
                        manipulation_indicators.append(f"⏰ Файл изменен через {diff_hours:.1f} часов после съемки")
            except:
                pass
        
        # Проверка на использование редакторов
        software = self.find_exif_value(exif_data, ":Software")
        creator_tool = self.find_exif_value(exif_data, ":CreatorTool")
        
        editors_used = []
        if software:
            software_lower = str(software).lower()
            if any(editor in software_lower for editor in ['photoshop', 'gimp', 'lightroom', 'snapseed']):
                editors_used.append(software)
        
        if creator_tool:
            creator_lower = str(creator_tool).lower()
            if any(editor in creator_lower for editor in ['photoshop', 'gimp', 'lightroom', 'snapseed']):
                editors_used.append(creator_tool)
        
        if editors_used:
            manipulation_indicators.append(f"🎨 Использованы редакторы: {', '.join(set(editors_used))}")
        
        # Проверка на подозрительные значения
        camera_sn = self.find_exif_value(exif_data, ":CameraSerialNumber")
        if camera_sn:
            sn_str = str(camera_sn).lower()
            if any(pattern in sn_str for pattern in ['000000', '123456', 'test', 'unknown']):
                manipulation_indicators.append("🔍 Подозрительный серийный номер камеры")
        
        # Проверка на отсутствие критических полей
        critical_fields = [":Make", ":Model", ":DateTimeOriginal"]
        missing_critical = []
        for field in critical_fields:
            if not self.find_exif_value(exif_data, field):
                missing_critical.append(field.replace(":", ""))
        
        if missing_critical:
            manipulation_indicators.append(f"📋 Отсутствуют критические поля: {', '.join(missing_critical)}")
        
        # Проверка на несоответствие размеров
        img_width = self.find_exif_value(exif_data, ":ImageWidth")
        img_height = self.find_exif_value(exif_data, ":ImageHeight")
        exif_width = self.find_exif_value(exif_data, ":ExifImageWidth")
        exif_height = self.find_exif_value(exif_data, ":ExifImageHeight")
        
        if img_width and exif_width and img_width != exif_width:
            manipulation_indicators.append("📐 Несоответствие размеров в разных полях EXIF")
        
        if manipulation_indicators:
            out.append("• Признаки возможных манипуляций:")
            for indicator in manipulation_indicators:
                out.append(f"  {indicator}")
        else:
            out.append("✅ Признаков манипуляций не обнаружено")
        
        return "\n".join(out) if len(out) > 2 else None

    def _analyze_mobile_features(self, exif_data):
        """Анализ мобильных функций и приложений"""
        out = []
        out.append("📱 МОБИЛЬНЫЙ АНАЛИЗ")
        out.append("-" * 60)
        
        # Анализ приложений-источников
        software = self.find_exif_value(exif_data, ":Software")
        creator_tool = self.find_exif_value(exif_data, ":CreatorTool")
        app_analysis = []
        
        if software:
            software_lower = str(software).lower()
            if any(app in software_lower for app in ['instagram', 'ig']):
                app_analysis.append("📸 Instagram - социальная сеть")
            elif any(app in software_lower for app in ['whatsapp', 'wa']):
                app_analysis.append("💬 WhatsApp - мессенджер")
            elif any(app in software_lower for app in ['telegram', 'tg']):
                app_analysis.append("✈️ Telegram - мессенджер")
            elif any(app in software_lower for app in ['tiktok', 'douyin']):
                app_analysis.append("🎵 TikTok - короткие видео")
            elif any(app in software_lower for app in ['snapchat', 'snap']):
                app_analysis.append("👻 Snapchat - исчезающие фото")
            elif any(app in software_lower for app in ['camera', 'камера']):
                app_analysis.append("📷 Стандартное приложение камеры")
            else:
                app_analysis.append(f"🔧 Неизвестное приложение: {software}")
        
        if creator_tool:
            creator_lower = str(creator_tool).lower()
            if any(tool in creator_lower for tool in ['photoshop', 'ps']):
                app_analysis.append("🎨 Adobe Photoshop - профессиональный редактор")
            elif any(tool in creator_lower for tool in ['lightroom', 'lr']):
                app_analysis.append("🌅 Adobe Lightroom - обработка RAW")
            elif any(tool in creator_lower for tool in ['snapseed']):
                app_analysis.append("📱 Google Snapseed - мобильный редактор")
            elif any(tool in creator_lower for tool in ['gimp']):
                app_analysis.append("🆓 GIMP - бесплатный редактор")
        
        if app_analysis:
            out.append("• Приложения и инструменты:")
            for app in app_analysis:
                out.append(f"  {app}")
        
        # Анализ мобильных режимов съемки
        scene_capture = self.find_exif_value(exif_data, ":SceneCaptureType")
        custom_rendered = self.find_exif_value(exif_data, ":CustomRendered")
        hdr = self.find_exif_value(exif_data, ":HDR")
        
        mobile_modes = []
        if scene_capture:
            if scene_capture == "0" or scene_capture == 0:
                mobile_modes.append("📷 Стандартный режим")
            elif scene_capture == "1" or scene_capture == 1:
                mobile_modes.append("🏞️ Пейзажный режим")
            elif scene_capture == "2" or scene_capture == 2:
                mobile_modes.append("👤 Портретный режим")
            elif scene_capture == "3" or scene_capture == 3:
                mobile_modes.append("🌙 Ночной режим")
        
        if custom_rendered:
            mobile_modes.append("🤖 AI-улучшения включены")
        
        if hdr:
            mobile_modes.append("☀️ HDR режим активен")
        
        # Анализ цифрового зума
        digital_zoom = self.find_exif_value(exif_data, ":DigitalZoomRatio")
        if digital_zoom and digital_zoom != "1" and digital_zoom != 1:
            try:
                zoom_val = float(digital_zoom)
                if zoom_val > 2.0:
                    mobile_modes.append(f"🔍 Цифровой зум {digital_zoom}x (возможна потеря качества)")
                else:
                    mobile_modes.append(f"🔍 Цифровой зум {digital_zoom}x")
            except:
                mobile_modes.append(f"🔍 Цифровой зум {digital_zoom}x")
        
        if mobile_modes:
            out.append("• Режимы съемки:")
            for mode in mobile_modes:
                out.append(f"  {mode}")
        
        # Анализ качества мобильной съемки
        iso = self.find_exif_value(exif_data, ":ISO")
        if iso:
            try:
                iso_val = float(iso)
                if iso_val >= 3200:
                    out.append("⚠️ Высокое ISO - возможен шум на мобильном устройстве")
                elif iso_val <= 100:
                    out.append("✅ Низкое ISO - хорошее качество для мобильного")
            except:
                pass
        
        return "\n".join(out) if len(out) > 2 else None

    def _forensic_analysis(self, exif_data):
        """Криминалистический анализ целостности файла"""
        out = []
        out.append("🕵️ КРИМИНАЛИСТИЧЕСКИЙ АНАЛИЗ")
        out.append("-" * 60)
        
        # Проверка целостности временных меток
        time_original = self.find_exif_value(exif_data, ":DateTimeOriginal")
        create_date = self.find_exif_value(exif_data, ":CreateDate")
        modify_date = self.find_exif_value(exif_data, ":ModifyDate")
        
        integrity_issues = []
        
        if time_original and create_date:
            try:
                time_orig = datetime.datetime.strptime(str(time_original).replace(":", "-", 2), "%Y-%m-%d %H-%M-%S")
                time_create = datetime.datetime.strptime(str(create_date).replace(":", "-", 2), "%Y-%m-%d %H-%M-%S")
                if abs((time_orig - time_create).total_seconds()) > 300:  # 5 минут
                    integrity_issues.append("⏰ Большая разница между временем съемки и создания файла")
            except:
                pass
        
        if time_original and modify_date:
            try:
                time_orig = datetime.datetime.strptime(str(time_original).replace(":", "-", 2), "%Y-%m-%d %H-%M-%S")
                time_modify = datetime.datetime.strptime(str(modify_date).replace(":", "-", 2), "%Y-%m-%d %H-%M-%S")
                if time_modify < time_orig:
                    integrity_issues.append("⚠️ Время изменения раньше времени съемки - подозрительно!")
                elif abs((time_modify - time_orig).total_seconds()) > 3600:  # 1 час
                    integrity_issues.append("📝 Файл был изменен после съемки")
            except:
                pass
        
        # Проверка на будущие даты
        if time_original:
            try:
                time_orig = datetime.datetime.strptime(str(time_original).replace(":", "-", 2), "%Y-%m-%d %H-%M-%S")
                now = datetime.datetime.now()
                if time_orig > now:
                    integrity_issues.append("🚨 Время съемки в будущем - возможно подделка!")
            except:
                pass
        
        # Проверка серийных номеров на подозрительные значения
        camera_sn = self.find_exif_value(exif_data, ":CameraSerialNumber")
        if camera_sn:
            sn_str = str(camera_sn).lower()
            suspicious_patterns = ["000000", "123456", "111111", "999999", "none", "null", "test", "unknown"]
            if any(pattern in sn_str for pattern in suspicious_patterns):
                integrity_issues.append("🔍 Подозрительный серийный номер камеры")
        
        # Проверка на отсутствие критических метаданных
        critical_fields = [":Make", ":Model", ":DateTimeOriginal"]
        missing_fields = []
        for field in critical_fields:
            if not self.find_exif_value(exif_data, field):
                missing_fields.append(field.replace(":", ""))
        
        if missing_fields:
            integrity_issues.append(f"📋 Отсутствуют критические поля: {', '.join(missing_fields)}")
        
        # Анализ размера файла на подозрительность
        file_size = self.find_exif_value(exif_data, ":FileSize")
        if file_size:
            try:
                size_mb = float(file_size) / (1024 * 1024)
                if size_mb < 0.1:
                    integrity_issues.append("📏 Подозрительно маленький размер файла")
                elif size_mb > 50:
                    integrity_issues.append("📏 Очень большой размер файла - возможно RAW или HDR")
            except:
                pass
        
        if integrity_issues:
            out.append("• Проблемы целостности:")
            for issue in integrity_issues:
                out.append(f"  {issue}")
        else:
            out.append("✅ Файл выглядит подлинным - серьезных проблем не обнаружено")
        
        return "\n".join(out) if len(out) > 2 else None

    def _content_quality_analysis(self, exif_data):
        """Анализ содержимого и качества изображения"""
        out = []
        out.append("🎨 АНАЛИЗ СОДЕРЖИМОГО И КАЧЕСТВА")
        out.append("-" * 60)
        
        # Анализ цветовых характеристик
        colorspace = self.find_exif_value(exif_data, ":ColorSpace")
        color_profile = self.find_exif_value(exif_data, ":ColorProfile")
        
        color_analysis = []
        if colorspace:
            if colorspace == "1" or colorspace == 1:
                color_analysis.append("🌈 sRGB - стандартное цветовое пространство")
            elif colorspace == "65535" or colorspace == 65535:
                color_analysis.append("🎨 Некалиброванное цветовое пространство")
            else:
                color_analysis.append(f"🎨 Цветовое пространство: {colorspace}")
        
        if color_profile:
            color_analysis.append(f"📋 Цветовой профиль: {color_profile}")
        
        # Анализ качества сжатия
        compression = self.find_exif_value(exif_data, ":Compression")
        if compression:
            if compression == "6" or compression == 6:
                color_analysis.append("📦 JPEG сжатие - стандартное")
            elif compression == "1" or compression == 1:
                color_analysis.append("📦 Без сжатия - высокое качество")
            else:
                color_analysis.append(f"📦 Тип сжатия: {compression}")
        
        # Анализ разрешения
        x_res = self.find_exif_value(exif_data, ":XResolution")
        y_res = self.find_exif_value(exif_data, ":YResolution")
        if x_res and y_res:
            try:
                dpi = float(x_res)
                if dpi >= 300:
                    color_analysis.append(f"🖨️ Высокое разрешение для печати: {dpi} DPI")
                elif dpi >= 150:
                    color_analysis.append(f"📱 Среднее разрешение: {dpi} DPI")
                else:
                    color_analysis.append(f"💻 Низкое разрешение: {dpi} DPI")
            except:
                pass
        
        if color_analysis:
            out.append("• Цветовые характеристики:")
            for analysis in color_analysis:
                out.append(f"  {analysis}")
        
        # Анализ технических параметров качества
        iso = self.find_exif_value(exif_data, ":ISO")
        fnum = self.find_exif_value(exif_data, ":FNumber")
        exposure = self.find_exif_value(exif_data, ":ExposureTime")
        
        quality_indicators = []
        
        if iso:
            try:
                iso_val = float(iso)
                if iso_val <= 100:
                    quality_indicators.append("⭐ Отличное качество - низкое ISO")
                elif iso_val <= 400:
                    quality_indicators.append("✅ Хорошее качество - умеренное ISO")
                elif iso_val <= 1600:
                    quality_indicators.append("⚠️ Среднее качество - высокое ISO")
                else:
                    quality_indicators.append("❌ Плохое качество - очень высокое ISO")
            except:
                pass
        
        if fnum:
            try:
                fnum_val = float(fnum)
                if fnum_val <= 2.8:
                    quality_indicators.append("🌟 Светосильный объектив")
                elif fnum_val <= 5.6:
                    quality_indicators.append("📸 Стандартная светосила")
                else:
                    quality_indicators.append("🔍 Темный объектив")
            except:
                pass
        
        if exposure:
            try:
                if "/" in str(exposure):
                    exp_val = 1.0 / float(exposure.split("/")[1])
                else:
                    exp_val = float(exposure)
                
                if exp_val >= 1.0:
                    quality_indicators.append("🌅 Длинная выдержка - возможны размытия")
                elif exp_val >= 1/60:
                    quality_indicators.append("📷 Стандартная выдержка")
                else:
                    quality_indicators.append("⚡ Короткая выдержка - четкое изображение")
            except:
                pass
        
        if quality_indicators:
            out.append("• Показатели качества:")
            for indicator in quality_indicators:
                out.append(f"  {indicator}")
        
        # Анализ размера изображения
        width = self.find_exif_value(exif_data, ":ImageWidth")
        height = self.find_exif_value(exif_data, ":ImageHeight")
        if width and height:
            try:
                megapixels = (float(width) * float(height)) / 1000000
                if megapixels >= 20:
                    out.append(f"📱 Высокое разрешение: {megapixels:.1f} МП")
                elif megapixels >= 10:
                    out.append(f"📱 Среднее разрешение: {megapixels:.1f} МП")
                else:
                    out.append(f"📱 Низкое разрешение: {megapixels:.1f} МП")
            except:
                pass
        
        return "\n".join(out) if len(out) > 2 else None

    def _network_biometric_analysis(self, exif_data):
        """Сетевой и биометрический анализ"""
        out = []
        out.append("🌐 СЕТЕВОЙ И БИОМЕТРИЧЕСКИЙ АНАЛИЗ")
        out.append("-" * 60)
        
        # Анализ уникальных идентификаторов
        image_uid = self.find_exif_value(exif_data, ":ImageUniqueID")
        exif_uid = self.find_exif_value(exif_data, ":ExifImageUniqueID")
        camera_sn = self.find_exif_value(exif_data, ":CameraSerialNumber")
        lens_sn = self.find_exif_value(exif_data, ":LensSerialNumber")
        
        identifiers = []
        if image_uid:
            identifiers.append(f"🆔 ImageUniqueID: {image_uid}")
        if exif_uid:
            identifiers.append(f"🆔 ExifImageUniqueID: {exif_uid}")
        if camera_sn:
            identifiers.append(f"📷 Серийный номер камеры: {camera_sn}")
        if lens_sn:
            identifiers.append(f"🔭 Серийный номер объектива: {lens_sn}")
        
        if identifiers:
            out.append("• Уникальные идентификаторы:")
            for identifier in identifiers:
                out.append(f"  {identifier}")
        
        # Анализ сетевых данных (если доступны)
        software = self.find_exif_value(exif_data, ":Software")
        if software:
            software_lower = str(software).lower()
            if any(cloud in software_lower for cloud in ['icloud', 'google', 'dropbox', 'onedrive']):
                out.append("☁️ Возможная синхронизация с облачным сервисом")
        
        # Анализ биометрических данных (если доступны)
        # В реальных EXIF данных биометрические данные обычно не хранятся
        # но можно проверить на наличие подозрительных полей
        
        # Проверка на стеганографию
        user_comment = self.find_exif_value(exif_data, ":UserComment")
        if user_comment:
            comment_lower = str(user_comment).lower()
            steganography_indicators = ['steg', 'hidden', 'secret', 'encrypt', 'password']
            if any(indicator in comment_lower for indicator in steganography_indicators):
                out.append("🔍 Возможна стеганография - подозрительный комментарий")
        
        # Анализ метаданных на скрытые данные
        all_fields = list(exif_data.keys())
        suspicious_fields = [field for field in all_fields if any(sus in field.lower() for sus in ['private', 'custom', 'user', 'hidden'])]
        
        if suspicious_fields:
            out.append("🔍 Обнаружены пользовательские поля:")
            for field in suspicious_fields[:5]:  # Показываем только первые 5
                out.append(f"  • {field}")
        
        # Анализ целостности файла
        file_size = self.find_exif_value(exif_data, ":FileSize")
        if file_size:
            try:
                size_mb = float(file_size) / (1024 * 1024)
                if size_mb > 100:
                    out.append("📊 Очень большой файл - возможно содержит дополнительные данные")
            except:
                pass
        
        return "\n".join(out) if len(out) > 2 else None