/**
 * GeoHunter — точка входа раздела «Фото» (ES modules).
 */
import { API } from './modules/api.js';
import { state, resetAnalysis, hasImg } from './modules/state.js';
import {
  closeFullscreenMap,
  destroyPhotoMaps,
  openFullscreenMap,
  initPhotoCyberMaps,
  remountShadowMapFromState,
} from './modules/map.js';
import {
  setRender,
  runAllTools,
  rerunTool,
  runExif,
  loadExiftoolFull,
} from './modules/tool-runners.js';
import { renderAll, scheduleRender } from './modules/ui-render.js';
import { isHttpUrl, datetimeLocalToExif } from './modules/utils.js';

setRender(scheduleRender);

function onFile(file) {
  if (!file) return;
  state.uploadFileName = file.name;
  const reader = new FileReader();
  reader.onload = (e) => {
    state.imgSrc = e.target.result;
    state.imgB64 = e.target.result.split(',')[1];
    state.imgUrl = '';
    state.urlMode = false;
    resetAnalysis();
    renderAll();
    setTimeout(() => void runAllTools(), 300);
  };
  reader.readAsDataURL(file);
}

function loadFromUrl() {
  const input = document.getElementById('imageUrlInput');
  const url = (input?.value || '').trim();
  if (!isHttpUrl(url)) {
    alert('Укажите корректный http(s) URL изображения');
    return;
  }
  state.imgUrl = url;
  state.imgSrc = url;
  state.imgB64 = null;
  state.urlMode = true;
  state.uploadFileName = null;
  resetAnalysis();
  renderAll();
  setTimeout(() => void runAllTools(), 300);
}

function clearAll() {
  state.imgSrc = null;
  state.imgB64 = null;
  state.imgUrl = '';
  state.uploadFileName = null;
  state.urlMode = false;
  resetAnalysis();
  destroyPhotoMaps();
  const urlInput = document.getElementById('imageUrlInput');
  if (urlInput) urlInput.value = '';
  renderAll();
}

async function downloadCleanImage() {
  if (!state.imgB64) {
    alert('Нужен загруженный файл (не URL).');
    return;
  }
  try {
    const r = await fetch(`${API}/api/exif/strip`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ imageBase64: state.imgB64 }),
    });
    if (!r.ok) {
      const j = await r.json().catch(() => ({}));
      throw new Error(j.error || 'Ошибка');
    }
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = blob.type === 'image/jpeg' ? 'clean.jpg' : 'clean.png';
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    alert('Не удалось удалить метаданные: ' + (e.message || e));
  }
}

