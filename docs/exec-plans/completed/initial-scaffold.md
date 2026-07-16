# Build plan — `rembg-product-background-removal`

Source of truth: `.claude/scratch/vcsk-9f45528c-eb49-4f45-8004-bb7ef5259b36/` (fresh clone of
vibe-coding-starter-kit). All keep/trim/add deltas are computed against that tree.

---

## 1. Purpose

`rembg-product-background-removal` is a self-hosted, batch **product-image background-removal**
pipeline for e-commerce catalog managers, print-on-demand platforms, and marketplace sellers who
process tens of thousands of product photos and need clean, transparent cutouts for
white-background listings, compositing, and marketing assets. Original product images land in
Backblaze B2; the app runs the open-source **rembg** (U²-Net family) library **locally** — no paid
API, no second key — to produce a matched transparent-PNG cutout per image, writing the cutout plus
a metadata sidecar back to B2. Every original generates a comparably-sized cutout, so stored volume
roughly doubles as SKUs are onboarded — the sample makes that write-amplification visible on the
dashboard. B2 is both the ingest landing zone and the durable system of record (originals, cutouts,
sidecars, and a per-SKU catalog manifest all live as B2 objects, browsable from the app).

**Primary entity:** a **Product** — an SKU-keyed record consisting of one original product image,
its (optional) derived cutout + sidecar, and editable metadata (category, batch, chosen model,
status). State is derived from B2 object layout + a per-SKU catalog JSON; there is no database.

---

## 2. Architecture delta from vibe-coding-starter-kit

The starter kit is the ceiling. Strip what an image-cutout catalog doesn't need; keep the reusable
B2 scaffolding; add the removal engine + catalog surface.

### KEEP (as-is — do not strip/rewrite)
- **UI kit & design system** — `apps/web/src/components/ui/`, tokens in `app/globals.css`, the
  `/design` reference page. Build all new screens from these primitives.
- **Bucket explorer (NON-NEGOTIABLE keep)** — `/files` route, `app/files/`, `components/files/`,
  and its sidebar entry. Full-bucket browse stays exactly as-is.
- **Upload** — `/upload` route, `app/upload/`, `components/upload/`, sidebar entry. Generic B2
  upload surface stays.
- **Settings** — `/settings` + `components/settings/` (settings-form is the form-UX exemplar; keep,
  light copy edits only).
- **Backend layered architecture** — `types → config → repo → service → runtime`, structural tests
  (`tests/test_structure.py`), `/health`, `/metrics`, JSON logging, CORS/error middleware, the
  TanStack Query data layer (`lib/queries.ts`, `lib/api-client.ts`) and its "new endpoint touches
  three files" rule, `scripts/doctor.mjs` preflight, `scripts/dev.sh`, `scripts/pick-port.mjs`.
- **Generic metadata extraction** — `service/metadata.py` + `components/files/file-metadata-panel.tsx`
  (MD5/SHA-256, image dims/EXIF) stays; it serves the generic upload/files surface. (Not the same as
  the cutout sidecar, which is purpose-built — see ADD.)
- **Agent-first docs skeleton** — AGENTS.md / ARCHITECTURE.md / docs structure, `_template.md`,
  `docs/exec-plans/{active,completed}/` (contents reset — see TRIM/Docs).

### TRIM (remove from starter)
- **Starter marketing screenshots** — `docs/images/b2-starterkit-dashboard1.png`,
  `docs/images/b2-starterkit-fileview2.png`, and the README "What it looks like" image block.
  Screenshots are produced by a later pipeline step (`sample-4-screenshot`); this step creates no
  binary assets.
- **Starter-specific completed exec-plans** — `docs/exec-plans/completed/2026-02-*.md` (download-count,
  preserve-filenames, initialization, etc.). They are the starter's history, not this sample's. Reset
  `docs/exec-plans/tech-debt-tracker.md` to an empty tracker; keep `active/.gitkeep`.
- **CODE_REVIEW.md** — starter-authoring artifact, not part of a shipped sample. Remove.
- No structural code is trimmed. The dashboard default components are **adapted**, not trimmed.

