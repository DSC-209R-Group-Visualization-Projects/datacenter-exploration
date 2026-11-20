// Shared helpers: theme colors, tooltip, data tables, motion preference.
const css = getComputedStyle(document.documentElement);
const C = {
  bg: css.getPropertyValue("--bg").trim(),
  text: css.getPropertyValue("--text").trim(),
  text2: css.getPropertyValue("--text-2").trim(),
  muted: css.getPropertyValue("--muted").trim(),
  grid: css.getPropertyValue("--grid").trim(),
  axis: css.getPropertyValue("--axis").trim(),
  dc: css.getPropertyValue("--dc").trim(),
  accent: css.getPropertyValue("--accent").trim(),
  city: css.getPropertyValue("--city").trim(),
};
const REDUCED = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const DUR = REDUCED ? 0 : 900;   // default transition length (ms)

const tip = {
  el: document.querySelector(".tooltip"),
  show(html, event) {
    this.el.innerHTML = html;
    this.el.classList.add("show");
    this.move(event);
  },
  move(event) {
    const pad = 14, r = this.el.getBoundingClientRect();
    let x = event.clientX + pad, y = event.clientY + pad;
    if (x + r.width > window.innerWidth - 8) x = event.clientX - r.width - pad;
    if (y + r.height > window.innerHeight - 8) y = event.clientY - r.height - pad;
    this.el.style.left = `${x}px`;
    this.el.style.top = `${y}px`;
  },
  hide() { this.el.classList.remove("show"); },
};

// Fill a <details class="data-table"> with a plain table (the accessible view of a chart).
function dataTable(selector, columns, rows) {
  const table = d3.select(selector).append("table");
  table.append("thead").append("tr").selectAll("th").data(columns).join("th").text(c => c.label);
  table.append("tbody").selectAll("tr").data(rows).join("tr")
    .selectAll("td").data(r => columns.map(c => ({ v: c.value(r), num: c.num })))
    .join("td").classed("num", d => d.num).text(d => d.v);
}

// Size an SVG to its container; returns {svg, width, height}. Re-called on resize.
function sizedSvg(container) {
  const node = d3.select(container).node();
  const { width, height } = node.getBoundingClientRect();
  const svg = d3.select(node).selectAll("svg").data([0]).join("svg").attr("viewBox", `0 0 ${width} ${height}`);
  return { svg, width, height };
}
