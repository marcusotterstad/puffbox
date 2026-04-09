"""Pipeline orchestration with pause/resume session support."""
from __future__ import annotations

import json
import secrets
import shutil
import tempfile
from dataclasses import dataclass, asdict, field
from datetime import date
from pathlib import Path
from typing import Literal, Any

from . import render
from .sources import model as model_src
from .sources import text as text_src
from .sources import meshy as meshy_src
from .spritesheet import build_spritesheet

SESSIONS_DIR = Path.home() / ".puffbox" / "sessions"

SourceKind = Literal["model", "text", "meshy"]


@dataclass
class PipelineArgs:
    source: SourceKind
    value: str                     # path for model, prompt for meshy, string for text
    frames: int = 1
    size: int = 1024
    output: str = "out.png"
    angle: float = 18.0
    axis: str = "Z"
    spin: bool = False
    saturation: float = 1.0
    brightness: float = 1.0
    font: str | None = None
    skip_refine: bool = False


@dataclass
class Session:
    session_id: str
    args: dict[str, Any]
    blend_path: str
    glb_path: str | None = None
    status: str = "paused"         # "paused" or "done"
    created: str = field(default_factory=lambda: date.today().isoformat())


def _new_session_dir() -> tuple[str, Path]:
    sid = f"{date.today().isoformat()}-{secrets.token_hex(3)}"
    d = SESSIONS_DIR / sid
    d.mkdir(parents=True, exist_ok=True)
    return sid, d


def _write_manifest(session_dir: Path, session: Session) -> None:
    (session_dir / "manifest.json").write_text(json.dumps(asdict(session), indent=2))


def _read_manifest(session_dir: Path) -> Session:
    data = json.loads((session_dir / "manifest.json").read_text())
    return Session(**data)


def _finalize_output(frames_dir: Path, args: PipelineArgs) -> Path:
    """Assemble frames into final output — either a single PNG or sprite sheet."""
    output = Path(args.output).expanduser().resolve()
    if args.spin and args.frames > 1:
        return build_spritesheet(
            frames_dir,
            output,
            saturation=args.saturation,
            brightness=args.brightness,
        )
    # still: just copy/process the single frame
    from PIL import Image, ImageEnhance
    still = frames_dir / "frame_000.png"
    if not still.exists():
        # maybe output was already the still
        if output.exists():
            return output
        raise FileNotFoundError(f"Expected still frame at {still}")
    img = Image.open(still).convert("RGBA")
    if args.saturation != 1.0:
        img = ImageEnhance.Color(img).enhance(args.saturation)
    if args.brightness != 1.0:
        img = ImageEnhance.Brightness(img).enhance(args.brightness)
    output.parent.mkdir(parents=True, exist_ok=True)
    img.save(output)
    return output


def run(args: PipelineArgs, *, pause_after_blend: bool = False) -> Path | str:
    """Run a full pipeline. If pause_after_blend, returns session id instead of output path."""
    sid, session_dir = _new_session_dir()
    blend_path = session_dir / "scene.blend"
    frames_dir = session_dir / "frames"
    frames_dir.mkdir(exist_ok=True)

    glb_path: Path | None = None
    num_frames = args.frames if args.spin else 1

    # Step 1: build the Blender scene (+ optionally render)
    if args.source == "text":
        text_src.validate(args.value)
        render.build_text_scene(
            args.value,
            font=args.font,
            save_blend=blend_path,
            frames=num_frames,
            size=args.size,
            output=frames_dir,
            angle=args.angle,
            axis=args.axis,
            spin=args.spin,
            no_render=pause_after_blend,
        )
    elif args.source == "model":
        model_path = model_src.resolve(args.value)
        render.build_model_scene(
            model_path,
            save_blend=blend_path,
            frames=num_frames,
            size=args.size,
            output=frames_dir,
            angle=args.angle,
            axis=args.axis,
            spin=args.spin,
            no_render=pause_after_blend,
        )
    elif args.source == "meshy":
        glb_path = session_dir / "model.glb"
        meshy_src.fetch_glb(args.value, glb_path, skip_refine=args.skip_refine)
        render.build_model_scene(
            glb_path,
            save_blend=blend_path,
            frames=num_frames,
            size=args.size,
            output=frames_dir,
            angle=args.angle,
            axis=args.axis,
            spin=args.spin,
            no_render=pause_after_blend,
        )
    else:
        raise ValueError(f"Unknown source: {args.source}")

    # Persist manifest
    session = Session(
        session_id=sid,
        args=asdict(args),
        blend_path=str(blend_path),
        glb_path=str(glb_path) if glb_path else None,
        status="paused" if pause_after_blend else "done",
    )
    _write_manifest(session_dir, session)

    if pause_after_blend:
        print(f"\n[paused] Scene saved: {blend_path}")
        print(f"Open it in Blender, tweak, save, then run:")
        print(f"    puffbox resume {sid}\n")
        return sid

    output = _finalize_output(frames_dir, args)
    session.status = "done"
    _write_manifest(session_dir, session)
    return output


def resume(session_id: str) -> Path:
    session_dir = SESSIONS_DIR / session_id
    if not session_dir.exists():
        raise FileNotFoundError(f"No session: {session_id}")
    session = _read_manifest(session_dir)
    args = PipelineArgs(**session.args)
    frames_dir = session_dir / "frames"
    frames_dir.mkdir(exist_ok=True)
    num_frames = args.frames if args.spin else 1

    render.render_from_blend(
        Path(session.blend_path),
        frames=num_frames,
        size=args.size,
        output=frames_dir,
    )
    output = _finalize_output(frames_dir, args)
    session.status = "done"
    _write_manifest(session_dir, session)
    return output
