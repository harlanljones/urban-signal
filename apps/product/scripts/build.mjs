import { cp, mkdir, readdir, readFile, rm, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { renderPage, SITE_ORIGIN } from "./shell.mjs";
import { renderCityPage } from "./render-city.mjs";

const root = resolve(import.meta.dirname, "..");
const dist = resolve(root, "dist");
await rm(dist, { recursive: true, force: true });
await mkdir(dist, { recursive: true });

// Minimal markdown → HTML for the changelog page, fed by the repository's
// own CHANGELOG.md. Escapes HTML first, then supports exactly what the file
// uses: ## / ### headings, "- " lists (with wrapped continuation lines),
// paragraphs, **bold**, [text](url) links, and `code` spans. The "# Changelog"
// title line is skipped — the page supplies its own heading.
function escapeHtml(text) {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function renderInline(text) {
  return text
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, '<a href="$2">$1</a>')
    .replace(/`([^`]+)`/g, "<code>$1</code>");
}

function renderChangelogMarkdown(markdown) {
  const out = [];
  let paragraph = [];
  let listItems = null;
  let lastWasList = false;
  const flushParagraph = () => {
    if (paragraph.length) {
      out.push(`      <p>${renderInline(paragraph.join(" "))}</p>`);
      paragraph = [];
    }
  };
  const closeList = () => {
    if (listItems) {
      out.push(`      <ul>\n${listItems.map((item) => `        <li>${item}</li>`).join("\n")}\n      </ul>`);
      listItems = null;
    }
    lastWasList = false;
  };
  for (const raw of markdown.split("\n")) {
    const line = raw.trim();
    if (!line || line === "---") {
      flushParagraph();
      closeList();
      continue;
    }
    if (line.startsWith("### ")) {
      flushParagraph();
      closeList();
      out.push(`      <h3>${renderInline(line.slice(4))}</h3>`);
    } else if (line.startsWith("## ")) {
      flushParagraph();
      closeList();
      out.push(`      <h2>${renderInline(line.slice(3))}</h2>`);
    } else if (line.startsWith("# ")) {
      // Document title — supplied by the page shell instead.
    } else if (/^-\s/.test(line)) {
      flushParagraph();
      if (!listItems) listItems = [];
      listItems.push(renderInline(line.replace(/^-\s+/, "")));
      lastWasList = true;
    } else if (lastWasList && /^\s{2,}\S/.test(raw)) {
      // Wrapped continuation of the previous list item.
      listItems[listItems.length - 1] += " " + renderInline(line);
    } else if (paragraph.length && /^\s{2,}\S/.test(raw)) {
      paragraph.push(line);
    } else {
      closeList();
      paragraph.push(line);
    }
  }
  flushParagraph();
  closeList();
  return out.join("\n");
}

// Assemble every route from its content fragment (pages/<name>.html) and
// metadata (pages/<name>.json) through the shared shell (scripts/shell.mjs —
// the single source of truth for head, topbar, nav, footer, and noscript
// fallback). "home" emits the root document; every other page emits
// dist/<route>/index.html. City subpages later just add fragment+meta pairs.
const pagesDir = resolve(root, "pages");
const pageRoutes = [];
for (const entry of await readdir(pagesDir)) {
  if (!entry.endsWith(".json")) continue;
  const name = entry.replace(/\.json$/, "");
  const meta = JSON.parse(await readFile(resolve(pagesDir, entry), "utf8"));
  let content = await readFile(resolve(pagesDir, `${name}.html`), "utf8");
  if (name === "changelog") {
    const markdown = await readFile(resolve(root, "CHANGELOG.md"), "utf8");
    const body = renderChangelogMarkdown(markdown);
    if (!content.includes("<!--changelog-body-->")) {
      throw new Error("pages/changelog.html is missing the <!--changelog-body--> marker");
    }
    content = content.replace("<!--changelog-body-->", body);
  }
  const html = renderPage({ route: name === "home" ? "" : name, ...meta, content });
  const outDir = name === "home" ? dist : resolve(dist, name);
  await mkdir(outDir, { recursive: true });
  await writeFile(resolve(outDir, "index.html"), html);
  pageRoutes.push(name === "home" ? "" : `${name}/`);
  console.log(`PAGE_OK /${name === "home" ? "" : name + "/"}`);
}

// Per-city subpages: one generated page per registry-derived city JSON.
// The template (scripts/render-city.mjs) consumes the per-city data only —
// adding a metro to the registry + facts:export is the whole job.
const citiesSource = resolve(root, "public/cities");
const facts = JSON.parse(await readFile(resolve(root, "public/facts.json"), "utf8"));
const cityIds = [];
for (const file of (await readdir(citiesSource)).filter((name) => name.endsWith(".json"))) {
  const detail = JSON.parse(await readFile(resolve(citiesSource, file), "utf8"));
  const outDir = resolve(dist, "cities", detail.id);
  await mkdir(outDir, { recursive: true });
  await writeFile(resolve(outDir, "index.html"), renderCityPage(detail, facts));
  cityIds.push(detail.id);
  console.log(`CITY_OK /cities/${detail.id}/`);
}

// Sitemap: every route, home first, then sections, then city pages.
const sitemapEntries = [...pageRoutes, ...cityIds.map((id) => `cities/${id}/`)]
  .map((route) => `  <url><loc>${SITE_ORIGIN}/${route}</loc></url>`)
  .join("\n");
await writeFile(
  resolve(dist, "sitemap.xml"),
  `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${sitemapEntries}\n</urlset>\n`
);
console.log(`SITEMAP_OK (${pageRoutes.length + cityIds.length} urls)`);

await cp(resolve(root, "src"), resolve(dist, "src"), { recursive: true });
await cp(resolve(root, "public"), resolve(dist, "public"), { recursive: true });
for (const asset of ["facts.json", "llms.txt", "llms-full.txt", "robots.txt"]) {
  await cp(resolve(root, "public", asset), resolve(dist, asset));
}
await cp(resolve(root, "public", "_redirects"), resolve(dist, "_redirects"));
console.log("SITE_BUILD_OK");
