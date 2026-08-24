---
target: marketing site
total_score: 21
max_score: 32
na_heuristics: 7,10
p0_count: 0
p1_count: 3
timestamp: 2026-08-24T03-31-05Z
slug: apps-site-index-html
---
# Urban Signal marketing site critique

## Design Health Score

| # | Heuristic | Score | Key issue |
|---|---|---:|---|
| 1 | Visibility of System Status | 3 | Layer selection, metro count, filter state, and the live readout respond clearly; illustrative status is not applied consistently to every staged proof object. |
| 2 | Match System / Real World | 2 | H3, EPSG, CapEx, LIMS, ONNX, and Catalyst Watch arrive faster than they are explained; several metadata labels invite factual scrutiny. |
| 3 | User Control and Freedom | 3 | Anchors, reversible filtering, and Escape-to-close work; the horizontally scrolling mobile pipeline has no visible affordance. |
| 4 | Consistency and Standards | 3 | The interface is coherent, but implementation fonts and accents have drifted from the durable design document. |
| 5 | Error Prevention | 2 | Marketing facts are duplicated in source rather than derived from authoritative artifacts, and city search ignores displayed state abbreviations. |
| 6 | Recognition Rather Than Recall | 2 | Most controls are labelled, but feed availability relies on tiny colored dots and hover-only titles; technical terms lack nearby definitions. |
| 7 | Flexibility and Efficiency | n/a | Persuade surface; no repeated expert workflow. |
| 8 | Aesthetic and Minimalist Design | 3 | Exceptionally authored composition, reduced by pervasive undersized annotations and a few contrast/overlap defects. |
| 9 | Error Recovery | 3 | Search has a useful empty state and navigation can be dismissed; there are few true error paths on this surface. |
| 10 | Help and Documentation | n/a | Persuade surface; contextual explanation is assessed under match and recognition. |
| **Total** | | **21/32** | **Acceptable (66%): visually strong, trust and mobile proof path need substantive work** |

## Design Specificity Verdict

**Highly specific and authored.** The H3 evidence field, survey marks, municipal-feed language, mono measurement annotations, dark-ink/paper rhythm, and layered signal controls belong to Urban Signal. The opening feels like a night-shift municipal observatory, not a transferable proptech template.

The missed opportunity is evidentiary rather than aesthetic: the page repeatedly promises an inspectable paper trail, but the strongest proof objects remain staged summaries. The 68/100 score cannot be traced, city cards do not open their sources, architecture nodes link only indirectly through a repository-root CTA, and the closing repeats the dashboard CTA instead of completing an evidence journey.

The deterministic CLI scan returned zero findings only under a degraded regex fallback because `htmlparser2`, `css-select`, `css-tree`, and `domutils` were unavailable. That is an undercount, not a clean result. Mutable live-browser injection succeeded and rendered 74 overlays; 84 console diagnostics spanned 12 rules, dominated by 66 `undersized-ui-text` reports, plus kicker repetition, dark glows, low contrast, extreme negative tracking, text occlusion, tiny text, line length, and related findings. The `theater-slop-phrase` result is a false positive because the copy rejects “black box theater.” The cyan-palette warning conflicts with an intentional design token and is not a defect by itself.

The live overlays were removed after evidence collection, so no reliable user-visible overlay remains in the browser.

## Overall Impression

The site earns attention immediately and expresses the product with unusual specificity. Its single biggest opportunity is to turn the visual language of evidence into actual evidence interaction. Right now the hero says “instrument,” while the rest of the page too often behaves like a beautifully art-directed explainer.

## What’s Working

1. **The hero is a genuine signature.** The inspectable hex field, converging signal layers, and responsive readout make spatial intelligence tangible without falling back to a generic dashboard screenshot.
2. **Editorial and technical voices coexist well.** Newsreader, DM Sans, and DM Mono establish clear roles, while paper interludes keep the control-room vocabulary from becoming monotonous.
3. **The tone is appropriately candid.** “Different cities. Different truths.” and “composition, not a verdict” reduce model-authority anxiety and reinforce the source-limitations story.

## Cognitive Load

**Moderate: 3 of 8 checklist items fail.** Single focus, grouping, hierarchy, one-thing-at-a-time sequencing, and progressive disclosure pass. Chunking fails because the interface exposes five pipeline stages, eight architecture nodes, and 17 city comparisons. Minimal choices fails at the five-option pipeline and eight-option architecture explorer. Working memory fails on mobile because users horizontally scroll a 765px pipeline through a 343px viewport, then read details below; the architecture result is also separated from earlier nodes by a flattened mobile stack.

The mobile document is roughly 9,300px tall. The one-column city matrix consumes about 2,687px, and the closing CTA does not begin until roughly y=8,500. The problem is endurance rather than raw clutter.

## Emotional Journey

The opening is the peak: intrigue, technical authority, and the sense of seeing a city wake up. The paper proof strip provides a useful exhale, and “composition, not a verdict” reassures at the highest-stakes analytical moment.

