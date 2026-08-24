# ADR 0006: Multi-Page Product Site Routing

**Status:** Accepted
**Date:** 2026-08-24
**Scope:** `apps/product` (build, routing, deployment shape)
**Supersedes:** —
**Companion:** HAR-214 (Linear), HAR-42 (canceled), `docs/agents/issue-tracker.md`

## Context

The product site (`apps/product`) is a zero-framework static surface: one hand-authored
`index.html`, three CSS layers, one ES module (`src/main.js`), built by a ~15-line
`scripts/build.mjs` and served by Cloudflare Workers assets. Site v2 (HAR-213) gives every
section a dedicated page and every registered metro a subpage, which forces a routing
decision before any page work starts.

Options weighed:

1. **Client-side router SPA** — one document, history-API routing. Rejected: breaks the
   existing `<noscript>` fallback contract, weakens per-route SEO and agent crawlability,
   and contradicts the evidence-first positioning (every claim should live at a stable,
   linkable URL without JavaScript).
2. **SSG framework (Astro et al.)** — ADR 0003 named Astro for a future marketing site,
   but the static site shipped first (HAR-43) and the Astro scaffold was canceled as its
   duplicate (HAR-42). Adopting a framework now would discard a working, dependency-free
   surface for a content scale (~25 documents) that does not justify it.
3. **Plain static multi-page** — extend the existing build emitter. No new dependencies;
   matches how the site already works; deploy target unchanged.

## Decision

Adopt **directory-index emission** in `scripts/build.mjs`:

- Source layout: root `index.html` remains the home page; additional routes live at
  `pages/<route>.html` (nesting allowed: `pages/cities/nyc.html`).
- Emission: each source becomes `dist/<route>/index.html` — a real directory index, not an
  extension-mangled file. This is stable under Workers assets `html_handling`
  ("auto-trailing-slash" default serves `/system/` → `/system/index.html`) and under plain
  static servers used in local dev.
- All asset and data references inside site HTML use root-absolute paths
  (`/src/styles.css`, `/facts.json`, `/public/favicon.svg`) so identical markup works at any
  route depth until the shared shell lands.
- Navigation links point at trailing-slash route paths; the current page is marked with
  `aria-current="page"` (styled lime in `polish.css`).
- Per-city subpages will reuse the same emitter, fed by generated per-city JSON from the
  registry exporter (HAR-217) rather than hand-authored HTML.

## Consequences

- Zero new build or runtime dependencies; the emitter stays small and inspectable.
- Chrome (topbar/nav/footer) is temporarily duplicated across `pages/*.html`;
  HAR-216 replaces the duplication with an extracted shared shell. Until then, chrome
  changes must be applied to all page sources.
- Every navigation is a full document load: honest, cacheable, crawlable — no hydration,
  no client state to trust.
- `_redirects` is untouched (`/dashboard` → external dashboard host); query-string
  preservation through that redirect becomes relevant when per-city deep links land (HAR-251).
- `verify-agent-surface.mjs` keeps asserting home-page markers; extending its assertions to
  every route is HAR-243's scope.
