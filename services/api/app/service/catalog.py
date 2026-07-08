"""Product catalog lifecycle — create, read, edit, delete, run, import.

The B2 object layout IS the database (see catalog_paths.py for the key map).
Status is DERIVED: a SKU is "done" once its cutout PNG exists, else "pending".
Dashboard aggregations live in catalog_stats.py and are re-exported here so the
runtime router has a single import surface.
"""

import csv
import io
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from app.repo import delete_prefix, get_object_bytes, get_presigned_url, list_prefix, put_bytes
from app.service.catalog_paths import (
    ALLOWED_IMAGE_TYPES,
    CATALOG_PREFIX,
    CUTOUTS_PREFIX,
    ORIGINALS_PREFIX,
    CatalogError,
    catalog_key,
    cutout_key,
    existing_cutout_keys,
    original_key,
    read_catalog,
    sidecar_key,
    to_product,
    validate_choice,
    validate_sku,
    write_catalog,
)
from app.service.catalog_stats import get_catalog_stats, get_cutout_activity
from app.service.removal import remove_background_for_key
from app.types import (
    PRODUCT_CATEGORIES,
    REMBG_MODELS,
    BatchRemovalResult,
    ImportResult,
    ImportRow,
    Product,
    ProductDetail,
    ProductUpdate,
    RemovalResult,
    RemovalSidecar,
)

logger = logging.getLogger(__name__)

__all__ = [
    "CatalogError",
    "create_product",
    "delete_product",
    "get_catalog_stats",
    "get_cutout_activity",
    "get_product",
    "import_csv",
    "list_products",
    "run_pending",
    "run_removal",
    "update_product",
]


# --- read ------------------------------------------------------------------


def list_products() -> list[Product]:
    cutout_keys = existing_cutout_keys()
    products: list[Product] = []
    for obj in list_prefix(CATALOG_PREFIX):
        if not obj["Key"].endswith(".json"):
            continue
        raw = get_object_bytes(obj["Key"])
        if raw is None:
            continue
        products.append(to_product(json.loads(raw.decode("utf-8")), cutout_keys))
    products.sort(key=lambda p: p.updated_at, reverse=True)
    return products


def get_product(sku: str) -> ProductDetail:
    validate_sku(sku)
    data = read_catalog(sku)
    if data is None:
        raise CatalogError(f"Product '{sku}' not found", status_code=404)
    ck = cutout_key(sku, data["original_filename"])
    has_cutout = get_object_bytes(ck) is not None
    sidecar = None
    if has_cutout:
        raw = get_object_bytes(sidecar_key(sku, data["original_filename"]))
        if raw is not None:
            sidecar = RemovalSidecar(**json.loads(raw.decode("utf-8")))
    return ProductDetail(
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
        original_url=get_presigned_url(data["original_key"]),
        cutout_url=get_presigned_url(ck) if has_cutout else None,
        sidecar=sidecar,
    )


# --- create / edit / delete ------------------------------------------------


def create_product(
    sku: str,
    category: str,
    batch: str | None,
    model: str,
    alpha_matting: bool,
    file_bytes: bytes,
    filename: str,
    content_type: str,
    remove_now: bool = False,
) -> Product:
    validate_sku(sku)
    validate_choice(category, PRODUCT_CATEGORIES, "category")
    validate_choice(model, REMBG_MODELS, "model")
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise CatalogError(
            f"Unsupported image type '{content_type}'. Use JPEG, PNG or WebP.",
            status_code=415,
        )
    if not file_bytes:
        raise CatalogError("Empty image file")
    if read_catalog(sku) is not None:
        raise CatalogError(f"Product '{sku}' already exists", status_code=409)

    safe_name = Path(filename).name or "image"
    ok = original_key(sku, safe_name)
    put_bytes(ok, file_bytes, content_type)

    now = datetime.now(UTC)
    data = {
        "sku": sku,
        "category": category,
        "batch": batch or None,
        "original_filename": safe_name,
        "original_key": ok,
        "model": model,
        "alpha_matting": alpha_matting,
        "status": "pending",
        "created_at": now,
        "updated_at": now,
    }
    write_catalog(data)
    logger.info("Product created: sku=%s key=%s", sku, ok)

    if remove_now:
        run_removal(sku)
    return to_product(data, existing_cutout_keys())


