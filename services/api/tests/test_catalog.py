"""Catalog lifecycle tests backed by an in-memory fake B2 (no network, no ML).

The fake replaces the repo functions that each catalog service module binds at
import time, so create/read/edit/delete/run/import all exercise real logic.
"""

import io
from datetime import UTC, datetime

import pytest
from PIL import Image

from app.service import catalog, catalog_paths, catalog_stats
from app.types import ProductUpdate, RemovalSidecar

_REPO_FNS = (
    "get_object_bytes",
    "get_presigned_url",
    "list_prefix",
    "put_bytes",
    "delete_prefix",
)


class FakeB2:
    def __init__(self):
        self.store: dict[str, dict] = {}

    def put_bytes(self, key, data, content_type):
        self.store[key] = {
            "data": data,
            "ct": content_type,
            "mtime": datetime.now(UTC),
        }

    def get_object_bytes(self, key):
        item = self.store.get(key)
        return item["data"] if item else None

    def list_prefix(self, prefix, max_keys=1000):
        return [
            {"Key": k, "Size": len(v["data"]), "LastModified": v["mtime"]}
            for k, v in self.store.items()
            if k.startswith(prefix)
        ]

    def delete_prefix(self, prefix):
        keys = [k for k in self.store if k.startswith(prefix)]
        for k in keys:
            del self.store[k]
        return len(keys)

    def get_presigned_url(self, key, filename=None, expires_in=600):
        return f"https://example.com/{key}"


@pytest.fixture
def fake_b2(monkeypatch):
    b2 = FakeB2()
    for mod in (catalog_paths, catalog, catalog_stats):
        for name in _REPO_FNS:
            if hasattr(mod, name):
                monkeypatch.setattr(mod, name, getattr(b2, name))
    return b2


def _png_bytes() -> bytes:
    img = Image.new("RGBA", (12, 8), (0, 128, 255, 255))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def _fake_sidecar() -> RemovalSidecar:
    return RemovalSidecar(
        model="u2net",
        rembg_version="2.0.57",
        processing_ms=42,
        width=12,
        height=8,
        foreground_ratio=0.75,
        alpha_matting=False,
        created_at=datetime.now(UTC),
    )


def _create(sku="SKU-1001", category="Apparel", model="u2net"):
    return catalog.create_product(
        sku=sku,
        category=category,
        batch="2026-summer",
        model=model,
        alpha_matting=False,
        file_bytes=_png_bytes(),
        filename="shoe.png",
        content_type="image/png",
    )


def test_create_then_read(fake_b2):
    product = _create()
    assert product.sku == "SKU-1001"
    assert product.status == "pending"
    assert product.original_key == "products/originals/SKU-1001/shoe.png"
    assert "products/originals/SKU-1001/shoe.png" in fake_b2.store
    assert "products/catalog/SKU-1001.json" in fake_b2.store

    detail = catalog.get_product("SKU-1001")
    assert detail.category == "Apparel"
    assert detail.batch == "2026-summer"
    assert detail.status == "pending"
    assert detail.cutout_url is None
    assert detail.original_url is not None


def test_create_rejects_bad_sku(fake_b2):
    with pytest.raises(catalog.CatalogError):
        _create(sku="bad sku!")


def test_create_rejects_bad_category(fake_b2):
    with pytest.raises(catalog.CatalogError):
        _create(category="Nonsense")


def test_create_rejects_unsupported_type(fake_b2):
    with pytest.raises(catalog.CatalogError) as exc:
        catalog.create_product(
            sku="SKU-2",
            category="Apparel",
            batch=None,
            model="u2net",
            alpha_matting=False,
            file_bytes=b"%PDF-1.4",
            filename="doc.pdf",
            content_type="application/pdf",
        )
    assert exc.value.status_code == 415


def test_create_duplicate_conflict(fake_b2):
    _create()
    with pytest.raises(catalog.CatalogError) as exc:
        _create()
    assert exc.value.status_code == 409


def test_get_missing_product_404(fake_b2):
    with pytest.raises(catalog.CatalogError) as exc:
        catalog.get_product("NOPE")
    assert exc.value.status_code == 404


def test_list_products(fake_b2):
    _create(sku="SKU-A")
    _create(sku="SKU-B")
    products = catalog.list_products()
    assert {p.sku for p in products} == {"SKU-A", "SKU-B"}


def test_update_product(fake_b2):
    _create()
    updated = catalog.update_product(
        "SKU-1001", ProductUpdate(category="Footwear", model="isnet-general-use")
    )
    assert updated.category == "Footwear"
    assert updated.model == "isnet-general-use"


def test_delete_is_scoped(fake_b2):
    _create(sku="SKU-A")
    _create(sku="SKU-B")
    catalog.delete_product("SKU-A")
    remaining = list(fake_b2.store.keys())
    assert all("SKU-A" not in k for k in remaining)
    assert any("SKU-B" in k for k in remaining)


def test_run_removal_writes_cutout_and_sidecar(fake_b2, monkeypatch):
    _create()
    sidecar = _fake_sidecar()
    monkeypatch.setattr(
        catalog,
        "remove_background_for_key",
        lambda key, model, am: (_png_bytes(), sidecar),
    )
    result = catalog.run_removal("SKU-1001")
    assert result.cutout_key == "products/cutouts/SKU-1001/shoe.png"
    assert "products/cutouts/SKU-1001/shoe.png" in fake_b2.store
    assert "products/cutouts/SKU-1001/shoe.json" in fake_b2.store

    detail = catalog.get_product("SKU-1001")
    assert detail.status == "done"
    assert detail.cutout_url is not None
    assert detail.sidecar is not None
    assert detail.sidecar.processing_ms == 42


def test_run_pending_batch(fake_b2, monkeypatch):
    _create(sku="SKU-A")
    _create(sku="SKU-B")
    monkeypatch.setattr(
        catalog,
        "remove_background_for_key",
        lambda key, model, am: (_png_bytes(), _fake_sidecar()),
    )
    batch = catalog.run_pending()
    assert batch.processed == 2
    assert batch.failed == 0
    # Re-running finds nothing pending.
    assert catalog.run_pending().processed == 0


def test_catalog_stats_amplification(fake_b2, monkeypatch):
    _create(sku="SKU-A")
    monkeypatch.setattr(
        catalog,
        "remove_background_for_key",
        lambda key, model, am: (_png_bytes(), _fake_sidecar()),
    )
    catalog.run_removal("SKU-A")
    stats = catalog.get_catalog_stats()
    assert stats.total_products == 1
    assert stats.cutouts_produced == 1
    assert stats.pending == 0
    assert stats.originals_bytes > 0
    assert stats.cutouts_bytes > 0
    assert stats.amplification_ratio >= 1.0
    assert stats.avg_processing_ms == 42


def test_import_csv(fake_b2):
    csv_text = "sku,category,batch,filename\nSKU-10,Apparel,b1,a.png\nSKU-11,Footwear,b1,missing.png\n"
    files = {"a.png": (_png_bytes(), "image/png")}
    result = catalog.import_csv(csv_text.encode("utf-8"), files)
    assert result.created == 1
    assert result.skipped == 1
    statuses = {r.sku: r.status for r in result.rows}
    assert statuses["SKU-10"] == "created"
    assert statuses["SKU-11"] == "skipped"
