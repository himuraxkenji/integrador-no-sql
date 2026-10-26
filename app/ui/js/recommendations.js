import { call } from "./api.js";
import { customers, loadCustomers, loadProducts, productName } from "./data.js";
import { h, field, fillSelect, fmtPrice, guard, table, badge, busy } from "./util.js";

const errSlot = h("div");
const customerSel = h("select");
const limit = h("input", { type: "number", min: "1", max: "50", value: "5" });
const out = h("div");

export function init(root) {
  customerSel.addEventListener("change", refresh);
  root.append(
    errSlot,
    h("section", { class: "card" }, h("h2", {}, "Recomendaciones"), h("div", { class: "form-grid" }, field("Cliente", customerSel), field("Cantidad", limit), h("div", { class: "actions" }, h("button", { onClick: busy(refresh) }, "Actualizar")))),
    out,
  );
}

export async function onShow() {
  await guard(errSlot, async () => {
    await Promise.all([loadCustomers(), loadProducts()]);
    fillSelect(customerSel, customers, (c) => c.id, (c) => `${c.id} - ${c.name}`);
    await refresh();
  });
}

async function refresh() {
  if (!customerSel.value) return;
  const id = encodeURIComponent(customerSel.value);
  await guard(errSlot, async () => {
    const [recs, orders] = await Promise.all([
      call("GET", `/customers/${id}/recommendations`, { query: { limit: limit.value } }),
      call("GET", `/customers/${id}/orders`),
    ]);
    const bought = [...new Set(orders.data.flatMap((o) => o.items.map((i) => i.product_id)))];
    const overlap = recs.data.filter((r) => bought.includes(r.product.id));
    const customer = customers.find((c) => c.id === customerSel.value);
    out.replaceChildren(
      h(
        "div",
        { class: "grid two" },
        h(
          "section",
          { class: "card" },
          h("h3", {}, "Recomendados"),
          customer ? h("p", { class: "muted" }, `Intereses: ${customer.interests.join(", ") || "-"}`) : null,
          recs.data.length
            ? table(["Producto", "Precio", "Score", "Motivo"], recs.data.map((r) => [`${r.product.id} - ${r.product.name}`, fmtPrice(r.product.price), Number(r.score).toFixed(2), r.reason]))
            : h("p", { class: "muted" }, "Sin recomendaciones."),
        ),
        h(
          "section",
          { class: "card" },
          h("h3", {}, "Ya comprado (excluido)"),
          bought.length ? h("ul", {}, bought.map((pid) => h("li", {}, `${pid} - ${productName(pid)}`))) : h("p", { class: "muted" }, "Todavía no compró nada."),
          overlap.length ? h("div", { class: "box error" }, `Atención: se recomendó algo ya comprado (${overlap.map((r) => r.product.id).join(", ")})`) : badge("Ninguna recomendación repite una compra", "green"),
        ),
      ),
    );
  });
}
