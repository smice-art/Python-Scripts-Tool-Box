import bpy
import math
import cmath

# 1. Clean up
if bpy.context.object and bpy.context.object.mode == 'EDIT':
    bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# --- Math Constants ---
ta = complex(1.958591030, -0.011278560)
tb = 2.0
tab = 0.5 * (ta * tb - cmath.sqrt(ta**2 * tb**2 - 4 * (ta**2 + tb**2)))
z0 = (tab - 2) * tb / (tb * tab - 2 * ta + 2j * tab)

def mult(m1, m2):
    return [[m1[0][0]*m2[0][0] + m1[0][1]*m2[1][0], m1[0][0]*m2[0][1] + m1[0][1]*m2[1][1]],
            [m1[1][0]*m2[0][0] + m1[1][1]*m2[1][0], m1[1][0]*m2[0][1] + m1[1][1]*m2[1][1]]]

def inv(m):
    det = m[0][0]*m[1][1] - m[0][1]*m[1][0]
    return [[m[1][1]/det, -m[0][1]/det], [-m[1][0]/det, m[0][0]/det]]

mat_a = [[ta/2, (ta*tab-2*tb+4j)/((2*tab+4)*z0)], [(ta*tab-2*tb-4j)*z0/(2*tab-4), ta/2]]
mat_A = inv(mat_a)
mat_b = [[0.5*(tb - 2j), 0.5*tb], [0.5*tb, 0.5*(tb + 2j)]]
mat_B = inv(mat_b)
generators = [mat_a, mat_A, mat_b, mat_B]

def reflect(c, a):
    conj_a = [[a[0][0].conjugate(), a[0][1].conjugate()], [a[1][0].conjugate(), a[1][1].conjugate()]]
    return mult(mult(a, c), inv(conj_a))

# --- Create Material ---
def get_gold_mat():
    mat = bpy.data.materials.new(name="Gold")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs['Base Color'].default_value = (1.0, 0.8, 0.1, 1.0)
    bsdf.inputs['Metallic'].default_value = 1.0
    bsdf.inputs['Roughness'].default_value = 0.1
    return mat

gold_mat = get_gold_mat()

# --- Recursive Builder ---
def build_gasket(current_c, depth, max_depth, last_idx):
    if depth > max_depth: return
    
    a_val, c_val = current_c[0][0], current_c[1][0]
    if abs(c_val) > 1e-9:
        cx = -(a_val / c_val).real
        cy = -(a_val / c_val).imag
        rad = abs((1j / c_val).real)
        
        # Only build if it's not a speck of dust
        if rad > 0.005:
            # Use Torus for that "interlocking rings" fractal look
            bpy.ops.mesh.primitive_torus_add(
                align='WORLD', 
                location=(cx, cy, 0), 
                major_radius=rad, 
                minor_radius=rad*0.05, # Thin rings
                major_segments=48, 
                minor_segments=12
            )
            obj = bpy.context.active_object
            obj.data.materials.append(gold_mat)
            bpy.ops.object.shade_smooth()

    # Branching
    for i, gen in enumerate(generators):
        if last_idx is not None and (i ^ 1) == last_idx: continue
        next_c = reflect(current_c, gen)
        build_gasket(next_c, depth + 1, max_depth, i)

# Start!
c_start = [[0j, 1j], [1j, 0j]]
build_gasket(c_start, 0, max_depth=4, last_idx=None)

print("Done! Zoom in on the center (X:0, Y:0).")