// Chapter 2, communities push back. One figure that changes with each step:
//  0) map: every moratorium at the place that adopted it (filled = in force, ring = proposed), grey data center sites
//  1) the same marks fly into monthly stacks, one square per adopted moratorium: the 2026 wave
//  2) back to the map: Ohio, Michigan and Georgia lead; Virginia has the most sites but only 6
//  3) Florida, Kansas and Maine: no operating sites, 68 moratoriums
//  4) bars: share of sites with documented opposition, by project status (a different source, the data center database)
//  5) bars: what moratoriums say they are about

const PUSHBACK = "#e5484d";
const CONCERN_COLORS = { grid_energy: "#3987e5", water: "#22a39a" };   // validated with the pushback red on --bg
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function PushbackChart(container, data, geo, sites) {
  const fmt = d3.format(",");
  const nShown = data.monthly.reduce((s, d) => s + d[1], 0);
  const STEPS = [
    { mode: "map", title: "Where communities are pushing back",
      sub: `${fmt(data.in_force)} data center moratoriums in force` },
    { mode: "wave", title: "The pushback wave",
      sub: `Moratoriums adopted per month, 2025 on. Each square is one moratorium` },
    { mode: "map", title: "Where communities are pushing back", sub: "Pushback leaders vs the state with the most sites",
      focus: ["OH", "MI", "GA", "VA"] },
    { mode: "map", title: "Where communities are pushing back", sub: "No operating data centers, but moratoriums",
      focus: ["FL", "KS", "ME"] },
    { mode: "outcomes", title: "What happens to projects that meet opposition",
      sub: "Share of sites with documented opposition to that project, by project status" },
    { mode: "concerns", title: "What moratoriums say they are about",
      sub: `Share of ${fmt(data.adopted)} adopted moratoriums citing each harm` },
  ];
  const SOURCES = {
    map: "Source: Moratorium Nation inventory (CC BY 4.0, compiled by Priyanka), plotted at the city, town, township or " +
      "county that adopted it, not at a data center site. It was searched month by month only for May–July 2026, so part " +
      "of the spike reflects search effort, and the recent months are likely incomplete. Most rows carry a \"verify\" " +
      "flag from the dataset author.",
    outcomes: "Different source from the maps above. This chart uses the data center database's per-project flag (337 of " +
      "1,733 sites have documented local opposition to that specific project), not Priyanka's moratorium inventory. A " +
      "moratorium is a town-wide pause on all data centers. This flag is opposition to one project. A site with no flag " +
      "may still sit in a town with a moratorium, and the reverse.",
    concerns: "These are the reasons written into the official action, not a survey of residents. One moratorium can cite " +
      "several reasons, so the shares add up to more than 100%. \"Need time to write rules\" (cited by " +
      `${data.rules_pct}%) and "other" are left off.`,
  };
  SOURCES.wave = SOURCES.map + ` Not shown: ${data.before_2025} adopted before 2025 and ${data.undated} with no recorded date.`;
  const stateName = new Map(geo.map(f => [f.properties.state, f.properties.name]));
  let step = 0, svg, W, H, narrow, marks;

  function render() {
    const s = sizedSvg(container);
    svg = s.svg; W = s.width; H = s.height;
    svg.selectAll("*").remove();
    narrow = W < 560;
    const LEG_H = 30;

    // ---- map positions
    // Full chart width, the same size as the Chapter 1 map
    const proj = d3.geoAlbersUsa().fitExtent([[0, LEG_H + 8], [W, H]], { type: "FeatureCollection", features: geo });
    const path = d3.geoPath(proj);
    const mapG = svg.append("g").attr("class", "pb-map");
    mapG.append("g").attr("class", "states").selectAll("path").data(geo).join("path")
      .attr("d", path).attr("fill", "#1f1f1e").attr("stroke", C.bg).attr("stroke-width", 0.8)
      .on("pointerenter pointermove", (e, f) => {
        const st = data.states[f.properties.state] || { mor: 0, op: 0 };
        tip.show(`<b>${f.properties.name}</b><br>${fmt(st.mor)} moratoriums adopted<br>${fmt(st.op)} operating data centers`, e);
      })
      .on("pointerleave", () => tip.hide());
    mapG.append("g").attr("class", "dc-sites").attr("pointer-events", "none").selectAll("circle")
      .data(sites.map(d => proj([d[0], d[1]])).filter(Boolean)).join("circle")
      .attr("cx", d => d[0]).attr("cy", d => d[1]).attr("r", narrow ? 1.1 : 1.5).attr("fill", "#8d8c86");
    const labelG = mapG.append("g").attr("class", "state-labels").attr("pointer-events", "none");

    // ---- wave layout: one column per month, squares stacked a few across
    const months = data.monthly.map(d => d[0]), maxN = d3.max(data.monthly, d => d[1]);
    const WM = { top: 64, right: 8, bottom: 40, left: 36 };
    const cw = (W - WM.left - WM.right) / months.length, plotH = H - WM.top - WM.bottom;
    let u = 12, per = 1;
    for (; u > 2; u -= 0.25) { per = Math.floor((cw - 2) / u); if (per >= 1 && Math.ceil(maxN / per) * u <= plotH) break; }
    const base = H - WM.bottom, yCount = n => base - (n / per) * u, col = i => WM.left + i * cw;
    const waveG = svg.append("g").attr("class", "pb-wave").attr("pointer-events", "none");
    const yTicks = d3.range(0, maxN + 1, narrow ? 50 : 25);
    waveG.append("g").attr("class", "grid").selectAll("line").data(yTicks).join("line")
      .attr("x1", WM.left).attr("x2", W - WM.right).attr("y1", yCount).attr("y2", yCount);
    waveG.append("g").attr("class", "axis").selectAll("text").data(yTicks).join("text")
      .attr("x", WM.left - 8).attr("y", d => yCount(d) + 4).attr("text-anchor", "end").text(d => d);
    const iBand = months.indexOf("2026-05"), iPeak = data.monthly.findIndex(d => d[1] === maxN);
    waveG.insert("rect", ":first-child").attr("x", col(iBand)).attr("width", cw * 3).attr("y", WM.top - 30)
      .attr("height", base - WM.top + 30).attr("fill", "#fff").attr("opacity", 0.05);
    waveG.append("text").attr("class", "label-muted").attr("x", col(iBand) + 4).attr("y", WM.top - 16)
      .attr("text-anchor", narrow ? "end" : "start").attr("dx", narrow ? cw * 3 - 8 : 0).text("searched month by month");
    waveG.append("text").attr("class", "label-strong").attr("x", col(iPeak) + cw / 2).attr("y", yCount(maxN) - 6)
      .attr("text-anchor", narrow ? "end" : "middle").call(t => t.append("tspan").text(maxN))
      .call(t => t.append("tspan").attr("class", "label").attr("font-weight", 400)
        .text(` in ${MONTHS[+data.monthly[iPeak][0].slice(5) - 1]} ${data.monthly[iPeak][0].slice(0, 4)}`));
    const iRecent = months.indexOf("2026-10");
    if (!narrow) waveG.append("text").attr("class", "label-muted").attr("text-anchor", "end")   // on phones the caption says it
      .attr("x", W - WM.right).attr("y", yCount(data.monthly[iRecent - 1][1]) - 30)   // clear of the September stack
      .call(t => t.append("tspan").text("recent months"))
      .call(t => t.append("tspan").attr("x", W - WM.right).attr("dy", "1.3em").text("likely incomplete"));
    const every = narrow ? 6 : 3;
    waveG.append("g").attr("class", "axis").selectAll("text").data(months.filter((_, i) => i % every === 0)).join("text")
      .attr("x", m => col(months.indexOf(m)) + cw / 2).attr("y", base + 16).attr("text-anchor", "middle")
      .call(t => t.append("tspan").text(m => MONTHS[+m.slice(5) - 1]))
      .call(t => t.append("tspan").attr("x", m => col(months.indexOf(m)) + cw / 2).attr("dy", "1.2em")
        .text(m => m.endsWith("-01") ? m.slice(0, 4) : ""));

    // ---- one mark per moratorium, with a map position and (if adopted from 2025 on) a wave position
    const slot = new Map(months.map(m => [m, 0]));
    marks = data.moratoria.map(d => {
      const xy = proj([d[0], d[1]]);
      return xy && { mx: xy[0], my: xy[1], kind: d[2], name: d[3], state: d[4], status: d[5], date: d[6], reasons: d[7] };
    }).filter(Boolean);
    for (const d of [...marks].sort((a, b) => b.kind - a.kind || a.date.localeCompare(b.date))) {
      if (d.kind === 0 || !slot.has(d.date)) continue;
      const j = slot.get(d.date); slot.set(d.date, j + 1);
      const i = months.indexOf(d.date);
      d.wx = col(i) + (cw - per * u) / 2 + (j % per) * u; d.wy = base - (Math.floor(j / per) + 1) * u;
      d.delay = Math.random();
    }
    const r = narrow ? 2.2 : 3;
    marks.forEach(d => { d.r = r; d.u = u; });
    svg.append("g").attr("class", "pb-marks").selectAll("rect").data(marks).join("rect")
      .on("pointerenter pointermove", (e, d) => {
        const [y, mo] = d.date ? d.date.split("-") : [];
        tip.show(`<b>${d.name}, ${d.state}</b><br>${d.kind === 0 ? "Proposed" : d.status[0].toUpperCase() + d.status.slice(1)}` +
          `${d.date ? ", " + MONTHS[+mo - 1] + " " + y : ""}<br><span style="color:${C.muted}">Reasons: ${d.reasons}</span>`, e);
      })
      .on("pointerleave", () => tip.hide());

    // ---- legends: one per mode
    const legMap = svg.append("g").attr("class", "legend pb-leg-map").attr("transform", "translate(4,12)");
    const key = (g, x, filled, text) => {
      const k = g.append("g").attr("transform", `translate(${x},0)`);
      k.append("circle").attr("r", 4).attr("fill", filled === true ? PUSHBACK : "none")
        .attr("stroke", filled === "site" ? "none" : PUSHBACK).attr("stroke-width", 1.4);
      if (filled === "site") k.select("circle").attr("r", 2).attr("fill", "#8d8c86");
      k.append("text").attr("class", "label").attr("x", 9).attr("y", 4).text(text);
      return k.node().getBBox().width + 18;
    };
    let x = 0;
    x += key(legMap, x, true, `in force (${fmt(data.in_force)})`);
    x += key(legMap, x, false, `proposed (${data.proposed})`);
    key(legMap, x, "site", narrow ? "data center" : "data center site");
    const legWave = svg.append("g").attr("class", "legend pb-leg-wave").attr("transform", "translate(4,12)");
    legWave.append("rect").attr("x", -4).attr("y", -4).attr("width", 8).attr("height", 8).attr("rx", 1.5).attr("fill", PUSHBACK);
    legWave.append("text").attr("class", "label").attr("x", 9).attr("y", 4)
      .text(`one adopted moratorium (${fmt(nShown)} from 2025 on)`);

    // ---- bar charts: labels above bars on phones, beside them on wide screens
    const barsG = svg.append("g").attr("class", "pb-bars");
    const hbar = (cls, rows, { label, value, text, color, max }) => {
      const g = barsG.append("g").attr("class", cls);
      const left = narrow ? 0 : d3.max(rows, d => label(d).length) * 7.2 + 14, valW = narrow ? 112 : 130;
      const top = 20, rowH = Math.min(narrow ? 64 : 110, (H - top - 10) / rows.length), bh = narrow ? Math.max(12, Math.min(22, rowH - 30)) : Math.min(44, rowH * 0.5);
      const xs = d3.scaleLinear([0, max], [left, W - valW]);
      const row = g.selectAll("g").data(rows).join("g")
        .attr("transform", (_, i) => `translate(0,${top + i * rowH + (narrow ? 18 : (rowH - bh) / 2)})`)
        .on("pointerenter pointermove", (e, d) => tip.show(text(d, true), e)).on("pointerleave", () => tip.hide());
      row.append("rect").attr("x", 0).attr("y", narrow ? -18 : -(rowH - bh) / 2).attr("width", W).attr("height", rowH)
        .attr("fill", "transparent");
      row.append("text").attr("class", "label").attr("x", narrow ? 0 : left - 10).attr("y", narrow ? -6 : bh / 2 + 4)
        .attr("text-anchor", narrow ? "start" : "end").text(label);
      row.append("path").attr("class", "bar").attr("fill", color).datum(d => ({ d, w: xs(value(d)) - left, left, bh }));
      row.append("text").attr("class", "label value").attr("y", bh / 2 + 4).attr("x", d => xs(value(d)) + 8)
        .html(d => text(d));
      return g;
    };
    hbar("pb-outcomes", data.outcomes, { label: d => d.label, value: d => d.n / d.of * 100, color: PUSHBACK, max: 100,
      text: (d, long) => long ? `<b>${d.label}</b><br>${Math.round(d.n / d.of * 100)}% have documented opposition to the project<br>${d.n} of ${fmt(d.of)} sites`
        : `<tspan font-weight="650" fill="${C.text}">${Math.round(d.n / d.of * 100)}%</tspan> (${d.n} of ${fmt(d.of)})` });
    hbar("pb-concerns", data.concerns, { label: d => d.label[0].toUpperCase() + d.label.slice(1), value: d => d.pct, max: 40,
      color: d => CONCERN_COLORS[d.key] || "#5d5c57",
      text: (d, long) => long ? `<b>${d.label[0].toUpperCase() + d.label.slice(1)}</b><br>cited by ${Math.round(d.pct)}% of adopted moratoriums`
        : `<tspan font-weight="650" fill="${C.text}">${Math.round(d.pct)}%</tspan>` });
    barsG.selectAll("path.bar").attr("d", p => roundEnd({ ...p, w: 0 }));

    // State callouts for steps 2 and 3. Each label sits in nearby empty space (ocean, Canada, the plains) with a
    // leader line to the state, so it never covers the dots it describes
    const SPOT = { MI: [-87.5, 48.3, "end"], OH: [-79.2, 44.6, "start"], GA: [-77.6, 30.6, "start"], VA: [-72.6, 37.2, "start"],
      FL: [-76.8, 26.2, "start"], KS: [-99.5, 42.6, "middle"], ME: [-69.6, 48.9, "middle"] };
    const callout = code => {
      const f = geo.find(g => g.properties.state === code), [cx, cy] = path.centroid(f), st = data.states[code] || { mor: 0, op: 0 };
      const [lx, ly] = proj(SPOT[code].slice(0, 2)) || [cx, cy];
      return { code, cx, cy, lx, ly, anchor: SPOT[code][2], name: stateName.get(code), mor: st.mor, op: st.op };
    };
    labelG.selectAll("g").data(Object.keys(SPOT).map(callout)).join("g")
      .attr("data-code", d => d.code).attr("opacity", 0)
      .call(g => g.append("line").attr("x1", d => d.cx).attr("y1", d => d.cy).attr("x2", d => d.lx).attr("y2", d => d.ly - 4)
        .attr("stroke", C.text2).attr("stroke-width", 1).attr("opacity", 0.6))
      .call(g => g.append("text").attr("class", "label-strong").attr("font-size", narrow ? 11 : 13)
        .attr("text-anchor", d => d.anchor).attr("x", d => d.lx + (d.anchor === "start" ? 4 : d.anchor === "end" ? -4 : 0))
        .attr("y", d => d.ly - (d.anchor === "middle" ? 18 : 2))
        .attr("stroke", C.bg).attr("stroke-width", 3.5).attr("paint-order", "stroke").attr("stroke-linejoin", "round")
        .call(t => t.append("tspan").text(d => narrow ? `${d.code} ${d.mor}` : d.name))
        .call(t => narrow && t.append("tspan").attr("font-weight", 400).attr("fill", C.text2)   // phones: one short line
          .text(d => d.code === "VA" ? ` · ${d.op} sites` : d.op === 0 ? " · no sites" : ""))
        .call(t => !narrow && t.append("tspan").attr("x", function () { return this.parentNode.getAttribute("x"); }).attr("dy", "1.2em")
          .attr("font-weight", 400).attr("fill", C.text2)
          .text(d => d.code === "VA" ? `${d.op} sites, ${d.mor} moratoriums`
            : d.op === 0 ? `${d.mor} moratoriums, no sites` : `${d.mor} moratoriums`)));
    labelG.selectAll("text").each(function () {   // keep labels inside the figure
      const b = this.getBBox(), over = Math.max(0, b.x + b.width - W + 2) - Math.max(0, -b.x + 2);
      if (over) d3.select(this).attr("transform", `translate(${-over},0)`);
    });

    update(step, 0);
  }

  function update(i, dur = DUR) {
    const prev = STEPS[step].mode;
    step = i;
    const st = STEPS[i], mode = st.mode;
    d3.select("#pushback-title").text(st.title);
    d3.select("#pushback-sub").text(st.sub);
    d3.select("#pushback-source").text(SOURCES[mode]);
    const t = svg.transition().duration(dur).ease(d3.easeCubicInOut);
    const show = (sel, on) => sel.attr("pointer-events", on ? null : "none").transition(t).attr("opacity", on ? 1 : 0);
    show(svg.select(".pb-map"), mode === "map");
    show(svg.select(".pb-wave"), mode === "wave");
    svg.select(".pb-wave").attr("pointer-events", "none");
    show(svg.select(".pb-leg-map"), mode === "map");
    show(svg.select(".pb-leg-wave"), mode === "wave");
    show(svg.select(".pb-outcomes"), mode === "outcomes");
    show(svg.select(".pb-concerns"), mode === "concerns");

    const focus = st.focus || [];
    svg.selectAll(".pb-map .states path").transition(t)
      .attr("fill", f => focus.includes(f.properties.state) ? "#34332f" : "#1f1f1e");
    svg.selectAll(".state-labels g").transition(t).attr("opacity", function () { return focus.includes(this.dataset.code) ? 1 : 0; });
    svg.select(".dc-sites").transition(t).attr("opacity", focus.length ? 0.75 : 0.4);

    // Marks: dots on the map, squares in the wave (staggered so they visibly travel), hidden on the bar steps
    const toWave = mode === "wave", onMap = mode === "map";
    const lit = d => !focus.length || focus.includes(d.state);
    svg.selectAll(".pb-marks rect")
      .attr("pointer-events", d => (onMap && d.kind !== 1) || (toWave && d.wx != null) ? null : "none")
      .transition(t).delay(d => (toWave || prev === "wave") && d.delay != null ? d.delay * dur * 0.8 : 0).duration(dur * 1.2)
      .attr("x", d => toWave && d.wx != null ? d.wx + 0.5 : d.mx - d.r)
      .attr("y", d => toWave && d.wx != null ? d.wy + 0.5 : d.my - d.r)
      .attr("width", d => toWave && d.wx != null ? d.u - 1 : 2 * d.r)
      .attr("height", d => toWave && d.wx != null ? d.u - 1 : 2 * d.r)
      .attr("rx", d => toWave && d.wx != null ? Math.min(1.5, d.u / 4) : d.r)
      .attr("fill", d => d.kind === 0 && !toWave ? "none" : PUSHBACK)
      .attr("stroke", d => d.kind === 0 ? PUSHBACK : toWave ? "none" : C.bg)
      .attr("stroke-width", d => d.kind === 0 ? 1.3 : 0.5)
      .attr("opacity", d => toWave ? (d.wx != null ? 1 : 0)
        : onMap ? (d.kind === 1 ? 0 : lit(d) ? 0.85 : 0.12) : 0);

    // Bars grow from the baseline; on the last step the untested harms step back
    const barsOn = sel => sel.transition(t).delay((_, j) => j * 60).attr("d", p => roundEnd(p));
    const barsOff = sel => sel.transition(t).attr("d", p => roundEnd({ ...p, w: 0 }));
    (mode === "outcomes" ? barsOn : barsOff)(svg.selectAll(".pb-outcomes path.bar"));
    (mode === "concerns" ? barsOn : barsOff)(svg.selectAll(".pb-concerns path.bar"));
    svg.selectAll(".pb-concerns > g").transition(t)
      .attr("opacity", d => !st.tested || CONCERN_COLORS[d.key] ? 1 : 0.3);
  }

  function roundEnd({ w, left, bh }) {   // 4px rounded data end, square at the baseline
    const rr = Math.max(0, Math.min(4, w, bh / 2));
    return `M${left},0h${Math.max(0, w - rr)}a${rr},${rr} 0 0 1 ${rr},${rr}v${bh - 2 * rr}a${rr},${rr} 0 0 1 ${-rr},${rr}h${Math.min(0, rr - w)}z`;
  }

  // On phones the caption is cut to three lines; a tap shows all of it
  d3.select("#pushback-source").on("click", function () { this.classList.toggle("open"); });
  render();
  window.addEventListener("resize", debounce(render, 150));
  return { update: i => update(i) };
}

