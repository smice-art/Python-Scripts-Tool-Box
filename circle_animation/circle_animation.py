import bpy
import bmesh
import random
from math import radians

# -------------------------------------------------------
# Helper: convert hex RGBA to 0–1 float tuple
# -------------------------------------------------------
def hex_to_rgba(hex_string):
    hex_string = hex_string.lstrip("#")
    return tuple(int(hex_string[i:i+2], 16)/255 for i in (0,2,4,6))

# -------------------------------------------------------
# SCENE CLEANUP
# -------------------------------------------------------
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        bpy.data.objects.remove(obj, do_unlink=True)

# Remove old material if it exists
if "CircleMaterial" in bpy.data.materials:
    bpy.data.materials.remove(bpy.data.materials["CircleMaterial"], do_unlink=True)

# -------------------------------------------------------
# CREATE ONE RANDOM-PER-OBJECT MATERIAL
# -------------------------------------------------------
single_mat = bpy.data.materials.new(name="CircleMaterial")
single_mat.use_nodes = True
nodes = single_mat.node_tree.nodes
links = single_mat.node_tree.links

# clear everything
for n in nodes:
    nodes.remove(n)

# add nodes
output = nodes.new("ShaderNodeOutputMaterial")
bsdf = nodes.new("ShaderNodeBsdfPrincipled")
obj_info = nodes.new("ShaderNodeObjectInfo")
colorramp = nodes.new("ShaderNodeValToRGB")

# place nodes
output.location = (400, 0)
bsdf.location = (200, 0)
colorramp.location = (0, 0)
obj_info.location = (-300, 0)

# set color ramp ends
colorramp.color_ramp.elements[0].color = hex_to_rgba("E7BC5CFF")
colorramp.color_ramp.elements[1].color = hex_to_rgba("E72712FF")

# connect nodes
links.new(obj_info.outputs["Random"], colorramp.inputs["Fac"])
links.new(colorramp.outputs["Color"], bsdf.inputs["Base Color"])
links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

# -------------------------------------------------------
# GRID PARAMETERS
# -------------------------------------------------------
rows = 6
cols = 8
spacing_x = 3
spacing_y = 3

# extrusion heights
extrusion_heights = [0.10, 0.20, 0.30, 0.40]

all_objects = []

# -------------------------------------------------------
# CREATE CIRCLES
# -------------------------------------------------------
for r in range(rows):
    for c in range(cols):

        base_x = c * spacing_x
        base_y = r * -spacing_y

        # radii rules
        radius1 = 1.0
        radius2 = random.uniform(0.3, radius1)
        radius3 = random.uniform(0.1, radius2)
        radius4 = 0.24
        radii = [radius1, radius2, radius3, radius4]

        for i, radius in enumerate(radii):
            bpy.ops.mesh.primitive_circle_add(
                radius=radius,
                fill_type='NGON',
                vertices=64,
                location=(base_x, base_y, i * 0.05)
            )
            obj = bpy.context.active_object
            all_objects.append(obj)

            # assign SINGLE material
            obj.data.materials.clear()
            obj.data.materials.append(single_mat)

            # ----------------------------------------------
            # CLOCK-HAND VERTEX DEFORMATION
            # ----------------------------------------------
            mesh = obj.data
            bm = bmesh.new()
            bm.from_mesh(mesh)

            # triangulate NGON for valid geometry
            bmesh.ops.triangulate(bm, faces=bm.faces[:])

            # pick only perimeter vertices (2 edges connected)
            perimeter = [v for v in bm.verts if len(v.link_edges) == 2]

            if perimeter:
                v = random.choice(perimeter)

                # radial vector = xy normalized
                radial = v.co.xy.normalized()
                dx, dy = radial.x, radial.y

                # pull outward
                v.co.x += dx * 0.12
                v.co.y += dy * 0.12

            # ----------------------------------------------
            # EXTRUSION (different per circle)
            # ----------------------------------------------
            bm.to_mesh(mesh)
            bm.free()

            bm2 = bmesh.new()
            bm2.from_mesh(mesh)

            faces = bm2.faces[:]
            ext = bmesh.ops.extrude_face_region(bm2, geom=faces)
            geom_extruded = ext["geom"]

            # move only new geometry
            for elem in geom_extruded:
                if isinstance(elem, bmesh.types.BMVert):
                    elem.co.z -= extrusion_heights[i]

            bm2.to_mesh(mesh)
            bm2.free()

# -------------------------------------------------------
# ANIMATION
# -------------------------------------------------------
for obj in all_objects:
    obj.rotation_euler = (0, 0, 0)
    obj.keyframe_insert(data_path="rotation_euler", frame=1)

    # random rotation direction and speed
    direction = random.choice([-1, 1])
    speed_factor = random.uniform(0.5, 2)

    final_rot = direction * speed_factor * radians(360)

    obj.rotation_euler[2] = final_rot
    obj.keyframe_insert(data_path="rotation_euler", frame=250)

# set interpolation to LINEAR for looping
for obj in all_objects:
    fcurve = obj.animation_data.action.fcurves[2]
    for kp in fcurve.keyframe_points:
        kp.interpolation = 'LINEAR'

print("✔ All done: grid, radii, extrusions, clock-hands, random colors, animation!")
