"""Source: a local image file (.png/.jpg/.jpeg) → Meshy image-to-3D → .glb."""
from __future__ import annotations

from pathlib import Path

SUPPORTED = {".png", ".jpg", ".jpeg"}


def resolve(path: str | Path) -> Path:
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"Image not found: {p}")
    if p.suffix.lower() not in SUPPORTED:
        raise ValueError(
            f"Unsupported image format: {p.suffix}. Use one of {sorted(SUPPORTED)}"
        )
    return p
