import { call, request, ensure } from "./api.js";
import { loadProducts, products } from "./data.js";
import { h, field, fillSelect, fmtPrice, guard, json, badge, table } from "./util.js";

const errSlot = h("div");
const category = h("select", { name: "category" });
const minPrice = h("input", { type: "number", name: "min_price", min: "0", step: "any" });
const maxPrice = h("input", { type: "number", name: "max_price", min: "0", step: "any" });
const available = h(
  "select",
  { name: "available" },
  h("option", { value: "" }, "Cualquiera"),
  h("option", { value: "true" }, "Con stock"),
  h("option", { value: "false" }, "Sin stock"),
);
const attrKey = h("input", { type: "text", name: "attr_key", placeholder: "ram_gb" });
const attrVal = h("input", { type: "text", name: "attr_val", placeholder: "16" });
const results = h("div", { class: "table-wrap" });
const detail = h("div", { class: "detail" }, h("p", { class: "muted" }, "Elegí un producto de la tabla."));
let currentId = null;

export function init(root) {
  const form = h(
    "form",
    { class: "form-grid", onSubmit: (e) => { e.preventDefault(); search(); } },
    field("Categoría", category),
    field("Precio mínimo", minPrice),
    field("Precio máximo", maxPrice),
    field("Disponibilidad", available),
    field("Atributo (clave)", attrKey),
    field("Atributo (valor)", attrVal),
    h("div", { class: "actions" }, h("button", { type: "submit" }, "Buscar"), h("button", { type: "reset", class: "secondary", onClick: () => setTimeout(search) }, "Limpiar")),
  );
  root.append(
    errSlot,
    h(
      "div",
      { class: "grid two" },
      h("section", { class: "card" }, h("h2", {}, "Búsqueda"), form, results),
      h("section", { class: "card" }, h("h2", {}, "Detalle del producto"), detail),
    ),
  );
}

export async function onShow() {
  await guard(errSlot, async () => {
    await loadProducts();
    const cats = [...new Set(products.map((p) => p.category))].sort();
    fillSelect(category, cats, (c) => c, (c) => c, "Todas");
    await search();
  });
}

function attrChips(attrs) {
  const entries = Object.entries(attrs || {});
  if (!entries.length) return "-";
  return h("div", { class: "attr-chips" }, entries.map(([k, v]) => h("span", { class: "attr-chip" }, `${k}: ${typeof v === "object" ? JSON.stringify(v) : v}`)));
}

async function search() {
  await guard(errSlot, async () => {
    const query = { category: category.value, min_price: minPrice.value, max_price: maxPrice.value, available: available.value, limit: 100 };
    if (attrKey.value.trim() && attrVal.value.trim()) query[`attr.${attrKey.value.trim()}`] = attrVal.value.trim();
    const list = (await call("GET", "/products", { query })).data;
    if (!list.length) {
      results.replaceChildren(h("p", { class: "muted" }, "Sin resultados."));
      return;
    }
    const rows = list.map((p) => ({
      attrs: { class: "clickable" + (p.id === currentId ? " selected" : ""), onClick: () => consult(p.id) },
      cells: [p.id, p.name, p.category, fmtPrice(p.price), p.stock, attrChips(p.attributes)],
    }));
    results.replaceChildren(h("p", { class: "muted" }, `${list.length} producto(s)`), table(["Id", "Nombre", "Categoría", "Precio", "Stock", "Atributos"], rows, "catalog"));
  });
}

async function consult(id, hint) {
  currentId = id;
  const slot = h("div");
  detail.replaceChildren(slot);
  await guard(slot, async () => {
    const res = ensure(await request("GET", `/products/${encodeURIComponent(id)}`));
    const p = res.data;
    const kind = res.cache === "HIT" ? "green" : res.cache === "MISS" ? "orange" : "gray";
    // replaceChildren no ignora null (lo escribe como "null"): se arma la lista sin huecos.
    detail.replaceChildren(
      h(
        "div",
        { class: "cache-line" },
        h("span", { class: `cache-badge ${kind}` }, res.cache || "?"),
        h("div", {}, h("div", {}, `X-Cache: ${res.cache || "(sin header)"}`), h("div", { class: "muted" }, `${res.ms} ms`)),
        h("button", { class: "secondary", onClick: () => consult(id, "Consulta repetida") }, "Volver a consultar"),
      ),
      ...(hint ? [h("div", { class: "box info" }, hint)] : []),
      h("h3", {}, "Atributos"),
      attrChips(p.attributes),
      h("pre", {}, json(p)),
      editForm(p),
    );
  });
  search();
}

function editForm(p) {
  const name = h("input", { type: "text", value: p.name });
  const price = h("input", { type: "number", step: "any", min: "0", value: p.price });
  const stock = h("input", { type: "number", step: "1", min: "0", value: p.stock });
  const slot = h("div");
  const save = async (e) => {
    e.preventDefault();
    await guard(slot, async () => {
      const body = {};
      if (name.value !== p.name) body.name = name.value;
      if (Number(price.value) !== p.price) body.price = Number(price.value);
      if (Number(stock.value) !== p.stock) body.stock = Number(stock.value);
      if (!Object.keys(body).length) {
        slot.replaceChildren(h("div", { class: "box info" }, "No hay cambios."));
        return;
      }
      await call("PUT", `/products/${encodeURIComponent(p.id)}`, { body });
      await loadProducts();
      await consult(p.id, "Producto actualizado. Mirá el badge: la caché se invalidó, por eso debería ser MISS. Tocá \"Volver a consultar\" y debería pasar a HIT.");
    });
  };
  const remove = async () => {
    if (!confirm(`¿Eliminar (borrado lógico) ${p.id}?`)) return;
    await guard(slot, async () => {
      await call("DELETE", `/products/${encodeURIComponent(p.id)}`);
      currentId = null;
      detail.replaceChildren(h("div", { class: "box info" }, `${p.id} eliminado (lógico). Volver a consultarlo debería dar 404.`), h("button", { class: "secondary", onClick: () => consult(p.id) }, "Consultar igual"));
      await loadProducts();
      search();
    });
  };
  return h(
    "div",
    {},
    h("h3", {}, "Editar"),
    h("form", { class: "form-grid", onSubmit: save }, field("Nombre", name), field("Precio", price), field("Stock", stock), h("div", { class: "actions" }, h("button", { type: "submit" }, "Guardar (PUT)"), h("button", { type: "button", class: "danger", onClick: remove }, "Eliminar (lógico)"))),
    slot,
  );
}
