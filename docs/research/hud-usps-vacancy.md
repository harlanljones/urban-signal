# HUD USPS address-vacancy data — register / reject / defer

**Date of assessment: 2026-08-25.** US-103. This is a **restricted-access**
federal dataset, so the single largest thing this pass could not do is put a
password on the register form and see exactly what a registered user receives.
Everything below the access line is sourced from HUD's public pages (the dataset
summary page and the sublicense agreement, both fetched live today); anything
not published is marked **unverified** and you should treat the exact
eligibility / sublicense terms as *subject to confirmation with HUD* before any
engineering commitment.

## Method, and its limits

Sources probed live on 2026-08-25:

- `https://www.huduser.gov/portal/datasets/usps.html` — dataset summary,
  access summary, admin definitions, duration-vintage note, MTC (Move to
  Competitive) warning, GTM / growth-vs-decline guidance.
- `https://www.huduser.gov/portal/usps/sublicense_agreement.html` — the
  **"SUBLICENSE FOR CENSUS TRACT LEVEL INFORMATION"** agreement: eligibility,
  Stated Purpose, use restrictions, confidentiality, term, venue.
- `https://www.huduser.gov/apps/public/usps/register` — attempted; returned an
  empty/JS-driven form body. **Unverified.**
- `USPS_HUD_Address_Vacancy_Data_Dictionaries.xlsx` (linked from the summary
  page) — a binary workbook; **not parsed — unverified.**
- `2018-USPS-FAQ.pdf` — returned as raw PDF bytes; **not rendered — unverified.**

**Limits, stated plainly.** I could not confirm: (1) the exact eligibility
check a registrant is asked to pass, (2) whether a consumer/non-government
applicant is categorically refused or merely needs re-plumbing, (3) the precise
field list in the data dictionary, (4) whether the delivered file is ZCTA-level
or tract-level in practice today (the *agreement* title says Census Tract; the
*summary* page says "quarterly aggregate data" and points at **ZIP Code
Crosswalk Files** as a nearby resource — I treat tract-level as the safe read,
ZCTA as unverified), and (5) the credit-side cost (free? fee? grant). Do not
infer a specific deliverable format from these public pages alone.

## Headline verdict

**DEFER.** The data is attractive in content — the *universe* of all US
addresses, quarterly, with a residential/business split, a 90-day vacancy
definition, duration-in-category fields, and a documented construction-vs-longevity
read — but it is **access-blocked at the organizational level**, not at the data
level. HUD states the data is available **only to governmental entities and
non-profit organizations** and licensed **only** for a narrow "Stated Purpose"
(measure/forecast neighborhood change, assess neighborhood needs, measure/assess
HUD programs) with **no selling, licensing, or distributing** and **no
marketing/promotion**. Urban Signal is a public dashboard carrying
commercial investment metrics (capex, permit velocity, shift ratio); serving
this data on it for unrestricted internal/external signal purposes collides
with the no-distribution + stated-purpose carve-outs. On top of the access wall,
the data is delivered as an **aggregate** (per the agreement, ZIP+4 → Census
Tract grouping), i.e. **not point events**, so it does not fit the existing
point→H3 7-9 producer/pull model that `get_dataset` and every feed producer are
built around. It therefore can't cleanly "register" as a non-spatial or
spatial feed without a new aggregate-ingestion path and a tract/ZCTA→H3
crosswalk. **Defer**, not reject: the signal is directionally real and
complementary; it's blocked by applicant eligibility, sublicense scope, and a
granularity/architecture mismatch.

## Access assessment

- **Eligibility** (source: summary page): "HUD can make the data accessible only
  to governmental entities and non-profit organizations registered as users."
- **Sublicense terms** (source: sublicense agreement):
  - **Stated Purpose:** "measuring and forecasting neighborhood changes,
    assessing neighborhood needs, and measuring/assessing the various HUD
    programs in which User is involved, including HOME, CDBG, ADDI, and ACA."
  - **Use:** "employed anywhere within User's own organization and User's own
    facilities," and displaying to other organizations *only as necessary to
    accomplish the Stated Purpose*; explicitly **no selling, licensing, or
    distributing**, and **no marketing or promotion**.
  - **Confidentiality:** confidential and proprietary; copies must carry the
    "…confidential and proprietary property of the United States Postal
    Service…" notice; governed by **39 U.S.C. § 412**, which prohibits public
    disclosure of address lists (so the registrant must secure it against public
    or unauthorized access).
  - **Term:** one year, Oct 1 → following Sep 30; terminable for no reason;
    immediate termination on possible improper disclosure.
  - **No accuracy warranty / no fitness warranty.**
