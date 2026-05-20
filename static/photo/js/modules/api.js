const API = window.location.origin;

async function parseResponse(r) {
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    throw new Error(data.error || data.message || `HTTP ${r.status}`);
  }
  return data;
}

/** POST JSON: при success:false на 200 — не бросает, возвращает тело ответа. */
export async function postJson(path, body) {
  const r = await fetch(API + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await parseResponse(r);
  if (data.success === false) {
    return { ...data, error: data.error || 'Ошибка запроса' };
  }
  return data;
}

export async function postJsonAllowFail(path, body) {
  const r = await fetch(API + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return parseResponse(r);
}

export { API };
