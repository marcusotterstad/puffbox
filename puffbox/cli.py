"""Puffbox CLI — argparse entry point."""
from __future__ import annotations

import argparse
import sys

from .pipeline import PipelineArgs, run, resume, list_sessions


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
                   help="Stop after building the .blend so you can hand-tweak in Blender, then run `puffbox resume <id>`")
    p.add_argument("--edit", action="store_true",
                   help="Open Blender GUI on the built scene; when you save and close Blender, puffbox renders whatever you set up automatically (one-shot edit flow)")


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

    p_resume = sub.add_parser("resume", help="Re-render a saved session (paused or done). Override size/frames/output to remix.")
    p_resume.add_argument("session_id")
    p_resume.add_argument("--size", type=int, default=None,
                          help="Override render size — e.g. resume a 512 session at 128")
    p_resume.add_argument("--output", default=None,
                          help="Override output path instead of overwriting the original")
    p_resume.add_argument("--frames", type=int, default=None,
                          help="Override frame count (default: auto-detect from .blend)")

    p_list = sub.add_parser("list", help="List all saved puffbox sessions, newest first")
    p_list.add_argument("--limit", type=int, default=20, help="Max rows to show (default: 20, 0 = all)")

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.cmd == "resume":
            out = resume(
                args.session_id,
                size=args.size,
                output=args.output,
                frames=args.frames,
            )
            print(f"[done] {out}")
            return 0

        if args.cmd == "list":
            sessions = list_sessions()
            if not sessions:
                print("No puffbox sessions yet.")
                return 0
            limit = args.limit if args.limit > 0 else len(sessions)
            shown = sessions[:limit]
            # Compute column widths
            print(f"{'ID':<24} {'DATE':<12} {'SRC':<6} {'VALUE':<28} {'SIZE':>5} {'FRM':>4} {'STATUS':<8} BLEND")
            print("-" * 100)
            for s in shown:
                a = s.get("args", {})
                value = str(a.get("value", ""))[:26]
                if len(str(a.get("value", ""))) > 26:
                    value = value + ".."
                blend_ok = "✓" if s.get("_blend_exists") else "✗"
                print(
                    f"{s.get('session_id', '?'):<24} "
                    f"{s.get('created', '?'):<12} "
                    f"{a.get('source', '?'):<6} "
                    f"{repr(value):<28} "
                    f"{a.get('size', '?'):>5} "
                    f"{a.get('frames', '?'):>4} "
                    f"{s.get('status', '?'):<8} "
                    f"{blend_ok}"
                )
            if len(sessions) > limit:
                print(f"\n... {len(sessions) - limit} more (use --limit 0 to see all)")
            print(f"\nResume any session: puffbox resume <ID>")
            print(f"Resize:             puffbox resume <ID> --size 128 --output out.png")
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
            edit=args.edit,
        )
        if args.pause_after_blend and args.edit:
            print("[error] --pause-after-blend and --edit are mutually exclusive", file=sys.stderr)
            return 1
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
