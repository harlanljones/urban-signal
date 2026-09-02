"""Configuration module using Pydantic Settings for Urban Signal."""

import json
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Application and infrastructure configuration for Urban Signal."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment
    app_env: str = Field(default="development", description="Environment: development, staging, production")
    log_level: str = Field(default="INFO", description="Log level")
    service_name: str = Field(default="urban-signal-predictor")
    city_data_dir: str = Field(
        default=str(Path(__file__).resolve().parent / "spatial" / "cities" / "data"),
        description="Directory containing declarative city-registration definitions",
    )

    # Kafka & Strimzi Streaming
    kafka_bootstrap_servers: str = Field(
        default="localhost:9092",
        description="Kafka bootstrap broker connection string",
    )
    kafka_schema_registry_url: str = Field(
        default="http://localhost:8081",
        description="Confluent/Apicurio Schema Registry endpoint",
    )
    kafka_security_protocol: str = Field(default="PLAINTEXT")
    kafka_sasl_mechanism: str | None = None
    kafka_sasl_username: str | None = None
    kafka_sasl_password: str | None = None
    # Partition count used when a consumer pre-creates a missing topic (US-69:
    # the scaling plan targets >= 12 partitions on raw.municipal.*; a 3-partition
    # creation default was the drift that concentrated backfill load on 0/1/2).
    kafka_topic_partitions: int = Field(
        default=12,
        description="Partitions assigned to topics created by consumer auto-provisioning",
        ge=1,
    )

    # Kafka Topic Definitions
    topic_permits: str = Field(default="raw.municipal.permits")
    topic_311: str = Field(default="raw.municipal.311")
    topic_sla: str = Field(default="raw.municipal.sla")
    topic_deeds: str = Field(default="raw.municipal.deeds")
    # Signal-survey raw topics (US-72): the taxonomy members beyond the four
    # original feeds. Registered by their own tickets (US-71/81/92/93); an
    # unregistered member simply has no jobs and no topics until then.
    topic_crime: str = Field(default="raw.municipal.crime", description="Crime incident records topic")
    topic_violations: str = Field(default="raw.municipal.violations", description="Building/property code-enforcement violations topic (US-209)")
    topic_inspections: str = Field(default="raw.municipal.inspections", description="Food-establishment inspection/licensing outcomes topic (US-209)")
    topic_street_cut: str = Field(default="raw.municipal.street_cut", description="Street-cut/utility permit records topic")
    topic_evictions: str = Field(default="raw.municipal.evictions", description="Eviction filings/executions topic")
    topic_str: str = Field(default="raw.municipal.str", description="Short-term rental registrations topic")
    # US-363 context/measurement families. `context_observations` carries both
    # energy benchmarking (§2.7) and bike/ped counters (§2.8) — one typed
    # ContextObservationEvent shape, one topic, two sources.
    topic_context_observations: str = Field(
        default="raw.context.observations",
        description="Periodic per-asset context measurements (energy benchmarking, bike/ped counters)",
    )
    topic_station_change: str = Field(
        default="raw.mobility.station_change",
        description="GBFS docked-station installs/removals (US-363 §1.2)",
    )
    topic_poi_change: str = Field(
        default="raw.poi.change",
        description="POI openings/closings from release deltas (US-363 §1.3)",
    )
    topic_infrastructure: str = Field(
        default="raw.infrastructure.assets",
        description="New fixed infrastructure: ev_station | small_cell | grid_capacity (US-363 §1.5)",
    )
    topic_insurance_loss: str = Field(
        default="raw.federal.insurance_loss",
        description="Paid NFIP flood claims, distress context (US-363 §1.4)",
    )
    topic_enriched_h3: str = Field(default="enriched.spatial.h3")
    topic_catalyst_alerts: str = Field(default="alerts.catalyst")
    topic_dlq: str = Field(default="dlq.schema.failures")
    # US-375/US-376: the anchor-institution tier (NCES school churn + Head
    # Start daily service locations share one event and one topic).
    topic_anchor_institutions: str = Field(
        default="raw.anchor.institutions",
        description="AnchorInstitutionEvent topic: school|charter churn + Head Start openings",
    )
