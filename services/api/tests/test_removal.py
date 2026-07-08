"""Tests for the rembg wrapper. rembg is NOT installed in the core test env,
so these tests either exercise the pure/helper paths or inject a fake `rembg`
module — they never require the heavy ML stack.
"""

import io
import sys
import types

import pytest
from PIL import Image

from app.service import removal


def _png_bytes(w: int = 10, h: int = 10, alpha: int = 255) -> bytes:
    img = Image.new("RGBA", (w, h), (200, 10, 10, alpha))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def test_available_models_includes_default():
    models = removal.available_models()
    assert "u2net" in models
    assert models[0] == "u2net"


def test_select_providers_defaults_to_cpu(monkeypatch):
    monkeypatch.setattr(removal.settings, "rembg_providers", "")
    # Force the onnxruntime import to fail so the result is deterministic.
    monkeypatch.setitem(sys.modules, "onnxruntime", None)
    assert removal._select_providers() == ["CPUExecutionProvider"]


def test_select_providers_honors_override(monkeypatch):
    monkeypatch.setattr(
        removal.settings,
        "rembg_providers",
        "CUDAExecutionProvider,CPUExecutionProvider",
    )
    assert removal._select_providers() == [
        "CUDAExecutionProvider",
        "CPUExecutionProvider",
    ]


def test_foreground_ratio():
    # All-zero histogram -> 0.0 regardless of pixel count.
    assert removal._foreground_ratio([0] * 256, 0) == 0.0
    # 100 pixels, all in the top alpha bucket -> full coverage.
    hist = [0] * 256
    hist[255] = 100
    assert removal._foreground_ratio(hist, 100) == 1.0


def test_missing_rembg_raises_clean_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "rembg", None)  # -> ImportError on import
    removal._session_cache.clear()
    with pytest.raises(removal.RembgNotInstalledError):
        removal.remove_background_bytes(_png_bytes(), "u2net", False)


def test_remove_background_with_fake_engine(monkeypatch):
    cutout = _png_bytes(alpha=255)
    fake = types.ModuleType("rembg")
    fake.remove = lambda data, session=None, alpha_matting=False: cutout
    fake.new_session = lambda model, providers=None: object()
    monkeypatch.setitem(sys.modules, "rembg", fake)
    removal._session_cache.clear()

    out, sidecar = removal.remove_background_bytes(_png_bytes(), "u2net", False)

    assert out == cutout
    assert sidecar.model == "u2net"
    assert sidecar.width == 10
    assert sidecar.height == 10
    assert sidecar.alpha_matting is False
    assert sidecar.foreground_ratio == 1.0
    assert sidecar.processing_ms >= 0


def test_unknown_model_rejected(monkeypatch):
    fake = types.ModuleType("rembg")
    fake.remove = lambda *a, **k: b""
    fake.new_session = lambda *a, **k: object()
    monkeypatch.setitem(sys.modules, "rembg", fake)
    removal._session_cache.clear()
    with pytest.raises(removal.RemovalError):
        removal.remove_background_bytes(_png_bytes(), "not-a-real-model", False)
