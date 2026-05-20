import { esc, exifTagValue, exifToDatetimeLocal, parseGpsCoords } from './utils.js';
import { IC } from './icons.js';
import { REVERSE_LABELS, SEARCH_ENGINE_LABELS } from './tools-config.js';
import { state } from './state.js';
import { getExifMapContainerId, getShadowMapContainerId } from './map.js';

function metaBox(entries) {
  const rows = entries
    .filter(([, v]) => v != null && v !== '')
    .map(
      ([k, v]) =>
        `<div class="meta-row"><span class="meta-key">${esc(k)}</span><span class="meta-val">${esc(v)}</span></div>`
    )
    .join('');
  return rows ? `<div class="exif-meta-box">${rows}</div>` : '';
}

function linkGrid(links, labels) {
  if (!links || typeof links !== 'object') return '';
  return `<div class="reverse-grid">${Object.entries(links)
    .map(([key, url]) => {
      const label = labels[key] || key;
      return `<a class="reverse-link" href="${esc(url)}" target="_blank" rel="noopener">${IC.ext}<span>${esc(label)}</span></a>`;
    })
    .join('')}</div>`;
}

function section(title, body) {
  if (!body) return '';
  return `<div class="section-label" style="color:var(--text3);margin-top:10px">${esc(title)}</div>${body}`;
}

function exifSubBlock(title, body) {
  if (!body) return '';
  return `<div class="exif-sub-block"><p class="exif-sub-title">${esc(title)}</p>${body}</div>`;
}

function compassFromAzimuth(deg) {
  const d = ((Number(deg) % 360) + 360) % 360;
  const names = [
    'север',
    'северо-восток',
    'восток',
    'юго-восток',
    'юг',
    'юго-запад',
    'запад',
    'северо-запад',
  ];
  return names[Math.round(d / 45) % 8];
}

function renderSunBlock(sun) {
  const az = Number(sun.azimuth);
  const el = Number(sun.elevation);
  const dir = compassFromAzimuth(az);
  return metaBox([
    ['Направление', dir],
    ['Азимут', Number.isFinite(az) ? `${az.toFixed(2)}°` : '—'],
    ['Высота', Number.isFinite(el) ? `${el.toFixed(2)}°` : '—'],
    ['UTC', sun.dt || '—'],
  ]);
}

export function getToolCardSummary(id, d) {
  if (!d || d.error) return '';
  switch (id) {
    case 'exif': {
      const c = parseGpsCoords(d.gps);
      if (c) {
        return `${c.lat.toFixed(5)}, ${c.lon.toFixed(5)}`;
      }
      return d.has_metadata === false ? 'нет метаданных' : 'нет GPS';
    }
    case 'shadows': {
      if (d.elevation == null) return '';
      const ang = `${Number(d.elevation).toFixed(1)}°`;
      const lat = d.latitude_summary;
      if (lat && !lat.startsWith('Нет')) {
        const short = lat.replace(/с\.ш\.|ю\.ш\./g, '').trim();
        return `${ang} · ${short.slice(0, 24)}`;
      }
      return ang;
    }
    case 'ocr':
      return d.fullText ? `${(d.fullText.match(/\S+/g) || []).length} слов` : d.emails?.length ? `${d.emails.length} email` : '';
    case 'qr': {
      const n = d.items?.length || d.decoded?.length || 0;
      return n ? `${n} код` : '—';
    }
    case 'forensics':
      return d.ela_image ? 'ELA' : '';
    case 'noise':
      return d.noise_image ? 'карта' : '';
    case 'stego':
      return d.verdict ? String(d.verdict).slice(0, 36) : d.chi_square_score != null ? `χ² ${d.chi_square_score}` : '';
    case 'faces':
      return d.face_count != null ? `${d.face_count} лиц` : '';
    case 'reverse':
      return d.mode === 'url' ? 'URL' : d.uploadPages ? 'загрузка' : '';
    case 'websearch': {
      const n = (d.results || []).length;
      return n ? `${n} запр.` : '';
    }
    default:
      return '';
  }
}

const ADDR_LABELS = {
  road: 'Улица', house_number: 'Дом', suburb: 'Район', city: 'Город', town: 'Город',
  village: 'Населённый пункт', state: 'Регион', country: 'Страна', postcode: 'Индекс',
};

