// Chapter 3, is the grid under strain. One map of grid regions, coloured by NERC's risk rating:
//  0) the regions themselves, uncoloured, with datacenter sites on top
//  1) NERC's 2026 ratings appear
//  2) sites in Elevated or High regions light up; the bars above the map count them
//  3) the map plays forward year by year to 2030 (the notebook's slider, now driven by the scroll)
//  4) the verdict. The year buttons let the reader scrub any year at any step.
// Risk is one orange ramp that brightens with risk (validated as an ordinal ramp on --bg). Sites are pale dots
// here because orange now means grid risk.

const RISK_LEVELS = ["Normal", "Elevated", "High"];
const RISK_COLORS = ["#5c443c", "#b0552f", "#f58a4e"];
const NO_RISK = "#262624";   // the region before ratings appear, and regions NERC doesn't rate here
const AREA_LABELS = { PJM: "PJM", MISO: "MISO", ERCOT: "ERCOT", SPP: "SPP", "New York": "NY", "New England": "New England",
  "SERC-East": "SERC-East", "SERC-Southeast": "SERC-Southeast", "SERC-Central": "SERC-Central", "SERC-Florida": "Florida",
  "WECC-Northwest": "Northwest", "WECC-Basin": "Basin", "WECC-California": "California", "WECC-Southwest": "Southwest",
  "WECC-Rocky Mountain": "Rockies" };
const PHONE_AREAS = ["PJM", "MISO", "ERCOT", "SPP", "WECC-Northwest"];

