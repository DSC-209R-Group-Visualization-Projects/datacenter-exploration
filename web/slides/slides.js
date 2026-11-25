// Slide deck wiring: builds the same charts as the scrolling page, then steps through slides and their builds.
// Keys: → / Space / PageDown next, ← / PageUp back, Home / End, P play. A click on the page also moves forward.
(async function deck() {
  const slides = [...document.querySelectorAll(".slide")];
  // One entry per build, in order: which slide, which .say (if any), and how long it stays up on autoplay
  const builds = slides.flatMap((slide, s) => {
    const says = [...slide.querySelectorAll(".say")];
    return says.length ? says.map(say => ({ s, say, sec: +say.dataset.sec }))
      : [{ s, say: null, sec: +slide.dataset.sec }];
  });
  const count = document.querySelector(".deck-count");
  const bar = document.querySelector(".deck-bar");
  const play = document.querySelector(".deck-play");

  initHero();
  document.fonts.ready.then(() => setTimeout(() => document.querySelector(".hero-title").classList.add("revealed"), 1500));
  const charts = { ...(await initBackstory()), ...(await initBuildout()), ...(await initPushback()),
    ...(await initGrid()), ...(await initBills()), ...(await initWater()) };

  let at = -1, timer = null;
  function show(k) {
    k = Math.max(0, Math.min(builds.length - 1, k));
    if (k === at) return;
    const b = builds[k], prev = builds[at];
    at = k;
    slides.forEach((el, s) => el.classList.toggle("on", s === b.s));
    slides[b.s].querySelectorAll(".say").forEach(el => el.classList.toggle("on", el === b.say));
    // Drive the chart to this build's step; going back into a slide replays from its first build
    const chart = charts[slides[b.s].dataset.chart];
    if (chart && b.say && (!prev || prev.say !== b.say)) chart.update(+b.say.dataset.step);
    count.textContent = `${b.s + 1} / ${slides.length}`;
    bar.style.transform = `scaleX(${(k + 1) / builds.length})`;
    history.replaceState(null, "", `#${k + 1}`);
  }

  // Autoplay: 120 s in all, each build held for its data-sec; stops on the last slide
  function stop() { clearTimeout(timer); timer = null; play.classList.remove("playing"); play.querySelector("span").textContent = "Play"; }
  function tick() {
    timer = setTimeout(() => { if (at >= builds.length - 1) return stop(); show(at + 1); tick(); }, builds[at].sec * 1000);
  }
  function start() {
    if (at >= builds.length - 1) show(0);
    play.classList.add("playing"); play.querySelector("span").textContent = "Pause";
    tick();
  }
  play.addEventListener("click", e => { e.stopPropagation(); timer ? stop() : start(); });

  // Manual moves pause autoplay
  const go = k => { stop(); show(k); };
  window.addEventListener("keydown", e => {
    if (["ArrowRight", " ", "PageDown", "Enter"].includes(e.key)) { e.preventDefault(); go(at + 1); }
    else if (["ArrowLeft", "PageUp", "Backspace"].includes(e.key)) { e.preventDefault(); go(at - 1); }
    else if (e.key === "Home") go(0);
    else if (e.key === "End") go(builds.length - 1);
    else if (e.key === "p" || e.key === "P") timer ? stop() : start();
  });
  document.addEventListener("click", e => {
    if (e.target.closest("a, button, input, .year-pick")) return;
    go(e.clientX < innerWidth * 0.2 ? at - 1 : at + 1);   // the left edge goes back
  });

  show((parseInt(location.hash.slice(1), 10) || 1) - 1);
})();
