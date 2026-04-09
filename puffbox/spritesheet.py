"""Assemble frame_*.png files into a horizontal sprite sheet or an animated GIF."""
from __future__ import annotations

import glob
import shutil
import subprocess
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageEnhance


def _load_frames(
    frames_dir: Path,
    saturation: float,
    brightness: float,
    skip_indices: Iterable[int],
) -> list[Image.Image]:
    paths = sorted(glob.glob(str(frames_dir / "frame_*.png")))
    if not paths:
        raise FileNotFoundError(f"No frame_*.png files in {frames_dir}")
    skip = set(skip_indices)
    images: list[Image.Image] = []
    for i, path in enumerate(paths):
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
    return images


def build_spritesheet(
    frames_dir: str | Path,
    output: str | Path,
    saturation: float = 1.0,
    brightness: float = 1.0,
    skip_indices: Iterable[int] = (),
) -> Path:
    frames_dir = Path(frames_dir)
    output = Path(output)
    images = _load_frames(frames_dir, saturation, brightness, skip_indices)

    w, h = images[0].size
    sheet = Image.new("RGBA", (w * len(images), h), (0, 0, 0, 0))
    for i, img in enumerate(images):
        sheet.paste(img, (i * w, 0))
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)
    return output


def build_gif(
    frames_dir: str | Path,
    output: str | Path,
    fps: float = 20.0,
    saturation: float = 1.0,
    brightness: float = 1.0,
    skip_indices: Iterable[int] = (),
) -> Path:
    """Assemble frames into a looping animated GIF with transparency.

    Prefers ImageMagick (`magick` or `convert`) if available — it produces
    cleaner transparent GIFs than Pillow. Falls back to Pillow with a white
    background composite if ImageMagick is not on PATH.
    """
    frames_dir = Path(frames_dir)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    delay_ms = max(int(round(1000 / fps)), 10)

    magick = shutil.which("magick") or shutil.which("convert")
    if magick:
        # ImageMagick path: load frame_*.png in order, set per-frame delay,
        # loop forever, dispose previous frame to keep transparency clean.
        paths = sorted(glob.glob(str(frames_dir / "frame_*.png")))
        if not paths:
            raise FileNotFoundError(f"No frame_*.png files in {frames_dir}")
        skip = set(skip_indices)
        kept = [p for i, p in enumerate(paths) if i not in skip]
        if not kept:
            raise ValueError("No frames left after filtering")
        cmd = [
            magick,
            "-delay", str(max(delay_ms // 10, 1)),  # ImageMagick uses centiseconds
            "-loop", "0",
            "-dispose", "previous",
            *kept,
            str(output),
        ]
        # Saturation/brightness via Pillow if non-default — otherwise pass-through.
        if saturation != 1.0 or brightness != 1.0:
            # Re-process via Pillow first into a temp dir, then call magick on those.
            import tempfile
            with tempfile.TemporaryDirectory() as tmp:
                tmp_dir = Path(tmp)
                images = _load_frames(frames_dir, saturation, brightness, skip_indices)
                for i, im in enumerate(images):
                    im.save(tmp_dir / f"frame_{i:03d}.png")
                cmd = [
                    magick,
                    "-delay", str(max(delay_ms // 10, 1)),
                    "-loop", "0",
                    "-dispose", "previous",
                    *sorted(str(p) for p in tmp_dir.glob("frame_*.png")),
                    str(output),
                ]
                subprocess.run(cmd, check=True, capture_output=True)
            return output
        subprocess.run(cmd, check=True, capture_output=True)
        return output

    # Pillow fallback: composite each frame onto white. Loses true transparency
    # but works without external tools and looks fine on white-background sites.
    images = _load_frames(frames_dir, saturation, brightness, skip_indices)
    composited = []
    for im in images:
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, (0, 0), im)
        composited.append(bg)
    composited[0].save(
        output,
        save_all=True,
        append_images=composited[1:],
        loop=0,
        duration=delay_ms,
        disposal=2,
        optimize=True,
    )
    return output
