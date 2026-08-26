"""Configuration module using Pydantic Settings for Urban Signal."""

import json
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
    topic_street_cut: str = Field(default="raw.municipal.street_cut", description="Street-cut/utility permit records topic")
    topic_evictions: str = Field(default="raw.municipal.evictions", description="Eviction filings/executions topic")
    topic_str: str = Field(default="raw.municipal.str", description="Short-term rental registrations topic")
    topic_enriched_h3: str = Field(default="enriched.spatial.h3")
    topic_catalyst_alerts: str = Field(default="alerts.catalyst")
    topic_dlq: str = Field(default="dlq.schema.failures")

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
    # Chicago CDOT street closures (native coordinates) is the registered feed;
    # NYC's DOT street-construction permits (tqtj-sjs8) stay deferred — current
    # rows are address-only.
    socrata_chicago_street_cut_endpoint: str = Field(
        default="https://data.cityofchicago.org/resource/jdis-5sry.json",
        description="Chicago CDOT street closures endpoint",
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

    # Austin (Socrata) — partial city: SLA/DEEDS absent (TABC statewide feeds
    # carry no geocodes; Travis County portal is unreachable)
    socrata_austin_permits_endpoint: str = Field(
        default="https://data.austintexas.gov/resource/quv8-5ckq.json",
        description="Austin Issued Building Permits endpoint",
    )
    socrata_austin_311_endpoint: str = Field(
        default="https://data.austintexas.gov/resource/xwdj-i9he.json",
        description="Austin 311 Public Data endpoint",
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
            "(not ingested: gpsx/gpsy are State Plane meters, fails G5)"
        ),
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

    # Kansas City, MO (Socrata): Business License Holders (US-134). Snapshot
    # feed carrying native GeoJSON point geometry (96.4% non-null) and a
    # valid_license_for YYYYMMDD expiration column; publication had lapsed
    # ~7mo at registration, hence the 90-day cadence.
    socrata_kansas_city_licenses_endpoint: str = Field(
        default="https://data.kcmo.org/resource/pnm4-68wg.json",
        description="Kansas City Business License Holders endpoint",
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
