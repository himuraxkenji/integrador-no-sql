import { call } from "./api.js";
import { customers, products, loadCustomers, loadProducts, productName } from "./data.js";
import { h, field, fillSelect, guard, table } from "./util.js";

const errSlot = h("div");
const customerSel = h("select");
const productSel = h("select");
const panel = h("div", { class: "grid three" });

export function init(root) {
  customerSel.addEventListener("change", refresh);
  productSel.addEventListener("change", refresh);
  root.append(
    errSlot,
    h(
      "section",
      { class: "card" },
      h("h2", {}, "Registrar vista"),
      h("div", { class: "form-grid" }, field("Cliente", customerSel), field("Producto", productSel), h("div", { class: "actions" }, h("button", { onClick: registerView }, "Registrar vista"))),
    ),
    panel,
  );
}

export async function onShow() {
  await guard(errSlot, async () => {
    await Promise.all([loadCustomers(), loadProducts()]);
    fillSelect(customerSel, customers, (c) => c.id, (c) => `${c.id} - ${c.name}`);
    fillSelect(productSel, products, (p) => p.id, (p) => `${p.id} - ${p.name}`);
    await refresh();
  });
}

async function registerView() {
  await guard(errSlot, async () => {
    await call("POST", `/products/${encodeURIComponent(productSel.value)}/views`, { body: { customer_id: customerSel.value } });
    await refresh();
  });
}

async function refresh() {
  if (!customerSel.value || !productSel.value) return;
  await guard(errSlot, async () => {
    const [views, recent, top] = await Promise.all([
      call("GET", `/products/${encodeURIComponent(productSel.value)}/views`),
      call("GET", `/customers/${encodeURIComponent(customerSel.value)}/recent`),
      call("GET", "/activity/top", { query: { limit: 10 } }),
    ]);
    panel.replaceChildren(
      h("section", { class: "card" }, h("h3", {}, "Vistas del producto"), h("div", { class: "big-number" }, views.data.views), h("div", { class: "muted" }, productName(productSel.value))),
      h(
        "section",
        { class: "card" },
        h("h3", {}, "Recientes del cliente"),
        recent.data.product_ids.length ? h("ol", {}, recent.data.product_ids.map((id) => h("li", {}, `${id} - ${productName(id)}`))) : h("p", { class: "muted" }, "Sin actividad."),
      ),
      h(
        "section",
        { class: "card" },
        h("h3", {}, "Más vistos"),
        top.data.length ? table(["#", "Producto", "Vistas"], top.data.map((t, i) => [i + 1, `${t.product_id} - ${productName(t.product_id)}`, t.views])) : h("p", { class: "muted" }, "Sin datos."),
      ),
    );
  });
}
