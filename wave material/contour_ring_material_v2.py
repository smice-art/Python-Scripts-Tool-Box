"""
Contour-Ring Material Generator v2 — parallel bands
-----------------------------------------------------
Difference from v1: instead of a Smooth-F1 Voronoi distance field (which
produces many separate closed "island" rings scattered around cell
centers), this version uses a Wave Texture in BANDS mode as the base
field. Bands mode always emits nested lines that all run in the same
general direction, so the ring/stripe pattern reads as parallel bands
rather than isolated blobs -- matching the marked reference area. A
Noise-based domain warp still gives the bands their organic wobble.

Ring coloring: a Color Ramp (CONSTANT interpolation) with ~30 elements,
where BOTH the stop positions (-> band width / spacing) and the colors
are randomized -- so band width varies irregularly and colors don't
progress as a gradient.

Run in Blender's Scripting tab with an object selected/active.
"""

import bpy
import random
import colorsys

# ---------------------------------------------------------------------------
# PARAMETERS
# ---------------------------------------------------------------------------
MAT_NAME             = "ContourRings"
SEED                  = 7          # change for a different palette / spacing / warp

NUM_COLORS            = 30         # number of distinct ring colors
MIN_BAND_GAP          = 0.35       # min spacing between ramp stops, as a
                                    # fraction of the *even* spacing (0=totally
                                    # random/can collapse thin, 1=perfectly even)

BAND_SCALE            = 6.0        # how many bands fit across the surface
BAND_DIRECTION        = 'DIAGONAL'  # 'X', 'Y', or 'DIAGONAL'
BAND_DISTORTION       = 2.0        # built-in wave distortion (organic wobble)
BAND_DETAIL           = 2.0        # wave detail (fine wobble on top)
BAND_DETAIL_SCALE     = 1.0

MAPPING_SCALE         = 1.0        # overall pan/zoom of the pattern
MAPPING_ROTATION_Z    = 0.6        # radians, angles the band direction

WARP_SCALE            = 1.5        # scale of the extra domain-warp noise
WARP_STRENGTH         = 0.25       # how much it distorts the bands further

BASE_ROUGHNESS        = 0.25
BUMP_NOISE_SCALE      = 12.0
BUMP_STRENGTH         = 0.15

random.seed(SEED)

# ---------------------------------------------------------------------------
# MATERIAL / NODE TREE (reuse if it already exists, so re-running the
# script while iterating doesn't spawn ContourRings.001, .002, ...)
# ---------------------------------------------------------------------------
if MAT_NAME in bpy.data.materials:
    mat = bpy.data.materials[MAT_NAME]
else:
    mat = bpy.data.materials.new(MAT_NAME)
mat.use_nodes = True
nt = mat.node_tree
nt.nodes.clear()


def mn(node_type, location):
    node = nt.nodes.new(node_type)
    node.location = location
    return node


def lk(from_node, from_socket, to_node, to_socket):
    nt.links.new(from_node.outputs[from_socket], to_node.inputs[to_socket])


def random_vivid_color():
    h = random.random()
    s = random.uniform(0.55, 1.0)
    v = random.uniform(0.55, 1.0)
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (r, g, b, 1.0)


# ---------------------------------------------------------------------------
# COORDINATE INPUT + DOMAIN WARP (extra organic wobble on top of the
# wave texture's own built-in distortion)
# ---------------------------------------------------------------------------
tex_coord = mn('ShaderNodeTexCoord', (-1400, 0))

mapping = mn('ShaderNodeMapping', (-1200, 0))
mapping.inputs['Scale'].default_value = (MAPPING_SCALE, MAPPING_SCALE, MAPPING_SCALE)
mapping.inputs['Rotation'].default_value = (0.0, 0.0, MAPPING_ROTATION_Z)
lk(tex_coord, 'Generated', mapping, 'Vector')

warp_noise = mn('ShaderNodeTexNoise', (-1000, 250))
warp_noise.noise_dimensions = '3D'
warp_noise.inputs['Scale'].default_value = WARP_SCALE
warp_noise.inputs['Detail'].default_value = 4.0

