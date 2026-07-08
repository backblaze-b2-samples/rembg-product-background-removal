<!-- last_verified: 2026-07-08 -->
# Security

Security principles and implementation for Rembg Cutout Studio.

## Trust Boundaries

- **Frontend -> API**: CORS-restricted to configured origins, scoped to `GET/POST/PATCH/DELETE/OPTIONS`
- **API -> B2**: Authenticated via `B2_APPLICATION_KEY_ID` + `B2_APPLICATION_KEY`, signature v4
- **Client -> B2**: Presigned URLs for preview/download (short expiry)

## Image processing & catalog safety

- Uploaded product images are processed **in-memory** (bytes → rembg → cutout bytes); no
  temp files are written for the transform.
- Product deletes are **scoped to the SKU's prefixes** (`products/originals/<sku>/`,
  `products/cutouts/<sku>/`, `products/catalog/<sku>.json`) via `repo.delete_prefix`, which
  refuses an empty prefix — a bug can never trigger a bucket-wide wipe.
- SKUs are validated against `^[A-Za-z0-9._-]+$` before being used as B2 key segments.
- Create accepts only JPEG/PNG/WebP for products (415 otherwise).

## Upload Validation

- Filename sanitization: path traversal, null bytes, unsafe chars stripped
- MIME/extension consistency check against allowlist
- Chunked streaming with size enforcement (100MB default)
- Content-type allowlist (images, PDFs, text, archives, audio/video)
- Empty file rejection

## File Key Validation

- Empty keys rejected
- Path traversal patterns rejected (`../`, `%2e%2e`, backslashes, null bytes)
- The bucket is the only access boundary — add prefix scoping in
  `services/api/app/service/files.py::validate_key` if your deployment
  shares a bucket with other workloads

## Download Safety

- Presigned URLs force `Content-Disposition: attachment`
- Prevents inline rendering of user-uploaded content (XSS mitigation)

## Secrets Management

- All secrets loaded via environment variables (pydantic-settings)
- Never committed to source control
- `.env.example` documents required variables without values

## Agent Security Rules

- Never commit `.env`, credentials, or API keys
- Never weaken validation without explicit instruction
- Never bypass CORS, auth, or input sanitization
- Always validate at system boundaries