# US-378: SBA 7(a)/504 loan approvals — cumulative FOIA snapshot per program.
    topic_sba_loans: str = Field(
        default="raw.sba.loans",
        description="SBA 7(a)/504 loan approvals topic (US-378)",
    )
    # US-379: full national snapshot state prevents re-emitting every branch.
    topic_bank_branches: str = Field(
        default="raw.federal.bank_branches",
        description="FDIC BankFind branch openings/closures topic (US-379)",
    )
    fdic_bankfind_state_dir: str = Field(
        default="./data/fdic_bankfind_state",
        description="Directory holding the FDIC branch snapshot state",
    )
    # US-376: the Head Start daily service-location snapshot.
    # US-376: the Head Start daily service-location snapshot.
    head_start_locations_url: str = Field(
        default="https://s3foa.s3.us-east-1.amazonaws.com/HS_Service_Locations.csv",
        description="Head Start service locations CSV (daily refresh, pre-geocoded)",
    )
    head_start_state_dir: str = Field(
        default="./data/head_start_state",
        description="Directory holding the Head Start site snapshot for status diffing",
    )

    # Scheduler durable watermark state (US-106): JSON file holding per-job
    # high watermarks so restarts resume instead of re-paging from the start.
    scheduler_state_file: str = Field(
        default="",
        description="Optional path to the scheduler watermark state file; empty disables persistence",
    )

    # Dispatcher durable calibration state (ADR 0008 §6): JSON store backing
    # the per-city calibration gate so it survives dispatcher restarts.
    alert_state_file: str = Field(
        default="",
        description="Optional path to the alert-dispatcher calibration state file; empty uses in-memory",
    )

    # Consumer Group Configurations
    cg_h3_enrichment: str = Field(default="h3-enrich-workers")
    cg_complaints: str = Field(default="spatial-complaint-grp")
    cg_hospitality: str = Field(default="hospitality-grp")
    cg_deeds: str = Field(default="deed-financial-grp")
    cg_inference: str = Field(default="ml-inference-workers")
    cg_alerts: str = Field(default="webhook-dispatchers")

    # Aggregation consume-loop cadence (ADR 0008 §2): bounds per-cell recompute
    # (≈5 DuckDB window queries) to once per window; records touching a hot
    # cell are absorbed. Single-instance worker; per-instance store.
    aggregation_cell_cooldown_seconds: int = Field(
        default=300,
        description="Per-cell aggregation cooldown window in seconds",
    )

    # Socrata SODA OpenData APIs (NYC Defaults)
    socrata_app_token: str | None = Field(default=None, description="Socrata App Token for high rate limits")
    socrata_dob_endpoint: str = Field(default="https://data.cityofnewyork.us/resource/ipu4-2q9a.json")
    socrata_311_endpoint: str = Field(default="https://data.cityofnewyork.us/resource/erm2-nwe9.json")
    socrata_sla_endpoint: str = Field(default="https://data.ny.gov/resource/9s3h-dpkz.json")
    socrata_deeds_endpoint: str = Field(default="https://data.cityofnewyork.us/resource/bnx9-e6tj.json")

    # Socrata SODA OpenData APIs (Chicago & Cook County)
    socrata_chicago_dob_endpoint: str = Field(
        default="https://data.cityofchicago.org/resource/ydr8-5enu.json",
        description="Chicago DOB Building Permits endpoint",
    )
    socrata_chicago_311_endpoint: str = Field(
        default="https://data.cityofchicago.org/resource/v6vf-nfxy.json",
        description="Chicago 311 Service Requests endpoint",
    )
    socrata_chicago_licenses_endpoint: str = Field(
        default="https://data.cityofchicago.org/resource/r5kz-chrr.json",
        description="Chicago Business & Hospitality Licenses endpoint",
    )
    socrata_chicago_deeds_endpoint: str = Field(
        default="https://datacatalog.cookcountyil.gov/resource/wvhk-k5uv.json",
        description="Cook County Assessor Parcel Sales endpoint",
    )

    # Socrata SODA OpenData APIs (San Francisco & Bay Area)
    socrata_sf_dob_endpoint: str = Field(
        default="https://data.sfgov.org/resource/i98e-djp9.json",
        description="SF Building Permits endpoint",
    )
    socrata_sf_311_endpoint: str = Field(
        default="https://data.sfgov.org/resource/vw6y-z8j6.json",
        description="SF 311 Service Requests endpoint",
    )
    socrata_sf_licenses_endpoint: str = Field(
        default="https://data.sfgov.org/resource/g8m3-pdis.json",
        description="SF Registered Business Locations endpoint",
    )
    socrata_sf_deeds_endpoint: str = Field(
        default="https://data.sfgov.org/resource/wv5m-vpq2.json",
        description="SF Assessor Historical Secured Property endpoint",
    )

    # Seattle / Puget Sound (Socrata + WA State LCB)
    socrata_seattle_permits_endpoint: str = Field(
        default="https://data.seattle.gov/resource/76t5-zqzr.json",
        description="Seattle SDCI Building Permits endpoint (2005+)",
    )
    socrata_seattle_311_endpoint: str = Field(
        default="https://data.seattle.gov/resource/5ngg-rpne.json",
        description="Seattle Customer Service Requests (Find It Fix It) endpoint",
    )
    socrata_seattle_licenses_endpoint: str = Field(
        default="https://data.wa.gov/resource/vgcw-qfjm.json",
        description="WA State LCB Local Authority Letters - liquor license applications endpoint",
    )

    # ArcGIS Feature Services (King County)
    arcgis_kc_sales_url: str = Field(
        default=(
            "https://services.arcgis.com/Ej0PsM5Aw677QF1W/arcgis/rest/services/"
            "PARCEL_SALES3YR_AREA_287/FeatureServer/0"
        ),
        description="King County Parcel Sales Last 3 Years ArcGIS FeatureServer layer URL",
    )

    # Savannah / Chatham County (ArcGIS Server, SAGIS)
    arcgis_savannah_permits_endpoint: str = Field(
        default=(
            "https://pub.sagis.org/arcgis/rest/services/Savannah/"
            "BuildingPermit_FC/FeatureServer/1"
        ),
        description="Savannah Residential Building Permits FeatureServer layer URL",
    )
    arcgis_savannah_permits_commercial_endpoint: str = Field(
        default=(
            "https://pub.sagis.org/arcgis/rest/services/Savannah/"
            "BuildingPermit_FC/FeatureServer/0"
        ),
        description="Savannah Commercial Building Permits FeatureServer layer URL",
    )

    # Bowling Green / Warren County (city ArcGIS Server)
    arcgis_bowling_green_permits_endpoint: str = Field(
        default=(
            "https://webgis.bgky.org/server/rest/services/CCPC/"
            "CCPC_Building_Permits_2010/FeatureServer/5"
        ),
        description="Bowling Green CCPC Building Permits FeatureServer layer URL",
    )

    # Tallahassee / Leon County (joint City/County ArcGIS Server)
    arcgis_tallahassee_permits_endpoint: str = Field(
        default=(
            "https://intervector.leoncountyfl.gov/intervector/rest/services/"
            "MapServices/TLC_OverlayPermitsActive_D_WM/MapServer/0"
        ),
        description="Tallahassee TLC Active Permits MapServer layer URL",
    )
    arcgis_tallahassee_311_endpoint: str = Field(
        default=(
            "https://intervector.leoncountyfl.gov/intervector/rest/services/"
            "MapServices/LCPW_InforServiceRequest_D_WM/MapServer/1"
        ),
        description="Tallahassee Infor Service Requests MapServer layer URL",
    )
    arcgis_tallahassee_deeds_endpoint: str = Field(
        default=(
            "https://intervector.leoncountyfl.gov/intervector/rest/services/"
            "MapServices/LCPA_Last3YearsSales_D_WM/MapServer/0"
        ),
        description="Tallahassee LCPA Last 3 Years Sales MapServer layer URL",
    )

    # Spartanburg County (on-prem ArcGIS Server)
    arcgis_spartanburg_permits_url: str = Field(
        default=(
            "https://maps.spartanburgcounty.org/server/rest/services/"
            "EnerGov/EnerGov_Spatial_Collections/FeatureServer/5"
        ),
        description="Spartanburg EnerGov Permits FeatureServer layer URL",
    )
    arcgis_spartanburg_sla_url: str = Field(
        default=(
            "https://maps.spartanburgcounty.org/server/rest/services/"
            "EnerGov/EnerGov_Spatial_Collections/FeatureServer/5"
        ),
        description="Spartanburg EnerGov Business Licenses FeatureServer layer URL",
    )

    # Los Angeles (Socrata)
    socrata_la_permits_endpoint: str = Field(
        default="https://data.lacity.org/resource/pi9x-tg5x.json",
        description="LADBS Building Permits Issued from 2020 to Present endpoint",
    )
    socrata_la_311_endpoint: str = Field(
        default="https://data.lacity.org/resource/2cy6-i7zn.json",
        description="MyLA311 Service Request Cases (current year) endpoint",
    )
    socrata_la_licenses_endpoint: str = Field(
        default="https://data.lacity.org/resource/6rrh-rzua.json",
        description="LA Office of Finance Listing of Active Businesses endpoint",
    )

    # Crime incident feeds (US-71): NIBRS-classified incident rows per metro.
    # LA stays out (mid-NIBRS-transition series break). NYC's YTD dataset
    # publishes monthly (G11 cadence declaration in the registry spec).
    socrata_nyc_crime_endpoint: str = Field(
        default="https://data.cityofnewyork.us/resource/5uac-w243.json",
        description="NYC crime current-year YTD incidents endpoint",
    )
    # NYC Marshal's executed evictions (US-93): context/validation only, never
    # a LIMS input (single-metro asymmetry rule). Carries lat/lon directly.
    socrata_nyc_evictions_endpoint: str = Field(
        default="https://data.cityofnewyork.us/resource/6z8x-wfk4.json",
        description="NYC Marshal's executed evictions endpoint",
    )
    # NYC DOHMH Restaurant Inspections (US-208): food-safety/public-health,
    # native lat/lng + point, `camis` stable PK, `inspection_date` calendar
    # watermark. Probed live 2026-08-30 (n≈296K, fresh 2026-08-27).
    socrata_nyc_inspections_endpoint: str = Field(
        default="https://data.cityofnewyork.us/resource/43nn-pn8j.json",
        description="NYC DOHMH Restaurant Inspection Results endpoint",
    )
    socrata_chicago_crime_endpoint: str = Field(
        default="https://data.cityofchicago.org/resource/ijzp-q8t2.json",
        description="Chicago crime incidents endpoint",
    )
    socrata_sf_crime_endpoint: str = Field(
        default="https://data.sfgov.org/resource/wg3w-h783.json",
        description="SF crime incident reports endpoint",
    )
    socrata_seattle_crime_endpoint: str = Field(
        default="https://data.seattle.gov/resource/tazs-3rd5.json",
        description="Seattle SPD crime data endpoint",
    )

    # Street-cut / utility permit feeds (US-81): disruption context signal.
    # Chicago CDOT street closures (jdis-5sry, native coordinates) is the
    # registered feed; the CDOT permit master (pubx-yq2d) rides along as an
    # unpolled companion until companion polling lands (US-196: 2026-08-27 G5
    # staging probe — 98.5% of address-bearing rows recovered). NYC's DOT
    # street-construction permits (tqtj-sjs8) stay unregistered: the 2026-08-27
    # G5 staging probe of the newest 500 rows recovered only 78.0% of
    # coordinates (house-number rows 60.1%, intersection rows 89.2%) — below
    # the 95% address-geocode floor for both the full spec and the
    # house-number-filtered fallback.
    socrata_chicago_street_cut_endpoint: str = Field(
        default="https://data.cityofchicago.org/resource/jdis-5sry.json",
        description="Chicago CDOT street closures endpoint",
    )
    socrata_chicago_cdot_permits_endpoint: str = Field(
        default="https://data.cityofchicago.org/resource/pubx-yq2d.json",
        description="Chicago CDOT permit master (street-cut companion; unpolled until companion polling lands)",
    )

    # --- US-363 §1.2 GBFS docked bikeshare (snapshot diff) ---
    # Auto-discovery roots. Every one verified 200 live 2026-08-28; Citi Bike
    # (bkn) publishes GBFS 2.3 with ttl=60 and 2,508 stations whose
    # station_information and station_status id spaces match exactly (98 of
    # them pre-activation, is_installed=0).
    #
    # LICENSE GATE. Only the Lyft-operated pool is registered. Lyft's Data
    # License Agreement grants product use while prohibiting re-hosting the
    # raw feed as a standalone dataset, which is what we do — we derive
    # events and keep a state store, never republish the feed.
    # Lime/Bird/Spin/Bolt/Veo are BARRED (internal-non-commercial-only,
    # 10-minute retention, no-database-augmentation clauses) and must not be
    # added here without new written terms.
    gbfs_nyc_discovery_endpoint: str = Field(
        default="https://gbfs.lyft.com/gbfs/2.3/bkn/gbfs.json",
        description="Citi Bike (Lyft) GBFS 2.3 auto-discovery root",
    )
    gbfs_chicago_discovery_endpoint: str = Field(
        default="https://gbfs.lyft.com/gbfs/2.3/chi/gbfs.json",
        description="Divvy (Lyft) GBFS 2.3 auto-discovery root",
    )
    gbfs_san_francisco_discovery_endpoint: str = Field(
        default="https://gbfs.lyft.com/gbfs/2.3/bay/gbfs.json",
        description="Bay Wheels (Lyft) GBFS 2.3 auto-discovery root",
    )
    # NOT `gbfs.lyft.com/gbfs/2.3/dca/` — that slug is a live-but-empty stub
    # (HTTP 200, fresh last_updated, `"stations": []`, verified 2026-08-28).
    # The real Capital Bikeshare system is `dca-cabi` on GBFS **1.1** with 866
    # stations, reached through the operator's own discovery root. Registering
    # the stub would have seeded an empty state store and then emitted 866
    # spurious installs the first time a populated feed was polled.
    gbfs_washington_dc_discovery_endpoint: str = Field(
        default="https://gbfs.capitalbikeshare.com/gbfs/gbfs.json",
        description="Capital Bikeshare (Lyft, system dca-cabi) GBFS 1.1 auto-discovery root",
    )
    gbfs_state_dir: str = Field(
        default="./data/gbfs_state",
        description="Directory holding the per-system station state store (US-363 §1.2)",
    )

    # --- US-363 §1.3 POI release deltas (Foursquare OS Places) ---
    # RELOCATED SOURCE, verified 2026-08-28: the anonymous S3 bucket
    # `fsq-os-places-us-east-1` now contains only LICENSE.txt and NOTICE.txt —
    # the release partitions are gone. FSQ moved the dataset to a GATED
    # Hugging Face repo (anonymous download returns 401). The
    # `release/dt=<date>/{places,deltas,categories}/parquet/` layout is
    # preserved; 21 releases exist, latest dt=2026-08-11 with 10 delta
    # partitions. Apache-2.0 still applies, and NOTICE.txt attribution must be
    # preserved wherever the data or its derivatives are distributed.
    fsq_places_repo: str = Field(
        default="foursquare/fsq-os-places",
        description="Hugging Face dataset repo for FSQ OS Places (gated; needs HF_TOKEN)",
    )
    fsq_places_api_base: str = Field(
        default="https://huggingface.co",
        description="Hugging Face API/resolve host for the FSQ release listing and partitions",
    )
    poi_state_dir: str = Field(
        default="./data/poi_state",
        description="Directory holding the last-processed POI release marker (US-363 §1.3)",
    )

    # --- US-363 §1.4 OpenFEMA ---
    # NfipClaims v3 verified live 2026-08-28 (HTTP 200). v2 `FimaNfipClaims` is
    # deprecated — frozen 2026-06-01, removal 2026-10-15 — and must not be
    # used. DisasterDeclarationsSummaries remains v2-only (v3 404s).
    openfema_nfip_claims_endpoint: str = Field(
        default="https://www.fema.gov/api/open/v3/NfipClaims",
        description="OpenFEMA NFIP claims v3 (OData). Coordinates are 0.1-degree truncated.",
    )
    openfema_disaster_declarations_endpoint: str = Field(
        default="https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries",
        description="OpenFEMA disaster declarations (v2 only; v3 404s as of 2026-08-28)",
    )

    # --- US-363 §1.5 NREL AFDC EV charging ---
    # UNVERIFIED HOST. developer.nrel.gov and afdc.energy.gov do not resolve
    # from this network (DNS failure, 2026-08-28) — the same block the
    # research sweep hit. The client is built to the documented contract and
    # exercised against fixtures; spot-verify developer.nrel.gov/terms/ and
    # one live page before enabling the job.
    nrel_afdc_endpoint: str = Field(
        default="https://developer.nrel.gov/api/alt-fuel-stations/v1.json",
        description="NREL AFDC alternative-fuel stations (needs NREL_API_KEY)",
    )
    # US-371: the key itself lives in the environment (NREL_API_KEY); this
    # optional setting makes `NrelAfdcClient()` constructible without an
    # AttributeError and keeps the scheduler free of hardcoded sentinels.
    nrel_api_key: str = Field(
        default="",
        description="NREL developer API key for the AFDC alt-fuel-stations feed (free key)",
    )
    ev_charging_state_dir: str = Field(
        default="./data/ev_charging_state",
        description="Directory holding the AFDC station snapshot for diffing (US-363 §1.5)",
    )

    # --- US-363 §2.7 building energy benchmarking (annual, zero new machinery) ---
    # All three re-probed live 2026-08-28. Coordinates are native on every
    # feed, so `needs_geocode` stays false; Chicago lags a reporting year.
    socrata_nyc_energy_benchmark_endpoint: str = Field(
        default="https://data.cityofnewyork.us/resource/5zyy-y8am.json",
        description="NYC LL84 energy & water benchmarking disclosure (max report_year 2024, n=103,259)",
    )
    socrata_chicago_energy_benchmark_endpoint: str = Field(
        default="https://data.cityofchicago.org/resource/xq83-jr8c.json",
        description="Chicago energy benchmarking (max data_year 2023 — the feed lags, n=28,329)",
    )
    socrata_seattle_energy_benchmark_endpoint: str = Field(
        default="https://data.seattle.gov/resource/teqw-tu6e.json",
        description="Seattle building energy benchmarking (max datayear 2024, n=34,699)",
    )
    # --- US-363 §2.8 bike/ped counters (daily rollup, zero new machinery) ---
    # NYC counts carry no geometry: `6up2-gnw8` is the sensor registry the
    # spec declares as a companion endpoint. Seattle's Fremont feed is one
    # fixed structure with no registry at all.
    socrata_nyc_bike_ped_counts_endpoint: str = Field(
        default="https://data.cityofnewyork.us/resource/ct66-47at.json",
        description="NYC DOT bike/ped/scooter counts, 15-minute directional (21.0M rows, same-day fresh)",
    )
    socrata_nyc_bike_ped_sensors_endpoint: str = Field(
        default="https://data.cityofnewyork.us/resource/6up2-gnw8.json",
        description="NYC DOT counter registry — lat/lon for ct66-47at sensor_id (67 sensors live)",
    )
    socrata_seattle_bike_ped_counts_endpoint: str = Field(
        default="https://data.seattle.gov/resource/65db-xm6k.json",
        description="Seattle Fremont Bridge hourly bike counts (~4-week lag, n=121,211)",
    )
    # San Diego (US-91): static-CSV open-data portal (seshat.datasd.org) — no
    # Socrata/ArcGIS API. Year-scoped approvals file; rotate per year (D3).
    csv_san_diego_permits_endpoint: str = Field(
        default="https://seshat.datasd.org/development_permits/approvals_issued_2026_datasd.csv",
        description="San Diego Development Services issued approvals (2026) CSV endpoint",
    )

    # San Diego Get It Done 311 (US-124): static-CSV portal. Year-scoped closed
    # file (rolls `_2027_` per year); the open queue (`companion_endpoints`) is
    # regenerated daily and holds the freshest still-open cases. Native lat/lng.
    csv_san_diego_311_endpoint: str = Field(
        default="https://seshat.datasd.org/get_it_done_reports/get_it_done_requests_closed_2026_datasd.csv",
        description="San Diego Get It Done 311 closed-requests (2026) CSV endpoint",
    )

    # San Diego Business Tax Certificates (US-125): static-CSV portal. Active
    # business-registry SNAPSHOT — re-pulled fully each poll and deduped on
    # account_key; judge freshness by file refresh, not per-row dates (the
    # cert effective/expiration dates are future-dated by design). Native
    # lat/lng; account_key arrives as a float-string that the producer
    # normalizes to integer digits.
    csv_san_diego_licenses_endpoint: str = Field(
        default="https://seshat.datasd.org/business_tax_certificates/sd_businesses_active_datasd.csv",
        description="San Diego Business Tax Certificates active-business CSV endpoint",
    )

    # Cincinnati (US-126): Hamilton County Auditor property-transfers CSV —
    # static-file download (no REST API), current-month sales published daily.
    # SaleDate is synthesized from the three int columns (MonthSale/DaySale/
    # YearSale), so the feed is a snapshot window re-pulled each poll and
    # deduped on ConveyanceNumber+PropertyNumber rather than filtered
    # incrementally; non-arm's-length rows are dropped via the Valid flag.
    csv_cincinnati_deeds_endpoint: str = Field(
        default="https://www.hamiltoncountyauditor.org/download/transfer_dailysales_new.csv",
        description="Hamilton County (Cincinnati) Auditor daily property-transfers CSV endpoint",
    )

    # Chattanooga (US-155): the Hub download proxy is the preferred endpoint,
    # while the ArcGIS item-data route is the verified fallback when the proxy
    # returns HTTP 500. The feed is a daily-refreshed flat CSV.
    csv_chattanooga_permits_endpoint: str = Field(
        default="https://data.chattanooga.gov/api/download/v1/items/9937e99e93de467eae5f592061c2672c/csv?layers=0",
        description="Chattanooga All Permits ArcGIS Hub CSV item endpoint",
    )
    csv_chattanooga_permits_fallback_endpoint: str = Field(
        default="https://www.arcgis.com/sharing/rest/content/items/9937e99e93de467eae5f592061c2672c/data",
        description="Chattanooga All Permits ArcGIS item-data fallback endpoint",
    )

    arcgis_chattanooga_deeds_url: str = Field(
        default=(
            "https://pwgis.chattanooga.gov/arcgis/rest/services/Misc/Parcels/"
            "FeatureServer/0"
        ),
        description="Chattanooga Hamilton County parcels FeatureServer layer URL",
    )

    # New Orleans (Socrata)
    socrata_nola_permits_endpoint: str = Field(
        default="https://data.nola.gov/resource/rcm3-fn58.json",
        description="NOLA Building Permits (2012-present, supersedes nbcf-m6c2) endpoint",
    )
    socrata_nola_311_endpoint: str = Field(
        default="https://data.nola.gov/resource/2jgv-pqrq.json",
        description="NOLA 311 OPCD Calls endpoint",
    )
    socrata_nola_licenses_endpoint: str = Field(
        default="https://data.nola.gov/resource/hjcd-grvu.json",
        description="NOLA Occupational Business Licenses endpoint",
    )
    socrata_nola_deeds_endpoint: str = Field(
        default="https://data.nola.gov/resource/hpm5-48nj.json",
        description="NORA Sold Properties (redevelopment disposals, not market deeds) endpoint",
    )

    # Norfolk (Socrata)
    socrata_norfolk_permits_endpoint: str = Field(
        default="https://data.norfolk.gov/resource/fahm-yuh4.json",
        description="Norfolk Permits endpoint",
    )
    socrata_norfolk_deeds_endpoint: str = Field(
        default="https://data.norfolk.gov/resource/qva7-tzrf.json",
        description="Norfolk Property Assessment and Sales FY27 endpoint (rotate ID each July)",
    )
    socrata_norfolk_311_endpoint: str = Field(
        default="https://data.norfolk.gov/resource/nbyu-xjez.json",
        description="MyNorfolk 311 service requests (address-string located, ADR 0004 geocoded)",
    )
    socrata_norfolk_licenses_endpoint: str = Field(
        default="https://data.norfolk.gov/resource/dpi6-sct5.json",
        description="Norfolk Business Licenses endpoint (native lat/lng; placeholder-address rows excluded via extra where)",
    )

    # Austin (Socrata) — permits + 311 native; US-136 adds TABC liquor-license
    # SLA (address-only, geocoded per ADR-0004). DEEDS absent (Travis County
    # Socrata portal is unreachable).
    socrata_austin_permits_endpoint: str = Field(
        default="https://data.austintexas.gov/resource/quv8-5ckq.json",
        description="Austin Issued Building Permits endpoint",
    )
    socrata_austin_311_endpoint: str = Field(
        default="https://data.austintexas.gov/resource/xwdj-i9he.json",
        description="Austin 311 Public Data endpoint",
    )
    # US-136: TABC statewide liquor-license feed (data.texas.gov 7hf9-qc9f).
    # Address-only (no geocodes) — geocoded at parse time per ADR-0004.
    socrata_austin_tabc_endpoint: str = Field(
        default="https://data.texas.gov/resource/7hf9-qc9f.json",
        description="Austin/TABC liquor license SLA endpoint (US-136)",
    )
    # US-372 state license registries. The $select composes a namespaced
    # license_type (license_type_ns) so the several registries sharing
    # topic_sla stay distinguishable downstream; httpx merges the client's
    # pagination params with the URL's $select (leaf-verified through
    # SocrataClient.paginate — see field_maps_state_licenses.py).
    socrata_tabc_active_endpoint: str = Field(
        default=(
            "https://data.texas.gov/resource/7hf9-qc9f.json"
            "?$select=*, 'tabc:' || license_type as license_type_ns"
        ),
        description="TABC active liquor licenses, namespaced license_type (US-372)",
    )
    socrata_co_liquor_endpoint: str = Field(
        default=(
            "https://data.colorado.gov/resource/ier5-5ms2.json"
            "?$select=*, 'co_liquor:' || license_type as license_type_ns"
        ),
        description="CO liquor licenses (geocoded points), namespaced license_type (US-372)",
    )
    socrata_or_ccb_endpoint: str = Field(
        default=(
            "https://data.oregon.gov/resource/g77e-6bhs.json"
            "?$select=*, 'or_ccb:' || license_type as license_type_ns"
        ),
        description="OR CCB active contractor licenses, namespaced license_type (US-372)",
    )
    # US-71: APD NIBRS Group A Offenses (Socrata `thrk-bqb6`). Rows carry no
    # lat/lng — only zip_code + census_block_group — so coordinates resolve from
    # the zip_code context via the ADR-0004 geocoder at parse time.
    socrata_austin_crime_endpoint: str = Field(
        default="https://data.austintexas.gov/resource/thrk-bqb6.json",
        description="Austin APD NIBRS Group A Offenses Socrata endpoint (US-71)",
    )
    # US-210: Austin Code Complaint Cases (Socrata `6wtj-zbtb`, the underlying
    # dataset behind the `3g2y-5uvh` story asset). Native lat/lng + point,
    # stable case_id PK, opened_date watermark. Probed live 2026-08-30
    # (n=82,854). VIOLATIONS-family code enforcement, distinct from 311.
    socrata_austin_violations_endpoint: str = Field(
        default="https://data.austintexas.gov/resource/6wtj-zbtb.json",
        description="Austin Code Complaint Cases endpoint (US-210)",
    )

    # Cincinnati (Socrata) — PERMITS, 311, and business licenses; no sales
    # feed was found in the verified Socrata catalog sweep.
    socrata_cincinnati_permits_endpoint: str = Field(
        default="https://data.cincinnati-oh.gov/resource/uhjb-xac9.json",
        description="Cincinnati issued permits endpoint",
    )
    socrata_cincinnati_311_endpoint: str = Field(
        default="https://data.cincinnati-oh.gov/resource/gcej-gmiw.json",
        description="Cincinnati 311 service requests endpoint",
    )
    socrata_cincinnati_licenses_endpoint: str = Field(
        default="https://data.cincinnati-oh.gov/resource/ehdi-ajku.json",
        description="Cincinnati business licenses endpoint",
    )

    # Pittsburgh, PA (CKAN): WPRDC PLI permits. Native lat/lng + issue_date
    # watermark (US-89). 311 archive / licensed businesses are address-only or
    # ungeocodable and stay unregistered.
    ckan_pittsburgh_permits_endpoint: str = Field(
        default="ckan://data.wprdc.org/f4d1177a-f597-4c32-8cbf-7885f56253f6",
        description="WPRDC PLI Permits datastore resource (City of Pittsburgh)",
    )

    # Pittsburgh deeds (US-129): WPRDC "Allegheny County Property Sale
    # Transactions" (package real-estate-sales, datastore-active, SQL enabled).
    # Schema is all-uppercase (PARID/DEEDBOOK/PRICE/RECORDDATE/SALEDATE), so the
    # CKAN SQL endpoint needs quoted identifiers. Address-only / PARID-only (no
    # lat/lng) — the deeds producer tolerates null coordinates (Cook County
    # wvhk-k5uv precedent). watermark_col is RECORDDATE (record-the-deed date,
    # with SALEDATE trailing by pub/recording lag).
    ckan_pittsburgh_deeds_endpoint: str = Field(
        default="ckan://data.wprdc.org/5bbe6c55-bce6-4edb-9d04-68edeb6bf7b1",
        description="WPRDC Allegheny County property-sales datastore resource",
    )

    # Pittsburgh 311 (US-132): WPRDC "Pittsburgh 311 Data" resource (the city's
    # post-transition replay of 311 requests, datastore-active). Native
    # lat/lng as TEXT (5-dec EXACT or 2-dec APPROXIMATE — the producer casts to
    # float); `created_date_utc` watermark; ~99.8% geocoded in the newest window.
    # The old `311-data` archive is a separate frozen package (newest 2025-03-10)
    # and the source of the obsolete "address-only archive" verdict.
    ckan_pittsburgh_311_endpoint: str = Field(
        default="ckan://data.wprdc.org/5202679a-d243-402e-b82a-63189995a942",
        description="WPRDC Pittsburgh 311 Data datastore resource",
    )

    # Boston (CKAN) — permits, current-year 311, and licensing board
    ckan_boston_permits_endpoint: str = Field(
        default="ckan://data.boston.gov/6ddcd912-32a0-43df-9908-63574f8c7e77",
        description="Boston approved building permits CKAN resource",
    )
    ckan_boston_311_endpoint: str = Field(
        default="ckan://data.boston.gov/1a0b420d-99f1-4887-9851-990b2a5a6e17",
        description="Boston 311 current-year CKAN resource",
    )
    ckan_boston_311_2025_endpoint: str = Field(
        default="ckan://data.boston.gov/9d7c2214-4709-478a-a2e8-fb2020a5bb94",
        description="Boston 311 2025 CKAN resource",
    )
    ckan_boston_licenses_endpoint: str = Field(
        default="ckan://data.boston.gov/04dc653b-1789-4374-9669-b07df7233344",
        description=(
            "Boston Licensing Board licenses CKAN resource "
            "(gpsx/gpsy State Plane coordinates transformed via EPSG:2249)"
        ),
    )
    # US-: Boston Crime Incident Reports (CKAN 6220d948-... odata v4). Source
    # carries Lat/Long directly, so no geocode step required. Mirrors the other
    # Boston CKAN feeds' `ckan://` scheme.
    ckan_boston_crime_endpoint: str = Field(
        default="ckan://data.boston.gov/6220d948-eae2-4e4b-8723-2dc8e67722a3",
        description="Boston Crime Incident Reports CKAN resource",
    )
    # US-209: Boston Property Assessment FY2026 (DEEDS proxy; snapshot). The registry
    # wires this as a snapshot-mode DEEDS feed so the model has a price-bearing proxy
    # where Boston lacks an open recorded-deeds endpoint.
    ckan_boston_property_assessment_endpoint: str = Field(
        default="ckan://data.boston.gov/e02c44d2-3c64-459c-8fe2-e1ce5f38a035",
        description="Boston Property Assessment FY2026 CKAN resource (DEEDS proxy; snapshot)",
    )
    # US-209: Boston Building & Property Violations (ISD code enforcement). Direct
    # lat/long columns; status_dttm watermark; case_no id.
    ckan_boston_violations_endpoint: str = Field(
        default="ckan://data.boston.gov/705244a6-70a6-4ff8-ab8e-56441aff18e7",
        description="Boston Building and Property Violations CKAN resource (US-209)",
    )
    # US-209: Boston Food Establishment Inspections. `location` is a "(lat, lng)"
    # string tuple; licenseno id; resultdttm / status_date watermark.
    ckan_boston_inspections_endpoint: str = Field(
        default="ckan://data.boston.gov/03693648-2c62-4a2c-a4ec-48de2ee14e18",
        description="Boston Food Establishment Inspections CKAN resource (US-209)",
    )

    # Baton Rouge / East Baton Rouge Parish (Socrata).
    socrata_baton_rouge_permits_endpoint: str = Field(
        default="https://data.brla.gov/resource/7fq7-8j7r.json",
        description="EBR Building Permits endpoint",
    )
    socrata_baton_rouge_311_endpoint: str = Field(
        default="https://data.brla.gov/resource/7ixm-mnvx.json",
        description="Baton Rouge 311 Citizen Requests endpoint",
    )
    socrata_baton_rouge_licenses_endpoint: str = Field(
        default="https://data.brla.gov/resource/xw6s-bcqm.json",
        description="EBR Businesses Registered snapshot endpoint",
    )

    # Montgomery County, MD (Socrata): point-geocoded permit families and ABS liquor licenses
    socrata_montgomery_permits_endpoint: str = Field(
        default="https://data.montgomerycountymd.gov/resource/m88u-pqki.json",
        description="Montgomery County residential permits endpoint",
    )
    socrata_montgomery_licenses_endpoint: str = Field(
        default="https://data.montgomerycountymd.gov/resource/c6rw-fazn.json",
        description="Montgomery County ABS liquor licensee endpoint",
    )
    # Montgomery County MD SDAT real-property deeds (US-128): per-parcel
    # assessment snapshot on `opendata.maryland.gov`; point-geocoded
    # (mappable_latitude_and_longitude WKT POINT + native MDP WGS84 numbers);
    # monthly snapshot.
    socrata_montgomery_deeds_endpoint: str = Field(
        default="https://opendata.maryland.gov/resource/kb22-is2w.json",
        description="Montgomery County MD SDAT real-property deeds snapshot endpoint",
    )

    # Denver (ArcGIS Hub): construction permits and ODC 311 only. Licenses
    # have no issue date and sales are ungeocoded, so both remain excluded.
    arcgis_denver_permits_url: str = Field(
        default=(
            "https://services1.arcgis.com/zdB7qR0BtYrg0Xpl/arcgis/rest/services/"
            "ODC_DEV_RESIDENTIALCONSTPERMIT_P/FeatureServer/316"
        ),
        description="Denver residential construction permits FeatureServer layer",
    )
    arcgis_denver_311_url: str = Field(
        default=(
            "https://services1.arcgis.com/zdB7qR0BtYrg0Xpl/arcgis/rest/services/"
            "ODC_service_requests_311/FeatureServer/66"
        ),
        description="Denver ODC 311 service requests FeatureServer table",
    )

    # Baltimore (ArcGIS): permits, current-year 311, and narrow liquor
    # licenses. The 311 service rotates to a new current-year layer annually.
    arcgis_baltimore_permits_url: str = Field(
        default="https://egisdata.baltimorecity.gov/egis/rest/services/Housing/DHCD_Open_Baltimore_Datasets/FeatureServer/3",
        description="Baltimore housing and building permits FeatureServer layer",
    )
    arcgis_baltimore_311_url: str = Field(
        default="https://services1.arcgis.com/UWYHeuuJISiGmgXx/ArcGIS/rest/services/311_Customer_Service_Requests_current/FeatureServer/0",
        description="Baltimore current-year 311 service requests FeatureServer layer",
    )
    arcgis_baltimore_311_2025_url: str = Field(
        default="https://services1.arcgis.com/UWYHeuuJISiGmgXx/ArcGIS/rest/services/311_Customer_Service_Requests_2025/FeatureServer/0",
        description="Baltimore 2025 311 service requests FeatureServer layer",
    )
    arcgis_baltimore_licenses_url: str = Field(
        default="https://opendata.baltimorecity.gov/egis/rest/services/NonSpatialTables/Licenses/FeatureServer/0",
        description="Baltimore liquor licenses FeatureServer table",
    )
    # Baltimore MD SDAT real-property deeds (US-128): per-parcel assessment
    # snapshot on `opendata.maryland.gov` (NOT federated under data.maryland.gov).
    # Point-geocoded via mappable_latitude_and_longitude (WKT POINT) plus native
    # mdp_latitude/_longitude MDP WGS84 numbers; monthly snapshot.
    socrata_baltimore_deeds_endpoint: str = Field(
        default="https://opendata.maryland.gov/resource/3x3p-xk2v.json",
        description="Baltimore City MD SDAT real-property deeds snapshot endpoint",
    )

    # Minneapolis (ArcGIS Hub "OpenDataMPLS"): construction/CCS permits and
    # year-sliced 311 (one Public_311_<year> layer per year; endpoint_by_year
    # in the registry resolves the current year and the annual rollover drill
    # guards New Year). Both layers are point-geocoded (outSR=4326).
    arcgis_minneapolis_permits_url: str = Field(
        default=(
            "https://services.arcgis.com/afSMGVsC7QlRK1kZ/arcgis/rest/services/"
            "CCS_Permits/FeatureServer/0"
        ),
        description="Minneapolis CCS permits FeatureServer layer URL",
    )
    arcgis_minneapolis_311_url: str = Field(
        default=(
            "https://services.arcgis.com/afSMGVsC7QlRK1kZ/arcgis/rest/services/"
            "Public_311_2026/FeatureServer/0"
        ),
        description="Minneapolis current-year Public 311 FeatureServer layer URL",
    )
    arcgis_minneapolis_licenses_url: str = Field(
        default=(
            "https://services.arcgis.com/afSMGVsC7QlRK1kZ/arcgis/rest/services/"
            "On_Sale_Liquor/FeatureServer/0"
        ),
        description="Minneapolis On-Sale liquor licenses FeatureServer layer URL (companion Off_Sale registered as companion_endpoints)",
    )

    # Peoria, IL (US-260). The deeds feed is on **Peoria County's** own ArcGIS
    # server, not the city's — the ArcGIS Hub domain named in the ticket
    # (peoria.opendata.arcgis.com) does not exist. Residential sales are
    # year-sliced MapServer layers under one service; `endpoint_by_year` in the
    # registry resolves the current year and the US-70 rollover drill guards New
    # Year. Point geometry in Web Mercator, lifted to WGS84 via outSR=4326.
    arcgis_peoria_deeds_url: str = Field(
        default=(
            "https://gis.peoriacounty.gov/arcgis/rest/services/DP/"
            "ResidentialSales/MapServer/5"
        ),
        description="Peoria County current-year residential sales MapServer layer URL",
    )

    # Detroit (ArcGIS FeatureServer — services2 host, camelCase ObjectId)
    arcgis_detroit_permits_url: str = Field(
        default=(
            "https://services2.arcgis.com/qvkbeam7Wirps6zC/arcgis/rest/services/"
            "bseed_building_permits/FeatureServer/0"
        ),
        description="Detroit BSEED Building Permits FeatureServer layer URL",
    )
    arcgis_detroit_311_url: str = Field(
        default=(
            "https://services2.arcgis.com/qvkbeam7Wirps6zC/arcgis/rest/services/"
            "improve_detroit/FeatureServer/0"
        ),
        description="Detroit Improve Detroit Issues FeatureServer layer URL",
    )
    arcgis_detroit_licenses_url: str = Field(
        default=(
            "https://services2.arcgis.com/qvkbeam7Wirps6zC/arcgis/rest/services/"
            "bseed_active_business_licenses/FeatureServer/0"
        ),
        description="Detroit BSEED Active Business Licenses FeatureServer layer URL",
    )
    arcgis_detroit_sales_url: str = Field(
        default=(
            "https://services2.arcgis.com/qvkbeam7Wirps6zC/arcgis/rest/services/"
            "assessor_property_sales_view/FeatureServer/0"
        ),
        description="Detroit Assessor Property Sales FeatureServer layer URL",
    )

    # Philadelphia (CARTO SQL API — opaque client-parsed URIs)
    carto_phl_permits_endpoint: str = Field(
        default="carto://phl.carto.com/permits",
        description="Philadelphia Building Permits CARTO table",
    )
    carto_phl_311_endpoint: str = Field(
        default="carto://phl.carto.com/public_cases_fc",
        description="Philadelphia 311 Public Cases CARTO table",
    )
    carto_phl_licenses_endpoint: str = Field(
        default="carto://phl.carto.com/business_licenses",
        description="Philadelphia Business Licenses CARTO table",
    )
    carto_phl_deeds_endpoint: str = Field(
        default="carto://phl.carto.com/rtt_summary",
        description="Philadelphia Real Estate Transfer Tax summary CARTO table",
    )

    # Washington DC (ArcGIS FeatureServers — year-sliced layers resolved via
    # endpoint_by_year in the registry; defaults below are current-year)
    arcgis_dc_permits_url: str = Field(
        default="https://maps2.dcgis.dc.gov/dcgis/rest/services/FEEDS/DCRA/FeatureServer/18",
        description="DC Building Permits (2026) FeatureServer layer URL",
    )
    arcgis_dc_311_url: str = Field(
        default=(
            "https://maps2.dcgis.dc.gov/dcgis/rest/services/"
            "DCGIS_DATA/ServiceRequests/FeatureServer/21"
        ),
        description="DC 311 City Service Requests (2026) FeatureServer layer URL",
    )
    arcgis_dc_licenses_url: str = Field(
        default="https://maps2.dcgis.dc.gov/dcgis/rest/services/FEEDS/DCRA/FeatureServer/0",
        description="DC Basic Business Licenses FeatureServer layer URL",
    )
    arcgis_dc_sales_url: str = Field(
        default=(
            "https://maps2.dcgis.dc.gov/dcgis/rest/services/"
            "DCGIS_DATA/Property_and_Land_WebMercator/FeatureServer/57"
        ),
        description="DC Tax System Property Sales CAMA FeatureServer layer URL",
    )

    # Prince George's County, MD (Socrata): 311 service requests. The
    # qzrv-2tnv parcel table stays unregistered pending producer geometry
    # hardening (HJ-125 finding — MultiPolygon shapes crash deed parsing).
    socrata_prince_georges_311_endpoint: str = Field(
        default="https://data.princegeorgescountymd.gov/resource/2ywx-ipcd.json",
        description="Prince George's County 311 service requests endpoint",
    )
    # Prince George's MD SDAT real-property deeds (US-128): per-parcel
    # assessment snapshot on `opendata.maryland.gov`; point-geocoded. This
    # sidesteps the held qzrv-2tnv parcel table (MultiPolygon geometry crash)
    # entirely — the SDAT dataset is Point-geocoded and parses cleanly.
    # monthly snapshot.
    socrata_pg_deeds_endpoint: str = Field(
        default="https://opendata.maryland.gov/resource/w3eb-4mzd.json",
        description="Prince George's County MD SDAT real-property deeds snapshot endpoint",
    )

    # Columbus, OH (ArcGIS): Accela-derived building permits (uppercase schema).
    arcgis_columbus_permits_url: str = Field(
        default=(
            "https://services1.arcgis.com/9yy6msODkIBzkUXU/arcgis/rest/services/"
            "Building_Permits/FeatureServer/0"
        ),
        description="Columbus Building Permits FeatureServer layer URL",
    )

    # Madison, WI (US-356): public Accela permitting surface.
    accela_madison_permits_endpoint: str = Field(
        default="https://aca-prod.accela.com/MADISON/Cap/CapHome.aspx",
        description="Madison Accela Citizen Access building-permit endpoint",
    )

    # Columbus, OH (ArcGIS, US-127): Franklin County Auditor sales-dashboard
    # points layer. Annual snapshot of validated arms-length sales with native
    # point geometry (outSR=4326); carries a dual old/new column set
    # (SALEPRICE vs Sale_Price, OWNERNME1 vs OWN1/OWN2). Instrument_Number and
    # MUNINAME/NHBDNAME are empty layer-wide, so the effective id is
    # PARCELID+OBJECTID and borough resolves by coordinate.
    arcgis_columbus_deeds_url: str = Field(
        default=(
            "https://services1.arcgis.com/7r2Wl09a1Apy459r/arcgis/rest/services/"
            "FCAO_Sales_Dashboard_Last_Years_Sales_Points/FeatureServer/0"
        ),
        description="Franklin County (Columbus) Auditor deeds/sales FeatureServer layer URL",
    )

    # Columbus, GA (ArcGIS): Building permit application locations — native
    # point geometry (MapServer Feature Layer 0, Residential; see also 1=Commercial,
    # 2=Pool/Sprinkler). Client requests outSR=4326 so coordinates parse to lat/lng.
    arcgis_columbus_ga_permits_url: str = Field(
        default=(
            "https://ccggisprod.columbusga.org/server/rest/services/"
            "BuildingPermits/MapServer/0"
        ),
        description="Columbus, GA building permits MapServer layer URL (Residential)",
    )

    # Pierce County, WA (ArcGIS): county applications and permits across six
    # departments (Building, Development Engineering, Environmental, Fire,
    # Land Use, Sewer). Point layer in WA State Plane; the client's outSR=4326
    # yields WGS84 directly. The permits spec filters to Building/Land-Use.
    arcgis_pierce_permits_url: str = Field(
        default=(
            "https://services2.arcgis.com/1UvBaQ5y1ubjUPmd/arcgis/rest/services/"
            "Permits_Pierce_County/FeatureServer/0"
        ),
        description="Pierce County permits and applications FeatureServer layer URL",
    )

    # Milwaukee, WI (ArcGIS): active liquor-license registry with point
    # geometry. ANSI-date-literal server (US-87): rejects ISO-string date
    # comparisons; the shared watermark_comparison handles it.
    arcgis_milwaukee_licenses_url: str = Field(
        default=(
            "https://milwaukeemaps.milwaukee.gov/arcgis/rest/services/"
            "regulation/license/MapServer/0"
        ),
        description="Milwaukee liquor license MapServer layer URL",
    )
    # US-138: Milwaukee building permits + yearly property-sales CSVs. Both
    # datasets are address-only and geocoded at parse time per ADR-0004; deeds
    # use an ADR-0005 typed text watermark.
    csv_milwaukee_permits_endpoint: str = Field(
        default=(
            "https://data.milwaukee.gov/dataset/9bada2e0-fad5-4545-8674-"
            "1b2c8c4e9f2f/resource/828e9630-d7cb-42e4-960e-964eae916397/"
            "download/buildingpermits.csv"
        ),
        description="Milwaukee building permits CSV endpoint (US-138)",
    )
    csv_milwaukee_deeds_endpoint: str = Field(
        default=(
            "https://data.milwaukee.gov/dataset/7a8b81f6-d750-4f62-aee8-"
            "30ffce1c64ce/resource/1f2dbf65-3ff9-49a2-a9ef-eb0b6c503017/"
            "download/armslengthsales_2025_valid_20260417.csv"
        ),
        description="Milwaukee 2025 property-sales CSV endpoint (US-138)",
    )
    # Milwaukee CKAN crime + 311 datastore resources.
    ckan_milwaukee_crime_endpoint: str = Field(
        default="ckan://data.milwaukee.gov/87843297-a6fa-46d4-ba5d-cb342fb2d3bb",
        description="Milwaukee crime incidents CKAN datastore resource",
    )
    ckan_milwaukee_311_endpoint: str = Field(
        default="ckan://data.milwaukee.gov/bf2b508a-5bfa-49da-8846-d87ffeee020a",
        description="Milwaukee 311 service requests CKAN datastore resource",
    )

    # Charlotte, NC (ArcGIS): city 311 service requests with native
    # LATITUDE/LONGITUDE + point geometry. Mecklenburg County permits/parcels
    # live on an ArcGIS Hub surface with no quickly-verifiable bulk feed
    # (US-88); the registration is 311-only.
    arcgis_charlotte_311_url: str = Field(
        default=(
            "https://gis.charlottenc.gov/arcgis/rest/services/"
            "ODP/ServiceRequests311/MapServer/0"
        ),
        description="Charlotte ODP 311 service requests layer URL",
    )

    # Houston, TX (ArcGIS, US-140): City of Houston mycity2 HOUSTON311_RECENT_SR_SNOW
    # FeatureServer — native LATITUDE/LONGITUDE doubles + point geometry, CREATED_ON
    # epoch-ms watermark. Rolling recent window (back to 2021-07); the registration
    # is 311-only.
    arcgis_houston_311_url: str = Field(
        default=(
            "https://mycity2.houstontx.gov/gisweb01/rest/services/311/"
            "HOUSTON311_RECENT_SR_SNOW/FeatureServer/0"
        ),
        description="Houston 311 recent service requests FeatureServer layer URL",
    )

    # Nashville, TN (ArcGIS): issued building permits plus residential STR
    # permits as the SLA-class signal; hubNashville 311 registers as the
    # COMPLAINTS_311 feed (US-131, re-adjudicated positive from HJ-119).
    arcgis_nashville_permits_url: str = Field(
        default=(
            "https://services2.arcgis.com/HdTo6HJqh92wn4D8/arcgis/rest/services/"
            "Building_Permits_Issued_2/FeatureServer/0"
        ),
        description="Nashville Building Permits Issued FeatureServer layer URL",
    )
    arcgis_nashville_str_url: str = Field(
        default=(
            "https://services2.arcgis.com/HdTo6HJqh92wn4D8/arcgis/rest/services/"
            "Residential_Short_Term_Rental_Permits_view/FeatureServer/0"
        ),
        description="Nashville Residential Short Term Rental Permits FeatureServer layer URL",
    )
    arcgis_nashville_311_url: str = Field(
        default=(
            "https://services2.arcgis.com/HdTo6HJqh92wn4D8/arcgis/rest/services/"
            "hubNashville_311_Service_Requests_Current_Year_view/FeatureServer/0"
        ),
        description="Nashville hubNashville 311 Service Requests Current Year FeatureServer layer URL",
    )

    # Kansas City, MO (Socrata): 311 Call Center Reported Issues. Corrects the
    # 2026-08-23 rejection (HJ-120); permits/SLA stay unregistered.
    socrata_kansas_city_311_endpoint: str = Field(
        default="https://data.kcmo.org/resource/d4px-6rwg.json",
        description="Kansas City 311 Call Center Reported Issues endpoint",
    )

    # Wichita, KS (ArcGIS, US-157): MABCD permits. The MISC/MABCD service
    # publishes two point layers — layer 0 is Code Enforcement Violations (a
    # documented trap) and layer 1 is the real permits SDE. ApplicationDate is
    # the epoch-ms watermark; PermitNumber identifies the permit and OBJECTID
    # stays out of the job-id chain as an edit counter. Only this one feed
    # (no 311/licenses/deeds) exists open.
    arcgis_wichita_permits_url: str = Field(
        default=(
            "https://gismaps.wichita.gov/ageweb/rest/services/MISC/MABCD/"
            "FeatureServer/1"
        ),
        description="Wichita MABCD permits FeatureServer layer URL (layer 1; layer 0 is violations)",
    )

    # Indianapolis, IN (ArcGIS, US-144): RIMAC service requests. Native point
    # geometry + LAT/LONG_ attributes; REQUESTEDDATETIME epoch-ms watermark.
    # 311-only registration — permits/licenses/deeds have no open feed.
    arcgis_indianapolis_311_url: str = Field(
        default=(
            "https://gis.indy.gov/server/rest/services/OpenData/"
            "ODP_RIMACServiceRequests/FeatureServer/0"
        ),
        description="Indianapolis RIMAC 311 service requests FeatureServer layer URL",
    )

    # Cleveland, OH (ArcGIS, US-153): live permits, 311, and parcel-transfer
    # layers from the City of Cleveland Open Data ArcGIS organization.
    arcgis_cleveland_permits_url: str = Field(
        default=(
            "https://services3.arcgis.com/dty2kHktVXHrqO8i/arcgis/rest/services/"
            "Building_Permits/FeatureServer/0"
        ),
        description="Cleveland issued building permits FeatureServer layer URL",
    )
    arcgis_cleveland_311_url: str = Field(
        default=(
            "https://services3.arcgis.com/dty2kHktVXHrqO8i/arcgis/rest/services/"
            "Data_311/FeatureServer/0"
        ),
        description="Cleveland 311 service requests FeatureServer layer URL",
    )
    arcgis_cleveland_deeds_url: str = Field(
        default=(
            "https://services3.arcgis.com/dty2kHktVXHrqO8i/arcgis/rest/services/"
            "Parcel_Analytics_(PUBLIC_DRAFT_)/FeatureServer/0"
        ),
        description="Cleveland parcel analytics transfer FeatureServer layer URL",
    )

    # Hartford, CT (ArcGIS + Socrata, US-152). Hartford's 311 X/Y values are
    # state-plane feet, so the registry routes these records through address
    # geocoding instead of treating them as latitude/longitude.
    arcgis_hartford_permits_url: str = Field(
        default=(
            "https://utility.arcgis.com/usrsvcs/servers/"
            "d595ae995fb049d3ac54919ebf24b1ac/rest/services/"
            "HartfordOpenDataTables/FeatureServer/0"
        ),
        description="Hartford building permits FeatureServer table URL",
    )
    arcgis_hartford_311_url: str = Field(
        default=(
            "https://utility.arcgis.com/usrsvcs/servers/"
            "2185af186dda46caa1e59323407d1daf/rest/services/"
            "Service_Requests_2015_to_Current/FeatureServer/9"
        ),
        description="Hartford current-year 311 FeatureServer layer URL",
    )
    socrata_hartford_sla_endpoint: str = Field(
        default="https://data.ct.gov/resource/ngch-56tr.json",
        description="Connecticut State Licenses and Credentials Socrata endpoint",
    )

    # Connecticut statewide Socrata feeds (US-419). SLA = State Licenses and
    # Credentials (ngch-56tr); DEEDS = Real Estate Sales / conveyance tax
    # (5mzw-sjtu). Both are filtered per-city/town at the registry level and
    # are address-only (needs_geocode=True).
    socrata_ct_sla_endpoint: str = Field(
        default="https://data.ct.gov/resource/ngch-56tr.json",
        description="Connecticut State Licenses and Credentials Socrata endpoint (statewide)",
    )
    socrata_ct_deeds_endpoint: str = Field(
        default="https://data.ct.gov/resource/5mzw-sjtu.json",
        description="Connecticut Real Estate Sales (2001-2024 GL) Socrata endpoint (statewide)",
    )

    # US-420: California ABC liquor license weekly bulk export (CSV zip).
    # DailyExport-CSV.zip holds one member (ABC-DailyDataExport.csv) with a
    # leading preamble line that CSVClient detects and strips. The registries
    # that ride it declare snapshot ingestion and geocode premise addresses.
    csv_ca_abc_endpoint: str = Field(
        default="https://www.abc.ca.gov/wp-content/uploads/DailyExport-CSV.zip",
        description="California ABC liquor license weekly CSV export zip",
    )

    # Worcester, MA (ArcGIS Hub, US-419). Both layers are non-spatial Tables
    # (address-only) with text M/D/YYYY date columns.
    arcgis_worcester_permits_url: str = Field(
        default=(
            "https://services1.arcgis.com/j8dqo2DJE7mVUBU1/arcgis/rest/services/"
            "Building_Permits/FeatureServer/0"
        ),
        description="Worcester building permits FeatureServer table URL",
    )
    arcgis_worcester_sla_url: str = Field(
        default=(
            "https://services1.arcgis.com/j8dqo2DJE7mVUBU1/arcgis/rest/services/"
            "Food_Establishment_Licenses/FeatureServer/0"
        ),
        description="Worcester food establishment licenses FeatureServer table URL",
    )

    # Raleigh, NC / Wake County (ArcGIS, US-151): native point permits and
    # 311 plus polygon parcel sales for the deeds signal.
    arcgis_raleigh_permits_url: str = Field(
        default=(
            "https://services.arcgis.com/v400IkDOw1ad7Yad/arcgis/rest/services/"
            "Building_Permits/FeatureServer/0"
        ),
        description="Raleigh building permits FeatureServer layer URL",
    )
    arcgis_raleigh_311_url: str = Field(
        default=(
            "https://services.arcgis.com/v400IkDOw1ad7Yad/arcgis/rest/services/"
            "Ask_Raleigh_Requests/FeatureServer/0"
        ),
        description="Raleigh Ask Raleigh service requests FeatureServer layer URL",
    )
    arcgis_wake_deeds_url: str = Field(
        default="https://maps.wake.gov/arcgis/rest/services/Property/Parcels/MapServer/0",
        description="Wake County parcel sales MapServer layer URL",
    )

    # Macon-Bibb County, GA (ArcGIS): Building Permits (2010‑Present) polygon layer.
    arcgis_macon_bibb_permits_url: str = Field(
        default=(
            "https://services6.arcgis.com/Yx1h0qHJ9wIpQWuU/arcgis/rest/services/"
            "Building_Permits_Public/FeatureServer/0"
        ),
        description="Macon-Bibb County Building Permits (2010‑Present) ArcGIS FeatureServer layer URL",
    )

    # San Antonio, TX (CKAN + ArcGIS, US-141): live building permits datastore
    # and point-based 311 service calls.
    ckan_san_antonio_permits_endpoint: str = Field(
        default="ckan://data.sanantonio.gov/c21106f9-3ef5-4f3a-8604-f992b4db7512",
        description="San Antonio building permits CKAN datastore URI",
    )
    arcgis_san_antonio_311_url: str = Field(
        default=(
            "https://services.arcgis.com/g1fRTDLeMgspWrYp/arcgis/rest/services/"
            "311_All_Service_Calls/FeatureServer/0"
        ),
        description="San Antonio 311 service calls FeatureServer layer URL",
    )

    # Sacramento / Sacramento County, CA (ArcGIS, US-142): native-point
    # county permits and city 311 service requests.
    arcgis_sacramento_permits_url: str = Field(
        default=(
            "https://services1.arcgis.com/5NARefyPVtAeuJPU/arcgis/rest/services/"
            "Permits/FeatureServer/0"
        ),
        description="Sacramento County permits FeatureServer layer URL",
    )
    arcgis_sacramento_city_permits_url: str = Field(
        default=(
            "https://services5.arcgis.com/54falWtcpty3V47Z/arcgis/rest/services/"
            "BldgPermitIssued_CurrentYear/FeatureServer/0"
        ),
        description=(
            "Sacramento city issued-permits table (US-196 companion; unpolled). "
            "2026-08-27 G5 staging probe recovered 90.4% of the newest 500 "
            "rows — below the 95% address-geocode floor, so this stays an "
            "inert companion until companion polling and a recovery fix land."
        ),
    )
    arcgis_sacramento_311_url: str = Field(
        default=(
            "https://services5.arcgis.com/54falWtcpty3V47Z/ArcGIS/rest/services/"
            "SalesForce311_View/FeatureServer/0"
        ),
        description="Sacramento 311 service requests FeatureServer layer URL",
    )

    # Reno / Washoe County, NV (ArcGIS, US-161): current county parcel sales
    # with polygon geometry and a MM/DD/YYYY text sale-date watermark.
    arcgis_reno_deeds_url: str = Field(
        default=(
            "https://gisweb.washoecounty.gov/arcgis/rest/services/OpenData/"
            "WashoeDataShare/MapServer/0"
        ),
        description="Washoe County parcel sales MapServer layer URL",
    )

    # Spokane / Spokane County, WA (US-160): annual county sales layers,
    # ArcGIS-hosted XLS permits, and Washington LCB renewal snapshots.
    arcgis_spokane_deeds_url: str = Field(
        default="https://gismo.spokanecounty.org/arcgis/rest/services/OpenData/Property/MapServer/20",
        description="Spokane County 2026 parcel sales MapServer layer URL",
    )
    excel_spokane_permits_url: str = Field(
        default="https://www.arcgis.com/sharing/rest/content/items/3fcb39ac614d41af9fd22b87af8ff245/data",
        description="Spokane County Building and Planning permits XLS download URL",
    )
    socrata_wa_liquor_renewal_endpoint: str = Field(
        default="https://data.wa.gov/resource/9dee-kzm5.json",
        description="Washington LCB liquor renewal Socrata endpoint",
    )
    socrata_wa_cannabis_renewal_endpoint: str = Field(
        default="https://data.wa.gov/resource/brpd-b6zd.json",
        description="Washington LCB cannabis renewal Socrata endpoint",
    )

    # Dayton, OH (US-159): Hansen service requests are a rolling 90-day
    # ArcGIS layer; the source has no public archive.
    arcgis_dayton_311_url: str = Field(
        default=(
            "https://maps.daytonohio.gov/gisservices/rest/services/"
            "PublicWorks/COD_ServiceRequests_Last90/MapServer/0"
        ),
        description="Dayton Hansen service requests rolling-90-day MapServer layer URL",
    )

    # Tulsa, OK (US-158): Verint customer-care cases are a live, approximately
    # 30-day rolling window; the public layer has no historical archive.
    arcgis_tulsa_311_url: str = Field(
        default=(
            "https://maps.cityoftulsa.org/hosting/rest/services/"
            "CustomerCare/VerintCasesPublic/FeatureServer/0"
        ),
        description="Tulsa Verint 311 cases rolling-window FeatureServer layer URL",
    )
    # Tulsa crime (ArcGIS `Tulsa_Crime_Time_Display`).
    arcgis_tulsa_crime_url: str = Field(
        default="https://services5.arcgis.com/cuQhNeNcUrgLmYGD/arcgis/rest/services/Tulsa_Crime_Time_Display/FeatureServer/0",
        description="Tulsa crime incidents ArcGIS FeatureServer layer URL",
    )

    # El Paso, TX (US-156): Accela-backed requests are a live 30-day partial
    # view. ArcGISClient requests outSR=4326, transforming native TX state-plane
    # geometry before the shared 311 parser sees each row.
    arcgis_el_paso_311_url: str = Field(
        default="https://gis.elpasotexas.gov/accela/rest/services/311/Requests/FeatureServer/0",
        description="El Paso Accela 311 requests FeatureServer layer URL",
    )
    # El Paso residential permits (ArcGIS `NewResi2018_19`).
    arcgis_el_paso_permits_url: str = Field(
        default="https://services1.arcgis.com/hyTVSIhR7dHyDsJF/arcgis/rest/services/NewResi2018_19/FeatureServer/0",
        description="El Paso residential permits ArcGIS FeatureServer layer URL",
    )

    # Durham, NC (US-154): live point permits and polygon parcel sales.
    arcgis_durham_permits_url: str = Field(
        default="https://webgis2.durhamnc.gov/server/rest/services/PublicServices/Inspections/MapServer/12",
        description="Durham All Building Permits MapServer layer URL",
    )
    arcgis_durham_deeds_url: str = Field(
        default="https://webgis2.durhamnc.gov/server/rest/services/PublicServices/Property/MapServer/4",
        description="Durham parcel sales/deeds MapServer layer URL",
    )

    # Wilmington, NC / New Hanover County (US-292): county permits FeatureServer.
    arcgis_wilmington_nc_permits_url: str = Field(
        default="https://gis.nhcgov.com/server/rest/services/Thematic/BuildingPermits/FeatureServer/0",
        description="New Hanover County building permits FeatureServer layer URL",
    )

    # Dallas, TX (US-149): live ROW/traffic-control permit proxy plus a
    # Building Services CRM view containing approximately 30 days of 311 data.
    arcgis_dallas_row_permits_url: str = Field(
        default=(
            "https://services2.arcgis.com/rwnOSbfKSwyTBcwN/arcgis/rest/services/"
            "ROW/FeatureServer/0"
        ),
        description="Dallas right-of-way permit proxy FeatureServer layer URL",
    )
    arcgis_dallas_311_url: str = Field(
        default=(
            "https://services2.arcgis.com/rwnOSbfKSwyTBcwN/arcgis/rest/services/"
            "CRM_30Days_viewLayer_BuildingServices/FeatureServer/0"
        ),
        description="Dallas Building Services approximately 30-day CRM view URL",
    )
    # Dallas crimes (Socrata `pumt-d92b`).
    socrata_dallas_crime_endpoint: str = Field(
        default="https://www.dallasopendata.com/resource/pumt-d92b.json",
        description="Dallas crimes Socrata endpoint",
    )

    # Louisville, KY (US-148): annual Metro 311 layer plus Kentucky ABC's
    # active-license registry, filtered by the ingestion spec to Jefferson
    # County.
    arcgis_louisville_311_url: str = Field(
        default=(
            "https://services1.arcgis.com/79kfd2K6fskCAkyg/arcgis/rest/services/"
            "metro_311_2026/FeatureServer/0"
        ),
        description="Louisville Metro 2026 311 FeatureServer layer URL",
    )
    arcgis_louisville_abc_url: str = Field(
        default=(
            "https://services1.arcgis.com/79kfd2K6fskCAkyg/arcgis/rest/services/"
            "ABC_State_ActiveLicenses/FeatureServer/0"
        ),
        description="Kentucky ABC active licenses FeatureServer layer URL",
    )
    # Louisville crime, active construction permits, and ROW construction
    # permits (ArcGIS, same org as the 311/ABC layers).
    arcgis_louisville_crime_url: str = Field(
        default="https://services1.arcgis.com/79kfd2K6fskCAkyg/arcgis/rest/services/crime_data_2025/FeatureServer",
        description="Louisville crime incidents ArcGIS FeatureServer layer URL",
    )
    arcgis_louisville_permits_url: str = Field(
        default="https://services1.arcgis.com/79kfd2K6fskCAkyg/arcgis/rest/services/active_construction_permits/FeatureServer",
        description="Louisville active construction permits ArcGIS FeatureServer layer URL",
    )
    arcgis_louisville_street_cut_url: str = Field(
        default="https://services1.arcgis.com/79kfd2K6fskCAkyg/arcgis/rest/services/Louisville_KY_ROW_Construction_Permits_new/FeatureServer",
        description="Louisville ROW construction permits ArcGIS FeatureServer layer URL",
    )

    # Portland, OR (US-143): residential permits from Portland Maps and OLCC
    # applications received from Oregon's Socrata portal.
    arcgis_portland_permits_url: str = Field(
        default=(
            "https://www.portlandmaps.com/od/rest/services/"
            "COP_OpenData_PlanningDevelopment/MapServer/89"
        ),
        description="Portland residential building permits MapServer layer URL",
    )
    socrata_portland_olcc_applications_endpoint: str = Field(
        default="https://data.oregon.gov/resource/qad4-bnxp.json",
        description="Oregon OLCC liquor applications received endpoint",
    )

    # San Jose, CA (US-147): City CKAN datastore resources. Permits are an
    # address-only rolling-30-day export; 311 is a current-year annual export.
    ckan_san_jose_permits_endpoint: str = Field(
        default="ckan://data.sanjoseca.gov/045b3678-e923-4002-b696-300955bc6d06",
        description="San Jose last-30-days building permits CKAN datastore resource",
    )
    ckan_san_jose_311_endpoint: str = Field(
        default="ckan://data.sanjoseca.gov/d886727c-60f1-4be7-9a30-f6806375b1a3",
        description="San Jose 2026 311 service requests CKAN datastore resource",
    )

    # Laredo (US-263): CKAN OpenGov "City of Laredo Building Applications;
    # Permits; Inspections" — resource 61972510-7b8c-488a-9e88-b73b0112f496,
    # 91,198 rows, monthly bulk replace, watermark "PERMIT ISS. DATE" newest
    # 2026-07-02, address-only STREET NBR + STREET (needs_geocode). 311/SLA/deeds
    # are Tier 3; state super-feed SLA companion (TX TDLR/TREC/TABC Webb 48479).
    ckan_laredo_permits_endpoint: str = Field(
        default="ckan://data.openlaredo.com/61972510-7b8c-488a-9e88-b73b0112f496",
        description="Laredo building permits CKAN datastore resource",
    )

    # Boise / Ada County (US-150): residential-only permits. The source layer
    # advertises Idaho state-plane geometry; ArcGIS queries request WGS84 and
    # the city registry declares address geocoding as the fallback.
    arcgis_boise_permits_url: str = Field(
        default="https://services1.arcgis.com/WHM6qC35aMtyAAlN/arcgis/rest/services/PDS_BuildingPermits_HighImpact/FeatureServer/0",
        description="Boise high-impact building permits ArcGIS FeatureServer layer URL",
    )
    # Boise Police Department crime incidents (ArcGIS `BPD_Crimes_Public`).
    arcgis_boise_crime_url: str = Field(
        default="https://services1.arcgis.com/WHM6qC35aMtyAAlN/arcgis/rest/services/BPD_Crimes_Public/FeatureServer",
        description="Boise crime incidents ArcGIS FeatureServer layer URL",
    )

    # Fort Worth / Tarrant County (US-150): CFW Development Permits Points, a
    # WGS84 ArcGIS point layer (759k+ records, hourly refresh). Geometry resolves
    # directly to lat/lng; address geocoding is the fallback for geometry-less rows.
    arcgis_fort_worth_permits_url: str = Field(
        default="https://mapit.fortworthtexas.gov/ags/rest/services/CIVIC/Permits/FeatureServer/0",
        description="Fort Worth development permits ArcGIS FeatureServer layer URL",
    )

    # Honolulu, HI (US-193): City and County of Honolulu Socrata. 311 is a
    # rolling 30-day snapshot (address-only, ADR-0004). Permits endpoint is
    # reserved for a live successor — 4vab-c87q is a closed archive through
    # 2025-06-30 and must not be wired as incremental.
    socrata_honolulu_311_endpoint: str = Field(
        default="https://data.honolulu.gov/resource/jdy7-ftwe.json",
        description="Honolulu HNL 311 Reports (rolling 30-day) Socrata endpoint",
    )
    socrata_honolulu_permits_endpoint: str = Field(
        default="https://data.honolulu.gov/resource/4vab-c87q.json",
        description="Honolulu building permits Socrata endpoint (CLOSED ARCHIVE through 2025-06-30; do not ingest as live)",
    )

    # Orlando / Orange County (US-194): Business Tax Receipts (primary SLA)
    # plus STR licenses as an SLA companion. Live BTR window is address-only
    # (ADR-0004). Do not wire FeedType.STR.
    socrata_orlando_sla_endpoint: str = Field(
        default="https://data.cityoforlando.net/resource/7388-4re5.json",
        description="Orlando Business Tax Receipts Socrata endpoint",
    )
    socrata_orlando_str_endpoint: str = Field(
        default="https://data.cityoforlando.net/resource/ssrj-rbua.json",
        description="Orlando Short Term Rental Licenses Socrata endpoint (SLA companion)",
    )
    # Gainesville, FL (Socrata): native-point permits with latitude/longitude and location_1.
    socrata_gainesville_permits_endpoint: str = Field(
        default="https://data.cityofgainesville.org/resource/p798-x3nx.json",
        description="Gainesville building permits Socrata endpoint",
    )

    # Melbourne / Palm Bay / Titusville (Brevard County, FL) — US-296
    arcgis_brevard_permits_url: str = Field(
        default="https://gis.palmbayflorida.org/arcgis/rest/services/GrowthManagement/BuildingPermits/FeatureServer/0",
        description="Palm Bay (Brevard County) Building Permits ArcGIS FeatureServer layer URL",
    )

    # Miami-Dade County (US-199): ArcGIS Hub permits table + LBT SLA snapshot
    # + PaGis last-sale points. No 311. Companions are metadata-only.
    arcgis_miami_dade_permits_url: str = Field(
        default="https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/miamidade_permit_data/FeatureServer/0",
        description="Miami-Dade building permits issued ArcGIS table URL (rolling 2-year, address-only)",
    )
    arcgis_miami_dade_sla_url: str = Field(
        default="https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/Local_Business_Tax_Feature_Layer_View/FeatureServer/0",
        description="Miami-Dade Local Business Tax ArcGIS FeatureServer layer URL",
    )
    arcgis_miami_dade_deeds_url: str = Field(
        default="https://gisweb.miamidade.gov/ArcGIS/rest/services/MD_ComparableSales/MapServer/5",
        description="Miami-Dade PaGis comparable-sales last-sale ArcGIS MapServer layer URL",
    )
    arcgis_miami_dade_sla_certificate_of_use_url: str = Field(
        default="https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/CertificateOfUse_New_gdb/FeatureServer/0",
        description="Miami-Dade certificate of use ArcGIS companion (not polled)",
    )
    arcgis_miami_dade_sla_enterprise_twin_url: str = Field(
        default="https://gisweb.miamidade.gov/ArcGIS/rest/services/BusinessTracker/MapServer/0",
        description="Miami-Dade BusinessTracker ArcGIS companion (not polled)",
    )

    # Memphis / Shelby County, TN (US-201): DPD building permits (monthly
    # ArcGIS dump) + citywide 311. Native WGS84 on permits; 311 prefers
    # outSR=4326 geometry (do not map mixed X/Y). Partial — no SLA/deeds.
    arcgis_memphis_permits_url: str = Field(
        default="https://services2.arcgis.com/saWmpKJIUAjyyNVc/arcgis/rest/services/DPD_Building_Permits/FeatureServer/0",
        description="Memphis DPD building permits ArcGIS FeatureServer layer URL",
    )
    arcgis_memphis_311_url: str = Field(
        default="https://311.memphistn.gov/server/rest/services/311/311_Request_Map_PROD/FeatureServer/0",
        description="Memphis 311 Request Map (layer 0) ArcGIS FeatureServer URL",
    )

    # Phoenix / Maricopa County (US-197): Planning_Permit daily points +
    # ShapePHX STR as SLA. Native geometry (outSR=4326); no geocode.
    # Companion ShapePHXPermitsPoints_DL is weekly Issued; do not wire the
    # frozen non-_DL twin. No 311 / deeds.
    arcgis_phoenix_permits_url: str = Field(
        default="https://maps.phoenix.gov/pub/rest/services/Public/Planning_Permit/MapServer/1",
        description="Phoenix Planning_Permit layer 1 ArcGIS MapServer URL",
    )
    arcgis_phoenix_shapephx_permits_url: str = Field(
        default="https://mapportal.phoenix.gov/pds/rest/services/ShapePHX/ShapePHXPermitsPoints_DL/MapServer/0",
        description="Phoenix ShapePHX Issued permits _DL companion ArcGIS MapServer URL",
    )
    arcgis_phoenix_sla_url: str = Field(
        default="https://mapportal.phoenix.gov/pds/rest/services/ShapePHX/ShapePHX_Short_Term_Rentals/MapServer/0",
        description="Phoenix ShapePHX Short Term Rentals ArcGIS MapServer URL (SLA)",
    )
    # US-392: Maricopa County Sales Affidavits — ArcGIS Online CSV Collection,
    # item f3484c72a938497286adc4e5de7e9963. Public anonymous download (61 MB
    # ZIP, `Data/Sales_Affidavits.txt` pipe-delimited member). Probe 2026-08-28:
    # 912,806 rows, fresh (item modified 2026-08-03), no Last-Modified header on
    # the download — freshness via AGOL item metadata or alarm_exempt.
    csv_phoenix_deeds_endpoint: str = Field(
        default="https://www.arcgis.com/sharing/rest/content/items/f3484c72a938497286adc4e5de7e9963/data",
        description="Maricopa County Sales Affidavits CSV Collection download URL (US-392)",
    )

    # Aurora, CO (US-326): issued building permits MapServer 44 (full history,
    # IssueDate watermark) + non-home business licenses MapServer 77 (Issue_Date
    # snapshot; L34 liquor / L36 all-business / L4 marijuana companions). Native
    # outSR=4326 geometry primary; EPSG:2232 State-Plane PropX/PropY fallback.
    arcgis_aurora_permits_url: str = Field(
        default="https://ags.auroragov.org/aurora/rest/services/OpenData/MapServer/44",
        description="Aurora issued building permits ArcGIS MapServer URL",
    )
    arcgis_aurora_sla_url: str = Field(
        default="https://ags.auroragov.org/aurora/rest/services/OpenData/MapServer/77",
        description="Aurora non-home business licenses ArcGIS MapServer URL (SLA)",
    )
    arcgis_aurora_sla_liquor_url: str = Field(
        default="https://ags.auroragov.org/aurora/rest/services/OpenData/MapServer/34",
        description="Aurora liquor licenses companion ArcGIS MapServer URL",
    )
    arcgis_aurora_sla_all_businesses_url: str = Field(
        default="https://ags.auroragov.org/aurora/rest/services/OpenData/MapServer/36",
        description="Aurora all-business licenses companion ArcGIS MapServer URL",
    )
    arcgis_aurora_sla_marijuana_url: str = Field(
        default="https://ags.auroragov.org/aurora/rest/services/OpenData/MapServer/4",
        description="Aurora marijuana licenses companion ArcGIS MapServer URL",
    )

    # Henderson, NV (US-325): DSC_Permits FeatureServer 0 (IssueDate) + Active
    # Licenses CSV item (Original Issue Date snapshot, address-only needs_geocode),
    # with MJBL companion item filtered Jurisdiction='HENDERSON'.
    arcgis_henderson_permits_url: str = Field(
        default="https://services2.arcgis.com/naGsY5NZWVbd6bwD/arcgis/rest/services/DSC_Permits/FeatureServer/0",
        description="Henderson DSC permits ArcGIS FeatureServer URL",
    )
    arcgis_henderson_sla_url: str = Field(
        default="https://www.arcgis.com/sharing/rest/content/items/2b3fac57210542229afc4bfddd6cd6e8/data",
        description="Henderson active business licenses CSV item URL (SLA)",
    )
    arcgis_henderson_sla_mjbl_url: str = Field(
        default="https://www.arcgis.com/sharing/rest/content/items/6c470a95e83e4051a4d1222afa056ed6/data",
        description="Henderson MJBL licenses CSV companion item URL",
    )

    # Virginia Beach, VA (US-354): Building_Permits_Applications_view (IssueDate,
    # cadence 1d), Business_Licenses_view (Begin_Date annual-trickle SLA, cadence
    # 365d), Property_Sales_ (Sales_Date batched deeds, cadence 14d). All Tables
    # (non_spatial, address-only needs_geocode).
    arcgis_virginia_beach_permits_url: str = Field(
        default="https://services2.arcgis.com/CyVvlIiUfRBmMQuu/arcgis/rest/services/Building_Permits_Applications_view/FeatureServer/0",
        description="Virginia Beach building permits view ArcGIS FeatureServer URL",
    )
    arcgis_virginia_beach_sla_url: str = Field(
        default="https://services2.arcgis.com/CyVvlIiUfRBmMQuu/arcgis/rest/services/Business_Licenses_view/FeatureServer/0",
        description="Virginia Beach business licenses view ArcGIS FeatureServer URL (SLA)",
    )
    arcgis_virginia_beach_deeds_url: str = Field(
        default="https://services2.arcgis.com/CyVvlIiUfRBmMQuu/arcgis/rest/services/Property_Sales_/FeatureServer/0",
        description="Virginia Beach property sales ArcGIS FeatureServer URL (deeds)",
    )

    # Omaha, NE (US-358): Mayor's Hotline Cityworks 311 MapServer 0 (DATETIMEINIT
    # DateOnly watermark, same-day, native outSR=4326, PROBADDRESS geocode).
    arcgis_omaha_311_url: str = Field(
        default="https://dcgis.org/server/rest/services/Cityworks/Mayors_Hotline_Dashboard_Interactive/MapServer/0",
        description="Omaha Mayor's Hotline 311 ArcGIS MapServer URL",
    )

    # Toledo, OH (US-359): Engage Toledo Cityworks service-request extract
    # MapServer 0 (INIT_DATE watermark, same-day, native outSR=4326 primary,
    # LOCATION geocode; do NOT map mixed X_COORD/Y_COORD).
    arcgis_toledo_311_url: str = Field(
        default="https://gis.toledo.oh.gov/arcgis/rest/services/Public/CityWorks_ServiceRequest_2022/MapServer/0",
        description="Toledo Engage 311 Cityworks ArcGIS MapServer URL",
    )

    # Buffalo, NY (US-349): restaurant-license SLA (Socrata). Native WGS84
    # latitude/longitude; NULLs-first ordering demands the issdttm IS NOT
    # NULL where guard; gpsx/gpsy are mixed-CRS and never candidates.
    socrata_buffalo_sla_endpoint: str = Field(
        default="https://data.buffalony.gov/resource/4pp3-qkuj.json",
        description="Buffalo restaurant licenses Socrata resource URL (SLA)",
    )

    # Rochester, NY (US-351): deeds/sales via the Monroe County RPS tax-parcel
    # open-data layer (native parcel polygons, monthly roll with lag).
    arcgis_rochester_deeds_url: str = Field(
        default="https://maps.cityofrochester.gov/server/rest/services/Open_Data/Tax_Parcels_Open_Data/FeatureServer/0",
        description="Rochester tax parcel open data ArcGIS FeatureServer URL (deeds)",
    )

    # Syracuse, NY (US-352): rental-registry SLA (native WGS84 coords,
    # event-driven RR_app_received watermark; PII dropped at field map).
    arcgis_syracuse_sla_url: str = Field(
        default="https://services6.arcgis.com/bdPqSfflsdgFRVVM/arcgis/rest/services/Syracuse_Rental_Registry/FeatureServer/0",
        description="Syracuse rental registry ArcGIS FeatureServer URL (SLA)",
    )

    # Lynchburg, VA (US-318): single ODPDynamic MapServer, layers 37 (permits),
    # 33 (SLA), 34 (deeds), 41 (parcel-join geometry source). Layer 34
    # publishes no objectIdField — ESRI_OID ordering is mandatory.
    arcgis_lynchburg_permits_url: str = Field(
        default="https://mapviewer.lynchburgva.gov/arcgis/rest/services/OpenData/ODPDynamic/MapServer/37",
        description="Lynchburg ODP building permits ArcGIS MapServer URL (layer 37)",
    )
    arcgis_lynchburg_sla_url: str = Field(
        default="https://mapviewer.lynchburgva.gov/arcgis/rest/services/OpenData/ODPDynamic/MapServer/33",
        description="Lynchburg ODP business licenses ArcGIS MapServer URL (layer 33)",
    )
    arcgis_lynchburg_deeds_url: str = Field(
        default="https://mapviewer.lynchburgva.gov/arcgis/rest/services/OpenData/ODPDynamic/MapServer/34",
        description="Lynchburg ODP property transfers ArcGIS MapServer URL (layer 34)",
    )
    arcgis_lynchburg_parcel_layer_url: str = Field(
        default="https://mapviewer.lynchburgva.gov/arcgis/rest/services/OpenData/ODPDynamic/MapServer/41",
        description="Lynchburg ODP parcel polygon layer URL (deeds geometry join)",
    )

    # Greenville, SC (US-340): rolling two-year building-permits window
    # (NewIssueDate watermark is not where-queryable; outSR=4326 geometry).
    arcgis_greenville_permits_url: str = Field(
        default="https://citygis.greenvillesc.gov/arcgis/rest/services/InfoHUB/BuildingPermits_PriorTwoYears/MapServer/0",
        description="Greenville building permits ArcGIS MapServer URL",
    )

    # Anchorage, AK (US-330): assessor property-information deeds (daily
    # batch republication; future-dated Deed_Date sentinels excluded at the
    # source via where guard).
    arcgis_anchorage_deeds_url: str = Field(
        default="https://services2.arcgis.com/Ce3DhLRthdwbHlfF/arcgis/rest/services/PropertyInformation_Hosted/FeatureServer/0",
        description="Anchorage property information ArcGIS FeatureServer URL (deeds)",
    )

    # Tucson, AZ (US-328): economic-development SLA snapshot (future-dated
    # DT_START application sentinels excluded via where guard; ANSI-date
    # host — gis.tucsonaz.gov is listed in ANSI_DATE_LITERAL_HOSTS).
    arcgis_tucson_sla_url: str = Field(
        default="https://gis.tucsonaz.gov/arcgis/rest/services/PublicMaps/OpenData_EconomicDevelopment/MapServer/3",
        description="Tucson economic development licenses ArcGIS MapServer URL (SLA)",
    )

    # Albuquerque / Bernalillo County (US-205): daily CABQ building-permits
    # CSV dump. Address-only (ADR 0004). AGIS City_Building_Permits is frozen
    # (max DateIssued 2025-01-16) and must not be wired.
    csv_albuquerque_permits_endpoint: str = Field(
        default="https://data.cabq.gov/business/buildingpermits/BuildingPermitsCABQ-en-us.csv",
        description="Albuquerque building permits daily CSV dump (US-205)",
    )

    # City of St. Louis, MO (US-200): CSB 311 zip + ColdFusion 30-day permits
    # CSV + excise liquor snapshot. Independent city; no county deeds.
    csv_st_louis_311_endpoint: str = Field(
        default="https://www.stlouis-mo.gov/data/upload/data-files/csb.zip",
        description="St. Louis CSB 311 yearly CSV zip (member 2026.csv)",
    )
    csv_st_louis_permits_endpoint: str = Field(
        default="https://www.stlouis-mo.gov/customcf/endpoints/building-permits/building-permits-30-days-export.cfm?permitType=all&dataType=csv",
        description="St. Louis building permits 30-day ColdFusion CSV export",
    )
    csv_st_louis_sla_endpoint: str = Field(
        default="https://www.stlouis-mo.gov/data/upload/data-files/excise-data/excise-permits-licenses.csv",
        description="St. Louis excise (liquor) licenses CSV snapshot",
    )

    # Tampa, FL (US-146): audited full permits and partial alcohol-beverage
    # history layers, both point-geocoded ArcGIS services.
    arcgis_tampa_permits_url: str = Field(
        default="https://arcgis.tampagov.net/arcgis/rest/services/Planning/PermitsAll/FeatureServer/0",
        description="Tampa full permits ArcGIS FeatureServer layer URL",
    )
    arcgis_tampa_sla_url: str = Field(
        default="https://arcgis.tampagov.net/arcgis/rest/services/Planning/AlcoholBeverage/FeatureServer/0",
        description="Tampa alcohol-beverage partial SLA ArcGIS FeatureServer layer URL",
    )
    # Tampa crime (calls for service) and right-of-way permits (ArcGIS).
    arcgis_tampa_crime_url: str = Field(
        default="https://arcgis.tampagov.net/arcgis/rest/services/CallsforService/FirePoliceCalls/MapServer/1",
        description="Tampa calls-for-service ArcGIS MapServer layer URL",
    )
    arcgis_tampa_street_cut_url: str = Field(
        default="https://arcgis.tampagov.net/arcgis/rest/services/Transportation/ROWPermits/FeatureServer/0",
        description="Tampa right-of-way permits ArcGIS FeatureServer layer URL",
    )

    # Cape Coral–Fort Myers, FL (US-285): public permits MapServer table (address-only).
    arcgis_cape_coral_permits_url: str = Field(
        default="https://capeims.capecoral.gov/arcgis/rest/services/OpenData/OpenData/MapServer/1",
        description="Cape Coral–Fort Myers building permits ArcGIS MapServer table URL (address-only)",
    )
    # Lakeland, FL (US-286): iMS Public CED permits MapServer layer (verified on GeoHub).
    arcgis_lakeland_permits_url: str = Field(
        default="https://gismims.lakelandgov.net/portal/rest/services/Public_CED/Lakeland_CED_Permits/MapServer/0",
        description="Lakeland iMS Public CED permits ArcGIS MapServer layer URL",
    )
    # Port St. Lucie, FL (US-289): public Building Permits FeatureServer (weekly updates)
    arcgis_port_st_lucie_permits_url: str = Field(
        default="https://services1.arcgis.com/YdUP5V6WwzeG8T8r/arcgis/rest/services/Permits/FeatureServer/0",
        description="Port St. Lucie building permits ArcGIS FeatureServer layer URL",
    )

    # Las Vegas / Clark County (US-145): address-only ArcGIS tables. Both
    # feeds declare ADR-0004 geocoding in the city registry.
    arcgis_las_vegas_permits_url: str = Field(
        default="https://services1.arcgis.com/F1v0ufATbBQScMtY/ArcGIS/rest/services/OpenData_Building_Permits_/FeatureServer/0",
        description="Clark County building permits ArcGIS table URL",
    )
    arcgis_las_vegas_deeds_url: str = Field(
        default="https://services1.arcgis.com/F1v0ufATbBQScMtY/ArcGIS/rest/services/parcels/FeatureServer/0",
        description="Clark County parcel sales ArcGIS table URL",
    )

    # Kansas City, MO (Socrata): Business License Holders (US-134). Snapshot
    # feed carrying native GeoJSON point geometry (96.4% non-null) and a
    # valid_license_for YYYYMMDD expiration column; publication had lapsed
    # ~7mo at registration, hence the 90-day cadence.
    socrata_kansas_city_licenses_endpoint: str = Field(
        default="https://data.kcmo.org/resource/pnm4-68wg.json",
        description="Kansas City Business License Holders endpoint",
    )

    # US-265: supplemental feeds for existing cities (research 2026-08-26). Each
    # endpoint is declared here so the interlock gate's endpoint-in-settings
    # invariant holds; the registry references these fields, never literals.
    socrata_dallas_crime_endpoint: str = Field(
        default="https://www.dallasopendata.com/resource/pumt-d92b.json",
        description="Dallas Crimes Socrata endpoint (aging; verify before relying)",
    )
    ckan_milwaukee_crime_endpoint: str = Field(
        default="ckan://data.milwaukee.gov/87843297-a6fa-46d4-ba5d-cb342fb2d3bb",
        description="Milwaukee NIBRS crime CKAN resource",
    )
    ckan_milwaukee_311_endpoint: str = Field(
        default="ckan://data.milwaukee.gov/bf2b508a-5bfa-49da-8846-d87ffeee020a",
        description="Milwaukee Call Center 311 CKAN resource",
    )
    arcgis_tulsa_crime_url: str = Field(
        default="https://services5.arcgis.com/cuQhNeNcUrgLmYGD/arcgis/rest/services/Tulsa_Crime_Time_Display/FeatureServer/0",
        description="Tulsa crime ArcGIS FeatureServer",
    )
    # Augusta, GA (US-287): CityView permits table (non-spatial; address-only).
    # Registered as PERMITS with ADR-0004 geocoding; 311 requires an API key and
    # is not registered. SLA uses SNAP GA slice.
    arcgis_augusta_permits_url: str = Field(
        default="https://gismap.augustaga.gov/arcgis/rest/services/EnterpriseApps/iasWorld_Permit/MapServer/1",
        description="Augusta CityView permits ArcGIS MapServer table URL (address-only, geocoded)",
    )
    arcgis_el_paso_permits_url: str = Field(
        default="https://services1.arcgis.com/hyTVSIhR7dHyDsJF/arcgis/rest/services/NewResi2018_19/FeatureServer/0",
        description="El Paso residential building permits ArcGIS FeatureServer (frozen 2018-2021 snapshot)",
    )
    arcgis_louisville_crime_url: str = Field(
        default="https://services1.arcgis.com/79kfd2K6fskCAkyg/arcgis/rest/services/crime_data_2025/FeatureServer",
        description="Louisville Metro crime ArcGIS FeatureServer (geocoded; no native coords)",
    )
    arcgis_louisville_permits_url: str = Field(
        default="https://services1.arcgis.com/79kfd2K6fskCAkyg/arcgis/rest/services/active_construction_permits/FeatureServer",
        description="Louisville active construction permits ArcGIS FeatureServer",
    )
    arcgis_louisville_street_cut_url: str = Field(
        default="https://services1.arcgis.com/79kfd2K6fskCAkyg/arcgis/rest/services/Louisville_KY_ROW_Construction_Permits_new/FeatureServer",
        description="Louisville ROW construction permits ArcGIS FeatureServer",
    )
    arcgis_tampa_crime_url: str = Field(
        default="https://arcgis.tampagov.net/arcgis/rest/services/CallsforService/FirePoliceCalls/MapServer/1",
        description="Tampa Police Calls for Service ArcGIS MapServer",
    )
    arcgis_tampa_street_cut_url: str = Field(
        default="https://arcgis.tampagov.net/arcgis/rest/services/Transportation/ROWPermits/FeatureServer/0",
        description="Tampa ROW permits ArcGIS FeatureServer",
    )
    arcgis_las_vegas_calls_for_service_url: str = Field(
        default="https://services.arcgis.com/jjSk6t82vIntwDbs/arcgis/rest/services/LVMPD_Calls_For_Service_All/FeatureServer",
        description="Las Vegas LVMPD Calls For Service ArcGIS FeatureServer",
    )
    arcgis_boise_crime_url: str = Field(
        default="https://services1.arcgis.com/WHM6qC35aMtyAAlN/arcgis/rest/services/BPD_Crimes_Public/FeatureServer",
        description="Boise BPD crimes ArcGIS FeatureServer",
    )
    ckan_san_jose_crime_endpoint: str = Field(
        default="ckan://data.sanjoseca.gov/dc0ec99c-0c6b-45fb-b1ec-faf072fe4833",
        description="San Jose Police Calls for Service (2026, updated daily) CKAN datastore resource",
    )
    # US-364: USDA FNS SNAP Retailer Locator — one national FeatureServer
    # (item 8b260f9a10b0459aa441ad8588c2251c, usda-fns org) sliced per metro
    # with a State where-clause. FNS states the data is updated every 2 weeks.
    arcgis_snap_retailers_url: str = Field(
        default=(
            "https://services1.arcgis.com/RLQu0rK7h4kbsBq5/arcgis/rest/services/"
            "snap_retailer_location_data/FeatureServer/0"
        ),
        description="USDA FNS SNAP retailer locations ArcGIS FeatureServer layer URL",
    )

    # US-397: TX state-registry SLA supplements (county-sliced Socrata feeds).
    # TREC broker/sales-agent stock, TREC initial-license applications (flow),
    # and TDLR all-license registry — all data.texas.gov, daily refresh.
    socrata_tx_trec_broker_endpoint: str = Field(
        default=(
            "https://data.texas.gov/resource/s7ft-44qi.json"
            "?$select=*, 'trec_broker:' || license_type as license_type_ns"
        ),
        description="TX TREC Broker & Sales Agent License Holders (county-sliced, daily)",
    )
    socrata_tx_trec_app_endpoint: str = Field(
        default=(
            "https://data.texas.gov/resource/bf5n-799f.json"
            "?$select=*, 'trec_app:' || license_type as license_type_ns"
        ),
        description="TX TREC Applications for Initial License Issuance (flow, daily)",
    )
    socrata_tx_tdlr_endpoint: str = Field(
        default=(
            "https://data.texas.gov/resource/7358-krk7.json"
            "?$select=*, 'tdlr:' || license_type as license_type_ns, :updated_at"
        ),
        description="TX TDLR All Licenses (contractor/trades slice, daily)",
    )

    # US-398: FL Statewide Cadastral — one national ArcGIS layer aggregating all
    # 67 FL counties' appraiser rolls; PERMITS new-supply proxy via year-built
    # cohort. Annual assessment cadence.
    arcgis_fl_cadastral_url: str = Field(
        default=(
            "https://services9.arcgis.com/Gh9awoU677aKree0/arcgis/rest/services/"
            "Florida_Statewide_Cadastral/FeatureServer/0"
        ),
        description="FL Statewide Cadastral appraiser-roll construction-activity layer",
    )

    # US-399: Buncombe County (NC) Property roll — Asheville DEEDS supplement.
    # Roll-grade (last sale per parcel); price reconstructed from NC excise
    # stamps (Stamps x 500). Snapshot, annual reappraisal cadence.
    arcgis_asheville_deeds_url: str = Field(
        default="https://gis.buncombecounty.org/arcgis/rest/services/opendata/FeatureServer/1",
        description="Buncombe County NC Property roll layer (Asheville DEEDS supplement)",
    )

    # US-404: MARTA station entrances/exits (Atlanta) — Socrata, weekly.
    socrata_marta_endpoint: str = Field(
        default="https://data.atlantaga.gov/resource/nwqk-3q5y.json",
        description="MARTA station entrances/exits (Atlanta) Socrata endpoint",
    )

    # Address geocoding (ADR 0004): confidence floor gates wrong-cell risk —
    # below it, events keep null H3 rather than a guessed coordinate.
    geocode_confidence_floor: float = Field(
        default=0.9,
        description="Minimum confidence for a geocoded coordinate to be used",
    )
    geocode_backend: str = Field(
        default="census",
        description="Geocoder backend: 'census' (TIGER range interpolation) or 'nominatim'",
    )
    nominatim_base_url: str = Field(
        default="https://nominatim.openstreetmap.org",
        description="Nominatim base URL (self-host in production backfills)",
    )

    # PostgreSQL / PostGIS Database
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_db: str = Field(default="urbansignal")
    postgres_user: str = Field(default="postgres")
    postgres_password: str = Field(default="postgres")

    @property
    def postgres_uri(self) -> str:
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def async_postgres_uri(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    # MinIO / S3 Object Storage
    minio_endpoint: str = Field(default="localhost:9000")
    minio_access_key: str = Field(default="minioadmin")
    minio_secret_key: str = Field(default="minioadmin")
    minio_bucket_features: str = Field(default="urban-signal-features")
    minio_secure: bool = Field(default=False)

    # Uber H3 Spatial Grid Settings
    h3_res_macro: int = Field(default=7, description="H3 Res 7 (~5.16 km²) macro district")
    h3_res_neighborhood: int = Field(default=8, description="H3 Res 8 (~0.74 km²) submarket")
    h3_res_micro: int = Field(default=9, description="H3 Res 9 (~0.10 km²) parcel catalyst")

    # Feature Decay Parameters
    capex_halflife_days: float = Field(default=180.0, description="Half-life in days for exponential CapEx time decay")
    lims_threshold: float = Field(default=85.0, description="Leading Indicator Momentum Score threshold for catalyst alert")

    # Ablation gate for the S1 license flow signals (US-27). Off (default):
    # the pipeline computes the derived move-in/move-out counts as 0 and the
    # enriched record emits 0 defaults — behavior identical to before S1. On:
    # first-seen/closed counts per hex per 90d window are derived, stored in
    # feature_store_h3, and emitted for ablation evaluation. Either way these
    # features never feed the LIMS score (survey standing rule: ablate derived
    # signals before promoting them into LIMS).
    sla_flow_ablation_enabled: bool = Field(
        default=False,
        description="Ablation gate for S1 license move-in/move-out flow signals",
    )

    # ML Inference & Hardware
    onnx_model_dir: str = Field(default="./models_storage")
    onnx_execution_provider: str = Field(default="CPUExecutionProvider")  # CUDAExecutionProvider is an explicit GPU opt-in
    gpu_device_id: int = Field(default=0)

    # Webhook Alert Dispatcher
    webhook_alert_urls: Annotated[list[str], NoDecode] = Field(
        default_factory=list,
        description="Endpoints to dispatch catalyst alerts",
    )

    # ------------------------------------------------------------------ #
    # West-metro registration wave (US-222..US-251): per-city feed endpoints.
    # Each endpoint is referenced by the matching REGISTRY DatasetSpec.
    # ------------------------------------------------------------------ #
    arcgis_rivco_permits_url: str = Field(
        default="https://gis.countyofriverside.us/arcgis_mapping/rest/services/OpenData/General/MapServer/280",
        description="Riverside County Accela permits ArcGIS MapServer URL (inland_empire)",
    )
    arcgis_riverside_crime_url: str = Field(
        default="https://services.arcgis.com/Fu2oOWg1Aw7azh41/arcgis/rest/services/View_CrimesRPD/FeatureServer/4",
        description="City of Riverside PD crime ArcGIS FeatureServer URL (inland_empire)",
    )
    arcgis_stockton_sla_url: str = Field(
        default="https://gisportal.stocktonca.gov/arcgis2/rest/services/OpenCounter/OpenCounterMap/MapServer/7",
        description="Stockton liquor licenses ArcGIS MapServer URL (SLA)",
    )
    boulder_permits_endpoint: str = Field(
        default="https://services.arcgis.com/ePKBjXrBZ2vEEgWd/arcgis/rest/services/Construction_Permits/FeatureServer/0",
        description="Boulder construction permits ArcGIS FeatureServer URL",
    )
    boulder_sla_endpoint: str = Field(
        default="https://gis.bouldercolorado.gov/ags_svr1/rest/services/plan/RentalHousingLicenses/MapServer/0",
        description="Boulder rental housing licenses ArcGIS MapServer URL (SLA)",
    )
    chandler_permits_endpoint: str = Field(
        default="https://gis.chandleraz.gov/portalserver/rest/services/Tolemi/Building_Blocks/MapServer/0",
        description="Chandler building-blelock permits ArcGIS MapServer URL",
    )
    arcgis_modesto_sla_url: str = Field(
        default="https://gis.modestogov.com/hosting/rest/services/ExternalServices/Map_Layer_Service_External/FeatureServer/7",
        description="Modesto business licenses ArcGIS FeatureServer URL (SLA)",
    )
    arcgis_bend_permits_url: str = Field(
        default="https://services5.arcgis.com/JisFYcK2mIVg9ueP/arcgis/rest/services/Permit_Applications_Point/FeatureServer/0",
        description="Bend permit applications ArcGIS FeatureServer URL",
    )
    arcgis_bend_sla_url: str = Field(
        default="https://services5.arcgis.com/JisFYcK2mIVg9ueP/arcgis/rest/services/License_Application_Points_(Business_Registrations)/FeatureServer/0",
        description="Bend business licenses ArcGIS FeatureServer URL (SLA)",
    )
    arcgis_bend_311_url: str = Field(
        default="https://services5.arcgis.com/JisFYcK2mIVg9ueP/arcgis/rest/services/Code_Enforcement_Cases_Polygon_(Public)/FeatureServer/0",
        description="Bend code enforcement cases ArcGIS FeatureServer URL (311)",
    )
    arcgis_bend_crime_url: str = Field(
        default="https://services5.arcgis.com/JisFYcK2mIVg9ueP/arcgis/rest/services/Public_Calls/FeatureServer/0",
        description="Bend public calls for service ArcGIS FeatureServer URL (crime)",
    )
    arcgis_vancouver_wa_permits_url: str = Field(
        default="https://services.arcgis.com/oNvpY90qsPDizwkN/arcgis/rest/services/Permits_and_Code_Enforcement_Data_(public_view)/FeatureServer/0",
        description="Vancouver WA permits ArcGIS FeatureServer URL",
    )
    arcgis_anaheim_permits_url: str = Field(
        default="https://services3.arcgis.com/hPs600I3X0RTaaaq/arcgis/rest/services/Accela_Building_Permits/FeatureServer/0",
        description="Anaheim Accela building permits ArcGIS FeatureServer URL",
    )
    arcgis_anaheim_sla_url: str = Field(
        default="https://services3.arcgis.com/hPs600I3X0RTaaaq/arcgis/rest/services/ActiveBusinessLicenses/FeatureServer/0",
        description="Anaheim active business licenses ArcGIS FeatureServer URL (SLA)",
    )
    socrata_santa_rosa_crime_endpoint: str = Field(
        default="https://data.sonomacounty.ca.gov/resource/3rsj-iche.json",
        description="Sonoma County Sheriff incident data Socrata endpoint (Santa Rosa crime)",
    )
    socrata_oakland_311_endpoint: str = Field(
        default="https://data.oaklandca.gov/resource/quth-gb8e.json",
        description="Oakland 311 service requests Socrata endpoint",
    )
    socrata_oakland_crime_endpoint: str = Field(
        default="https://data.oaklandca.gov/resource/ppgh-7dqv.json",
        description="Oakland OPD CrimeWatch data Socrata endpoint",
    )
    arcgis_nampa_permits_endpoint: str = Field(
        default="https://utility.arcgis.com/usrsvcs/servers/7751a4c516434f1d947c67cd78a4d968/rest/services/Public/PublicRoadClosures/FeatureServer/3",
        description="Nampa ROW road-closure permits ArcGIS FeatureServer URL",
    )
    arcgis_yakima_permits_endpoint: str = Field(
        default="https://gis.yakimawa.gov/arcgis/rest/services/Planning/BuildingPermits/FeatureServer/0",
        description="Yakima building permits ArcGIS FeatureServer URL",
    )
    arcgis_oxnard_ventura_sla_endpoint: str = Field(
        default="https://services.arcgis.com/dBVj4EXO3IdRPOqb/arcgis/rest/services/OpenData_PSI_BusinessLicenses/FeatureServer/0",
        description="Ventura business licenses ArcGIS FeatureServer URL (SLA)",
    )
    arcgis_oxnard_ventura_311_endpoint: str = Field(
        default="https://services.arcgis.com/dBVj4EXO3IdRPOqb/arcgis/rest/services/Graffiti_Responses_Read_Only/FeatureServer/0",
        description="Ventura graffiti-response requests ArcGIS FeatureServer URL (311)",
    )
    arcgis_oxnard_ventura_crime_endpoint: str = Field(
        default="https://services.arcgis.com/dBVj4EXO3IdRPOqb/arcgis/rest/services/OpenData_Police_Crimes/FeatureServer/0",
        description="Ventura police crimes ArcGIS FeatureServer URL",
    )
    arcgis_medford_permits_endpoint: str = Field(
        default="https://maps.medfordmaps.org/arcgis/rest/services/TRAKiTExport/TRAKiTPermits_service/FeatureServer/1",
        description="Medford TRAKiT permits ArcGIS FeatureServer URL",
    )
    arcgis_medford_sla_endpoint: str = Field(
        default="https://maps.medfordmaps.org/arcgis/rest/services/MLI2/MLI_TRAKiT_Service/FeatureServer/14",
        description="Medford TRAKiT business licenses ArcGIS FeatureServer URL (SLA)",
    )
    arcgis_medford_311_endpoint: str = Field(
        default="https://maps.medfordmaps.org/arcgis/rest/services/MLI2/MLI_TRAKiT_Service/FeatureServer/12",
        description="Medford TRAKiT code enforcement cases ArcGIS FeatureServer URL (311)",
    )
    arcgis_tempe_permits_endpoint: str = Field(
        default="https://services.arcgis.com/lQySeXwbBg53XWDi/arcgis/rest/services/building_permits/FeatureServer/0",
        description="Tempe building permits ArcGIS FeatureServer URL",
    )
    arcgis_tempe_complaints_311_endpoint: str = Field(
        default="https://services.arcgis.com/lQySeXwbBg53XWDi/arcgis/rest/services/code_complaints/FeatureServer/0",
        description="Tempe code complaints ArcGIS FeatureServer URL (311)",
    )
    arcgis_tempe_crime_endpoint: str = Field(
        default="https://services.arcgis.com/lQySeXwbBg53XWDi/arcgis/rest/services/General_Offenses_(Open_Data)/FeatureServer/0",
        description="Tempe general offenses ArcGIS FeatureServer URL (crime)",
    )
    arcgis_bozeman_permits_url: str = Field(
        default="https://services3.arcgis.com/f4hk1qcfxRJ0L2BU/arcgis/rest/services/BP_Comm_Dev_Report_Data_view/FeatureServer/0",
        description="Bozeman building permits ArcGIS FeatureServer URL",
    )
    arcgis_bozeman_crime_url: str = Field(
        default="https://gisweb.bozeman.net/hosted/rest/services/BPD_CFS_Public_30_Days/FeatureServer/0",
        description="Bozeman BPD calls-for-service ArcGIS FeatureServer URL (crime)",
    )
    arcgis_missoula_permits_url: str = Field(
        default="https://services.arcgis.com/HfwHS0BxZBQ1E5DY/arcgis/rest/services/AddressesWithPermits_mso/FeatureServer/0",
        description="Missoula address permits ArcGIS FeatureServer URL",
    )
    arcgis_santa_fe_311_url: str = Field(
        default="https://services7.arcgis.com/p0Gk2nDbPs7KEqSZ/arcgis/rest/services/CRM_Report_A_Problem_New_Public/FeatureServer/0",
        description="Santa Fe CRM report-a-problem ArcGIS FeatureServer URL (311)",
    )
    arcgis_eugene_311_url: str = Field(
        default="https://services3.arcgis.com/F7NiRLGNbA2hh7gE/arcgis/rest/services/2020_2021CampingWorkOrders/FeatureServer/0",
        description="Eugene camping work orders ArcGIS FeatureServer URL (311)",
    )
    arcgis_eugene_sla_url: str = Field(
        default="https://services3.arcgis.com/F7NiRLGNbA2hh7gE/arcgis/rest/services/Food_Service_Establishments_Updated_VIEW_CBE/FeatureServer/0",
        description="Eugene food-service establishments ArcGIS FeatureServer URL (SLA)",
    )
    arcgis_eugene_deeds_url: str = Field(
        default="https://services3.arcgis.com/F7NiRLGNbA2hh7gE/arcgis/rest/services/CityLandDeeds/FeatureServer/0",
        description="Eugene city land deeds ArcGIS FeatureServer URL",
    )
    arcgis_glendale_az_311_url: str = Field(
        default="https://gismaps.glendaleaz.com/gisserver/rest/services/OpenData/GLENDALEONE_EXTERNAL_REQUESTS_PTS/MapServer/0",
        description="Glendale GlendaleOne 311 ArcGIS MapServer URL",
    )
    arcgis_glendale_az_sla_url: str = Field(
        default="https://gismaps.glendaleaz.com/gisserver/rest/services/OpenData/Business_Licenses/MapServer/1",
        description="Glendale business licenses ArcGIS MapServer URL (SLA)",
    )
    scottsdale_permits_endpoint: str = Field(
        default="https://maps.scottsdaleaz.gov/arcgis/rest/services/OpenData_Tabular/MapServer/12",
        description="Scottsdale building permits ArcGIS MapServer table URL",
    )
    scottsdale_sla_endpoint: str = Field(
        default="https://maps.scottsdaleaz.gov/arcgis/rest/services/OpenData_Tabular/MapServer/6",
        description="Scottsdale business licenses ArcGIS MapServer table URL (SLA)",
    )
    long_beach_sla_endpoint: str = Field(
        default="https://services6.arcgis.com/yCArG7wGXGyWLqav/arcgis/rest/services/Business_Licenses_Public_View/FeatureServer/0",
        description="Long Beach business licenses ArcGIS FeatureServer URL (SLA)",
    )
    long_beach_crime_endpoint: str = Field(
        default="https://services6.arcgis.com/yCArG7wGXGyWLqav/arcgis/rest/services/Police_Crime_Mapping/FeatureServer/0",
        description="Long Beach police crime mapping ArcGIS FeatureServer URL",
    )
    las_cruces_permits_endpoint: str = Field(
        default="https://maps.las-cruces.org/gis/rest/services/Information_Services/MapServer/1",
        description="Las Cruces building permits ArcGIS MapServer URL",
    )
    las_cruces_busreg_endpoint: str = Field(
        default="https://maps.las-cruces.org/gis/rest/services/Information_Services/MapServer/2",
        description="Las Cruces business registration arcGIS MapServer URL (SLA)",
    )
    billings_permits_url: str = Field(
        default="https://billingsgis.com/arcgis_public/rest/services/ArcOnline_Public/BuildingPermits_CodeViolations_EXT/MapServer/0",
        description="Billings building permits ArcGIS MapServer URL",
    )
    billings_311_url: str = Field(
        default="https://services6.arcgis.com/rCC3yWJa2mjYtKDP/arcgis/rest/services/Requests_public_00e63199176f44b788fd43684476713d/FeatureServer/0",
        description="Billings 311/service requests ArcGIS FeatureServer URL",
    )
    salem_or_permits_endpoint: str = Field(
        default="https://services.arcgis.com/kIA6yS9KDGqZL7U3/arcgis/rest/services/Structure_Permits/FeatureServer/0",
        description="Salem OR structure permits ArcGIS FeatureServer URL",
    )
    salem_or_sla_endpoint: str = Field(
        default="https://services.arcgis.com/kIA6yS9KDGqZL7U3/arcgis/rest/services/Amanda_MultiFamily_Licenses_Data/FeatureServer/0",
        description="Salem OR multi-family enterprise licenses ArcGIS FeatureServer URL (SLA)",
    )

    @field_validator("webhook_alert_urls", mode="before")
    @classmethod
    def parse_webhook_alert_urls(cls, value: object) -> object:
        """Treat an unset secret as an empty destination list."""
        if value is None or (isinstance(value, str) and not value.strip()):
            return []
        if isinstance(value, str):
            return json.loads(value)
        return value

    @model_validator(mode="after")
    def reject_production_placeholder_credentials(self) -> "Settings":
        """Prevent an accidental production deployment with development credentials."""
        if self.app_env.lower() == "production":
            placeholders = {
                "POSTGRES_PASSWORD": self.postgres_password,
                "MINIO_ACCESS_KEY": self.minio_access_key,
                "MINIO_SECRET_KEY": self.minio_secret_key,
            }
            unsafe = [
                name
                for name, value in placeholders.items()
                if value.lower() in {"postgres", "minioadmin", "change-me", "replace-me"}
                or value.lower().startswith(("change_me", "replace_me"))
            ]
            if unsafe:
                names = ", ".join(unsafe)
                raise ValueError(
                    f"Production requires non-placeholder credentials for: {names}"
                )
        return self


settings = Settings()
