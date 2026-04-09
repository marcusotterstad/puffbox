"""Blender subprocess driver."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

BLENDER_SCRIPTS_DIR = Path(__file__).parent / "blender_scripts"
RENDER_SPRITE = BLENDER_SCRIPTS_DIR / "render_sprite.py"
BUILD_TEXT = BLENDER_SCRIPTS_DIR / "build_text.py"


class BlenderNotFound(RuntimeError):
    pass


def _blender_bin() -> str:
    b = os.environ.get("BLENDER_BIN") or shutil.which("blender")
    if not b:
        raise BlenderNotFound(
            "Blender not found on PATH. Install Blender >= 4.0 or set $BLENDER_BIN."
        )
    return b


def _run(cmd: list[str]) -> None:
    print("$", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        tail = (result.stdout[-800:] + "\n" + result.stderr[-800:]).strip()
        raise RuntimeError(f"Blender failed (exit {result.returncode}):\n{tail}")
    # print Blender's tail so user sees progress
    tail = result.stdout.strip().splitlines()[-8:]
    for line in tail:
        print("  " + line)


def build_model_scene(
    model_path: Path,
    *,
    save_blend: Path | None,
    frames: int,
    size: int,
    output: Path,
    angle: float,
    axis: str,
    spin: bool,
    no_render: bool,
) -> None:
    cmd = [
        _blender_bin(), "--background", "--python", str(RENDER_SPRITE), "--",
        "--mode", "build",
        "--model", str(model_path),
        "--frames", str(frames),
        "--size", str(size),
        "--output", str(output),
        "--angle", str(angle),
        "--axis", axis,
    ]
    if spin:
        cmd.append("--spin")
    if save_blend:
        cmd += ["--save-blend", str(save_blend)]
    if no_render:
        cmd.append("--no-render")
    _run(cmd)


def build_text_scene(
    text: str,
    *,
    font: str | None,
    save_blend: Path | None,
    frames: int,
    size: int,
    output: Path,
    angle: float,
    axis: str,
    spin: bool,
    no_render: bool,
) -> None:
    cmd = [
        _blender_bin(), "--background", "--python", str(BUILD_TEXT), "--",
        "--text", text,
        "--frames", str(frames),
        "--size", str(size),
        "--output", str(output),
        "--angle", str(angle),
        "--axis", axis,
    ]
    if font:
        cmd += ["--font", font]
    if spin:
        cmd.append("--spin")
    if save_blend:
        cmd += ["--save-blend", str(save_blend)]
    if no_render:
        cmd.append("--no-render")
    _run(cmd)


def render_from_blend(
    blend_path: Path,
    *,
    frames: int,
    size: int,
    output: Path,
) -> None:
    cmd = [
        _blender_bin(), "--background", "--python", str(RENDER_SPRITE), "--",
        "--mode", "render",
        "--blend", str(blend_path),
        "--frames", str(frames),
        "--size", str(size),
        "--output", str(output),
    ]
    _run(cmd)
