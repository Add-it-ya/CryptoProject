const BASE = '/api';

export const getToken = () => sessionStorage.getItem('cv_token');
export const setToken = (t) => (t ? sessionStorage.setItem('cv_token', t) : sessionStorage.removeItem('cv_token'));

export async function api(path, { method = 'GET', body, form, raw } = {}) {
  const headers = {};
  const t = getToken();
  if (t) headers.Authorization = 'Bearer ' + t;
  let b;
  if (form) b = form;
  else if (raw) {
    b = raw;
    headers['Content-Type'] = 'application/octet-stream';
  } else if (body !== undefined) {
    b = JSON.stringify(body);
    headers['Content-Type'] = 'application/json';
  }
  const res = await fetch(BASE + path, { method, headers, body: b });
  if (!res.ok) {
    let e;
    try {
      e = (await res.json()).error;
    } catch {
      e = res.statusText;
    }
    throw new Error(e || 'request failed');
  }
  return res;
}

export const getJSON = async (path, opts) => (await api(path, opts)).json();
export const getBytes = async (path) => new Uint8Array(await (await api(path)).arrayBuffer());