function formatAddressRows(addr) {
  if (!addr || typeof addr !== 'object') return '';
  const rows = Object.entries(ADDR_LABELS).map(([key, label]) => {
    const v = addr[key];
    if (!v) return '';
    return `<div class="exif-addr-row"><dt>${esc(label)}</dt><dd>${esc(v)}</dd></div>`;
  }).filter(Boolean).join('');
  return rows ? `<dl class="exif-addr-dl">${rows}</dl>` : '';
}

function renderLocationMapBlock(gps) {
  const coords = parseGpsCoords(gps);
  if (!coords) return '';
  const { lat, lon } = coords;
  const mapId = getExifMapContainerId();
  return `<div class="location-map-wrap">
    <div id="${mapId}" class="gps-map gps-map-inline photo-map--exif location-map"></div>
    <div class="tag-list location-map-actions">
      <button type="button" class="upload-toggle" data-gh="open-full-map" data-lat="${lat}" data-lon="${lon}">Карта на весь экран</button>
    </div>
  </div>`;
}

function renderLocationAddressCol(gps) {
  const coords = parseGpsCoords(gps);
  if (!coords) {
    const hint = gps?.note ? esc(String(gps.note)) : 'Числовые координаты в EXIF не найдены';
    const hasAddr = gps?.display_name || (gps?.address && Object.keys(gps.address).length);
    if (hasAddr) {
      return `<div class="gps-box gps-box--col">
        <div class="gps-address"><p class="gps-address-title">Место (без координат для карты)</p>
        ${gps.display_name ? `<p class="gps-address-text">${esc(gps.display_name)}</p>` : ''}
        ${formatAddressRows(gps.address)}
        <p class="gps-geocode-miss">${hint}</p></div></div>`;
    }
    return `<div class="no-gps">${IC.info}<span>${hint}</span></div>`;
  }
  const { lat, lon } = coords;
  let h = `<div class="gps-box gps-box--col">
    <div class="gps-address">
      <p class="gps-address-title">Адрес</p>`;
  if (gps.display_name) h += `<p class="gps-address-text">${esc(gps.display_name)}</p>`;
  else if (!gps.address) h += `<p class="gps-geocode-miss">Адрес не загружен (нужен интернет).</p>`;
  if (gps.offline_location && !gps.display_name) {
    h += `<p class="gps-address-text">${esc(gps.offline_location)} (офлайн)</p>`;
  }
  h += formatAddressRows(gps.address);
  h += `</div>
    <div class="gps-coord-row">
      <span class="gps-coord-key">Координаты</span>
      <span class="gps-coord-val">${lat.toFixed(6)}, ${lon.toFixed(6)}</span>
    </div>
    <div class="gps-links">
      <a href="https://www.google.com/maps?q=${lat},${lon}" target="_blank" rel="noopener">${IC.ext} Google</a>
      <a href="https://yandex.ru/maps/?pt=${lon},${lat}&z=15&l=map" target="_blank" rel="noopener">${IC.ext} Яндекс</a>
    </div>
  </div>`;
  return h;
}

function renderExifMetadataCol(d) {
  let html = '';
  if (d.sun && !d.sun.error) {
    html += exifSubBlock('Солнце', renderSunBlock(d.sun));
  } else if (d.sun?.error) {
    html += `<p class="exif-file-note">${esc(d.sun.error)}</p>`;
  }
  if (d.camera && Object.keys(d.camera).length) {
    html += exifSubBlock('Камера', metaBox(Object.entries(d.camera)));
  }
  if (d.dates && Object.keys(d.dates).length) {
    html += exifSubBlock('Даты', metaBox(Object.entries(d.dates)));
  }
  if (d.software && Object.keys(d.software).length) {
    html += exifSubBlock('ПО / автор', metaBox(Object.entries(d.software)));
  }
  if (d.shooting && Object.keys(d.shooting).length) {
    html += exifSubBlock(
      'Параметры съёмки',
      metaBox(Object.entries(d.shooting).map(([k, v]) => [k, Array.isArray(v) ? v.join('/') : String(v)]))
    );
  }
  if (d.hashes && typeof d.hashes === 'object') {
    html += exifSubBlock('Хэши', metaBox(Object.entries(d.hashes)));
  }
  if (d.exiftool_tag_count) {
    html += `<p class="exif-file-note">ExifTool: ${d.exiftool_tag_count} тегов</p>`;
  }
  if (d.exiftool?.error) {
    html += `<p class="exif-file-note" style="color:var(--amber)">${esc(d.exiftool.error)}</p>`;
  }
  const tags = renderExifTagsList();
  if (tags) html += exifSubBlock('ExifTool — все теги', tags);
  return html || `<p style="color:var(--text4)">Нет дополнительных метаданных</p>`;
}

