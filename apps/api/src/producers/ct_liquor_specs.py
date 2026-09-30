"""Connecticut liquor permits for the Hartford, New Haven and Bridgeport ``sla`` feeds.

The three cities read ``data.ct.gov/resource/ngch-56tr`` ("State Licenses and
Credentials"), which holds every credential the Department of Consumer
Protection issues: pharmacists, locksmiths, gas dealers and home-improvement
contractors as well as the Liquor Control Division's permits. Filtered by city
alone (the registration through 2026-09-30), Hartford's feed held 247,564
credentials, most of them individuals, and published each individual's name as
the premises name. The ``sla`` feed exists for licensed premises, so each city
now also filters on ``credentialtype`` to the permits below: 1,546 of Hartford's
rows on 2026-09-30.

The list is every permanent permit for a Connecticut premises that sells,
serves or makes alcohol. Left out: temporary and event permits (``LTA``,
``LTB``, ``LTN``, ``LCO``, ``LSP``, ``LNC``, ``LAU``, ``LFP``, ``LFM``, ``LPG``,
``LTV``), caterers (``LCT``, ``LRC``; they serve at other people's premises),
out-of-state shippers and retailers, wholesalers, warehouses, transporters and
brokers, permits for aircraft, boats and trains (``LIA``, ``LIB``, ``LRR``),
brand-label registrations (``LBD``, 240,164 rows statewide) and filings or
applications (``LIQF``, ``LIQ``). Codes and names were read from the live table
on 2026-09-30 (``$group=credentialtype, credential``).

LEAF data: the registry YAML carries the resulting ``where`` and field map for
each city, and ``tests/unit/test_ct_liquor_permits.py`` pins them to this
module.
"""

CT_LIQUOR_CREDENTIAL_TYPES: tuple[str, ...] = (
    # Served on the premises.
    "LIR",  # restaurant liquor
    "LRW",  # restaurant wine & beer
    "LRB",  # restaurant beer
    "LCA",  # cafe liquor
    "LCR",  # Connecticut craft cafe liquor
    "LCW",  # cafe wine-beer-cider
    "LIT",  # tavern liquor
    "LIH",  # hotel liquor
    "LIC",  # club liquor
    "LPC",  # non-profit club liquor
    "LGC",  # golf country club liquor
    "LBA",  # bowling establishment liquor
    "LBB",  # bowling establishment beer and wine
    "LRF",  # racquetball facility liquor
    "LRS",  # resort liquor
    "LCN",  # casino liquor
    "LCM",  # coliseum liquor
    "LCC",  # coliseum concession beer
    "LAP",  # amphitheater
    "LCS",  # concession
    "LFB",  # special sporting facility bar liquor
    "LFC",  # special sporting facility concession liquor
    "LFG",  # special sporting facility guest liquor
    "LFR",  # special sporting facility restaurant liquor
    "LOL",  # special outing facility liquor
    "LSE",  # outdoor open air liquor
    "LTH",  # non-profit theater liquor
    "LPA",  # non-profit public museum liquor
    "LIU",  # university liquor
    "LUW",  # university beer & wine
    "LUB",  # university beer only
    "LAB",  # airport bar liquor
    "LAT",  # airport restaurant liquor
    "LAC",  # airport airline club liquor
    "LMI",  # military liquor
    # Sold for consumption elsewhere.
    "LIP",  # package store liquor
    "LGB",  # grocery beer
    "LID",  # druggist liquor
    "LWG",  # gift basket retailer
    "LRE",  # religious wine retailer liquor
    # Made on the premises.
    "LMB",  # manufacturer beer
    "LMP",  # manufacturer for beer and brew pub
    "LBP",  # brew pub liquor
    "LML",  # manufacturer liquor
    "LMS",  # manufacturer spirits
    "LMA",  # manufacturer apple brandy
    "LMC",  # manufacturer cider-liquor
    "LMW",  # manufacturer cider-wine-mead
    "LFW",  # farm winery liquor
    "LBF",  # farm brewery liquor
    "LDF",  # farm distillery liquor
    "FWBC",  # Connecticut farm winery, brewery and cidery
    "CGAL",  # Connecticut grown manufacturer for alcoholic liquor
    "LFO",  # off-site farm winery sales and tasting
)

# ``name`` is the permittee, a person on individually held permits, so it is
# never a candidate; ``businessname`` is the holding company (business rows
# only) and ``dba`` the trade name on the door.
CT_LIQUOR_SLA_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["credentialid", "fullcredentialcode"],
    "license_type": ["credential", "credentialtype"],
    "effective_date": ["effectivedate", "issuedate"],
    "expiration_date": ["expirationdate"],
    "address_street": ["address"],
    "zipcode": ["zip"],
    "borough": ["city"],
    "premises_name": ["businessname", "dba"],
    "dba": ["dba", "businessname"],
    "status": ["status"],
}


def ct_liquor_where(city: str) -> str:
    """SoQL filter for one city's liquor permits (``city`` as the table spells it)."""
    codes = ", ".join(f"'{code}'" for code in CT_LIQUOR_CREDENTIAL_TYPES)
    return f"city = '{city}' AND credentialtype IN ({codes})"
