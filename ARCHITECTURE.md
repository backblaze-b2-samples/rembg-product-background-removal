<!-- last_verified: 2026-07-08 -->
# Architecture

**Rembg Cutout Studio** is a batch product-image background-removal pipeline. Originals land
in Backblaze B2; the app runs rembg (U²-Net) **locally** to produce a transparent cutout +
sidecar per SKU, written back to B2. There is **no database** — the B2 object layout plus a
per-SKU catalog JSON is the system of record.

## Components

- **apps/web/** — Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  - Catalog (`/products`) — the primary-entity explorer: table, create/edit form, detail with
    before/after cutout viewer, per-product and batch removal, CSV import
  - Domain dashboard — products, cutouts produced, pending, storage vs. amplification,
    cutouts-per-day chart, recent cutouts
  - Bucket explorer (`/files`) and generic Upload (`/upload`) — reusable B2 scaffolding
  - Dark mode via `next-themes`
- **services/api/** — FastAPI backend (layered architecture)
  - `service/removal.py` — rembg/U²-Net engine wrapper, **lazy-imports** the ML stack
    (`requirements-ml.txt`); CPU-default / GPU-autodetect; computes a foreground-coverage proxy
  - `service/catalog*.py` + `runtime/catalog.py` — product lifecycle (create/read/edit/delete/
    run/import) + dashboard stats over the B2 object layout
  - Generic file upload/listing/deletion, metadata extraction (images, PDFs)
  - B2 S3 integration via boto3 (repo layer only)
  - Health check, structured JSON logging, Prometheus-format metrics
- **packages/shared/** — TypeScript type definitions
  - Mirrors Pydantic models from the API (Product, ProductDetail, RemovalSidecar, CatalogStats, …)
  - Consumed by `apps/web/` as workspace dependency

## B2 object layout (system of record)

```
products/originals/<sku>/<filename>    original product image (feeds rembg)
products/cutouts/<sku>/<stem>.png      transparent cutout
products/cutouts/<sku>/<stem>.json     sidecar (model, rembg_version, processing_ms, w/h,
                                        foreground_ratio, alpha_matting, created_at)
products/catalog/<sku>.json            per-SKU manifest (editable metadata + status)
```

Status is **derived**: a SKU is `done` once its cutout PNG exists, else `pending`.
`foreground_ratio` is an honest alpha-coverage proxy, not a model confidence score.

## Backend Layering

The API follows a strict layered architecture:

```
types/     Pydantic models — no logic, no imports from other layers
  |
config/    Settings (pydantic-settings) — depends only on types
  |
repo/      Data access (boto3 B2 client) — no business logic
  |
service/   Business logic — calls repo, returns types
  |
runtime/   FastAPI routes — calls service, never repo directly
```

### Layering Rules

1. Dependencies flow downward only: `types` -> `config` -> `repo` -> `service` -> `runtime`
2. No backward imports (e.g., service must not import from runtime)
3. `boto3` only allowed in `repo/` layer
4. All boundary data uses Pydantic models (no raw dicts across layers)
5. Each file stays under 300 lines

### Directory Structure

```
services/api/
  main.py                  App entrypoint, middleware, router registration
  requirements.txt         Core API deps (no rembg)
  requirements-ml.txt      Heavy ML deps (rembg, onnxruntime) — installed separately
  app/
    types/                 Pydantic models (Product, RemovalSidecar, CatalogStats, files, …)
    config/                Settings loaded from environment (derives S3 endpoint from region)
    repo/                  B2 S3 client (data access layer): bytes + prefix helpers
    service/               Business logic: removal (rembg), catalog, catalog_stats, files, metadata
    runtime/               FastAPI route handlers (catalog, files, upload, health, metrics)
  tests/                   pytest tests (structural + integration; rembg mocked)
```

### rembg data flow (marquee feature)

```
run: POST /products/{sku}/remove
  runtime/catalog.py -> service/catalog.run_removal(sku)
    -> repo.get_object_bytes(original_key)          # read original from B2
    -> service/removal.remove_background_bytes(...)  # lazy-import rembg, U²-Net session
    -> repo.put_bytes(cutout .png, sidecar .json)    # write cutout + sidecar to B2
    -> write updated catalog JSON (status = done)
```

`service/removal.py` selects onnxruntime execution providers at runtime (CUDA if available,
else CPU; CoreML opt-in via `REMBG_PROVIDERS`) and caches one session per (model, providers).
If the ML deps are missing it raises `RembgNotInstalledError` → the router returns a clean 503.

## Boundary Invariants

- **No external SDK leakage**: `boto3` is only imported in `app/repo/`. All other layers interact with B2 through the repo interface.
- **No raw dicts at boundaries**: All data crossing layer boundaries uses typed Pydantic models.
- **No mutable globals**: Configuration is read-only after init. No module-level mutable state shared between layers.
- **Validated inputs**: All HTTP inputs validated by FastAPI/Pydantic. All file keys validated against prefix allowlist.

## Deployment

- **Local dev** — `pnpm dev` runs both services via `concurrently`
  - Web: `localhost:3000`
  - API: `localhost:8000`
- **Railway** — two services from the same repo
  - See `infra/railway/README.md` for configuration

## Data Stores

- **Backblaze B2** — object storage (S3-compatible API)
  - Originals, cutouts, sidecars, per-SKU catalog JSON, generic uploads — all in one bucket
  - Catalog listing derived from `products/catalog/*.json` merged with cutout presence
  - S3 endpoint is **derived from `B2_REGION`** (`https://s3.<region>.backblazeb2.com`); no
    hardcoded region in source. `region_name` is passed to boto3.
  - No application database — B2 is the sole data store

## External Services

- **Backblaze B2 S3 API** — file storage, retrieval, deletion, presigned URLs

## Trust Boundaries

See [docs/SECURITY.md](docs/SECURITY.md) for full security documentation.

- **Frontend -> API** — CORS-restricted to configured origins. `CORSMiddleware` is registered LAST in `main.py` (outermost) so it wraps **every** response, including uncaught-exception 500s — otherwise the browser would block error responses and the UI would only see an opaque "network error". See [docs/RELIABILITY.md](docs/RELIABILITY.md#error-handling).
- **API -> B2** — authenticated via application keys, signature v4
- **Client -> B2** — presigned URLs for download (10-min expiry, forced attachment)

## Data Flows

- **Create product**: Browser -> `POST /products` (multipart) -> service validates SKU/category/model -> repo writes original + catalog JSON (`pending`) -> optional immediate removal
- **Run removal**: Browser -> `POST /products/{sku}/remove` -> service reads original from B2 -> rembg -> writes cutout + sidecar -> catalog status `done` (see rembg data flow above)
- **Batch removal**: `POST /products/remove-pending` -> iterate pending catalog JSONs -> run removal each
- **CSV import**: `POST /products/import` (multipart CSV + images) -> match rows to files -> create pending products
- **List / detail**: `GET /products`, `GET /products/{sku}` -> merge catalog JSON with cutout presence + presigned URLs
- **Edit / delete**: `PATCH /products/{sku}` (metadata; SKU immutable) / `DELETE /products/{sku}` (scoped to the SKU's prefixes only)
- **Generic files**: upload / list / download (presigned) / delete via `/upload` and `/files`

## Observability

- Structured JSON logging on all requests with `request_id`
- Request timing middleware (logs duration per request; also the catch-all that converts uncaught exceptions to a typed JSON 500)
- `/metrics` endpoint (Prometheus format: request count, latency, upload count)
- `/health` endpoint (B2 connectivity check)

## Canonical Files

- rembg engine wrapper: `services/api/app/service/removal.py`
- Catalog lifecycle: `services/api/app/service/catalog.py` (+ `catalog_paths.py`, `catalog_stats.py`)
- Catalog router: `services/api/app/runtime/catalog.py`
- B2 data access (repo layer): `services/api/app/repo/b2_client.py`
- Pydantic models: `services/api/app/types/` (`products.py`, `files.py`, `upload.py`, `stats.py`, `formatting.py`)
- Config (pydantic-settings): `services/api/app/config/settings.py`
- Structural tests: `services/api/tests/test_structure.py`
- Frontend API client: `apps/web/src/lib/api-client.ts`
- Catalog UI: `apps/web/src/components/catalog/` and `apps/web/src/app/products/`
- Shared TypeScript types: `packages/shared/src/types.ts`

## Core Features

- [Background Removal](docs/features/background-removal.md)
- [Product Catalog](docs/features/product-catalog.md)
- [Batch Ingest](docs/features/batch-ingest.md)
- [Dashboard](docs/features/dashboard.md)
- [File Upload](docs/features/file-upload.md)
- [File Browser](docs/features/file-browser.md)
- [Metadata Extraction](docs/features/metadata-extraction.md)

## References

- [docs/SECURITY.md](docs/SECURITY.md) — security principles and implementation
- [docs/RELIABILITY.md](docs/RELIABILITY.md) — reliability expectations
- [AGENTS.md](AGENTS.md) — architectural invariants and agent instructions