function renderLocationSection(d) {
  const gps = d.gps || {};
  const hasGps = !!parseGpsCoords(gps);
  const mapBlock = hasGps
    ? renderLocationMapBlock(gps)
    : gps?.note
      ? `<p class="exif-file-note location-no-gps">${esc(String(gps.note))}</p>`
      : `<p class="exif-file-note location-no-gps">Нет координат для карты — нужны GPSLatitude/GPSLongitude в EXIF.</p>`;
  return `<div class="location-section">
    <div class="section-label location-section-title">Местоположение</div>
    ${mapBlock}
    <div class="exif-side-by-side location-split">
      <div class="exif-col location-col-address">${renderLocationAddressCol(gps)}</div>
      <div class="exif-col location-col-meta">${renderExifMetadataCol(d)}</div>
    </div>
  </div>`;
}

function renderExifTagsList() {
  if (!state.exifShowAllTags) return '';
  if (state.exiftoolFullLoading) {
    return `<p style="color:var(--text4);font-size:11px;margin-top:8px">Загрузка тегов ExifTool…</p>`;
  }
  if (state.exiftoolFullErr) {
    return `<p class="error-text">${esc(state.exiftoolFullErr)}</p>`;
  }
  const rec = state.exiftoolFull;
  if (!rec || typeof rec !== 'object') {
    return `<p style="color:var(--text4);font-size:11px;margin-top:8px">Включите «Все теги» (нужен ExifTool в системе).</p>`;
  }
  const q = (state.exiftoolFullQuery || '').trim().toLowerCase();
  const entries = Object.entries(rec).filter(([k, v]) => {
    if (!q) return true;
    return `${k} ${exifTagValue(v)}`.toLowerCase().includes(q);
  });
  const shown = entries.slice(0, 400);
  const rows = shown
    .map(
      ([k, v]) =>
        `<div class="exiftool-row"><span class="exiftool-k">${esc(k)}</span><span class="exiftool-v">${esc(exifTagValue(v))}</span></div>`
    )
    .join('');
  return `
    <div class="exiftool-search">
      <input type="search" class="exiftool-search-input" placeholder="Фильтр тегов…" value="${esc(state.exiftoolFullQuery)}" data-gh="exif-filter"/>
      <span class="exiftool-search-meta">${shown.length}/${entries.length}</span>
    </div>
    <div class="exiftool-list scroll-y">${rows || '<p style="color:var(--text4)">Нет совпадений</p>'}</div>
    ${entries.length > 400 ? `<p class="exif-file-note">Показаны первые 400 из ${entries.length} тегов.</p>` : ''}`;
}

function renderExif(d) {
  if (d.error) return `<p class="error-text">${esc(d.error)}</p>`;

  let html = `<div class="tag-list exif-toolbar" style="margin-bottom:10px">
    <button type="button" class="upload-toggle ${state.exifAdvanced ? 'active' : ''}" data-gh="toggle-exiftool">ExifTool</button>
    <button type="button" class="upload-toggle ${state.exifShowAllTags ? 'active' : ''}" data-gh="toggle-exif-tags">Все теги</button>
    <button type="button" class="upload-toggle" data-gh="strip-exif">Удалить метаданные</button>
  </div>`;

  if (d.has_metadata === false && !d.gps) {
    html += `<p style="color:var(--text4);margin-top:8px">В файле не обнаружено EXIF/GPS. Загрузите оригинал с камеры или включите ExifTool.</p>`;
  }

  if (Array.isArray(d.privacy) && d.privacy.length) {
    html += section(
      'Приватность',
      `<div class="tag-list">${d.privacy.map((x) => `<span class="tag" style="border-color:rgba(239,68,68,0.2);color:var(--red)">${esc(x)}</span>`).join('')}</div>`
    );
  }

  html += renderLocationSection(d);

  return html;
}

