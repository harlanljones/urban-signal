const NAV = [
  { route: "system", label: "System" },
  { route: "evidence", label: "Evidence" },
  { route: "methodology", label: "Methodology" },
  { route: "cities", label: "Cities" },
  { route: "architecture", label: "Code" },
];

const BRAND_MARK = '<svg viewBox="0 0 32 32"><path d="M16 2v28M2 16h28M7 7l18 18M25 7 7 25"/><circle cx="16" cy="16" r="7"/></svg>';
const FONTS = "https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;500;600;700&family=Newsreader:opsz,wght@6..72,400;6..72,500&display=swap";
const REPOSITORY = "https://github.com/harlanljones/urban-signal";
export const SITE_ORIGIN = "https://urban-signal.harlanljones.com";

const JSON_LD = `  <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "WebSite",
      "name": "Urban Signal",
      "description": "Open-source, evidence-traceable spatial intelligence built from municipal telemetry.",
      "isAccessibleForFree": true,
      "sameAs": "${REPOSITORY}",
      "about": {
        "@type": "SoftwareSourceCode",
        "name": "Urban Signal",
        "codeRepository": "${REPOSITORY}",
        "programmingLanguage": ["Python", "JavaScript"]
      },
      "keywords": ["municipal data", "spatial intelligence", "H3", "permits", "311", "open source"]
    }
  </script>`;

function renderNav(current) {
  const links = NAV.map(({ route, label }) =>
    `<a href="/${route}/"${route === current ? ' aria-current="page"' : ""}>${label}</a>`
  ).join("\n      ");
  return `    <nav id="nav" class="nav" aria-label="Primary navigation">
      ${links}
      <a class="nav-cta" href="/dashboard">Live demo <svg class="icon" viewBox="0 0 20 20" aria-hidden="true"><path d="M3 10h13M11 5l5 5-5 5"/></svg></a>
    </nav>`;
}

const DEFAULT_NOSCRIPT = `<div class="no-script"><p>Interactive controls require JavaScript. Product facts and evidence remain available:</p><a href="/facts.json">Machine-readable facts</a> · <a href="/llms-full.txt">Full agent context</a> · <a href="${REPOSITORY}">Repository</a></div>`;

export function renderPage({ route = "", title, description, content, noscript, extraHead = "", jsonLd = null }) {
  const current = NAV.some(({ route: r }) => r === route) ? route : "";
  const path = route ? `/${route}/` : "/";
  const canonical = `${SITE_ORIGIN}${path}`;
  const pageLd = jsonLd ? `<script type="application/ld+json">${JSON.stringify(jsonLd)}</script>` : "";
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#07110f">
  <meta name="description" content="${description}">
  <link rel="canonical" href="${canonical}">
  <meta property="og:title" content="${title}">
  <meta property="og:description" content="${description}">
  <meta property="og:url" content="${canonical}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Urban Signal">
  <meta name="twitter:card" content="summary">
  <link rel="icon" href="/public/favicon.svg">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="${FONTS}" rel="stylesheet">
  <link rel="alternate" type="text/plain" href="/llms.txt" title="LLM summary">
  <link rel="alternate" type="application/json" href="/facts.json" title="Machine-readable product facts">
  <link rel="stylesheet" href="/src/styles.css">
  <link rel="stylesheet" href="/src/overdrive.css">
  <link rel="stylesheet" href="/src/polish.css">
  <link rel="stylesheet" href="/src/extras.css">
${JSON_LD}
${pageLd}
${extraHead}
  <title>${title}</title>
</head>
<body>
<a class="skip-link" href="#content">Skip to content</a>
<div class="site-shell">
  <header class="topbar">
    <a class="brand" href="/" aria-label="Urban Signal home">
      <span class="brand-mark" aria-hidden="true">${BRAND_MARK}</span>
      <span>Urban Signal</span>
    </a>
    <button class="menu-toggle" type="button" aria-expanded="false" aria-controls="nav">Menu</button>
${renderNav(current)}
  </header>

  <main id="content">
${content}
  </main>

  <footer class="footer section-wrap">
    <a class="brand" href="/"><span class="brand-mark" aria-hidden="true">${BRAND_MARK}</span><span>Urban Signal</span></a>
    <nav class="agent-links" aria-label="Machine-readable resources"><a href="/llms.txt">LLM guide</a><a href="/facts.json">Product facts</a><a href="/llms-full.txt">Agent context</a></nav>
    <nav class="site-links" aria-label="Site reference"><a href="/glossary/">Glossary</a><a href="/changelog/">Changelog</a></nav>
    <span class="mono">OPEN SOURCE / EVIDENCE FIRST</span>
  </footer>
</div>
<noscript>${noscript || DEFAULT_NOSCRIPT}</noscript>
<script type="module" src="/src/main.js"></script>
</body>
</html>
`;
}
