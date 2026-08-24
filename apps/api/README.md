# Urban Signal API

The Python core lives in this Turborepo application. The package namespace remains
`src` for compatibility with existing service entry points and imports.

The dashboard HTML is served by `src/serving/dashboard.py`. When dashboard behavior
changes, export the synchronized Worker asset with:

```bash
python scripts/export_dashboard.py
```

The current dashboard supports all seventeen registered metros and a comparison mode
for layering multiple regions in one MapLibre viewport. See
[`docs/dashboard.md`](../../docs/dashboard.md) for the interaction contract,
snapshot endpoints, and screenshot evidence.
