import { IC, CAT_ICONS, TOOL_ICONS } from './icons.js';
import { TOOLS, CATEGORIES } from './tools-config.js';
import { state, hasImg } from './state.js';
import { renderToolContent, getToolCardSummary } from './tool-render.js';
import { esc } from './utils.js';
import { remountExifMapFromState, remountShadowMapFromState } from './map.js';

let _renderRaf = 0;
let _uploadPreviewMounted = false;
let _pendingRender = { light: false, tools: null, maps: false };

function patchUploadProgress() {
  const anyRunning = state.running.size > 0;
  const progress = state.doneSet.size + state.errSet.size;
  const status = document.querySelector('.preview-status');
  const runBtn = document.querySelector('[data-gh="run-all"]');
  const progressWrap = document.querySelector('.progress-wrap');
  if (status) {
    status.textContent = anyRunning
      ? `${state.running.size} инструментов…`
      : state.doneSet.size
        ? `${state.doneSet.size} из ${TOOLS.length} готово`
        : 'Запуск…';
  }
  if (runBtn) {
    runBtn.disabled = anyRunning;
    runBtn.innerHTML = anyRunning
      ? `<span class="spinner">${IC.loader}</span> Анализ…`
      : `${IC.play} Запустить`;
  }
  if (progressWrap) {
    if (!anyRunning) {
      progressWrap.remove();
      return;
    }
    const fill = progressWrap.querySelector('.progress-fill');
    const pt = progressWrap.querySelector('.progress-text');
    if (fill) fill.style.width = `${(progress / TOOLS.length) * 100}%`;
    if (pt) {
      const spans = pt.querySelectorAll('span');
      if (spans[0]) {
        spans[0].textContent = `${state.doneSet.size} готово${state.errSet.size ? `, ${state.errSet.size} ошибок` : ''}`;
      }
      if (spans[1]) spans[1].textContent = `${Math.round((progress / TOOLS.length) * 100)}%`;
    }
  } else if (anyRunning && state.imgSrc) {
    renderUpload();
  }
}

export function renderHeader() {
  const br = document.getElementById('badgeRunning');
  const bd = document.getElementById('badgeDone');
  const be = document.getElementById('btnExport');
  const bej = document.getElementById('btnExportJson');
  if (!br || !bd) return;
  const progress = state.doneSet.size + state.errSet.size;

  br.style.display = state.running.size > 0 ? 'inline-flex' : 'none';
  if (state.running.size > 0) br.textContent = `${state.running.size} активны`;

  bd.style.display = state.doneSet.size > 0 ? 'inline-flex' : 'none';
  if (state.doneSet.size > 0) bd.textContent = `${state.doneSet.size}/${TOOLS.length}`;

  const showExport = progress > 0 ? 'inline-flex' : 'none';
  if (be) be.style.display = showExport;
  if (bej) bej.style.display = showExport;
}

