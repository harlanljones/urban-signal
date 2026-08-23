"""Configuration module using Pydantic Settings for Urban Signal."""

from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    kafka_sasl_mechanism: Optional[str] = None
    kafka_sasl_username: Optional[str] = None
    kafka_sasl_password: Optional[str] = None

    # Kafka Topic Definitions
    topic_permits: str = Field(default="raw.municipal.permits")
    topic_311: str = Field(default="raw.municipal.311")
    topic_sla: str = Field(default="raw.municipal.sla")
    topic_deeds: str = Field(default="raw.municipal.deeds")
    topic_enriched_h3: str = Field(default="enriched.spatial.h3")
    topic_catalyst_alerts: str = Field(default="alerts.catalyst")
    topic_dlq: str = Field(default="dlq.schema.failures")

    # Consumer Group Configurations
    cg_h3_enrichment: str = Field(default="h3-enrich-workers")
    cg_complaints: str = Field(default="spatial-complaint-grp")
    cg_hospitality: str = Field(default="hospitality-grp")
    cg_deeds: str = Field(default="deed-financial-grp")
    cg_inference: str = Field(default="ml-inference-workers")
    cg_alerts: str = Field(default="webhook-dispatchers")

    # Socrata SODA OpenData APIs (NYC Defaults)
    socrata_app_token: Optional[str] = Field(default=None, description="Socrata App Token for high rate limits")
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

    # PostgreSQL / PostGIS Database
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_db: str = Field(default="urbandev")
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
    minio_bucket_features: str = Field(default="urban-features")
    minio_secure: bool = Field(default=False)

    # Uber H3 Spatial Grid Settings
    h3_res_macro: int = Field(default=7, description="H3 Res 7 (~5.16 km²) macro district")
    h3_res_neighborhood: int = Field(default=8, description="H3 Res 8 (~0.74 km²) submarket")
    h3_res_micro: int = Field(default=9, description="H3 Res 9 (~0.10 km²) parcel catalyst")

    # Feature Decay Parameters
    capex_halflife_days: float = Field(default=180.0, description="Half-life in days for exponential CapEx time decay")
    lims_threshold: float = Field(default=85.0, description="Leading Indicator Momentum Score threshold for catalyst alert")

    # ML Inference & Hardware
    onnx_model_dir: str = Field(default="./models_storage")
    onnx_execution_provider: str = Field(default="CUDAExecutionProvider")  # or CPUExecutionProvider
    gpu_device_id: int = Field(default=0)

    # Webhook Alert Dispatcher
    webhook_alert_urls: List[str] = Field(default_factory=list, description="Endpoints to dispatch catalyst alerts")


settings = Settings()
