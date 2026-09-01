"""National feed registry (US-363 §1.3, §1.4, §1.5).

Three of the sweep's four new components read **national** files that cover
every registered metro at once: Foursquare's POI release deltas, OpenFEMA's
NFIP claims and disaster declarations, and NREL's AFDC station list. None of
them is city-shaped, so none belongs in ``CityRegistration.datasets``:

* a city holds at most one ``DatasetSpec`` per ``FeedType``, and these feeds
  have no per-city endpoint to hold;
* registering one national feed 62 times would make 62 jobs poll the same URL;
* the interlock gate's city invariants (endpoint-per-city, job-name
  uniqueness, per-city producer keys) are meaningful for municipal feeds and
  meaningless here.

They register here instead, with their own spec shape and their own
invariants, and resolve ``city_id`` per row by point-in-metro-bbox — which is
exactly how the sweep describes them ("`city_id` by point-in-registered-metro-
bbox — all sources carry lat/lon, no geocoding").

GBFS is the deliberate exception and stays in the city registry: one GBFS
system maps one-to-one onto one metro.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from src.config import settings


class NationalFeed(str, Enum):
    """National feed families."""

    POI_CHANGE = "poi_change"
    NFIP_CLAIMS = "nfip_claims"
    DISASTER_DECLARATIONS = "disaster_declarations"
    EV_CHARGING = "ev_charging"
    SBA_LOAN = "sba_loan"
    BANK_BRANCH = "bank_branch"


@dataclass
class NationalFeedSpec:
    """Ingestion contract for one national feed."""

    feed: NationalFeed
    endpoint: str
    platform: str  # "hf_parquet" | "odata" | "rest"
    topic: str
    producer_key: str
    id_keys: List[str] = field(default_factory=list)
    watermark_col: str = ""
    ingestion_mode: str = "incremental"
    interval_seconds: float = 86400.0
    expected_cadence_days: Optional[int] = None
    auth: str = "none"  # none | bearer | api_key
    auth_env: Optional[str] = None
    state_dir: Optional[str] = None
    row_filter: Dict[str, str] = field(default_factory=dict)
    attribution: Optional[str] = None
    verified: bool = True
    notes: str = ""

    def token(self) -> Optional[str]:
        if self.auth == "none" or not self.auth_env:
            return None
        return os.environ.get(self.auth_env) or None


# Apache-2.0 obliges us to preserve Foursquare's NOTICE.txt wherever the data
# or a derivative is distributed. Carried on the spec so a surface cannot
# render POI-derived signal without the attribution travelling with it.
FSQ_ATTRIBUTION = (
    "Contains information from Foursquare OS Places, licensed under the "
    "Apache License, Version 2.0. NOTICE.txt preserved per the license."
)


NATIONAL_FEEDS: Dict[NationalFeed, NationalFeedSpec] = {
    NationalFeed.POI_CHANGE: NationalFeedSpec(
        feed=NationalFeed.POI_CHANGE,
        endpoint=settings.fsq_places_repo,
        platform="hf_parquet",
        topic=settings.topic_poi_change,
        producer_key="poi_change",
        id_keys=["fsq_place_id"],
        ingestion_mode="release_delta",
        interval_seconds=86400.0,
        expected_cadence_days=35,
        auth="bearer",
        auth_env="HF_TOKEN",
        state_dir=settings.poi_state_dir,
        attribution=FSQ_ATTRIBUTION,
        notes=(
            "SOURCE RELOCATED, verified 2026-08-28. The anonymous S3 bucket "
            "`fsq-os-places-us-east-1` the sweep recorded now holds only "
            "LICENSE.txt and NOTICE.txt — every release partition is gone. "
            "Foursquare moved the dataset to a GATED Hugging Face repo "
            "(anonymous download returns 401; access is auto-granted on "
            "request). The `release/dt=<date>/{places,deltas,categories}/"
            "parquet/` layout is unchanged: 21 releases, latest dt=2026-08-11 "
            "with 10 delta partitions. Apache-2.0 still applies."
        ),
    ),
    NationalFeed.NFIP_CLAIMS: NationalFeedSpec(
        feed=NationalFeed.NFIP_CLAIMS,
        endpoint=settings.openfema_nfip_claims_endpoint,
        platform="odata",
        topic=settings.topic_insurance_loss,
        producer_key="nfip_claims",
        id_keys=["id"],
        watermark_col="dateOfLoss",
        interval_seconds=86400.0,
        expected_cadence_days=30,
        notes=(
            "v3 verified live 2026-08-28: $inlinecount=allpages, $filter, "
            "$orderby, $select, $top/$skip all behave (NY since 2024-01-01 "
            "-> count 1,443). v2 `FimaNfipClaims` is DEPRECATED — frozen "
            "2026-06-01, removal 2026-10-15 — and must never be used. "
            "Coordinates are privacy-truncated to 0.1 degrees; H3 comes from "
            "`censusGeoid` via the tract centroid instead."
        ),
    ),
    NationalFeed.DISASTER_DECLARATIONS: NationalFeedSpec(
        feed=NationalFeed.DISASTER_DECLARATIONS,
        endpoint=settings.openfema_disaster_declarations_endpoint,
        platform="odata",
        topic=settings.topic_context_observations,
        producer_key="nfip_claims",
        id_keys=["femaDeclarationString"],
        watermark_col="declarationDate",
        interval_seconds=86400.0,
        expected_cadence_days=30,
        notes=(
            "v2 only — v3 404s (verified 2026-08-28). County-level, no loss "
            "amount and no point geometry, so it rides the existing "
            "ContextObservationEvent shape rather than earning an event type: "
            "a declaration is context around claims, not a sited event."
        ),
    ),
    NationalFeed.EV_CHARGING: NationalFeedSpec(
        feed=NationalFeed.EV_CHARGING,
        endpoint=settings.nrel_afdc_endpoint,
        platform="rest",
        topic=settings.topic_infrastructure,
        producer_key="ev_charging",
        id_keys=["id"],
        ingestion_mode="snapshot",
        interval_seconds=86400.0,
        expected_cadence_days=7,
        auth="api_key",
        auth_env="NREL_API_KEY",
        state_dir=settings.ev_charging_state_dir,
        row_filter={"fuel_type_code": "ELEC"},
        verified=False,
        notes=(
            "UNVERIFIED HOST. developer.nrel.gov and afdc.energy.gov do not "
            "resolve from this network (DNS failure 2026-08-28) — the same "
            "block the research sweep hit, so nothing about this feed has "
            "been confirmed live by anyone yet. The client is written to the "
            "documented contract and covered by fixture tests. Spot-verify "
            "developer.nrel.gov/terms/ and one live response before enabling "
            "the job; `verified=False` is what keeps it out of the scheduled "
            "set until someone does."
        ),
    ),
    NationalFeed.SBA_LOAN: NationalFeedSpec(
        feed=NationalFeed.SBA_LOAN,
        endpoint="https://data.sba.gov/dataset/7a-504-foia",
        platform="csv",
        topic=settings.topic_sba_loans,
        producer_key="sba_loan",
        id_keys=["locationid", "program"],
        ingestion_mode="full",
        interval_seconds=86400.0,
        expected_cadence_days=90,
        notes=(
            "Cumulative FOIA snapshot per program (504 + 7a). Quarterly update "
            "cadence; the filename as-of date is the watermark. Addresses are "
            "SBA-truncated to 49 chars — geocode street-first with zip+city "
            "fallback. 504 rows carry project_county for county-join downstream."
        ),
    ),
    NationalFeed.BANK_BRANCH: NationalFeedSpec(
        feed=NationalFeed.BANK_BRANCH,
        endpoint="https://api.fdic.gov/banks/locations",
        platform="rest",
        topic=settings.topic_bank_branches,
        producer_key="bank_branch",
        id_keys=["UNINUM"],
        watermark_col="RUNDATE",
        ingestion_mode="snapshot",
        interval_seconds=86400.0,
        expected_cadence_days=1,
        state_dir=settings.fdic_bankfind_state_dir,
        notes=(
            "FDIC BankFind full-service brick-and-mortar branches (SERVTYPE=11). "
            "Openings use ESTYMD; closures are detection-dated from snapshot diff. "
            "Latest-year SOD DEPSUMBR is attached as annual deposit context."
        ),
    ),
}


def get_national_feed(feed: NationalFeed) -> NationalFeedSpec:
    """Look up a national feed spec, with a readable error."""
    try:
        return NATIONAL_FEEDS[feed]
    except KeyError as exc:
        raise KeyError(
            f"national feed {feed!r} is not registered; known feeds: "
            f"{sorted(f.value for f in NATIONAL_FEEDS)}"
        ) from exc


def schedulable_feeds() -> List[NationalFeedSpec]:
    """Return verified feeds whose credentials and licensing gates are ready.

    Foursquare's commercial run also requires the documented non-commercial
    category exclusion list. Keep the feed visible in metadata, but do not
    schedule it while that list is empty; ``PoiDiffProducer`` fails closed on
    the same condition.
    """
    from src.producers.poi_diff_producer import NON_COMMERCIAL_CATEGORY_IDS

    return [
        spec
        for spec in NATIONAL_FEEDS.values()
        if spec.verified
        and (spec.auth == "none" or spec.token())
        and (
            spec.feed is not NationalFeed.POI_CHANGE
            or bool(NON_COMMERCIAL_CATEGORY_IDS)
        )
    ]
