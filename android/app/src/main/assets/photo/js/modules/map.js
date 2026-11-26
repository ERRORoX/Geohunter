import { parseGpsCoords } from './utils.js';

let photoMapExif = null;
let photoMapGeo = null;
let photoMapShadow = null;
let photoMapFullscreen = null;
let photoMarkerExif = null;
let photoMarkerGeo = null;
let photoMarkerFullscreen = null;

const _maplibreWaiters = [];
let _maplibreInjecting = false;

/** Как в GeoHunter/static/photo/js/photo.js — Liberty + затемнение канваса в photo.css */
const PHOTO_MAP_STYLE_URL = 'https://tiles.openfreemap.org/styles/liberty';
const EXIF_MAP_ID = 'photo-leaflet-exif';
const FULLSCREEN_MAP_ID = 'photo-leaflet-fullscreen';

let _shadowMapKey = '';

export function destroyPhotoMaps() {
  if (photoMarkerExif) { try { photoMarkerExif.remove(); } catch (_) {} photoMarkerExif = null; }
  if (photoMarkerGeo) { try { photoMarkerGeo.remove(); } catch (_) {} photoMarkerGeo = null; }
  if (photoMapExif) { try { photoMapExif.remove(); } catch (_) {} photoMapExif = null; }
  if (photoMapGeo) { try { photoMapGeo.remove(); } catch (_) {} photoMapGeo = null; }
  if (photoMapShadow) { try { photoMapShadow.remove(); } catch (_) {} photoMapShadow = null; }
  if (photoMarkerFullscreen) { try { photoMarkerFullscreen.remove(); } catch (_) {} photoMarkerFullscreen = null; }
  if (photoMapFullscreen) { try { photoMapFullscreen.remove(); } catch (_) {} photoMapFullscreen = null; }
  _shadowMapKey = '';
}

/** Сброс inline-карты EXIF при частичной перерисовке карточки. */
export function resetExifInlineMap() {
  if (photoMarkerExif) { try { photoMarkerExif.remove(); } catch (_) {} photoMarkerExif = null; }
  if (photoMapExif) { try { photoMapExif.remove(); } catch (_) {} photoMapExif = null; }
}

function loadMapLibre(cb) {
  if (typeof maplibregl !== 'undefined') { cb(); return; }
  _maplibreWaiters.push(cb);
  if (_maplibreInjecting) return;
  _maplibreInjecting = true;
  if (!document.querySelector('link[href*="maplibre-gl"][rel="stylesheet"]')) {
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = 'https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css';
    link.crossOrigin = 'anonymous';
    document.head.appendChild(link);
  }
  const script = document.createElement('script');
  script.src = 'https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js';
  script.crossOrigin = 'anonymous';
  script.onload = () => {
    const q = _maplibreWaiters.splice(0);
    q.forEach((fn) => { try { fn(); } catch (_) {} });
    _maplibreInjecting = false;
  };
  script.onerror = () => {
    _maplibreInjecting = false;
    console.warn('MapLibre не загрузился — проверьте интернет');
  };
  document.head.appendChild(script);
}

function pinEl() {
  const wrap = document.createElement('div');
  wrap.className = 'photo-map-pin';
  wrap.setAttribute('aria-hidden', 'true');
  wrap.innerHTML =
    '<span class="photo-map-pin-core"></span><span class="photo-map-pin-pulse"></span><span class="photo-map-pin-ring"></span>';
  return wrap;
}

/** Тот же mount, что mountPhotoCyberMap в эталонном GeoHunter. */
export function mountPhotoMap(containerId, lat, lon, slot = 'exif') {
  loadMapLibre(() => {
    const el = document.getElementById(containerId);
    if (!el || typeof maplibregl === 'undefined') return;
    const prevMap =
      slot === 'geo' ? photoMapGeo : slot === 'fullscreen' ? photoMapFullscreen : photoMapExif;
    const prevMarker =
      slot === 'geo' ? photoMarkerGeo : slot === 'fullscreen' ? photoMarkerFullscreen : photoMarkerExif;
    if (prevMarker) { try { prevMarker.remove(); } catch (_) {} }
    if (prevMap) { try { prevMap.remove(); } catch (_) {} }
    if (slot === 'geo') { photoMapGeo = null; photoMarkerGeo = null; }
    else if (slot === 'fullscreen') { photoMapFullscreen = null; photoMarkerFullscreen = null; }
    else { photoMapExif = null; photoMarkerExif = null; }

    const map = new maplibregl.Map({
      container: el,
      style: PHOTO_MAP_STYLE_URL,
      center: [lon, lat],
      zoom: 15.35,
      pitch: 48,
      bearing: -20,
      attributionControl: true,
      maxPitch: 85,
      antialias: true,
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: true }), 'top-right');
    map.addControl(new maplibregl.FullscreenControl({ container: el }), 'top-right');

    if (slot === 'geo') photoMapGeo = map;
    else if (slot === 'fullscreen') photoMapFullscreen = map;
    else photoMapExif = map;

    map.once('load', () => {
      const active =
        slot === 'geo' ? photoMapGeo : slot === 'fullscreen' ? photoMapFullscreen : photoMapExif;
      if (active !== map) return;
      const marker = new maplibregl.Marker({ element: pinEl(), anchor: 'center' })
        .setLngLat([lon, lat])
        .addTo(map);
      if (slot === 'geo') photoMarkerGeo = marker;
      else if (slot === 'fullscreen') photoMarkerFullscreen = marker;
      else photoMarkerExif = marker;
      try { map.resize(); } catch (_) {}
    });

    requestAnimationFrame(() => { try { map.resize(); } catch (_) {} });
    setTimeout(() => { try { map.resize(); } catch (_) {} }, 280);
  });
}

