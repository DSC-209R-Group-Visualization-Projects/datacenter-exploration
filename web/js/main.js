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

  // Backstory, facility scale, the Chapter 1 map, the grid map and the water map: let the closing card rise to the top of the chart before the chart scrolls away.
  // The bottom padding is the chart's height minus the card's, measured so it holds whatever size the card text is
  const holdLast = () => document.querySelectorAll("#scrolly-electricity, #scrolly-scale, #scrolly-buildout, #scrolly-grid, #scrolly-water").forEach(sec => {
    const steps = sec.querySelector(".steps"), last = steps.querySelector(".step:last-child");
    steps.style.paddingBottom = innerWidth > 900 ? Math.max(0, sec.querySelector(".sticky").offsetHeight - last.offsetHeight) + "px" : "";
  });
  holdLast();
  document.fonts.ready.then(holdLast);
  addEventListener("resize", holdLast);

  // Closing statements fade up one at a time; backstory photos fade in once and stay
  const reveal = new IntersectionObserver(entries => {
    for (const e of entries) if (e.isIntersecting) e.target.classList.add("is-visible");
  }, { rootMargin: "0px 0px -35% 0px" });
  document.querySelectorAll(".statement, .verdict").forEach(el => reveal.observe(el));

  // Apollo 11, then Colossus, then the protest, then black behind the central question: each layer comes in with its statement,
  // and all fade at the end
  const moon = document.querySelector(".moon");
  if (moon) {
    const ramp = (v, a, b) => Math.min(1, Math.max(0, (v - a) / (b - a)));
    let ticking = false;
    const paint = () => {
      ticking = false;
      const r = moon.getBoundingClientRect(), p = ramp(-r.top, 0, r.height - innerHeight);
      // 0 until the section is 60% of the way up the screen, full once its top has scrolled 20% past
      const enter = ramp(-r.top, -0.4 * innerHeight, 0.2 * innerHeight), leave = 1 - ramp(p, 0.96, 1);
      const swap1 = ramp(p, 0.246, 0.323), swap2 = ramp(p, 0.508, 0.585), swap3 = ramp(p, 0.769, 0.831);
      moon.style.setProperty("--apollo", (enter * (1 - swap1)).toFixed(3));
      moon.style.setProperty("--xai", (swap1 * (1 - swap2)).toFixed(3));
      moon.style.setProperty("--push", (swap2 * (1 - swap3)).toFixed(3));
      moon.style.setProperty("--black", (swap3 * leave).toFixed(3));
      // The statements swap without overlapping: each is gone before the next appears
      moon.style.setProperty("--text1", (enter * (1 - ramp(p, 0.215, 0.262))).toFixed(3));
      moon.style.setProperty("--text2", (ramp(p, 0.277, 0.323) * (1 - ramp(p, 0.477, 0.523))).toFixed(3));
      moon.style.setProperty("--text3", (ramp(p, 0.538, 0.585) * (1 - ramp(p, 0.738, 0.785))).toFixed(3));
      moon.style.setProperty("--text4", (ramp(p, 0.800, 0.846) * leave).toFixed(3));
      moon.style.setProperty("--moon-p", p.toFixed(3));
    };
    addEventListener("scroll", () => { if (!ticking) { ticking = true; requestAnimationFrame(paint); } }, { passive: true });
    addEventListener("resize", paint);
    paint();
  }

  // Black scenes (end of Chapter 2, and the grid, bills and water verdicts): black comes up as each section reaches the top, the statement fades in
  // on it, and both fade at the end (except the closing line, which ends the page)
  const bridges = document.querySelectorAll(".bridge");
  if (bridges.length) {
    const ramp = (v, a, b) => Math.min(1, Math.max(0, (v - a) / (b - a)));
    let ticking = false;
    const paint = () => {
      ticking = false;
      for (const bridge of bridges) {
        const r = bridge.getBoundingClientRect(), p = ramp(-r.top, 0, r.height - innerHeight), leave = bridge.classList.contains("bridge-end") ? 1 : 1 - ramp(p, 0.85, 1);
        bridge.style.setProperty("--black", (ramp(-r.top, -0.5 * innerHeight, 0) * leave).toFixed(3));
        bridge.style.setProperty("--text4", (ramp(p, 0.1, 0.3) * leave).toFixed(3));
      }
    };
    addEventListener("scroll", () => { if (!ticking) { ticking = true; requestAnimationFrame(paint); } }, { passive: true });
    addEventListener("resize", paint);
    paint();
    // Each statement's cue scrolls on to the next statement (data-to is where it is fully shown, as a share of the section)
    moon.querySelectorAll("[data-to]").forEach(cue => cue.addEventListener("click", e => {
      e.preventDefault();
      const top = moon.getBoundingClientRect().top + scrollY + +cue.dataset.to * (moon.offsetHeight - innerHeight);
      scrollTo({ top, behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
    }));
  }
  // End of the page: 3 seconds after the closing line is fully up, offer a way back to the top. Hidden again on scrolling back up
  const toTop = document.querySelector(".to-top"), end = document.querySelector(".bridge-end");
  if (toTop && end) {
    let timer = null;
    const check = () => {
      const full = +end.style.getPropertyValue("--text4") >= 0.99;
      if (full && !timer) timer = setTimeout(() => toTop.classList.add("show"), 3000);
      if (!full && timer) { clearTimeout(timer); timer = null; toTop.classList.remove("show"); }
    };
    // After the black scenes repaint this frame, so --text4 is current
    addEventListener("scroll", () => requestAnimationFrame(check), { passive: true });
    requestAnimationFrame(check);
    toTop.addEventListener("click", () =>
      scrollTo({ top: 0, behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" }));
  }
  // Play button: scrolls the whole page in 7 minutes at an even pace (from the top if already at the end). The button pauses it,
  // and so does any wheel, touch, key or click from the reader
  const play = document.querySelector(".autoplay");
  if (play) {
    const TOTAL_MS = 420000, root = document.documentElement, word = play.querySelector("span");
    let raf = null, last, y;
    const stop = () => {
      if (raf === null) return;
      cancelAnimationFrame(raf); raf = null;
      root.style.scrollBehavior = "";
      play.classList.remove("playing"); word.textContent = "Play";
      play.setAttribute("aria-label", "Play: auto-scroll through the story");
    };
    const frame = now => {
      const max = root.scrollHeight - innerHeight;   // re-read each frame, as held charts can change the page height
      y = Math.min(max, y + (now - last) * max / TOTAL_MS); last = now;
      scrollTo(0, y);
      if (y >= max) stop(); else raf = requestAnimationFrame(frame);
    };
    const start = () => {
      root.style.scrollBehavior = "auto";   // the page's smooth scrolling would fight the per-frame steps
      y = scrollY >= root.scrollHeight - innerHeight - 2 ? 0 : scrollY;
      last = performance.now(); raf = requestAnimationFrame(frame);
      play.classList.add("playing"); word.textContent = "Pause";
      play.setAttribute("aria-label", "Pause auto-scroll");
    };
    play.addEventListener("click", () => raf === null ? start() : stop());
    ["wheel", "touchstart", "keydown", "pointerdown"].forEach(t => addEventListener(t, e => {
      if (!(e.target instanceof Element && e.target.closest(".autoplay"))) stop();
    }, { passive: true }));
  }
  // Idle scroll cue: after 7 seconds with no scrolling or input, show the cue at the bottom of the screen, unless a section's own
  // cue is already showing (the hero and the black scenes) or the reader has reached the end of the page
  const idle = document.querySelector(".idle-cue");
  if (idle) {
    const own = [...document.querySelectorAll(".scroll-cue:not(.idle-cue)")];
    const ownShowing = () => own.some(el => {
      const r = el.getBoundingClientRect();
      return r.bottom > 0 && r.top < innerHeight && +getComputedStyle(el).opacity > 0.1;
    });
    let timer;
    const wake = () => {
      idle.classList.remove("show");
      clearTimeout(timer);
      timer = setTimeout(() => {
        const atEnd = scrollY + innerHeight >= document.documentElement.scrollHeight - 40;
        if (!atEnd && !ownShowing()) idle.classList.add("show");
      }, 7000);
    };
    ["scroll", "wheel", "keydown", "pointerdown", "touchstart"].forEach(t => addEventListener(t, wake, { passive: true }));
    idle.addEventListener("click", e => {
      e.preventDefault();
      scrollBy({ top: innerHeight * 0.7, behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
    });
    wake();
  }
})();
