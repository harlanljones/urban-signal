import { createObservatory } from "./observatory.js";

const REPOSITORY = "https://github.com/harlanljones/urban-signal";
const layers = ["Permits", "311", "Licenses", "Deeds"];
const layerDetails = {
  ingest: ["01", "Start with the records nobody designed for you.", "Socrata, ArcGIS, Carto, and CKAN endpoints arrive with different names, shapes, watermarks, and gaps. City-specific producers keep those facts intact while making the event contract consistent.", '{ <b>"source"</b>: "socrata",<br>&nbsp;&nbsp;<b>"type"</b>: "permit",<br>&nbsp;&nbsp;<b>"city_id"</b>: "sf" }', "apps/api/src/producers"],
  normalize: ["02", "Make different vocabularies comparable.", "Field maps resolve city-specific columns into typed permit, complaint, license, and deed events. Unknown fields remain available for inspection instead of disappearing into a generic bucket.", '{ <b>"event_type"</b>: "permit",<br>&nbsp;&nbsp;<b>"occurred_at"</b>: "2026-08-23",<br>&nbsp;&nbsp;<b>"lat"</b>: 37.7749 }', "apps/api/src/schemas/models.py"],
  spatial: ["03", "Give every event a neighborhood-sized address.", "The H3 indexer assigns WGS84 coordinates to resolutions 7, 8, and 9, then joins division and submarket context. This is where a flat record becomes a place.", '{ <b>"h3_res_9"</b>: "8928…",<br>&nbsp;&nbsp;<b>"division"</b>: "SF_CORE",<br>&nbsp;&nbsp;<b>"resolution"</b>: 9 }', "apps/api/src/spatial/h3_indexer.py"],
  features: ["04", "Let time and type change the meaning.", "Time-decayed CapEx, permit velocity, 311 shift dynamics, and license activity become interpretable features. The pipeline preserves the ingredients behind the score.", '{ <b>"capex_density"</b>: 0.82,<br>&nbsp;&nbsp;<b>"permit_velocity"</b>: 0.61,<br>&nbsp;&nbsp;<b>"lims"</b>: 68.0 }', "apps/api/src/features/lims_calculator.py"],
  serve: ["05", "Put the signal where a person can use it.", "PostGIS stores the spatial system of record; model artifacts support 6-, 12-, and 18-month horizons; FastAPI and edge snapshots make the result reachable without hiding the source trail.", '{ <b>"horizon"</b>: "12m",<br>&nbsp;&nbsp;<b>"prediction"</b>: 0.68,<br>&nbsp;&nbsp;<b>"explain"</b>: true }', "apps/api/src/export/snapshot_builder.py"]
};
const archDetails = {
  sources: ["Different inputs. One honest contract.", "Source-specific producers preserve municipal differences before normalization.", "apps/api/src/producers", "Inspect source producers"],
  registry: ["The registry is a product surface.", "City IDs, boundaries, divisions, submarkets, and feed availability are centralized in one authoritative contract.", "apps/api/src/spatial/city_registry.py", "Inspect the city registry"],
  kafka: ["A durable event backbone.", "Typed municipal events move through Kafka topics before workers enrich, aggregate, and sync them.", "apps/api/src/consumers", "Inspect event consumers"],
  h3: ["Space is a first-class dimension.", "H3 resolutions 7, 8, and 9 connect macro context, submarkets, and neighborhood-scale cells.", "apps/api/src/spatial/h3_indexer.py", "Inspect H3 indexing"],
  features: ["Momentum with ingredients attached.", "Feature aggregation combines time windows and spatial context into LIMS, shift dynamics, velocity, and catalyst alerts.", "apps/api/src/features/lims_calculator.py", "Inspect LIMS features"],
  storage: ["A spatial system of record.", "PostGIS stores queryable events, features, divisions, and snapshots while object storage holds partitions and model artifacts.", "apps/api/src/storage", "Inspect storage contracts"],
  models: ["Three horizons, three questions.", "Model implementations cover 6-, 12-, and 18-month horizons with spatial-temporal leakage controls.", "apps/api/src/models", "Inspect model code"],
  edge: ["The last mile is part of the evidence.", "Versioned snapshots make precomputed spatial views quick to reach without obscuring their origin.", "apps/api/src/export/snapshot_builder.py", "Inspect snapshot delivery"]
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const sourceUrl = (path) => `${REPOSITORY}/${path.includes(".") ? "blob" : "tree"}/main/${path}`;
let siteFacts = null;
let showAllCities = false;
let cityFilters = { feed: -1, platform: "all" };

function metroMatchesFilters({ feeds, platforms }) {
  if (cityFilters.feed !== -1 && !feeds[cityFilters.feed]) return false;
  if (cityFilters.platform !== "all" && !platforms.some((entry) => entry && entry.platform === cityFilters.platform)) return false;
  return true;
}

function feedSummary(feeds) {
  const available = layers.filter((_, index) => feeds[index]);
  const limited = layers.filter((_, index) => !feeds[index]);
  return {
    available: available.length ? available.join(", ") : "No feeds currently available",
    limited: limited.length ? limited.join(", ") : "None"
  };
}

function renderCities(filter = "") {
  if (!siteFacts) return;
  const query = filter.trim().toLocaleLowerCase();
  const matches = siteFacts.metros.filter(({ id, name, state, feeds, platforms }) => {
    const matchesQuery = [id, name, state].some((value) => value.toLocaleLowerCase().includes(query));
    return matchesQuery && metroMatchesFilters({ feeds, platforms });
  });
  const isCompact = matchMedia("(max-width: 600px)").matches;
  const visible = isCompact && !query && !showAllCities ? matches.slice(0, 5) : matches;
  const cityGrid = $("#city-grid");
  const cityCount = $("#city-count");
  const cityToggle = $("#city-toggle");
  if (!cityGrid || !cityCount || !cityToggle) return;

  cityGrid.replaceChildren();
  cityGrid.setAttribute("aria-busy", "false");
  cityCount.textContent = visible.length === matches.length ? `${matches.length} REGISTERED METRO${matches.length === 1 ? "" : "S"}` : `${visible.length} OF ${matches.length} METROS SHOWN`;
  cityToggle.hidden = !isCompact || Boolean(query) || matches.length <= 5;
  cityToggle.textContent = showAllCities ? "Show fewer metros" : `Show all ${matches.length} registered metros`;
  cityToggle.setAttribute("aria-expanded", String(showAllCities));

  if (!matches.length) {
    const empty = document.createElement("p");
    empty.className = "city-empty";
    empty.textContent = "No registered metro matches that name or state. Try “CA”, “New York”, or clear the search.";
    empty.setAttribute("role", "status");
    cityGrid.append(empty);
    return;
  }

  visible.forEach(({ id, name, state, divisions, feeds, platforms, evidence_path: evidencePath }) => {
    const card = document.createElement("details");
    card.className = "city-card";
    const summary = document.createElement("summary");
    const title = document.createElement("span");
    title.className = "city-title";
    title.innerHTML = '<span class="city-name"></span><span class="city-state"></span>';
    $(".city-name", title).textContent = name;
    $(".city-state", title).textContent = ` / ${state}`;
    const meta = document.createElement("span");
    meta.className = "city-meta";
    meta.innerHTML = '<span class="city-divisions"></span><span class="feeds"></span>';
    $(".city-divisions", meta).textContent = divisions;
    const feedList = $(".feeds", meta);
    const summaryText = feedSummary(feeds);
    feedList.setAttribute("aria-label", `Available: ${summaryText.available}. Limited or missing: ${summaryText.limited}.`);
    feeds.forEach((live, index) => {
      const feed = document.createElement("span");
      feed.className = `feed-token ${live ? "live" : "limited"}`;
      feed.textContent = layers[index];
      feedList.append(feed);
    });
    summary.append(title, meta);

    const evidence = document.createElement("div");
    evidence.className = "city-evidence";
    const availability = document.createElement("p");
    availability.innerHTML = `<strong>Available:</strong> ${summaryText.available}<br><strong>Limited or missing:</strong> ${summaryText.limited}`;
    const link = document.createElement("a");
    link.href = sourceUrl(evidencePath);
    link.target = "_blank";
    link.rel = "noreferrer";
    link.textContent = "Inspect this metro’s source contract";
    const twin = document.createElement("a");
    twin.href = `/cities/${id}/`;
    twin.textContent = `Open ${name}’s page`;
    const twinData = document.createElement("a");
    twinData.href = `/public/cities/${id}.json`;
    twinData.target = "_blank";
    twinData.rel = "noreferrer";
    twinData.textContent = "Machine-readable coverage";
    evidence.append(availability, link, twin, twinData);
    card.append(summary, evidence);
    cityGrid.append(card);
  });
}

function renderPlatformMatrix() {
  const host = $("#platform-matrix");
  if (!host || !siteFacts) return;
  const platforms = new Map();
  const cadence = layers.map(() => ({ metros: 0, intervals: new Set(), platforms: new Set() }));
  siteFacts.metros.forEach(({ id, platforms: feeds }) => {
    feeds.forEach((entry, index) => {
      if (!entry) return;
      if (!platforms.has(entry.platform)) platforms.set(entry.platform, new Set());
      platforms.get(entry.platform).add(id);
      cadence[index].metros += 1;
      cadence[index].intervals.add(entry.interval_seconds);
      cadence[index].platforms.add(entry.platform);
    });
  });
  const cadenceLabel = (intervals) => {
    const fmt = (seconds) => (seconds % 60 === 0 ? `${seconds / 60} min` : `${seconds}s`);
    const values = [...intervals];
    return values.length === 1 ? `every ${fmt(values[0])}` : values.map(fmt).join(" / ");
  };
  const platformBlocks = [...platforms.entries()]
    .sort((a, b) => b[1].size - a[1].size)
    .map(([name, metros]) => `<span class="platform-stat"><b>${metros.size}</b><small>${name}<br>metros</small></span>`)
    .join("");
  const cadenceRows = layers
    .map((label, index) => {
      const row = cadence[index];
      if (!row.metros) return `<tr><td>${label}</td><td>—</td><td>not published</td><td>—</td></tr>`;
      return `<tr><td>${label}</td><td>${row.metros}</td><td>${cadenceLabel(row.intervals)}</td><td>${[...row.platforms].join(", ")}</td></tr>`;
    })
    .join("");
  host.innerHTML = `
    <div class="platform-stats">${platformBlocks}</div>
    <table class="cadence-table">
      <caption class="sr-only">Feed families with publishing metro counts, poll cadence, and platforms</caption>
      <thead><tr><th scope="col">Feed family</th><th scope="col">Metros publishing</th><th scope="col">Poll cadence</th><th scope="col">Platforms</th></tr></thead>
      <tbody>${cadenceRows}</tbody>
    </table>
    <p class="matrix-note mono">DERIVED FROM REGISTRY FACTS · <a href="/facts.json">FACTS.JSON</a></p>`;
}

function renderLimitations() {
  const host = $("#limitations-list");
  if (!host || !siteFacts) return;
  host.replaceChildren();
  siteFacts.limitations.forEach((limitation) => {
    const item = document.createElement("li");
    item.textContent = limitation;
    host.append(item);
  });
}

function refreshCityViews() {
  buildCityChips();
  renderCities($("#city-filter")?.value || "");
  renderCoverageMatrix();
}

function buildCityChips() {
  const feedRow = $("#feed-chips");
  const platformRow = $("#platform-chips");
  if (!feedRow || !platformRow || !siteFacts) return;
  const chip = (parent, label, pressed, apply) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "chip";
    button.setAttribute("aria-pressed", String(pressed));
    button.textContent = label;
    button.addEventListener("click", () => { apply(); refreshCityViews(); });
    parent.append(button);
  };
  feedRow.replaceChildren();
  chip(feedRow, "All", cityFilters.feed === -1, () => { cityFilters.feed = -1; });
  layers.forEach((label, index) => chip(feedRow, label, cityFilters.feed === index, () => { cityFilters.feed = cityFilters.feed === index ? -1 : index; }));
  platformRow.replaceChildren();
  chip(platformRow, "All", cityFilters.platform === "all", () => { cityFilters.platform = "all"; });
  const platformNames = [...new Set(siteFacts.metros.flatMap(({ platforms: list }) => list.filter(Boolean).map((entry) => entry.platform)))];
  platformNames.forEach((name) => chip(platformRow, name, cityFilters.platform === name, () => { cityFilters.platform = cityFilters.platform === name ? "all" : name; }));
}