async function initPushback() {
  const [data, buildout, sites] = await Promise.all([d3.json("data/pushback.json"), d3.json("data/buildout.json"),
    d3.json("data/sites.json")]);
  const chart = PushbackChart("#chart-pushback", data, buildout.states, sites.points);
  const name = new Map(buildout.states.map(f => [f.properties.state, f.properties.name]));
  const rows = Object.entries(data.states).filter(([, s]) => s.mor > 0)
    .map(([code, s]) => ({ name: name.get(code) || code, ...s })).sort((a, b) => b.mor - a.mor || b.op - a.op);
  dataTable("#table-pushback", [
    { label: "State", value: r => r.name },
    { label: "Moratoriums adopted", value: r => r.mor, num: true },
    { label: "Operating data centers", value: r => r.op, num: true },
  ], rows);
  dataTable("#table-pushback", [
    { label: "Month", value: r => `${MONTHS[+r[0].slice(5) - 1]} ${r[0].slice(0, 4)}` },
    { label: "Moratoriums adopted", value: r => r[1], num: true },
  ], data.monthly);
  dataTable("#table-pushback", [
    { label: "Project status", value: r => r.label },
    { label: "With documented opposition", value: r => `${Math.round(r.n / r.of * 100)}% (${r.n} of ${r.of})`, num: true },
  ], data.outcomes);
  dataTable("#table-pushback", [
    { label: "Reason cited", value: r => r.label },
    { label: "Share of adopted moratoriums", value: r => `${Math.round(r.pct)}%`, num: true },
  ], data.concerns);
  return { "scrolly-pushback": chart };
}
