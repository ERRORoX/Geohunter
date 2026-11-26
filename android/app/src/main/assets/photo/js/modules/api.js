const API = window.location.origin;

let nativeRequestSequence = 0;
const nativePending = new Map();

if (typeof window !== 'undefined' && !window.__geoHunterNativeResolve) {
  window.__geoHunterNativeResolve = (id, serialized) => {
    const pending = nativePending.get(id);
    if (!pending) return;
    nativePending.delete(id);
    try {
      const data = JSON.parse(serialized);
      if (data && data.success === false && pending.rejectOnFailure) {
        pending.reject(new Error(data.error || 'Ошибка локального API'));
      } else {
        pending.resolve(data);
      }
    } catch (error) {
      pending.reject(error);
    }
  };
}

function nativePostJson(path, body, rejectOnFailure) {
  return new Promise((resolve, reject) => {
    const bridge = window.GeoHunterNative;
    if (!bridge || typeof bridge.postJson !== 'function') {
      reject(new Error('Локальный API GeoHunter недоступен.'));
      return;
    }
    const id = `gh-${++nativeRequestSequence}`;
    nativePending.set(id, { resolve, reject, rejectOnFailure });
    try {
      bridge.postJson(path, JSON.stringify(body || {}), id);
    } catch (error) {
      nativePending.delete(id);
      reject(error);
    }
  });
}

async function parseResponse(r) {
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    throw new Error(data.error || data.message || `HTTP ${r.status}`);
  }
  return data;
}

/** POST JSON: сохраняет исходный контракт веб-версии и использует локальный Android API в APK. */
export async function postJson(path, body) {
  if (window.GeoHunterNative) {
    const data = await nativePostJson(path, body, false);
    if (data.success === false) return { ...data, error: data.error || 'Ошибка запроса' };
    return data;
  }
  const r = await fetch(API + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await parseResponse(r);
  if (data.success === false) return { ...data, error: data.error || 'Ошибка запроса' };
  return data;
}

export async function postJsonAllowFail(path, body) {
  if (window.GeoHunterNative) return nativePostJson(path, body, false);
  const r = await fetch(API + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return parseResponse(r);
}

export { API };

/** Сохраняет файл в системную папку Downloads/GeoHunter на Android. */
export function saveNativeFile(fileName, mimeType, base64) {
  return new Promise((resolve, reject) => {
    const bridge = window.GeoHunterNative;
    if (!bridge || typeof bridge.saveBase64 !== 'function') {
      reject(new Error('Нативное сохранение файлов недоступно.'));
      return;
    }
    const id = `gh-save-${++nativeRequestSequence}`;
    nativePending.set(id, {
      rejectOnFailure: true,
      resolve,
      reject,
    });
    try {
      bridge.saveBase64(fileName, mimeType, base64, id);
    } catch (error) {
      nativePending.delete(id);
      reject(error);
    }
  });
}