async function exportReport() {
  if (!Object.keys(state.results).length) {
    alert('Нет данных');
    return;
  }
  let report = '# GeoHunter Report\n\n';
  for (const [id, data] of Object.entries(state.results)) {
    report += `## ${id}\n\n\`\`\`json\n${JSON.stringify(data, null, 2)}\n\`\`\`\n\n`;
  }
  const blob = new Blob([report], { type: 'text/markdown' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'geohunter-report.md';
  a.click();
}

async function exportJson() {
  if (!Object.keys(state.results).length) {
    alert('Нет данных');
    return;
  }
  const payload = {
    geoHunterExport: 2,
    imageUrl: state.imgUrl,
    uploadFileName: state.uploadFileName,
    results: state.results,
    searchResults: state.searchResults,
    reverseLinks: state.results.reverse,
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'geohunter-export.json';
  a.click();
}

async function handleGhAction(action, el) {
  switch (action) {
    case 'toggle-exiftool':
      state.exifAdvanced = !state.exifAdvanced;
      state.exiftoolFull = null;
      await runExif();
      break;
    case 'toggle-exif-tags':
      state.exifShowAllTags = !state.exifShowAllTags;
      if (state.exifShowAllTags) await loadExiftoolFull();
      renderAll();
      break;
    case 'strip-exif':
      await downloadCleanImage();
      break;
    case 'exif-filter':
      state.exiftoolFullQuery = el.value || '';
      renderAll();
      break;
    case 'shadow-map-toggle':
      state.shadowMapOpen = !state.shadowMapOpen;
      renderAll();
      if (state.shadowMapOpen) remountShadowMapFromState(state.results.shadows);
      break;
    case 'zoom-img':
      window.open(el.src, '_blank');
      break;
    case 'open-full-map': {
      const lat = parseFloat(el.dataset.lat);
      const lon = parseFloat(el.dataset.lon);
      if (Number.isFinite(lat) && Number.isFinite(lon)) openFullscreenMap(lat, lon);
      break;
    }
    case 'run-all':
      await runAllTools();
      break;
    case 'clear':
      clearAll();
      break;
    case 'retry': {
      const id = el.dataset.tool;
      if (id) await rerunTool(id);
      break;
    }
    case 'collapse': {
      const id = el.dataset.tool;
      if (id) {
        if (state.collapsedSet.has(id)) state.collapsedSet.delete(id);
        else state.collapsedSet.add(id);
        renderAll();
        if (id === 'exif' && state.results.exif) {
          queueMicrotask(() => initPhotoCyberMaps(state.results.exif));
        }
      }
      break;
    }
    default:
      break;
  }
}

let shadowRerunTimer = null;

function scheduleShadowRerun() {
  clearTimeout(shadowRerunTimer);
  shadowRerunTimer = setTimeout(() => void rerunTool('shadows'), 800);
}

function bindEvents() {
  document.addEventListener('click', (e) => {
    const t = e.target.closest('[data-gh]');
    if (t) {
      e.preventDefault();
      void handleGhAction(t.dataset.gh, t);
      return;
    }
    if (e.target.closest('#dropZone') && e.target.id !== 'imageUrlInput' && e.target.id !== 'btnLoadUrl') {
      document.getElementById('fileInput')?.click();
    }
  });

  document.addEventListener('change', (e) => {
    if (e.target.id === 'fileInput' && e.target.files?.[0]) onFile(e.target.files[0]);
    const sp = e.target.dataset?.shadowParam;
    if (sp === 'h') {
      state.shadowParams.objectHeight = parseFloat(e.target.value) || 1;
      scheduleShadowRerun();
    } else if (sp === 'l') {
      state.shadowParams.shadowLength = parseFloat(e.target.value) || 1.5;
      scheduleShadowRerun();
    } else if (sp === 'dt') {
      state.shadowDate = datetimeLocalToExif(e.target.value);
      scheduleShadowRerun();
    }
  });

  document.addEventListener('input', (e) => {
    if (e.target.dataset?.gh === 'exif-filter') void handleGhAction('exif-filter', e.target);
  });

  const uploadArea = document.getElementById('uploadArea');
  if (uploadArea) {
    uploadArea.addEventListener('dragover', (e) => {
      e.preventDefault();
      document.getElementById('dropZone')?.classList.add('dragging');
    });
    uploadArea.addEventListener('dragleave', () => {
      document.getElementById('dropZone')?.classList.remove('dragging');
    });
    uploadArea.addEventListener('drop', (e) => {
      e.preventDefault();
      document.getElementById('dropZone')?.classList.remove('dragging');
      if (e.dataTransfer?.files?.[0]) onFile(e.dataTransfer.files[0]);
    });
  }

  document.getElementById('btnLoadUrl')?.addEventListener('click', (e) => {
    e.preventDefault();
    loadFromUrl();
  });

  document.getElementById('btn-close-full-map')?.addEventListener('click', () => {
    closeFullscreenMap(state.results.exif);
  });
}

window.GeoHunter = {
  runAllParallel: runAllTools,
  rerunTool,
  clearAll,
  onFile,
  exportReport,
  exportJson,
  downloadCleanImage,
  openMap: openFullscreenMap,
  render: renderAll,
  get state() {
    return state;
  },
};

document.addEventListener('DOMContentLoaded', () => {
  bindEvents();
  renderAll();
});
