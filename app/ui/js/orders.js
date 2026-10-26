import { call } from "./api.js";
import { customers, products, loadCustomers, loadProducts, productName } from "./data.js";
import { h, field, fillSelect, fmtPrice, guard, syncBadge, table, busy } from "./util.js";

const errSlot = h("div");
const customerSel = h("select");
const productSel = h("select");
const qty = h("input", { type: "number", min: "1", step: "1", value: "1" });
const cartBox = h("div");
const resultBox = h("div");
const listBox = h("div");
let cart = [];

export function init(root) {
  customerSel.addEventListener("change", () => { cart = []; renderCart(); resultBox.replaceChildren(); loadOrders(); });
  root.append(
    errSlot,
    h(
      "div",
      { class: "grid two" },
      h(
        "section",
        { class: "card" },
        h("h2", {}, "Nueva compra"),
        field("Cliente", customerSel),
        h("div", { class: "form-grid" }, field("Producto", productSel), field("Cantidad", qty), h("div", { class: "actions" }, h("button", { class: "secondary", onClick: addItem }, "Agregar al carrito"))),
        cartBox,
        h("div", { class: "actions" }, h("button", { onClick: busy(buy) }, "Comprar")),
        resultBox,
      ),
      h("section", { class: "card" }, h("h2", {}, "Órdenes del cliente"), listBox),
    ),
  );
  renderCart();
}

export async function onShow() {
  await guard(errSlot, async () => {
    await Promise.all([loadCustomers(), loadProducts()]);
    fillSelect(customerSel, customers, (c) => c.id, (c) => `${c.id} - ${c.name}`);
    fillSelect(productSel, products, (p) => p.id, (p) => `${p.id} - ${p.name} (${fmtPrice(p.price)}, stock ${p.stock})`);
    await loadOrders();
  });
}

function addItem() {
  const q = Number(qty.value);
  if (!productSel.value || !(q > 0)) return;
  const existing = cart.find((i) => i.product_id === productSel.value);
  if (existing) existing.quantity += q;
  else cart.push({ product_id: productSel.value, quantity: q });
  renderCart();
}

function renderCart() {
  if (!cart.length) {
    cartBox.replaceChildren(h("p", { class: "muted" }, "Carrito vacío."));
    return;
  }
  cartBox.replaceChildren(
    table(["Producto", "Cantidad", ""], cart.map((i, idx) => [`${i.product_id} - ${productName(i.product_id)}`, i.quantity, h("button", { class: "secondary small", onClick: () => { cart.splice(idx, 1); renderCart(); } }, "Quitar")])),
  );
}

async function buy() {
  resultBox.replaceChildren();
  if (!cart.length) {
    resultBox.append(h("div", { class: "box info" }, "Agregá al menos un producto al carrito."));
    return;
  }
  await guard(resultBox, async () => {
    const res = await call("POST", "/orders", { body: { customer_id: customerSel.value, items: cart } });
    cart = [];
    renderCart();
    resultBox.replaceChildren(orderCard(res.data, "Orden creada"));
    await loadOrders();
  }, "Creando la orden…");
}

function orderCard(o, title) {
  return h(
    "div",
    { class: "order" },
    h("div", {}, h("strong", {}, `${title}: ${o.id}`), " ", syncBadge(o.sync_status), " ", h("span", { class: "muted" }, `total ${fmtPrice(o.total)}`)),
    o.sync_error ? h("div", { class: "box error" }, `sync_error: ${o.sync_error}`) : null,
    h("ul", {}, o.items.map((i) => h("li", {}, `${i.quantity} x ${i.product_id} - ${productName(i.product_id)} a ${fmtPrice(i.unit_price)}`))),
  );
}

async function loadOrders() {
  if (!customerSel.value) return;
  await guard(listBox, async () => {
    const list = (await call("GET", `/customers/${encodeURIComponent(customerSel.value)}/orders`)).data;
    listBox.replaceChildren(...(list.length ? list.map((o) => orderCard(o, "Orden")) : [h("p", { class: "muted" }, "Este cliente no tiene órdenes.")]));
  }, "Cargando órdenes…");
}
