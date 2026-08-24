# Product Site Personas & Voice

Operationalizes the audience and brand commitments in [`PRODUCT.md`](../../PRODUCT.md)
for all product-site copy. The site v2 epic (HJ-213) ratified the weighting:
**the technical / open-source evaluator is the primary voice**; every page pairs
analyst-facing interpretation with an inspectable evidence trail. No page splits the
audiences into separate experiences (`PRODUCT.md`, Operating Context).

## Personas

### P1 — Technical / OSS evaluator (primary)

| | |
|---|---|
| Arrives from | GitHub, llms.txt, HN/lobsters, a dashboard deep-link |
| Job to be done | Decide whether the system is honest: are the claims real, does the code exist, can I reproduce it? |
| Depth expected | Methodology-grade. Contracts, failure modes, leakage controls, exact source paths. |
| Evidence need | Every non-obvious claim links a repository path or a registry-derived fact. Repro commands. |
| Lands on | `/evidence/`, `/architecture/`, `/methodology/`, city pages' evidence blocks |
| Success test | They can audit a claim end-to-end without filing a question. |

### P2 — Market / proptech analyst & investor

| | |
|---|---|
| Arrives from | "see the city before the market does" positioning, partner intros |
| Job to be done | Judge whether the signal is decision-useful: what leads, over what horizon, with what caveats. |
| Depth expected | Signal-reading guidance: LIMS ingredients, horizons, what a feed mix can and cannot support. |
| Evidence need | Composition transparency over black-box scores; horizons stated; no performance promises. |
| Lands on | `/methodology/`, `/cities/<id>`, the live dashboard |
| Success test | They can state what the score is made of and what it does not claim. |

### P3 — Planner / policy analyst

| | |
|---|---|
| Arrives from | Municipal-data circles, coverage questions ("does it have my metro?") |
| Job to be done | Understand coverage and cadence: which feeds exist, how fresh, which platform. |
| Depth expected | Matrices and cadence facts, not marketing. |
| Evidence need | Registry-derived coverage truth, including partial availability as a first-class state. |
| Lands on | `/cities/`, `/system/` |
| Success test | They can predict exactly what their metro's page will and will not show. |

### P4 — Researcher / journalist

| | |
|---|---|
| Arrives from | Citing urban-data work; verifying a claim before publishing |
| Job to be done | Cite responsibly: provenance, limitations, update cadence. |
| Depth expected | Explicit limitations blocks, machine-readable facts, stable URLs. |
| Evidence need | `facts.json`, `llms-full.txt`, limitations mirrored in prose. |
| Lands on | `/methodology/`, `/faq/` (planned), agent surfaces |
| Success test | They can quote the limitations section verbatim and be correct. |

## Voice rules (binding)

1. **Evidence-first.** Every non-obvious claim links a repository path or a
   registry-derived fact. If it cannot link, it cannot ship.
2. **No invented proof.** No customers, adoption metrics, testimonials, accuracy
   percentages, or availability promises — `PRODUCT.md` forbids fabricating them;
   `facts.json.limitations` states it publicly.
3. **Illustrative is labeled.** The hero cell and the 68/100 composition are interface
   examples, always carrying their disclosure markers (`verify-agent-surface.mjs`
   enforces this on the home page).
4. **Coverage honesty.** Never imply uniform four-feed coverage; "limited" is rendered,
   not hidden. City differences are product truth (`PRODUCT.md`, principle 3).
5. **Technically exact, generous with explanation.** Plain declarative sentences. Banned
   register: "powerful", "revolutionary", "seamless", "trusted by". The work is the pitch.
6. **Machine parity.** Anything a human can read, an agent can read: claims that change
   on a page change `llms.txt` / `facts.json` in the same change (enforced from HJ-243).

## Page-type register (maps to wave S)

| Page | Register | Persona lead |
|---|---|---|
| `/` hub | What is this, can I trust it, where do I go deeper — under two scrolls for P1 | P1 |
| `/system/` | Stage-by-stage: what enters, what changes, how failure is handled | P1, P3 |
| `/evidence/` | One record end-to-end; reproduce-it-locally block | P1 |
| `/methodology/` | Composition, horizons, leakage controls, "what LIMS is not" | P1, P2 |
| `/cities/` + `/cities/<id>` | Methodology documentation per metro; coverage matrix honesty; how to read this metro's signals | P3, P2 |
| `/architecture/` | System map, serving surface, registration rule as public docs | P1 |

## Copy checklist (every page PR)

- [ ] Every non-obvious claim links a repo path or registry-derived fact
- [ ] No banned claim classes (rule 2) and no banned register (rule 5)
- [ ] Illustrative values keep their disclosure markers
- [ ] Partial coverage rendered as limited, never smoothed
- [ ] Agent surfaces updated in the same change if claims moved
- [ ] Reads correctly with JavaScript disabled (noscript path truthful)
