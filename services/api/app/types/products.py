from datetime import datetime

from pydantic import BaseModel

# --- Finite option sets (mirrored by the frontend selectors) ---

# rembg / U2Net-family models exposed in the UI. First entry is the default.
REMBG_MODELS: list[str] = [
    "u2net",
    "u2netp",
    "isnet-general-use",
    "u2net_human_seg",
    "silueta",
]

PRODUCT_CATEGORIES: list[str] = [
    "Apparel",
    "Footwear",
    "Accessories",
    "Electronics",
    "Home",
    "Beauty",
    "Other",
]

# Object status is DERIVED from B2 layout, never trusted blindly:
#   "pending" — original present, no cutout yet
#   "done"    — a cutout PNG exists for the SKU
PRODUCT_STATUSES = ("pending", "done")


class RemovalSidecar(BaseModel):
    """Metadata written alongside every cutout in B2.

    `foreground_ratio` is an HONEST coverage proxy (fraction of pixels whose
    alpha is above threshold), NOT a model confidence score — rembg emits no
    true confidence, so we do not fabricate one.
    """

    model: str
    rembg_version: str
    processing_ms: int
    width: int
    height: int
    foreground_ratio: float
    alpha_matting: bool
    created_at: datetime


class Product(BaseModel):
    """A catalog row — one SKU, its original image, and derived cutout state."""

    sku: str
    category: str
    batch: str | None = None
    original_filename: str
    original_key: str
    model: str
    alpha_matting: bool
    status: str
    created_at: datetime
    updated_at: datetime
    cutout_key: str | None = None
    thumbnail_url: str | None = None


class ProductDetail(Product):
    """Product with presigned preview URLs and the cutout sidecar."""

    original_url: str | None = None
    cutout_url: str | None = None
    sidecar: RemovalSidecar | None = None


class RemovalResult(BaseModel):
    sku: str
    cutout_key: str
    sidecar: RemovalSidecar


class BatchRemovalResult(BaseModel):
    processed: int
    failed: int
    results: list[RemovalResult]


class CatalogStats(BaseModel):
    total_products: int
    cutouts_produced: int
    pending: int
    originals_bytes: int
    originals_human: str
    cutouts_bytes: int
    cutouts_human: str
    # (originals + cutouts) / originals — how much storage a catalog costs
    # relative to the originals alone. ~2.0 once every SKU has a cutout.
    amplification_ratio: float
    avg_processing_ms: int


class DailyCutoutCount(BaseModel):
    date: str
    cutouts: int


class ImportRow(BaseModel):
    sku: str
    status: str  # "created" | "skipped"
    detail: str | None = None


class ImportResult(BaseModel):
    created: int
    skipped: int
    rows: list[ImportRow]


class ProductUpdate(BaseModel):
    """Editable fields. SKU is immutable (it is the B2 key)."""

    category: str | None = None
    batch: str | None = None
    model: str | None = None
    alpha_matting: bool | None = None