- **Request path:** register → `https://www.huduser.gov/apps/public/usps/register`,
  then login; questions to `USPSVacancydata@hud.gov`. Beyond the existence of
  that path, **unverified.**

**What an applicant must be:** a registered user at a **government entity or a
non-profit organization**, bound to the Stated Purpose, keeping the data
confidential and inside its own organization, and not reselling or redistributing
it. Urban Signal is not currently that entity.

## Data assessment

- **Cadence / lag:** quarterly ("updated every three months"). Volume/key:
  address-universe counts for the prior quarter. **Contextual, not real-time.**
- **Granularity ("address universe"):** counts reflect the universe of all
  USPS-recorded addresses. But the *delivered unit* is an **aggregate** — the
  agreement is for "Census Tract Level Information," i.e. ZIP+4 aggregated into
  census-tract groupings such that the fine level "is not discernable by any
  means." Treat tract-level as the likely unit; ZCTA-level **unverified**.
- **Residential vs business:** split is present — USPS records each address as
  residential or business; both vacancy and no-stat are reported per category.
- **Administrative definitions** (source: summary page):
  - **Total Addresses:** all recorded residential+business addresses.
  - **Total Vacant:** addresses delivery staff on **urban routes** flagged vacant
    (not collecting mail) **for 90 days or longer**.
  - **Total No-Stat:** addresses that are No-Stat for reasons including rural
    routes vacant 90+ days, **addresses under construction and not yet
    occupied**, and urban addresses a carrier flags as unlikely to be active
    for some time.
  - **Duration fields:** USPS reports the **number of days an address has been in
    each category**; counting began **November 18, 2005** (so December 2005 shows
    nothing >3 months). This is the long-duration-vacancy hook.
- **Methodology-change risk (documented):** HUD states plainly that changes in how
  USPS manages address data "have made longitudinal analysis… more challenging,"
  and flags the **Move to Competitive (MTC)** program as having caused a
  "dramatic increase in the number of addresses." HUD "strongly urges all current
  and potential users to read" the FAQ before longitudinal analysis. This is a
  documented structural break, not a hypothetical.
- **Growth / decline guidance (from HUD):** increase in AMS address count *with* a
  similar increase in no-stat → likely new construction/additions; no-stat with a
  stable or reduced address count → likely long-term vacancy; a **reduction** in
  total AMS addresses quarter-over-quarter → indicator of demolition. (A
  demolished-and-replaced building typically moves to no-stat, not off the
  ledger.) This gives a construction-vs-longevity discriminator but only after
  you hold the AMS-total series.

## Urban Signal fit

- **Point→H3 mismatch.** Every current feed is point-based: a producer pulls
  records, computes `lat/lng`, and emits `h3_res7/8/9` via
  `H3SpatialIndexer.get_multi_res_hierarchy` (`spatial/h3_indexer.py`). The
  HUD vacancy counts are **not point events** — they're pre-aggregated counts
  keyed to a census tract (or ZCTA). You cannot run a vacancy row through
  `latlng_to_h3`; there is no address geometry in the file. This is a
  categorical difference from `DatasetSpec`/`get_dataset`/`resolve_endpoint`
  (`city_registry.py` ~2458/2482), which resolve an endpoint and hand rows to a
  producer.
- **Crosswalk needed, and it's lossy.** H3 cells and census tracts/ZCTAs do not
  nest. Any assignment is areal-apportionment, and a tract can span multiple H3
  cells at res 7 (5.16 km²) / res 8 (0.74 km²) / res 9 (0.10 km²). At res 9 a
  single tract routinely covers dozens-to-hundreds of cells, so a per-cell rate
  would be near-constant and thus low-signal — the useful granularity is res 7,
  maybe res 8, via tract→H3 intersection weighting.
- **Metro / division / submarket units.** These are point/bbox-keyed
  (`METRO_BBOX`, `DIVISION_BBOXES`, `SubmarketMeta` lat/lng — see
  `new_orleans.py`, `norfolk.py`). An aggregate count can be attached to a
  division/metro only by intersecting the tract (or ZCTA) geometry with the
  bbox/point and allocating counts — again an areal join, not a lookup. Workable
  at the metro/division level, crude at the submarket level.
- **No free data; no direct feed.** This is not an open Socrata/ArcGIS endpoint
  you poll. It's a gated, confidential, licensed product. The repo's existing
  `platform="socrata|arcgis|ckan"` model has no concept of a credentialed,
  license-restricted government product. Registering it naively (a `DatasetSpec`
  pointing at a URL) would both fail (auth wall) and violate the sublicense
  (distribution of confidential data).
- **Who already covers the comparison target.** Construction growth is already
  the `FeedType.PERMITS` family and development a `DEEDS`/`STREET_CUT` family;
  business presence is `FeedType.SLA`. A vacancy/no-stat signal would test
  **against** those, not alongside them as a peer point feed.

