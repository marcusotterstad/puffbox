"""
Blender script: render a scene (already built or to-be-built from a model) as
either a single still or a spinning sprite sheet of N frames.

Two modes:

  1. build: import a model file, set up camera/lighting/spin, optionally save
     a .blend file, optionally render frames.
  2. render-only: open an existing .blend (possibly hand-tweaked by the user)
     and render frames from it.

Usage (from terminal):
    blender --background --python render_sprite.py -- --mode build \\
        --model path/to/file.glb --frames 12 --size 512 \\
        --output frames/ --save-blend scene.blend --no-render

    blender --background --python render_sprite.py -- --mode render \\
        --blend scene.blend --frames 12 --output frames/
"""

import bpy
import sys
import os
import math
from mathutils import Vector


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for collection in bpy.data.collections:
        if collection.name != bpy.context.scene.collection.name:
            bpy.data.collections.remove(collection)


def import_model(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    if ext in ('.glb', '.gltf'):
        bpy.ops.import_scene.gltf(filepath=filepath)
    elif ext == '.fbx':
        bpy.ops.import_scene.fbx(filepath=filepath)
    elif ext == '.obj':
        bpy.ops.wm.obj_import(filepath=filepath)
    else:
        raise ValueError(f"Unsupported format: {ext}")
    imported = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
    if not imported:
        imported = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    return imported


def get_bounding_box(objects):
    min_co = Vector((float('inf'),) * 3)
    max_co = Vector((float('-inf'),) * 3)
    for obj in objects:
        for corner in obj.bound_box:
            world = obj.matrix_world @ Vector(corner)
            for i in range(3):
                min_co[i] = min(min_co[i], world[i])
                max_co[i] = max(max_co[i], world[i])
    return min_co, max_co


def setup_camera(objects, elevation_deg=25, padding=1.15):
    min_co, max_co = get_bounding_box(objects)
    center = (min_co + max_co) / 2
    size = max_co - min_co
    max_dim = max(size.x, size.y, size.z) or 1.0

    cam_data = bpy.data.cameras.new("PuffCam")
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = max_dim * padding
    cam_obj = bpy.data.objects.new("PuffCam", cam_data)
    bpy.context.collection.objects.link(cam_obj)

    elevation = math.radians(elevation_deg)
    distance = max_dim * 4
    cam_obj.location = (
        center.x,
        center.y - distance * math.cos(elevation),
        center.z + distance * math.sin(elevation),
    )
    direction = center - cam_obj.location
    cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = cam_obj
    return cam_obj, center, size


def setup_puffy_lighting(center, size):
    """Soft key + blue rim, tuned for the puffy white aesthetic."""
    max_dim = max(size) or 1.0

    # Key light — warm-white, upper-front. Sun energy in Blender is in W/m²;
    # 1.0 is already bright. Keep things under ~1.5 to preserve shading.
    key_data = bpy.data.lights.new("Key", 'SUN')
    key_data.energy = 1.2
    key_data.color = (1.0, 0.98, 0.95)
    key_data.angle = math.radians(35)
    key_obj = bpy.data.objects.new("Key", key_data)
    bpy.context.collection.objects.link(key_obj)
    key_obj.location = (center.x + max_dim, center.y - max_dim * 2, center.z + max_dim * 3)
    key_obj.rotation_euler = (math.radians(55), 0, math.radians(25))

    # Fill — very soft
    fill_data = bpy.data.lights.new("Fill", 'SUN')
    fill_data.energy = 0.35
    fill_data.color = (0.95, 0.97, 1.0)
    fill_obj = bpy.data.objects.new("Fill", fill_data)
    bpy.context.collection.objects.link(fill_obj)
    fill_obj.location = (center.x - max_dim * 2, center.y - max_dim, center.z + max_dim)
    fill_obj.rotation_euler = (math.radians(70), 0, math.radians(-45))

    # Blue rim from above/behind
    rim_data = bpy.data.lights.new("Rim", 'SUN')
    rim_data.energy = 0.6
    rim_data.color = (0.55, 0.75, 1.0)
    rim_obj = bpy.data.objects.new("Rim", rim_data)
    bpy.context.collection.objects.link(rim_obj)
    rim_obj.location = (center.x, center.y + max_dim * 2, center.z + max_dim * 3)
    rim_obj.rotation_euler = (math.radians(-140), 0, 0)

    # Faint ambient world light so shadow sides aren't pitch black
    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("PuffWorld")
        bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.85, 0.90, 1.0, 1.0)
        bg.inputs[1].default_value = 0.4


def setup_render(size):
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
    scene.render.resolution_x = size
    scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    # Enable raytraced shadows / AO where available for softer look.
    try:
        scene.eevee.use_raytracing = True
    except Exception:
        pass
    scene.view_settings.look = 'None'
    scene.view_settings.view_transform = 'Standard'


