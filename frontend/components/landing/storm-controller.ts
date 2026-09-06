const clamp = (value: number) => Math.min(1, Math.max(0, value));
const between = (value: number, start: number, end: number) => clamp((value - start) / (end - start));
const ease = (value: number) => value * value * (3 - 2 * value);

const vocabulary = ["{ }", "[ ]", "=>", "form.tsx", "onClick()", "/players", "state/", "name", "number", "list.map()", "return", "storage.ts", "...", "+", "/ui", "data/", "render()", "save()"];

// Stable positions and bounded text. No random source, timers, or per-glyph DOM.
export function createFragments(mobile: boolean) {
  const limit = mobile ? 330 : 850;
  const result: { text: string; x: number; y: number; layer: number }[] = [];
  let glyphs = 0;
  for (let index = 0; index < 150; index++) {
    const text = vocabulary[(index * 7 + 3) % vocabulary.length];
    if (glyphs + text.length > limit) break;
    glyphs += text.length;
    result.push({ text, x: ((index * 137 + 67) % 997) / 997, y: ((index * 229 + 113) % 991) / 991, layer: index % 3 });
  }
  return result;
}

type Scene = {
  element: HTMLElement;
  kind: string;
  pin: boolean;
  top: number;
  height: number;
  stageHeight: number;
  canvas: HTMLCanvasElement | null;
  context: CanvasRenderingContext2D | null;
  width: number;
  canvasHeight: number;
  ratio: number;
  lensMaxScale: number;
  verbs: HTMLElement[];
};

const desktopFragments = createFragments(false);
const mobileFragments = createFragments(true);

function paint(scene: Scene, progress: number, mobile: boolean, font: string) {
  const { context: ctx, width, canvasHeight: height } = scene;
  if (!ctx || !width || !height) return;
  ctx.setTransform(scene.ratio, 0, 0, scene.ratio, 0, 0);
  ctx.clearRect(0, 0, width, height);
  const fragments = mobile ? mobileFragments : desktopFragments;
  const order = scene.kind === "scope" ? ease(between(progress, 0.46, 0.93)) : 0;
  const freeze = scene.kind === "scope" ? Math.min(progress, 0.28) : progress;
  const density = scene.kind === "speed" ? 0.12 + 0.88 * progress : 1;
  const visibleCount = Math.round(fragments.length * density);
  for (let index = 0; index < visibleCount; index++) {
    const part = fragments[index];
    const size = (mobile ? 12 : 15) + part.layer * (mobile ? 2 : 5);
    const speed = scene.kind === "speed" ? progress * progress : freeze;
    const scatteredX = part.x * (width - 60) + Math.sin(index * 2.4 + speed * 3) * (mobile ? 14 : 45);
    const scatteredY = part.y * (height - 30) + Math.cos(index * 1.7 + speed * 4) * (mobile ? 20 : 60);
    const targetX = width * (mobile ? 0.76 : 0.79) + (index % 4) * 12;
    const targetY = height * 0.22 + (index % 5) * height * 0.115;
    const x = scatteredX * (1 - order) + targetX * order;
    const y = scatteredY * (1 - order) + targetY * order;
    ctx.font = `${size}px ${font}`;
    ctx.fillStyle = scene.kind === "gap" && index % 7 === 0 ? "#b69b75" : ["#62596b", "#907d9c", "#b394c0"][part.layer];
    let opacity = scene.kind === "speed" ? 0.32 + part.layer * 0.2 : 0.36 + part.layer * 0.17;
    if (scene.kind === "scope") {
      opacity *= 1 - 0.86 * between(progress, 0.22, 0.48);
      opacity *= 1 - order;
    }
    ctx.globalAlpha = opacity;
    ctx.fillText(part.text, x, y);
  }
  ctx.globalAlpha = 1;
}

/** One controller per landing mount. Scroll is native and RAF is event-coalesced:
 * no idle loop, no per-frame React updates, and no layout reads during painting.
 * The returned cleanup invalidates callbacks as well as cancelling their IDs.
 */