The emotional valley begins in the coverage matrix, where 17 near-identical cards turn the central honesty claim into inventory. Architecture partly recovers interest, but the ending repeats the dashboard CTA. Under the peak-end rule, the page ends below its opening peak; a completed source-to-cell trace would create a much stronger final memory.

## Priority Issues

### [P1] “Evidence first” is asserted more often than demonstrated

**Why it matters:** Visitors cannot follow a displayed city, score, architecture node, or source layer to its provenance. This weakens the defining promise for both buyers and technical evaluators.

**Fix:** Make each city reveal source URLs, freshness, named gaps, and registry/code links. Label the score illustrative or bind it to a real snapshot. Deep-link architecture nodes to exact repository paths. Turn one pipeline example into a complete source → normalized event → H3 cell → feature → output trace.

**Suggested command:** `$impeccable shape`

### [P1] Mobile turns the proof path into endurance browsing

**Why it matters:** The 9,300px page, 2,687px city list, hidden 422px of pipeline content, and overloaded first section make the experience expensive to finish on a phone.

**Fix:** Collapse cities into a selected-city disclosure or compact list, expose a step cue for the pipeline, and simplify the mobile hero to thesis, primary CTA, and one compact inspection affordance. Preserve the full observatory farther down.

**Suggested command:** `$impeccable adapt`

### [P1] Credibility metadata is not source-bound

**Why it matters:** The registry currently contains 17 cities while PRODUCT.md still states nine, showing internal truth drift even though the rendered count matches the registry. The hero’s Tokyo coordinates are unrelated to the registered US metros, the timestamp is hard-coded, and “≈174m² hex” appears to confuse an edge-scale value with area. Small metadata errors are disproportionately damaging on a site built around technical exactness.

**Fix:** Generate city count, feed coverage, timestamps, coordinates, and spatial metadata from authoritative build artifacts. Resolve the stale product brief. Validate the H3 unit/value and label decorative or illustrative metadata explicitly. Add a build-time consistency gate.

**Suggested command:** `$impeccable harden`

### [P2] Microtype falls below the craft and accessibility floor

**Why it matters:** The live detector reported 66 undersized UI-text cases, including hero metadata, pipeline labels, city divisions, and feed labels, plus two low-contrast cases and one hero text/control occlusion. These details communicate proof; making them hard to read makes the product feel less rigorous.

**Fix:** Raise essential annotations to a readable minimum, reserve sub-10px type for nonessential measurement texture, correct coral-on-paper contrast, relax the hero tracking from -0.06em, and re-test the 900–1200px collision range. Keep dense data labels concise rather than merely small.

**Suggested command:** `$impeccable typeset`

### [P2] The closing conversion path does not serve both evaluation depths

**Why it matters:** Prospective partners and technical evaluators receive the same repeated “Live demo” route. The page never resolves the final questions “Can I trust this?” and “How do I audit it?”

**Fix:** End with two explicit routes—**Explore a real signal** and **Audit the implementation**—each paired with a concrete evidence artifact. Make the ending the payoff to the evidence journey, not another hero CTA.

**Suggested command:** `$impeccable clarify`

## Persona Red Flags

**Jordan, first-timer:** H3, EPSG, CapEx, LIMS, ONNX, and Catalyst Watch appear without plain-language definitions. “Trace a signal” lands on a conceptual selector rather than one actual trace. Feed dots do not name the missing source.

**Riley, stress tester:** The authoritative registry and PRODUCT.md disagree on city count. Searching a displayed abbreviation such as “CA” returns no result because filtering checks only city names. Hard-coded timestamps, feed arrays, coordinates, and score values invite future drift.

**Casey, distracted mobile user:** Reaching the final CTA requires roughly 11 viewport heights. The pipeline scrolls horizontally without a cue; the city list dominates the journey; the expanded menu overlays the headline while the trigger still says “Menu.” “Trace a signal” is only about 27px high despite being a meaningful touch action.

**Technical evaluator:** The visual sophistication raises the verification bar. The repository CTA points to the root instead of cited implementations, and the unlabelled 68/100 panel does not meet the same disclosure standard as the “Illustrative cell” readout.

## Minor Observations

- DESIGN.md specifies Manrope/Georgia and blue while the implementation uses DM Sans/Newsreader and teal. The implementation is stronger, but the durable spec is stale.
- Feed availability is conveyed by color and a count; assistive technology does not receive the names of missing feeds.
- The mobile menu should change to “Close” or gain an equally explicit expanded state.
- Hero and navigation repeat “Live demo”; one should become an evidence-oriented action.
- The detector’s six kicker-above-heading findings confirm a repeated compositional habit. The pattern suits the municipal-document world, but losing one or two would strengthen hierarchy.

## Questions to Consider

- What if the final act traced one real permit all the way to a scored H3 cell?
- If “no black box theater” is the promise, why can’t a visitor open the 68/100 score and inspect its ingredients?
- Does mobile need every metro expanded, or should it ask the visitor to choose one city first?
- What would change if every technical noun carried a tiny, exact source or code citation?