export function renderUpload() {
  const el = document.getElementById('uploadArea');
  if (!el) return;
  const anyRunning = state.running.size > 0;
  const progress = state.doneSet.size + state.errSet.size;

  if (!state.imgSrc) {
    el.innerHTML = `
      <div class="upload-area" id="dropZone">
        <input type="file" id="fileInput" accept="image/*" style="display:none"/>
        <div class="upload-icon">${IC.upload}</div>
        <p class="upload-title">Перетащите фото или нажмите для выбора</p>
        <p class="upload-sub">PNG, JPG, WebP · EXIF, анализ, OCR, обратный поиск</p>
        <div class="url-row" style="margin-top:14px;display:flex;gap:8px;flex-wrap:wrap;justify-content:center">
          <input type="url" id="imageUrlInput" class="url-input" placeholder="Или публичный URL изображения (для reverse search)" style="flex:1;min-width:200px;max-width:420px"/>
          <button type="button" class="btn btn-emerald" id="btnLoadUrl">По URL</button>
        </div>
      </div>`;
    return;
  }

  el.innerHTML = `
    <div class="preview">
      <div class="preview-img-wrap">
        <img src="${state.imgSrc}" class="preview-img" alt=""/>
        <button type="button" class="preview-close" data-gh="clear">✕</button>
      </div>
      <div class="preview-info">
        <p class="preview-title">${state.urlMode ? 'Изображение по URL' : 'Изображение загружено'}</p>
        <p class="preview-status">${anyRunning ? `${state.running.size} инструментов…` : state.doneSet.size ? `${state.doneSet.size} из ${TOOLS.length} готово` : 'Запуск…'}</p>
        ${state.imgUrl ? `<p class="exif-file-note" style="margin-top:4px">${esc(state.imgUrl)}</p>` : ''}
      </div>
      <div class="preview-actions">
        <button type="button" class="btn btn-emerald" data-gh="run-all" ${anyRunning ? 'disabled' : ''}>
          ${anyRunning ? `<span class="spinner">${IC.loader}</span>` : IC.play}
          ${anyRunning ? 'Анализ…' : 'Запустить'}
        </button>
        <button type="button" class="btn" data-gh="clear">Сброс</button>
      </div>
    </div>
    ${anyRunning ? `
      <div class="progress-wrap">
        <div class="progress-bar"><div class="progress-fill" style="width:${(progress / TOOLS.length) * 100}%"></div></div>
        <div class="progress-text">
          <span>${state.doneSet.size} готово${state.errSet.size ? `, ${state.errSet.size} ошибок` : ''}</span>
          <span>${Math.round((progress / TOOLS.length) * 100)}%</span>
        </div>
      </div>` : ''}`;
}

function renderCard(tool) {
  const isR = state.running.has(tool.id);
  const isD = state.doneSet.has(tool.id);
  const isE = state.errSet.has(tool.id);
  const isC = state.collapsedSet.has(tool.id);
  const d = state.results[tool.id];

  if (!isR && !isD && !isE && !d) return '';

  const hasSoftErr = isD && d?.error;
  const cls = isR ? 'running' : isD ? (hasSoftErr ? 'done warn' : 'done') : isE ? 'error' : 'idle';
  const wideCls = tool.id === 'exif' ? ' tool-card--wide' : '';
  const iconCls = isR ? 'running' : isD ? (hasSoftErr ? 'done' : 'done') : isE ? 'error' : 'idle';

  let iconHtml;
  if (isR) iconHtml = `<span class="spinner" style="color:var(--amber)">${IC.loader}</span>`;
  else if (isD) iconHtml = `<span style="color:var(--emerald)">${IC.check}</span>`;
  else if (isE) iconHtml = `<span style="color:var(--red)">${IC.xcirc}</span>`;
  else iconHtml = `<span style="color:${tool.color}">${TOOL_ICONS[tool.id]}</span>`;

  const showBody = (isD || (d && d.error)) && !isC && d;
  const content = showBody ? renderToolContent(tool.id, d) : '';
  const summary = isD && !isR && !d?.error ? getToolCardSummary(tool.id, d) : '';
  const errorHtml =
    isE && d?.error && !isD
      ? `<div style="padding:4px 12px 8px;border-top:1px solid rgba(255,255,255,0.04)"><p style="font-size:10px;color:var(--red)">${esc(d.error)}</p></div>`
      : '';

  return `
    <div class="tool-card ${cls}${wideCls}" data-tool-id="${tool.id}">
      <div class="tool-header">
        <div class="tool-icon ${iconCls}">${iconHtml}</div>
        <span class="tool-name">${tool.name}</span>
        ${summary ? `<span class="tool-summary">${esc(summary)}</span>` : ''}
        ${isR ? '<span class="tool-status">анализ...</span>' : ''}
        <div class="tool-actions">
          ${isD ? `<button type="button" class="tool-btn" data-gh="collapse" data-tool="${tool.id}">${isC ? IC.chevDown : IC.chevUp}</button>` : ''}
          ${isD || isE ? `<button type="button" class="tool-btn" data-gh="retry" data-tool="${tool.id}" ${isR ? 'disabled' : ''}>${IC.retry}</button>` : ''}
        </div>
      </div>
      ${content}
      ${errorHtml}
    </div>`;
}

