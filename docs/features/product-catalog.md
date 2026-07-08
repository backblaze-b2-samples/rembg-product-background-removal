<!-- last_verified: 2026-07-08 -->
# Feature: Product Catalog (primary entity)

## Purpose
Manage the lifecycle of the primary entity — a **Product** (SKU + original image + optional
cutout/sidecar + editable metadata) — with no database: the B2 object layout plus a per-SKU
catalog JSON is the source of truth.

## Used By
- UI: `/products` (list), `/products/new` (create), `/products/[sku]` (detail: before/after,
  edit dialog, delete, download)
- API: `GET /products`, `POST /products`, `GET /products/{sku}`, `PATCH /products/{sku}`,
  `DELETE /products/{sku}`, `POST /products/{sku}/remove`

## Core Functions
- `services/api/app/service/catalog.py` — list/get/create/update/delete/run
- `services/api/app/service/catalog_paths.py` — B2 key layout, validation, JSON I/O
- `services/api/app/runtime/catalog.py` — router (no business logic)
- `apps/web/src/components/catalog/` — `product-table`, `product-form`, `product-detail`,
  `remove-button`
- `apps/web/src/lib/queries.ts` — `useProducts`, `useProduct`, `useCreateProduct`,
  `useUpdateProduct`, `useDeleteProduct`, `useRunRemoval`

## Canonical Files
- Lifecycle service: `services/api/app/service/catalog.py`
- Form exemplar: `apps/web/src/components/catalog/product-form.tsx`

## Lifecycle (all five verbs are built and exposed)
| Verb | UI | Behavior |
|------|----|----------|
| create | `/products/new` form | validate SKU, upload original to `products/originals/<sku>/`, write catalog JSON (`pending`); optional "Remove background now" |
| read | list + detail | before/after + sidecar + derived status |
| edit | pre-filled dialog on detail | update category / batch / model / alpha_matting; **SKU read-only** (it is the B2 key) |
| delete | detail | scoped delete of only the SKU's `originals/`, `cutouts/`, `catalog/` keys |
| run | detail / list batch | run rembg → write cutout + sidecar; re-runnable with a different model |

## Form UX conventions
- Finite fields use selectors: `category` (7 options), `model` (5 rembg models) → `Select`;
  `alpha_matting` → `Switch`. Free-text: `sku` (pattern `^[A-Za-z0-9._-]+$`), `batch`.
- Create form shows safe-default hints (placeholders / descriptions, no autofill button):
  SKU `SKU-1001`, category defaults to Apparel, model defaults to `u2net (general purpose)`,
  batch `2026-summer`, and a note that a safe test run = one JPEG/PNG, model `u2net`,
  alpha-matting off.
- Edit form opens pre-filled with the product's real values; SKU is read-only; no hints.

## Inputs
- create (multipart): `file`, `sku`, `category`, `batch?`, `model`, `alpha_matting`, `remove_now`
- update (JSON): `category?`, `batch?`, `model?`, `alpha_matting?`

## Outputs
- `Product` / `ProductDetail` (with presigned `original_url`, `cutout_url`, `thumbnail_url`,
  and the sidecar when a cutout exists)
- Side effects: B2 writes/deletes scoped to the SKU's prefixes

## Edge Cases
- Invalid SKU / category / model → 400
- Unsupported image type (not JPEG/PNG/WebP) → 415
- Duplicate SKU → 409
- Missing product → 404
- Delete is always prefix-scoped — never a bucket-wide wipe

## UX States
- List: loading skeleton / error+retry / empty ("No products yet") / populated table
- Detail: loading / error / before/after with sidecar panel

## Verification
- Test files: `services/api/tests/test_catalog.py`
- Required cases: create+read, bad SKU/category/type, duplicate 409, list, update, scoped
  delete, run writes cutout+sidecar
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm build && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all tests green; every verb reachable from the UI

## Related Docs
- [Background Removal](background-removal.md)
- [Batch Ingest](batch-ingest.md)
- [App Workflows](../app-workflows.md)
