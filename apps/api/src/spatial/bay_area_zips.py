"""Bay Area ZIP-prefix membership (US-440).

Redfin's ZIP tracker and Zillow's ZHVI/ZORI files are national; both the
Redfin ingest and the ZCTA-to-H3 join need one shared, testable definition of
"is this ZIP in scope" rather than each re-deriving it. The nine-county Bay
Area is covered by these 3-digit ZIP prefixes (San Francisco, San Mateo,
Santa Clara, Alameda, Contra Costa, Marin, Napa, Sonoma, Solano counties):

    940xx  San Francisco / Marin
    941xx  San Francisco (PO boxes / unique ZIPs)
    942xx  San Francisco (PO boxes / government)
    943xx  Peninsula (San Mateo county)
    944xx  Peninsula / South SF
    945xx  East Bay (Richmond / San Rafael / Contra Costa)
    946xx  East Bay (Oakland / Alameda)
    947xx  East Bay (Berkeley / Alameda)
    948xx  East Bay (Contra Costa: Concord, Richmond)
    949xx  Marin / North Bay
    950xx  Napa / Solano / North Bay
    951xx  Santa Clara (San Jose)
    953xx  Santa Clara (South county: Gilroy, Morgan Hill)
    954xx  Sonoma / Napa
    955xx  Solano / Napa (Vallejo, Fairfield)

**Deviation from the ticket's literal list.** US-440 enumerates "940xx, 941xx,
943xx, 944xx, 945xx, 947xx, 948xx, 949xx, 950xx, 951xx, 953xx, 954xx, 955xx" —
omitting 942xx and, more materially, 946xx. 946xx is Oakland/Alameda (Oakland
Downtown is already a registered submarket in ``cities/san_francisco.py`` at
37.8044/-122.2711, which resolves to a 946xx ZIP); dropping it would silently
exclude the East Bay's largest city from "all Bay Area ZIPs" ingestion. Both
prefixes are added here; see PR_DESCRIPTION.md for the full note.

This is a coarse ZIP-prefix filter, not a boundary — it is only used to keep
national feeds to a scannable Bay Area slice before the ZCTA polygon join
does the real geography.
"""

from __future__ import annotations

BAY_AREA_ZIP_PREFIXES: tuple[str, ...] = (
    "940",
    "941",
    "942",
    "943",
    "944",
    "945",
    "946",
    "947",
    "948",
    "949",
    "950",
    "951",
    "953",
    "954",
    "955",
)


def normalize_zip(value: object) -> str:
    """Coerce a ZIP-ish value to a bare 5-digit string, or "" if it isn't one.

    Handles Redfin's ``"Zip Code: 94104"`` region labels, floats from a badly
    typed spreadsheet (``94104.0``), and ZIP+4 (``94104-1234``).
    """
    text = str(value or "").strip()
    if not text:
        return ""
    if ":" in text:
        text = text.rsplit(":", 1)[-1].strip()
    text = text.split("-")[0].strip()
    text = text.removesuffix(".0")
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) < 5:
        return ""
    digits = digits[:5].zfill(5)
    return digits


def is_bay_area_zip(value: object) -> bool:
    """True if a ZIP/ZCTA falls under a registered Bay Area 3-digit prefix."""
    zcta = normalize_zip(value)
    if not zcta:
        return False
    return zcta[:3] in BAY_AREA_ZIP_PREFIXES
