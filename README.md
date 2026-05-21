<p align="center">
  <img src="docs/banner.png" alt="GeoHunter — ERRORoX" width="100%">
</p>

```text
 ██████╗ ███████╗ ██████╗ ██╗  ██╗██╗   ██╗███╗   ██╗████████╗███████╗██████╗
██╔════╝ ██╔════╝██╔═══██╗██║  ██║██║   ██║████╗  ██║╚══██╔══╝██╔════╝██╔══██╗
██║  ███╗█████╗  ██║   ██║███████║██║   ██║██╔██╗ ██║   ██║   █████╗  ██████╔╝
██║   ██║██╔══╝  ██║   ██║██╔══██║██║   ██║██║╚██╗██║   ██║   ██╔══╝  ██╔══██╗
╚██████╔╝███████╗╚██████╔╝██║  ██║╚██████╔╝██║ ╚████║   ██║   ███████╗██║  ██║
 ╚═════╝ ╚══════╝ ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝   ╚═╝   ╚══════╝╚═╝  ╚═╝
     [ ЛОКАЛЬНЫЙ ФОТО-OSINT УЗЕЛ ] :: EXIF // ГЕО // КРИМИНАЛИСТИКА // РАЗВЕДКА
```

<h1 align="center">GeoHunter</h1>

<p align="center">
  <strong>Локальный фреймворк разбора изображений</strong><br>
  метаданные · геопривязка · криминалистика · текст · коды · обратный и веб-поиск
</p>

<p align="center">
  <a href="https://www.instagram.com/_specter_X/"><img src="https://img.shields.io/badge/Instagram-_specter_X-E4405F?style=for-the-badge&logo=instagram&logoColor=white" alt="Instagram @_specter_X"></a>
  <img src="https://img.shields.io/badge/автор-ERRORoX-00ff88?style=for-the-badge&labelColor=0a0e14" alt="ERRORoX">
  <img src="https://img.shields.io/badge/стек-Flask%20%7C%20MapLibre%20%7C%20ExifTool-111827?style=for-the-badge&color=00ff88" alt="стек">
  <img src="https://img.shields.io/badge/лицензия-MIT-00ff88?style=for-the-badge&labelColor=0a0e14" alt="MIT">
</p>

---

## /// БРИФИНГ

**GeoHunter** — мой рабочий стенд под фото-OSINT: один снимок → метаданные, координаты, карта, следы монтажа, шум, тени, LSB, лица, OCR, QR и ссылки на обратный поиск.  
Всё крутится **на вашем хосте** (Flask). Файл в облако для «магического анализа» не уходит.

```bash
# после run.py
http://127.0.0.1:5050/photo/
```

> **Операционная безопасность:** геокод отправляет координаты на Nominatim; карта подгружает тайлы из сети. Учитывайте это в чувствительных расследованиях.

---

## /// ВИЗУАЛ · ПОЛЕВОЙ ОТЧЁТ

<p align="center"><b>01 — EXIF / GPS / КАРТА</b> · точка, адрес, предупреждение о геотеге</p>

<p align="center">
  <img src="docs/screenshots/01-exif-gps-map.png" alt="EXIF, GPS и карта" width="48%">
  <img src="docs/screenshots/02-map-detail.png" alt="Детализация карты" width="48%">
</p>

<p align="center"><b>02 — ПАНЕЛЬ МЕТАДАННЫХ</b> · адрес, солнце, камера, хэши</p>

<p align="center">
  <img src="docs/screenshots/03-metadata.png" alt="Панель метаданных" width="78%">
</p>

<p align="center"><b>03 — КРИМИНАЛИСТИКА</b> · ELA · шум · тени · LSB</p>

<p align="center">
  <img src="docs/screenshots/04-forensics.png" alt="Криминалистика" width="78%">
</p>

---

## /// РЕЕСТР МОДУЛЕЙ

| Модуль | Назначение | Стек |
|--------|------------|------|
| `EXIF` | GPS, WGS84, геокод, карта, ExifTool, ссылки на карты | exiftool, Nominatim, MapLibre |
| `ELA` | анализ уровня ошибок — зоны пересохранения и ретуши | Pillow |
| `ШУМ` | карта шума, неоднородность по кадру | NumPy, SciPy |
| `ТЕНИ` | азимут солнца, оценка широты по тени и времени из EXIF | Astral |
| `LSB` | младшие биты, признаки стеганографии | Pillow |
| `ЛИЦА` | детекция лиц | OpenCV |
| `OCR` | текст, email, телефоны, URL | Tesseract rus+eng |
| `QR` | QR и штрихкоды | pyzbar |
| `ОБРАТНЫЙ` | Lens, Яндекс, Bing, TinEye — ручная проверка | браузер |
| `ПОИСК` | готовые запросы из EXIF и OCR | браузер |