### ADD (new for this sample)
**Backend (`services/api/app/`)**
- `service/removal.py` — the marquee engine wrapper. **Lazy-imports `rembg`** inside functions (so
  the core API installs/tests without the heavy ML deps). Fetches the original bytes from B2 (via
  repo), runs `rembg` with a selected model + optional alpha-matting, computes a foreground-coverage
  metric, times the run, and returns cutout PNG bytes + a sidecar dict. Single + batch entry points.
  **CPU default / GPU autodetect** (see §4, Feature 1). If `rembg` is not installed, the run path
  surfaces a clean 503 ("ML deps not installed — `pip install -r requirements-ml.txt`").
- `service/catalog.py` — product lifecycle logic: list products (from per-SKU catalog JSONs, merged
  with cutout/sidecar presence → status), get product detail, create (register + validate),
  edit (category/batch/model), delete (scoped to the SKU's prefixes), CSV-manifest import, and
  `get_catalog_stats()` (totals, pending, originals-vs-cutouts bytes + amplification ratio, avg
  processing ms).
- `repo/b2_client.py` — extend (boto3 stays repo-only): `get_object_bytes(key)`, `put_bytes(key,
  data, content_type)` (cutout PNG + sidecar JSON + catalog JSON), `list_prefix(prefix)`,
  `delete_prefix(prefix)` (scoped, paginated). Reuse existing helpers where possible.
- `runtime/catalog.py` — router: `GET /products`, `POST /products` (create), `GET /products/{sku}`,
  `PATCH /products/{sku}` (edit), `DELETE /products/{sku}`, `POST /products/{sku}/remove` (run),
  `POST /products/remove-pending` (batch run), `POST /products/import` (CSV manifest),
  `GET /products/stats`. No business logic in handlers.
- `types/` — Pydantic models: `Product`, `ProductDetail`, `RemovalResult`, `CatalogStats`,
  `ImportResult`. Keep files < 300 lines.
- Tests: `tests/test_catalog.py`, `tests/test_removal.py` (rembg mocked/lazy so tests need no ML
  deps), update `conftest.py` + existing fixtures for the renamed env vars (§3). `test_structure.py`
  must stay green (rembg import isolated to `service/removal.py`; boto3 still repo-only).

**B2 object layout (the durable "database")**
- `products/originals/<sku>/<filename>` — original product image.
- `products/cutouts/<sku>/<filename>.png` — transparent cutout.
- `products/cutouts/<sku>/<filename>.json` — sidecar: `{ model, rembg_version, processing_ms, width,
  height, foreground_ratio, alpha_matting, created_at }`. `foreground_ratio` = fraction of pixels
  with alpha above threshold — an honest **coverage proxy**, documented as such (rembg emits no true
  confidence score; do not fabricate one).
- `products/catalog/<sku>.json` — per-SKU manifest: `{ sku, category, batch, original_filename,
  original_key, model, alpha_matting, status, created_at, updated_at }`. Source of truth for editable
  metadata + status.

**Frontend (`apps/web/src/`)**
- `app/products/page.tsx` — **Catalog** = the sample-specific asset explorer scoped to `products/`
  (see §"Non-negotiable" note): a table of products (SKU, category, batch, status, thumbnail),
  a "Process all pending" batch button, and a CSV-import entry. This is the scoped complement to the
  full-bucket `/files` explorer.
- `app/products/new/page.tsx` — create form (§4 form-UX).
- `app/products/[sku]/page.tsx` — product detail: **before/after** (original vs cutout rendered over
  a checkerboard so transparency is visible), sidecar metadata, and the lifecycle actions
  (Remove background / Re-run, Edit, Delete, Download cutout).
- `components/catalog/` — `product-table.tsx`, `product-form.tsx` (create + edit), `product-detail.tsx`
  (before/after viewer), `remove-button.tsx`, `batch-process.tsx`, `csv-import.tsx`.
- `lib/queries.ts` + `lib/api-client.ts` — product hooks/functions (respect the three-file rule).
- Adapt **Dashboard** (`app/page.tsx` + `components/dashboard/`): stats cards → Products / Cutouts
  produced / Pending / Storage (originals vs cutouts + ~2× amplification ratio); chart → cutouts
  produced per day (reuse activity shape); table → recent cutouts. New aggregations flow through
  `runtime → service → repo` and TanStack Query.
- **Sidebar**: add a **Catalog** entry (icon `Scissors` or `PackageOpen`) between Dashboard and
  Upload; keep Dashboard / Upload / Files / Settings + Design. Add `"/products": "Catalog"` to
  `header.tsx` `pageTitles`.
- `packages/shared/src/types.ts` — add `Product`, `ProductDetail`, `RemovalResult`, `CatalogStats`,
  `ImportResult`.

**Non-negotiable keep + add — resolved:** `/files` (full-bucket browse) is kept unchanged, and the
new **Catalog** (`/products`) is the added sample-specific explorer scoped to the sample's own
`products/` folder. Both ship.

---

## 3. B2 surface (S3-compatible only — no b2-native)

All via boto3 in `repo/` with `user_agent_extra` set and standardized `B2_*` env vars.

| Operation | Used for |
|-----------|----------|
| `put_object` | upload originals, cutouts (PNG), sidecar JSON, catalog JSON, imported CSV |
| `get_object` | **read original bytes from B2 to feed rembg** (originals live in B2), read sidecar/catalog |
| `list_objects_v2` (paginated) | catalog listing (scoped to `products/`), dashboard stats, generic files |
| `head_object` | file metadata |
| `delete_object` | scoped product delete (only the SKU's `originals/`, `cutouts/`, `catalog/` keys) |
| `generate_presigned_url` | serve originals + cutouts for preview/download |

No b2-native API anywhere. Custom UA required on the single cached S3 client. Deletes are always
scoped to a specific SKU prefix (never a bucket-wide wipe) — matches the repo's safety convention.

**Env var rename to Standard #3 (mandatory — starter deviates).** The starter uses `B2_ENDPOINT`,
`B2_KEY_ID`, `B2_APPLICATION_KEY`, `B2_BUCKET_NAME`, `b2_public_url`. This sample must use:

| Standard #3 name | Notes |
|------------------|-------|
| `B2_APPLICATION_KEY_ID` | was `B2_KEY_ID` |
| `B2_APPLICATION_KEY` | unchanged |
| `B2_BUCKET_NAME` | unchanged |
| `B2_REGION` | **replaces `B2_ENDPOINT`**; derive endpoint `https://s3.{B2_REGION}.backblazeb2.com` and pass `region_name` to boto3 |
| `B2_PUBLIC_URL_BASE` | was `b2_public_url`; **optional** (presigned URLs work without it — do not fail startup on its absence) |

Update `config/settings.py`, `repo/b2_client.py` (derive endpoint + set `region_name`), `main.py`
startup validation (require KEY_ID/KEY/BUCKET/REGION; PUBLIC_URL_BASE optional), `.env.example`,
`scripts/doctor.mjs`, README, and all test fixtures/conftest accordingly.

---

## 4. Key features

**Feature 1 — Background removal (rembg / U²-Net) · `deployment: local` · cost $0 · no API key**
- Provider/model: **rembg** (`danielgatis/rembg`), U²-Net family. Model selector: `u2net` (default,
  general), `u2netp` (lightweight/fast), `isnet-general-use` (sharper edges), `u2net_human_seg`,
  `silueta`. Optional `alpha_matting` toggle (finer edges via pymatting; slower; default off).
- `deployment: local` — heavy workload runs on-device. **Hard rule: CPU default, GPU autodetect.**
  Select onnxruntime providers at runtime: prefer `CUDAExecutionProvider` if available, else
  `CPUExecutionProvider`; pass explicitly to `rembg.new_session(model, providers=[...])`. **Apple
  MPS/CoreML EP is flaky for U²-Net → not used by default** (documented; opt-in via a `REMBG_PROVIDERS`
  env override). No GPU is ever hard-required.
- Cost: $0 (local compute, no external API, no second key). Models download once from GitHub on
  first use (~176 MB for u2net) to `~/.u2net/`; needs network on first run — document.
- **Dependency hygiene (false-green trap):** rembg + onnxruntime are heavy. Put ML deps in a
  **separate `services/api/requirements-ml.txt`**, pinned; keep `requirements.txt` core-only (no
  rembg) so the API installs/tests fast and green. `service/removal.py` lazy-imports rembg. Starting
  pin window (VERIFY step validates end-to-end and may adjust): `rembg[cpu]>=2.0.57,<2.0.60`,
  `onnxruntime>=1.17,<1.20`, `numpy>=1.26,<2` (rembg/onnxruntime need numpy<2), `pillow>=11`. Note in
  the plan/README that tests passing ≠ marquee feature working — only end-to-end verify (later step)
  confirms rembg actually produces a cutout on a fresh clone.

**Feature 2 — Product catalog CRUD** (the primary-entity lifecycle — see below). Scoped Catalog view
(`/products`) + create/detail/edit/delete.

**Feature 3 — Batch ingest via CSV manifest** — upload a CSV (`sku,category,batch,filename`) plus a
set of image files; the backend matches each row's `filename` to an uploaded image, uploads the
original to `products/originals/<sku>/`, writes the catalog JSON as `status: pending`, and reports
per-row success/skip. Demonstrates the "tens of thousands of images at ingest" story.

**Feature 4 — Batch background removal** — "Process all pending" runs rembg across every pending
product sequentially; each produces a cutout + sidecar. Demonstrates continuous write amplification.

**Feature 5 — Before/after preview + sidecar metadata** — product detail shows the opaque original
beside the transparent cutout (checkerboard backing), plus sidecar fields (model, rembg version,
processing ms, dimensions, foreground coverage, alpha-matting). The screenshot money-shot.

**Feature 6 — Domain dashboard** — Products, Cutouts produced, Pending, Storage (originals vs
cutouts bytes + amplification ratio), avg processing time; cutouts-per-day chart; recent cutouts.

### External API provider
None. rembg is fully local (`deployment: local`, $0, no key). No Genblaze routing — the description
specifies "no second API key, B2 credentials only" and does not mention Genblaze / `genblaze-*`.

### Primary-entity lifecycle (Product) — all verbs built, none omitted
| Verb | UI surface | Behavior |
|------|-----------|----------|
| **create** | `/products/new` form | validate SKU, upload original to `products/originals/<sku>/`, write catalog JSON (`status: pending`); optional "Remove background now" switch |
| **read** | `/products` list + `/products/[sku]` detail | before/after + sidecar + status |
| **edit** | pre-filled dialog/form on detail | update category / batch / model / alpha_matting; **SKU is read-only** (it's the B2 key — renaming = moving objects, out of scope, noted in the form) |
| **delete** | detail (and per-row) | scoped delete of the SKU's `originals/`, `cutouts/`, `catalog/` keys only |
| **run** | detail "Remove background" / "Re-run"; list "Process all pending" | run rembg → write cutout PNG + sidecar; re-runnable with a different model |

All five verbs are genuinely supported and exposed. `omitted_ui_verbs` = **[]** (empty).

### Form UX conventions (create/edit)
- **Finite-value fields → selectors** (both forms): `model` → `Select` (5 rembg models); `category`
  → `Select` (Apparel, Footwear, Accessories, Electronics, Home, Beauty, Other); `alpha_matting`
  → `Switch`. Free-text fields: `sku` (`Input`, required, pattern `^[A-Za-z0-9._-]+$`), `batch`
  (`Input`, optional).
- **Create-form default hints** (placeholder / `FormDescription`, guidance only — no autofill
  button): sku e.g. `SKU-1001`; category defaults to `Apparel`; model defaults to `u2net (general
  purpose)`; batch e.g. `2026-summer`; a note that a safe test run = upload one JPEG/PNG product
  photo, keep model `u2net`, leave alpha-matting off.
- **Edit form** opens pre-filled with the product's real values; SKU read-only; no default hints.
- Exemplar to mirror: `apps/web/src/components/settings/settings-form.tsx`.

---

## 5. Doc transforms

- **README.md** — full rewrite: purpose, ingest→remove→store→serve workflow, **two-step install**
  (`requirements.txt` then `requirements-ml.txt` + first-run model download note), features, B2
  object layout, Standard #3 env vars, GPU/CPU note, commands. Omit the image block (screenshots
  added later). Keep the B2 sign-up UTM links (retag `utm_content`, see §6).
- **AGENTS.md** — update repo map (add catalog/removal), §2 building-on contract (Catalog + removal
  are sample additions; bucket explorer + upload + UI kit still "keep"), commands.
- **ARCHITECTURE.md** — add removal + catalog services and the data flow (B2 originals → rembg →
  cutout + sidecar; catalog JSON as system of record); note the lazy rembg import + layering.
- **docs/features/**: keep + adapt `dashboard.md` (new metrics); keep `file-upload.md`,
  `file-browser.md`, `metadata-extraction.md`. ADD `background-removal.md`, `product-catalog.md`,
  `batch-ingest.md`. Keep `_template.md`.
- **docs/app-workflows.md** — rewrite journeys: ingest (single + CSV) → remove (single + batch) →
  review before/after → serve via presigned URL.
- **docs/SECURITY.md / RELIABILITY.md / design-system.md / dev-workflows.md** — keep; light edits for
  renamed commands, env vars, and the new endpoints. Note in SECURITY: uploaded images are processed
  in-memory; scoped deletes only.
- **infra/railway/README.md** — note ML deps + model-download memory/build implications (rembg +
  onnxruntime are large; first run pulls the model). Keep minimal.
- On PASS, the scaffold plan is moved to `docs/exec-plans/completed/initial-scaffold.md` (Phase 5).

---

## 6. Rename table (`vibe-coding-starter-kit` → `rembg-product-background-removal`)

Display name (human-facing): **"Rembg Cutout Studio"**. Package/identifier: `rembg-product-background-removal`.

| Identifier / location | From | To |
|-----------------------|------|-----|
| Root `package.json` `name` | `vibe-coding-starter-kit` | `rembg-product-background-removal` |
| Workspace pkg scope (all files) | `@vibe-coding-starter-kit/web`, `@vibe-coding-starter-kit/shared` | `@rembg-product-background-removal/web`, `@rembg-product-background-removal/shared` |
| All `@vibe-coding-starter-kit/shared` imports | 10+ web files (api-client, queries, file-*, upload-progress, command-palette, file-tree) | `@rembg-product-background-removal/shared` |
| `pnpm --filter` scripts + `next.config.ts` transpile/paths | `@vibe-coding-starter-kit/*` | `@rembg-product-background-removal/*` |
| `app-config.ts` `APP_NAME` | `"OSS Starter Kit"` | `"Rembg Cutout Studio"` |
| `app-config.ts` `APP_DESCRIPTION` | file-mgmt copy | `"Batch background removal for product images with rembg, stored on Backblaze B2"` |
| `main.py` FastAPI `title`/`description` | `"OSS Starter Kit API"` | `"Rembg Cutout Studio API"` + removal/catalog description |
| S3 `user_agent_extra` (`b2_client.py`) | `b2ai-oss-start` | `b2ai-rembg-cutouts` |
| UTM `utm_content` tags (README, sidebar, doctor.mjs) | `b2ai-oss-start` | `b2ai-rembg-cutouts` |
| Titles/prose "Vibe Coding Starter Kit" / "OSS Starter Kit" | README, AGENTS, docs, CODE_REVIEW(removed) | Rembg Cutout Studio / rembg-product-background-removal |
| Any CI workflow name / image tag / railway service slug | starter slug | `rembg-product-background-removal` |

Do a global find/replace of `vibe-coding-starter-kit` → `rembg-product-background-removal` across all
tracked files **except** `pnpm-lock.yaml` (regenerated by pnpm install), then targeted display-string
edits above. Verify `pnpm lint`, `pnpm build`, `pnpm lint:api`, `pnpm test:api`, `pnpm check:structure`
all pass after the rename.

---

## 7. Build order (guidance for the builder)
1. Copy tree, strip `.git`, global identifier rename, env-var rename (§3/§6), delete TRIM items.
2. Backend: settings/b2_client/main env changes → repo helpers → `service/removal.py` (lazy rembg) →
   `service/catalog.py` → `runtime/catalog.py` → types → `requirements-ml.txt` → tests. Keep
   `test_structure.py` green.
3. Frontend: shared types → api-client/queries → catalog components → routes → sidebar/header →
   dashboard adaptation.
4. Docs (§5). Run the full check suite; fix lint/build/test/structure until green.

**Verdict gating reminder:** the marquee rembg run is validated end-to-end by the later verify step,
not here. This step must ship correct, pinned, lazy-imported, fully-wired code with green
lint/build/test/structure — a green build with an unrunnable ML feature is a false green.
