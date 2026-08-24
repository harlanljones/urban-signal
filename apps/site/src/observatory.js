const TAU = Math.PI * 2;
const palette = ["#c5f36a", "#55c9b2", "#f2785c", "#d8bd62"];
function hexPath(ctx, x, y, size) { ctx.beginPath(); for (let i = 0; i < 6; i += 1) { const a = Math.PI / 6 + i * TAU / 6; const px = x + Math.cos(a) * size; const py = y + Math.sin(a) * size; i ? ctx.lineTo(px, py) : ctx.moveTo(px, py); } ctx.closePath(); }
export function createObservatory(canvas, options = {}) {
  if (!canvas) return { setState() {}, destroy() {} };
  const state = { scrollProgress: 0, activeLayer: 0, pointer: { x: 0, y: 0 }, reducedMotion: Boolean(options.reducedMotion) };
  // Keep one renderer and let the browser choose the lightest supported surface.
  // The 2D path is deliberately complete so WebGL-disabled browsers retain the same evidence geometry.
  const ctx = canvas.getContext("2d");
  if (!ctx || typeof ctx.clearRect !== "function") return { setState() {}, destroy() {} };
  let raf = 0; let visible = true; let destroyed = false; let start = performance.now();
  const size = () => { const rect = canvas.getBoundingClientRect(); const dpr = Math.min(devicePixelRatio || 1, 2); canvas.width = Math.max(1, Math.floor(rect.width * dpr)); canvas.height = Math.max(1, Math.floor(rect.height * dpr)); return { w: rect.width, h: rect.height, dpr }; };
  const render = (now) => { if (destroyed) return; if (visible) { const { w, h, dpr } = size(); ctx.save(); ctx.scale(dpr, dpr); ctx.clearRect(0, 0, w, h); const t = state.reducedMotion ? 0 : (now - start) / 1000; const drift = (state.pointer.x / Math.max(innerWidth, 1) - .5) * 14; const cx = w * .68 + drift; const cy = h * .52 + state.scrollProgress * 26;
      ctx.globalAlpha = .32; ctx.strokeStyle = "#4e796d"; ctx.lineWidth = 1; for (let row = -2; row < 15; row += 1) for (let col = -2; col < 20; col += 1) { const x = col * 44 + (row % 2) * 22; const y = row * 38; const wave = Math.sin(col * .31 + row * .53 + t * .18) * 2; hexPath(ctx, x + wave, y + wave, 21); ctx.stroke(); }
      for (let layer = 0; layer < 4; layer += 1) { const y = h * (.16 + layer * .17) + Math.sin(t * .1 + layer) * (state.reducedMotion ? 0 : 4); const skew = layer * 13 + state.scrollProgress * 16; ctx.save(); ctx.translate(cx - w * .05 + skew, y); ctx.rotate(-.11); ctx.globalAlpha = layer === state.activeLayer ? .42 : .22; ctx.fillStyle = `${palette[layer]}18`; ctx.strokeStyle = palette[layer]; ctx.lineWidth = layer === state.activeLayer ? 1.4 : .7; ctx.beginPath(); ctx.moveTo(-w * .12, -h * .08); ctx.lineTo(w * .42, -h * .12); ctx.lineTo(w * .5, h * .08); ctx.lineTo(-w * .04, h * .13); ctx.closePath(); ctx.fill(); ctx.stroke(); for (let i = 0; i < 9; i += 1) for (let j = 0; j < 5; j += 1) { const px = -w * .02 + i * 39 + Math.sin(i + j) * 5; const py = -h * .03 + j * 27; hexPath(ctx, px, py, 9); ctx.fillStyle = `${palette[layer]}${i % 3 === 0 ? "aa" : "35"}`; ctx.fill(); } ctx.restore(); }
      ctx.restore(); } raf = requestAnimationFrame(render); };
  const observer = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; if (visible && !raf) raf = requestAnimationFrame(render); }, { threshold: 0 }); observer.observe(canvas); const resize = () => size(); addEventListener("resize", resize, { passive: true }); raf = requestAnimationFrame(render);
  return { setState(next = {}) { Object.assign(state, next); }, destroy() { destroyed = true; cancelAnimationFrame(raf); observer.disconnect(); removeEventListener("resize", resize); ctx.clearRect(0, 0, canvas.width, canvas.height); } };
}