function GridChart(container, data, states) {
  const fmt = d3.format(",");
  const STEPS = [
    { year: null, sub: "Grid regions, grouped by NERC assessment area" },
    { year: 2026, sub: "NERC rating of the risk of running short of power" },
    { year: 2026, sub: "Datacenters in regions rated Elevated or High risk", lit: true },
    { year: 2030, sub: "Datacenters in regions rated Elevated or High risk", lit: true, play: true },
    { year: 2030, sub: "Datacenters in regions rated Elevated or High risk", lit: true },
  ];
  const years = data.years;
  let step = 0, year = null, lit = false, svg, W, H, narrow, timer;

  function render() {
    const s = sizedSvg(container);
    svg = s.svg; W = s.width; H = s.height;
    svg.selectAll("*").remove();
    narrow = W < 560;
    const TOP = narrow ? 128 : 104;   // legend row, then the two count bars, then the map

    const proj = d3.geoAlbersUsa().fitExtent([[0, TOP + 6], [W, H]], { type: "FeatureCollection", features: states });
    const path = d3.geoPath(proj);
    const mapG = svg.append("g").attr("class", "grid-map");
    // States underneath, so counties no utility region covers read as land, not holes
    mapG.append("path").attr("d", path({ type: "FeatureCollection", features: states })).attr("fill", "#1c1c1b");
    mapG.append("g").attr("class", "regions").selectAll("path").data(data.regions).join("path")
      .attr("d", path).attr("stroke", C.bg).attr("stroke-width", 0.6)
      .on("pointerenter pointermove", (e, f) => {
        const p = f.properties, r = year && p.risk ? p.risk[years.indexOf(year)] : null;
        tip.show(`<b>${p.area || p.name}</b>${p.area ? `<br><span style="color:${C.muted}">${p.name}</span>` : ""}` +
          (p.risk ? (r ? `<br>${r} risk in ${year}` : "") + `<br>${fmt(p.op)} operating, ${fmt(p.pl)} planned in the area`
            : "<br>Not rated in this assessment"), e);
      })
      .on("pointerleave", () => tip.hide());
    mapG.append("path").attr("class", "state-lines").attr("pointer-events", "none")
      .attr("d", path({ type: "FeatureCollection", features: states }))
      .attr("fill", "none").attr("stroke", "rgba(255,255,255,0.10)").attr("stroke-width", 0.5);

    const sites = data.sites.map(d => { const xy = proj([d[0], d[1]]); return xy && { x: xy[0], y: xy[1], op: d[2] === 1, risk: d.slice(3) }; })
      .filter(Boolean).sort((a, b) => a.op - b.op);
    mapG.append("g").attr("class", "g-sites").attr("pointer-events", "none").selectAll("circle").data(sites).join("circle")
      .attr("cx", d => d.x).attr("cy", d => d.y).attr("r", d => (narrow ? 1.5 : 2) * (d.op ? 1 : 0.9))
      .attr("fill", d => d.op ? C.text : "none").attr("stroke", d => d.op ? C.bg : C.text)
      .attr("stroke-width", d => d.op ? 0.4 : 0.8);

    // Area labels at the centre of each assessment area
    const areas = d3.groups(data.regions.filter(f => f.properties.area), f => f.properties.area)
      .filter(([a]) => AREA_LABELS[a] && (!narrow || PHONE_AREAS.includes(a)))
      .map(([a, fs]) => ({ a, xy: path.centroid({ type: "FeatureCollection", features: fs }) }));
    mapG.append("g").attr("class", "area-labels").attr("pointer-events", "none").selectAll("text").data(areas).join("text")
      .attr("class", "label-strong").attr("x", d => d.xy[0]).attr("y", d => d.xy[1]).attr("text-anchor", "middle")
      .attr("font-size", narrow ? 11 : 12.5).attr("stroke", C.bg).attr("stroke-width", 3).attr("paint-order", "stroke")
      .attr("stroke-linejoin", "round").text(d => AREA_LABELS[d.a]);
    mapG.append("text").attr("class", "year-badge").attr("x", W - 4).attr("y", H - 8).attr("text-anchor", "end");

    // Legend: risk swatches, then the site keys
    const leg = svg.append("g").attr("class", "legend");
    const keys = RISK_LEVELS.map((r, i) => ({ label: r, color: RISK_COLORS[i] })).concat([{ label: "not rated", color: NO_RISK }]);
    const kg = leg.selectAll("g").data(keys).join("g");
    kg.append("rect").attr("width", 12).attr("height", 12).attr("rx", 2).attr("fill", d => d.color)
      .attr("stroke", d => d.color === NO_RISK ? C.axis : "none");
    kg.append("text").attr("class", "label").attr("x", 17).attr("y", 10.5).text(d => d.label);
    let lx = 0;   // lay the keys out by their measured width
    kg.attr("transform", function () { const x = lx; lx += this.getBBox().width + 14; return `translate(${x},4)`; });
    const dots = leg.append("g").attr("transform", narrow ? "translate(6,34)" : `translate(${lx + 4},10)`);
    dots.append("circle").attr("r", 3).attr("fill", C.text);
    dots.append("text").attr("class", "label").attr("x", 8).attr("y", 4).text("operating");
    dots.append("circle").attr("cx", 86).attr("r", 2.6).attr("fill", "none").attr("stroke", C.text).attr("stroke-width", 1);
    dots.append("text").attr("class", "label").attr("x", 94).attr("y", 4).text("planned");

    // Two stacked bars: operating and planned sites by the risk rating of their region in the chosen year
    const barsTop = narrow ? 64 : 34, bh = 12, labW = narrow ? 0 : 74;
    const xb = d3.scaleLinear([0, 1], [labW, W - (narrow ? 0 : 150)]);   // room on the right for "69% High, 9% Elevated"
    const bars = svg.append("g").attr("class", "risk-bars");
    ["operating", "pipeline"].forEach((g, i) => {
      const row = bars.append("g").attr("class", `rb-${g}`).attr("transform", `translate(0,${barsTop + i * (narrow ? 32 : 30)})`);
      row.append("text").attr("class", "label").attr("x", narrow ? 0 : labW - 10).attr("y", narrow ? -4 : bh - 1)
        .attr("text-anchor", narrow ? "start" : "end").text(g === "operating" ? `Operating (${data.operating})` : `Planned (${data.planned})`);
      row.append("text").attr("class", "label rb-note").attr("x", W).attr("y", narrow ? -4 : bh - 1)
        .attr("text-anchor", "end");
      row.selectAll("rect").data(RISK_LEVELS.concat(["not assessed"])).join("rect").attr("height", bh)
        .attr("fill", (_, k) => RISK_COLORS[k] || NO_RISK).attr("x", labW).attr("width", 0)
        .on("pointerenter pointermove", (e, r) => {
          const n = (data.by_year[year] || {})[g]?.[r] || 0, tot = g === "operating" ? data.operating : data.planned;
          tip.show(`<b>${fmt(n)} ${g === "operating" ? "operating" : "planned"}</b> (${Math.round(n / tot * 100)}%)<br>in ${r === "not assessed" ? "regions not assessed" : r + " risk regions"}, ${year}`, e);
        })
        .on("pointerleave", () => tip.hide());
    });
    xb.labW = labW; bars.node().__xb = xb;

    setYear(year, 0);
  }

  function setYear(y, dur = DUR) {
    year = y;
    const yi = years.indexOf(y), t = svg.transition().duration(dur).ease(d3.easeCubicInOut);
    d3.selectAll("#grid-years button").classed("active", function () { return +this.dataset.year === y; })
      .attr("aria-pressed", function () { return +this.dataset.year === y; });
    svg.selectAll(".regions path").transition(t)
      .attr("fill", f => yi < 0 || !f.properties.risk ? NO_RISK : RISK_COLORS[RISK_LEVELS.indexOf(f.properties.risk[yi])]);
    svg.selectAll(".g-sites circle").transition(t)
      .attr("opacity", d => !lit || yi < 0 ? (d.op ? 0.85 : 0.55) : d.risk[yi] >= 1 ? (d.op ? 1 : 0.8) : 0.18);
    svg.select(".year-badge").text(yi < 0 ? "" : y);

    // Count bars
    const xb = svg.select(".risk-bars").node().__xb;
    svg.select(".risk-bars").transition(t).attr("opacity", yi < 0 ? 0 : 1);
    if (yi < 0) return;
    for (const g of ["operating", "pipeline"]) {
      const tot = g === "operating" ? data.operating : data.planned, counts = data.by_year[y][g];
      let acc = 0;
      svg.selectAll(`.rb-${g} rect`).each(function (r) {
        const n = counts[r] || 0, x0 = acc; acc += n / tot;
        d3.select(this).transition(t).attr("x", xb(x0) + (x0 > 0 ? 1 : 0)).attr("width", Math.max(0, xb(acc) - xb(x0) - (x0 > 0 ? 1 : 0)));
      });
      // Same split as the text: share in High and share in Elevated regions
      svg.select(`.rb-${g} .rb-note`).text(["High", "Elevated"].filter(r => counts[r])
        .map(r => `${Math.round(counts[r] / tot * 100)}% ${r}`).join(", "));
    }
  }

  function update(i, dur = DUR) {
    clearInterval(timer);
    step = i;
    const st = STEPS[i];
    lit = !!st.lit;
    d3.select("#grid-sub").text(st.sub);
    svg.select(".area-labels").transition().duration(dur).attr("opacity", i === 0 ? 1 : 0.55);
    if (st.play && !REDUCED) {
      // Play the years forward from wherever the map is now (2026 when scrolling down)
      let y = Math.max(years[0], Math.min(year || years[0], st.year));
      setYear(y, dur);
      timer = setInterval(() => {
        if (y >= st.year) { clearInterval(timer); return; }
        setYear(++y, dur * 0.8);
      }, dur * 1.1);
    } else setYear(st.year, dur);
  }

  d3.selectAll("#grid-years button").on("click", function () { clearInterval(timer); setYear(+this.dataset.year); });
  render();
  window.addEventListener("resize", debounce(render, 150));
  return { update: i => update(i) };
}

async function initGrid() {
  const [data, buildout] = await Promise.all([d3.json("data/grid.json"), d3.json("data/buildout.json")]);
  d3.select("#grid-years").selectAll("button").data(data.years).join("button").attr("type", "button")
    .attr("data-year", y => y).text(y => y);
  const chart = GridChart("#chart-grid", data, buildout.states);
  const rows = d3.groups(data.regions.filter(f => f.properties.area), f => f.properties.area)
    .map(([area, fs]) => ({ area, risk: fs[0].properties.risk, op: fs[0].properties.op, pl: fs[0].properties.pl }))
    .sort((a, b) => b.op - a.op);
  dataTable("#table-grid", [{ label: "NERC assessment area", value: r => r.area }]
    .concat(data.years.map((y, i) => ({ label: String(y), value: r => r.risk[i] })))
    .concat([{ label: "Operating", value: r => r.op, num: true }, { label: "Planned", value: r => r.pl, num: true }]), rows);
  return { "scrolly-grid": chart };
}
