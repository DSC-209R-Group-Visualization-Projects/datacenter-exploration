// Page wiring: progress bar, header, scroll steps, statement reveals.
(async function main() {
  const header = document.querySelector(".site-header");
  const bar = document.querySelector(".progress-bar");
  const hero = document.querySelector(".hero");
  function onScroll() {
    const max = document.documentElement.scrollHeight - window.innerHeight;
    bar.style.transform = `scaleX(${max > 0 ? window.scrollY / max : 0})`;
    header.classList.toggle("solid", window.scrollY > hero.offsetHeight - 80);
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  // Title reveal: hold the full title for a moment once the font has loaded, then fade to "ai in America"
  document.fonts.ready.then(() => setTimeout(() => document.querySelector(".hero-title").classList.add("revealed"), 2000));

  initHero();
  const charts = { ...(await initBackstory()), ...(await initBuildout()), ...(await initPushback()),
    ...(await initGrid()), ...(await initBills()), ...(await initWater()) };

  // A step becomes active when it crosses the middle of the viewport. On phones the chart fills the top of the
  // screen, so the trigger line sits lower and the active card reads below the chart.
  const trigger = matchMedia("(max-width: 900px)").matches ? "-80% 0px -20% 0px" : "-50% 0px -50% 0px";
  for (const section of document.querySelectorAll(".scrolly")) {
    const chart = charts[section.id];
    const steps = section.querySelectorAll(".step");
    let current = -1;
    const io = new IntersectionObserver(entries => {
      for (const e of entries) {
        if (!e.isIntersecting) continue;
        const i = +e.target.dataset.step;
        if (i === current) continue;
        current = i;
        steps.forEach(s => s.classList.toggle("is-active", s === e.target));
        chart.update(i);
      }
    }, { rootMargin: trigger });
    steps.forEach(s => io.observe(s));
  }

  // Closing statements fade up one at a time
  const reveal = new IntersectionObserver(entries => {
    for (const e of entries) if (e.isIntersecting) e.target.classList.add("is-visible");
  }, { rootMargin: "0px 0px -35% 0px" });
  document.querySelectorAll(".statement, .aim, .verdict").forEach(el => reveal.observe(el));

  // Apollo 11, then Colossus: Apollo fades up with the first statement, gives way to Colossus with the second halfway, and both fade at the end
  const moon = document.querySelector(".moon");
  if (moon) {
    const ramp = (v, a, b) => Math.min(1, Math.max(0, (v - a) / (b - a)));
    let ticking = false;
    const paint = () => {
      ticking = false;
      const r = moon.getBoundingClientRect(), p = ramp(-r.top, 0, r.height - innerHeight);
      // 0 until the section is 60% of the way up the screen, full once its top has scrolled 20% past
      const enter = ramp(-r.top, -0.4 * innerHeight, 0.2 * innerHeight), swap = ramp(p, 0.4, 0.6), leave = 1 - ramp(p, 0.82, 1);
      moon.style.setProperty("--apollo", (enter * (1 - swap)).toFixed(3));
      moon.style.setProperty("--xai", (swap * leave).toFixed(3));
      // The statements swap without overlapping: the first is gone before the second appears
      moon.style.setProperty("--text1", (enter * (1 - ramp(p, 0.36, 0.46))).toFixed(3));
      moon.style.setProperty("--text2", (ramp(p, 0.54, 0.64) * leave).toFixed(3));
      moon.style.setProperty("--moon-p", p.toFixed(3));
    };
    addEventListener("scroll", () => { if (!ticking) { ticking = true; requestAnimationFrame(paint); } }, { passive: true });
    addEventListener("resize", paint);
    paint();
  }
})();
