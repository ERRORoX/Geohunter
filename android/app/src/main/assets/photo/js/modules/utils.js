export function esc(s) {
  const el = document.createElement('div');
  el.textContent = s == null ? '' : String(s);
  return el.innerHTML;
}

export function isHttpUrl(s) {
  try {
    const u = new URL(String(s));
    return u.protocol === 'http:' || u.protocol === 'https:';
  } catch {
    return false;
  }
}

/** EXIF "2024:03:15 12:00:00" → value для input datetime-local */
export function exifToDatetimeLocal(s) {
  if (!s) return '';
  const m = String(s).match(/^(\d{4})[:\-](\d{2})[:\-](\d{2})[ T](\d{2}):(\d{2})/);
  if (!m) return '';
  return `${m[1]}-${m[2]}-${m[3]}T${m[4]}:${m[5]}`;
}

/** datetime-local → EXIF-строка */
export function datetimeLocalToExif(s) {
  if (!s) return '';
  const m = String(s).match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/);
  if (!m) return '';
  return `${m[1]}:${m[2]}:${m[3]} ${m[4]}:${m[5]}:00`;
}

/** Нормализованные координаты из объекта gps API (числа или строки DMS). */
export function parseGpsCoords(gps) {
  if (!gps || typeof gps !== 'object') return null;
  const tryPair = (lat, lon) => {
    const la = Number(lat);
    const lo = Number(lon);
    if (Number.isFinite(la) && Number.isFinite(lo) && Math.abs(la) <= 90 && Math.abs(lo) <= 180) {
      return { lat: la, lon: lo };
    }
    return null;
  };
  let p = tryPair(gps.latitude ?? gps.lat, gps.longitude ?? gps.lon);
  if (p) return p;
  const pos = gps.GPSPosition ?? gps.position;
  if (pos != null) {
    const s = String(pos).trim();
    const m = s.match(/^([-+]?\d+(?:\.\d+)?)\s*[,;]\s*([-+]?\d+(?:\.\d+)?)/);
    if (m) {
      p = tryPair(m[1], m[2]);
      if (p) return p;
    }
  }
  return null;
}

export function exifTagValue(v) {
  if (v == null) return '';
  if (typeof v === 'object' && v !== null) {
    if ('val' in v) return String(v.val);
    if ('value' in v) return String(v.value);
    try {
      return JSON.stringify(v);
    } catch {
      return String(v);
    }
  }
  return String(v);
}
