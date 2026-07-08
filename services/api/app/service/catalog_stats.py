"""Dashboard aggregations over the B2 catalog layout."""

import json
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from app.repo import get_object_bytes, list_prefix
from app.service.catalog_paths import (
    CATALOG_PREFIX,
    CUTOUTS_PREFIX,
    ORIGINALS_PREFIX,
)
from app.types import CatalogStats, DailyCutoutCount
from app.types.formatting import humanize_bytes


def get_catalog_stats() -> CatalogStats:
    catalog_objs = [
        o for o in list_prefix(CATALOG_PREFIX) if o["Key"].endswith(".json")
    ]
    total_products = len(catalog_objs)

    originals_bytes = sum(o["Size"] for o in list_prefix(ORIGINALS_PREFIX))
    cutout_objs = list_prefix(CUTOUTS_PREFIX)
    cutouts_bytes = sum(o["Size"] for o in cutout_objs if o["Key"].endswith(".png"))
    cutouts_produced = sum(1 for o in cutout_objs if o["Key"].endswith(".png"))

    ms_values: list[int] = []
    for o in cutout_objs:
        if not o["Key"].endswith(".json"):
            continue
        raw = get_object_bytes(o["Key"])
        if raw is None:
            continue
        try:
            ms_values.append(int(json.loads(raw.decode("utf-8"))["processing_ms"]))
        except (KeyError, ValueError, json.JSONDecodeError):
            continue

    # (originals + cutouts) / originals — storage a catalog costs relative to
    # the originals alone. Approaches ~2.0 once every SKU has a cutout.
    amplification = (
        round((originals_bytes + cutouts_bytes) / originals_bytes, 2)
        if originals_bytes
        else 0.0
    )
    return CatalogStats(
        total_products=total_products,
        cutouts_produced=cutouts_produced,
        pending=max(total_products - cutouts_produced, 0),
        originals_bytes=originals_bytes,
        originals_human=humanize_bytes(originals_bytes),
        cutouts_bytes=cutouts_bytes,
        cutouts_human=humanize_bytes(cutouts_bytes),
        amplification_ratio=amplification,
        avg_processing_ms=int(sum(ms_values) / len(ms_values)) if ms_values else 0,
    )


def get_cutout_activity(days: int = 7) -> list[DailyCutoutCount]:
    cutouts = [o for o in list_prefix(CUTOUTS_PREFIX) if o["Key"].endswith(".png")]
    today = datetime.now(UTC).date()
    cutoff = today - timedelta(days=days - 1)
    counts: dict[str, int] = defaultdict(int)
    for o in cutouts:
        d = o["LastModified"].date()
        if d >= cutoff:
            counts[d.isoformat()] += 1
    return [
        DailyCutoutCount(
            date=(cutoff + timedelta(days=i)).isoformat(),
            cutouts=counts.get((cutoff + timedelta(days=i)).isoformat(), 0),
        )
        for i in range(days)
    ]
