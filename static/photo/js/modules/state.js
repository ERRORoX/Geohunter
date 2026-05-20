/** Центральное состояние раздела «Фото». */
export const state = {
  imgSrc: null,
  imgB64: null,
  imgUrl: '',
  urlMode: false,
  uploadFileName: null,

  running: new Set(),
  doneSet: new Set(),
  errSet: new Set(),
  collapsedSet: new Set(),

  results: {},
  searchResults: [],
  reverseLinks: null,

  shadowParams: { objectHeight: 1, shadowLength: 1.5 },
  shadowDate: '',
  shadowMapOpen: false,

  exifAdvanced: true,
  exifShowAllTags: false,
  exiftoolFull: null,
  exiftoolFullLoading: false,
  exiftoolFullErr: '',
  exiftoolFullQuery: '',
};

export function hasImg() {
  return !!(state.imgB64 || state.imgUrl);
}

export function imgPayload() {
  return {
    imageBase64: state.imgB64 || undefined,
    imageUrl: state.imgUrl || undefined,
  };
}

export function resetAnalysis() {
  state.running.clear();
  state.doneSet.clear();
  state.errSet.clear();
  state.collapsedSet.clear();
  state.results = {};
  state.searchResults = [];
  state.reverseLinks = null;
  state.exiftoolFull = null;
  state.exiftoolFullLoading = false;
  state.exiftoolFullErr = '';
  state.exiftoolFullQuery = '';
  state.shadowMapOpen = false;
  state.shadowDate = '';
}

export function markRunning(id) {
  state.running.add(id);
  state.errSet.delete(id);
}

export function markDone(id, data) {
  state.running.delete(id);
  state.doneSet.add(id);
  state.errSet.delete(id);
  state.results[id] = data;
}

export function markError(id, message) {
  state.running.delete(id);
  state.doneSet.delete(id);
  state.errSet.add(id);
  state.results[id] = { error: message };
}
