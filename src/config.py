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
        default="https://datacatalog.cookcountyil.gov/resource/x5kz-z7if.json",
        description="Cook County / Chicago Property Transfers endpoint",
    )

    # Socrata SODA OpenData APIs (San Francisco & Bay Area)
    socrata_sf_dob_endpoint: str = Field(
        default="https://data.sfgov.org/resource/i98e-46e2.json",
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
        default="https://data.sfgov.org/resource/5cei-gny5.json",
        description="SF Assessor Historical Secured Property endpoint",
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
