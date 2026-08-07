"""
Render every material in the current .blend onto a flat plane and save as PNG,
at a resolution you control (unlike the fixed 128x128 asset preview icons).

Run inside Blender's Scripting tab (open the file first, then Run Script),
OR headless via:
    blender --background yourfile.blend --python render_material_thumbnails.py

This builds its own temporary scene (plane + camera + lights), renders each
material, then cleans up — it does not touch or save your original scene.
"""

import bpy
import os

# --- CONFIG ---------------------------------------------------------------
OUTPUT_DIR = "/Users/XXXXXXXXX/blender/tmp"
RESOLUTION = 1000                # width & height in pixels
FILE_FORMAT = 'JPEG'
JPEG_QUALITY = 90                # 0-100
ENGINE = 'BLENDER_EEVEE_NEXT'    # Blender 4.2+ identifier for EEVEE. Use Cycles for headless/batch runs (see note below).
SAMPLES = 128                     # only used if ENGINE == 'CYCLES'
LIGHT_INTENSITY = 0.3            # global multiplier — turn up/down to brighten or dim all lights at once
SUN_ENERGY = 0.7                 # base key light strength (multiplied by LIGHT_INTENSITY)
FILL_ENERGY = 150                # base fill light strength (multiplied by LIGHT_INTENSITY)
PLANE_SIZE = 2.0
BACKGROUND_COLOR = (0.02, 0.02, 0.02, 1.0)   # dark neutral backdrop
ONLY_ASSETS = False              # True = only render materials marked as assets
PREFIX_WITH_BLENDFILE = True     # avoid name collisions across multiple files
# ---------------------------------------------------------------------------


def build_render_scene():
    scene = bpy.data.scenes.new("ThumbRenderScene")

    # Render settings
    valid_engines = {'BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE', 'CYCLES'}
    engine = ENGINE
    if engine not in valid_engines:
        print(f"  ! unknown ENGINE '{engine}', falling back to CYCLES")
        engine = 'CYCLES'
    try:
        scene.render.engine = engine
    except TypeError:
        # older/newer Blender version uses the other EEVEE identifier
        fallback = 'BLENDER_EEVEE' if engine == 'BLENDER_EEVEE_NEXT' else 'BLENDER_EEVEE_NEXT'
        print(f"  ! '{engine}' not available on this Blender version, trying '{fallback}'")
        scene.render.engine = fallback

    scene.render.resolution_x = RESOLUTION
    scene.render.resolution_y = RESOLUTION
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = FILE_FORMAT
    if FILE_FORMAT == 'JPEG':
        scene.render.image_settings.quality = JPEG_QUALITY
    scene.render.film_transparent = False
    if scene.render.engine == 'CYCLES':
        scene.cycles.samples = SAMPLES

    # World background
    world = bpy.data.worlds.new("ThumbWorld")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = BACKGROUND_COLOR
    scene.world = world

    # Plane
    mesh = bpy.data.meshes.new("ThumbPlaneMesh")
    half = PLANE_SIZE / 2
    verts = [(-half, -half, 0), (half, -half, 0), (half, half, 0), (-half, half, 0)]
    faces = [(0, 1, 2, 3)]
    mesh.from_pydata(verts, [], faces)
    mesh.uv_layers.new(name="UVMap")
    mesh.update()
    plane_obj = bpy.data.objects.new("ThumbPlane", mesh)
    scene.collection.objects.link(plane_obj)

    # Camera - straight top-down orthographic view of the plane
    cam_data = bpy.data.cameras.new("ThumbCam")
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = PLANE_SIZE * 1.05  # tiny margin so plane edges aren't clipped
    cam_obj = bpy.data.objects.new("ThumbCam", cam_data)
    cam_obj.location = (0, 0, 3.0)
    cam_obj.rotation_euler = (0, 0, 0)  # straight down along -Z
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj

    # Key light - straight down too, so the flat top-down shot isn't dark/flat-shaded oddly
    sun_data = bpy.data.lights.new("ThumbSun", type='SUN')
    sun_data.energy = SUN_ENERGY * LIGHT_INTENSITY
    sun_data.angle = 0.3
    sun_obj = bpy.data.objects.new("ThumbSun", sun_data)
    sun_obj.location = (0, 0, 3)
    sun_obj.rotation_euler = (0, 0, 0)
    scene.collection.objects.link(sun_obj)

    # Soft fill light, slightly offset for a bit of depth on bumpy/normal-mapped materials
    fill_data = bpy.data.lights.new("ThumbFill", type='AREA')
    fill_data.energy = FILL_ENERGY * LIGHT_INTENSITY
    fill_data.size = 3
    fill_obj = bpy.data.objects.new("ThumbFill", fill_data)
    fill_obj.location = (1.0, -1.0, 2.5)
    scene.collection.objects.link(fill_obj)

    return scene, plane_obj


def cleanup_render_scene(scene, plane_obj):
    mesh = plane_obj.data
    cam = scene.camera
    cam_data = cam.data if cam else None
    world = scene.world

    lights = [obj for obj in scene.collection.objects if obj.type == 'LIGHT']
    light_datas = [obj.data for obj in lights]

    for obj in list(scene.collection.objects):
        bpy.data.objects.remove(obj, do_unlink=True)

    bpy.data.meshes.remove(mesh)
    if cam_data:
        bpy.data.cameras.remove(cam_data)
    for ld in light_datas:
        bpy.data.lights.remove(ld)
    if world:
        bpy.data.worlds.remove(world)

    bpy.data.scenes.remove(scene)


def safe_name(name):
    return "".join(c if c.isalnum() or c in "-_. " else "_" for c in name)


def render_material(mat, scene, plane_obj, output_dir):
    if plane_obj.data.materials:
        plane_obj.data.materials[0] = mat
    else:
        plane_obj.data.materials.append(mat)

    ext = "jpg" if FILE_FORMAT == 'JPEG' else "png"
    if PREFIX_WITH_BLENDFILE:
        blend_stem = os.path.splitext(os.path.basename(bpy.data.filepath))[0] or "untitled"
        filename = f"{safe_name(blend_stem)}__{safe_name(mat.name)}.{ext}"
    else:
        filename = f"{safe_name(mat.name)}.{ext}"

    filepath = os.path.join(output_dir, filename)
    scene.render.filepath = filepath

    with bpy.context.temp_override(scene=scene):
        bpy.ops.render.render(write_still=True)

    print(f"  ✓ rendered: {filepath}")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    materials = [m for m in bpy.data.materials if m.users > 0 or True]
    if ONLY_ASSETS:
        materials = [m for m in materials if m.asset_data is not None]

    print(f"Rendering {len(materials)} materials at {RESOLUTION}x{RESOLUTION}...")

    scene, plane_obj = build_render_scene()
    try:
        for mat in materials:
            if not mat.use_nodes and mat.node_tree is None:
                pass  # still fine, plain materials render too
            try:
                render_material(mat, scene, plane_obj, OUTPUT_DIR)
            except Exception as e:
                print(f"  ! failed on {mat.name}: {e}")
    finally:
        cleanup_render_scene(scene, plane_obj)

    print(f"\nDone. Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
