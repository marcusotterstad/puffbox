"""Puffbox CLI — argparse entry point."""
from __future__ import annotations

import argparse
import sys

from .pipeline import PipelineArgs, run, resume


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--frames", type=int, default=12, help="Frames for sprite sheet (with --spin)")
    p.add_argument("--size", type=int, default=1024, help="Render size (px)")
    p.add_argument("--output", default="out.png", help="Output PNG path")
    p.add_argument("--angle", type=float, default=18, help="Camera elevation (deg)")
    p.add_argument("--axis", default="Z", choices=["X", "Y", "Z"], help="Spin axis")
    p.add_argument("--spin", action="store_true", help="Spin 360° and output sprite sheet")
    p.add_argument("--saturation", type=float, default=1.0)
    p.add_argument("--brightness", type=float, default=1.0)
    p.add_argument("--pause-after-blend", action="store_true",
                   help="Stop after building the .blend so you can hand-tweak in Blender")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="puffbox",
        description="Generate pre-rendered puffy 3D assets (Y2K / Frutiger Aero aesthetic).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p_text = sub.add_parser("text", help="Puffy 3D balloon text")
    p_text.add_argument("text", help="The word(s) to render")
    p_text.add_argument("--font", default=None, help="Path to .ttf/.otf font")
    _add_common(p_text)

    p_model = sub.add_parser("model", help="Render an existing 3D model file")
    p_model.add_argument("model", help="Path to .glb/.fbx/.obj")
    _add_common(p_model)

    p_meshy = sub.add_parser("meshy", help="Generate via Meshy AI text-to-3D then render")
    p_meshy.add_argument("prompt", help="Description for Meshy")
    p_meshy.add_argument("--skip-refine", action="store_true", help="Preview-only (faster)")
    _add_common(p_meshy)

    p_resume = sub.add_parser("resume", help="Resume a paused session")
    p_resume.add_argument("session_id")

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.cmd == "resume":
            out = resume(args.session_id)
            print(f"[done] {out}")
            return 0

        source_map = {"text": ("text", "text"), "model": ("model", "model"), "meshy": ("meshy", "prompt")}
        source, value_attr = source_map[args.cmd]
        pargs = PipelineArgs(
            source=source,
            value=getattr(args, value_attr),
            frames=args.frames,
            size=args.size,
            output=args.output,
            angle=args.angle,
            axis=args.axis,
            spin=args.spin,
            saturation=args.saturation,
            brightness=args.brightness,
            font=getattr(args, "font", None),
            skip_refine=getattr(args, "skip_refine", False),
        )
        result = run(pargs, pause_after_blend=args.pause_after_blend)
        if args.pause_after_blend:
            print(f"[paused] session: {result}")
        else:
            print(f"[done] {result}")
        return 0
    except Exception as e:
        print(f"[error] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
