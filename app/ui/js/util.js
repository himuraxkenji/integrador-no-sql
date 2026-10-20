import { ApiError } from "./api.js";

export function h(tag, attrs, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2).toLowerCase(), v);
    else if (v === true) el.setAttribute(k, "");
    else el.setAttribute(k, v);
  }
  append(el, children);
  return el;
}

function append(el, children) {
  for (const c of children.flat(Infinity)) {
    if (c == null || c === false) continue;
    el.append(c.nodeType ? c : String(c));
  }
}

export const fmtPrice = (n) => `$ ${Number(n).toLocaleString("es-AR", { maximumFractionDigits: 2 })}`;
export const json = (v) => JSON.stringify(v, null, 2);

export function badge(text, kind = "gray") {
  return h("span", { class: `badge ${kind}` }, text);
}

export function syncBadge(status) {
  const kind = { synced: "green", failed: "red", pending: "gray" }[status] || "gray";
  return badge(status, kind);
}

export function errorBox(err) {
  if (err instanceof ApiError && err.kind === "pending") {
    return h("div", { class: "box warn", role: "alert" }, h("strong", {}, "Pendiente de implementar"), h("div", {}, err.message));
  }
  if (err instanceof ApiError && err.kind === "network") {
    return h("div", { class: "box error", role: "alert" }, h("strong", {}, "API no disponible"), h("div", {}, err.message));
  }
  return h("div", { class: "box error", role: "alert" }, h("strong", {}, "Error"), h("div", {}, err?.message || String(err)));
}

/** Ejecuta fn y, si falla, muestra el error dentro de `slot`. Devuelve undefined ante error. */
export async function guard(slot, fn) {
  slot.replaceChildren();
  try {
    return await fn();
  } catch (err) {
    slot.replaceChildren(errorBox(err));
    return undefined;
  }
}

export function fillSelect(select, items, value, label, placeholder) {
  const prev = select.value;
  select.replaceChildren();
  if (placeholder != null) select.append(h("option", { value: "" }, placeholder));
  for (const it of items) select.append(h("option", { value: value(it) }, label(it)));
  if ([...select.options].some((o) => o.value === prev)) select.value = prev;
}

export function table(headers, rows, cls = "") {
  return h(
    "table",
    { class: cls },
    h("thead", {}, h("tr", {}, headers.map((x) => h("th", {}, x)))),
    h("tbody", {}, rows.map((r) => h("tr", r.attrs || {}, (r.cells || r).map((c) => h("td", {}, c))))),
  );
}

export function field(label, input) {
  return h("label", { class: "field" }, h("span", {}, label), input);
}
