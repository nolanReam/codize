const clamp = (v: number) => Math.min(1, Math.max(0, v));
const between = (v: number, a: number, b: number) => clamp((v - a) / (b - a));
const ease = (v: number) => v * v * (3 - 2 * v);
const ramp = (p: number, a: number, b: number) => ease(between(p, a, b));
export const cue = (p: number, enter: number, full: number, leave: number, gone: number) => ramp(p, enter, full) * (1 - ramp(p, leave, gone));
export const readingHolds = { idea: [0.18, 0.245], growth: [0.405, 0.48], lost: [0.715, 0.79], questions: [0.9, 1], method: [0.67, 1] } as const;

/** Follow visual pixels only. Native scroll is never written. 85ms response,
 * 160px lag cap, delta-time aware, exact rest so the RAF can stop. */
export function followVisual(current: number, target: number, deltaMs: number) {
  const bounded = target + Math.max(-160, Math.min(160, current - target));
  const next = target + (bounded - target) * Math.exp(-Math.max(0, deltaMs) / 85);
  return Math.abs(next - target) < 0.25 ? target : next;
}
const vocabulary = ["{ }", "[ ]", "=>", "PlayerForm.tsx", "onClick()", "/players", "useEffect()", "name", "number", "stats.ts", "return", "storage.ts", "...", "+", "TeamPage.tsx", "/games", "render()", "save()", "api/"];
export function createFragments(mobile: boolean) {
  const result: { text: string; x: number; y: number; layer: number }[] = [];
  let glyphs = 0;
  for (let index = 0; index < 150; index++) {
    const text = vocabulary[(index * 7 + 3) % vocabulary.length];
    if (glyphs + text.length > (mobile ? 330 : 850)) break;
    glyphs += text.length;
    result.push({ text, x: ((index * 137 + 67) % 997) / 997, y: ((index * 229 + 113) % 991) / 991, layer: index % 3 });
  }
  return result;
}
const desktopFragments = createFragments(false), mobileFragments = createFragments(true);
type Scene = {
  element: HTMLElement; kind: string; top: number; height: number; stageHeight: number;
  canvas: HTMLCanvasElement | null; context: CanvasRenderingContext2D | null;
  width: number; canvasHeight: number; ratio: number; visual: number | null; lensMaxScale: number;
  verbs: HTMLElement[]; requests: HTMLElement[]; files: HTMLElement[]; origins: { x: number; y: number }[];
  typed: { element: HTMLElement; text: string; start: number; end: number }[];
};
// Integrated slopes keep background motion continuous and slow during holds.
function stormTravel(p: number) {
  return [[0, 0.39, 1], [0.39, 0.49, 0.08], [0.49, 0.7, 1], [0.7, 0.8, 0.04]]
    .reduce((sum, [a, b, speed]) => sum + Math.max(0, Math.min(p, b) - a) * speed, 0);
}
function paint(scene: Scene, p: number, mobile: boolean, font: string) {
  const { context: ctx, width, canvasHeight: height } = scene;
  if (!ctx || !width || !height) return;
  ctx.setTransform(scene.ratio, 0, 0, scene.ratio, 0, 0);
  ctx.clearRect(0, 0, width, height);
  const scope = scene.kind === "scope";
  if (!scope && (p < 0.27 || p >= 0.815)) return;
  const travel = scope ? Math.min(p, 0.43) * 0.3 : stormTravel(p);
  const expansion = scope ? 1 : ramp(p, 0.27, 0.65);
  const order = scope ? ramp(p, 0.43, 0.65) : 0;
  const reading = scope ? 0 : Math.max(cue(p, 0.38, 0.405, 0.48, 0.5), cue(p, 0.69, 0.715, 0.79, 0.815));
  const fragments = mobile ? mobileFragments : desktopFragments;
  fragments.forEach((part, index) => {
    const appearing = scope ? 1 : between(p, 0.27 + index / fragments.length * 0.23, 0.32 + index / fragments.length * 0.23);
    const x = width * 0.55 + (part.x - 0.55) * width * expansion + Math.sin(index * 2.4 + travel * 8) * (mobile ? 12 : 40);
    const y = height * 0.55 + (part.y - 0.55) * height * expansion + Math.cos(index * 1.7 + travel * 10) * (mobile ? 18 : 55);
    ctx.font = `${(mobile ? 11 : 13) + part.layer * (mobile ? 2 : 4)}px ${font}`;
    ctx.fillStyle = ["#62596b", "#907d9c", "#b394c0"][part.layer];
    ctx.globalAlpha = appearing * (scope ? 0.38 * (1 - order) : (0.35 + part.layer * 0.16) * (1 - reading * 0.84));
    ctx.fillText(part.text, x * (1 - order) + width * 0.25 * order, y * (1 - order) + (height * 0.2 + index % 5 * height * 0.13) * order);
  });
  ctx.globalAlpha = 1;
}

