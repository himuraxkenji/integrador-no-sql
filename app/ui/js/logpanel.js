import { logEntries, onLog, clearLog } from "./api.js";
import { h, json } from "./util.js";

const hhmmss = (d) => d.toLocaleTimeString("es-AR", { hour12: false }) + "." + String(d.getMilliseconds()).padStart(3, "0");

export function init(root) {
  const list = h("div", { class: "log-list" });
  const count = h("span", { class: "muted" }, "0");
  const panel = h(
    "details",
    { class: "log-panel", id: "log-panel" },
    h("summary", {}, h("strong", {}, "Log de requests"), " ", count),
    h("div", { class: "log-bar" }, h("button", { class: "secondary small", onClick: clearLog }, "Limpiar")),
    list,
  );
  root.append(panel);

  const row = (e) => {
    const kind = e.status === "ERR" ? "red" : e.status >= 500 ? "red" : e.status >= 400 ? "orange" : "green";
    return h(
      "details",
      { class: "log-entry" },
      h(
        "summary",
        {},
        h("span", { class: "t" }, hhmmss(e.time)),
        h("span", { class: "m" }, e.method),
        h("span", { class: "p" }, e.path),
        h("span", { class: `badge ${kind}` }, e.status),
        h("span", { class: "ms" }, `${e.ms} ms`),
        e.cache ? h("span", { class: `badge ${e.cache === "HIT" ? "green" : "orange"}` }, e.cache) : null,
      ),
      h("div", { class: "log-detail" }, h("div", {}, h("strong", {}, "Request"), h("pre", {}, e.request === undefined ? "(sin cuerpo)" : json(e.request))), h("div", {}, h("strong", {}, "Response"), h("pre", {}, typeof e.response === "string" ? e.response : json(e.response)))),
    );
  };

  const redraw = () => {
    count.textContent = String(logEntries.length);
    list.replaceChildren(...[...logEntries].reverse().map(row));
  };
  onLog((ev) => {
    if (ev.type === "clear") return redraw();
    count.textContent = String(logEntries.length);
    list.prepend(row(ev.entry));
    while (list.children.length > 300) list.lastChild.remove();
  });
  redraw();
}
