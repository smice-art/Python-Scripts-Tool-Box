import bpy
import bmesh
import random

# --- Settings ---
COLOR_START_HEX = "#E7B3A6"
COLOR_END_HEX = "#D00000"
ATTR_NAME = "Col"          # color attribute layer name
MAT_NAME = "RandomFaceColorMat"

ROUGHNESS = 0.4   # 0.0 = mirror-smooth, 1.0 = fully matte
METALLIC = 0.0    # 0.0 = dielectric, 1.0 = fully metallic


def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    return (r, g, b)


def lerp_color(c1, c2, t):
    return tuple(c1[i] + (c2[i] - c1[i]) * t for i in range(3))


color_start = hex_to_rgb(COLOR_START_HEX)
color_end = hex_to_rgb(COLOR_END_HEX)

obj = bpy.context.edit_object
if obj is None or obj.mode != 'EDIT':
    raise RuntimeError("Object must be in Edit Mode")

mesh = obj.data
bm = bmesh.from_edit_mesh(mesh)

# --- 1) Assign random colors per face ---
color_layer = bm.loops.layers.color.get(ATTR_NAME)
if color_layer is None:
    color_layer = bm.loops.layers.color.new(ATTR_NAME)

for face in bm.faces:
    t = random.random()
    r, g, b = lerp_color(color_start, color_end, t)
    col = (r, g, b, 1.0)
    for loop in face.loops:
        loop[color_layer] = col

bmesh.update_edit_mesh(mesh)

# --- 2) Make sure this attribute is the active/render color attribute ---
mesh.color_attributes.active_color_name = ATTR_NAME
for attr in mesh.color_attributes:
    if attr.name == ATTR_NAME:
        mesh.color_attributes.render_color_index = list(mesh.color_attributes).index(attr)

# --- 3) Create (or reuse) a material that reads the color attribute ---
mat = bpy.data.materials.get(MAT_NAME)
if mat is None:
    mat = bpy.data.materials.new(MAT_NAME)
mat.use_nodes = True

nt = mat.node_tree
nodes = nt.nodes
links = nt.links

principled = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
if principled is None:
    principled = nodes.new("ShaderNodeBsdfPrincipled")

attr_node = next((n for n in nodes if n.type == 'VERTEX_COLOR'), None)
if attr_node is None:
    attr_node = nodes.new("ShaderNodeVertexColor")
attr_node.layer_name = ATTR_NAME

links.new(attr_node.outputs["Color"], principled.inputs["Base Color"])

# --- roughness / metallic ---
principled.inputs["Roughness"].default_value = ROUGHNESS
principled.inputs["Metallic"].default_value = METALLIC

# --- 4) Assign material to the object (slot 0) ---
if len(obj.data.materials) == 0:
    obj.data.materials.append(mat)
else:
    obj.data.materials[0] = mat

print(f"Colored {len(bm.faces)} faces, assigned material '{MAT_NAME}' "
      f"(Roughness={ROUGHNESS}, Metallic={METALLIC}).")
