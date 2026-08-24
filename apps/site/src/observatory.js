const TAU = Math.PI * 2;
const SQRT3 = Math.sqrt(3);
const palette = ["#c5f36a", "#55c9b2", "#f2785c", "#d8bd62"];
const layerNames = ["Permits", "311", "Licenses", "Deeds"];

const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
const lerp = (from, to, amount) => from + (to - from) * amount;
const hash = (x, y, layer = 0) => {
  const value = Math.sin(x * 91.7 + y * 183.3 + layer * 47.1) * 43758.5453;
  return value - Math.floor(value);
};

function hexPath(ctx, x, y, size) {
  ctx.beginPath();
  for (let index = 0; index < 6; index += 1) {
    const angle = Math.PI / 6 + index * TAU / 6;
    const pointX = x + Math.cos(angle) * size;
    const pointY = y + Math.sin(angle) * size;
    index ? ctx.lineTo(pointX, pointY) : ctx.moveTo(pointX, pointY);
  }
  ctx.closePath();
}

function rgba(hex, alpha) {
  const value = Number.parseInt(hex.slice(1), 16);
  return `rgba(${value >> 16}, ${(value >> 8) & 255}, ${value & 255}, ${alpha})`;
}

export function createObservatory(canvas, options = {}) {
  if (!canvas) return { setState() {}, destroy() {} };
  const ctx = canvas.getContext("2d", { alpha: true });
  if (!ctx) return { setState() {}, destroy() {} };

  const state = {
    scrollProgress: 0,
    activeLayer: 0,
    pointer: { x: 0, y: 0 },
    pointerTarget: { x: 0, y: 0 },
    pointerActive: false,
    reducedMotion: Boolean(options.reducedMotion)
  };
  const routes = [
    [[.5, .2], [.61, .3], [.72, .27], [.82, .4], [.93, .36]],
    [[.47, .65], [.58, .55], [.69, .59], [.8, .48], [.96, .55]],
    [[.58, .08], [.66, .19], [.77, .16], [.88, .26]],
    [[.54, .82], [.65, .7], [.75, .76], [.9, .65]]
  ];
  let raf = 0;
  let visible = true;
  let destroyed = false;
  let lastInspection = "";
  let bounds = { w: 1, h: 1, dpr: 1 };
  const startedAt = performance.now();

  function resize() {
    const rect = canvas.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const pixelWidth = Math.max(1, Math.floor(rect.width * dpr));
    const pixelHeight = Math.max(1, Math.floor(rect.height * dpr));
    if (canvas.width !== pixelWidth || canvas.height !== pixelHeight) {
      canvas.width = pixelWidth;
      canvas.height = pixelHeight;
    }
    bounds = { w: rect.width, h: rect.height, dpr };
    if (!state.pointerTarget.x && !state.pointerTarget.y) {
      state.pointer = { x: rect.width * .73, y: rect.height * .48 };
      state.pointerTarget = { ...state.pointer };
    }
  }

  function nearestCell(point) {
    const size = bounds.w < 640 ? 24 : 30;
    const horizontal = SQRT3 * size;
    const row = Math.round(point.y / (size * 1.5));
    const col = Math.round((point.x - (row % 2) * horizontal / 2) / horizontal);
    return { row, col, x: col * horizontal + (row % 2) * horizontal / 2, y: row * size * 1.5, size };
  }

  function emitInspection(cell) {
    if (typeof options.onInspect !== "function") return;
    const density = Math.round(18 + hash(cell.col, cell.row, state.activeLayer) * 72);
    const id = `8928${Math.abs(cell.col * 173 + cell.row * 97).toString(16).padStart(5, "0")}fff`;
    const key = `${id}-${state.activeLayer}-${density}`;
    if (key === lastInspection) return;
    lastInspection = key;
    options.onInspect({ id, density, layer: layerNames[state.activeLayer], active: state.pointerActive });
  }

  function drawGrid(focus, time) {
    const { w, h } = bounds;
    const size = w < 640 ? 24 : 30;
    const horizontal = SQRT3 * size;
    const rows = Math.ceil(h / (size * 1.5)) + 2;
    const cols = Math.ceil(w / horizontal) + 2;
    const convergence = 1 - Math.pow(1 - state.scrollProgress, 3);
    const fieldShift = lerp(0, w * .05, convergence);

    for (let row = -1; row < rows; row += 1) {
      for (let col = -1; col < cols; col += 1) {
        const x = col * horizontal + (row % 2) * horizontal / 2 + fieldShift;
        const y = row * size * 1.5;
        const distance = Math.hypot(x - focus.x, y - focus.y);
        const signal = hash(col, row, state.activeLayer);
        const local = clamp(1 - distance / 270, 0, 1);
        const pulse = state.reducedMotion ? 0 : Math.sin(time * 1.15 + col * .48 + row * .32) * .5 + .5;
        ctx.lineWidth = local > .72 ? 1.25 : .65;
        ctx.strokeStyle = rgba(local > .52 ? palette[state.activeLayer] : "#55756b", .12 + local * .48);
        hexPath(ctx, x, y, size - 1.2);
        ctx.stroke();
        if (signal > .8 && x > w * .38) {
          const alpha = .08 + signal * .13 + pulse * .08;
          ctx.fillStyle = rgba(palette[state.activeLayer], alpha * (local + .24));
          ctx.fill();
        }
      }
    }
  }

  function drawRoutes(time) {
    const { w, h } = bounds;
    routes.forEach((route, routeIndex) => {
      ctx.beginPath();
      route.forEach(([x, y], pointIndex) => {
        const px = x * w;
        const py = y * h;
        pointIndex ? ctx.lineTo(px, py) : ctx.moveTo(px, py);
      });
      ctx.strokeStyle = rgba(palette[routeIndex], routeIndex === state.activeLayer ? .52 : .16);
      ctx.lineWidth = routeIndex === state.activeLayer ? 1.25 : .6;
      ctx.stroke();
      for (let dot = 0; dot < 4; dot += 1) {
        const progress = state.reducedMotion ? (dot + 1) / 5 : (time * (.035 + routeIndex * .004) + dot / 4) % 1;
        const segmentPosition = progress * (route.length - 1);
        const segment = Math.min(route.length - 2, Math.floor(segmentPosition));
        const amount = segmentPosition - segment;
        const [startX, startY] = route[segment];
        const [endX, endY] = route[segment + 1];
        const x = lerp(startX, endX, amount) * w;
        const y = lerp(startY, endY, amount) * h;
        ctx.beginPath();
        ctx.arc(x, y, routeIndex === state.activeLayer ? 2.7 : 1.5, 0, TAU);
        ctx.fillStyle = rgba(palette[routeIndex], routeIndex === state.activeLayer ? .95 : .35);
        ctx.fill();
      }
    });
  }

  function drawLayers(time) {
    const { w, h } = bounds;
    const convergence = 1 - Math.pow(1 - state.scrollProgress, 3);
    const separation = lerp(h * .115, h * .035, convergence);
    const centerX = w * .73 + (state.pointer.x - w * .73) * .06;
    const centerY = h * .39 + state.scrollProgress * h * .12;
    for (let layer = 3; layer >= 0; layer -= 1) {
      const offset = (layer - 1.5) * separation;
      const float = state.reducedMotion ? 0 : Math.sin(time * .42 + layer * .8) * 3;
      const active = layer === state.activeLayer;
      ctx.save();
      ctx.translate(centerX + layer * 7, centerY + offset + float);
      ctx.rotate(-.105);
      ctx.beginPath();
      ctx.moveTo(-w * .19, -h * .075);
      ctx.lineTo(w * .18, -h * .12);
      ctx.lineTo(w * .26, h * .075);
      ctx.lineTo(-w * .11, h * .12);
      ctx.closePath();
      ctx.fillStyle = rgba(palette[layer], active ? .105 : .028);
      ctx.strokeStyle = rgba(palette[layer], active ? .78 : .22);
      ctx.lineWidth = active ? 1.2 : .65;
      ctx.fill();
      ctx.stroke();
      for (let index = 0; index < 24; index += 1) {
        const col = index % 6;
        const row = Math.floor(index / 6);
        const pointX = -w * .11 + col * w * .055 + (row % 2) * 11;
        const pointY = -h * .055 + row * h * .035;
        const activity = hash(col, row, layer);
        if (activity < .48) continue;
        hexPath(ctx, pointX, pointY, active ? 6.3 : 4.7);
        ctx.fillStyle = rgba(palette[layer], active ? .28 + activity * .48 : .13);
        ctx.fill();
      }
      ctx.restore();
    }
  }

  function drawFocus(cell, time) {
    const color = palette[state.activeLayer];
    const pulse = state.reducedMotion ? 0 : (Math.sin(time * 2.1) + 1) / 2;
    ctx.save();
    ctx.strokeStyle = rgba(color, .92);
    ctx.lineWidth = 1.4;
    hexPath(ctx, cell.x, cell.y, cell.size - 2);
    ctx.stroke();
    ctx.fillStyle = rgba(color, .08 + pulse * .06);
    ctx.fill();
    ctx.beginPath();
    ctx.arc(cell.x, cell.y, cell.size * (1.35 + pulse * .32), 0, TAU);
    ctx.strokeStyle = rgba(color, .18 - pulse * .1);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(cell.x - cell.size * 1.7, cell.y);
    ctx.lineTo(cell.x + cell.size * 1.7, cell.y);
    ctx.moveTo(cell.x, cell.y - cell.size * 1.7);
    ctx.lineTo(cell.x, cell.y + cell.size * 1.7);
    ctx.strokeStyle = rgba(color, .34);
    ctx.lineWidth = .6;
    ctx.stroke();
    ctx.restore();
  }

  function schedule() {
    if (!destroyed && visible && !raf && !state.reducedMotion) raf = requestAnimationFrame(render);
  }

  function render(now) {
    raf = 0;
    if (destroyed || !visible) return;
    const { w, h, dpr } = bounds;
    const ease = state.reducedMotion ? 1 : .085;
    state.pointer.x = lerp(state.pointer.x, state.pointerTarget.x, ease);
    state.pointer.y = lerp(state.pointer.y, state.pointerTarget.y, ease);
    const focus = nearestCell(state.pointer);
    const time = (now - startedAt) / 1000;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    ctx.save();
    drawGrid(focus, time);
    drawRoutes(time);
    drawLayers(time);
    drawFocus(focus, time);
    ctx.restore();
    emitInspection(focus);
    schedule();
  }

  const observer = new IntersectionObserver(([entry]) => {
    visible = entry.isIntersecting;
    if (visible) { resize(); render(performance.now()); schedule(); }
    else if (raf) { cancelAnimationFrame(raf); raf = 0; }
  }, { threshold: 0 });
  const onResize = () => { resize(); render(performance.now()); };
  observer.observe(canvas);
  addEventListener("resize", onResize, { passive: true });
  resize();
  render(performance.now());
  schedule();

  return {
    setState(next = {}) {
      if (next.pointer) state.pointerTarget = { ...next.pointer };
      Object.assign(state, { ...next, pointer: state.pointer });
      if (state.reducedMotion) render(performance.now());
      else schedule();
    },
    destroy() {
      destroyed = true;
      cancelAnimationFrame(raf);
      observer.disconnect();
      removeEventListener("resize", onResize);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
  };
}
