"""Source: an existing .glb/.fbx/.obj file on disk."""
from __future__ import annotations

from pathlib import Path

SUPPORTED = {".glb", ".gltf", ".fbx", ".obj"}


def resolve(path: str | Path) -> Path:
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"Model not found: {p}")
    if p.suffix.lower() not in SUPPORTED:
        raise ValueError(f"Unsupported model format: {p.suffix}. Use one of {SUPPORTED}")
    return p
