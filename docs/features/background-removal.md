<!-- last_verified: 2026-07-08 -->
# Feature: Background Removal (rembg / U²-Net)

## Purpose
Produce a clean, transparent-PNG cutout of a product from its original photo, running the
open-source **rembg** (U²-Net family) library locally — no paid API, no second key.

## Used By
- UI: product detail "Remove background" / "Re-run" button; catalog "Process all pending"
- API: `POST /products/{sku}/remove`, `POST /products/remove-pending`

## Core Functions
- `services/api/app/service/removal.py`
  - `remove_background_bytes(bytes, model, alpha_matting)` — pure transform → (PNG, sidecar)
  - `remove_background_for_key(key, model, alpha_matting)` — fetch original from B2 + run
  - `_select_providers()` — onnxruntime provider autodetect (CUDA → CPU)
  - `_foreground_ratio(...)` — honest alpha-coverage proxy
- `services/api/app/service/catalog.py::run_removal` — orchestrates read → run → write

## Canonical Files
- Engine wrapper: `services/api/app/service/removal.py`

## Inputs
- `sku`: str (path) — resolves the original key + model + alpha_matting from the catalog JSON
- Model: one of `u2net` (default), `u2netp`, `isnet-general-use`, `u2net_human_seg`, `silueta`
- `alpha_matting`: bool — finer edges via pymatting (slower; default off)

## Outputs
- `products/cutouts/<sku>/<stem>.png` — transparent cutout (RGBA PNG)
- `products/cutouts/<sku>/<stem>.json` — sidecar `{ model, rembg_version, processing_ms,
  width, height, foreground_ratio, alpha_matting, created_at }`
- Catalog JSON status flips to `done`
- Response: `RemovalResult { sku, cutout_key, sidecar }`

## Flow
- Router calls `run_removal(sku)` → read catalog JSON for original key + settings
- `remove_background_for_key` fetches original bytes from B2 (repo)
- rembg session is created/cached per (model, providers) and run on the bytes
- Sidecar metrics computed (timing, dimensions, foreground coverage)
- Cutout PNG + sidecar JSON written to B2; catalog status updated

## Device policy (`deployment: local`)
- **CPU by default; GPU auto-detected; a GPU is never required.**
- Providers picked at runtime: `CUDAExecutionProvider` if available, else `CPUExecutionProvider`.
- Apple CoreML/MPS is flaky for U²-Net → **opt-in only** via `REMBG_PROVIDERS`
  (e.g. `REMBG_PROVIDERS=CoreMLExecutionProvider,CPUExecutionProvider`).

## Dependency hygiene (false-green trap)
- rembg + onnxruntime are heavy and live in `services/api/requirements-ml.txt`, installed
  separately. `service/removal.py` **lazy-imports** them, so the core API + tests run without them.
- If the ML deps are missing, the run path raises `RembgNotInstalledError` → the router
  returns a clean **503** with an actionable install hint.
- First run downloads the model (~176 MB for `u2net`) to `~/.u2net/` — network required once.
- A green `pnpm test:api` does **not** prove the engine works (tests mock rembg). Only an
  end-to-end run confirms it.

## Edge Cases
- ML deps not installed → 503 ("`pip install -r services/api/requirements-ml.txt`")
- Unknown model → `RemovalError` (400/500), never a silent fallback
- Original missing in B2 → `RemovalError`
- rembg emits no confidence → `foreground_ratio` is documented as a coverage proxy, not confidence

## UX States
- Idle: "Remove background" (pending) / "Re-run" (has cutout)
- Loading: button shows "Removing…" and is disabled
- Error: toast surfaces the 503 install hint or the failure message verbatim

## Verification
- Test files: `services/api/tests/test_removal.py`, `services/api/tests/test_catalog.py`
- Required cases: provider autodetect/override, missing-deps error, fake-engine happy path,
  unknown model, sidecar written on run
- Quick verify command: `pnpm test:api`
- Full end-to-end (real engine): `pip install -r services/api/requirements-ml.txt`, create a
  product with a JPEG/PNG, click "Remove background", confirm a cutout renders over the
  checkerboard and a sidecar JSON appears in B2.
- Pass criteria: tests green; a real run yields a transparent PNG + sidecar in B2.

## Related Docs
- [Product Catalog](product-catalog.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [App Workflows](../app-workflows.md)