warp_sub = mn('ShaderNodeVectorMath', (-800, 250))
warp_sub.operation = 'SUBTRACT'
warp_sub.inputs[1].default_value = (0.5, 0.5, 0.5)
lk(warp_noise, 'Color', warp_sub, 0)

warp_scale = mn('ShaderNodeVectorMath', (-600, 250))
warp_scale.operation = 'SCALE'
warp_scale.inputs['Scale'].default_value = WARP_STRENGTH
lk(warp_sub, 'Vector', warp_scale, 0)

warp_add = mn('ShaderNodeVectorMath', (-400, 100))
warp_add.operation = 'ADD'
lk(mapping, 'Vector', warp_add, 0)
lk(warp_scale, 'Vector', warp_add, 1)

# ---------------------------------------------------------------------------
# BAND FIELD: Wave Texture in BANDS mode -> naturally parallel, one
# direction, with built-in distortion/detail for organic wobble.
# ---------------------------------------------------------------------------
wave = mn('ShaderNodeTexWave', (-200, 100))
wave.wave_type = 'BANDS'
wave.bands_direction = BAND_DIRECTION
wave.wave_profile = 'SIN'
wave.inputs['Scale'].default_value = BAND_SCALE
wave.inputs['Distortion'].default_value = BAND_DISTORTION
wave.inputs['Detail'].default_value = BAND_DETAIL
wave.inputs['Detail Scale'].default_value = BAND_DETAIL_SCALE
lk(warp_add, 'Vector', wave, 'Vector')

# ---------------------------------------------------------------------------
# COLOR RAMP: ~30 constant bands, positions AND colors both randomized
# ---------------------------------------------------------------------------
ramp = mn('ShaderNodeValToRGB', (200, 100))
ramp.color_ramp.interpolation = 'CONSTANT'
lk(wave, 'Fac', ramp, 'Fac')

# build randomized-but-increasing stop positions
even_step = 1.0 / NUM_COLORS
positions = []
prev = 0.0
for i in range(NUM_COLORS):
    even_pos = i * even_step
    jitter = random.uniform(-0.5, 0.5) * even_step * (1.0 - MIN_BAND_GAP)
    pos = even_pos + jitter
    pos = max(pos, prev + even_step * MIN_BAND_GAP * 0.1)  # avoid duplicates
    pos = min(pos, 1.0)
    positions.append(pos)
    prev = pos
positions[0] = 0.0

elements = ramp.color_ramp.elements
elements[0].position = positions[0]
elements[0].color = random_vivid_color()
for i in range(1, NUM_COLORS):
    el = elements.new(positions[i])
    el.color = random_vivid_color()

# ---------------------------------------------------------------------------
# SURFACE BUMP (independent low-frequency noise -> subtle lumpiness)
# ---------------------------------------------------------------------------
bump_noise = mn('ShaderNodeTexNoise', (200, -250))
bump_noise.inputs['Scale'].default_value = BUMP_NOISE_SCALE
bump_noise.inputs['Detail'].default_value = 6.0
lk(mapping, 'Vector', bump_noise, 'Vector')

bump = mn('ShaderNodeBump', (500, -250))
bump.inputs['Strength'].default_value = BUMP_STRENGTH
lk(bump_noise, 'Fac', bump, 'Height')

# ---------------------------------------------------------------------------
# SHADING + OUTPUT
# ---------------------------------------------------------------------------
principled = mn('ShaderNodeBsdfPrincipled', (600, 100))
principled.inputs['Roughness'].default_value = BASE_ROUGHNESS
lk(ramp, 'Color', principled, 'Base Color')
lk(bump, 'Normal', principled, 'Normal')

output = mn('ShaderNodeOutputMaterial', (900, 100))
lk(principled, 'BSDF', output, 'Surface')

# ---------------------------------------------------------------------------
# ASSIGN TO ACTIVE OBJECT
# ---------------------------------------------------------------------------
obj = bpy.context.active_object
if obj is not None:
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
    print(f"Assigned '{MAT_NAME}' to '{obj.name}'.")
else:
    print(f"Created material '{MAT_NAME}' (no active object to assign it to).")
