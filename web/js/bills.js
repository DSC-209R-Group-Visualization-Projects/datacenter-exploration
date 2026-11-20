// Chapter 4, are datacenters raising electric bills. Two charts:
// PriceChart, one dot per state, price change 2019-2025 against datacenters per resident:
//  0) the scatter with the US average   1) Virginia and the biggest increases labelled
//  2) PJM states coloured, with the two medians   3) dots regroup into columns by how the state's grid buys power
//  4) the PJM column alone (the timing warning)
// CapacityChart, the PJM capacity auction:
//  0) clearing price per MW-day   1) total cost   2-4) the market monitor's re-run without datacenter load
//  5-6) the rough add to a typical household bill, with a kWh slider (Sanjana's usage slider)
// Market colours pass the validator on --bg (all pairs); PJM is the chapter's yellow. The re-run bars use a validated
// one-hue yellow ramp. Utility-run is the neutral grey on purpose: no regional market.

const PJM = "#b68c0b";   // yellow, so bills read apart from the orange grid-risk ramp in Chapter 3
const OTHER = "#6b6a65";
const MARKETS = [
  { key: "utility", color: OTHER, label: "Utility-run, no regional market", short: "Utility-run" },
  { key: "regional", color: "#3987e5", label: "Regional market, no capacity auction", short: "No auction" },
  { key: "capacity", color: "#1baf7a", label: "Other capacity auctions", short: "Other auctions" },
  { key: "PJM", color: PJM, label: "PJM capacity auction", short: "PJM" },
];
const MARKET_BY_KEY = Object.fromEntries(MARKETS.map(m => [m.key, m]));
const ZERO = 0.2;   // where states with no datacenters sit on the log axis
const pct = v => `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v).toFixed(Math.abs(v) < 1 ? 1 : 0)}%`;

