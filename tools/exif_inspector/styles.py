#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EXIF Inspector - Настройки стилей
Все цвета, шрифты и настройки в одном месте
"""

# Dark Web цветовая схема
COLORS = {
    # Фоновые цвета - глубокий чёрный
    'background': '#000000',           # Чистый чёрный фон
    'panel_bg': '#0a0a0a',             # Очень тёмный серый
    'block_bg': '#111111',             # Тёмный серый для блоков
    
    # Основной текст - контрастный
    'text_primary': '#ffffff',         # Чистый белый
    'text_secondary': '#cccccc',       # Светло-серый
    'text_muted': '#888888',           # Серый
    
    # Dark Web акцентные цвета
    'dark_red': '#8b0000',             # Тёмно-красный
    'blood_red': '#ff0000',            # Кроваво-красный
    'dark_green': '#006400',           # Тёмно-зелёный
    'toxic_green': '#00ff00',          # Токсичный зелёный
    'dark_blue': '#000080',            # Тёмно-синий
    'cyber_blue': '#00ffff',           # Кибер-голубой
    'dark_purple': '#4b0082',          # Тёмно-фиолетовый
    'neon_purple': '#ff00ff',          # Неоновый фиолетовый
    
    # Границы и разделители
    'border': '#1a1a1a',               # Тёмно-серый
    'border_light': '#333333',         # Серый
    
    # Дополнительные цвета
    'warning': '#ff8c00',              # Тёмно-оранжевый
    'danger': '#dc143c',               # Малиновый
    'success': '#32cd32',              # Лайм-зелёный
    'info': '#4169e1'                  # Королевский синий
}

# Шрифты
FONTS = {
    'title': ("Consolas", 14, "bold"),
    'subtitle': ("Consolas", 10),
    'button': ("Consolas", 10, "bold"),
    'label': ("Consolas", 11, "bold"),
    'entry': ("Consolas", 10),
    'output': ("Consolas", 8, "bold"),
    'status': ("Consolas", 10),
    'matrix': ("Consolas", 12)
}

# Размеры окна
WINDOW_SIZE = "1200x800"

# Настройки анимации
ANIMATION_SETTINGS = {
    'scan_speed': 2,
    'scan_line_width': 3,
    'matrix_drops_count': 50,
    'matrix_update_interval': 100,
    'scan_update_interval': 50,
    'indicator_update_interval': 500
}

# Символы для матричного дождя
MATRIX_CHARS = "ERROR"

# Поддерживаемые форматы изображений
SUPPORTED_FORMATS = [
    '.jpg', '.jpeg', '.png', '.tiff', '.tif', 
    '.gif', '.bmp', '.raw', '.cr2', '.nef', '.arw'
]

# Настройки EXIF категорий
EXIF_CATEGORIES = {
    "📁 Основная информация": [
        "SourceFile", "FileName", "FileSize", "FileType", "FileTypeExtension",
        "MIMEType", "ImageWidth", "ImageHeight", "ImageSize", "Megapixels",
        "FileModifyDate", "FileAccessDate", "FileInodeChangeDate", "FilePermissions",
        "Directory", "FileInode", "FileDevice", "FileLinks", "FileUserID", "FileGroupID"
    ],
    "📱 Устройство и производитель": [
        "Make", "Model", "Software", "DeviceSettingDescription", "ExifToolVersion",
        "UniqueCameraModel", "LocalizedCameraModel", "CameraSerialNumber", "InternalSerialNumber",
        "FirmwareVersion", "LensModel", "LensSerialNumber", "LensFirmwareVersion"
    ],
    "📅 Время и даты": [
        "DateTime", "DateTimeOriginal", "CreateDate", "ModifyDate",
        "SubSecCreateDate", "SubSecDateTimeOriginal", "SubSecModifyDate",
        "SubSecTime", "SubSecTimeOriginal", "SubSecTimeDigitized",
        "TimeCreated", "DateCreated", "DigitalCreationDate", "DigitalCreationTime"
    ],
    "📍 GPS и геолокация": [
        "GPSLatitude", "GPSLongitude", "GPSAltitude", "GPSLatitudeRef", "GPSLongitudeRef",
        "GPSDateTime", "GPSTimeStamp", "GPSDateStamp", "GPSAltitudeRef",
        "GPSProcessingMethod", "GPSAreaInformation", "GPSDOP", "GPSSpeed", "GPSTrack",
        "GPSImgDirection", "GPSMapDatum", "GPSDestLatitude", "GPSDestLongitude"
    ],
    "📷 Настройки камеры": [
        "ExposureTime", "ShutterSpeed", "ShutterSpeedValue", "FNumber", "Aperture", "ApertureValue",
        "ISO", "FocalLength", "FocalLengthIn35mmFormat", "FocalLength35efl",
        "Flash", "WhiteBalance", "ExposureMode", "ExposureProgram", "MeteringMode",
        "BrightnessValue", "LightValue", "CircleOfConfusion", "FOV", "HyperfocalDistance",
        "ExposureBiasValue", "MaxApertureValue", "SubjectDistance", "SubjectDistanceRange",
        "DigitalZoomRatio", "FocalPlaneXResolution", "FocalPlaneYResolution"
    ],
    "🎨 Цвет и обработка": [
        "ColorSpace", "ColorProfile", "ColorTemperature", "Saturation", "Contrast",
        "Sharpness", "Brightness", "YCbCrPositioning", "YCbCrSubSampling",
        "ColorComponents", "BitsPerSample", "Compression", "EncodingProcess",
        "ColorMode", "ColorFilter", "ColorMatrix", "ColorMatrix1", "ColorMatrix2",
        "CustomRendered", "GainControl", "SceneCaptureType", "SceneType"
    ],
    "🔧 Технические данные EXIF": [
        "ExifByteOrder", "ExifVersion", "FlashpixVersion", "InteropIndex", "InteropVersion",
        "XResolution", "YResolution", "ResolutionUnit", "ComponentsConfiguration",
        "PixelXDimension", "PixelYDimension", "ExifImageWidth", "ExifImageHeight",
        "ThumbnailOffset", "ThumbnailLength", "ScaleFactor35efl", "ExifImageUniqueID",
        "ImageUniqueID", "DocumentName", "ImageDescription", "Artist", "Copyright",
        "UserComment", "RelatedImageFileFormat", "RelatedImageWidth", "RelatedImageHeight"
    ],
    "📸 Сенсор и оптика": [
        "Sensor_type", "SensingMethod", "Mirror", "SceneType", "SceneCaptureType",
        "FileSource", "CustomRendered", "DigitalZoomRatio", "SubjectDistanceRange",
        "LensSpecification", "LensMake", "LensModel", "LensSerialNumber",
        "FocalPlaneResolutionUnit", "FocalPlaneXResolution", "FocalPlaneYResolution",
        "SensingMethod", "CFAPattern", "CFAPattern2", "CFALayout", "CFAPlaneColor"
    ],
    "📱 Мобильные устройства": [
        "DeviceSettingDescription", "DeviceAttributes", "DeviceManufacturer", "DeviceModel",
        "DeviceSoftwareVersion", "DeviceFirmwareVersion", "DeviceSerialNumber",
        "DeviceUniqueID", "DeviceUserID", "DeviceGroupID", "DevicePermissions"
    ],
    "🎬 Видео и аудио": [
        "VideoFrameRate", "VideoBitRate", "VideoCodec", "AudioCodec", "AudioBitRate",
        "AudioSampleRate", "AudioChannels", "Duration", "FrameCount", "FrameRate"
    ],
    "🔍 Дополнительные метаданные": [
        "XMPToolkit", "CreatorTool", "Creator", "Rights", "UsageTerms", "WebStatement",
        "Subject", "Description", "Title", "Headline", "Caption", "Keywords",
        "Location", "City", "State", "Country", "CountryCode", "Sublocation"
    ]
}

# Русские названия полей
FIELD_NAMES = {
    # Основная информация
    "SourceFile": "Исходный файл",
    "FileName": "Имя файла",
    "FileSize": "Размер файла",
    "FileType": "Тип файла",
    "FileTypeExtension": "Расширение файла",
    "MIMEType": "MIME тип",
    "ImageWidth": "Ширина изображения",
    "ImageHeight": "Высота изображения",
    "ImageSize": "Размер изображения",
    "Megapixels": "Мегапиксели",
    "FileModifyDate": "Дата изменения файла",
    "FileAccessDate": "Дата доступа к файлу",
    "FileInodeChangeDate": "Дата изменения inode",
    "FilePermissions": "Права доступа к файлу",
    "Directory": "Директория",
    "FileInode": "Inode файла",
    "FileDevice": "Устройство файла",
    "FileLinks": "Ссылки на файл",
    "FileUserID": "ID пользователя файла",
    "FileGroupID": "ID группы файла",

    # Устройство и производитель
    "Make": "Производитель",
    "Model": "Модель",
    "Software": "Программное обеспечение",
    "DeviceSettingDescription": "Описание настроек устройства",
    "ExifToolVersion": "Версия ExifTool",
    "UniqueCameraModel": "Уникальная модель камеры",
    "LocalizedCameraModel": "Локализованная модель камеры",
    "CameraSerialNumber": "Серийный номер камеры",
    "InternalSerialNumber": "Внутренний серийный номер",
    "FirmwareVersion": "Версия прошивки",
    "LensModel": "Модель объектива",
    "LensSerialNumber": "Серийный номер объектива",
    "LensFirmwareVersion": "Версия прошивки объектива",

    # Время и даты
    "DateTime": "Дата и время",
    "DateTimeOriginal": "Оригинальная дата и время",
    "CreateDate": "Дата создания",
    "ModifyDate": "Дата изменения",
    "SubSecCreateDate": "Дата создания с долями секунды",
    "SubSecDateTimeOriginal": "Оригинальная дата с долями секунды",
    "SubSecModifyDate": "Дата изменения с долями секунды",
    "SubSecTime": "Доли секунды времени",
    "SubSecTimeOriginal": "Оригинальные доли секунды времени",
    "SubSecTimeDigitized": "Оцифрованные доли секунды времени",
    "TimeCreated": "Время создания",
    "DateCreated": "Дата создания",
    "DigitalCreationDate": "Дата цифрового создания",
    "DigitalCreationTime": "Время цифрового создания",

    # GPS и геолокация
    "GPSLatitude": "GPS Широта",
    "GPSLongitude": "GPS Долгота",
    "GPSAltitude": "GPS Высота",
    "GPSLatitudeRef": "Ссылка GPS широты",
    "GPSLongitudeRef": "Ссылка GPS долготы",
    "GPSDateTime": "GPS дата и время",
    "GPSTimeStamp": "GPS временная метка",
    "GPSDateStamp": "GPS дата",
    "GPSAltitudeRef": "Ссылка GPS высоты",
    "GPSProcessingMethod": "Метод обработки GPS",
    "GPSAreaInformation": "Информация о GPS области",
    "GPSDOP": "GPS DOP",
    "GPSSpeed": "GPS скорость",
    "GPSTrack": "GPS трек",
    "GPSImgDirection": "GPS направление изображения",
    "GPSMapDatum": "GPS картографическая датум",
    "GPSDestLatitude": "GPS широта назначения",
    "GPSDestLongitude": "GPS долгота назначения",

    # Настройки камеры
    "ExposureTime": "Выдержка",
    "ShutterSpeed": "Скорость затвора",
    "ShutterSpeedValue": "Значение скорости затвора",
    "FNumber": "Диафрагма",
    "Aperture": "Диафрагма (число)",
    "ApertureValue": "Значение диафрагмы",
    "ISO": "ISO",
    "FocalLength": "Фокусное расстояние",
    "FocalLengthIn35mmFormat": "Фокусное расстояние в 35мм эквиваленте",
    "FocalLength35efl": "Эффективное фокусное расстояние",
    "Flash": "Вспышка",
    "WhiteBalance": "Баланс белого",
    "ExposureMode": "Режим экспозиции",
    "ExposureProgram": "Программа экспозиции",
    "MeteringMode": "Режим замера",
    "BrightnessValue": "Значение яркости",
    "LightValue": "Значение освещенности",
    "CircleOfConfusion": "Круг нерезкости",
    "FOV": "Поле зрения",
    "HyperfocalDistance": "Гиперфокальное расстояние",
    "ExposureBiasValue": "Значение экспокоррекции",
    "MaxApertureValue": "Максимальное значение диафрагмы",
    "SubjectDistance": "Расстояние до объекта",
    "SubjectDistanceRange": "Диапазон расстояния до объекта",
    "DigitalZoomRatio": "Коэффициент цифрового зума",
    "FocalPlaneXResolution": "Разрешение фокальной плоскости по X",
    "FocalPlaneYResolution": "Разрешение фокальной плоскости по Y",

    # Цвет и обработка
    "ColorSpace": "Цветовое пространство",
    "ColorProfile": "Цветовой профиль",
    "ColorTemperature": "Цветовая температура",
    "Saturation": "Насыщенность",
    "Contrast": "Контрастность",
    "Sharpness": "Резкость",
    "Brightness": "Яркость",
    "YCbCrPositioning": "Позиционирование YCbCr",
    "YCbCrSubSampling": "Подвыборка YCbCr",
    "ColorComponents": "Цветовые компоненты",
    "BitsPerSample": "Битов на сэмпл",
    "Compression": "Сжатие",
    "EncodingProcess": "Процесс кодирования",
    "ColorMode": "Режим цвета",
    "ColorFilter": "Цветовой фильтр",
    "ColorMatrix": "Цветовая матрица",
    "ColorMatrix1": "Цветовая матрица 1",
    "ColorMatrix2": "Цветовая матрица 2",
    "CustomRendered": "Пользовательская обработка",
    "GainControl": "Управление усилением",
    "SceneCaptureType": "Тип захвата сцены",
    "SceneType": "Тип сцены",

    # Технические данные EXIF
    "ExifByteOrder": "Порядок байтов EXIF",
    "ExifVersion": "Версия EXIF",
    "FlashpixVersion": "Версия FlashPix",
    "InteropIndex": "Индекс совместимости",
    "InteropVersion": "Версия совместимости",
    "XResolution": "Разрешение по X",
    "YResolution": "Разрешение по Y",
    "ResolutionUnit": "Единица разрешения",
    "ComponentsConfiguration": "Конфигурация компонентов",
    "PixelXDimension": "Размер пикселя по X",
    "PixelYDimension": "Размер пикселя по Y",
    "ExifImageWidth": "Ширина EXIF изображения",
    "ExifImageHeight": "Высота EXIF изображения",
    "ThumbnailOffset": "Смещение миниатюры",
    "ThumbnailLength": "Длина миниатюры",
    "ScaleFactor35efl": "Масштабный коэффициент 35мм",
    "ExifImageUniqueID": "Уникальный ID EXIF изображения",
    "ImageUniqueID": "Уникальный ID изображения",
    "DocumentName": "Имя документа",
    "ImageDescription": "Описание изображения",
    "Artist": "Автор",
    "Copyright": "Авторские права",
    "UserComment": "Комментарий пользователя",
    "RelatedImageFileFormat": "Формат связанного изображения",
    "RelatedImageWidth": "Ширина связанного изображения",
    "RelatedImageHeight": "Высота связанного изображения",

    # Сенсор и оптика
    "Sensor_type": "Тип сенсора",
    "SensingMethod": "Метод сенсора",
    "Mirror": "Зеркало",
    "SceneType": "Тип сцены",
    "SceneCaptureType": "Тип захвата сцены",
    "FileSource": "Источник файла",
    "CustomRendered": "Пользовательская обработка",
    "DigitalZoomRatio": "Коэффициент цифрового зума",
    "SubjectDistanceRange": "Диапазон расстояния до объекта",
    "LensSpecification": "Спецификация объектива",
    "LensMake": "Производитель объектива",
    "LensModel": "Модель объектива",
    "LensSerialNumber": "Серийный номер объектива",
    "FocalPlaneResolutionUnit": "Единица разрешения фокальной плоскости",
    "FocalPlaneXResolution": "Разрешение фокальной плоскости по X",
    "FocalPlaneYResolution": "Разрешение фокальной плоскости по Y",
    "CFAPattern": "Паттерн CFA",
    "CFAPattern2": "Паттерн CFA 2",
    "CFALayout": "Макет CFA",
    "CFAPlaneColor": "Цвет плоскости CFA",

    # Мобильные устройства
    "DeviceSettingDescription": "Описание настроек устройства",
    "DeviceAttributes": "Атрибуты устройства",
    "DeviceManufacturer": "Производитель устройства",
    "DeviceModel": "Модель устройства",
    "DeviceSoftwareVersion": "Версия ПО устройства",
    "DeviceFirmwareVersion": "Версия прошивки устройства",
    "DeviceSerialNumber": "Серийный номер устройства",
    "DeviceUniqueID": "Уникальный ID устройства",
    "DeviceUserID": "ID пользователя устройства",
    "DeviceGroupID": "ID группы устройства",
    "DevicePermissions": "Права устройства",

    # Видео и аудио
    "VideoFrameRate": "Частота кадров видео",
    "VideoBitRate": "Битрейт видео",
    "VideoCodec": "Кодек видео",
    "AudioCodec": "Кодек аудио",
    "AudioBitRate": "Битрейт аудио",
    "AudioSampleRate": "Частота дискретизации аудио",
    "AudioChannels": "Каналы аудио",
    "Duration": "Длительность",
    "FrameCount": "Количество кадров",
    "FrameRate": "Частота кадров",

    # Дополнительные метаданные
    "XMPToolkit": "XMP Toolkit",
    "CreatorTool": "Инструмент создания",
    "Creator": "Создатель",
    "Rights": "Права",
    "UsageTerms": "Условия использования",
    "WebStatement": "Веб-заявление",
    "Subject": "Тема",
    "Description": "Описание",
    "Title": "Заголовок",
    "Headline": "Заголовок",
    "Caption": "Подпись",
    "Keywords": "Ключевые слова",
    "Location": "Местоположение",
    "City": "Город",
    "State": "Область/Штат",
    "Country": "Страна",
    "CountryCode": "Код страны",
    "Sublocation": "Подместоположение"
}
