// Chapter 5, is there enough water. One figure that turns from a map into bars:
//  0) the sites on a plain map   1) counties shaded by how much of them is under high water stress
//  2) sites outside high-stress basins dim, leaving the ~500 that are (the notebook's D3 note)
//  3) the map gives way to bars: sites by the stress of their basin, with the US population for reference
//  4) the verdict, with the high-stress part of each bar in focus
// Water is a one-hue teal ramp that brightens with stress (validated as an ordinal ramp on --bg).
// Sites are pale dots, as in Chapter 3, so the teal reads only as water.

const W_BINS = [0.2, 0.4, 0.6, 0.8];
const W_COLORS = ["#235550", "#2b7068", "#358c82", "#46aa9e", "#6cc9bd"];
const W_LABELS = ["1–20%", "20–40%", "40–60%", "60–80%", "80–100%"];
// Basin stress, most stressed first (same order as the notebook bars). Arid is grey: little water, but little use either
const STRESS_COLORS = ["#a3e6dc", "#6cc9bd", "#358c82", "#2b7068", "#235550", "#4a4945"];
const STRESS_SHORT = ["Extremely high", "High", "Medium-high", "Low-medium", "Low", "Arid"];

function WaterChart(container, data, states) {
  const fmt = d3.format(",");
  const tot = g => d3.sum(data.counts[g]);
  const high = g => data.counts[g][0] + data.counts[g][1];
  const nHigh = high("operating") + high("pipeline");
  const STEPS = [
    { view: "map", sub: "Operating and planned datacenters" },
    { view: "map", shade: true, sub: "Share of each county in high or extremely high water stress" },
    { view: "map", shade: true, lit: true, sub: `The ${fmt(nHigh)} datacenters in basins under high or extremely high water stress` },
    { view: "bars", sub: "Share of sites by the water stress of their river basin (numbers are site counts)" },
    { view: "bars", focus: true, sub: "Share of sites by the water stress of their river basin (numbers are site counts)" },
  ];
  const ROWS = [
    { key: "operating", label: `Operating (${fmt(tot("operating"))} sites)`, short: `Operating (${fmt(tot("operating"))})`,
      shares: data.counts.operating.map(n => n / tot("operating") * 100), counts: data.counts.operating },
    { key: "pipeline", label: `Planned (${fmt(tot("pipeline"))} sites)`, short: `Planned (${fmt(tot("pipeline"))})`,
      shares: data.counts.pipeline.map(n => n / tot("pipeline") * 100), counts: data.counts.pipeline },
    { key: "pop", label: "US population", short: "US population", shares: data.pop_share, counts: null },
  ];
  let step = 0, svg, W, H, narrow;

  function render() {
    const s = sizedSvg(container);
    svg = s.svg; W = s.width; H = s.height;
    svg.selectAll("*").remove();
    narrow = W < 560;
    renderMap();
    renderBars();
    update(step, 0);
  }

  function renderMap() {
    const TOP = narrow ? 78 : 56;   // legend rows above the map
    const proj = d3.geoAlbersUsa().fitExtent([[0, TOP + 6], [W, H - (narrow ? 0 : 24)]], { type: "FeatureCollection", features: states });
    const path = d3.geoPath(proj);
    const g = svg.append("g").attr("class", "w-map");
    g.append("path").attr("d", path({ type: "FeatureCollection", features: states })).attr("fill", "#1c1c1b");
    g.append("g").attr("class", "w-counties").selectAll("path").data(data.counties).join("path")
      .attr("d", path).attr("fill", f => W_COLORS[d3.bisectLeft(W_BINS, f.properties.share)])
      .on("pointerenter pointermove", (e, f) => tip.show(`<b>${f.properties.name}</b><br>${Math.round(f.properties.share * 100)}% in high or extremely high water stress`, e))
      .on("pointerleave", () => tip.hide());
    g.append("path").attr("pointer-events", "none").attr("d", path({ type: "FeatureCollection", features: states }))
      .attr("fill", "none").attr("stroke", "rgba(255,255,255,0.14)").attr("stroke-width", 0.6);

    const sites = data.sites.map(d => { const xy = proj([d[0], d[1]]); return xy && { x: xy[0], y: xy[1], op: d[2] === 1, stress: d[3] }; })
      .filter(Boolean).sort((a, b) => a.op - b.op);
    const r = narrow ? 1.5 : 2;
    const sg = g.append("g").attr("class", "w-sites").attr("pointer-events", "none");
    sg.selectAll("circle").data(sites.filter(d => d.stress >= 0)).join("circle")
      .attr("cx", d => d.x).attr("cy", d => d.y).attr("r", d => r * (d.op ? 1 : 0.9))
      .attr("fill", d => d.op ? C.text : "none").attr("stroke", d => d.op ? C.bg : C.text).attr("stroke-width", d => d.op ? 0.4 : 0.8);
    // Sites where Aqueduct has no value (mostly metro Atlanta): small crosses, left out of the shares
    const x = r + 0.6;
    sg.selectAll("path").data(sites.filter(d => d.stress < 0)).join("path").attr("class", "w-gap")
      .attr("d", d => `M${d.x - x},${d.y - x}L${d.x + x},${d.y + x}M${d.x - x},${d.y + x}L${d.x + x},${d.y - x}`)
      .attr("stroke", C.muted).attr("stroke-width", 1);

    // Top states for the lit step, bottom right under the map
    const top = Object.entries(data.top_states).map(([st, n]) => `${st} ${n}`).join(" · ");
    g.append("text").attr("class", "label w-top").attr("x", W).attr("y", H - 4).attr("text-anchor", "end")
      .text(narrow ? top : `Most in high-stress basins: ${top}`);

    // Legend: the county ramp, then the site keys
    const leg = g.append("g").attr("class", "legend");
    leg.append("text").attr("class", "label-muted w-ramp").attr("y", 11).text("share of county in high or extremely high stress");
    const sw = narrow ? Math.min(52, (W - 4) / 5) : 52;
    const bins = leg.append("g").attr("class", "w-ramp").attr("transform", "translate(0,18)").selectAll("g").data(W_COLORS).join("g")
      .attr("transform", (_, i) => `translate(${i * sw},0)`);
    bins.append("rect").attr("width", sw - 2).attr("height", 10).attr("rx", 2).attr("fill", c => c);
    bins.append("text").attr("class", "label-muted").attr("x", (sw - 2) / 2).attr("y", 24).attr("text-anchor", "middle")
      .text((_, i) => W_LABELS[i]);
    const keys = leg.append("g").attr("transform", narrow ? "translate(4,66)" : `translate(${5 * sw + 24},23)`);
    const k = [
      { label: "operating", draw: s => s.append("circle").attr("r", 3).attr("fill", C.text) },
      { label: "planned", draw: s => s.append("circle").attr("r", 2.6).attr("fill", "none").attr("stroke", C.text).attr("stroke-width", 1) },
      { label: `no water data (${data.no_basin})`, draw: s => s.append("path").attr("d", "M-3,-3L3,3M-3,3L3,-3").attr("stroke", C.muted).attr("stroke-width", 1.2) },
    ];
    const kg = keys.selectAll("g").data(k).join("g");
    kg.each(function (d) { d.draw(d3.select(this)); });
    kg.append("text").attr("class", "label").attr("x", 8).attr("y", 4).text(d => d.label);
    let kx = 0;
    kg.attr("transform", function () { const x0 = kx; kx += this.getBBox().width + 16; return `translate(${x0},0)`; });
  }

  function renderBars() {
    const g = svg.append("g").attr("class", "w-bars").attr("opacity", 0).attr("pointer-events", "none");
    const labW = narrow ? 0 : 150, top = narrow ? 92 : 80, bh = narrow ? 20 : 30;
    const rowH = Math.min(narrow ? 120 : 150, (H - top - 30) / 3);
    const x = d3.scaleLinear([0, 100], [labW, W - 4]);

    g.append("g").attr("class", "axis").attr("transform", `translate(0,${top + rowH * 3 - 18})`)
      .call(d3.axisBottom(x).ticks(narrow ? 4 : 5).tickFormat(d => d + "%").tickSize(-(rowH * 3 - 18)))
      .call(a => a.select(".domain").remove())
      .call(a => a.selectAll(".tick line").attr("stroke", C.grid));

    ROWS.forEach((row, i) => {
      const y = top + i * rowH + (narrow ? 24 : 18);
      const rg = g.append("g").attr("class", `w-row w-row-${row.key}`).attr("transform", `translate(0,${y})`);
      const hp = row.shares[0] + row.shares[1];
      // Phones have no room under the bar, so the high-stress share joins the row label
      const short = `${row.short}: ${Math.round(hp)}% in high stress` + (row.counts ? ` (${high(row.key)})` : "");
      rg.append("text").attr("class", i < 2 ? "label label-strong" : "label").attr("x", narrow ? 0 : labW - 12)
        .attr("y", narrow ? -8 : bh / 2 + 4).attr("text-anchor", narrow ? "start" : "end").text(narrow ? short : row.label);
      let acc = 0;
      const segs = row.shares.map((p, k) => { const s = { k, p, x0: acc, n: row.counts && row.counts[k] }; acc += p; return s; });
      rg.selectAll("rect").data(segs).join("rect").attr("class", d => d.k < 2 ? "w-hi" : "w-lo")
        .attr("x", d => x(d.x0) + (d.k ? 1 : 0)).attr("width", d => Math.max(0, x(d.x0 + d.p) - x(d.x0) - (d.k ? 2 : 0)))
        .attr("y", 0).attr("height", bh).attr("fill", d => STRESS_COLORS[d.k])
        .on("pointerenter pointermove", (e, d) => tip.show(`<b>${row.label}</b><br>${data.stress[d.k]}: ` +
          (d.n != null ? `${fmt(d.n)} sites (${Math.round(d.p)}%)` : `${d.p.toFixed(1)}% of people`), e))
        .on("pointerleave", () => tip.hide());
      // Counts inside the wider segments (dark ink on the bright high-stress steps)
      rg.selectAll("text.w-n").data(segs.filter(d => d.n != null && x(d.x0 + d.p) - x(d.x0) > (narrow ? 22 : 26))).join("text")
        .attr("class", d => `label w-n ${d.k < 2 ? "w-hi" : "w-lo"}`).attr("x", d => x(d.x0 + d.p / 2)).attr("y", bh / 2 + 4)
        .attr("text-anchor", "middle").style("fill", d => d.k < 2 ? C.bg : C.text).text(d => d.n);
      // Bracket under the high-stress part
      rg.append("path").attr("d", `M${x(0)},${bh + 5}V${bh + 9}H${x(hp)}V${bh + 5}`).attr("fill", "none").attr("stroke", C.text2);
      if (!narrow) rg.append("text").attr("class", "label label-strong").attr("x", x(0)).attr("y", bh + 25)
        .text(row.counts ? `${Math.round(hp)}% high or extremely high (${high(row.key)})` : `${data.pop_high.toFixed(0)}% of Americans`);
    });

    // Legend: six stress levels, wrapped by measured width
    const leg = g.append("g").attr("class", "legend");
    leg.append("text").attr("class", "label-muted").attr("y", 11).text("water stress of the river basin");
    const kg = leg.selectAll("g").data(STRESS_SHORT).join("g");
    kg.append("rect").attr("width", 12).attr("height", 12).attr("rx", 2).attr("fill", (_, k) => STRESS_COLORS[k]);
    kg.append("text").attr("class", "label").attr("x", 17).attr("y", 10.5).text(d => d);
    let lx = 0, ly = 20;
    kg.attr("transform", function () {
      const w = this.getBBox().width;
      if (lx && lx + w > W) { lx = 0; ly += 20; }
      const t = `translate(${lx},${ly})`; lx += w + 14; return t;
    });
  }

  function update(i, dur = DUR) {
    step = i;
    const st = STEPS[i], t = svg.transition().duration(dur).ease(d3.easeCubicInOut);
    d3.select("#water-sub").text(st.sub);
    const map = st.view === "map";
    svg.select(".w-map").attr("pointer-events", map ? "all" : "none").transition(t).attr("opacity", map ? 1 : 0);
    svg.select(".w-bars").attr("pointer-events", map ? "none" : "all").transition(t).attr("opacity", map ? 0 : 1);
    // Counties step back a little once the sites are lit, so the pale dots read on the bright teal
    svg.selectAll(".w-counties path").transition(t).attr("opacity", st.shade ? (st.lit ? 0.6 : 1) : 0);
    svg.selectAll(".w-ramp").transition(t).attr("opacity", st.shade ? 1 : 0.25);
    svg.selectAll(".w-sites circle").transition(t)
      .attr("opacity", d => !st.lit ? (d.op ? 0.85 : 0.55) : d.stress <= 1 ? 1 : 0.12);
    svg.selectAll(".w-gap").transition(t).attr("opacity", st.lit ? 0.9 : 0.5);
    svg.select(".w-top").transition(t).attr("opacity", st.lit ? 1 : 0);
    svg.selectAll(".w-bars .w-lo").transition(t).attr("opacity", st.focus ? 0.3 : 1);
  }

  render();
  window.addEventListener("resize", debounce(render, 150));
  return { update: i => update(i) };
}

async function initWater() {
  const [data, buildout] = await Promise.all([d3.json("data/water.json"), d3.json("data/buildout.json")]);
  const chart = WaterChart("#chart-water", data, buildout.states);
  d3.select("#water-source").on("click", function () { this.classList.toggle("open"); });
  const op = d3.sum(data.counts.operating), pl = d3.sum(data.counts.pipeline);
  dataTable("#table-water", [
    { label: "Basin water stress", value: r => r.stress },
    { label: "Operating", value: r => r.op, num: true },
    { label: "% of operating", value: r => (r.op / op * 100).toFixed(1), num: true },
    { label: "Planned", value: r => r.pl, num: true },
    { label: "% of planned", value: r => (r.pl / pl * 100).toFixed(1), num: true },
    { label: "% of US population", value: r => r.pop.toFixed(1), num: true },
  ], data.stress.map((s, k) => ({ stress: s, op: data.counts.operating[k], pl: data.counts.pipeline[k], pop: data.pop_share[k] })));
  return { "scrolly-water": chart };
}