def create_spin(objects, center, num_frames, axis='Z'):
    empty = bpy.data.objects.new("PuffPivot", None)
    bpy.context.collection.objects.link(empty)
    empty.location = center
    for obj in objects:
        if obj.parent is None:
            obj.parent = empty
            obj.matrix_parent_inverse = empty.matrix_world.inverted()

    axis_idx = {'X': 0, 'Y': 1, 'Z': 2}[axis.upper()]
    scene = bpy.context.scene
    scene.frame_start = 0
    scene.frame_end = max(num_frames - 1, 0)
    empty.rotation_euler[axis_idx] = 0
    empty.keyframe_insert("rotation_euler", index=axis_idx, frame=0)
    empty.rotation_euler[axis_idx] = math.radians(360)
    empty.keyframe_insert("rotation_euler", index=axis_idx, frame=num_frames)
    if empty.animation_data and empty.animation_data.action:
        for fc in empty.animation_data.action.fcurves:
            for kf in fc.keyframe_points:
                kf.interpolation = 'LINEAR'
    return empty


def render_frames(output_dir, num_frames):
    os.makedirs(output_dir, exist_ok=True)
    scene = bpy.context.scene
    for frame in range(num_frames):
        scene.frame_set(frame)
        filepath = os.path.join(output_dir, f"frame_{frame:03d}.png")
        scene.render.filepath = filepath
        bpy.ops.render.render(write_still=True)
        print(f"Rendered frame {frame + 1}/{num_frames}: {filepath}")


def render_still(output_path):
    scene = bpy.context.scene
    scene.frame_set(scene.frame_start)
    scene.render.filepath = output_path
    bpy.ops.render.render(write_still=True)
    print(f"Rendered still: {output_path}")


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["build", "render"], default="build")
    p.add_argument("--model", default=None)
    p.add_argument("--blend", default=None)
    p.add_argument("--frames", type=int, default=1)
    p.add_argument("--size", type=int, default=512)
    p.add_argument("--output", default="./frames")
    p.add_argument("--angle", type=float, default=18)
    p.add_argument("--axis", default="Z", choices=["X", "Y", "Z"])
    p.add_argument("--spin", action="store_true")
    p.add_argument("--save-blend", default=None, help="Save .blend after setup")
    p.add_argument("--no-render", action="store_true")
    return p.parse_args(argv)


def main():
    args = parse_args()

    if args.mode == "render":
        if not args.blend or not os.path.exists(args.blend):
            print(f"Error: --blend file not found: {args.blend}")
            sys.exit(1)
        bpy.ops.wm.open_mainfile(filepath=args.blend)
        # Preserve the blend's aspect ratio; only scale if --size differs.
        scene = bpy.context.scene
        rx, ry = scene.render.resolution_x, scene.render.resolution_y
        if rx and ry:
            aspect = rx / ry
            if aspect >= 1:
                scene.render.resolution_x = int(args.size * aspect)
                scene.render.resolution_y = args.size
            else:
                scene.render.resolution_x = args.size
                scene.render.resolution_y = int(args.size / aspect)
        else:
            scene.render.resolution_x = args.size
            scene.render.resolution_y = args.size
        scene.render.film_transparent = True
        scene.render.image_settings.file_format = 'PNG'
        scene.render.image_settings.color_mode = 'RGBA'
        if args.frames > 1:
            render_frames(args.output, args.frames)
        else:
            render_still(args.output if args.output.endswith(".png")
                         else os.path.join(args.output, "frame_000.png"))
        return

    # build mode
    clear_scene()
    if not args.model:
        print("Error: --model required in build mode")
        sys.exit(1)
    model_path = os.path.abspath(args.model)
    if not os.path.exists(model_path):
        print(f"Error: model not found: {model_path}")
        sys.exit(1)

    print(f"Importing {model_path}...")
    objects = import_model(model_path)
    print(f"Imported {len(objects)} mesh(es)")

    _, center, size = setup_camera(objects, args.angle)
    setup_puffy_lighting(center, size)
    setup_render(args.size)

    num_frames = args.frames if args.spin else 1
    if args.spin:
        create_spin(objects, center, num_frames, args.axis)

    if args.save_blend:
        os.makedirs(os.path.dirname(os.path.abspath(args.save_blend)), exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args.save_blend))
        print(f"Saved blend: {args.save_blend}")

    if args.no_render:
        return

    if args.spin:
        render_frames(args.output, num_frames)
    else:
        out = args.output if args.output.endswith(".png") else os.path.join(args.output, "frame_000.png")
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        render_still(out)


if __name__ == "__main__":
    main()