export function renderMain() {
  const el = document.getElementById('mainArea');
  if (!el) return;

  if (!hasImg()) {
    el.innerHTML = `<div class="overview-grid">${CATEGORIES.map(
      (cat) => `
      <div class="overview-card">
        <div class="overview-card-header">
          <span class="category-icon">${CAT_ICONS[cat]}</span>
          <span>${cat}</span>
          <span class="ov-count">${TOOLS.filter((t) => t.cat === cat).length}</span>
        </div>
        ${TOOLS.filter((t) => t.cat === cat)
          .map(
            (t) => `
          <div class="overview-item">
            <span class="oi-icon" style="color:${t.color}">${TOOL_ICONS[t.id]}</span>
            <div><p class="oi-name">${t.name}</p><p class="oi-desc">${esc(t.desc)}</p></div>
          </div>`
          )
          .join('')}
      </div>`
    ).join('')}</div>`;
    return;
  }

  el.innerHTML = `<div>${CATEGORIES.map((cat) => {
    const catTools = TOOLS.filter((t) => t.cat === cat);
    const hasAny = catTools.some(
      (t) => state.running.has(t.id) || state.doneSet.has(t.id) || state.errSet.has(t.id) || state.results[t.id]
    );
    if (!hasAny) return '';
    const catDone = catTools.filter((t) => state.doneSet.has(t.id)).length;
    const catRunning = catTools.filter((t) => state.running.has(t.id)).length;
    const catErrors = catTools.filter((t) => state.errSet.has(t.id)).length;
    return `
      <div class="category">
        <div class="category-header">
          <span class="category-icon">${CAT_ICONS[cat]}</span>
          <span class="category-name">${cat}</span>
          ${catRunning ? `<span style="font-size:9px;color:var(--amber)" class="pulse">${catRunning} выполняется</span>` : ''}
          ${catDone ? `<span class="category-badge">${catDone}/${catTools.length}</span>` : ''}
          ${catErrors ? `<span style="font-size:8px;padding:0 4px;border-radius:9999px;border:1px solid rgba(239,68,68,0.2);color:var(--red)">${catErrors}</span>` : ''}
        </div>
        <div class="tools-grid">${catTools.map((t) => renderCard(t)).join('')}</div>
      </div>`;
  }).join('')}</div>`;
}

function upsertToolCard(toolId) {
  const tool = TOOLS.find((t) => t.id === toolId);
  if (!tool) return false;
  const html = renderCard(tool);
  const existing = document.querySelector(`[data-tool-id="${toolId}"]`);
  if (existing) {
    if (html) existing.outerHTML = html;
    else existing.remove();
    return true;
  }
  return false;
}

function renderAllNow() {
  const opts = _pendingRender;
  _pendingRender = { light: false, tools: null, maps: false };

  renderHeader();
  if (!state.imgSrc) {
    _uploadPreviewMounted = false;
    renderUpload();
  } else if (_uploadPreviewMounted && document.querySelector('.preview')) {
    patchUploadProgress();
  } else {
    renderUpload();
    _uploadPreviewMounted = true;
  }

  const toolIds = opts.tools;
  if (toolIds?.length) {
    let allOk = true;
    for (const id of toolIds) {
      if (!upsertToolCard(id)) allOk = false;
    }
    if (!allOk) renderMain();
  } else if (!opts.light) {
    renderMain();
  } else if (!document.getElementById('mainArea')?.querySelector('[data-tool-id]')) {
    renderMain();
  }

  if (opts.maps || !opts.light) {
    remountExifMapFromState(state.results.exif);
    if (state.shadowMapOpen) remountShadowMapFromState(state.results.shadows);
  }
}

/** Сглаживает частые перерисовки при параллельном анализе (без мигания всей страницы). */
export function scheduleRender(patch = {}) {
  if (patch.light) _pendingRender.light = true;
  if (patch.maps) _pendingRender.maps = true;
  if (patch.tools?.length) {
    const cur = _pendingRender.tools || [];
    _pendingRender.tools = [...new Set([...cur, ...patch.tools])];
  }
  if (_renderRaf) cancelAnimationFrame(_renderRaf);
  _renderRaf = requestAnimationFrame(() => {
    _renderRaf = 0;
    renderAllNow();
  });
}

export function renderAll() {
  scheduleRender();
}
