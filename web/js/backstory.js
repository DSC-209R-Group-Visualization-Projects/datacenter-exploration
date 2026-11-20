// Backstory charts.
//  1) ElectricityChart: a 1950–2028 timeline of eras and milestones that, at the 2000s step, rescales into the
//     US data center electricity chart and draws its line era by era, ending with the 2028 projection fan.
//  2) ScaleChart: power drawn by one facility, one circle per step (area ∝ MW). The scale resets to the largest
//     visible circle, so earlier facilities shrink as bigger ones arrive.

function ElectricityChart(container, data) {
  const STEPS = [
    { mode: "timeline", eras: ["early"], sub: "1950s–1960s: the first data centers" },
    { mode: "timeline", eras: ["super"], sub: "1970s–1980s: mainframes and supercomputers" },
    { mode: "timeline", eras: ["internet"], sub: "1990s: the internet arrives" },
    { mode: "data", eras: ["internet", "cloud"], cutoff: 2006, ymax: 200, sub: "Terawatt-hours per year, 2000–2006" },
    { mode: "data", eras: ["deep"], cutoff: 2018, ymax: 200, sub: "Terawatt-hours per year, through 2018" },
    { mode: "data", eras: ["genai"], cutoff: 2023, ymax: 200, sub: "Terawatt-hours per year, through 2023" },
    { mode: "data", eras: [], cutoff: 2023, projection: true, ymax: 620, sub: "Terawatt-hours per year, with the 2028 projection" },
  ];
  const elec = data.electricity, proj = data.projection;
  const LABELLED = { 2006: "1.5% of US", 2018: "1.9%", 2023: "4.4%" };
  // Milestone label heights above the timeline baseline (px), staggered so neighbours don't collide
  const LIFT = { 1958: 64, 1969: 120, 2006: 64, 2012: 120, 2022.9: 64 };
  const M = { top: 34, right: 118, bottom: 34, left: 52 };
  let step = 0, W, H, x, y, svg, g, clipRect, narrow;

  const segments = [   // solid / dashed (gap between reports) / solid
    { pts: elec.filter(d => d.year <= 2006), dash: null },
    { pts: elec.filter(d => d.year === 2006 || d.year === 2014), dash: "5 5" },
    { pts: elec.filter(d => d.year >= 2014), dash: null },
  ];

  function render() {
    const s = sizedSvg(container);
    narrow = s.width < 560;
    M.right = narrow ? 92 : 118; M.left = narrow ? 40 : 52;
    svg = s.svg; W = s.width - M.left - M.right; H = s.height - M.top - M.bottom;
    svg.selectAll("*").remove();
    svg.append("defs").append("clipPath").attr("id", "elec-clip").append("rect")
      .attr("x", 0).attr("y", -M.top).attr("height", H + M.top + 4);
    clipRect = svg.select("#elec-clip rect");
    svg.append("defs").append("clipPath").attr("id", "elec-plot").append("rect")
      .attr("x", 0).attr("y", -M.top).attr("width", W).attr("height", H + M.top);
    g = svg.append("g").attr("transform", `translate(${M.left},${M.top})`);

    g.append("g").attr("class", "bands").attr("clip-path", "url(#elec-plot)")
      .selectAll("g").data(data.eras).join("g")
      .call(b => b.append("rect").attr("y", 0).attr("height", H))
      .call(b => b.append("text").attr("class", "label").attr("y", -14).attr("text-anchor", "middle").text(d => d.name));
    g.append("g").attr("class", "grid");
    g.append("g").attr("class", "axis y-axis");
    g.append("g").attr("class", "axis x-axis");
    g.append("text").attr("class", "label-muted gap-note").attr("text-anchor", "start");

    const ms = g.append("g").attr("class", "milestones").attr("clip-path", "url(#elec-plot)")
      .selectAll("g").data(data.milestones).join("g");
    ms.append("line").attr("stroke", C.muted).attr("stroke-width", 1).attr("stroke-dasharray", "2 3");
    ms.append("circle").attr("r", 4).attr("fill", C.text2).attr("stroke", C.bg).attr("stroke-width", 2);
    ms.append("text").attr("class", "label").attr("dx", 7).text(d => d.label);

    const fan = g.append("g").attr("class", "projection").attr("clip-path", "url(#elec-clip)");
    fan.append("path").attr("class", "fan").attr("fill", C.dc).attr("fill-opacity", 0.14);
    fan.selectAll("line.edge").data(["high_twh", "low_twh"]).join("line").attr("class", "edge")
      .attr("stroke", C.dc).attr("stroke-width", 1.5).attr("stroke-dasharray", "4 4");

    const line = g.append("g").attr("class", "line").attr("clip-path", "url(#elec-clip)");
    line.selectAll("path").data(segments).join("path").attr("fill", "none").attr("stroke", C.dc)
      .attr("stroke-width", 2).attr("stroke-linejoin", "round").attr("stroke-linecap", "round")
      .attr("stroke-dasharray", d => d.dash);

    g.append("g").attr("class", "value-labels").selectAll("text").data(elec.filter(d => LABELLED[d.year])).join("text")
      .attr("text-anchor", d => narrow && d.year === 2006 ? "start" : "end").attr("dx", d => narrow && d.year === 2006 ? 6 : -9).attr("dy", -10)
      .call(t => t.append("tspan").attr("class", "label-strong").text(d => `${Math.round(d.twh)} TWh`))
      .call(t => t.append("tspan").attr("class", "label").attr("dx", 5).text(d => narrow ? LABELLED[d.year].replace(" of US", "") : LABELLED[d.year]));

    // 2028 end-points and label
    const ends = g.append("g").attr("class", "proj-ends");
    ends.selectAll("circle").data([proj.high_twh, proj.low_twh]).join("circle").attr("r", 4.5)
      .attr("fill", C.bg).attr("stroke", C.dc).attr("stroke-width", 2);
    const pl = ends.append("text").attr("class", "proj-label");
    pl.append("tspan").attr("class", "label-strong").attr("x", 12).text(narrow ? "2028" : "2028 projection");
    pl.append("tspan").attr("class", "label").attr("x", 12).attr("dy", "1.35em").text(`${proj.low_twh}–${proj.high_twh} TWh`);
    pl.append("tspan").attr("class", "label").attr("x", 12).attr("dy", "1.35em").text(`${proj.low_pct}–${proj.high_pct}% of US`);

    // Points last, so their hit targets sit on top
    const pts = g.append("g").attr("class", "points").selectAll("g").data(elec).join("g");
    pts.append("circle").attr("class", "dot").attr("r", 4.5).attr("fill", C.dc).attr("stroke", C.bg).attr("stroke-width", 2);
    pts.append("circle").attr("class", "hit").attr("r", 14).attr("fill", "transparent")
      .on("pointerenter pointermove", (e, d) => tip.show(`<b>${d.year}</b><br>${d.twh} TWh` +
        (d.pct_us ? `<br>${d.pct_us}% of US electricity` : ""), e))
      .on("pointerleave", () => tip.hide());
    ends.selectAll("circle").on("pointerenter pointermove", (e, v) => tip.show(
      `<b>2028 projection, ${v === proj.high_twh ? "high" : "low"}</b><br>${v} TWh<br>` +
      `${v === proj.high_twh ? proj.high_pct : proj.low_pct}% of US electricity`, e)).on("pointerleave", () => tip.hide());

    update(step, 0);
  }

  function update(i, dur = DUR) {
    step = i;
    const st = STEPS[i], timeline = st.mode === "timeline";
    d3.select("#elec-sub").text(st.sub);
    x = d3.scaleLinear().domain(timeline ? [1948, 2030] : [1999, 2029]).range([0, W]);
    y = d3.scaleLinear().domain([0, st.ymax || 200]).range([H, 0]);
    const base = timeline ? H * 0.62 : H;
    const t = svg.transition().duration(dur).ease(d3.easeCubicInOut);
    const t2 = t.transition().duration(dur);   // drawing happens after the rescale

    // Era bands and names (names hidden when they don't fit their band)
    g.selectAll(".bands g").each(function (d, k) {
      const b = d3.select(this), on = st.eras.includes(d.id);
      b.select("rect").transition(t).attr("x", x(d.start)).attr("width", Math.max(0, x(d.end) - x(d.start)))
        .attr("fill", on ? "rgba(57,135,229,0.13)" : (k % 2 ? "rgba(255,255,255,0)" : "rgba(255,255,255,0.025)"));
      const x0 = Math.max(x(d.start), 0), x1 = Math.min(x(d.end), W);
      const txt = b.select("text"), fits = txt.node().getComputedTextLength() + 10 < x1 - x0;
      txt.transition(t).attr("x", (x0 + x1) / 2).style("fill", on ? C.text : C.muted)
        .attr("font-weight", on ? 650 : 400).attr("opacity", fits && x1 > x0 ? 1 : 0);
    });

    // Axes
    const xAxis = d3.axisBottom(x).tickFormat(d3.format("d")).tickSizeOuter(0)
      .tickValues(timeline ? d3.range(1950, 2030, narrow ? 20 : 10) : d3.range(2000, 2029, narrow ? 8 : 4));
    g.select(".x-axis").transition(t).attr("transform", `translate(0,${base})`).call(xAxis);
    g.select(".y-axis").transition(t).attr("opacity", timeline ? 0 : 1)
      .call(d3.axisLeft(y).ticks(5).tickSize(0).tickPadding(8)).call(a => a.select(".domain").remove());
    g.select(".grid").transition(t).attr("opacity", timeline ? 0 : 1)
      .call(d3.axisLeft(y).ticks(5).tickSize(-W).tickFormat("")).call(a => a.select(".domain").remove());
    g.select(".gap-note").text("National estimates of data center electricity begin in 2000")
      .transition(t).attr("x", x(2000)).attr("y", base + 46).attr("opacity", timeline && i === 2 ? 1 : 0);

    // Milestones: on the timeline they rise from the baseline; on the chart only ChatGPT stays, as a full-height rule
    const shown = d => timeline ? d.year < [1970, 1990, 2000][i] : d.year > 2022 && i >= 5;
    g.selectAll(".milestones g").each(function (d) {
      const m = d3.select(this), top = timeline ? base - LIFT[d.year] : 0, vis = shown(d) ? 1 : 0;
      m.transition(t).attr("opacity", vis);
      m.select("line").transition(t).attr("x1", x(d.year)).attr("x2", x(d.year)).attr("y1", base).attr("y2", top);
      m.select("circle").transition(t).attr("cx", x(d.year)).attr("cy", base).attr("opacity", timeline ? 1 : 0);
      const txt = m.select("text").text(narrow ? d.short : timeline ? d.label : "ChatGPT (Nov 2022)");
      const flip = x(d.year) + 7 + txt.node().getComputedTextLength() > W;
      txt.transition(t).attr("x", x(d.year)).attr("y", timeline ? top + 4 : narrow ? H - 8 : 14)
        .attr("dx", flip ? -7 : 7).attr("text-anchor", flip ? "end" : "start");
    });

    // Line: rescale with the axes, then reveal up to this step's cutoff by growing the clip
    const ln = d3.line().x(d => x(d.year)).y(d => y(d.twh));
    g.selectAll(".line path").transition(t).attr("d", d => ln(d.pts));
    const reveal = timeline ? 0 : st.projection ? W + M.right : x(st.cutoff) + 6;
    clipRect.transition(t2).attr("width", Math.max(0, reveal));

    g.selectAll(".points g").each(function (d) {
      const p = d3.select(this), vis = !timeline && d.year <= st.cutoff;
      p.selectAll("circle").transition(vis ? t2 : t).attr("cx", x(d.year)).attr("cy", y(d.twh));
      p.select(".dot").transition(vis ? t2 : t).attr("opacity", vis ? 1 : 0);
      p.select(".hit").attr("pointer-events", vis ? "all" : "none");
    });
    g.selectAll(".value-labels text").transition(t).attr("x", d => x(d.year)).attr("y", d => y(d.twh))
      .transition().duration(dur / 2).attr("opacity", d => !timeline && (narrow ? d.year === st.cutoff : d.year <= st.cutoff) ? 1 : 0);

    // Projection fan
    const p0 = [x(2023), y(176)], hi = [x(proj.year), y(proj.high_twh)], lo = [x(proj.year), y(proj.low_twh)];
    g.select(".fan").transition(t).attr("d", `M${p0}L${hi}L${lo}Z`).attr("opacity", st.projection ? 1 : 0);
    g.selectAll(".edge").transition(t).attr("x1", p0[0]).attr("y1", p0[1])
      .attr("x2", (_, k) => (k ? lo : hi)[0]).attr("y2", (_, k) => (k ? lo : hi)[1]).attr("opacity", st.projection ? 1 : 0);
    const ends = g.select(".proj-ends");
    ends.transition(st.projection ? t2 : t).attr("opacity", st.projection ? 1 : 0);
    ends.attr("pointer-events", st.projection ? "all" : "none");
    ends.selectAll("circle").transition(t).attr("cx", x(proj.year)).attr("cy", v => y(v));
    ends.select(".proj-label").transition(t)
      .attr("transform", `translate(${x(proj.year)},${(y(proj.high_twh) + y(proj.low_twh)) / 2 - 18})`);
  }

  render();
  window.addEventListener("resize", debounce(render, 150));
  return { update: i => update(i) };
}

