import { renderPage } from "./shell.mjs";

const REPOSITORY = "https://github.com/harlanljones/urban-signal";
const FEEDS = [
  { key: "permits", label: "Permits" },
  { key: "311", label: "311" },
  { key: "sla", label: "Licenses" },
  { key: "deeds", label: "Deeds" },
];

const esc = (value) => String(value).replace(/&/g, "&amp;").replace(/</g, "&lt;");
const cadenceLabel = (seconds) => (seconds % 60 === 0 ? `${seconds / 60} min` : `${seconds}s`);
const coord = (value, positive, negative) => `${Math.abs(value).toFixed(4)}° ${value >= 0 ? positive : negative}`;

function missingFeedLine(key) {
  switch (key) {
    case "deeds":
      return "Property-transfer momentum is <strong>not measured here</strong> — ownership-turnover narratives are unsupported by this metro’s feeds.";
    case "sla":
      return "Commercial-licensing momentum is <strong>not measured here</strong> — license-led reads are unsupported.";
    case "311":
      return "Service-request shift context is <strong>absent</strong> — demand-shift reads are unsupported.";
    case "permits":
      return "Permit velocity is <strong>not measured here</strong> — construction-commitment reads are unsupported.";
  }
}

function howToRead(detail) {
  const available = FEEDS.filter(({ key }) => detail.feeds[key]);
  const missing = FEEDS.filter(({ key }) => !detail.feeds[key]);
  const names = available.map(({ label }) => label);
  let html = "";
  if (missing.length === 0) {
    html += `<p>${esc(detail.name)} publishes <strong>all four signal families</strong>, so its momentum score reads across the full spectrum — construction commitment, service-demand shifts, commercial licensing, and property transfers. Cross-family conclusions are supported.</p>`;
  } else {
    html += `<p>${esc(detail.name)} is <strong>${esc(names.join(", "))}</strong>-led. Its momentum score moves on ${esc(names.join(", ").toLowerCase())} alone.</p>`;
    html += missing.map(({ key }) => `<p>${missingFeedLine(key)}</p>`).join("");
  }
  html += `<p>Feed cadence bounds freshness: this page states each feed’s declared poll interval, and staleness is audited against it. Coverage facts on this page are generated from the registry — they cannot disagree with it.</p>`;
  return html;
}

function coverageRows(detail) {
  return FEEDS.map(({ key, label }) => {
    const spec = detail.feeds[key];
    if (!spec) {
      return `<tr><th scope="row">${label}</th><td class="cell-none"><span aria-label="not published">— not published</span></td><td class="cell-none">—</td></tr>`;
    }
    return `<tr><th scope="row">${label}</th><td><span class="cell-platform">${esc(spec.platform)}</span><span class="cell-cadence">every ${cadenceLabel(spec.interval_seconds)}</span></td><td><span class="cell-watermark">${esc(spec.watermark_col || "declared in registry")}</span></td></tr>`;
  }).join("");
}

function divisionBlocks(detail) {
  const entries = Object.entries(detail.divisions);
  if (!entries.length) {
    return `<p class="city-empty-note">Division and submarket breakdown lands with this metro’s first syncs — the registry entry is authoritative meanwhile.</p>`;
  }
  return entries
    .map(([key, division]) => {
      const chips = (division.submarkets || []).map((name) => `<span class="chip">${esc(name)}</span>`).join("");
      return `<div class="division-block">
        <h3>${esc(division.name)}<span class="mono division-count">${(division.submarkets || []).length} submarkets</span></h3>
        <div class="chip-row">${chips || '<span class="city-empty-note">No submarket roster yet.</span>'}</div>
      </div>`;
    })
    .join("");
}

