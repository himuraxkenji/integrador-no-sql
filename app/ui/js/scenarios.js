// Escenarios 01-07: replican los pasos y aserciones de tests/acceptance/test_0N_*.py.
import { request, ApiError, ensure } from "./api.js";
import { h, badge, setBusy, spinner } from "./util.js";

const CUSTOMER = "c-008";

const show = (v) => (typeof v === "string" ? v : JSON.stringify(v));
const ids = (recs) => recs.map((r) => r.product.id);

class Ctx {
  constructor(onStep, onWait) {
    this.steps = [];
    this.onStep = onStep;
    this.onWait = onWait;
    this.stamp = Date.now();
    this.n = 0;
  }
  push(step) {
    this.steps.push(step);
    this.onStep(step);
  }
  check(desc, expected, obtained, ok) {
    this.push({ desc, expected: show(expected), obtained: show(obtained), state: ok ? "ok" : "fail" });
    return ok;
  }
  /** Llamada cruda; un 501 aborta el escenario como "pendiente". */
  async req(method, path, opts) {
    this.onWait(`${method} ${path}`);
    const res = await request(method, path, opts);
    if (res.status === 501) ensure(res);
    return res;
  }
  status(desc, res, expected) {
    return this.check(desc, `HTTP ${expected}`, `HTTP ${res.status}`, res.status === expected);
  }
  async newProduct({ price = 100, stock = 10, category = "notebooks" } = {}) {
    const id = `ui-${this.stamp}-${++this.n}`;
    const res = await this.req("POST", "/products", { body: { id, name: `Producto UI ${id}`, category, price, stock, attributes: {} } });
    this.status(`Crear producto de prueba ${id}`, res, 201);
    if (!res.ok) throw new Error("No se pudo crear el producto de prueba");
    return res.data;
  }
  async buy(productId, quantity = 1, customer = CUSTOMER) {
    return this.req("POST", "/orders", { body: { customer_id: customer, items: [{ product_id: productId, quantity }] } });
  }
  async view(productId, customer = CUSTOMER) {
    const res = await this.req("POST", `/products/${productId}/views`, { body: { customer_id: customer } });
    if (res.status !== 202) this.status(`Registrar vista de ${productId}`, res, 202);
    return res;
  }
  async count(productId) {
    return (await this.req("GET", `/products/${productId}/views`)).data.views;
  }
  async setFault(down) {
    const res = await this.req("POST", "/admin/faults", { body: { relations_down: down } });
    this.status(`POST /admin/faults relations_down=${down}`, res, 200);
  }
}

const cacheStep = (c, desc, res, cache) =>
  c.check(desc, `HTTP 200, X-Cache: ${cache}`, `HTTP ${res.status}, X-Cache: ${res.cache}`, res.status === 200 && res.cache === cache);

