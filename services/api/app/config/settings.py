from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- Backblaze B2 (S3-compatible) — Standardized B2_* names ---
    # The S3 endpoint is derived from the region so there is never a hardcoded
    # region string in source. boto3 also receives `region_name` (see repo/).
    b2_application_key_id: str = ""
    b2_application_key: str = ""
    b2_bucket_name: str = ""
    b2_region: str = ""
    # Optional: a public/CDN base URL for objects. Presigned URLs work without
    # it, so its absence must NEVER fail startup.
    b2_public_url_base: str = ""

    api_port: int = 8000
    # Explicit allowlist by default — covers Next on :3000 and the
    # fallback :3001 it picks if 3000 is busy. Production deploys should
    # override with the exact frontend origin.
    api_cors_origins: str = "http://localhost:3000,http://localhost:3001"
    # Optional dev-only escape hatch: a regex that matches additional
    # allowed origins. Empty by default — set this to e.g.
    # `^http://localhost:\d+$` to accept any localhost port without
    # listing each one. NEVER ship this to production.
    api_cors_origin_regex: str = ""

    # Upload limits
    max_file_size: int = 100 * 1024 * 1024  # 100MB

    # --- rembg background-removal engine ---
    # Default U2Net-family model used when a product doesn't pin one.
    rembg_default_model: str = "u2net"
    # Optional comma-separated onnxruntime execution-provider override, e.g.
    # "CUDAExecutionProvider,CPUExecutionProvider" or "CoreMLExecutionProvider".
    # Empty = runtime autodetect (CUDA if available, else CPU). See
    # service/removal.py. Apple MPS/CoreML is opt-in only (flaky for U2Net).
    rembg_providers: str = ""

    # Small durable counters (downloads, etc). Point at a persistent
    # volume in production if you care about surviving restarts.
    download_count_file: str = "data/download_count.json"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",")]

    @property
    def b2_endpoint(self) -> str:
        """Derive the S3 endpoint from the region — no hardcoded region."""
        return f"https://s3.{self.b2_region}.backblazeb2.com"

    @property
    def rembg_provider_list(self) -> list[str]:
        """Explicit provider override as a list, or [] for autodetect."""
        return [p.strip() for p in self.rembg_providers.split(",") if p.strip()]


settings = Settings()
