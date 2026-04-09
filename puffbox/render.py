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
    rotate_x: float = 0.0,
    rotate_y: float = 0.0,
    rotate_z: float = 0.0,
    mesh_scale: float = 1.0,
    center: bool = False,
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
        "--rotate-x", str(rotate_x),
        "--rotate-y", str(rotate_y),
        "--rotate-z", str(rotate_z),
        "--mesh-scale", str(mesh_scale),
    ]
    if center:
        cmd.append("--center")
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
    """Render a .blend in background. frames=0 means auto-detect from scene range."""
    cmd = [
        _blender_bin(), "--background", "--python", str(RENDER_SPRITE), "--",
        "--mode", "render",
        "--blend", str(blend_path),
        "--frames", str(frames),
        "--size", str(size),
        "--output", str(output),
    ]
    _run(cmd)


def open_in_blender_gui(blend_path: Path) -> None:
    """Open a .blend in Blender's GUI (foreground) and block until the user exits.

    Stdout/stderr are NOT captured — the user sees Blender's terminal output
    directly. After Blender exits, control returns to the pipeline.
    """
    cmd = [_blender_bin(), str(blend_path)]
    print(f"$ {' '.join(cmd)}")
    print("[edit] Blender is opening. Make your changes, save the .blend, then close Blender to continue.")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"Blender (GUI) exited with code {result.returncode}")
    print("[edit] Blender closed — continuing pipeline...")
