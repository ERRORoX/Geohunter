<p align="center">
  <img src="docs/banner.svg" alt="GeoHunter — ERRORoX" width="100%">
</p>

<h1 align="center">GeoHunter</h1>

<p align="center">
  <strong>Локальный разбор фотографий для OSINT</strong><br>
  EXIF, GPS, карта, криминалистика, OCR, QR, обратный поиск
</p>

<p align="center">
  <img src="https://img.shields.io/badge/author-ERRORoX-00ff88?style=for-the-badge&labelColor=0a0e14" alt="ERRORoX">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Flask-3.x-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask">
  <img src="https://img.shields.io/badge/license-MIT-00ff88?style=for-the-badge&labelColor=0a0e14" alt="MIT">
</p>

---

**GeoHunter** — веб-приложение, которое я собрал под свои задачи по разбору снимков: вытащить метаданные, показать точку на карте, прогнать ELA/шум/тени, вытащить текст и QR, собрать ссылки на обратный поиск. Всё крутится у вас на машине через Flask, без отправки файла в чужой «облачный анализ».

После запуска интерфейс: **http://127.0.0.1:5050/photo/**

## Скриншоты

| EXIF, GPS и карта | Детализация карты |
|:---:|:---:|
| ![EXIF и карта](docs/screenshots/01-exif-gps-map.png) | ![Карта](docs/screenshots/02-map-detail.png) |
| *координаты, адрес, MapLibre, предупреждение о GPS* | *3D-вид, маркер, OpenFreeMap* |

| Метаданные и геоданные | Криминалистика |
|:---:|:---:|
| ![Метаданные](docs/screenshots/03-metadata.png) | ![Криминалистика](docs/screenshots/04-forensics.png) |
| *адрес, солнце, камера, хэши* | *ELA, шум, тени, LSB* |

## Возможности

- **EXIF / GPS** — WGS84, геокод (Nominatim), карта, ExifTool, Google / Яндекс / OSM
- **ELA** — зоны с другим уровнем сжатия (правки JPEG)
- **Шум** — карта шума по кадру
- **Тени** — азимут и оценка широты по тени + дате из EXIF
- **LSB** — подозрение на стеганографию
- **Лица** — детекция OpenCV
- **OCR** — Tesseract, email, телефоны, URL
- **QR** — декод штрихкодов
- **Обратный поиск** — Lens, Яндекс, Bing, TinEye
- **Веб-поиск** — готовые запросы из EXIF/OCR

Плюс экспорт **Markdown / JSON**, скачивание JPEG **без EXIF**, полный дамп тегов.

## Быстрый старт

```bash
git clone <url> GeoHunter && cd GeoHunter
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python3 run.py
```

Системные пакеты (Debian / Kali / Ubuntu):

```bash
sudo apt install -y exiftool tesseract-ocr tesseract-ocr-rus tesseract-ocr-eng libzbar0 libgl1
```

Если `python3` не тот — явно:

```bash
/usr/bin/python3.13 run.py
```

Настройки: `.env` (см. `.env.example`).

## Как пользоваться

1. Загрузить фото или URL.
2. **Запустить** — модули работают параллельно.
3. В **EXIF** — карта, адрес, «Все теги», удаление метаданных.
4. Экспорт — иконки в шапке.

GPS есть только если он реально в файле (Telegram/WhatsApp часто вырезают). Для карты нужен доступ к `tiles.openfreemap.org` и CDN MapLibre.

## API

`POST /api/...`, JSON, поле `imageBase64`.

| Путь | Назначение |
|------|------------|
| `/api/exif` | EXIF, GPS, геокод |
| `/api/exif/strip` | JPEG без метаданных |
| `/api/forensics/ela` | ELA |
| `/api/forensics/noise` | шум |
| `/api/forensics/shadow-solve` | тени |
| `/api/forensics/stego` | LSB |
| `/api/forensics/faces` | лица |
| `/api/ocr` | текст |
| `/api/qr-barcode` | QR |
| `/api/reverse-search` | ссылки |
| `/api/search` | веб-запросы |
| `/api/export-report` | отчёт MD |
| `/api/export-json` | JSON |

```bash
curl -s -X POST http://127.0.0.1:5050/api/exif \
  -H "Content-Type: application/json" \
  -d "{\"imageBase64\":\"$(base64 -w0 photo.jpg)\",\"exiftool\":true,\"geocode\":true}"
```

## Структура

```
run.py
backend/          — Flask, API, tools/
static/photo/     — UI
tools/exif_inspector/
docs/             — баннер и скриншоты для README
```

## Частые проблемы

| Симптом | Решение |
|---------|---------|
| Нет exiftool | `apt install libimage-exiftool-perl` |
| Пустой OCR | `tesseract-ocr-rus` |
| QR молчит | `libzbar0` |
| Белая карта | интернет + консоль F12 |
| 413 | `MAX_UPLOAD_MB` в `.env` |

## Автор

**ERRORoX** — автор и мейнтейнер GeoHunter.

По вопросам, багам и предложениям: issues в репозитории или лично автору. В багрепорте приложите ОС, версию Python, `exiftool -ver` и текст ошибки из терминала / F12.

## Лицензия

Проект распространяется под **[MIT License](LICENSE)** — © 2026 ERRORoX.

Используйте на свой страх и риск и только в рамках закона. Координаты при геокоде уходят на Nominatim. Не выставляйте инстанс в открытый интернет без HTTPS и смены `SECRET_KEY`.
