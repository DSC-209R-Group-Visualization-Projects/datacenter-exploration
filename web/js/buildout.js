// Chapter 1, the build-out. One map that changes with each step:
//  0) states shaded by operating datacenters, one dot per site
//  1) zoom into Virginia's counties
//  2) back out, with Virginia, Georgia and Texas highlighted and a bar comparing them
//  3) planned sites drop in and states recolour to their total if every planned site is built
// Bins match the notebook maps (0 | 1 | 2-3 | 4-9 | 10-19 | 20-49 | 50+), so a colour means the same count
// on the state map and the county map. Dark-mode ramp: one hue, darkest = fewest.

const BIN_EDGES = [1, 2, 4, 10, 20, 50];
const BIN_LABELS = ["0", "1", "2–3", "4–9", "10–19", "20–49", "50+"];
const BIN_COLORS = ["#20201f", "#15304f", "#1a4470", "#1f5a93", "#2a72b8", "#4690dc", "#86b9f2"];
const binColor = n => BIN_COLORS[d3.bisectRight(BIN_EDGES, n)];

function BuildoutMap(container, data) {
  const STEPS = [
    { sub: "Operating datacenters per state", legend: "operating datacenters per state", zoom: null },
    { sub: "Virginia: operating datacenters per county", legend: "operating datacenters per county", zoom: "VA" },
    { sub: "The three states with the most operating datacenters", legend: "operating datacenters per state", zoom: null,
      focus: ["VA", "GA", "TX"] },
    { sub: "Total sites per state if every planned site is built", legend: "total sites if all are built", zoom: null,
      planned: true },
  ];
  const fmt = d3.format(",");
  const byState = new Map(data.states.map(f => [f.properties.state, f.properties]));
  const topCounty = [...data.va_counties].sort((a, b) => b.properties.op - a.properties.op)[0];
  let step = 0, svg, W, H, path, mapG, k = 1, narrow;

  function render() {
    const s = sizedSvg(container);
    svg = s.svg; W = s.width; H = s.height;
    svg.selectAll("*").remove();
    narrow = W < 560; const LEG_H = narrow ? 76 : 54;   // phones: dot keys go on a second legend row
    const proj = d3.geoAlbersUsa().fitExtent([[0, LEG_H + 6], [W, H]], { type: "FeatureCollection", features: data.states });
    path = d3.geoPath(proj);

    // The map is clipped to the area under the legend, so the Virginia zoom stays inside the figure
    svg.append("defs").append("clipPath").attr("id", "buildout-clip")
      .append("rect").attr("y", LEG_H).attr("width", W).attr("height", H - LEG_H);
    mapG = svg.append("g").attr("clip-path", "url(#buildout-clip)").append("g").attr("class", "map");
    mapG.append("g").attr("class", "states").selectAll("path").data(data.states).join("path")
      .attr("d", path).attr("stroke", C.bg).attr("stroke-width", 0.8).attr("vector-effect", "non-scaling-stroke")
      .on("pointerenter pointermove", (e, f) => {
        const p = f.properties;
        tip.show(`<b>${p.name}</b><br>${fmt(p.op)} operating<br>${fmt(p.pl)} planned`, e);
      })
      .on("pointerleave", () => tip.hide());
    mapG.append("g").attr("class", "counties").selectAll("path").data(data.va_counties).join("path")
      .attr("d", path).attr("fill", f => binColor(f.properties.op))
      .attr("stroke", C.bg).attr("stroke-width", 0.5).attr("vector-effect", "non-scaling-stroke")
      .on("pointerenter pointermove", (e, f) => tip.show(`<b>${f.properties.name}, VA</b><br>${fmt(f.properties.op)} operating`, e))
      .on("pointerleave", () => tip.hide());
    // Label the top county in Virginia (Loudoun). Font size is divided by the zoom so it stays readable.
    // Right of the county on wide screens; left of it on phones, where the right side runs off the edge
    const [[bx0], [bx1]] = path.bounds(topCounty), lx = narrow ? bx0 : bx1, ly = path.centroid(topCounty)[1];
    mapG.append("g").attr("class", "county-label").attr("opacity", 0)
      .call(g => g.append("text").attr("class", "label-strong").attr("x", lx).attr("y", ly).attr("text-anchor", narrow ? "end" : "start")
        .text(`${topCounty.properties.name}: ${topCounty.properties.op}`));

    // Sites: planned rings first so operating dots sit on top
    const sites = data.sites.map(d => { const xy = proj([d[0], d[1]]); return xy && { x: xy[0], y: xy[1], op: d[2] === 1,
      name: d[3], city: d[4], state: d[5], status: d[6], delay: Math.random() }; }).filter(Boolean)
      .sort((a, b) => a.op - b.op);
    mapG.append("g").attr("class", "sites").selectAll("circle").data(sites).join("circle")
      .attr("cx", d => d.x).attr("cy", d => d.y)
      .attr("fill", d => d.op ? C.accent : "none").attr("stroke", d => d.op ? C.bg : C.accent)
      .on("pointerenter pointermove", (e, d) => tip.show(`<b>${d.name}</b><br>${d.city ? d.city + ", " : ""}${d.state}` +
        `<br><span style="color:${C.muted}">${d.op ? "Operating" : "Planned: " + d.status}</span>`, e))
      .on("pointerleave", () => tip.hide());

    // Legend: seven swatches plus the dot and ring keys
    const leg = svg.append("g").attr("class", "legend");
    leg.append("text").attr("class", "label-muted legend-title").attr("y", 12);
    const sw = narrow ? Math.min(44, W / 7) : Math.min(40, (W - 230) / 7);
    const bins = leg.append("g").attr("transform", "translate(0,20)").selectAll("g").data(BIN_COLORS).join("g")
      .attr("transform", (_, i) => `translate(${i * sw},0)`);
    bins.append("rect").attr("width", sw - 2).attr("height", 10).attr("rx", 2).attr("fill", c => c)
      .attr("stroke", (_, i) => i === 0 ? C.axis : "none");
    bins.append("text").attr("class", "label-muted").attr("x", (sw - 2) / 2).attr("y", 26).attr("text-anchor", "middle")
      .text((_, i) => BIN_LABELS[i]);
    const keys = leg.append("g").attr("transform", narrow ? "translate(4,66)" : `translate(${7 * sw + 18},25)`);
    keys.append("circle").attr("r", 4).attr("fill", C.accent).attr("stroke", C.bg);
    keys.append("text").attr("class", "label").attr("x", 9).attr("y", 4).text(`operating (${fmt(data.operating)})`);
    const plKey = keys.append("g").attr("class", "planned-key").attr("transform", narrow ? "translate(130,0)" : "translate(0,20)");
    plKey.append("circle").attr("r", 3.5).attr("fill", "none").attr("stroke", C.accent).attr("stroke-width", 1.3);
    plKey.append("text").attr("class", "label").attr("x", 9).attr("y", 4).text(`planned (${fmt(data.planned)})`);

    update(step, 0);
  }

  function zoomTo(code) {
    if (!code) return { k: 1, x: 0, y: 0 };
    const [[x0, y0], [x1, y1]] = path.bounds(data.states.find(f => f.properties.state === code));
    const top = 60, kk = 0.9 / Math.max((x1 - x0) / W, (y1 - y0) / (H - top));
    return { k: kk, x: W / 2 - kk * (x0 + x1) / 2, y: top + (H - top) / 2 - kk * (y0 + y1) / 2 };
  }

  function update(i, dur = DUR) {
    step = i;
    const st = STEPS[i], z = zoomTo(st.zoom);
    k = z.k;
    d3.select("#buildout-sub").text(st.sub);
    const t = svg.transition().duration(dur * 1.3).ease(d3.easeCubicInOut);
    const inFocus = code => (st.focus ? st.focus.includes(code) : st.zoom ? code === st.zoom : true);

    mapG.transition(t).attr("transform", `translate(${z.x},${z.y}) scale(${z.k})`);
    mapG.selectAll(".states path").transition(t)
      .attr("fill", f => binColor(f.properties.op + (st.planned ? f.properties.pl : 0)))
      .attr("fill-opacity", f => inFocus(f.properties.state) ? 1 : 0.28);
    mapG.select(".counties").attr("pointer-events", st.zoom ? "all" : "none")
      .transition(t).attr("opacity", st.zoom === "VA" ? 1 : 0);
    mapG.select(".county-label").transition(t).attr("opacity", st.zoom === "VA" ? 1 : 0)
      .select("text").attr("font-size", 13 / z.k).attr("dx", (narrow ? -10 : 10) / z.k).attr("dy", 4 / z.k)
      .attr("stroke", C.bg).attr("stroke-width", 3 / z.k).attr("paint-order", "stroke");

    // Dots keep the same on-screen size at any zoom. Planned rings drop in, staggered, at the last step.
    const r = 2.6 / z.k;
    mapG.selectAll(".sites circle")
      .attr("pointer-events", d => (d.op || st.planned) && inFocus(d.state) ? "all" : "none")
      .transition(t).delay(d => d.op || !st.planned ? 0 : dur * 1.3 + d.delay * dur * 1.5).duration(dur * 0.6)
      .attr("r", d => d.op ? r : r * 1.05).attr("stroke-width", d => (d.op ? 0.5 : 0.9) / z.k)
      .attr("opacity", d => (d.op || st.planned) ? (inFocus(d.state) ? (d.op ? 0.92 : 0.75) : 0.15) : 0);

    svg.select(".legend-title").text(st.legend);
    svg.select(".planned-key").transition().duration(dur / 2).attr("opacity", st.planned ? 1 : 0.25);

    // Bar comparison for step 2: Virginia against Georgia + Texas combined
    const card = d3.select("#buildout-compare").classed("show", !!st.focus);
    if (st.focus && card.select(".bar").empty()) drawCompare(card);
  }

  function drawCompare(card) {
    const [va, ga, tx] = ["VA", "GA", "TX"].map(s => byState.get(s));
    const max = va.op;
    card.html(`<p class="compare-title">Operating datacenters</p>
      <div class="bar-row"><span class="bar-name">${va.name}</span><span class="bar"><i style="width:100%"></i></span><b>${va.op}</b></div>
      <div class="bar-row"><span class="bar-name">${ga.name} + ${tx.name}</span><span class="bar">
        <i style="width:${ga.op / max * 100}%" title="${ga.name}: ${ga.op}"></i><i class="b2" style="width:${tx.op / max * 100}%" title="${tx.name}: ${tx.op}"></i>
      </span><b>${ga.op + tx.op}</b></div>
      <p class="compare-note">${ga.name} ${ga.op} + ${tx.name} ${tx.op}</p>`);
  }

  render();
  window.addEventListener("resize", debounce(render, 150));
  return { update: i => update(i) };
}

async function initBuildout() {
  const data = await d3.json("data/buildout.json");
  const chart = BuildoutMap("#chart-buildout", data);
  const rows = data.states.map(f => f.properties).filter(p => p.op + p.pl > 0)
    .sort((a, b) => b.op - a.op || b.pl - a.pl);
  dataTable("#table-buildout", [
    { label: "State", value: r => r.name },
    { label: "Operating", value: r => r.op, num: true },
    { label: "Planned", value: r => r.pl, num: true },
    { label: "Total if all are built", value: r => r.op + r.pl, num: true },
  ], rows);
  return { "scrolly-buildout": chart };
}
