# Puffbox

Pre-rendered 3D assets in the 90s / Y2K / Frutiger Aero aesthetic — puffy white inflated shapes, soft lighting, transparent PNG sprites — with very low effort.

Puffbox turns a single command into a ready-to-drop sprite. Give it a word, a 3D model, or a text prompt; it drives Blender in the background and spits out a transparent PNG (or a spinning sprite sheet) in the signature puffy-white Frutiger Aero look.

## Requirements

- Python 3.10+
- [Blender 4.0+](https://www.blender.org/download/) available on your `$PATH` (or set `$BLENDER_BIN`)
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

### Puffy 3D text (flagship feature)

```bash
# Single still PNG of the word "Aerdash" in puffy white material
puffbox text "Aerdash" --output aerdash.png

# 12-frame spinning sprite sheet
puffbox text "Puffbox" --spin --frames 12 --output puffbox.png

# Use a specific font
puffbox text "Hello" --font /usr/share/fonts/truetype/fredoka/Fredoka-Bold.ttf
```

### Render an existing 3D model

```bash
puffbox model path/to/mushroom.glb --spin --frames 12 --output mushroom.png
```

Supports `.glb`, `.gltf`, `.fbx`, `.obj`.

### Generate via Meshy AI text-to-3D

Requires `MESHY_API_KEY` in your environment or in `~/.env`.

```bash
puffbox meshy "a small cartoon mushroom" --spin --frames 12 --output mushroom.png
```

### Common flags

| flag                    | default     | description                                          |
| ----------------------- | ----------- | ---------------------------------------------------- |
| `--frames N`            | 12          | Frames for sprite sheet (with `--spin`)              |
| `--size N`              | 1024        | Render resolution (px, square or width-base)        |
| `--output PATH`         | `out.png`   | Output PNG path                                      |
| `--angle N`             | 18          | Camera elevation angle (degrees)                     |
| `--axis X\|Y\|Z`        | Z           | Spin axis                                            |
| `--spin`                | off         | Produce sprite sheet instead of single still         |
| `--saturation F`        | 1.0         | Post-process saturation multiplier                   |
| `--brightness F`        | 1.0         | Post-process brightness multiplier                   |
| `--pause-after-blend`   | off         | Stop after Blender setup so you can hand-tweak       |

## The pause / resume workflow (killer feature)

Automated pipelines are great until they aren't. Sometimes you need to nudge a material, rotate a letter, or reposition a rim light by hand. Puffbox lets you stop mid-pipeline, open the intermediate `.blend` in Blender, tweak whatever you want, then resume rendering.

```
$ puffbox text "Aerdash" --pause-after-blend
[1/3] Building text geometry in Blender...
[2/3] Saved intermediate scene to: ~/.puffbox/sessions/2026-04-09-abc123/scene.blend
       Open it in Blender, tweak whatever you want (animation, materials, lighting), save, then run:
       puffbox resume 2026-04-09-abc123

$ blender ~/.puffbox/sessions/2026-04-09-abc123/scene.blend
# (tweak the scene by hand, save, close)

$ puffbox resume 2026-04-09-abc123
[3/3] Rendering frames from your tweaked scene...
[done] Sprite sheet saved to: ./aerdash.png
```

Each session lives under `~/.puffbox/sessions/<session-id>/`:

- `scene.blend` — the Blender file
- `manifest.json` — original CLI args so `resume` knows what to do
- `frames/` — rendered frames
- `model.glb` (meshy sessions only) — the downloaded source model

## Tuning the puffy look

The "puffy balloon text" material lives in [`puffbox/blender_scripts/build_text.py`](puffbox/blender_scripts/build_text.py). Tunable constants at the top of the file control:

- `EXTRUDE`, `BEVEL_DEPTH`, `BEVEL_RES` — text extrusion and rounded edges
- `SOLIDIFY_THICKNESS` — extra inflation (set > 0 with care; can cause normal explosion on thin fonts)
- `SUBSURF_LEVELS` — smoothness of the puffy look
- `BASE_COLOR`, `SUBSURFACE_WEIGHT`, `ROUGHNESS`, `SPECULAR` — material
- `CAMERA_ELEVATION_DEG`, `CAMERA_PADDING` — framing

Lighting (soft key + rim + warm fill + blue-tinted world ambient) lives in [`puffbox/blender_scripts/render_sprite.py`](puffbox/blender_scripts/render_sprite.py) in `setup_puffy_lighting`.

## Roadmap

Future blocks / ideas:

- **Material presets** — `--material puffy|glossy|jelly|frosted`
- **GPT-Image input** — rasterize an AI image → depth → 3D displacement
- **Expanded Meshy modes** — sketch-to-3D, image-to-3D
- **Background presets** — optional cloud / gradient backdrops for full Y2K wallpaper vibes
- **Web UI** — a tiny Flask/FastAPI frontend for non-CLI users
- **Batch manifests** — describe a whole asset pack in YAML, run once

## Credits

Built by [Marcus](https://github.com/marcus) as part of the [Aerdash](https://github.com/marcus/Aerdash) project, whose UI is being rebuilt around this aesthetic. Seed code adapted from Aerdash's existing Blender render pipeline.

Released under the MIT license.