function formatAge(hours) {
  return hours >= 48 ? `${Math.round(hours / 24)}d` : `${Math.round(hours)}h`;
}

function freshTokens(metro) {
  const cityFresh = siteFacts.freshness?.[metro.id];
  if (!cityFresh || typeof cityFresh !== "object") return '<span class="fresh-missing" aria-label="no sync data">—</span>';
  const tokens = metro.platforms.flatMap((entry, index) => {
    if (!entry) return [];
    const key = siteFacts.feed_labels?.[index] ?? layers[index].toLowerCase();
    const record = cityFresh[key];
    if (!record || typeof record.age_hours !== "number") return [`<span class="fresh-token fresh-missing">${key} —</span>`];
    const stale = record.age_hours > 48;
    return [`<span class="fresh-token${stale ? " fresh-stale" : ""}" title="last synced ${record.last_synced_at ?? "unknown"}">${key} ${formatAge(record.age_hours)}</span>`];
  });
  return tokens.length ? tokens.join("") : '<span class="fresh-missing" aria-label="no sync data">—</span>';
}

function renderCoverageMatrix() {
  const host = $("#coverage-matrix");
  if (!host || !siteFacts) return;
  const query = ($("#city-filter")?.value || "").trim().toLocaleLowerCase();
  const metros = siteFacts.metros.filter(({ id, name, state, feeds, platforms }) => {
    const matchesQuery = [id, name, state].some((value) => value.toLocaleLowerCase().includes(query));
    return matchesQuery && metroMatchesFilters({ feeds, platforms });
  });
  const cadenceLabel = (seconds) => (seconds % 60 === 0 ? `${seconds / 60}m` : `${seconds}s`);
  const showFreshness = Boolean(siteFacts.freshness);
  const head = `<tr><th scope="col">Metro</th>${layers.map((label) => `<th scope="col">${label}</th>`).join("")}${showFreshness ? '<th scope="col">Freshness</th>' : ""}</tr>`;
  const rows = metros
    .map(({ id, name, state, platforms }) => {
      const cells = platforms
        .map((entry) => entry
          ? `<td><span class="cell-platform">${entry.platform}</span><span class="cell-cadence">${cadenceLabel(entry.interval_seconds)}</span></td>`
          : '<td class="cell-none"><span aria-label="not published">—</span></td>')
        .join("");
      const freshness = showFreshness ? `<td class="cell-fresh">${freshTokens({ id, platforms })}</td>` : "";
      return `<tr><th scope="row"><a class="matrix-metro" href="/cities/${id}/">${name}</a><span class="matrix-state">/ ${state}</span></th>${cells}${freshness}</tr>`;
    })
    .join("");
  host.innerHTML = `
    <div class="matrix-wrap">
      <table class="coverage-table">
        <caption class="sr-only">Coverage matrix: ${metros.length} metros by feed family, with platform and poll cadence</caption>
        <thead>${head}</thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
    <p class="matrix-note mono">${metros.length} OF ${siteFacts.metros.length} METROS · <a href="/facts.json">FACTS.JSON</a></p>`;
}

