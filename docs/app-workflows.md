<!-- last_verified: 2026-07-08 -->
# App Workflows

User journeys inside Rembg Cutout Studio. The end-to-end story is
**ingest → remove → review → serve**.

## Ingest a single product

- User navigates to `/products/new`
- Enters a SKU (e.g. `SKU-1001`), chooses a category and rembg model (selectors), optionally
  a batch, and picks a product photo (JPEG/PNG/WebP)
- Optionally flips "Remove background now" to run the cutout immediately
- On submit: the original uploads to `products/originals/<sku>/…`, a catalog JSON is written
  as `pending` (or `done` if removed now), and the user lands on the product detail page
- See: [Product Catalog](features/product-catalog.md)

## Ingest in bulk (CSV manifest)

- From `/products`, user clicks "Import CSV"
- Uploads a `sku,category,batch,filename` CSV plus the matching image files
- Each matched row registers a pending product; the dialog reports created/skipped counts
- See: [Batch Ingest](features/batch-ingest.md)

## Remove backgrounds

- **Single**: on a product detail page, click "Remove background" (or "Re-run" to redo with a
  different model). rembg runs locally; a transparent cutout + sidecar are written to B2 and
  the status flips to `done`.
- **Batch**: on `/products`, click "Process all pending" to run rembg across every pending
  product sequentially — demonstrating continuous write amplification.
- If the ML deps aren't installed, the app surfaces a clear 503 with the install command.
- See: [Background Removal](features/background-removal.md)

## Review before/after

- On the product detail page, the original is shown beside the cutout rendered over a
  transparency checkerboard so the removed background reads as transparent
- The sidecar panel shows model, rembg version, processing time, dimensions, foreground
  coverage (an honest proxy, not a confidence score), and alpha-matting
- Edit metadata via a pre-filled dialog (SKU is read-only); delete removes only this SKU's
  objects from B2

## Serve / download

- "Download cutout" fetches a presigned URL and downloads the transparent PNG
- Previews use presigned URLs too; nothing requires the bucket to be public

## View the dashboard

- `/` shows Products, Cutouts produced (+ avg ms), Pending, and Cutout storage with an
  amplification ratio vs. the originals, plus a cutouts-per-day chart and recent cutouts
- See: [Dashboard](features/dashboard.md)

## Browse the whole bucket

- `/files` is the full-bucket explorer (tree view, preview, download, delete) — the reusable
  B2 scaffolding, complementing the `products/`-scoped Catalog
- `/upload` is the generic B2 upload surface
- See: [File Browser](features/file-browser.md), [File Upload](features/file-upload.md)