/** Как initPhotoCyberMaps() в эталонном GeoHunter. */
export function initPhotoCyberMaps(exifResult) {
  const gps = exifResult?.gps;
  const coords = parseGpsCoords(gps);
  if (!coords) return;
  const el = document.getElementById(EXIF_MAP_ID);
  if (!el || !el.isConnected) return;
  mountPhotoMap(EXIF_MAP_ID, coords.lat, coords.lon, 'exif');
}

export function getExifMapContainerId() {
  return EXIF_MAP_ID;
}

/** @deprecated используйте initPhotoCyberMaps */
export function remountExifMapFromState(exifResult) {
  initPhotoCyberMaps(exifResult);
}

export function openFullscreenMap(lat, lon) {
  const box = document.getElementById('map-container');
  if (box) box.style.display = 'block';
  mountPhotoMap(FULLSCREEN_MAP_ID, lat, lon, 'fullscreen');
}

export function closeFullscreenMap(exifResult) {
  const box = document.getElementById('map-container');
  if (box) box.style.display = 'none';
  if (photoMarkerFullscreen) { try { photoMarkerFullscreen.remove(); } catch (_) {} photoMarkerFullscreen = null; }
  if (photoMapFullscreen) { try { photoMapFullscreen.remove(); } catch (_) {} photoMapFullscreen = null; }
  initPhotoCyberMaps(exifResult);
}

const SHADOW_MAP_ID = 'gh-shadow-locus-map';

export function getShadowMapContainerId() {
  return SHADOW_MAP_ID;
}

function boundsFromGeoJson(geojson) {
  const coords = [];
  for (const f of geojson?.features || []) {
    const g = f.geometry;
    if (g?.type === 'LineString') coords.push(...g.coordinates);
  }
  if (!coords.length) return null;
  let minLon = 180;
  let maxLon = -180;
  let minLat = 90;
  let maxLat = -90;
  for (const [lon, lat] of coords) {
    minLon = Math.min(minLon, lon);
    maxLon = Math.max(maxLon, lon);
    minLat = Math.min(minLat, lat);
    maxLat = Math.max(maxLat, lat);
  }
  return [
    [minLon, minLat],
    [maxLon, maxLat],
  ];
}

export function mountShadowLocusMap(containerId, geojson) {
  if (!geojson?.features?.length) return;
  loadMapLibre(() => {
    const el = document.getElementById(containerId);
    if (!el || typeof maplibregl === 'undefined') return;
    if (photoMapShadow) {
      try { photoMapShadow.remove(); } catch (_) {}
      photoMapShadow = null;
    }

    const map = new maplibregl.Map({
      container: el,
      style: PHOTO_MAP_STYLE_URL,
      center: [0, 20],
      zoom: 1.2,
      attributionControl: true,
    });
    photoMapShadow = map;
    map.addControl(new maplibregl.NavigationControl({ showCompass: true }), 'top-right');

    map.once('load', () => {
      if (photoMapShadow !== map) return;
      map.addSource('shadow-locus', { type: 'geojson', data: geojson });
      map.addLayer({
        id: 'shadow-locus-glow',
        type: 'line',
        source: 'shadow-locus',
        paint: {
          'line-color': '#f59e0b',
          'line-width': 6,
          'line-opacity': 0.2,
          'line-blur': 2,
        },
      });
      map.addLayer({
        id: 'shadow-locus-line',
        type: 'line',
        source: 'shadow-locus',
        paint: {
          'line-color': '#f59e0b',
          'line-width': 2.5,
          'line-opacity': 0.9,
        },
      });
      const b = boundsFromGeoJson(geojson);
      if (b) {
        try { map.fitBounds(b, { padding: 36, maxZoom: 4, duration: 0 }); } catch (_) {}
      }
      try { map.resize(); } catch (_) {}
    });
    requestAnimationFrame(() => { try { map.resize(); } catch (_) {} });
    setTimeout(() => { try { map.resize(); } catch (_) {} }, 280);
  });
}

export function remountShadowMapFromState(shadowResult) {
  const geojson = shadowResult?.geojson;
  if (!geojson) return;
  let key = '';
  try { key = JSON.stringify(geojson); } catch { key = String(Date.now()); }
  if (key === _shadowMapKey && photoMapShadow) return;
  _shadowMapKey = key;
  const run = () => {
    const el = document.getElementById(SHADOW_MAP_ID);
    if (!el || el.offsetParent === null) return;
    mountShadowLocusMap(SHADOW_MAP_ID, geojson);
  };
  requestAnimationFrame(() => setTimeout(run, 120));
}