export function renderCityPage(detail, facts) {
  const content = `
    <section class="section-wrap section-block city-head" aria-labelledby="city-title">
      <span class="mono label">REGISTERED METRO</span>
      <h1 id="city-title">${esc(detail.name)}<em class="city-state-em"> / ${esc(detail.state)}</em></h1>
      <p class="city-coords mono">CENTER ${coord(detail.center.lat, "N", "S")} · ${coord(detail.center.lng, "E", "W")} · REGISTRY-DERIVED COVERAGE</p>
      <div class="closing-routes city-actions">
        <a class="route-primary" href="/dashboard?city=${encodeURIComponent(detail.id)}"><span>Open the live map</span><small>The dashboard precomputes this metro’s signals</small></a>
        <a class="route-secondary" href="${REPOSITORY}/blob/main/${detail.evidence_path}" target="_blank" rel="noreferrer"><span>Audit the source contract</span><small>${esc(detail.evidence_path)}</small></a>
      </div>
    </section>

    <section class="section-wrap section-block" aria-labelledby="city-coverage-title">
      <div class="section-heading">
        <span class="mono label">COVERAGE</span>
        <h2 id="city-coverage-title">What publishes here,<br><em>and what does not.</em></h2>
        <p>Generated from the registry — a cell shows the platform, its poll cadence, and the watermark column that drives incremental sync.</p>
      </div>
      <div class="matrix-wrap">
        <table class="coverage-table city-table">
          <caption class="sr-only">${esc(detail.name)} feed coverage: platform, cadence, watermark</caption>
          <thead><tr><th scope="col">Feed family</th><th scope="col">Platform + cadence</th><th scope="col">Watermark column</th></tr></thead>
          <tbody>${coverageRows(detail)}</tbody>
        </table>
      </div>
      <p class="matrix-note mono">MACHINE TWIN · <a href="/public/cities/${detail.id}.json">/public/cities/${detail.id}.json</a> · FROM ${esc(detail.generated_from)}</p>
    </section>

    <section class="section-wrap section-block" aria-labelledby="city-divisions-title">
      <div class="section-heading">
        <span class="mono label">GEOGRAPHY</span>
        <h2 id="city-divisions-title">Divisions &amp;<br><em>submarkets.</em></h2>
        <p>The registry’s roster for this metro — the same boundaries the dashboard and the H3 joins use.</p>
      </div>
      <div class="division-wrap">${divisionBlocks(detail)}</div>
    </section>

    <section class="section-wrap section-block" aria-labelledby="city-read-title">
      <div class="section-heading">
        <span class="mono label">READING GUIDE</span>
        <h2 id="city-read-title">How to read<br><em>this metro’s signals.</em></h2>
      </div>
      <div class="city-read">${howToRead(detail)}</div>
    </section>

    <section class="section-wrap section-block city-limits-section" aria-labelledby="city-limits-title">
      <div class="section-heading">
        <span class="mono label">THE BOUNDARY</span>
        <h2 id="city-limits-title">Published <em>limitations.</em></h2>
      </div>
      <ul class="city-limits">
        ${facts.limitations.map((limitation) => `<li>${esc(limitation)}</li>`).join("")}
      </ul>
    </section>`;

  const breadcrumb = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "Home", item: "/" },
      { "@type": "ListItem", position: 2, name: "Cities", item: "/cities/" },
      { "@type": "ListItem", position: 3, name: detail.name, item: `/cities/${detail.id}/` },
    ],
  };
  const dataset = {
    "@context": "https://schema.org",
    "@type": "Dataset",
    name: `${detail.name} municipal feed coverage`,
    description: `Registry-derived coverage for ${detail.name} (${detail.state}): which municipal feed families publish, on which platform, at what cadence.`,
    url: `/cities/${detail.id}/`,
    sameAs: [`${REPOSITORY}/blob/main/${detail.evidence_path}`, `/public/cities/${detail.id}.json`],
    isAccessibleForFree: true,
    creator: { "@type": "Organization", name: "Urban Signal", url: REPOSITORY },
    keywords: ["municipal data", "permits", "311", "licenses", "deeds", detail.state],
  };

  return renderPage({
    route: "cities",
    title: `${detail.name} — Urban Signal`,
    description: `${detail.name} (${detail.state}) coverage: which feed families publish, on which platform, at what cadence — registry-derived, with honest limits.`,
    content,
    extraHead: `<script type="application/ld+json">${JSON.stringify(breadcrumb)}</script>
<script type="application/ld+json">${JSON.stringify(dataset)}</script>`,
  });
}