function ScaleChart(container, data) {
  const items = data.facilities;
  // On the last step the 1 GW campus is drawn inside the Memphis outlines (all three share one baseline and centre)
  const NESTED = new Set(["xAI Colossus sites, Memphis–Southaven", "All Memphis homes", "All of Memphis"]);
  const LABEL_H = 84, TOP = 44;
  let step = 0, svg, W, H, minSlot, GAP, narrow;

  const wrap = (s, n) => s.split(" ").reduce((lines, w) => {
    const last = lines[lines.length - 1];
    if (last && (last + " " + w).length <= n) lines[lines.length - 1] = last + " " + w; else lines.push(w);
    return lines;
  }, []);

  function layout(i) {
    let visible = i < 5 ? items.filter(d => d.kind === "facility").slice(0, i + 1) : items;
    // Phones: just the newest two facilities, and only the Memphis comparison on the last step
    if (narrow) visible = i < 5 ? visible.slice(-2) : items.filter(d => NESTED.has(d.label));
    const nest = i === 5, maxMw = d3.max(visible, d => d.mw);
    const units = nest ? [...visible.filter(d => !NESTED.has(d.label)), { group: true, mw: maxMw }] : visible;
    const avail = H - LABEL_H - TOP, cap = Math.min(avail, W * 0.6);
    const slot = (D, mw) => Math.max(D * Math.sqrt(mw / maxMw), minSlot) + GAP;
    let lo = 0, hi = cap;                         // largest diameter that fits the width
    for (let k = 0; k < 30; k++) { const mid = (lo + hi) / 2; if (d3.sum(units, u => slot(mid, u.mw)) <= W) lo = mid; else hi = mid; }
    const D = lo;
    let cursor = (W - d3.sum(units, u => slot(D, u.mw))) / 2;
    const centre = new Map();
    for (const u of units) { const w = slot(D, u.mw); centre.set(u.group ? "group" : u.label, cursor + w / 2); cursor += w; }
    return {
      maxMw, pos: visible.map(d => ({
        ...d, nested: nest && NESTED.has(d.label),
        cx: centre.get(nest && NESTED.has(d.label) ? "group" : d.label),
        r: Math.max(D * Math.sqrt(d.mw / maxMw) / 2, 2.5),
      })),
    };
  }

  function render() {
    const s = sizedSvg(container);
    svg = s.svg; W = s.width; H = s.height;
    narrow = W < 560; GAP = narrow ? 6 : 16;   // phones: tighter slots and short names
    minSlot = Math.min(118, W / 5 - GAP);
    svg.selectAll("*").remove();
    svg.append("text").attr("class", "label-muted scale-note").attr("x", 0).attr("y", 14);
    svg.append("g").attr("class", "circles");
    update(step, 0);
  }

  function update(i, dur = DUR) {
    step = i;
    const { maxMw, pos } = layout(i);
    const base = H - LABEL_H, fmt = d3.format(",");
    const t = svg.transition().duration(dur).ease(d3.easeCubicInOut);
    svg.select(".scale-note").text(`Largest circle shown: ${fmt(Math.round(maxMw))} MW`);
    const outer = d => d.kind === "city" && d.mw === d3.max(items, e => e.mw);

    const groups = svg.select(".circles").selectAll("g.item").data(pos, d => d.label).join(
      enter => {
        const e = enter.append("g").attr("class", "item").attr("opacity", 0)
          .attr("transform", d => `translate(${d.cx},${base})`);
        e.append("circle").attr("cy", 0).attr("r", 0)
          .attr("fill", d => d.kind === "city" ? "rgba(255,255,255,0.035)" : C.dc)
          .attr("fill-opacity", d => d.kind === "city" ? 1 : 0.88)
          .attr("stroke", d => d.kind === "city" ? (outer(d) ? C.text2 : "#ffffff") : C.bg)
          .attr("stroke-width", d => d.kind === "city" ? 1.5 : 2)
          .attr("stroke-dasharray", d => d.kind === "city" ? "4 4" : null);
        // Facilities: value and name under the baseline. Memphis outlines: one line at the top of the circle.
        e.filter(d => d.kind === "facility").append("text").attr("class", "below").attr("text-anchor", "middle").attr("y", 22)
          .each(function (d) {
            const el = d3.select(this);
            el.append("tspan").attr("class", "label-strong").attr("x", 0).text(`${fmt(Math.round(d.mw))} MW`);
            wrap(narrow ? d.short : d.label, narrow ? 16 : Math.max(10, Math.floor(minSlot / 7))).forEach(l =>
              el.append("tspan").attr("class", "label").attr("x", 0).attr("dy", "1.3em").text(l));
            el.append("tspan").attr("class", "label-muted").attr("x", 0).attr("dy", "1.3em").text(`(${d.when})`);
          });
        // The city label sits on one line above its outline; the homes label is centred in its circle on two lines
        e.filter(d => d.kind === "city").append("text").attr("class", "top").attr("text-anchor", "middle")
          .style("fill", d => outer(d) ? null : "#ffffff")
          .each(function (d) {
            const el = d3.select(this), name = d.label.toLowerCase().replace("memphis", "Memphis");
            el.append("tspan").attr("class", "label-strong").attr("x", 0).text(`${fmt(d.mw)} MW `);
            el.append("tspan").attr("class", "label").attr("x", outer(d) ? null : 0).attr("dy", outer(d) ? null : "1.3em").text(name);
          });
        e.on("pointerenter pointermove", (ev, d) => tip.show(`<b>${d.label}</b> (${d.when})<br>${fmt(Math.round(d.mw))} MW<br><span style="color:${C.muted}">${d.source}</span>`, ev))
          .on("pointerleave", () => tip.hide());
        return e;
      },
      update => update,
      exit => exit.call(x => x.transition(t).attr("opacity", 0).remove().select("circle").attr("r", 0)),
    );
    // Draw order: the city outline above the campus, the homes outline above both
    groups.sort((a, b) => (a.kind === "city") - (b.kind === "city") || (outer(b) - outer(a)));
    groups.transition(t).attr("opacity", 1).attr("transform", d => `translate(${d.cx},${base})`);
    groups.select("circle").transition(t).attr("r", d => d.r).attr("cy", d => -d.r);
    groups.select("text.top").transition(t).attr("y", d => outer(d) ? -2 * d.r - 10 : -d.r - 4);
    groups.selectAll("text.top tspan").style("fill", function () { return this.parentNode.style.fill || null; });
  }

  render();
  window.addEventListener("resize", debounce(render, 150));
  return { update: i => update(i) };
}