**Дополнительно:** экспорт MD/JSON · JPEG без EXIF · полный дамп тегов ExifTool.

---

## /// РАЗВЁРТЫВАНИЕ · ЛОКАЛЬНЫЙ УЗЕЛ

**Требования:** Python 3.10+ · Linux / macOS / WSL

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip \
  exiftool tesseract-ocr tesseract-ocr-rus tesseract-ocr-eng \
  libzbar0 libgl1
```

```bash
git clone <url> GeoHunter && cd GeoHunter
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python3 run.py
```

Проверка утилит:

```bash
exiftool -ver && tesseract --version
```

Если `python3` не системный:

```bash
/usr/bin/python3.13 run.py
```

Конфиг: `.env` ← `.env.example` (`PORT`, `MAX_UPLOAD_MB`, `SECRET_KEY`, …).

---

## /// РАБОЧИЙ ЦИКЛ ОПЕРАТОРА

1. **ЗАГРУЗКА** — файл или URL в `/photo/`.
2. **ЗАПУСК** — параллельный прогон всех модулей.
3. **РАЗБОР** — EXIF (карта и адрес), криминалистика, OCR/QR, ссылки на поиск.
4. **ЭКСПОРТ** — MD/JSON из шапки после прогона.
5. **ОЧИСТКА** — «Удалить метаданные» → копия JPEG без EXIF.

**Заметки по полю:**

- GPS часто вырезают мессенджеры — нужен **оригинал с камеры**.
- Белая карта → нет сети или блок CDN MapLibre / OpenFreeMap.
- Ошибка 413 → увеличить `MAX_UPLOAD_MB`.

---

## /// API · БЕЗ ИНТЕРФЕЙСА

`POST` · JSON · поле `imageBase64`

```
/api/exif              — метаданные, GPS, геокод
/api/exif/strip        — JPEG без EXIF
/api/exif/exiftool/json
/api/forensics/ela | noise | stego | faces | shadow-solve
/api/ocr | /api/qr-barcode
/api/reverse-search | /api/search
/api/export-report | /api/export-json
```

```bash
curl -s -X POST http://127.0.0.1:5050/api/exif \
  -H "Content-Type: application/json" \
  -d "{\"imageBase64\":\"$(base64 -w0 photo.jpg)\",\"exiftool\":true,\"geocode\":true}"
```

Полный список настроек: `backend/config.py`.

---

## /// СТРУКТУРА ПРОЕКТА

```
run.py
backend/           — маршруты, сервисы, инструменты
static/photo/      — веб-интерфейс
tools/exif_inspector/
docs/              — баннер и скриншоты
LICENSE            — MIT © ERRORoX
```

Новый модуль: `backend/tools/` → `registry.py` → `routes.py` → `tools-config.js`.

---

## /// СБОИ И РЕШЕНИЯ

| Симптом | Решение |
|---------|---------|
| нет exiftool | `apt install libimage-exiftool-perl` |
| пустой OCR | `tesseract-ocr-rus` |
| QR не читается | `libzbar0` |
| модуль «Лица» недоступен | `pip install opencv-python-headless` |
| белая карта | F12 → сеть; проверить openfreemap и unpkg |
| нет точки на карте | в EXIF нет координат |

При старте сервер пишет в лог, чего не хватает (`env_check.py`).

---

## /// ОПЕРАТОР

<table>
  <tr>
    <td><b>Позывной</b></td>
    <td><b>ERRORoX</b></td>
  </tr>
  <tr>
    <td><b>Связь</b></td>
    <td>
      <a href="https://www.instagram.com/_specter_X/">Instagram @_specter_X</a>
    </td>
  </tr>
  <tr>
    <td><b>Роль</b></td>
    <td>автор · сопровождение · GeoHunter</td>
  </tr>
</table>

Баги и идеи — issues в репозитории или личные сообщения. В отчёте укажите: ОС, `python3 --version`, `exiftool -ver`, текст ошибки из терминала и консоли браузера (F12).

---

## /// ПРАВО И ОТВЕТСТВЕННОСТЬ

## Лицензия / License

🌐 **English:** 
This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

🇷🇺 **Русский:**
Этот проект распространяется под лицензией GNU General Public License v3.0. Вы можете свободно использовать, изучать и модифицировать софт, при условии, что измененные версии также останутся открытыми (Open Source). Подробности в файле [LICENSE](LICENSE).

Анализируйте только те материалы, на которые у вас есть право. Не выставляйте сервер в открытый интернет без авторизации, HTTPS и смены `SECRET_KEY`. Вывод модулей — **гипотеза для проверки**, не готовый вердикт.

```text
[ КОНЕЦ ] :: на связи :: ERRORoX :: @_specter_X
```