def update_product(sku: str, update: ProductUpdate) -> Product:
    validate_sku(sku)
    data = read_catalog(sku)
    if data is None:
        raise CatalogError(f"Product '{sku}' not found", status_code=404)
    if update.category is not None:
        validate_choice(update.category, PRODUCT_CATEGORIES, "category")
        data["category"] = update.category
    if update.model is not None:
        validate_choice(update.model, REMBG_MODELS, "model")
        data["model"] = update.model
    if update.batch is not None:
        data["batch"] = update.batch or None
    if update.alpha_matting is not None:
        data["alpha_matting"] = update.alpha_matting
    data["updated_at"] = datetime.now(UTC)
    write_catalog(data)
    return to_product(data, existing_cutout_keys())


def delete_product(sku: str) -> None:
    """Scoped delete — only this SKU's originals, cutouts and catalog keys."""
    validate_sku(sku)
    if read_catalog(sku) is None:
        raise CatalogError(f"Product '{sku}' not found", status_code=404)
    delete_prefix(f"{ORIGINALS_PREFIX}{sku}/")
    delete_prefix(f"{CUTOUTS_PREFIX}{sku}/")
    delete_prefix(catalog_key(sku))
    logger.info("Product deleted (scoped): sku=%s", sku)


# --- run (background removal) ----------------------------------------------


def run_removal(sku: str) -> RemovalResult:
    validate_sku(sku)
    data = read_catalog(sku)
    if data is None:
        raise CatalogError(f"Product '{sku}' not found", status_code=404)

    cutout_bytes, sidecar = remove_background_for_key(
        data["original_key"], data["model"], data["alpha_matting"]
    )
    ck = cutout_key(sku, data["original_filename"])
    put_bytes(ck, cutout_bytes, "image/png")
    put_bytes(
        sidecar_key(sku, data["original_filename"]),
        sidecar.model_dump_json(indent=2).encode("utf-8"),
        "application/json",
    )
    data["status"] = "done"
    data["updated_at"] = datetime.now(UTC)
    write_catalog(data)
    logger.info("Cutout produced: sku=%s ms=%d", sku, sidecar.processing_ms)
    return RemovalResult(sku=sku, cutout_key=ck, sidecar=sidecar)


def run_pending() -> BatchRemovalResult:
    cutout_keys = existing_cutout_keys()
    results: list[RemovalResult] = []
    failed = 0
    for obj in list_prefix(CATALOG_PREFIX):
        if not obj["Key"].endswith(".json"):
            continue
        raw = get_object_bytes(obj["Key"])
        if raw is None:
            continue
        data = json.loads(raw.decode("utf-8"))
        if cutout_key(data["sku"], data["original_filename"]) in cutout_keys:
            continue  # already has a cutout
        try:
            results.append(run_removal(data["sku"]))
        except Exception:
            logger.exception("Batch removal failed for sku=%s", data.get("sku"))
            failed += 1
    return BatchRemovalResult(processed=len(results), failed=failed, results=results)


# --- CSV import ------------------------------------------------------------


def import_csv(csv_bytes: bytes, files: dict[str, tuple[bytes, str]]) -> ImportResult:
    """Register products from a CSV manifest (sku,category,batch,filename).

    `files` maps an uploaded filename -> (bytes, content_type).
    """
    rows: list[ImportRow] = []
    created = skipped = 0
    reader = csv.DictReader(io.StringIO(csv_bytes.decode("utf-8-sig")))
    for row in reader:
        sku = (row.get("sku") or "").strip()
        filename = (row.get("filename") or "").strip()
        category = (row.get("category") or "Other").strip() or "Other"
        batch = (row.get("batch") or "").strip() or None
        if not sku or not filename:
            skipped += 1
            rows.append(
                ImportRow(
                    sku=sku or "(missing)",
                    status="skipped",
                    detail="missing sku or filename",
                )
            )
            continue
        payload = files.get(filename)
        if payload is None:
            skipped += 1
            rows.append(
                ImportRow(
                    sku=sku,
                    status="skipped",
                    detail=f"no uploaded file named '{filename}'",
                )
            )
            continue
        try:
            create_product(
                sku=sku,
                category=category if category in PRODUCT_CATEGORIES else "Other",
                batch=batch,
                model="u2net",
                alpha_matting=False,
                file_bytes=payload[0],
                filename=filename,
                content_type=payload[1],
            )
            created += 1
            rows.append(ImportRow(sku=sku, status="created"))
        except CatalogError as e:
            skipped += 1
            rows.append(ImportRow(sku=sku, status="skipped", detail=e.detail))
    return ImportResult(created=created, skipped=skipped, rows=rows)
