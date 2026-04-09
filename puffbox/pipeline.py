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
from .spritesheet import build_spritesheet, build_gif

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
    edit: bool = False             # if True: build scene → open Blender GUI → wait → render
    fps: float = 20.0              # frames per second when output is a .gif


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
    """Assemble frames into the final output. The output format is decided
    by the file extension of args.output:

      - .gif  → animated GIF (requires >1 frame; falls back to single still
                if only one frame was rendered)
      - .png  → sprite sheet if >1 frame, single still if 1 frame
      - other → single still PNG

    The number of frames is detected by counting frame_*.png files in
    frames_dir, so --edit mode sessions produce GIFs/sprite sheets
    automatically based on what the user actually built — no separate flag.
    """
    output = Path(args.output).expanduser().resolve()
    frames = sorted(frames_dir.glob("frame_*.png"))
    if not frames:
        raise FileNotFoundError(f"No rendered frames in {frames_dir}")

    suffix = output.suffix.lower()

    if len(frames) > 1 and suffix == ".gif":
        return build_gif(
            frames_dir,
            output,
            fps=args.fps,
            saturation=args.saturation,
            brightness=args.brightness,
        )

    if len(frames) > 1:
        return build_spritesheet(
            frames_dir,
            output,
            saturation=args.saturation,
            brightness=args.brightness,
        )

    # Single still
    from PIL import Image, ImageEnhance
    img = Image.open(frames[0]).convert("RGBA")
    if args.saturation != 1.0:
        img = ImageEnhance.Color(img).enhance(args.saturation)
    if args.brightness != 1.0:
        img = ImageEnhance.Brightness(img).enhance(args.brightness)
    output.parent.mkdir(parents=True, exist_ok=True)
    img.save(output)
    return output


def run(args: PipelineArgs, *, pause_after_blend: bool = False) -> Path | str:
    """Run a full pipeline.

    Modes:
    - Default: build scene → render → output
    - pause_after_blend=True: build scene → save .blend → STOP. Returns session id.
      Caller resumes later with `puffbox resume <id>`.
    - args.edit=True: build scene → open Blender GUI (blocking) → wait for user
      to save and close → render whatever they set up → output. One-shot flow,
      no separate resume command needed.
    """
    sid, session_dir = _new_session_dir()
    blend_path = session_dir / "scene.blend"
    frames_dir = session_dir / "frames"
    frames_dir.mkdir(exist_ok=True)

    glb_path: Path | None = None

    # In edit mode we always defer the render until after the user has tweaked
    # the .blend in Blender's GUI.
    skip_initial_render = pause_after_blend or args.edit

    # Only pre-stretch the timeline to args.frames when there's an actual
    # multi-frame intent (spin or edit). Otherwise leave it at 1 so a saved
    # still session doesn't carry a phantom frame range that would trick
    # `resume` into producing a sprite sheet on the next run.
    build_frames = args.frames if (args.spin or args.edit) else 1

    # Step 1: build the Blender scene (+ optionally render)
    if args.source == "text":
        text_src.validate(args.value)
        render.build_text_scene(
            args.value,
            font=args.font,
            save_blend=blend_path,
            frames=build_frames,
            size=args.size,
            output=frames_dir,
            angle=args.angle,
            axis=args.axis,
            spin=args.spin,
            no_render=skip_initial_render,
        )
    elif args.source == "model":
        model_path = model_src.resolve(args.value)
        render.build_model_scene(
            model_path,
            save_blend=blend_path,
            frames=build_frames,
            size=args.size,
            output=frames_dir,
            angle=args.angle,
            axis=args.axis,
            spin=args.spin,
            no_render=skip_initial_render,
        )
    elif args.source == "meshy":
        glb_path = session_dir / "model.glb"
        meshy_src.fetch_glb(args.value, glb_path, skip_refine=args.skip_refine)
        render.build_model_scene(
            glb_path,
            save_blend=blend_path,
            frames=build_frames,
            size=args.size,
            output=frames_dir,
            angle=args.angle,
            axis=args.axis,
            spin=args.spin,
            no_render=skip_initial_render,
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

    if args.edit:
        # Open Blender GUI on the scene, block until user closes it.
        render.open_in_blender_gui(blend_path)
        # Then render whatever they set up, auto-detecting the frame range
        # from the (now possibly hand-edited) scene.
        render.render_from_blend(
            blend_path,
            frames=0,  # 0 = auto-detect from scene.frame_start..frame_end
            size=args.size,
            output=frames_dir,
        )

    output = _finalize_output(frames_dir, args)
    session.status = "done"
    _write_manifest(session_dir, session)
    return output


def resume(
    session_id: str,
    *,
    size: int | None = None,
    output: str | None = None,
    frames: int | None = None,
) -> Path:
    """Re-render a saved session. Optional kwargs override the manifest:
    - size:    re-render at a different resolution (e.g. 128 from a 512 source)
    - output:  write the result somewhere new instead of overwriting the old one
    - frames:  override the frame count auto-detected from the .blend
    """
    session_dir = SESSIONS_DIR / session_id
    if not session_dir.exists():
        raise FileNotFoundError(f"No session: {session_id}")
    session = _read_manifest(session_dir)
    # Drop unknown fields gracefully (forward-compat with older manifests).
    known = {f.name for f in PipelineArgs.__dataclass_fields__.values()}
    args = PipelineArgs(**{k: v for k, v in session.args.items() if k in known})
    if size is not None:
        args.size = size
    if output is not None:
        args.output = output
    if frames is not None:
        args.frames = frames

    frames_dir = session_dir / "frames"
    frames_dir.mkdir(exist_ok=True)

    # Wipe stale frames from any previous render so the finalize step counts
    # only what THIS render produced.
    for old in frames_dir.glob("frame_*.png"):
        old.unlink()

    render.render_from_blend(
        Path(session.blend_path),
        frames=frames or 0,  # 0 = auto-detect from scene.frame_start..frame_end
        size=args.size,
        output=frames_dir,
    )
    output_path = _finalize_output(frames_dir, args)
    session.status = "done"
    _write_manifest(session_dir, session)
    return output_path


def list_sessions() -> list[dict]:
    """Return all sessions sorted newest-first. Each entry is the parsed manifest."""
    sessions = []
    if not SESSIONS_DIR.exists():
        return sessions
    for d in sorted(SESSIONS_DIR.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        manifest = d / "manifest.json"
        if not manifest.exists():
            continue
        try:
            data = json.loads(manifest.read_text())
            # Decorate with whether the .blend still exists on disk
            data["_blend_exists"] = Path(data.get("blend_path", "")).exists()
            sessions.append(data)
        except Exception:
            continue
    return sessions