export const SCENARIOS = [
  {
    id: "01",
    title: "Primera lectura (MISS)",
    summary: "La primera lectura la responde MongoDB y deja una entrada en caché.",
    mutates: false,
    async run(c) {
      const p = await c.newProduct();
      const first = await c.req("GET", `/products/${p.id}`);
      cacheStep(c, "Primer GET /products/{id}", first, "MISS");
      c.check("El nombre coincide con el creado", p.name, first.data?.name, first.data?.name === p.name);
      cacheStep(c, "Segundo GET: la entrada de caché existe", await c.req("GET", `/products/${p.id}`), "HIT");
      c.status("GET de un producto inexistente", await c.req("GET", "/products/no-existe"), 404);
    },
  },
  {
    id: "02",
    title: "Lectura repetida (HIT)",
    summary: "Las lecturas repetidas las responde la caché.",
    mutates: false,
    async run(c) {
      const p = await c.newProduct();
      const url = `/products/${p.id}`;
      const first = await c.req("GET", url);
      cacheStep(c, "Primer GET", first, "MISS");
      for (let i = 1; i <= 3; i++) {
        const r = await c.req("GET", url);
        cacheStep(c, `GET repetido #${i}`, r, "HIT");
        c.check(`Mismo cuerpo que la primera lectura (#${i})`, "iguales", JSON.stringify(r.data) === JSON.stringify(first.data) ? "iguales" : "distintos", JSON.stringify(r.data) === JSON.stringify(first.data));
      }
    },
  },
  {
    id: "03",
    title: "Actualizar invalida la caché",
    summary: "Tras actualizar o borrar, la caché no sirve datos viejos.",
    mutates: false,
    async run(c) {
      const p = await c.newProduct({ price: 100 });
      const url = `/products/${p.id}`;
      await c.req("GET", url);
      cacheStep(c, "GET previo deja la caché caliente", await c.req("GET", url), "HIT");
      c.status("PUT price=150", await c.req("PUT", url, { body: { price: 150 } }), 200);
      const after = await c.req("GET", url);
      c.check("Precio nuevo visible", 150, after.data?.price, after.data?.price === 150);
      c.check("Se re-leyó de MongoDB", "X-Cache: MISS", `X-Cache: ${after.cache}`, after.cache === "MISS");
      cacheStep(c, "Vuelve a cachearse", await c.req("GET", url), "HIT");

      const upd = await c.req("PUT", url, { body: { stock: 3 } });
      c.check("Update parcial: stock cambia y el precio se conserva", "stock=3, price=150", `stock=${upd.data?.stock}, price=${upd.data?.price}`, upd.data?.stock === 3 && upd.data?.price === 150);

      const q = await c.newProduct();
      const qurl = `/products/${q.id}`;
      await c.req("GET", qurl);
      c.status("DELETE (lógico) de un producto cacheado", await c.req("DELETE", qurl), 204);
      c.status("GET posterior al borrado", await c.req("GET", qurl), 404);
      const found = await c.req("GET", "/products", { query: { category: q.category, limit: 200 } });
      const present = (found.data || []).some((x) => x.id === q.id);
      c.check("No aparece en la búsqueda", "ausente", present ? "presente" : "ausente", !present);
    },
  },
  {
    id: "04",
    title: "Vistas y actividad",
    summary: "Las vistas actualizan contadores, historial reciente y ranking.",
    mutates: true,
    async run(c) {
      const p = await c.newProduct();
      const before = await c.count(p.id);
      c.check("Contador inicial", 0, before, before === 0);
      for (let i = 0; i < 3; i++) await c.view(p.id);
      const after = await c.count(p.id);
      c.check("Contador tras 3 vistas", 3, after, after === 3);

      const a = await c.newProduct();
      const b = await c.newProduct();
      await c.view(a.id);
      await c.view(b.id);
      await c.view(a.id);
      const recent = (await c.req("GET", `/customers/${CUSTOMER}/recent`)).data?.product_ids || [];
      c.check("Más reciente primero: [a, b]", [a.id, b.id], recent.slice(0, 2), recent[0] === a.id && recent[1] === b.id);
      c.check("Sin duplicados", "sin duplicados", `${recent.length} ids, ${new Set(recent).size} únicos`, recent.length === new Set(recent).size);

      // El límite configurado lo informa la API (campo `limit`); se envían limit + 2 vistas.
      const limit = Number((await c.req("GET", "/customers/c-007/recent")).data?.limit) || 0;
      for (let i = 0; i < limit + 2; i++) await c.view((await c.newProduct()).id, "c-007");
      const bounded = (await c.req("GET", "/customers/c-007/recent", { query: { limit: 1000 } })).data?.product_ids || [];
      c.check(`Historial acotado (${limit + 2} vistas, límite ${limit})`, limit, bounded.length, limit > 0 && bounded.length === limit);

      const popular = await c.newProduct();
      const quiet = await c.newProduct();
      for (let i = 0; i < 5; i++) await c.view(popular.id, "c-006");
      await c.view(quiet.id, "c-006");
      const top = (await c.req("GET", "/activity/top", { query: { limit: 100 } })).data || [];
      const order = top.map((t) => t.product_id);
      c.check("El popular rankea antes que el silencioso", "pos(popular) < pos(quiet)", `${order.indexOf(popular.id)} vs ${order.indexOf(quiet.id)}`, order.includes(popular.id) && order.indexOf(popular.id) < order.indexOf(quiet.id));
      const views = top.map((t) => t.views);
      c.check("Ranking en orden descendente", "descendente", views.join(",").slice(0, 60), views.every((v, i) => i === 0 || views[i - 1] >= v));
    },
  },
  {
    id: "05",
    title: "Compra",
    summary: "Una compra crea la orden en MongoDB y actualiza las relaciones de compra.",
    mutates: true,
    async run(c) {
      const p = await c.newProduct({ price: 100, stock: 10 });
      const res = await c.buy(p.id, 2);
      c.status("POST /orders", res, 201);
      const o = res.data || {};
      c.check("sync_status", "synced", o.sync_status, o.sync_status === "synced");
      c.check("Total = 2 x 100", 200, o.total, o.total === 200);
      c.check("Cantidad del ítem", 2, o.items?.[0]?.quantity, o.items?.[0]?.quantity === 2);
      const fetched = await c.req("GET", `/orders/${o.id}`);
      c.check("GET /orders/{id}: synced", "synced", fetched.data?.sync_status, fetched.data?.sync_status === "synced");
      const mine = (await c.req("GET", `/customers/${CUSTOMER}/orders`)).data || [];
      c.check("Aparece en las órdenes del cliente", "presente", mine.some((x) => x.id === o.id) ? "presente" : "ausente", mine.some((x) => x.id === o.id));

      const q = await c.newProduct({ price: 100 });
      const snap = (await c.buy(q.id)).data;
      await c.req("PUT", `/products/${q.id}`, { body: { price: 999 } });
      const unit = (await c.req("GET", `/orders/${snap?.id}`)).data?.items?.[0]?.unit_price;
      c.check("Snapshot de precio tras subir el precio a 999", 100, unit, unit === 100);

      const low = await c.newProduct({ stock: 1 });
      c.status("Stock insuficiente (1 disponible, pide 5)", await c.buy(low.id, 5), 409);
      c.status("Producto inexistente", await c.buy("no-existe"), 404);
      c.status("Cliente inexistente", await c.buy((await c.newProduct()).id, 1, "fantasma"), 404);
    },
  },
  {
    id: "06",
    title: "Recomendaciones",
    summary: "Candidatos del buscador + detalles de MongoDB, sin lo ya comprado (dataset de muestra).",
    mutates: true,
    async run(c) {
      const recs = async (cust) => (await c.req("GET", `/customers/${cust}/recommendations`, { query: { limit: 20 } })).data || [];
      const ana = await recs("c-001");
      const aid = ids(ana);
      c.check("Primera recomendación de Ana (c-001)", "kb-001", aid[0], aid[0] === "kb-001");
      c.check("También recomienda mn-002", "incluye mn-002", aid.join(", "), aid.includes("mn-002"));
      c.check("Excluye lo ya comprado (nb-001, ms-001)", "ausentes", aid.filter((x) => ["nb-001", "ms-001"].includes(x)).join(", ") || "ausentes", !aid.includes("nb-001") && !aid.includes("ms-001"));
      const f = ana[0];
      c.check("Detalles comerciales de MongoDB", "Teclado Mecánico Forge, 90", `${f?.product?.name}, ${f?.product?.price}`, f?.product?.name === "Teclado Mecánico Forge" && f?.product?.price === 90);
      c.check("score > 0 y motivo presente", "score>0, reason", `${f?.score}, ${f?.reason}`, f?.score > 0 && !!f?.reason);
      c.check("Descarta productos inactivos (mn-004)", "ausente", aid.includes("mn-004") ? "presente" : "ausente", !aid.includes("mn-004"));
      const order = await c.req("POST", "/orders", { body: { customer_id: "c-007", items: [{ product_id: "kb-002", quantity: 1 }] } });
      c.status("c-007 compra kb-002", order, 201);
      const after = ids(await recs("c-007"));
      c.check("kb-002 deja de recomendarse a c-007", "ausente", after.includes("kb-002") ? "presente" : "ausente", !after.includes("kb-002"));
    },
  },
  {
    id: "07",
    title: "Falla parcial",
    summary: "Si el almacén de relaciones cae, la orden no se pierde: se detecta y se recupera.",
    mutates: true,
    async run(c) {
      const unsynced = async () => ((await c.req("GET", "/admin/sync-status")).data?.unsynced || []).map((o) => o.id);
      try {
        await c.setFault(true);
        const p = await c.newProduct();
        const res = await c.buy(p.id);
        c.status("POST /orders con la falla activa (la compra se registra)", res, 201);
        const o = res.data || {};
        c.check("sync_status de la respuesta", "failed", o.sync_status, o.sync_status === "failed");
        c.check("sync_error informado", "presente", o.sync_error || "(vacío)", !!o.sync_error);
        const fetched = await c.req("GET", `/orders/${o.id}`);
        c.check("GET /orders/{id} persiste failed", "failed", fetched.data?.sync_status, fetched.data?.sync_status === "failed");
        const st = (await c.req("GET", "/admin/sync-status")).data || {};
        c.check("Detección: counts.failed >= 1", ">= 1", st.counts?.failed, st.counts?.failed >= 1);
        c.check("Detección: la orden figura en unsynced", "presente", (await unsynced()).includes(o.id) ? "presente" : "ausente", (await unsynced()).includes(o.id));

        const still = (await c.req("POST", "/admin/reconcile")).data || {};
        c.check("Reconciliar con la falla activa: still_failed >= 1", ">= 1", still.still_failed, still.still_failed >= 1);
        c.check("Sigue en unsynced (no se pierde nada)", "presente", (await unsynced()).includes(o.id) ? "presente" : "ausente", (await unsynced()).includes(o.id));

        await c.setFault(false);
        const rep = (await c.req("POST", "/admin/reconcile")).data || {};
        c.check("Reconciliar tras recuperar: la orden está en synced_order_ids", "presente", (rep.synced_order_ids || []).includes(o.id) ? "presente" : "ausente", (rep.synced_order_ids || []).includes(o.id));
        const done = await c.req("GET", `/orders/${o.id}`);
        c.check("La orden quedó synced", "synced", done.data?.sync_status, done.data?.sync_status === "synced");
        c.check("Ya no figura en unsynced", "ausente", (await unsynced()).includes(o.id) ? "presente" : "ausente", !(await unsynced()).includes(o.id));
        const second = (await c.req("POST", "/admin/reconcile")).data || {};
        c.check("Reconciliar dos veces es seguro: checked = 0", 0, second.checked, second.checked === 0);
      } finally {
        // Siempre deja la falla apagada, incluso si algo explotó a mitad de camino.
        try {
          const r = await request("POST", "/admin/faults", { body: { relations_down: false } });
          c.check("Limpieza: relations_down apagada", "HTTP 200", `HTTP ${r.status}`, r.status === 200);
        } catch {
          /* sin red: nada más que hacer */
        }
      }
    },
  },
];

