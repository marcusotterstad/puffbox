# Puffbox

Type a word. Get puffy 3D balloon text. That's it.

Pre-rendered 3D assets in the chunky 90s CGI / CD-ROM kid-game aesthetic, generated from a one-line command. No Blender knowledge required.

<p align="center">
<img src="assets/puffbox_text_128.gif" alt="puffy 3D PUFFBOX text">
<br>
<code>puffbox text "PUFFBOX" --frames 12 --size 128 --output puffbox.gif</code>
</p>

## Install

Needs Python 3.10+ and Blender 4.0+ on `$PATH` (or set `$BLENDER_BIN`).

```bash
git clone https://github.com/marcusotterstad/puffbox
cd puffbox
pip install -e .
```

## Quick start

```bash
puffbox text "Aerdash"                            # puffy 3D text → PNG
puffbox text "Start" --frames 12 --output go.gif  # animated GIF
puffbox text "Edit" --edit                        # open Blender, tweak, save & close, puffbox renders
```

Output format is decided by the file extension on `--output`: `.gif` writes an animated GIF, `.png` writes a sprite sheet (or a single still if 1 frame).

## Render your own 3D models

Already have a `.glb`, `.fbx`, or `.obj`? Spin it through the same puffy pipeline:

<p align="center">
<img src="assets/puffbox_spin.gif" alt="rotating wrapped present">
<br>
<code>puffbox model gift_box.glb --spin --frames 12 --size 256 --axis Z --rotate-z 45 --output gift.gif</code>
</p>

```bash
puffbox model thing.glb --spin --frames 12        # spinning sprite sheet of any model
```

## Generate 3D from a prompt or image

If you set `MESHY_API_KEY` (sign up at [meshy.ai](https://www.meshy.ai)), Puffbox can generate the 3D model for you from text or an image, then render it in the same style.

<p align="center">
<img src="assets/mushroom_spin.gif" alt="spinning magical mushroom">
<br>
<code>puffbox meshy "magical glowing mushroom, purple cap, turquoise stem" --spin --frames 12 --size 64</code>
</p>

<p align="center">
<img src="assets/magnet_spin.gif" alt="spinning cartoon horseshoe magnet">
<br>
<code>puffbox meshy magnet.png --spin --frames 12 --size 64 --rotate-x 180</code>
</p>

```bash
puffbox meshy "a cartoon mushroom" --spin          # text-to-3D
puffbox meshy magnet.png --spin                    # image-to-3D (auto-detected from file extension)
```

## All commands

```bash
puffbox text "WORD"                               # puffy 3D balloon text
puffbox model file.glb --spin                     # render an existing 3D model
puffbox meshy "<prompt or image path>" --spin     # AI-generated 3D (needs MESHY_API_KEY)

puffbox list                                      # session history
puffbox resume <id> --size 128 --output a.gif     # re-render any past session
```

## Flags

| flag | description |
|---|---|
| `--frames N` | sprite sheet length / pre-stretched timeline in `--edit` |
| `--size N` | render resolution (px) |
| `--output PATH` | output path; `.gif` writes animated GIF, `.png` writes sprite sheet |
| `--spin` | auto 360° spin → sprite sheet or GIF |
| `--edit` | open Blender GUI; renders automatically when you save and close |
| `--fps N` | animation speed when output is a `.gif` (default 20) |
| `--axis X\|Y\|Z`, `--angle N`, `--saturation`, `--brightness` | tweaks |
| `--rotate-x N`, `--rotate-y N`, `--rotate-z N` | pre-spin rotate the imported mesh (`model` / `meshy`) |
| `--mesh-scale F`, `--center` | scale / recenter the imported mesh |

## Sessions

Every render is saved under `~/.puffbox/sessions/<id>/` as `scene.blend` + frames + `manifest.json`. `puffbox list` shows them, `puffbox resume <id>` re-renders — pass `--size` / `--frames` / `--output` to remix without redoing the slow steps.

## Hand-tweaking

Two ways to get into Blender mid-pipeline:

- `--edit` opens Blender already in camera view with the timeline pre-set to `--frames`. Save and close — Puffbox auto-renders whatever you built. If you keyframed an animation, you get a sprite sheet; if not, a single PNG.
- `--pause-after-blend` stops after the `.blend` is built. Open it manually, do anything, then `puffbox resume <id>` to finish.

Material and lighting tunables: top of `puffbox/blender_scripts/build_text.py` and `render_sprite.py`.

## License

[MIT](LICENSE).