## Two-metro pilot feasibility

A two-metro pilot is *technically* straightforward (pull two metros' worth of
tract-level counts, intersect with two metro/division bboxes, attach to res-7
cells, compare against permit velocity) but is **blocked before any data moves**:

1. **Applicant and eligibility.** Urban Signal must be (or must be represented
   by) a **registered government or non-profit user**. That is the single
   hard gate. As a repo, it isn't one; the pilot would need a host — e.g. a
   public agency, a university, or a non-profit — to hold the sublicense and
   request a two-metro slice.
2. **Purpose must be on-brief.** The stated purpose is neighborhood-change
   measurement/forecast and HUD-program assessment. Using it to feed
   commercial investment metrics on a public dashboard is *outside* that
   scope and is also explicitly barred (no distribution, no marketing). The
   pilot's stated aim should be *forecasting/measuring neighborhood change*,
   and the output kept confidential within the licensee org — not published.

**Concrete pilot plan (once eligibility is solved):** (a) confirm with HUD the
delivered unit (tract vs ZCTA) and get the data-dictionary field list; (b) pick
two metros — a post-disaster/recovery metro (New Orleans) and a market with
active infill/redevelopment (Norfolk), i.e. one high-vacancy/no-stat and one
high-construction, to exercise the construction-vs-longevity discriminator;
(c) register the two metros' tracts/ZCTAs with `H3` res-7/8 cells via areal
intersection; (d) produce vacancy rate, no-stat rate, AMS-address deltas, and a
long-duration (e.g. >6 mo / >1 yr) breakdown per division/submarket; (e) test
against existing `PERMITS` and `SLA` volume per unit — expect no-stat to track
permits in growth units and vacancy/no-stat-with-flat-AMS to track long-term
vacancy; (f) flag the **MTC** break quarter so longitudinal test windows exclude
it.

**The blocker restated:** the pilot is blocked on *who asks and for what
purpose*, not on engineering. Someone with government/non-profit standing must
request it, scoped to neighborhood-change assessment, and agree to keep the
result confidential.

## Risks and dependencies (mapped to the issue)

- **Access restricted to registered government/nonprofit + stated purpose** —
  confirmed, and the dominant risk. Urban Signal has no standing. **Dependency:
  a qualifying host entity and a purpose-scoped request.**
- **Limited to the sublicense purpose, no distribution/marketing** — confirmed
  in the agreement text. **Risk: publishing aggregated rates on the public
  dashboard is a likely violation.** Mitigation: treat as a confidential internal
  signal or get explicit HUD re-scoping; do not ship it as a public feed.
- **Quarterly cadence + administrative definitions ⇒ contextual, not real-time**
  — confirmed. Vacant=90+ days urban-route, no-stat includes under-construction
  and rural/really-long vacancy, so rates are *indicator* not *headline*.
- **Move to Competitive creates artificial longitudinal shifts** — confirmed as
  documented by HUD; must be flagged as a break and excluded from the comparison
  window. **Dependency: FAQ + break-date crosswalk.**
- **Crosswalk / version management** — required: tract/ZCTA→H3 apportionment,
  tract→division/submarket allocation, plus crosswalk-version pinning and a track
  of U.S. Census geometry releases. Material engineering effort, and a lossy one.

## Recommendation

**DEFER.** Do not register as a `FeedType`/`DatasetSpec` now. The content is
genuinely valuable (address *universe*, quarterly, 90-day + long-duration
fields, residential/business split, construction-vs-longevity read) and it is
the exact *contextual longitudinal* layer the issue describes — but it is gated
on **applicant eligibility (government/non-profit only)** and bound to a **narrow
stated purpose with no distribution/marketing**, which a public, commercially
tuned dashboard does not satisfy.

**What unblocks it:**
1. **An eligible host** — a registered government or non-profit entity willing to
   hold the sublicense and request a two-metro slice for *neighborhood-change
   forecast/assessment* (the on-brief purpose).
2. **Scope confirmation from HUD** — that the intended use (aggregating to
   res-7/metro/division units as a confidential contextual signal) is within the
   stated purpose, and clarifying the delivered unit (tract vs ZCTA) + full data
   dictionary.
3. **An aggregate-ingestion + crosswalk design** — tract/ZCTA → H3 (res 7, maybe
   8) areal apportionment — before any producer work, since the point→H3 model
   does not apply.

Re-open / merge into a real ticket (not US-103) once a host entity is identified
or HUD confirms the intended use is licensable. Until then, the vacancy and
no-stat measures are a **contextual complement to `FeedType.PERMITS`/`SLA`/`DEEDS`**,
not a new registered feed.
