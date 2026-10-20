import { request, ApiError } from "./api.js";
import { h, badge } from "./util.js";
import * as catalog from "./catalog.js";
import * as activity from "./activity.js";
import * as orders from "./orders.js";
import * as recommendations from "./recommendations.js";
import * as faults from "./faults.js";
import * as scenarios from "./scenarios.js";
import * as logpanel from "./logpanel.js";

const TABS = [
  { id: "catalogo", label: "Catálogo", mod: catalog },
  { id: "actividad", label: "Actividad", mod: activity },
  { id: "ordenes", label: "Órdenes", mod: orders },
  { id: "recomendaciones", label: "Recomendaciones", mod: recommendations },
  { id: "fallo", label: "Fallo parcial", mod: faults },
  { id: "escenarios", label: "Escenarios 01-07", mod: scenarios },
];

// Los tres motores son obligatorios; qué responsabilidad cubre cada derivado es decisión del equipo.
const ENGINES = [
  ["mongo", "MongoDB · fuente de verdad"],
  ["redis", "Redis"],
  ["neo4j", "Neo4j"],
];

const root = document.getElementById("app");
const badges = h("div", { class: "health" });
const nav = h("nav", { class: "tabs", role: "tablist" });
const main = h("main");
const logRoot = h("div");
const sections = new Map();

async function refreshHealth() {
  badges.replaceChildren(badge("consultando...", "gray"));
  try {
    const res = await request("GET", "/health");
    const data = res.data || {};
    badges.replaceChildren(...ENGINES.map(([key, label]) => {
      const v = data[key] ?? "sin dato";
      return h("span", { class: `badge ${v === "ok" || v === "fake" ? "green" : "red"}`, title: `estado: ${v}` }, `${label}: ${v}`);
    }));
  } catch (err) {
    badges.replaceChildren(badge(err instanceof ApiError ? "API no disponible" : "error", "red"));
  }
}

function select(id) {
  for (const t of TABS) {
    const active = t.id === id;
    sections.get(t.id).section.hidden = !active;
    sections.get(t.id).button.setAttribute("aria-selected", String(active));
  }
  history.replaceState(null, "", `#${id}`);
  const tab = TABS.find((t) => t.id === id);
  tab.mod.onShow();
}

root.append(
  h("header", {}, h("h1", {}, "NEXUS ", h("small", {}, "interfaz de prueba")), badges, h("button", { class: "secondary", onClick: refreshHealth }, "Actualizar estado")),
  nav,
  main,
  logRoot,
);

for (const t of TABS) {
  const section = h("section", { id: `tab-${t.id}`, role: "tabpanel", hidden: true });
  const button = h("button", { role: "tab", class: "tab", onClick: () => select(t.id) }, t.label);
  nav.append(button);
  main.append(section);
  sections.set(t.id, { section, button });
  t.mod.init(section);
}
logpanel.init(logRoot);
refreshHealth();
select(TABS.some((t) => `#${t.id}` === location.hash) ? location.hash.slice(1) : TABS[0].id);
