// Hero background: every operating and planned data center as a point of light on an Albers USA map.
// Points fade in over ~2.5 s, then a few at a time pulse softly. Static when reduced motion is requested.
async function initHero() {
  const data = await d3.json("data/sites.json");
  d3.select("#hero-n-op").text(data.operating.toLocaleString());
  d3.select("#hero-n-pl").text(data.planned.toLocaleString());

  const canvas = document.querySelector(".hero-map");
  const ctx = canvas.getContext("2d");
  const rgb = d3.rgb(C.dc).brighter(0.3);   // a touch lighter than --dc so the points glow on the dark map
  let pts = [], start = null, raf = null;

  function layout() {
    const dpr = window.devicePixelRatio || 1, w = canvas.clientWidth, h = canvas.clientHeight;
    canvas.width = w * dpr; canvas.height = h * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    // Map sits to the right on wide screens (title on the left), centred on narrow ones
    const left = w > 900 ? w * 0.28 : w * 0.02;
    const proj = d3.geoAlbersUsa().fitExtent([[left, h * 0.08], [w * 0.98, h * 0.92]],
      { type: "MultiPoint", coordinates: data.points.map(p => [p[0], p[1]]) });
    pts = data.points.map(p => {
      const xy = proj([p[0], p[1]]);
      return xy && { x: xy[0], y: xy[1], op: p[2] === 1, delay: Math.random() * 2500, phase: Math.random() * Math.PI * 2 };
    }).filter(Boolean);
  }

  function draw(t) {
    if (start === null) start = t;
    const el = t - start;
    ctx.clearRect(0, 0, canvas.clientWidth, canvas.clientHeight);
    for (const p of pts) {
      const a = REDUCED ? 1 : Math.min(1, Math.max(0, (el - p.delay) / 600));
      if (a === 0) continue;
      const pulse = REDUCED ? 1 : 0.75 + 0.25 * Math.sin(el / 1400 + p.phase);
      if (p.op) {
        ctx.beginPath(); ctx.arc(p.x, p.y, 5, 0, Math.PI * 2);     // soft glow
        ctx.fillStyle = `rgba(${rgb.r},${rgb.g},${rgb.b},${0.18 * a * pulse})`; ctx.fill();
        ctx.beginPath(); ctx.arc(p.x, p.y, 1.8, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${rgb.r},${rgb.g},${rgb.b},${a})`; ctx.fill();
      } else {
        ctx.beginPath(); ctx.arc(p.x, p.y, 2, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(${rgb.r},${rgb.g},${rgb.b},${0.75 * a * pulse})`; ctx.lineWidth = 0.9; ctx.stroke();
      }
    }
    if (!REDUCED) raf = requestAnimationFrame(draw);
  }

  layout();
  raf = requestAnimationFrame(draw);
  window.addEventListener("resize", () => { layout(); if (REDUCED) requestAnimationFrame(draw); });
  // Stop animating once the hero is off screen
  new IntersectionObserver(([e]) => {
    if (REDUCED) return;
    if (e.isIntersecting && raf === null) raf = requestAnimationFrame(draw);
    if (!e.isIntersecting && raf !== null) { cancelAnimationFrame(raf); raf = null; }
  }).observe(canvas);
}
