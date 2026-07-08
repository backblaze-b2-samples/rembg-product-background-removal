<!-- last_verified: 2026-07-08 -->
# Feature: Dashboard

## Purpose
Give an at-a-glance overview of the background-removal catalog: how many products exist, how
many cutouts have been produced, how many are pending, and how much extra storage the cutouts
add on B2 (write amplification).

## Used By
- UI: `/` page (dashboard home)
- API: `GET /products/stats`, `GET /products/stats/activity`, `GET /products`

## Core Functions
- `apps/web/src/components/dashboard/catalog-stats-cards.tsx` — 4 stat cards
- `apps/web/src/components/dashboard/cutout-chart.tsx` — bar chart of cutouts produced per day
- `apps/web/src/components/dashboard/recent-cutouts-table.tsx` — most recent cutouts
- `apps/web/src/lib/api-client.ts` — `getCatalogStats()`, `getCutoutActivity()`, `getProducts()`
- `services/api/app/runtime/catalog.py` — `GET /products/stats` handler
- `services/api/app/service/catalog_stats.py` — `get_catalog_stats()`, `get_cutout_activity()`

## Canonical Files
- Stats cards: `apps/web/src/components/dashboard/catalog-stats-cards.tsx`
- Stats service logic: `services/api/app/service/catalog_stats.py`

## Inputs
- None (dashboard loads data automatically)

## Outputs
- `GET /products/stats` → `CatalogStats` (total_products, cutouts_produced, pending,
  originals_bytes/human, cutouts_bytes/human, amplification_ratio, avg_processing_ms)
- `GET /products/stats/activity?days=7` → `DailyCutoutCount[]` for the chart
- `GET /products` → `Product[]` filtered to `done` for the recent-cutouts table

## Flow
- Page loads → parallel API calls (catalog stats, cutout activity, products)
- Stat cards show Products, Cutouts produced (+ avg ms), Pending, and Cutout storage
  (with `orig <size> · <ratio>× total` amplification hint)
- Chart shows cutouts produced per day for the last 7 days
- Recent cutouts table lists the newest `done` products (SKU, category, model, updated)

## Edge Cases
- API unavailable → error states with retry; the chart does not show a false zero while loading
- No products / no cutouts → empty chart + empty table messages
- Large catalog → stats paginate through all objects using `ContinuationToken`

## UX States
- Loading: skeleton placeholders for cards, chart, and table
- Empty: "No cutouts yet" / "No products yet"
- Loaded: populated cards, chart, table

## Verification
- Test files: `services/api/tests/test_catalog.py` (`test_catalog_stats_amplification`)
- Required cases: stats with cutouts, empty catalog, amplification math
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green, no ruff violations

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [App Workflows](../app-workflows.md)
