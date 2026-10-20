// Datos de referencia compartidos por las pestañas (clientes y productos).
import { call } from "./api.js";

export let customers = [];
export let products = [];

export async function loadCustomers() {
  customers = (await call("GET", "/customers")).data;
  return customers;
}

export async function loadProducts() {
  products = (await call("GET", "/products", { query: { limit: 200 } })).data;
  return products;
}

export const productName = (id) => products.find((p) => p.id === id)?.name || id;