function renderOcr(d) {
  if (d.error) return `<p class="error-text">${esc(d.error)}</p>`;
  if (d.hint && !d.fullText) return `<p class="exif-file-note">${esc(d.hint)}</p>`;
  if (!d.fullText && !d.emails?.length && !d.phones?.length && !d.urls?.length) {
    return `<p style="color:var(--text4)">Текст не найден. Установите tesseract-ocr-rus.</p>`;
  }
  let html = '';
  if (d.fullText) {
    html += `<div class="text-box"><div class="tb-label">Текст</div><div class="tb-text scroll-y" style="max-height:120px">${esc(d.fullText)}</div></div>`;
  }
  const tags = [
    ['Email', d.emails],
    ['Телефоны', d.phones],
    ['URL', d.urls],
  ];
  for (const [label, arr] of tags) {
    if (arr?.length) {
      html += section(label, `<div class="tag-list">${arr.map((t) => `<span class="tag">${esc(t)}</span>`).join('')}</div>`);
    }
  }
  return html;
}

function renderQr(d) {
  if (d.error) return `<p class="error-text">${esc(d.error)}</p>`;
  const items = d.items?.length ? d.items : (d.decoded || []).map((s) => ({ type: 'code', data: s }));
  if (!items.length) return `<p style="color:var(--text4)">Коды не найдены</p>`;
  return metaBox(items.map((it) => [it.type || 'QR', it.data || it]));
}

function renderImageTool(d, key, label) {
  if (d.error) return `<p class="error-text">${esc(d.error)}</p>`;
  const src = d[key];
  if (!src) return `<p style="color:var(--text4)">Нет данных</p>`;
  return `<div class="ela-img-wrap" style="margin-top:12px;border-radius:10px;overflow:hidden;border:1px solid var(--border)">
    <img src="${src}" alt="${esc(label)}" style="width:100%;display:block;cursor:zoom-in" data-gh="zoom-img"/>
    ${d.note ? `<p class="exif-file-note">${esc(d.note)}</p>` : ''}
  </div>`;
}

function renderStego(d) {
  if (d.error) return `<p class="error-text">${esc(d.error)}</p>`;
  let html = '';
  if (d.verdict) {
    html += metaBox([
      ['Вердикт', d.verdict],
      ['Энтропия LSB', d.lsb_entropy != null ? String(d.lsb_entropy) : '—'],
      ['Доля единиц', d.lsb_ones_ratio != null ? String(d.lsb_ones_ratio) : '—'],
      ['χ² (LSB)', d.chi_square_score != null ? String(d.chi_square_score) : '—'],
    ]);
  }
  if (d.hidden_text_preview) {
    html += section('Фрагмент из LSB', `<pre class="stego-preview">${esc(d.hidden_text_preview)}</pre>`);
  }
  if (d.lsb_image) {
    html += renderImageTool({ ...d, note: d.note }, 'lsb_image', 'LSB');
  }
  return html || `<p style="color:var(--text4)">Нет данных</p>`;
}

function renderFaces(d) {
  if (d.error) return `<p class="error-text">${esc(d.error)}</p>`;
  const n = d.face_count != null ? String(d.face_count) : '—';
  let html = metaBox([['Найдено', n]]);
  if (d.annotated_image && d.face_count > 0) {
    html += renderImageTool({ ...d, note: '' }, 'annotated_image', 'Лица');
  } else if (!d.face_count) {
    html += `<p class="exif-file-note">${esc(d.note || '')}</p>`;
  }
  return html;
}

