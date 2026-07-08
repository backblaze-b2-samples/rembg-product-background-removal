import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.service.catalog import (
    CatalogError,
    create_product,
    delete_product,
    get_catalog_stats,
    get_cutout_activity,
    get_product,
    import_csv,
    list_products,
    run_pending,
    run_removal,
    update_product,
)
from app.service.removal import RembgNotInstalledError, RemovalError
from app.types import (
    BatchRemovalResult,
    CatalogStats,
    DailyCutoutCount,
    ImportResult,
    Product,
    ProductDetail,
    ProductUpdate,
    RemovalResult,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _run_or_http(fn, *args):
    """Execute a removal-bearing service call, mapping engine errors to HTTP."""
    try:
        return fn(*args)
    except CatalogError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    except RembgNotInstalledError as e:
        raise HTTPException(status_code=503, detail=e.detail) from None
    except RemovalError as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# --- static paths first (so "stats"/"import" don't match "{sku}") ---


@router.get("/products", response_model=list[Product])
async def list_products_endpoint():
    try:
        return list_products()
    except CatalogError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None


@router.get("/products/stats", response_model=CatalogStats)
async def catalog_stats_endpoint():
    return get_catalog_stats()


@router.get("/products/stats/activity", response_model=list[DailyCutoutCount])
async def cutout_activity_endpoint(days: int = 7):
    if days < 1 or days > 90:
        raise HTTPException(status_code=400, detail="Days must be between 1 and 90")
    return get_cutout_activity(days=days)


@router.post("/products/remove-pending", response_model=BatchRemovalResult)
async def remove_pending_endpoint():
    return _run_or_http(run_pending)


@router.post("/products/import", response_model=ImportResult)
async def import_endpoint(
    manifest: UploadFile = File(...),
    files: list[UploadFile] = File(default=[]),
):
    csv_bytes = await manifest.read()
    payloads: dict[str, tuple[bytes, str]] = {}
    for f in files:
        payloads[f.filename or ""] = (
            await f.read(),
            f.content_type or "application/octet-stream",
        )
    try:
        return import_csv(csv_bytes, payloads)
    except CatalogError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None


@router.post("/products", response_model=Product)
async def create_product_endpoint(
    file: UploadFile = File(...),
    sku: str = Form(...),
    category: str = Form("Apparel"),
    batch: str | None = Form(None),
    model: str = Form("u2net"),
    alpha_matting: bool = Form(False),
    remove_now: bool = Form(False),
):
    file_bytes = await file.read()
    return _run_or_http(
        create_product,
        sku,
        category,
        batch,
        model,
        alpha_matting,
        file_bytes,
        file.filename or "image",
        file.content_type or "application/octet-stream",
        remove_now,
    )


# --- {sku} paths ---


@router.get("/products/{sku}", response_model=ProductDetail)
async def get_product_endpoint(sku: str):
    try:
        return get_product(sku)
    except CatalogError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None


@router.patch("/products/{sku}", response_model=Product)
async def update_product_endpoint(sku: str, update: ProductUpdate):
    try:
        return update_product(sku, update)
    except CatalogError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None


@router.delete("/products/{sku}")
async def delete_product_endpoint(sku: str):
    try:
        delete_product(sku)
    except CatalogError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    return {"deleted": True, "sku": sku}


@router.post("/products/{sku}/remove", response_model=RemovalResult)
async def remove_endpoint(sku: str):
    return _run_or_http(run_removal, sku)