function PriceChart(container, data) {
  const STEPS = [
    { cols: false, color: "none", labels: [], sub: "Each dot is a state. Residential price change, 2019–2025, after inflation" },
    { cols: false, color: "none", labels: ["VA", "DC", "CA", "ME", "MD", "NY"], rho: true,
      sub: "Each dot is a state. Residential price change, 2019–2025, after inflation" },
    { cols: false, color: "pjm", labels: ["VA", "DC", "MD", "NJ", "PA", "OH"], medians: true,
      sub: "States on the PJM grid against every other state" },
    { cols: true, color: "market", labels: ["CA", "DC", "VA", "ME"], sub: "States grouped by how their grid buys power" },
    { cols: true, color: "market", labels: ["DC", "MD", "NJ", "VA"], focus: "PJM",
      sub: "Price data ends in 2025; the PJM auction jump began reaching bills in June 2025" },
  ];
  const states = data.states.map(d => ({ ...d, x0: d.per_m > 0 ? d.per_m : ZERO }));
  let step = 0, svg, W, H, narrow, x, y, xc, colX, g, m;

  function render() {
    const s = sizedSvg(container);
    svg = s.svg; W = s.width; H = s.height;
    svg.selectAll("*").remove();
    narrow = W < 560;
    m = { t: narrow ? 58 : 36, r: narrow ? 8 : 16, b: narrow ? 60 : 46, l: narrow ? 36 : 46 };
    x = d3.scaleLog([0.15, 75], [m.l, W - m.r]);
    y = d3.scaleLinear([-16, 38], [H - m.b, m.t]);

    // Column layout: one column per market type, dots dodged sideways so none overlap
    xc = d3.scaleBand(MARKETS.map(d => d.key), [m.l, W - m.r]).padding(0.12);
    const r = narrow ? 4.5 : 5.5;
    colX = new Map();
    for (const mk of MARKETS) {
      const placed = [];
      for (const d of states.filter(d => d.market === mk.key).sort((a, b) => a.chg - b.chg)) {
        const cy = y(d.chg);
        let k = 0, dx = 0;
        while (placed.some(p => Math.hypot(p.dx - dx, p.cy - cy) < 2 * r + 1)) { k++; dx = Math.ceil(k / 2) * (2 * r + 1) * (k % 2 ? 1 : -1); }
        placed.push({ dx, cy });
        colX.set(d.st, xc(mk.key) + xc.bandwidth() / 2 + dx);
      }
    }

    g = svg.append("g");
    g.append("g").attr("class", "axis y-axis").attr("transform", `translate(${m.l},0)`)
      .call(d3.axisLeft(y).tickValues(d3.range(-10, 38, 10)).tickSize(-(W - m.l - m.r)).tickPadding(6)
        .tickFormat(v => `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v)}%`))
      .call(a => a.select(".domain").remove())
      .call(a => a.selectAll(".tick line").attr("stroke", C.grid))
      .call(a => a.selectAll(".tick").filter(v => v === 0).select("line").attr("stroke", C.axis));
    g.append("g").attr("class", "axis x-axis x-log").attr("transform", `translate(0,${H - m.b})`)
      .call(d3.axisBottom(x).tickValues(narrow ? [ZERO, 1, 5, 20, 50] : [ZERO, 0.5, 1, 2, 5, 10, 20, 50])
        .tickFormat(v => v === ZERO ? "0" : v).tickSizeOuter(0))
      .call(a => a.append("text").attr("class", "label-muted").attr("x", W - m.r).attr("y", 36).attr("text-anchor", "end")
        .text(narrow ? "datacenters per million residents (log)" : "operating and planned datacenters per million residents (log scale)"));
    // Column labels, two lines on phones
    const xcol = g.append("g").attr("class", "x-cols").attr("opacity", 0);
    xcol.selectAll("text").data(MARKETS).join("text").attr("class", "label").attr("text-anchor", "middle")
      .attr("x", d => xc(d.key) + xc.bandwidth() / 2).attr("y", H - m.b + 18)
      .each(function (d) {
        const n = states.filter(s => s.market === d.key).length, t = d3.select(this);
        const med = `median ${pct(data.medians.market[d.key])}`;
        const lines = narrow ? d.short.split(" ").concat([pct(data.medians.market[d.key])]) : [d.label.length > 30 && xc.bandwidth() < 230 ? d.short : d.label, `${n} states · ${med}`];
        lines.forEach((l, i) => t.append("tspan").attr("x", d => xc(d.key) + xc.bandwidth() / 2).attr("dy", i ? 15 : 0)
          .attr("class", i === lines.length - 1 ? "label-muted" : null).text(l));
      });

    // US average, then the medians
    g.append("g").attr("class", "us-line").call(gg => {
      gg.append("line").attr("x1", m.l).attr("x2", W - m.r).attr("y1", y(data.us_change)).attr("y2", y(data.us_change))
        .attr("stroke", C.muted).attr("stroke-dasharray", "4 3");
      gg.append("text").attr("class", "label-muted").attr("x", W - m.r).attr("y", y(data.us_change) - 6).attr("text-anchor", "end")
        .text(`US average ${pct(data.us_change)}`);
    });
    const md = g.append("g").attr("class", "medians").attr("opacity", 0);
    [{ v: data.medians.pjm, c: PJM }, { v: data.medians.other, c: C.text2 }].forEach(d =>
      md.append("line").attr("x1", m.l).attr("x2", W - m.r).attr("y1", y(d.v)).attr("y2", y(d.v)).attr("stroke", d.c)
        .attr("stroke-width", 1.5).attr("stroke-dasharray", "6 3"));
    const cm = g.append("g").attr("class", "col-medians").attr("opacity", 0);
    for (const mk of MARKETS) {
      const v = data.medians.market[mk.key], x0 = xc(mk.key), bw = xc.bandwidth();
      cm.append("line").attr("x1", x0 + bw * 0.12).attr("x2", x0 + bw * 0.88).attr("y1", y(v)).attr("y2", y(v))
        .attr("stroke", C.text).attr("stroke-width", 2).attr("data-key", mk.key);
    }
    g.append("text").attr("class", "rho label-muted").attr("x", m.l + 8).attr("y", m.t + 4).attr("opacity", 0)
      .text(`rank correlation ${data.rho.toFixed(2).replace("-", "−")}`);

    // Dots and their labels
    g.append("g").attr("class", "dots").selectAll("circle").data(states, d => d.st).join("circle")
      .attr("r", r).attr("stroke", C.bg).attr("stroke-width", 1.2).attr("cy", d => y(d.chg)).attr("cx", d => x(d.x0))
      .on("pointerenter pointermove", (e, d) => tip.show(`<b>${d.name}</b><br>${d.dc} datacenters (${d.per_m.toFixed(1)} per million residents)` +
        `<br>${d.p0.toFixed(1)} → ${d.p1.toFixed(1)} cents/kWh (2025 $)<br>${pct(d.chg)} after inflation` +
        `<br><span style="color:${C.muted}">${MARKET_BY_KEY[d.market].label}</span>`, e))
      .on("pointerleave", () => tip.hide());
    g.append("g").attr("class", "dot-labels").attr("pointer-events", "none").selectAll("text").data(states, d => d.st).join("text")
      .attr("class", "label-strong").attr("dy", 4).attr("stroke", C.bg).attr("stroke-width", 3).attr("paint-order", "stroke")
      .attr("opacity", 0).text(d => d.st === "VA" ? `Virginia ${pct(d.chg)}` : d.st);

    // Legends: PJM against the rest (step 2), then the four market types (steps 3-4), laid out by measured width
    const legend = (cls, keys) => {
      const kg = svg.append("g").attr("class", cls).attr("opacity", 0).selectAll("g").data(keys).join("g");
      kg.append("circle").attr("cx", 5).attr("cy", 6).attr("r", 5).attr("fill", d => d.color);
      kg.append("text").attr("class", "label").attr("x", 14).attr("y", 10.5).text(d => d.label);
      let lx = 0, ly = 0;
      kg.attr("transform", function () {
        const w = this.getBBox().width + 16;
        if (lx + w > W && lx > 0) { lx = 0; ly += 20; }
        const t = `translate(${lx},${ly})`; lx += w; return t;
      });
    };
    legend("legend-pjm", [{ color: PJM, label: `PJM states (dashed line: median ${pct(data.medians.pjm)})` },
      { color: OTHER, label: `all other states (median ${pct(data.medians.other)})` }]);
    legend("legend-market", MARKETS.map(d => ({ color: d.color, label: narrow ? d.short : d.label })));

    update(step, 0);
  }

  function update(i, dur = DUR) {
    step = i;
    const st = STEPS[i], t = svg.transition().duration(dur).ease(d3.easeCubicInOut);
    d3.select("#bills-sub").text(st.sub);
    const fill = d => st.color === "pjm" ? (d.pjm ? PJM : OTHER) : st.color === "market" ? MARKET_BY_KEY[d.market].color
      : st.labels.includes(d.st) ? C.text : "#8a8882";
    const op = d => st.focus && d.market !== st.focus ? 0.25 : 1;
    const cx = d => st.cols ? colX.get(d.st) : x(d.x0);
    svg.selectAll(".dots circle").transition(t).attr("cx", cx).attr("fill", fill).attr("opacity", op);
    // Virginia sits at the right edge of the scatter, so its label goes on the left there
    const left = d => d.st === "VA" && !st.cols;
    const labels = narrow && st.color === "pjm" ? ["VA", "DC", "MD"] : st.labels;
    svg.selectAll(".dot-labels text").transition(t).attr("x", d => cx(d) + (left(d) ? -9 : 9))
      .attr("text-anchor", d => left(d) ? "end" : "start").attr("y", d => y(d.chg)).attr("opacity", d => labels.includes(d.st) ? 1 : 0);
    svg.selectAll(".dot-labels text").filter(d => d.st === "VA").text(d => narrow && st.cols ? "VA" : `Virginia ${pct(d.chg)}`);
    svg.select(".x-log").transition(t).attr("opacity", st.cols ? 0 : 1);
    svg.select(".x-cols").transition(t).attr("opacity", st.cols ? 1 : 0);
    svg.select(".us-line").transition(t).attr("opacity", st.medians ? 0.35 : st.cols ? 0 : 1);
    svg.select(".medians").transition(t).attr("opacity", st.medians ? 1 : 0);
    svg.select(".col-medians").transition(t).attr("opacity", st.cols ? 1 : 0);
    svg.selectAll(".col-medians [data-key]").transition(t).attr("opacity", function () {
      return st.focus && this.dataset.key !== st.focus ? 0.3 : 1; });
    svg.select(".rho").transition(t).attr("opacity", st.rho ? 1 : 0);
    svg.select(".legend-market").transition(t).attr("opacity", st.color === "market" ? 1 : 0);
    svg.select(".legend-pjm").transition(t).attr("opacity", st.color === "pjm" ? 1 : 0);
  }

  render();
  window.addEventListener("resize", debounce(render, 150));
  return { update: i => update(i) };
}

