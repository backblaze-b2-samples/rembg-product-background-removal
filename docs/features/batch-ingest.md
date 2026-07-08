<!-- last_verified: 2026-07-08 -->
# Feature: Batch Ingest (CSV manifest)

## Purpose
Onboard many SKUs at once — the "tens of thousands of images at ingest" story — by uploading a
CSV manifest plus a set of image files.

## Used By
- UI: `/products` → "Import CSV" dialog (`components/catalog/csv-import.tsx`)
- API: `POST /products/import` (multipart)

## Core Functions
- `services/api/app/service/catalog.py::import_csv`
- `apps/web/src/components/catalog/csv-import.tsx`
- `apps/web/src/lib/queries.ts::useImportProducts`

## Canonical Files
- Import logic: `services/api/app/service/catalog.py::import_csv`

## Inputs
- `manifest`: a CSV file with header `sku,category,batch,filename`
- `files`: one or more image files (JPEG/PNG/WebP) whose names match the manifest `filename`

## Outputs
- One pending product per matched row: original uploaded to `products/originals/<sku>/`,
  catalog JSON written with `status: pending`
- Response: `ImportResult { created, skipped, rows[] }` — per-row `created` / `skipped(+reason)`

## Flow
- Parse the CSV (UTF-8, BOM-tolerant)
- For each row: validate `sku` + `filename`; find the matching uploaded image
- Create the product (category falls back to `Other` if unknown; model defaults to `u2net`)
- Report per-row outcome; run "Process all pending" afterwards to cut them out

## Edge Cases
- Missing `sku` or `filename` → row skipped ("missing sku or filename")
- No uploaded file matching `filename` → row skipped ("no uploaded file named …")
- Duplicate SKU (already exists) → row skipped (409 surfaced as a skip reason)
- Unknown category → coerced to `Other`

## UX States
- Dialog: choose CSV + images; disabled Import until a manifest is selected; toast summary on done

## Verification
- Test files: `services/api/tests/test_catalog.py::test_import_csv`
- Required cases: created row, skipped-missing-file row, per-row status map
- Quick verify command: `pnpm test:api`
- Pass criteria: import reports correct created/skipped counts; pending products appear in the list

## Related Docs
- [Product Catalog](product-catalog.md)
- [Background Removal](background-removal.md)
- [App Workflows](../app-workflows.md)