/** One owned, on-demand RAF. Cached geometry; no React state per frame.
 * Disposal, offscreen, visibility and preference changes invalidate ownership. */
export function createStormController(root: HTMLElement): () => void {
  if (typeof IntersectionObserver === "undefined" || typeof ResizeObserver === "undefined" || !window.matchMedia) return () => {};
  const motion = window.matchMedia("(prefers-reduced-motion: no-preference) and (min-height: 700px)");
  const scenes: Scene[] = Array.from(root.querySelectorAll<HTMLElement>("[data-storm-pin]")).map(element => ({
    element, kind: element.dataset.stormAct!, top: 0, height: 0, stageHeight: 0, canvas: element.querySelector("canvas"), context: null,
    width: 0, canvasHeight: 0, ratio: 1, visual: null, lensMaxScale: 1, origins: [],
    verbs: Array.from(element.querySelectorAll<HTMLElement>("[data-storm-verb]")),
    requests: Array.from(element.querySelectorAll<HTMLElement>("[data-storm-request]")),
    files: Array.from(element.querySelectorAll<HTMLElement>("[data-storm-file]")),
    typed: Array.from(element.querySelectorAll<HTMLElement>("[data-prompt-text], [data-question]")).map(node => ({
      element: node, text: node.textContent ?? "",
      start: node.hasAttribute("data-prompt-text") ? 0.115 : node.dataset.question === "first" ? 0.824 : 0.864,
      end: node.hasAttribute("data-prompt-text") ? 0.18 : node.dataset.question === "first" ? 0.848 : 0.9,
    })),
  }));
  const active = new Set<Scene>();
  const entrances = Array.from(root.querySelectorAll<HTMLElement>("[data-storm-enter]"));
  let disposed = false, frame: number | null = null, previousTime: number | null = null;
  let mobile = false, dirtyGeometry = true, font = "monospace";
  function cancel() { if (frame !== null) window.cancelAnimationFrame(frame); frame = null; previousTime = null; }
  function measure() {
    mobile = window.innerWidth <= 600;
    font = getComputedStyle(root).getPropertyValue("--font-v2-mono").trim() || "monospace";
    for (const scene of scenes) {
      const rect = scene.element.getBoundingClientRect();
      scene.top = rect.top + window.scrollY; scene.height = rect.height;
      const focusWidth = scene.element.querySelector<HTMLElement>("[data-storm-focus]")?.clientWidth;
      scene.lensMaxScale = focusWidth ? Math.max(1, Math.min(mobile ? 1.06 : 1.18, (window.innerWidth - 32) / focusWidth)) : 1;
      scene.stageHeight = scene.element.querySelector<HTMLElement>("[data-storm-stage]")?.getBoundingClientRect().height ?? window.innerHeight;
      const agent = scene.element.querySelector<HTMLElement>("[data-agent-window]");
      if (agent) {
        const originX = agent.offsetLeft + agent.offsetWidth * 0.5;
        const originY = agent.offsetTop + agent.offsetHeight * 0.55;
        scene.origins = [...scene.requests, ...scene.files].map(node => ({
          x: originX - node.offsetLeft - node.offsetWidth / 2,
          y: originY - node.offsetTop - node.offsetHeight / 2,
        }));
      }
      if (!active.has(scene) || !scene.canvas) continue;
      scene.width = scene.canvas.parentElement!.clientWidth; scene.canvasHeight = scene.canvas.parentElement!.clientHeight;
      scene.ratio = Math.min(window.devicePixelRatio || 1, mobile ? 1.5 : 2);
      const width = Math.round(scene.width * scene.ratio), height = Math.round(scene.canvasHeight * scene.ratio);
      if (scene.canvas.width !== width || scene.canvas.height !== height) { scene.canvas.width = width; scene.canvas.height = height; }
      if (!scene.context) scene.context = scene.canvas.getContext("2d");
      if (scene.context) scene.canvas.parentElement!.dataset.canvasReady = "true";
    }
    dirtyGeometry = false;
  }
  function renderScene(scene: Scene, p: number, timestamp: number) {
    const set = (name: string, value: number, unit = "") => scene.element.style.setProperty(`--${name}`, `${value}${unit}`);
    scene.element.dataset.visualProgress = p.toFixed(5);
    if (scene.kind === "journey") {
      const growth = cue(p, 0.38, 0.405, 0.48, 0.5), lost = cue(p, 0.69, 0.715, 0.79, 0.815), quiet = Math.max(growth, lost);
      const settled = 1 - Math.pow(1 - between(p, 0.025, 0.105), 2);
      set("idea-opacity", Math.max(0.15, ramp(p, 0, 0.025)) * (1 - ramp(p, 0.245, 0.275)));
      set("agent-y", (1 - settled) * scene.stageHeight * 0.8 - ramp(p, 0.28, 0.64) * 75, "px");
      set("agent-opacity", ramp(p, 0.025, 0.07) * (1 - quiet * 0.85) * (1 - ramp(p, 0.79, 0.815)));
      set("agent-scale", 1 - ramp(p, 0.28, 0.65) * 0.14);
      set("prompt-y", -ramp(p, 0.21, 0.235) * 112, "px");
      set("welcome-opacity", 1 - ramp(p, 0.205, 0.22)); set("working-opacity", ramp(p, 0.232, 0.244));
      set("possibilities-opacity", cue(p, 0.255, 0.28, 0.35, 0.385));
      set("storm-opacity", ramp(p, 0.265, 0.29) * (1 - ramp(p, 0.795, 0.815)));
      set("growth-opacity", growth); set("lost-opacity", lost);
      set("files-opacity", cue(p, 0.505, 0.53, 0.56, 0.58));
      set("connection-label-opacity", cue(p, 0.585, 0.61, 0.64, 0.66));
      set("connections-opacity", ramp(p, 0.575, 0.615) * 0.6 * (1 - quiet * 0.9));
      set("connections-dash", 1 - ramp(p, 0.575, 0.64)); set("silence-opacity", ramp(p, 0.815, 0.824));
      const travel = stormTravel(p);
      [...scene.requests, ...scene.files].forEach((node, index) => {
        const file = index >= scene.requests.length, n = file ? index - scene.requests.length : index;
        const origin = scene.origins[index] ?? { x: 0, y: 0 };
        const start = file ? 0.355 + n * 0.026 : 0.272 + n * 0.024, appear = ramp(p, start, start + 0.04);
        node.style.setProperty("--artifact-opacity", `${appear * (1 - quiet * 0.92) * (file ? 0.88 : 1 - ramp(p, 0.43, 0.68) * 0.5)}`);
        node.style.setProperty("--artifact-x", `${(1 - appear) * origin.x + Math.sin(index * 2 + travel * 7) * (mobile ? 9 : 34)}px`);
        node.style.setProperty("--artifact-y", `${(1 - appear) * origin.y + Math.cos(index * 2 + travel * 8) * (mobile ? 14 : 42)}px`);
        node.style.setProperty("--artifact-scale", `${0.7 + 0.3 * appear}`);
        node.style.setProperty("--artifact-rotate", `${file ? (n % 2 ? 1 : -1) * (2 + travel * 4) : 0}deg`);
      });
      scene.typed.forEach(({ element, text, start, end }) => {
        const next = text.slice(0, Math.floor(between(p, start, end) * text.length));
        if (element.textContent !== next) element.textContent = next;
        element.dataset.typing = String(p >= start && p < end);
      });
      // Blink while moving through typing. Steady at rest; no idle animation.
      const typing = scene.typed.some(item => p >= item.start && p < item.end);
      set("cursor-opacity", typing ? (Math.floor(timestamp / 420) % 2 ? 0 : 1) : p < 0.21 ? 1 : 0);
    } else {
      const organize = ramp(p, 0.43, 0.65);
      set("codize-opacity", 1 - ramp(p, 0.12, 0.18));
      set("focus-opacity", ramp(p, 0.16, 0.22) * (1 - ramp(p, 0.47, 0.6)));
      set("focus-scale", 0.96 + 0.04 * ramp(p, 0.16, 0.22));
      set("lens-scale", 1 + Math.sin(organize * Math.PI) * (scene.lensMaxScale - 1));
      set("peak-opacity", ramp(p, 0.395, 0.455)); set("peak-y", (1 - ramp(p, 0.395, 0.455)) * 18, "px");
      set("details-opacity", ramp(p, 0.60, 0.67)); set("rule-opacity", ramp(p, 0.58, 0.66) * 0.16);
      set("verb-scale", 0.42 + organize * 0.58);
      scene.verbs.forEach((verb, index) => {
        const x = mobile ? [4, 5, 185, 185, 52] : [20, 20, 720, 720, 300];
        const y = mobile ? [-70, -55, -230, -215, 60] : [-65, 180, -215, 40, 80];
        const spread = mobile ? Math.min(1, (window.innerWidth - 48) / 342) : Math.min(1, window.innerWidth / 1440);
        verb.style.setProperty("--verb-x", `${x[index] * spread * (1 - organize)}px`);
        verb.style.setProperty("--verb-y", `${y[index] * (1 - organize)}px`);
        verb.style.setProperty("--verb-opacity", `${ramp(p, 0.235 + index * 0.033, 0.27 + index * 0.033) * (0.4 + 0.6 * organize)}`);
      });
    }
    paint(scene, p, mobile, font);
  }
  function schedule() {
    if (disposed || !motion.matches || document.hidden || !active.size || frame !== null) return;
    const owned = window.requestAnimationFrame(timestamp => {
      if (disposed || frame !== owned) return;
      frame = null;
      if (!motion.matches || document.hidden) return;
      if (dirtyGeometry) measure();
      const delta = previousTime === null ? 16.67 : Math.min(64, Math.max(0, timestamp - previousTime));
      previousTime = timestamp;
      let moving = false;
      for (const scene of active) {
        const span = Math.max(1, scene.height - scene.stageHeight), target = clamp((window.scrollY - scene.top) / span) * span;
        scene.visual = scene.visual === null ? target : followVisual(scene.visual, target, delta);
        moving ||= scene.visual !== target;
        renderScene(scene, scene.visual / span, timestamp);
      }
      if (moving) schedule(); else previousTime = null;
    });
    frame = owned;
  }
  function invalidate() { dirtyGeometry = true; schedule(); }
  function restoreText() { scenes.forEach(scene => scene.typed.forEach(item => { item.element.textContent = item.text; delete item.element.dataset.typing; })); }
  function syncMotion() {
    cancel();
    scenes.forEach(scene => { scene.visual = null; if (scene.canvas) delete scene.canvas.parentElement!.dataset.canvasReady; });
    if (motion.matches) root.dataset.motion = "on"; else { delete root.dataset.motion; restoreText(); }
    invalidate();
  }
  function syncVisibility() { if (document.hidden) cancel(); else { scenes.forEach(scene => { scene.visual = null; }); invalidate(); } }
  const intersection = new IntersectionObserver(entries => {
    if (disposed) return;
    for (const entry of entries) {
      const entrance = entry.target as HTMLElement;
      if (entry.isIntersecting && entrance.hasAttribute("data-storm-enter")) entrance.dataset.entered = "true";
      const scene = scenes.find(item => item.element === entry.target);
      if (!scene) continue;
      if (entry.isIntersecting) active.add(scene); else { active.delete(scene); scene.visual = null; }
    }
    if (!active.size) cancel();
    invalidate();
  });
  const resize = new ResizeObserver(() => { if (!disposed) invalidate(); });
  scenes.forEach(scene => { intersection.observe(scene.element); resize.observe(scene.element); });
  entrances.forEach(entrance => intersection.observe(entrance)); resize.observe(root);
  window.addEventListener("scroll", schedule, { passive: true }); window.addEventListener("resize", invalidate);
  document.addEventListener("visibilitychange", syncVisibility); motion.addEventListener("change", syncMotion);
  void document.fonts?.ready.then(() => { if (!disposed) invalidate(); }); syncMotion();
  return () => {
    disposed = true; cancel(); intersection.disconnect(); resize.disconnect(); active.clear(); restoreText();
    window.removeEventListener("scroll", schedule); window.removeEventListener("resize", invalidate);
    document.removeEventListener("visibilitychange", syncVisibility); motion.removeEventListener("change", syncMotion);
    delete root.dataset.motion; entrances.forEach(entrance => { delete entrance.dataset.entered; });
    scenes.forEach(scene => {
      scene.element.removeAttribute("style"); delete scene.element.dataset.visualProgress;
      [...scene.verbs, ...scene.requests, ...scene.files].forEach(node => {
        Array.from(node.style).filter(name => name !== "--verb-index" && name !== "--artifact-index").forEach(name => node.style.removeProperty(name));
      });
      if (scene.canvas) delete scene.canvas.parentElement!.dataset.canvasReady;
    });
  };
}
