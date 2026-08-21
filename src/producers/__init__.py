"""Data producers and Socrata ingestion stream adapters."""

from src.producers.base_producer import BaseKafkaProducer
from src.producers.complaints_311_producer import Complaints311Producer
from src.producers.deeds_acris_producer import DeedsACRISProducer
from src.producers.dob_permits_producer import DOBPermitsProducer
from src.producers.scheduler import (
    DeduplicationFilter,
    JobConfig,
    JobMetrics,
    MunicipalIngestionScheduler,
)
from src.producers.sla_licenses_producer import SLALicensesProducer
from src.producers.socrata_client import SocrataClient

__all__ = [
    "SocrataClient",
    "BaseKafkaProducer",
    "DOBPermitsProducer",
    "Complaints311Producer",
    "SLALicensesProducer",
    "DeedsACRISProducer",
    "MunicipalIngestionScheduler",
    "JobConfig",
    "JobMetrics",
    "DeduplicationFilter",
]