function debounce(fn, ms) { let id; return () => { clearTimeout(id); id = setTimeout(fn, ms); }; }

async function initBackstory() {
  const data = await d3.json("data/backstory.json");
  d3.selectAll("[data-fill]").each(function () { this.textContent = data.memphis[this.dataset.fill]; });

  const charts = {
    "scrolly-electricity": ElectricityChart("#chart-electricity", data),
    "scrolly-scale": ScaleChart("#chart-scale", data),
  };

  dataTable("#table-electricity", [
    { label: "Year", value: r => r.year },
    { label: "TWh per year", value: r => r.twh, num: true },
    { label: "Share of US electricity", value: r => r.pct, num: true },
  ], [...data.electricity.map(d => ({ year: d.year, twh: d.twh, pct: d.pct_us ? `${d.pct_us}%` : "–" })),
      { year: "2028 (projection)", twh: `${data.projection.low_twh}–${data.projection.high_twh}`, pct: `${data.projection.low_pct}–${data.projection.high_pct}%` }]);
  dataTable("#table-scale", [
    { label: "Facility or place", value: r => `${r.label} (${r.when})` },
    { label: "Megawatts", value: r => d3.format(",")(Math.round(r.mw)), num: true },
    { label: "Source", value: r => r.source },
  ], data.facilities);

  return charts;
}