function CapacityChart(container, data) {
  const STEPS = [
    { mode: "price", title: "PJM capacity auction clearing price", sub: "$ per MW-day, as published, by delivery year (June to May)" },
    { mode: "cost", title: "PJM capacity auction total cost", sub: "$ billion, as published, by delivery year (June to May)" },
    { mode: "imm", rows: 2, title: "The market monitor's re-run of the 2025/26 auction", sub: "Total capacity auction cost, $ billion, 2025 dollars" },
    { mode: "imm", rows: 4, title: "The market monitor's re-run of the 2025/26 auction", sub: "Total capacity auction cost, $ billion, 2025 dollars" },
    { mode: "imm", rows: 4, band: true, title: "The market monitor's re-run of the 2025/26 auction", sub: "Total capacity auction cost, $ billion, 2025 dollars" },
    { mode: "bill", title: "Rough add to a typical PJM household bill", sub: "" },
    { mode: "bill", title: "Rough add to a typical PJM household bill", sub: "" },
  ];
  const SOURCES = {
    price: "Source: PJM Base Residual Auction reports. Clearing prices are as published (RTO price).",
    imm: "Source: Monitoring Analytics (PJM's Independent Market Monitor), \"Analysis of the 2025/2026 RPM Base Residual Auction, Part G\", June 3, 2025, Table 7. A model re-run that holds every bid fixed, not something anyone observed. 2024/25 is converted to 2025 dollars (BLS CPI-U).",
    bill: "The auction cost is spread evenly over every kWh in PJM, in 2025 dollars (BLS CPI-U, by the year each delivery period starts). Households use more power at peak times, so their real share is likely higher. Split of 2025/26 from the market monitor's re-run without datacenter load. Sources: PJM Base Residual Auction reports; Monitoring Analytics, Part G, June 3, 2025.",
  };
  SOURCES.cost = SOURCES.price;
  const A = data.auctions, typical = data.typical_kwh, imm = data.imm;
  const fmt1 = d3.format(".1f");
  let step = 0, kwh = typical, svg, W, H, narrow, x, m;

  function render() {
    const s = sizedSvg(container);
    svg = s.svg; W = s.width; H = s.height;
    svg.selectAll("*").remove();
    narrow = W < 560;
    m = { t: 34, r: narrow ? 6 : 16, b: 44, l: narrow ? 40 : 50 };
    x = d3.scaleBand(A.map(d => d.year), [m.l, W - m.r]).padding(0.3);
    const key = narrow ? ["2018/19", "2024/25", "2025/26", "2027/28"] : A.map(d => d.year);

    // Shared delivery-year axis for price, cost and bill
    const yr = svg.append("g").attr("class", "years-g");
    yr.append("g").attr("class", "axis y-axis").attr("transform", `translate(${m.l},0)`);
    yr.append("g").attr("class", "axis x-axis").attr("transform", `translate(0,${H - m.b})`)
      .call(d3.axisBottom(x).tickSizeOuter(0).tickSize(0).tickPadding(8)
        .tickFormat((d, i) => narrow ? (i % 2 ? "" : d.slice(2)) : d))
      .call(a => a.select(".domain").attr("stroke", C.axis))
      .call(a => a.append("text").attr("class", "label-muted").attr("x", W - m.r).attr("y", 36).attr("text-anchor", "end")
        .text("delivery year, June to May"));

    // Price: a step line with dots
    const pg = yr.append("g").attr("class", "m-price");
    pg.append("path").attr("class", "price-line").attr("fill", "none").attr("stroke", PJM).attr("stroke-width", 2);
    pg.selectAll("circle").data(A).join("circle").attr("cx", d => x(d.year) + x.bandwidth() / 2).attr("r", 4.5)
      .attr("fill", PJM).attr("stroke", C.bg).attr("stroke-width", 2)
      .on("pointerenter pointermove", (e, d) => tip.show(`<b>${d.year}</b><br>$${d3.format(",.2f")(d.price)} per MW-day` +
        `<br>total cost $${d.cost}B (as published)<br>reserve margin ${d.margin}%`, e))
      .on("pointerleave", () => tip.hide());
    pg.selectAll("text.v").data(A.filter(d => key.includes(d.year))).join("text").attr("class", "v label")
      .attr("x", d => x(d.year) + x.bandwidth() / 2).attr("text-anchor", "middle").text(d => `$${Math.round(d.price)}`);
    pg.append("text").attr("class", "jump label-strong").attr("text-anchor", "end").text("9.3× jump");

    // Cost and bill: bars
    const cg = yr.append("g").attr("class", "m-cost");
    cg.selectAll("path").data(A).join("path").attr("fill", d => d.start >= 2025 ? PJM : OTHER)
      .on("pointerenter pointermove", (e, d) => tip.show(`<b>${d.year}</b><br>$${d.cost} billion (as published)` +
        `<br>$${fmt1(d.cost_real)} billion in 2025 dollars`, e))
      .on("pointerleave", () => tip.hide());
    cg.selectAll("text").data(A.filter(d => key.includes(d.year))).join("text").attr("class", "label")
      .attr("x", d => x(d.year) + x.bandwidth() / 2).attr("text-anchor", "middle").text(d => narrow ? `$${Math.round(d.cost)}B` : `$${d.cost}B`);
    const bg = yr.append("g").attr("class", "m-bill");
    bg.selectAll("path.bar").data(A).join("path").attr("class", "bar").attr("fill", d => d.start === 2025 ? "#8a8882" : d.start > 2025 ? "#5c4813" : "#4a4945")
      .on("pointerenter pointermove", (e, d) => tip.show(`<b>${d.year}</b><br>about $${fmt1(d.month * kwh / typical)} a month` +
        `<br><span style="color:${C.muted}">at ${kwh} kWh a month, 2025 dollars</span>` +
        (d.start === 2025 ? `<br>datacenter demand: about $${fmt1(data.dc_part * kwh / typical)}` : ""), e))
      .on("pointerleave", () => tip.hide());
    bg.append("path").attr("class", "dc-part").attr("fill", PJM).attr("stroke", C.bg).attr("stroke-width", 2).attr("pointer-events", "none");
    bg.append("text").attr("class", "dc-label").attr("text-anchor", "middle").attr("fill", C.bg).attr("font-weight", 700)
      .attr("font-size", narrow ? 11 : 12.5).attr("pointer-events", "none");
    bg.selectAll("text.v").data(A.filter(d => key.includes(d.year))).join("text").attr("class", "v label")
      .attr("x", d => x(d.year) + x.bandwidth() / 2).attr("text-anchor", "middle");
    const bl = bg.append("g").attr("class", "legend");
    [{ c: "#4a4945", t: narrow ? "earlier" : "earlier auctions" }, { c: "#8a8882", t: narrow ? "anyway" : "2025/26 without datacenters" },
     { c: PJM, t: narrow ? "datacenters" : "2025/26 datacenter demand (monitor)" }, { c: "#5c4813", t: narrow ? "not split" : "later auctions, not split" }]
      .forEach(d => {
        const k = bl.append("g");
        k.append("rect").attr("width", 12).attr("height", 12).attr("rx", 2).attr("fill", d.c);
        k.append("text").attr("class", "label").attr("x", 17).attr("y", 10.5).text(d.t);
      });
    let lx = 0;
    bl.selectAll("g").attr("transform", function () { const t = `translate(${lx},0)`; lx += this.getBBox().width + 16; return t; });

    // IMM re-run: four horizontal bars
    const ig = svg.append("g").attr("class", "m-imm");
    const rows = [
      { label: "2024/25 auction (actual)", v: imm.prior, c: OTHER },
      { label: "2025/26 re-run, no datacenter load", v: imm.no_dc, c: "#5c4813", note: `+$${fmt1(imm.no_dc - imm.prior)}B from other causes` },
      { label: "2025/26 re-run, no new datacenter load", v: imm.no_new_dc, c: "#8a6b10" },
      { label: "2025/26 auction (actual)", v: imm.actual, c: PJM, note: `+$${fmt1(imm.actual - imm.no_dc)}B from datacenters` },
    ];
    const labW = narrow ? 0 : Math.min(270, W * 0.34), xi = immX();
    const top = m.t + 34, rowH = Math.min(narrow ? 90 : 110, (H - top - 40) / rows.length), bh = Math.min(30, rowH * 0.42);
    ig.append("g").attr("class", "axis x-axis").attr("transform", `translate(0,${top + rows.length * rowH})`)
      .call(d3.axisBottom(xi).ticks(narrow ? 3 : 4).tickFormat(v => `$${v}B`).tickSize(-(rows.length * rowH + 10)).tickPadding(6))
      .call(a => a.select(".domain").remove()).call(a => a.selectAll(".tick line").attr("stroke", C.grid));
    const early = A.filter(d => d.start <= 2021).map(d => d.cost_real);
    ig.append("g").attr("class", "band").attr("opacity", 0).call(b => {
      b.append("rect").attr("x", xi(d3.min(early))).attr("width", xi(d3.max(early)) - xi(d3.min(early)))
        .attr("y", top - 22).attr("height", rows.length * rowH + 22).attr("fill", "rgba(255,255,255,0.06)");
      b.append("text").attr("class", "label-muted").attr("x", xi(d3.mean([d3.min(early), d3.max(early)]))).attr("y", top - 8)
        .attr("text-anchor", "middle").text(narrow ? "2017–2021 range" : `2017/18–2021/22 range, $${fmt1(d3.min(early))}–${fmt1(d3.max(early))}B`);
    });
    const rg = ig.selectAll("g.row").data(rows).join("g").attr("class", "row")
      .attr("transform", (_, i) => `translate(0,${top + i * rowH + (narrow ? 18 : 10)})`);
    rg.append("text").attr("class", "label").attr("x", narrow ? 0 : labW - 10).attr("y", narrow ? -6 : bh / 2 + 4)
      .attr("text-anchor", narrow ? "start" : "end").text(d => d.label);
    rg.append("path").attr("fill", d => d.c)
      .on("pointerenter pointermove", (e, d) => tip.show(`<b>${d.label}</b><br>$${d3.format(".2f")(d.v)} billion`, e))
      .on("pointerleave", () => tip.hide());
    ig.attr("data-bh", bh);
    rg.append("text").attr("class", "v label-strong").attr("y", bh / 2 + 4);

    update(step, 0);
  }

  function setBill(dur) {
    const sc = kwh / typical, yb = d3.scaleLinear([0, Math.max(20, d3.max(A, d => d.month) * sc * 1.12)], [H - m.b, m.t + 30]).nice();
    const t = svg.transition().duration(dur);
    svg.select(".years-g .y-axis").transition(t).call(d3.axisLeft(yb).ticks(5).tickFormat(v => `$${v}`).tickSize(-(W - m.l - m.r)).tickPadding(6))
      .call(a => a.select(".domain").remove()).call(a => a.selectAll(".tick line").attr("stroke", C.grid));
    svg.selectAll(".m-bill path.bar").transition(t).attr("d", d => bar(x(d.year), yb, d.month * sc));
    const j = A.find(d => d.start === 2025), dc = data.dc_part * sc, rest = j.month * sc - dc;
    svg.select(".m-bill .dc-part").transition(t).attr("d", bar(x(j.year), yb, dc, rest));
    svg.select(".m-bill .dc-label").transition(t).attr("x", x(j.year) + x.bandwidth() / 2).attr("y", yb(rest + dc / 2) + 4)
      .text(x.bandwidth() > 34 ? `~$${Math.round(dc)}` : "");
    svg.selectAll(".m-bill text.v").transition(t).attr("y", d => yb(d.month * sc) - 6).text(d => `$${Math.round(d.month * sc)}`);
    svg.select(".m-bill .legend").attr("transform", `translate(${m.l},${m.t - 4})`);
    d3.select("#capacity-sub").text(`$ a month for capacity, 2025 dollars, at ${kwh} kWh a month`);
  }

  // A vertical bar with a 4px rounded top, from base value b0 up by v
  function bar(x0, yy, v, b0 = 0) {
    const w = x.bandwidth(), y1 = yy(b0 + v), y0 = yy(b0), h = Math.max(0, y0 - y1), rr = b0 > 0 || v > 0 ? Math.min(4, h, w / 2) : 0;
    return `M${x0},${y0}v${-(h - rr)}a${rr},${rr} 0 0 1 ${rr},${-rr}h${w - 2 * rr}a${rr},${rr} 0 0 1 ${rr},${rr}v${h - rr}z`;
  }

  function update(i, dur = DUR) {
    step = i;
    const st = STEPS[i], t = svg.transition().duration(dur).ease(d3.easeCubicInOut);
    d3.select("#capacity-title").text(st.title);
    d3.select("#capacity-sub").text(st.sub);
    d3.select("#capacity-source").text(SOURCES[st.mode]);
    d3.select("#capacity-kwh").classed("show", st.mode === "bill");
    for (const md of ["price", "cost", "bill", "imm"])
      svg.select(`.m-${md}`).attr("pointer-events", st.mode === md ? "all" : "none").transition(t).attr("opacity", st.mode === md ? 1 : 0);
    // Named transitions, so the fade doesn't cancel the y axis rescale below
    svg.selectAll(".years-g .axis").transition("fade").duration(dur).attr("opacity", st.mode === "imm" ? 0 : 1);

    if (st.mode === "price" || st.mode === "cost") {
      const yv = st.mode === "price" ? d3.scaleLinear([0, 400], [H - m.b, m.t]) : d3.scaleLinear([0, 20], [H - m.b, m.t]);
      svg.select(".years-g .y-axis").transition(t)
        .call(d3.axisLeft(yv).ticks(5).tickFormat(v => st.mode === "price" ? `$${v}` : `$${v}B`).tickSize(-(W - m.l - m.r)).tickPadding(6))
        .call(a => a.select(".domain").remove()).call(a => a.selectAll(".tick line").attr("stroke", C.grid));
      if (st.mode === "price") {
        const cx = d => x(d.year) + x.bandwidth() / 2;
        svg.select(".price-line").attr("d", d3.line().x(cx).y(d => yv(d.price)).curve(d3.curveStep)(A));
        svg.selectAll(".m-price circle").attr("cy", d => yv(d.price));
        svg.selectAll(".m-price text.v").attr("y", d => yv(d.price) - 11);
        const j = A.find(d => d.start === 2025);
        const prev = A[A.indexOf(j) - 1];
        svg.select(".m-price .jump").attr("x", (cx(prev) + cx(j)) / 2 - 8).attr("y", yv((prev.price + j.price) / 2));
      } else {
        svg.selectAll(".m-cost path").transition(t).attr("d", d => bar(x(d.year), yv, d.cost));
        svg.selectAll(".m-cost text").transition(t).attr("y", d => yv(d.cost) - 6);
      }
    }
    if (st.mode !== "cost") svg.selectAll(".m-cost path").transition(t).attr("d", d => bar(x(d.year), d3.scaleLinear([0, 20], [H - m.b, m.t]), 0));
    if (st.mode === "bill") setBill(dur);
    else {
      const y0 = d3.scaleLinear([0, 20], [H - m.b, m.t]), j = A.find(d => d.start === 2025);
      svg.selectAll(".m-bill path.bar").transition(t).attr("d", d => bar(x(d.year), y0, 0));
      svg.select(".m-bill .dc-part").transition(t).attr("d", bar(x(j.year), y0, 0));
    }

    // IMM rows: grow in; the two re-runs wait until step 3
    const labW = narrow ? 0 : Math.min(270, W * 0.34), xi = immX(), bh = +svg.select(".m-imm").attr("data-bh");
    const shown = (d, k) => st.mode === "imm" && (st.rows === 4 || k === 0 || k === 3);
    svg.selectAll(".m-imm g.row").each(function (d, k) {
      const on = shown(d, k), w = on ? xi(d.v) - labW : 0;
      const row = d3.select(this);
      row.select("path").transition(t).attr("d", hbar(labW, w, bh));
      // The "+$X from ..." notes compare against the re-run, so they wait for all four rows
      row.select("text.v").text(`$${fmt1(d.v)}B` + (d.note && !narrow && st.rows === 4 ? `  ${d.note}` : ""))
        .transition(t).attr("x", labW + w + 8).attr("opacity", on ? 1 : 0);
      row.select("text.label").transition(t).attr("opacity", on ? 1 : 0.35);
    });
    svg.select(".m-imm .band").transition(t).attr("opacity", st.band ? 1 : 0);
  }

  // IMM x scale: room on the right for "$14.7B  +$9.3B from datacenters" (just the value on phones)
  function immX() {
    const labW = narrow ? 0 : Math.min(270, W * 0.34);
    return d3.scaleLinear([0, 18], [labW, W - m.r - (narrow ? 50 : 210)]);
  }

  function hbar(left, w, bh) {   // 4px rounded data end, square at the baseline
    const rr = Math.max(0, Math.min(4, w, bh / 2));
    return `M${left},0h${Math.max(0, w - rr)}a${rr},${rr} 0 0 1 ${rr},${rr}v${bh - 2 * rr}a${rr},${rr} 0 0 1 ${-rr},${rr}h${Math.min(0, rr - w)}z`;
  }

  // Usage slider: set your own monthly kWh
  const input = d3.select("#capacity-kwh input").attr("value", typical).property("value", typical);
  input.on("input", function () {
    kwh = +this.value;
    d3.select("#capacity-kwh output").text(`${kwh} kWh`);
    if (STEPS[step].mode === "bill") setBill(0);
  });
  d3.select("#capacity-kwh output").text(`${kwh} kWh`);
  d3.select("#capacity-source").on("click", function () { this.classList.toggle("open"); });
  render();
  window.addEventListener("resize", debounce(render, 150));
  return { update: i => update(i) };
}