function renderCompareColumns() {
  const host = $("#compare-host");
  if (!host || !siteFacts) return;
  const picks = ["#compare-select-a", "#compare-select-b"].map((selector) => $(selector)?.value);
  if (picks.some((id) => !id)) return;
  const fmt = (seconds) => (seconds % 60 === 0 ? `${seconds / 60} min` : `${seconds}s`);
  const columns = picks
    .map((id) => siteFacts.metros.find((metro) => metro.id === id))
    .filter(Boolean)
    .map((metro) => {
      const rows = layers
        .map((label, index) => {
          const entry = metro.platforms[index];
          return `<tr><th scope="row">${label}</th>${entry
            ? `<td><span class="cell-platform">${entry.platform}</span><span class="cell-cadence">every ${fmt(entry.interval_seconds)}</span></td>`
            : '<td class="cell-none"><span aria-label="not published">—</span></td>'}</tr>`;
        })
        .join("");
      return `
      <article class="compare-col">
        <header class="compare-head"><h3><a href="/cities/${metro.id}/">${metro.name}</a><span class="matrix-state">/ ${metro.state}</span></h3><span class="mono compare-id">${metro.id}</span></header>
        <table class="cadence-table compare-table">
          <caption class="sr-only">${metro.name}: coverage by feed family</caption>
          <thead><tr><th scope="col">Feed family</th><th scope="col">Platform · cadence</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
        <p class="compare-counts mono">${metro.divisions.toUpperCase()} · ${metro.submarket_count} SUBMARKETS</p>
        <div class="compare-links">
          <a href="${sourceUrl(metro.evidence_path)}" target="_blank" rel="noreferrer">Inspect this metro’s source contract</a>
          <a href="/public/cities/${metro.id}.json" target="_blank" rel="noreferrer">Machine-readable coverage</a>
        </div>
      </article>`;
    });
  host.innerHTML = `<div class="compare-grid">${columns.join("")}</div><p class="matrix-note mono">RENDERED FROM REGISTRY FACTS · <a href="/facts.json">FACTS.JSON</a></p>`;
}

