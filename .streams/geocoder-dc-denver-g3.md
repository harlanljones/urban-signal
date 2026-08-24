# Stream log — dc-denver-g3 — 2026-08-24

## Outcome

Two leaf streams (dc-g3 subagent, denver-g3 subagent) + one orchestrator
spine hold.

### US-74 DC — COMPLETED
SLA upgraded from non_spatial to geocoded-premises: needs_geocode +
geocode_context "Washington, DC" + address_street<-PREMISEADDRESS field_map
entry + server-side scope filter extra["where"]="PREMISEINDC = 'Yes'" (~24%
of watermark-window premises are out-of-state). DEEDS stays non_spatial:
zero address-like columns exist (verified over newest 300 rows + metadata);
parcel-join out of scope per D6; deed avsc lat/lng nullable so no DLQ risk.
New scheduler capability: extra["where"] flows into job_metadata as
base_where and joins every fetch WHERE (generalizes D7's exclude_guard).

Geocoder normalizer bumped to v2: unit designators remove designator+value
IN PLACE instead of truncating the tail — DC's mid-string units ("7701
GEORGIA AVE NW, STE 102, Washington, DC") were losing their city context and
missing. Hook also skips context-suffix append when the query already names
a state (US state-code guard) so genuine MD/VA premises aren't corrupted.

**G5'/G8' evidence (live, newest 500 SLA rows under the registered scope):**
events **500/500 = 100%**; resolved coordinates **481/500 = 96.2%**;
null-H3 **3.8%** <= 5%.

### US-73 Denver — COMPLETED AS DUAL DESCOPE
- Licenses (table 31): descoped per ticket rule — only date-like field is
  Expiration_Date (term-driven, not arrival-driven; ORDER BY DESC maxima are
  year-2200/8099 corruptions; all rows share one status). No watermark.
- Sales (table 60): reverted under G8' — ZERO address columns (newest 500
  verified); registration would emit 100% null-H3 events. Candidate recipe
  preserved in test constants incl. LOAD-BEARING ADR 0005 text-watermark
  declaration (RECEPTION_DATE int yyyymmdd; value 50250305 parses as year
  5025 and would blind polling without watermark_exclude). Quoted-string
  numeric comparison verified working server-side for future use.

Denver remains its 2-feed stub (permits + 311), now with pinned evidence.

### Gates
interlock 20 passed; full suite 671 passed / 3 skipped / 0 failed; ruff
clean on touched files, spine debt identical to HEAD (33=33).