export function createStormController(root: HTMLElement): () => void {
  if (typeof IntersectionObserver === "undefined" || typeof ResizeObserver === "undefined" || !window.matchMedia) return () => {};
  const motion = window.matchMedia("(prefers-reduced-motion: no-preference) and (min-height: 700px)");
  const scenes: Scene[] = Array.from(root.querySelectorAll<HTMLElement>("[data-storm-act]"))
    .filter(element => ["speed", "gap", "scope"].includes(element.dataset.stormAct ?? ""))
    .map(element => ({ element, kind: element.dataset.stormAct!, pin: element.hasAttribute("data-storm-pin"), top: 0, height: 0, stageHeight: 0, canvas: element.querySelector("canvas"), context: null, width: 0, canvasHeight: 0, ratio: 1, lensMaxScale: 1.38, verbs: Array.from(element.querySelectorAll<HTMLElement>("[data-storm-verb]")) }));
  const active = new Set<Scene>();
  let disposed = false;
  let frame: number | null = null;
  let mobile = false;
  let dirtyGeometry = true;
  let font = "monospace";

  function cancel() {
    if (frame !== null) window.cancelAnimationFrame(frame);
    frame = null;
  }

  function measure() {
    mobile = window.innerWidth <= 600;
    font = getComputedStyle(root).getPropertyValue("--font-v2-mono").trim() || "monospace";
    for (const scene of scenes) {
      const rect = scene.element.getBoundingClientRect();
      scene.top = rect.top + window.scrollY;
      scene.height = rect.height;
      scene.stageHeight = scene.element.querySelector<HTMLElement>("[data-storm-stage]")?.getBoundingClientRect().height ?? window.innerHeight;
      const focusWidth = scene.element.querySelector<HTMLElement>("[data-storm-focus]")?.clientWidth;
      if (focusWidth) scene.lensMaxScale = Math.max(1, Math.min(1.38, (window.innerWidth - 32) / focusWidth));
      if (!active.has(scene) || !scene.canvas) continue;
      const field = scene.canvas.parentElement!;
      scene.width = field.clientWidth;
      scene.canvasHeight = field.clientHeight;
      scene.ratio = Math.min(window.devicePixelRatio || 1, mobile ? 1.5 : 2);
      const width = Math.round(scene.width * scene.ratio);
      const height = Math.round(scene.canvasHeight * scene.ratio);
      if (scene.canvas.width !== width || scene.canvas.height !== height) {
        scene.canvas.width = width;
        scene.canvas.height = height;
      }
      if (!scene.context) scene.context = scene.canvas.getContext("2d");
      if (scene.context) field.dataset.canvasReady = "true";
    }
    dirtyGeometry = false;
  }

  function render() {
    if (dirtyGeometry) measure();
    for (const scene of active) {
      const p = scene.pin
        ? clamp((window.scrollY - scene.top) / Math.max(1, scene.height - scene.stageHeight))
        : clamp((window.scrollY + window.innerHeight - scene.top) / (scene.height + window.innerHeight));
      const style = scene.element.style;
      if (scene.kind === "scope") {
        const lock = ease(between(p, 0, 0.28));
        const organize = ease(between(p, 0.48, 0.92));
        const spread = mobile ? 1 : Math.min(1, window.innerWidth / 1440);
        style.setProperty("--lens-x", `${(1 - lock) * (mobile ? -28 : -180 * spread)}px`);
        style.setProperty("--lens-y", `${(1 - lock) * (mobile ? 50 : 90)}px`);
        style.setProperty("--lens-scale", `${0.68 + lock * 0.32 + between(p, 0.35, 0.58) * (scene.lensMaxScale - 1)}`);
        style.setProperty("--lens-opacity", `${1 - between(p, 0.51, 0.61)}`);
        style.setProperty("--copy-opacity", `${between(p, 0.08, 0.24)}`);
        style.setProperty("--focus-opacity", `${1 - between(p, 0.46, 0.55)}`);
        // These same five DOM fragments live in the storm, then become the
        // method. Their scale/placement resolves; no second set replaces them.
        style.setProperty("--method-opacity", `${0.18 + 0.82 * between(p, 0.5, 0.68)}`);
        style.setProperty("--verb-scale", `${0.32 + 0.68 * organize}`);
        style.setProperty("--details-opacity", `${between(p, 0.82, 0.98)}`);
        style.setProperty("--rule-opacity", `${between(p, 0.72, 0.98) * 0.16}`);
        scene.verbs.forEach((verb, index) => {
          const offsets = mobile ? [100, 8, 165, 25, 70] : [600, 20, 760, 420, 60];
          verb.style.setProperty("--verb-x", `${offsets[index] * spread * (1 - organize)}px`);
          const vertical = [-25, 60, -100, 35, -20];
          verb.style.setProperty("--verb-y", `${vertical[index] * (mobile ? 0.5 : 1) * (1 - organize)}px`);
        });
      } else if (scene.kind === "gap") {
        // A clipped hard stop at the end, not another pin or a slow crossfade.
        style.setProperty("--gap-cut", `${between(p, 0.67, 0.74) * 100}%`);
      }
      paint(scene, p, mobile, font);
    }
  }

  function schedule() {
    if (disposed || !motion.matches || document.hidden || !active.size || frame !== null) return;
    const owned = window.requestAnimationFrame(() => {
      if (disposed || frame !== owned) return;
      frame = null;
      if (motion.matches && !document.hidden) render();
    });
    frame = owned;
  }

  function invalidate() { dirtyGeometry = true; schedule(); }
  function syncMotion() {
    cancel();
    if (motion.matches) root.dataset.motion = "on";
    else {
      delete root.dataset.motion;
      for (const scene of scenes) {
        if (scene.canvas) delete scene.canvas.parentElement!.dataset.canvasReady;
      }
    }
    invalidate();
  }
  function syncVisibility() { if (document.hidden) cancel(); else invalidate(); }

  const intersection = new IntersectionObserver(entries => {
    if (disposed) return;
    for (const entry of entries) {
      const scene = scenes.find(item => item.element === entry.target);
      if (!scene) continue;
      if (entry.isIntersecting) active.add(scene); else active.delete(scene);
    }
    if (!active.size) cancel();
    invalidate();
  });
  const resize = new ResizeObserver(() => { if (!disposed) invalidate(); });
  for (const scene of scenes) { intersection.observe(scene.element); resize.observe(scene.element); }
  resize.observe(root);
  window.addEventListener("scroll", schedule, { passive: true });
  window.addEventListener("resize", invalidate);
  document.addEventListener("visibilitychange", syncVisibility);
  motion.addEventListener("change", syncMotion);
  void document.fonts?.ready.then(() => { if (!disposed) invalidate(); });
  syncMotion();

  return () => {
    disposed = true;
    cancel();
    intersection.disconnect();
    resize.disconnect();
    active.clear();
    window.removeEventListener("scroll", schedule);
    window.removeEventListener("resize", invalidate);
    document.removeEventListener("visibilitychange", syncVisibility);
    motion.removeEventListener("change", syncMotion);
    delete root.dataset.motion;
    for (const scene of scenes) {
      scene.element.removeAttribute("style");
      scene.verbs.forEach(verb => { verb.style.removeProperty("--verb-x"); verb.style.removeProperty("--verb-y"); });
      if (scene.canvas) delete scene.canvas.parentElement!.dataset.canvasReady;
    }
  };
}
