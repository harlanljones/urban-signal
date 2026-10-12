# Urban Signal

Real-time geospatial intelligence and commercial catalyst forecasting for U.S.
metros: municipal feeds flow into H3 hex grids, models score cells, and
precomputed snapshots are published to the edge for the dashboard and product
site to serve.

## Language

### Geography and coverage

**Metro**:
A registered metropolitan jurisdiction with its own feeds and grid (one `CityId`).
_Avoid_: city, market, region (overloaded with the build region)

**Submarket**:
A curated anchor point inside a metro; the smallest unit of LIMS baselines and
the anchor grid coverage interpolates from.
_Avoid_: neighborhood, district, zone

**Urban Anchor**:
A Census urban-area polygon that bounds where urban-detail grid coverage may
exist; the coverage authority for the detail tier.
_Avoid_: urban footprint, metro boundary, coverage box

**Coverage tier**:
A level of grid promise: the national base tier (coarse resolutions, everywhere,
workforce signal) or the urban detail tier (fine resolutions, inside Urban
Anchors, LIMS signal).
_Avoid_: pyramid level, zoom band (that is the display ladder's term)

**Display ladder**:
The continuous zoom-to-resolution mapping across both coverage tiers.
_Avoid_: LOD table, zoom mapping

**LOD (level of detail)**:
One resolution level of a coverage tier's grid.
_Avoid_: zoom level (camera position, not grid resolution)

**Honesty labels**:
How a cell states its provenance: `measured` (from its own feed/model),
`interpolated` (synthesized from the nearest submarket baseline), or null
(outside its anchor — never invented).
_Avoid_: synthetic value (ambiguous between the model's forecast and a synthesized input)

### Publication

**Snapshot**:
One immutable precomputed publication of the grid, catalog, and catalysts.
_Avoid_: export, dump, cache

**Release**:
A content-addressed generation of a snapshot, addressed by content key and
promoted by pointer.
_Avoid_: version (ambiguous with app version), deployment

**Region**:
The unit of build, promotion, and failure isolation in a snapshot: an Urban
Anchor's detail set or a national parent group. A failed region keeps its
previous generation.
_Avoid_: shard (a storage slice, not a build unit), chunk (a transport batch)

**Backfill**:
Filling grid cells from region builds incrementally — spatially (detail beyond
registered metros), on refresh (only changed regions), or historically (past
generations read by content key).
_Avoid_: seed, warm-up, bootstrap

**Golden count**:
The expected cell-count invariant a published tier or region must match;
coverage drift fails promotion instead of shrinking silently.
_Avoid_: expected size, budget (a budget is a cap, not an invariant)
