"""Background-removal engine wrapper (rembg / U2Net family).

The heavy ML dependencies (`rembg`, `onnxruntime`) live in
`requirements-ml.txt` and are **lazy-imported inside functions here** so the
core API installs and its tests run green without them. Any code path that
actually needs the engine raises `RembgNotInstalledError`, which the router
surfaces as a clean 503.

Device policy (deployment: local): CPU by default, GPU auto-detected. We pick
onnxruntime execution providers at runtime — prefer CUDA when available, else
CPU — and pass them explicitly to `new_session(...)`. A GPU is never
hard-required. Apple CoreML/MPS is flaky for U2Net so it is opt-in only via the
`REMBG_PROVIDERS` env override (see config/settings.py).
"""

import io
import logging
import time
from datetime import UTC, datetime

from app.config import settings
from app.repo import get_object_bytes
from app.types import REMBG_MODELS, RemovalResult, RemovalSidecar

logger = logging.getLogger(__name__)

# Alpha threshold (0-255) for the foreground-coverage proxy. A pixel counts as
# "foreground" if its alpha exceeds this after cutout.
_ALPHA_THRESHOLD = 16

_INSTALL_HINT = (
    "Background-removal dependencies are not installed. Run "
    "`pip install -r services/api/requirements-ml.txt` (rembg + onnxruntime). "
    "The first run downloads the selected model (~176 MB for u2net) to ~/.u2net/."
)


class RembgNotInstalledError(RuntimeError):
    """Raised when the rembg/onnxruntime stack is unavailable."""

    def __init__(self, detail: str = _INSTALL_HINT):
        self.detail = detail
        super().__init__(detail)


class RemovalError(RuntimeError):
    """Raised when a removal run fails for a reason other than missing deps."""


# Cache one rembg session per (model, providers) combo — session creation
# loads the ONNX model into memory and is expensive.
_session_cache: dict[tuple, object] = {}


def available_models() -> list[str]:
    return list(REMBG_MODELS)


def _select_providers() -> list[str]:
    """Explicit override, else autodetect: CUDA if present, otherwise CPU."""
    override = settings.rembg_provider_list
    if override:
        return override
    try:
        import onnxruntime as ort

        available = set(ort.get_available_providers())
    except Exception:  # onnxruntime missing or broken -> safe CPU default
        return ["CPUExecutionProvider"]
    if "CUDAExecutionProvider" in available:
        return ["CUDAExecutionProvider", "CPUExecutionProvider"]
    return ["CPUExecutionProvider"]


def _rembg_version() -> str:
    try:
        from importlib.metadata import version

        return version("rembg")
    except Exception:
        return "unknown"


def _get_session(model: str):
    if model not in REMBG_MODELS:
        raise RemovalError(
            f"Unknown model '{model}'. Choose one of: {', '.join(REMBG_MODELS)}"
        )
    try:
        from rembg import new_session
    except ImportError as e:
        raise RembgNotInstalledError() from e
    providers = _select_providers()
    cache_key = (model, tuple(providers))
    if cache_key not in _session_cache:
        logger.info(
            "Creating rembg session model=%s providers=%s", model, providers
        )
        _session_cache[cache_key] = new_session(model, providers=providers)
    return _session_cache[cache_key]


def _foreground_ratio(alpha_hist: list[int], total_pixels: int) -> float:
    """Fraction of pixels with alpha above threshold. Honest coverage proxy."""
    if total_pixels <= 0:
        return 0.0
    foreground = sum(alpha_hist[_ALPHA_THRESHOLD + 1 :])
    return round(foreground / total_pixels, 4)


def remove_background_bytes(
    original_bytes: bytes, model: str, alpha_matting: bool
) -> tuple[bytes, RemovalSidecar]:
    """Run rembg on raw image bytes; return (cutout PNG bytes, sidecar).

    Pure transform — no B2 I/O. Lazy-imports the ML stack.
    """
    try:
        from PIL import Image
        from rembg import remove
    except ImportError as e:
        raise RembgNotInstalledError() from e

    session = _get_session(model)
    start = time.perf_counter()
    try:
        cutout_bytes = remove(
            original_bytes,
            session=session,
            alpha_matting=alpha_matting,
        )
    except Exception as e:  # surface any engine failure as a clean RemovalError
        raise RemovalError(f"rembg failed: {e}") from e
    processing_ms = int((time.perf_counter() - start) * 1000)

    img = Image.open(io.BytesIO(cutout_bytes)).convert("RGBA")
    width, height = img.size
    alpha_hist = img.getchannel("A").histogram()  # 256 buckets

    sidecar = RemovalSidecar(
        model=model,
        rembg_version=_rembg_version(),
        processing_ms=processing_ms,
        width=width,
        height=height,
        foreground_ratio=_foreground_ratio(alpha_hist, width * height),
        alpha_matting=alpha_matting,
        created_at=datetime.now(UTC),
    )
    return cutout_bytes, sidecar


def remove_background_for_key(
    original_key: str, model: str, alpha_matting: bool
) -> tuple[bytes, RemovalSidecar]:
    """Fetch the original from B2 (via repo) and run the cutout."""
    original_bytes = get_object_bytes(original_key)
    if original_bytes is None:
        raise RemovalError(f"Original image not found in B2: {original_key}")
    return remove_background_bytes(original_bytes, model, alpha_matting)


def build_result(
    sku: str, cutout_key: str, sidecar: RemovalSidecar
) -> RemovalResult:
    return RemovalResult(sku=sku, cutout_key=cutout_key, sidecar=sidecar)
