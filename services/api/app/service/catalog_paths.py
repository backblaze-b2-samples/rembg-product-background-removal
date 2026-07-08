"""Shared catalog helpers: B2 key layout, validation, and JSON I/O.

The B2 object layout IS the database:
  products/originals/<sku>/<filename>       original product image
  products/cutouts/<sku>/<stem>.png         transparent cutout
  products/cutouts/<sku>/<stem>.json        removal sidecar
  products/catalog/<sku>.json               per-SKU manifest (editable metadata)
"""

import json
import re
from pathlib import Path

from app.repo import get_object_bytes, get_presigned_url, list_prefix, put_bytes
from app.types import Product

CATALOG_PREFIX = "products/catalog/"
ORIGINALS_PREFIX = "products/originals/"
CUTOUTS_PREFIX = "products/cutouts/"

_SKU_RE = re.compile(r"^[A-Za-z0-9._-]+$")
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


class CatalogError(Exception):
    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def catalog_key(sku: str) -> str:
    return f"{CATALOG_PREFIX}{sku}.json"


def original_key(sku: str, filename: str) -> str:
    return f"{ORIGINALS_PREFIX}{sku}/{filename}"


def cutout_key(sku: str, filename: str) -> str:
    return f"{CUTOUTS_PREFIX}{sku}/{Path(filename).stem}.png"


def sidecar_key(sku: str, filename: str) -> str:
    return f"{CUTOUTS_PREFIX}{sku}/{Path(filename).stem}.json"


def validate_sku(sku: str) -> None:
    if not sku or not _SKU_RE.match(sku):
        raise CatalogError(
            "SKU may only contain letters, digits, dots, dashes and underscores"
        )


def validate_choice(value: str, allowed: list[str], field: str) -> None:
    if value not in allowed:
        raise CatalogError(
            f"Invalid {field} '{value}'. Allowed: {', '.join(allowed)}"
        )


def read_catalog(sku: str) -> dict | None:
    raw = get_object_bytes(catalog_key(sku))
    if raw is None:
        return None
    return json.loads(raw.decode("utf-8"))


def write_catalog(data: dict) -> None:
    put_bytes(
        catalog_key(data["sku"]),
        json.dumps(data, indent=2, default=str).encode("utf-8"),
        "application/json",
    )


def existing_cutout_keys() -> set[str]:
    return {
        o["Key"] for o in list_prefix(CUTOUTS_PREFIX) if o["Key"].endswith(".png")
    }


def to_product(data: dict, cutout_keys: set[str]) -> Product:
    sku = data["sku"]
    ck = cutout_key(sku, data["original_filename"])
    has_cutout = ck in cutout_keys
    return Product(
        sku=sku,
        category=data["category"],
        batch=data.get("batch"),
        original_filename=data["original_filename"],
        original_key=data["original_key"],
        model=data["model"],
        alpha_matting=data["alpha_matting"],
        status="done" if has_cutout else "pending",
        created_at=data["created_at"],
        updated_at=data["updated_at"],
        cutout_key=ck if has_cutout else None,
        thumbnail_url=get_presigned_url(ck if has_cutout else data["original_key"]),
    )