function renderShadows(d) {
  const h = Number(state.shadowParams.objectHeight) || 1;
  const l = Number(state.shadowParams.shadowLength) || 1.5;
  const dates = state.results.exif?.dates || {};
  const dtRaw =
    state.shadowDate ||
    dates.DateTimeOriginal ||
    dates.DateTime ||
    dates.DateTimeDigitized ||
    '';
  const dtLocal = exifToDatetimeLocal(dtRaw);
  const el = d.elevation != null ? Number(d.elevation).toFixed(1) : null;

  let html = '';
  if (d.error) html += `<p class="error-text">${esc(d.error)}</p>`;

  html += `<div class="shadow-compact exif-meta-box">
    <div class="shadow-inputs-row">
      <label class="shadow-field"><span>Объект, м</span>
        <input type="number" step="0.1" min="0.1" class="url-input shadow-input" value="${h}" data-shadow-param="h"/></label>
      <label class="shadow-field"><span>Тень, м</span>
        <input type="number" step="0.1" min="0.1" class="url-input shadow-input" value="${l}" data-shadow-param="l"/></label>
      <label class="shadow-field"><span>Дата съёмки</span>
        <input type="datetime-local" class="url-input shadow-input" value="${esc(dtLocal)}" data-shadow-param="dt"/></label>
    </div>`;

  const rows = [];
  if (el != null) rows.push(['Угол', `${el}°`]);
  if (d.latitude_summary) rows.push(['Широты', d.latitude_summary]);
  const exifSun = state.results.exif?.sun;
  if (exifSun && !exifSun.error && el != null && exifSun.elevation != null) {
    const exEl = Number(exifSun.elevation);
    const diff = Math.abs(exEl - Number(el));
    rows.push(['EXIF', diff <= 3 ? `≈ ${exEl.toFixed(1)}°` : `${exEl.toFixed(1)}° (Δ${diff.toFixed(1)}°)`]);
  }
  if (rows.length) {
    html += rows.map(([k, v]) => `<div class="meta-row"><span class="meta-key">${esc(k)}</span><span class="meta-val">${esc(v)}</span></div>`).join('');
  }
  html += `</div>`;

  if (d.geojson) {
    const mapId = getShadowMapContainerId();
    html += `<button type="button" class="btn btn-sm shadow-map-toggle" data-gh="shadow-map-toggle">${state.shadowMapOpen ? 'Скрыть карту' : 'Карта широт'}</button>`;
    if (state.shadowMapOpen) {
      html += `<div id="${mapId}" class="gps-map shadow-locus-map shadow-locus-map--compact"></div>`;
    }
  }

  return html;
}

function renderReverse(d) {
  if (d.error) return `<p class="error-text">${esc(d.error)}</p>`;
  let html = '';
  if (d.note) html += `<p class="exif-file-note">${esc(d.note)}</p>`;
  if (d.mode === 'url' && d.links) {
    html += linkGrid(d.links, REVERSE_LABELS);
  } else if (d.uploadPages) {
    html += section('Загрузить файл вручную', linkGrid(d.uploadPages, REVERSE_LABELS));
  }
  if (!state.imgUrl && state.imgB64) {
    html += `<p class="exif-file-note" style="margin-top:8px">Укажите публичный URL изображения в форме загрузки — появятся ссылки «по URL».</p>`;
  }
  return html || `<p style="color:var(--text4)">Нет ссылок</p>`;
}

function renderWebSearch(d) {
  if (d.error) return `<p class="error-text">${esc(d.error)}</p>`;
  const results = d.results || state.searchResults || [];
  if (!results.length) {
    return `<p style="color:var(--text4)">Нет запросов. Дождитесь EXIF/OCR или перезапустите инструмент.</p>`;
  }
  return results
    .map((block) => {
      const q = block.query || '';
      return `<div style="margin-bottom:12px">
        <div class="section-label" style="color:var(--text3)">${esc(q)}</div>
        ${linkGrid(block.links, SEARCH_ENGINE_LABELS)}
      </div>`;
    })
    .join('');
}

export function renderToolContent(id, d) {
  let inner;
  switch (id) {
    case 'exif':
      inner = renderExif(d);
      break;
    case 'ocr':
      inner = renderOcr(d);
      break;
    case 'qr':
      inner = renderQr(d);
      break;
    case 'forensics':
      inner = renderImageTool(d, 'ela_image', 'ELA');
      break;
    case 'noise':
      inner = renderImageTool(d, 'noise_image', 'Noise');
      break;
    case 'shadows':
      inner = renderShadows(d);
      break;
    case 'stego':
      inner = renderStego(d);
      break;
    case 'faces':
      inner = renderFaces(d);
      break;
    case 'reverse':
      inner = renderReverse(d);
      break;
    case 'websearch':
      inner = renderWebSearch(d);
      break;
    default:
      inner = `<pre style="font-size:11px;color:var(--text2);overflow:auto">${esc(JSON.stringify(d, null, 2))}</pre>`;
  }
  return `<div class="tool-content" style="margin-top:0">${inner}</div>`;
}
