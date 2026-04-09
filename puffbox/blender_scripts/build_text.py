"""
Blender script: build puffy white 3D balloon text from a string, then hand off
to render_sprite's setup (camera, lighting, render) by directly calling into it.

Usage:
    blender --background --python build_text.py -- --text "Aerdash" \\
        --frames 1 --size 1024 --output out.png \\
        [--font /path/to/font.ttf] [--save-blend scene.blend] [--no-render] [--spin]

Tunable constants live at the top of the file so the puffy look can be
fine-tuned without digging through the code.
"""

import bpy
import sys
import os
import math
from mathutils import Vector
from mathutils import Vector

# ---- Puffy look tunables -----------------------------------------------------
EXTRUDE = 0.35           # text extrusion depth (front-to-back thickness)
BEVEL_DEPTH = 0.04       # rounded edge on the text curve itself — keep small to avoid self-intersection on thin glyph strokes
BEVEL_RES = 4            # bevel resolution
SOLIDIFY_THICKNESS = 0.0   # set >0 to inflate more via solidify
VOXEL_REMESH_SIZE = 0.0  # voxel remesh disabled — kept the v2 look (small spikes acceptable, was way better than the post-remesh attempts)
CAST_FACTOR = 0.0
SUBSURF_LEVELS = 4       # viewport/render subdivision
SHRINKWRAP_OFFSET = 0.0  # set >0 to puff outward more
BASE_COLOR = (0.95, 0.96, 0.98, 1.0)  # slightly off-white so shading reads
SUBSURFACE_WEIGHT = 0.15
SUBSURFACE_RADIUS = (0.3, 0.3, 0.3)
ROUGHNESS = 0.45
SPECULAR = 0.5
CAMERA_ELEVATION_DEG = 12
CAMERA_PADDING = 1.12        # ortho scale padding
# -----------------------------------------------------------------------------

# Make sibling module importable
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import render_sprite  # noqa: E402


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)


def find_font(font_path_hint=None):
    """Return a bpy Font. Tries hint, then common rounded fonts, then default."""
    candidates = []
    if font_path_hint:
        candidates.append(font_path_hint)
    # Common rounded sans locations on Linux
    candidates += [
        "/usr/share/fonts/truetype/fredoka/Fredoka-Bold.ttf",
        "/usr/share/fonts/truetype/nunito/Nunito-Black.ttf",
        "/usr/share/fonts/truetype/quicksand/Quicksand-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for p in candidates:
        if p and os.path.exists(p):
            try:
                return bpy.data.fonts.load(p), p
            except Exception:
                continue
    return None, None  # Blender built-in Bfont


def build_text_object(text, font_path_hint=None):
    bpy.ops.object.text_add(location=(0, 0, 0))
    text_obj = bpy.context.object
    text_obj.data.body = text
    text_obj.data.extrude = EXTRUDE
    text_obj.data.bevel_depth = BEVEL_DEPTH
    text_obj.data.bevel_resolution = BEVEL_RES
    text_obj.data.align_x = 'CENTER'
    text_obj.data.align_y = 'CENTER'
    # Stand the text upright so it faces -Y (default camera direction).
    text_obj.rotation_euler = (math.radians(90), 0, 0)

    font, font_path = find_font(font_path_hint)
    if font:
        text_obj.data.font = font
        print(f"Font: {font_path}")
    else:
        print("Font: Blender default (Bfont) — install Fredoka/Nunito for better look")

    # Convert to mesh so modifiers behave nicely
    bpy.ops.object.convert(target='MESH')
    mesh_obj = bpy.context.object

    # Clean up mesh — merge near-duplicate verts and recalculate normals.
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.001)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')

    # External fonts may give the converted mesh a huge matrix_world scale.
    # Bake transforms into vertices, then resize so biggest dim = 1 unit.
    bpy.ops.object.select_all(action='DESELECT')
    mesh_obj.select_set(True)
    bpy.context.view_layer.objects.active = mesh_obj
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    verts = mesh_obj.data.vertices
    if verts:
        xs = [v.co.x for v in verts]; ys = [v.co.y for v in verts]; zs = [v.co.z for v in verts]
        dx = max(xs) - min(xs); dy = max(ys) - min(ys); dz = max(zs) - min(zs)
        biggest = max(dx, dy, dz, 1e-6)
        scale = 1.0 / biggest
        for v in verts:
            v.co = v.co * scale
        mesh_obj.data.update()

    # Solidify for extra thickness/inflation (off by default — voxel remesh handles inflation)
    if SOLIDIFY_THICKNESS > 0:
        solid = mesh_obj.modifiers.new("Solidify", 'SOLIDIFY')
        solid.thickness = SOLIDIFY_THICKNESS
        solid.offset = 0
        solid.use_even_offset = True
        solid.use_quality_normals = True

    # Voxel remesh — uniform watertight topology, no self-intersections.
    if VOXEL_REMESH_SIZE > 0:
        remesh = mesh_obj.modifiers.new("Remesh", 'REMESH')
        remesh.mode = 'VOXEL'
        remesh.voxel_size = VOXEL_REMESH_SIZE
        remesh.use_smooth_shade = True
        bpy.ops.object.modifier_apply(modifier="Remesh")

    # Cast to sphere — pushes vertices outward toward a sphere envelope.
    # This is what gives the actual "balloon / inflated" look.
    if CAST_FACTOR > 0:
        cast = mesh_obj.modifiers.new("Cast", 'CAST')
        cast.cast_type = 'SPHERE'
        cast.factor = CAST_FACTOR
        cast.use_x = True
        cast.use_y = True
        cast.use_z = True

    # Subdivision surface for smooth puffy shape
    subsurf = mesh_obj.modifiers.new("Subsurf", 'SUBSURF')
    subsurf.levels = 2
    subsurf.render_levels = SUBSURF_LEVELS

    bpy.ops.object.shade_smooth()
    return mesh_obj


