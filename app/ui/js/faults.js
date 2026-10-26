import { call } from "./api.js";
import { h, guard, badge, table, syncBadge, fmtPrice, json, busy } from "./util.js";

const errSlot = h("div");
const faultBox = h("div");
const syncBox = h("div");
const reportBox = h("div");

export function init(root) {
  root.append(
    errSlot,
    h(
      "div",
      { class: "grid two" },
      h("section", { class: "card" }, h("h2", {}, "Falla inyectada"), h("p", { class: "muted" }, "Con relations_down activo, toda escritura en el almacén de relaciones falla (escenario 07)."), faultBox),
      h(
        "section",
        { class: "card" },
        h("h2", {}, "Sincronización de órdenes"),
        h("div", { class: "actions" }, h("button", { class: "secondary", onClick: busy(loadSync) }, "Actualizar"), h("button", { onClick: busy(reconcile) }, "Reconciliar")),
        reportBox,
        syncBox,
      ),
    ),
  );
}

export async function onShow() {
  await guard(errSlot, async () => {
    await loadFaults();
    await loadSync();
  });
}

async function loadFaults() {
  const f = (await call("GET", "/admin/faults")).data;
  faultBox.replaceChildren(
    h("div", { class: "cache-line" }, f.relations_down ? badge("relations_down: ACTIVA", "red") : badge("relations_down: apagada", "green")),
    h("div", { class: "actions" }, h("button", { class: f.relations_down ? "" : "danger", onClick: busy(() => toggle(!f.relations_down)) }, f.relations_down ? "Apagar falla" : "Encender falla")),
  );
}

async function toggle(value) {
  await guard(errSlot, async () => {
    await call("POST", "/admin/faults", { body: { relations_down: value } });
    await loadFaults();
  }, "Cambiando la falla…");
}

async function loadSync() {
  await guard(errSlot, async () => {
    const s = (await call("GET", "/admin/sync-status")).data;
    syncBox.replaceChildren(
      h("div", { class: "chips" }, Object.entries(s.counts).map(([k, v]) => h("span", { class: "chip" }, syncBadge(k), ` ${v}`))),
      s.unsynced.length
        ? table(["Orden", "Cliente", "Total", "Estado", "Error"], s.unsynced.map((o) => [o.id, o.customer_id, fmtPrice(o.total), syncBadge(o.sync_status), o.sync_error || "-"]))
        : h("p", { class: "muted" }, "No hay órdenes sin sincronizar."),
    );
  });
}

async function reconcile() {
  await guard(errSlot, async () => {
    const r = (await call("POST", "/admin/reconcile")).data;
    reportBox.replaceChildren(h("div", { class: "box info" }, h("strong", {}, `Revisadas ${r.checked}, sincronizadas ${r.synced}, siguen fallando ${r.still_failed}`), h("pre", {}, json(r))));
    await loadSync();
  }, "Reconciliando…");
}
