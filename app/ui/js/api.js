// Único punto de contacto con la API: registra cada llamada, mide el tiempo,
// captura X-Cache y traduce los errores (501, 4xx/5xx, red caída) a ApiError.

const MAX_LOG = 300;
const listeners = new Set();
export const logEntries = [];
let seq = 0;

export function onLog(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

function notify(event) {
  for (const fn of listeners) fn(event);
}

export function clearLog() {
  logEntries.length = 0;
  notify({ type: "clear" });
}

export class ApiError extends Error {
  // kind: "pending" (501) | "http" (4xx/5xx) | "network"
  constructor(kind, message, res = null) {
    super(message);
    this.kind = kind;
    this.res = res;
  }
}

export function detailText(data) {
  if (data == null) return "";
  if (typeof data === "string") return data;
  const d = data.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((e) => `${(e.loc || []).join(".")}: ${e.msg}`).join(" | ");
  return JSON.stringify(data);
}

function buildUrl(path, query) {
  if (!query) return path;
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) {
    if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
  }
  const s = qs.toString();
  return s ? `${path}?${s}` : path;
}

function record(entry) {
  entry.id = ++seq;
  entry.time = new Date();
  logEntries.push(entry);
  if (logEntries.length > MAX_LOG) logEntries.shift();
  notify({ type: "add", entry });
}

/** Llamada "cruda": devuelve la respuesta aunque sea 4xx/5xx. Solo lanza ante error de red. */
export async function request(method, path, { query, body } = {}) {
  const url = buildUrl(path, query);
  const init = { method, headers: {} };
  if (body !== undefined) {
    init.headers["content-type"] = "application/json";
    init.body = JSON.stringify(body);
  }
  const t0 = performance.now();
  let resp;
  try {
    resp = await fetch(url, init);
  } catch (err) {
    record({ method, path: url, status: "ERR", ms: Math.round(performance.now() - t0), cache: null, request: body, response: String(err) });
    throw new ApiError("network", "No se pudo conectar con la API. ¿Está corriendo? (docker compose up, o uvicorn con ADAPTERS=fake)");
  }
  const text = await resp.text();
  const ms = Math.round(performance.now() - t0);
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }
  const res = { ok: resp.ok, status: resp.status, data, ms, cache: resp.headers.get("X-Cache"), method, path: url };
  record({ method, path: url, status: resp.status, ms, cache: res.cache, request: body, response: data });
  return res;
}

/** Convierte una respuesta no exitosa en ApiError (501 -> "pending"). */
export function ensure(res) {
  if (res.ok) return res;
  if (res.status === 501) throw new ApiError("pending", detailText(res.data) || "Funcionalidad sin implementar", res);
  throw new ApiError("http", `HTTP ${res.status}: ${detailText(res.data)}`, res);
}

/** Llamada "estricta": lanza ApiError ante cualquier respuesta no exitosa. */
export async function call(method, path, opts) {
  return ensure(await request(method, path, opts));
}