async function initBills() {
  const data = await d3.json("data/bills.json");
  const price = PriceChart("#chart-bills", data);
  d3.select("#bills-source").on("click", function () { this.classList.toggle("open"); });
  const capacity = CapacityChart("#chart-capacity", data);
  const rows = [...data.states].sort((a, b) => b.chg - a.chg);
  dataTable("#table-bills", [
    { label: "State", value: r => r.name },
    { label: "Datacenters", value: r => r.dc, num: true },
    { label: "Per million residents", value: r => r.per_m.toFixed(1), num: true },
    { label: `${data.base} price (¢/kWh, 2025 $)`, value: r => r.p0.toFixed(1), num: true },
    { label: `${data.end} price`, value: r => r.p1.toFixed(1), num: true },
    { label: "Change", value: r => pct(r.chg), num: true },
    { label: "How the grid buys power", value: r => MARKET_BY_KEY[r.market].label },
  ], rows);
  dataTable("#table-capacity", [
    { label: "Delivery year", value: r => r.year },
    { label: "Clearing price ($/MW-day)", value: r => d3.format(",.2f")(r.price), num: true },
    { label: "Total cost ($B, as published)", value: r => r.cost, num: true },
    { label: "Total cost ($B, 2025 $)", value: r => r.cost_real.toFixed(1), num: true },
    { label: `Typical bill add ($/month, ${data.typical_kwh} kWh)`, value: r => r.month.toFixed(2), num: true },
  ], data.auctions);
  return { "scrolly-bills": price, "scrolly-capacity": capacity };
}
