"""Assemble frame_*.png files into a horizontal sprite sheet."""
from __future__ import annotations

import glob
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageEnhance


def build_spritesheet(
    frames_dir: str | Path,
    output: str | Path,
    saturation: float = 1.0,
    brightness: float = 1.0,
    skip_indices: Iterable[int] = (),
) -> Path:
    frames_dir = Path(frames_dir)
    output = Path(output)
    frames = sorted(glob.glob(str(frames_dir / "frame_*.png")))
    if not frames:
        raise FileNotFoundError(f"No frame_*.png files in {frames_dir}")

    skip = set(skip_indices)
    images = []
    for i, path in enumerate(frames):
        if i in skip:
            continue
        img = Image.open(path).convert("RGBA")
        if saturation != 1.0:
            img = ImageEnhance.Color(img).enhance(saturation)
        if brightness != 1.0:
            img = ImageEnhance.Brightness(img).enhance(brightness)
        images.append(img)

    if not images:
        raise ValueError("No frames left after filtering")

    w, h = images[0].size
    sheet = Image.new("RGBA", (w * len(images), h), (0, 0, 0, 0))
    for i, img in enumerate(images):
        sheet.paste(img, (i * w, 0))
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)
    return output