/** Corre un escenario y devuelve { state: ok|fail|pending, steps }. */
export async function runScenario(def, onStep = () => {}, onWait = () => {}) {
  const c = new Ctx(onStep, onWait);
  let state = "ok";
  try {
    await def.run(c);
  } catch (err) {
    if (err instanceof ApiError && err.kind === "pending") {
      c.push({ desc: "Funcionalidad sin implementar", expected: "-", obtained: err.message, state: "pending" });
    } else {
      c.push({ desc: "Error inesperado", expected: "sin errores", obtained: err.message, state: "fail" });
    }
  }
  if (c.steps.some((s) => s.state === "fail")) state = "fail";
  else if (c.steps.some((s) => s.state === "pending")) state = "pending";
  return { state, steps: c.steps };
}

const MARK = { ok: ["✓", "green"], fail: ["✗", "red"], pending: ["⚠", "yellow"] };
const STATE_TEXT = { ok: "OK", fail: "FALLÓ", pending: "PENDIENTE" };

export function init(root) {
  const summary = h("div", { class: "box info" }, "Todavía no se ejecutó nada.");
  const runAll = h("button", { onClick: () => all() }, "Ejecutar todos");
  const cards = new Map();
  const results = new Map();

  // state === null: el escenario está corriendo; `waiting` es la request en curso (paso en progreso).
  const render = (def, steps, state, waiting) => {
    const card = cards.get(def.id);
    card.status.replaceChildren(state ? badge(STATE_TEXT[state], MARK[state][1]) : h("span", { class: "badge gray", role: "status" }, spinner(), " ejecutando..."));
    if (state) card.body.removeAttribute("aria-busy");
    else card.body.setAttribute("aria-busy", "true");
    card.body.replaceChildren(
      steps.length || waiting
        ? h(
            "table",
            { class: "steps" },
            h("thead", {}, h("tr", {}, ["Paso", "Esperado", "Obtenido", ""].map((t) => h("th", {}, t)))),
            h(
              "tbody",
              {},
              steps.map((s) => h("tr", { class: s.state }, h("td", {}, s.desc), h("td", {}, s.expected), h("td", {}, s.obtained), h("td", { class: `mark ${MARK[s.state][1]}` }, MARK[s.state][0]))),
              waiting ? h("tr", { class: "running" }, h("td", { colspan: "3" }, h("span", { class: "loading" }, spinner(), h("span", {}, `En curso: ${waiting}`))), h("td", { class: "mark" }, "…")) : null,
            ),
          )
        : "",
    );
  };

  const runOne = async (def) => {
    const card = cards.get(def.id);
    setBusy(card.button, true);
    const steps = [];
    render(def, steps, null);
    try {
      const res = await runScenario(
        def,
        (s) => {
          steps.push(s);
          render(def, steps, null);
        },
        (waiting) => render(def, steps, null, waiting),
      );
      render(def, res.steps, res.state);
      results.set(def.id, res.state);
      return res.state;
    } finally {
      setBusy(card.button, false);
    }
  };

  const all = async () => {
    setBusy(runAll, true);
    summary.className = "box info";
    summary.textContent = "Ejecutando...";
    for (const def of SCENARIOS) await runOne(def);
    const states = SCENARIOS.map((d) => results.get(d.id));
    const n = (s) => states.filter((x) => x === s).length;
    summary.className = `box ${n("fail") ? "error" : n("pending") ? "warn" : "ok"}`;
    summary.textContent = `Resumen: ${n("ok")} OK, ${n("fail")} fallaron, ${n("pending")} pendientes (de ${SCENARIOS.length}).`;
    setBusy(runAll, false);
    summary.dataset.done = "1";
  };

  root.append(
    h("section", { class: "card" }, h("h2", {}, "Escenarios obligatorios"), h("p", { class: "muted" }, "Cada tarjeta ejecuta los mismos pasos y aserciones que tests/acceptance/test_0N_*.py contra la API en vivo. Crean productos con ids únicos, así que se pueden repetir."), h("div", { class: "actions" }, runAll), summary),
    ...SCENARIOS.map((def) => {
      const status = h("span");
      const body = h("div", { class: "table-wrap" });
      const button = h("button", { onClick: () => runOne(def) }, "Ejecutar");
      cards.set(def.id, { status, body, button });
      return h(
        "section",
        { class: "card", id: `scenario-${def.id}` },
        h("div", { class: "card-head" }, h("h3", {}, `Escenario ${def.id} - ${def.title}`), status, button),
        h("p", { class: "muted" }, def.summary),
        def.mutates ? h("div", { class: "box warn" }, "Modifica datos del dataset (vistas, órdenes o stock). make seed restaura un estado limpio.") : null,
        body,
      );
    }),
  );
}

export function onShow() {}