def make_puffy_material():
    mat = bpy.data.materials.new("PuffyWhite")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    if bsdf is None:
        return mat
    bsdf.inputs["Base Color"].default_value = BASE_COLOR
    bsdf.inputs["Roughness"].default_value = ROUGHNESS
    # Input names vary across Blender versions; set defensively.
    for name, value in [
        ("Subsurface Weight", SUBSURFACE_WEIGHT),
        ("Subsurface", SUBSURFACE_WEIGHT),
        ("Subsurface Radius", SUBSURFACE_RADIUS),
        ("Subsurface Color", (1.0, 1.0, 1.0, 1.0)),
        ("Specular IOR Level", SPECULAR),
        ("Specular", SPECULAR),
    ]:
        inp = bsdf.inputs.get(name)
        if inp is not None:
            try:
                inp.default_value = value
            except Exception:
                pass
    return mat


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--text", required=True)
    p.add_argument("--font", default=None)
    p.add_argument("--frames", type=int, default=1)
    p.add_argument("--size", type=int, default=1024)
    p.add_argument("--output", default="out.png")
    p.add_argument("--angle", type=float, default=CAMERA_ELEVATION_DEG)
    p.add_argument("--axis", default="Y", choices=["X", "Y", "Z"])
    p.add_argument("--spin", action="store_true")
    p.add_argument("--save-blend", default=None)
    p.add_argument("--no-render", action="store_true")
    return p.parse_args(argv)


def main():
    args = parse_args()
    clear_scene()

    mesh_obj = build_text_object(args.text, args.font)
    mat = make_puffy_material()
    if mesh_obj.data.materials:
        mesh_obj.data.materials[0] = mat
    else:
        mesh_obj.data.materials.append(mat)

    # Compute bounding box of the text mesh using the evaluated depsgraph,
    # so Subsurf/Solidify modifiers are accounted for.
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = mesh_obj.evaluated_get(depsgraph)
    min_co = Vector((float('inf'),) * 3)
    max_co = Vector((float('-inf'),) * 3)
    for v in eval_obj.data.vertices:
        world = mesh_obj.matrix_world @ v.co
        for i in range(3):
            min_co[i] = min(min_co[i], world[i])
            max_co[i] = max(max_co[i], world[i])
    center = (min_co + max_co) / 2
    size = max_co - min_co

    # Custom ortho camera for text: frame horizontally, wide aspect.
    scene = bpy.context.scene
    text_len = max(len(args.text), 1)
    aspect_w = min(max(text_len * 0.55, 1.0), 4.0)
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
    scene.render.resolution_x = int(args.size * aspect_w)
    scene.render.resolution_y = args.size
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'

    cam_data = bpy.data.cameras.new("PuffCam")
    cam_data.type = 'ORTHO'
    # ortho_scale defines the longer render axis in world units.
    # We need the text width (size.x) to fit horizontally with padding.
    needed_width = size.x * CAMERA_PADDING
    needed_height = size.y * CAMERA_PADDING * 1.4  # extra vertical room for rim light halo
    # Pick whichever forces a larger ortho_scale.
    cam_data.ortho_scale = max(needed_width, needed_height * aspect_w)
    cam_obj = bpy.data.objects.new("PuffCam", cam_data)
    bpy.context.collection.objects.link(cam_obj)

    elev = math.radians(args.angle)
    dist = max(size.x, size.y, size.z, 1.0) * 5
    cam_obj.location = (
        center.x,
        center.y - dist * math.cos(elev),
        center.z + dist * math.sin(elev),
    )
    direction = center - Vector(cam_obj.location)
    cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    scene.camera = cam_obj

    render_sprite.setup_puffy_lighting(center, size)
    # Don't call setup_render here — it would overwrite resolution to square.
    try:
        scene.eevee.use_raytracing = True
    except Exception:
        pass
    scene.view_settings.look = 'None'
    scene.view_settings.view_transform = 'Standard'

    num_frames = args.frames if args.spin else 1
    if args.spin:
        render_sprite.create_spin([mesh_obj], center, num_frames, args.axis)
    else:
        # Pre-stretch the timeline to args.frames so --edit users land on a
        # ready N-frame timeline they can keyframe into immediately.
        render_sprite.setup_timeline(args.frames)

    render_sprite.set_viewport_to_camera()

    if args.save_blend:
        os.makedirs(os.path.dirname(os.path.abspath(args.save_blend)), exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args.save_blend))
        print(f"Saved blend: {args.save_blend}")

    if args.no_render:
        return

    if args.spin:
        render_sprite.render_frames(args.output, num_frames)
    else:
        out = args.output if args.output.endswith(".png") else os.path.join(args.output, "frame_000.png")
        os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
        render_sprite.render_still(out)


if __name__ == "__main__":
    main()
