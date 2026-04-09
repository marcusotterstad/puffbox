# Puffbox

Pre-rendered 3D assets in the 90s / Y2K / Frutiger Aero aesthetic — puffy white inflated shapes, soft lighting, transparent PNG sprites — with very low effort.

Puffbox turns a single command into a ready-to-drop sprite. Give it a word, a 3D model, or a text prompt; it drives Blender in the background and spits out a transparent PNG (or a sprite sheet) in the signature puffy-white look. When the defaults aren't quite right, drop into Blender for a few clicks and Puffbox finishes the rest automatically.

## Requirements

- Python 3.10+
- [Blender 4.0+](https://www.blender.org/download/) on your `$PATH` (or `$BLENDER_BIN`)
- A rounded sans-serif font for the best `puffbox text` results. Try one of:
  - [Fredoka](https://fonts.google.com/specimen/Fredoka)
  - [Nunito](https://fonts.google.com/specimen/Nunito)
  - [Quicksand](https://fonts.google.com/specimen/Quicksand)
  - Comic Sans (yes, really)

  If none are installed, Puffbox falls back to DejaVu Sans Bold, which still looks decent.

## Install

```bash
git clone <this repo> puffbox
cd puffbox
pip install -e .
```

## Usage

### Puffy 3D text — the flagship

```bash
# Single still PNG of the word "Aerdash" in puffy white material
puffbox text "Aerdash" --output aerdash.png

# 12-frame spinning sprite sheet
puffbox text "Puffbox" --spin --frames 12 --output puffbox.png

# Use a specific font
puffbox text "Hello" --font /usr/share/fonts/truetype/fredoka/Fredoka-Bold.ttf
```

### Tweak it in Blender, then let Puffbox finish — `--edit`

This is the killer feature. `--edit` builds the scene, opens Blender's GUI on it for you, and resumes the render automatically the moment you close Blender. The viewport opens **already in camera view**, the timeline is **already set to your `--frames` count**, and a sprite sheet is assembled if you keyframed an animation. No second command, no copy-pasting session ids.

```bash
# Build a 12-frame "Start" scene, open Blender, render whatever I set up
puffbox text "Start" --frames 12 --size 512 --output ~/start.png --edit
```

What happens:

1. Puffbox builds the puffy "Start" geometry, lights, camera, materials
2. Blender opens — **looking through the camera**, timeline ready at frames 1–12
3. You animate, tweak materials, move the camera, whatever. **Save** (Ctrl+S)
4. **Close Blender**. Puffbox detects the exit, renders all 12 frames, assembles the sprite sheet
5. Output lands at `~/start.png`

If you save with only 1 frame in your range, you get a single PNG. If you save with N frames, you get an N-frame sprite sheet. Puffbox decides the output type from what you actually built — there's no separate flag to remember.

### Render an existing 3D model

```bash
puffbox model path/to/mushroom.glb --spin --frames 12 --output mushroom.png
```

Supports `.glb`, `.gltf`, `.fbx`, `.obj`. Works with `--edit` too.

### Generate via Meshy AI text-to-3D

Requires `MESHY_API_KEY` in your environment or in `~/.env`.

```bash
puffbox meshy "a small cartoon mushroom" --spin --frames 12 --output mushroom.png
```

### See your history — `puffbox list`

Every Puffbox run is saved as a session at `~/.puffbox/sessions/<id>/` containing the `scene.blend`, the rendered frames, and a `manifest.json` with the original CLI args. Nothing is ever deleted automatically.

```bash
puffbox list                # newest 20
puffbox list --limit 0      # all of them
```

```
ID                       DATE         SRC    VALUE                         SIZE  FRM STATUS   BLEND
----------------------------------------------------------------------------------------------------
2026-04-09-9ee4e1        2026-04-09   text   'Start'                        512   12 done     ✓
2026-04-09-87a0ff        2026-04-09   text   'Aerdash'                      512    1 done     ✓
2026-04-09-ea751f        2026-04-09   text   'Puffbox'                      384   12 done     ✓
...
```

### Re-mix any session — `puffbox resume`

`resume` re-renders any saved session from its `.blend`. By default it reuses the original size/frames; CLI flags override anything you want to change. This is how you go back and produce a 128px version of a 512px asset, or a 6-frame version of a 12-frame loop, without rebuilding the scene.

```bash
# Same scene, smaller
puffbox resume 2026-04-09-9ee4e1 --size 128 --output ~/start_128.png

# Same scene, fewer frames
puffbox resume 2026-04-09-9ee4e1 --frames 6 --output ~/start_short.png

# Same scene, both
puffbox resume 2026-04-09-9ee4e1 --size 256 --frames 8 --output ~/start_remix.png

# Just re-render in place at the original settings
puffbox resume 2026-04-09-9ee4e1
```

`resume` also picks up any hand-edits you made if you opened the `.blend` in Blender between runs. The frame range is auto-detected from the `.blend` unless `--frames` overrides it.

### The advanced pause workflow — `--pause-after-blend`

If you want to do a long manual session in Blender across multiple sittings, use `--pause-after-blend` instead of `--edit`. It builds the scene, prints the session id, and exits — no Blender opens. Pick it back up later with `resume`.

```bash
$ puffbox text "Aerdash" --pause-after-blend
[paused] Scene saved: ~/.puffbox/sessions/2026-04-09-abc123/scene.blend
Open it in Blender, tweak, save, then run:
    puffbox resume 2026-04-09-abc123
```

For most one-shot tweaks, prefer `--edit`.

### Common flags

| flag                    | default     | description                                              |
| ----------------------- | ----------- | -------------------------------------------------------- |
| `--frames N`            | 12          | Sprite sheet frame count (also pre-stretches the timeline in `--edit` mode) |
| `--size N`              | 1024        | Render resolution in pixels (square or width-base)       |
| `--output PATH`         | `out.png`   | Output PNG path                                          |
| `--angle N`             | 18          | Camera elevation angle (degrees)                         |
| `--axis X\|Y\|Z`        | Z           | Spin axis when `--spin` is set                           |
| `--spin`                | off         | Auto-spin 360° → sprite sheet                            |
| `--saturation F`        | 1.0         | Post-process saturation multiplier                       |
| `--brightness F`        | 1.0         | Post-process brightness multiplier                       |
| `--edit`                | off         | Open Blender GUI on the built scene; render after close  |
| `--pause-after-blend`   | off         | Build only, exit. Resume later with `puffbox resume`    |

`resume`-only flags: `--size`, `--frames`, `--output` (all override the saved manifest).

## Sessions on disk

Each session lives at `~/.puffbox/sessions/<session-id>/`:

- `scene.blend` — the Blender file you can open and edit any time
- `manifest.json` — original CLI args so `resume` knows what to do
- `frames/` — rendered frames (cleared and rewritten on each `resume`)
- `model.glb` (meshy sessions only) — the downloaded source model

Session ids are date-prefixed (`YYYY-MM-DD-<hex>`), so `puffbox list` always sorts newest-first. To delete a session, just `rm -rf` its directory.

## Tuning the puffy look

The "puffy balloon text" material lives in [`puffbox/blender_scripts/build_text.py`](puffbox/blender_scripts/build_text.py). Tunable constants at the top of the file:

- `EXTRUDE` — front-to-back text thickness
- `BEVEL_DEPTH`, `BEVEL_RES` — rounded text edges (kept small to avoid self-intersection on thin fonts)
- `SUBSURF_LEVELS` — smoothness of the puffy look
- `SOLIDIFY_THICKNESS`, `VOXEL_REMESH_SIZE`, `CAST_FACTOR` — alternate inflation strategies, off by default
- `BASE_COLOR`, `SUBSURFACE_WEIGHT`, `ROUGHNESS`, `SPECULAR` — material
- `CAMERA_ELEVATION_DEG`, `CAMERA_PADDING` — framing

Lighting (soft key + blue rim + warm fill + blue-tinted world ambient) lives in [`puffbox/blender_scripts/render_sprite.py`](puffbox/blender_scripts/render_sprite.py) in `setup_puffy_lighting`.

If you find a tuning combo you like, the easiest way to make it permanent is to edit those constants directly — no recompile needed, the next run picks them up.

## Roadmap

Future ideas:

- **Material presets** — `--material puffy|glossy|jelly|frosted`
- **Per-letter inflation for text** — currently the whole word is one mesh; per-letter origin would give cleaner balloon shapes
- **GPT-Image input** — rasterize an AI image → depth → 3D displacement
- **Expanded Meshy modes** — sketch-to-3D, image-to-3D
- **Background presets** — optional cloud / gradient backdrops for full Y2K wallpaper vibes
- **Batch manifests** — describe a whole asset pack in YAML, run once
- **Web UI** — a tiny frontend for non-CLI users, so people can generate assets without installing Blender locally

## License

Released under the MIT license. Contributions welcome.
