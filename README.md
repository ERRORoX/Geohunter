# GeoHunter

**Локальная веб-платформа OSINT-анализа фотографий** — метаданные, геолокация, криминалистика изображений, OCR, QR и обратный поиск. Работает в браузере; обработка выполняется на вашем сервере, без облачного ИИ.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Flask](https://img.shields.io/badge/Flask-3.x-green)
![License](https://img.shields.io/badge/License-Internal-lightgrey)

---

## Содержание

- [Возможности](#возможности)
- [Требования](#требования)
- [Быстрый старт](#быстрый-старт)
- [Установка (подробно)](#установка-подробно)
- [Запуск](#запуск)
- [Использование](#использование)
- [Конфигурация](#конфигурация)
- [API](#api)
- [Структура проекта](#структура-проекта)
- [Устранение неполадок](#устранение-неполадок)
- [Безопасность и этика](#безопасность-и-этика)
- [Разработка](#разработка)

---

## Возможности

| Модуль | Описание | Зависимости |
|--------|----------|-------------|
| **EXIF / GPS** | Координаты, карта (MapLibre + OpenFreeMap), геокодирование адреса (Nominatim), ExifTool | `exiftool`, интернет для геокода |
| **Криминалистика (ELA)** | Error Level Analysis — следы пересохранения/монтажа | Pillow, OpenCV |
| **Анализ шума** | Неоднородность шума по кадру | NumPy, SciPy |
| **Анализ теней** | Оценка широты по углу тени и времени съёмки | Astral, EXIF-дата |
| **LSB / стеганография** | Младшие биты, подозрение на скрытые данные | Pillow |
| **Лица** | Детекция лиц (Haar Cascade) | OpenCV |
| **OCR** | Текст, email, телефоны, URL | Tesseract (`rus` + `eng`) |
| **QR / штрихкоды** | Декодирование кодов на изображении | `libzbar`, pyzbar |
| **Обратный поиск** | Ссылки на Google Lens, Яндекс, Bing, TinEye и др. | только браузер |
| **Веб-поиск** | Готовые поисковые запросы по данным из EXIF/OCR | только браузер |

Дополнительно:

- экспорт отчёта в **Markdown** и **JSON**;
- удаление EXIF из копии файла (скачивание «чистого» изображения);
- полный дамп тегов ExifTool с фильтром;
- параллельный запуск всех инструментов из UI.

---

## Требования

### Система

- **ОС:** Linux (рекомендуется Debian/Ubuntu/Kali), macOS или Windows (WSL2)
- **Python:** 3.10 или новее (рекомендуется **3.13**)
- **RAM:** от 2 ГБ для типичных JPEG; тяжёлые RAW увеличивают нагрузку
- **Интернет:** для карты, геокодирования и внешних ссылок поиска (основной анализ EXIF/OCR работает офлайн)

### Системные пакеты (Debian/Ubuntu/Kali)

```bash
sudo apt update
sudo apt install -y \
  python3 python3-venv python3-pip \
  exiftool \
  tesseract-ocr tesseract-ocr-rus tesseract-ocr-eng \
  libzbar0 \
  libgl1
```

> **Kali:** пакеты обычно уже установлены; проверьте наличие `exiftool` и `tesseract`.

### Python-зависимости

См. [`requirements.txt`](requirements.txt). Устанавливаются в виртуальное окружение (см. ниже).

---

## Быстрый старт

```bash
cd GeoHunter
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

python3 run.py
```

Откройте в браузере: **http://127.0.0.1:5050/photo/**

> Если в терминале IDE `python3` указывает на Cursor/Electron, используйте системный интерпретатор:
> `/usr/bin/python3.13 run.py`

---

## Установка (подробно)

### 1. Клонирование / копирование проекта

```bash
git clone <URL-репозитория> GeoHunter
cd GeoHunter
```

### 2. Виртуальное окружение

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Проверка внешних утилит

```bash
exiftool -ver
tesseract --version
```

### 4. (Опционально) Файл окружения

```bash
cp .env.example .env   # если есть шаблон; иначе создайте .env вручную
```

Минимальный пример `.env`:

```env
PORT=5050
HOST=0.0.0.0
FLASK_DEBUG=1
MAX_UPLOAD_MB=16
LOG_LEVEL=INFO
```

---

## Запуск

| Команда | Описание |
|---------|----------|
| `python3 run.py` | Основной способ (порт **5050** по умолчанию) |
| `PORT=8080 python3 run.py` | Другой порт |
| `FLASK_DEBUG=0 python3 run.py` | Без режима отладки (для «продакшена») |

После старта в консоли:

```text
GeoHunter → http://127.0.0.1:5050/photo/
Python: /usr/bin/python3.13
```

Альтернатива (напрямую Flask):

```bash
cd backend && python3 geohunter_blueprint.py
```

---

## Использование

### Веб-интерфейс (`/photo/`)

1. **Загрузите изображение** (перетаскивание, выбор файла или URL).
2. Нажмите **«Запустить»** — анализ всех модулей параллельно.
3. Раскройте карточки инструментов:
   - **EXIF** — GPS, карта, адрес, камера, даты, приватность;
   - **Криминалистика / шум / тени / LSB / лица** — визуальные и числовые метрики;
   - **OCR / QR** — извлечённый текст и коды;
   - **Обратный поиск / веб-поиск** — ссылки для ручной проверки в браузере.
4. **Экспорт** — кнопки Markdown / JSON в шапке (после завершения анализа).
5. **Удалить метаданные** — скачать копию без EXIF (кнопка в блоке EXIF).

### Советы

- Для GPS нужны теги `GPSLatitude` / `GPSLongitude` (или эквивалент через ExifTool).
- Карта требует доступа к `tiles.openfreemap.org` и `unpkg.com` (MapLibre).
- Геокод адреса использует [Nominatim](https://nominatim.org/) — не злоупотребляйте частыми запросами.
- Включите **«Все теги»** в EXIF для полного списка ExifTool (может занять несколько секунд).

---

## Конфигурация

Переменные окружения (файл `.env` или экспорт в shell):

| Переменная | По умолчанию | Назначение |
|------------|--------------|------------|
| `PORT` | `5050` | Порт HTTP-сервера |
| `HOST` | `0.0.0.0` | Адрес привязки |
| `FLASK_DEBUG` | `1` в `run.py` | Режим отладки Flask |
| `FLASK_USE_RELOADER` | `0` | Автоперезагрузка при изменении кода |
| `MAX_UPLOAD_MB` | `16` | Лимит размера тела запроса |
| `CORS_ORIGINS` | `*` | CORS (список через запятую) |
| `RATE_LIMIT_ENABLED` | `true` | Ограничение частоты запросов |
| `RATE_LIMIT_PER_MINUTE` | `60` | Запросов в минуту |
| `SECRET_KEY` | *(смените!)* | Секрет Flask (≥ 32 символов) |
| `LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `NOMINATIM_TIMEOUT` | `8` | Таймаут геокодера (сек) |
| `USER_AGENT` | `GeoHunter-EXIF/1.0` | User-Agent для Nominatim |
| `TESSERACT_CMD` | — | Путь к `tesseract`, если не в `PATH` |
| `GEOHUNTER_PYTHON` | — | Явный путь к Python для `run.py` |

---

## API

Базовый URL: `http://127.0.0.1:5050`

Все методы анализа изображений принимают JSON с полем **`imageBase64`** (data URL или чистый Base64).

| Метод | Путь | Назначение |
|-------|------|------------|
| `POST` | `/api/exif` | EXIF, GPS, геокод, сводка |
| `POST` | `/api/exif/strip` | JPEG без метаданных (бинарный ответ) |
| `POST` | `/api/exif/exiftool/json` | Полный JSON ExifTool |
| `POST` | `/api/exif/exiftool/txt` | Текстовый дамп ExifTool |
| `POST` | `/api/ocr` | OCR |
| `POST` | `/api/qr-barcode` | QR / штрихкоды |
| `POST` | `/api/forensics/ela` | ELA |
| `POST` | `/api/forensics/noise` | Анализ шума |
| `POST` | `/api/forensics/stego` | LSB / стеганография |
| `POST` | `/api/forensics/faces` | Детекция лиц |
| `GET` | `/api/forensics/sun` | Справка по модулю солнца |
| `POST` | `/api/forensics/shadow-solve` | Анализ теней |
| `POST` | `/api/reverse-search` | Ссылки обратного поиска |
| `POST` | `/api/search` | Поисковые запросы |
| `POST` | `/api/export-report` | Отчёт Markdown |
| `POST` | `/api/export-json` | Экспорт JSON |
| `GET` | `/api/ui/host-os` | Информация об ОС хоста |

Пример запроса EXIF:

```bash
curl -s -X POST http://127.0.0.1:5050/api/exif \
  -H "Content-Type: application/json" \
  -d '{"imageBase64":"'"$(base64 -w0 sample.jpg)"'","exiftool":true,"geocode":true}'
```

---

## Структура проекта

```text
GeoHunter/
├── run.py                 # Точка входа
├── requirements.txt       # Зависимости Python
├── README.md
├── backend/
│   ├── geohunter_blueprint.py   # Flask-приложение
│   ├── routes.py                # HTTP API
│   ├── services.py              # EXIF, GPS, геокод
│   ├── config.py                # Настройки (pydantic-settings)
│   ├── tools/                   # Плагины анализа
│   └── modules/                 # Вспомогательная логика
├── static/
│   ├── photo/                   # UI раздела «Фото»
│   │   ├── index.html
│   │   ├── css/photo.css
│   │   └── js/                  # ES modules
│   └── css/                     # Общая тема
└── tools/
    └── exif_inspector/          # Расширенный разбор EXIF
```

---

## Устранение неполадок

| Симптом | Решение |
|---------|---------|
| `exiftool не найден` | `sudo apt install libimage-exiftool-perl` |
| OCR пустой / ошибка | `sudo apt install tesseract-ocr tesseract-ocr-rus`; проверьте `tesseract --list-langs` |
| QR не декодируется | `sudo apt install libzbar0`; `pip install pyzbar` |
| Модуль «Лица» недоступен | `pip install opencv-python-headless` |
| Белая карта | Проверьте интернет и консоль браузера (F12); нужны `tiles.openfreemap.org`, `unpkg.com` |
| `python3` ведёт на Cursor | Запуск: `/usr/bin/python3.13 run.py` или `GEOHUNTER_PYTHON=/usr/bin/python3.13` |
| 413 Payload Too Large | Увеличьте `MAX_UPLOAD_MB` в `.env` |
| Нет GPS на карте | В файле нет координат в EXIF; загрузите оригинал с камеры/телефона |

Логи сервера при старте предупреждают о недостающих модулях (см. `backend/env_check.py`).

---

## Безопасность и этика

- Используйте GeoHunter **только на законных основаниях**: свои материалы, расследования с полномочиями, обучение.
- Не выкладывайте сервер в открытый интернет без аутентификации, HTTPS и жёсткого `SECRET_KEY`.
- Смените `SECRET_KEY` в production; ограничьте `CORS_ORIGINS` и включите rate limit.
- Геокодирование и карты отправляют координаты внешним сервисам — учитывайте OPSEC.
- Результаты OSINT — **гипотезы**, а не доказательства; перепроверяйте источники.

---

## Разработка

```bash
source venv/bin/activate
FLASK_DEBUG=1 python3 run.py
```

- UI: `static/photo/js/modules/` — модули ES6 (`photo-app.js`, `tool-runners.js`, `map.js`, …).
- Новый инструмент: класс в `backend/tools/`, регистрация в `backend/tools/registry.py`, endpoint в `routes.py`, запись в `static/photo/js/modules/tools-config.js`.

Проверка окружения при старте:

```bash
python3 -c "import sys; sys.path.insert(0,'backend'); from env_check import get_environment_status; import json; print(json.dumps(get_environment_status(), indent=2))"
```

---

## Поддержка

При ошибках приложите:

1. ОС и версию Python (`python3 --version`).
2. Вывод `exiftool -ver` и `tesseract --version`.
3. Текст ошибки из терминала и консоли браузера (F12).
4. Формат файла (JPEG/PNG/HEIC) без персональных данных на снимке.

---

**GeoHunter** — внутренний инструмент анализа изображений. Вопросы по развёртыванию и доступу — к администратору репозитория.