function renderCompare() {
  const host = $("#compare-host");
  const selects = [$("#compare-select-a"), $("#compare-select-b")];
  if (!host || !siteFacts || selects.some((select) => !select)) return;
  if (!selects[0].options.length) {
    siteFacts.metros.forEach(({ id, name, state }) => {
      selects.forEach((select) => {
        const option = document.createElement("option");
        option.value = id;
        option.textContent = `${name}, ${state}`;
        select.append(option);
      });
    });
    selects.forEach((select, index) => {
      select.selectedIndex = index;
      select.addEventListener("change", renderCompareColumns);
    });
  }
  renderCompareColumns();
}

async function loadFacts() {
  const cityGrid = $("#city-grid");
  try {
    const response = await fetch("/facts.json", { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    siteFacts = await response.json();
    $$('[data-metro-count]').forEach((node) => { node.textContent = siteFacts.metros.length; });
    renderCities($("#city-filter")?.value || "");
    renderPlatformMatrix();
    renderLimitations();
    buildCityChips();
    renderCoverageMatrix();
    renderCompare();
  } catch {
    if (!cityGrid) return;
    cityGrid.setAttribute("aria-busy", "false");
    cityGrid.innerHTML = '<div class="city-error" role="alert"><strong>Coverage facts could not be loaded.</strong><p>Retry the local facts file or inspect the authoritative registry directly.</p><button type="button">Retry</button><a href="https://github.com/harlanljones/urban-signal/blob/main/apps/api/src/spatial/city_registry.py">Open city registry</a></div>';
    $("button", cityGrid)?.addEventListener("click", loadFacts, { once: true });
  }
}

function mountObservatoryControls() {
  const legend = $(".layer-legend");
  if (!legend) return;
  legend.setAttribute("aria-label", "Inspect signal layer");
  $$(':scope > div', legend).forEach((item, layer) => {
    const control = document.createElement("button");
    control.type = "button";
    control.className = `layer-control${layer === 0 ? " active" : ""}`;
    control.dataset.observatoryLayer = String(layer);
    control.setAttribute("aria-pressed", String(layer === 0));
    control.append(...item.childNodes);
    item.replaceWith(control);
  });
  legend.insertAdjacentHTML("afterend", '<div class="signal-readout" aria-live="polite"><span class="mono readout-status"><i></i> ILLUSTRATIVE CELL</span><strong id="readout-layer">Permits</strong><span id="readout-cell" class="mono">H3 R9 / 89280000000fff</span><div><span>RELATIVE DENSITY</span><b id="readout-density">—</b></div><small>Move across the field to inspect</small></div>');
}

function setObservatoryLayer(layer) {
  $$('[data-observatory-layer]').forEach((control) => {
    const selected = Number(control.dataset.observatoryLayer) === layer;
    control.classList.toggle("active", selected);
    control.setAttribute("aria-pressed", String(selected));
  });
  document.dispatchEvent(new CustomEvent("observatory:layer", { detail: { layer } }));
}

function selectLayer(button) {
  $$(".pipeline-step").forEach((step) => {
    const selected = step === button;
    step.classList.toggle("active", selected);
    step.setAttribute("aria-pressed", String(selected));
  });
  const [index, title, copy, code, path] = layerDetails[button.dataset.step] || layerDetails.ingest;
  $("#detail-index").textContent = index;
  $("#detail-title").textContent = title;
  $("#detail-copy").textContent = copy;
  $("#detail-code").innerHTML = `<span class="code-comment">// illustrative ${button.dataset.step} output</span><code>${code}</code>`;
  $("#detail-source").href = sourceUrl(path);
  setObservatoryLayer((Number(index) - 1) % layers.length);
}

function init() {
  mountObservatoryControls();
  loadFacts();
  const canvas = $("#observatory-canvas");
  const hero = $(".hero");
  const renderer = createObservatory(canvas, {
    reducedMotion: matchMedia("(prefers-reduced-motion: reduce)").matches,
    onInspect: ({ id, density, layer }) => {
      $("#readout-cell").textContent = `H3 R9 / ${id}`;
      $("#readout-density").textContent = `${density}%`;
      $("#readout-layer").textContent = layer;
    }
  });
  const sync = () => renderer.setState({ scrollProgress: Math.min(1, scrollY / Math.max(1, innerHeight * 1.1)) });
  const inspect = (event) => {
    const rect = canvas.getBoundingClientRect();
    renderer.setState({ pointer: { x: event.clientX - rect.left, y: event.clientY - rect.top }, pointerActive: true });
  };
  addEventListener("scroll", sync, { passive: true });
  hero?.addEventListener("pointermove", inspect, { passive: true });
  hero?.addEventListener("pointerleave", () => renderer.setState({ pointerActive: false }));
  document.addEventListener("observatory:layer", (event) => renderer.setState({ activeLayer: event.detail.layer }));
  $$('[data-observatory-layer]').forEach((control) => control.addEventListener("click", () => setObservatoryLayer(Number(control.dataset.observatoryLayer))));
  sync();

  $("#city-filter")?.addEventListener("input", (event) => { renderCities(event.target.value); renderCoverageMatrix(); });
  $("#city-toggle")?.addEventListener("click", () => { showAllCities = !showAllCities; renderCities(); });
  matchMedia("(max-width: 600px)").addEventListener("change", () => { showAllCities = false; renderCities($("#city-filter")?.value || ""); });
  $$(".pipeline-step").forEach((button) => button.addEventListener("click", () => { selectLayer(button); button.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "nearest", inline: "center" }); }));

  const archNote = $("#arch-note");
  $$(".arch-node").forEach((button) => button.addEventListener("click", () => {
    $$(".arch-node").forEach((node) => {
      const selected = node === button;
      node.classList.toggle("selected", selected);
      node.setAttribute("aria-pressed", String(selected));
    });
    const [title, copy, path, linkLabel] = archDetails[button.dataset.arch] || archDetails.sources;
    archNote.innerHTML = '<span class="mono">SELECTED NODE</span><strong></strong><p></p><a class="source-link" target="_blank" rel="noreferrer"></a>';
    $("strong", archNote).textContent = title;
    $("p", archNote).textContent = copy;
    $("a", archNote).href = sourceUrl(path);
    $("a", archNote).textContent = linkLabel;
  }));

  const menu = $(".menu-toggle");
  const nav = $(".nav");
  const closeMenu = () => { nav?.classList.remove("open"); menu?.setAttribute("aria-expanded", "false"); if (menu) menu.textContent = "Menu"; };
  menu?.addEventListener("click", () => {
    const open = !nav?.classList.contains("open");
    nav?.classList.toggle("open", open);
    menu.setAttribute("aria-expanded", String(open));
    menu.textContent = open ? "Close" : "Menu";
  });
  $$(".nav a").forEach((link) => link.addEventListener("click", closeMenu));
  document.addEventListener("keydown", (event) => { if (event.key === "Escape") closeMenu(); });
  addEventListener("pagehide", () => { removeEventListener("scroll", sync); hero?.removeEventListener("pointermove", inspect); renderer.destroy(); }, { once: true });
}

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
else init();
