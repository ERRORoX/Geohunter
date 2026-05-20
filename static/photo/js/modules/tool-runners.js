import { postJson, postJsonAllowFail } from './api.js';
import { OFFLINE_EP } from './tools-config.js';
import {
  state,
  imgPayload,
  markRunning,
  markDone,
  markError,
  hasImg,
} from './state.js';

let renderFn = () => {};

export function setRender(fn) {
  renderFn = fn;
}

function pickShadowDate() {
  const d = state.results.exif?.dates || {};
  return (
    state.shadowDate ||
    d.DateTimeOriginal ||
    d.DateTime ||
    d.DateTimeDigitized ||
    ''
  );
}

async function finish(id, promise) {
  markRunning(id);
  renderFn({ light: true, tools: [id] });
  try {
    const data = await promise;
    if (data && data.success === false) {
      markDone(id, { ...data, error: data.error || 'Ошибка' });
    } else {
      markDone(id, data);
    }
  } catch (e) {
    markError(id, e.message || String(e));
  }
  renderFn({ tools: [id], maps: id === 'exif' || id === 'shadows' });
  return state.results[id];
}

export async function runExif() {
  if (!state.imgB64) {
    markError('exif', 'EXIF доступен только при загрузке файла');
    renderFn({ tools: ['exif'] });
    return state.results.exif;
  }
  return finish(
    'exif',
    postJson('/api/exif', {
      imageBase64: state.imgB64,
      exiftool: !!state.exifAdvanced,
      ...(state.uploadFileName ? { filename: state.uploadFileName } : {}),
    })
  );
}

export async function loadExiftoolFull() {
  if (!state.imgB64 || !state.exifAdvanced) return null;
  if (state.exiftoolFull) return state.exiftoolFull;
  state.exiftoolFullLoading = true;
  state.exiftoolFullErr = '';
  renderFn({ tools: ['exif'] });
  try {
    const d = await postJson('/api/exif/exiftool/json', {
      imageBase64: state.imgB64,
      exiftool: true,
      ...(state.uploadFileName ? { filename: state.uploadFileName } : {}),
    });
    state.exiftoolFull = d.record || {};
    state.exiftoolFullLoading = false;
    renderFn({ tools: ['exif'], maps: true });
    return state.exiftoolFull;
  } catch (e) {
    state.exiftoolFullErr = e.message || String(e);
    state.exiftoolFullLoading = false;
    renderFn({ tools: ['exif'] });
    return null;
  }
}

export async function runOfflineTool(id, endpoint, extraBody = {}) {
  if (id === 'reverse') {
    return finish(id, postJsonAllowFail(endpoint, { imageUrl: state.imgUrl || '' }));
  }
  if (id === 'websearch') {
    return finish(
      id,
      postJsonAllowFail(endpoint, {
        exif: state.results.exif || null,
        ocr: state.results.ocr || null,
      })
    ).then((data) => {
      if (data?.results) state.searchResults = data.results;
      return data;
    });
  }
  if (!state.imgB64) {
    markError(id, 'Загрузите файл изображения');
    renderFn({ tools: [id] });
    return state.results[id];
  }

  let body = { ...imgPayload(), ...extraBody };
  if (id === 'shadows') {
    body = {
      objectHeight: state.shadowParams.objectHeight,
      shadowLength: state.shadowParams.shadowLength,
      dt: pickShadowDate(),
    };
  }
  return finish(id, postJson(endpoint, body));
}

export async function runAllTools() {
  if (!hasImg()) return;

  if (state.imgB64) {
    await runExif();
    if (state.exifAdvanced && state.exifShowAllTags) {
      await loadExiftoolFull();
    }
  } else {
    markError('exif', 'EXIF по URL недоступен — загрузите файл');
    renderFn({ tools: ['exif'] });
  }

  const fileTools = ['ocr', 'qr', 'forensics', 'noise', 'stego', 'faces'];
  await Promise.allSettled([
    runOfflineTool('reverse', OFFLINE_EP.reverse),
    ...(state.imgB64 ? fileTools.map((id) => runOfflineTool(id, OFFLINE_EP[id])) : []),
  ]);

  await runOfflineTool('websearch', OFFLINE_EP.websearch);

  if (state.imgB64) {
    await runOfflineTool('shadows', OFFLINE_EP.shadows);
  }
}

export function rerunTool(id) {
  if (id === 'exif') {
    state.exiftoolFull = null;
    return runExif();
  }
  const ep = OFFLINE_EP[id];
  if (ep) return runOfflineTool(id, ep);
}
