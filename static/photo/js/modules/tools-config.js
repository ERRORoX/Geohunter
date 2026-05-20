/** Список инструментов GeoHunter (фото). */

export const TOOLS = [
  {
    id: 'exif',
    name: 'EXIF и местоположение',
    desc: 'Метаданные, GPS, адрес, карта',
    cat: 'Метаданные',
    color: 'var(--sky)',
  },
  {
    id: 'forensics',
    name: 'Криминалистика (ELA)',
    desc: 'Следы монтажа по уровню сжатия',
    cat: 'Анализ',
    color: 'var(--rose)',
  },
  {
    id: 'noise',
    name: 'Анализ шума',
    desc: 'Неестественные области шума',
    cat: 'Анализ',
    color: 'var(--pink)',
  },
  {
    id: 'shadows',
    name: 'Анализ теней',
    desc: 'Угол солнца и широта по тени',
    cat: 'Анализ',
    color: 'var(--amber)',
  },
  {
    id: 'stego',
    name: 'LSB / стеганография',
    desc: 'Младшие биты и скрытые данные',
    cat: 'Анализ',
    color: 'var(--cyan)',
  },
  {
    id: 'faces',
    name: 'Лица',
    desc: 'Детекция лиц (OpenCV)',
    cat: 'Анализ',
    color: 'var(--emerald)',
  },
  {
    id: 'ocr',
    name: 'OCR / текст',
    desc: 'Распознавание текста на фото',
    cat: 'Текст',
    color: 'var(--cyan)',
  },
  {
    id: 'qr',
    name: 'QR и штрихкоды',
    desc: 'Ссылки и данные из кодов',
    cat: 'Текст',
    color: 'var(--violet)',
  },
  {
    id: 'reverse',
    name: 'Обратный поиск',
    desc: 'Где ещё встречается изображение',
    cat: 'Поиск',
    color: 'var(--violet)',
  },
  {
    id: 'websearch',
    name: 'Веб-поиск',
    desc: 'Запросы Google/Yandex по данным фото',
    cat: 'Поиск',
    color: 'var(--emerald)',
  },
];

export const CATEGORIES = [...new Set(TOOLS.map((t) => t.cat))];

export const OFFLINE_EP = {
  ocr: '/api/ocr',
  qr: '/api/qr-barcode',
  forensics: '/api/forensics/ela',
  noise: '/api/forensics/noise',
  shadows: '/api/forensics/shadow-solve',
  stego: '/api/forensics/stego',
  faces: '/api/forensics/faces',
  reverse: '/api/reverse-search',
  websearch: '/api/search',
};

export const REVERSE_LABELS = {
  googleLens: 'Google Lens',
  yandexImages: 'Яндекс',
  bingVisual: 'Bing',
  tineye: 'TinEye',
  baidu: 'Baidu',
};

export const SEARCH_ENGINE_LABELS = {
  google: 'Google',
  yandex: 'Яндекс',
  duckduckgo: 'DuckDuckGo',
  bing: 'Bing',
};
