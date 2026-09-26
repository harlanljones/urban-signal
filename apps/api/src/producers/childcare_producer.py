"""Childcare licensing ingestion (US-377).

LEAF module — no spine edits.

Four municipal childcare registries (TX HHSC CCL, NY OCFS, NYC DOHMH, DC Child
Development Centers) are household-formation proxies: a new provider opening is
a leading indicator of household formation in a submarket, which is the same
signal shape the business-licensing feeds under ``FeedType.SLA`` carry. They
therefore share ``SLALicensesProducer``'s classify → geocode → H3 path and the
same ``SLALicenseEvent`` shape, and — per the ``ENERGY_BENCHMARK``/``BIKE_PED``
precedent in the interlock gate — the same Kafka topic. They are told apart
downstream by their registered feed and their own inline field map.

Why a subclass rather than a second registration under ``FeedType.SLA``: the
gate requires ``producer_key == feed.value`` and a topic per feed type, and one
city can hold only one ``DatasetSpec`` per feed type. US-377 originally
satisfied that by *replacing* each city's ``datasets.sla`` block, which dropped
nine metros' business-licensing and SNAP retailer feeds. Registering childcare
as its own feed lets a metro carry both.
"""

from __future__ import annotations

from src.producers.sla_licenses_producer import SLALicensesProducer


class ChildcareLicensingProducer(SLALicensesProducer):
    """Parses childcare licensing rows with the ``childcare`` field maps."""

    # A `FeedType` value, held as a string: `city_registry` imports the city
    # modules, which import producers, so resolving it at module scope here is
    # a circular import.
    FEED = "childcare"

    def run_stream(
        self,
        city_id: str = "nyc",
        limit: int = 5000,
        where_clause: str | None = None,
    ) -> int:
        """Stream a city's childcare registry.

        Mirrors the parent helper but resolves the ``childcare`` dataset, so the
        same entry point works for both feeds.
        """
        return super().run_stream(
            city_id=city_id,
            limit=limit,
            where_clause=where_clause,
            feed_type=self.FEED,
        )
