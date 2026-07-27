import bpy
import bmesh
import math
import cmath

# --- SETTINGS ---
SHAPE_TYPE = 2  # 1 = Torus, 2 = Sphere, 3 = Cube
FLAT_MODE = True 
MAX_DEPTH = 4    
RAD_SCALE = 1.0  

# --- Math Constants (Tweaked to break perfect overlap) ---
ta = complex(1.958591030, -0.011278560)
# We change 2.0 to 2.001 to "break" the perfect symmetry that causes overlaps
tb = 2.001 

tab = 0.5 * (ta * tb - cmath.sqrt(ta**2 * tb**2 - 4 * (ta**2 + tb**2)))
z0 = (tab - 2) * tb / (tb * tab - 2 * ta + 2j * tab)

# Matrices
mat_a = [[ta/2, (ta*tab-2*tb+4j)/((2*tab+4)*z0)], [(ta*tab-2*tb-4j)*z0/(2*tab-4), ta/2]]
def inv(m):
    det = m[0][0]*m[1][1] - m[0][1]*m[1][0]
    return [[m[1][1]/det, -m[0][1]/det], [-m[1][0]/det, m[0][0]/det]]
mat_A = inv(mat_a)
mat_b = [[0.5*(tb - 2j), 0.5*tb], [0.5*tb, 0.5*(tb + 2j)]]
mat_B = inv(mat_b)
generators = [mat_a, mat_A, mat_b, mat_B]

def reflect(c, a):
    conj_a = [[a[0][0].conjugate(), a[0][1].conjugate()], [a[1][0].conjugate(), a[1][1].conjugate()]]
    m = [[c[0][0]*conj_a[1][1] - c[0][1]*conj_a[1][0], -c[0][0]*conj_a[0][1] + c[0][1]*conj_a[0][0]],
         [c[1][0]*conj_a[1][1] - c[1][1]*conj_a[1][0], -c[1][0]*conj_a[0][1] + c[1][1]*conj_a[0][0]]]
    return [[a[0][0]*m[0][0] + a[0][1]*m[1][0], a[0][0]*m[0][1] + a[0][1]*m[1][1]],
            [a[1][0]*m[0][0] + a[1][1]*m[1][0], a[1][0]*m[0][1] + a[1][1]*m[1][1]]]

# --- Cleanup ---
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Global list to track positions and avoid overlaps
spawned_locations = []
DIST_EPSILON = 0.001 

def create_mesh_obj(name, loc, rad, depth):
    # Check if we already have an object at this exact spot
    for other_loc in spawned_locations:
        dist = (loc - other_loc).length
        if dist < DIST_EPSILON:
            return None # Skip overlap
            
    spawned_locations.append(loc)
    
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    if SHAPE_TYPE == 2:
        bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=12, radius=rad * RAD_SCALE)
    elif SHAPE_TYPE == 3:
        bmesh.ops.create_cube(bm, size=rad * 2 * RAD_SCALE)
    
    bm.to_mesh(mesh)
    bm.free()
    
    obj.location = loc
    
    # Material with size-based coloring
    mat = bpy.data.materials.new(name="FractalMat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    # Color based on depth: Larger = Blue, Smaller = Red
    bsdf.inputs[0].default_value = (depth/5, 0.5, 1.0 - (depth/5), 1.0)
    obj.data.materials.append(mat)
    
    return obj

def build(current_c, depth, last_idx):
    if depth > MAX_DEPTH: return
    
    a_val, c_val = current_c[0][0], current_c[1][0]
    if abs(c_val) > 1e-9:
        cx_2d, cy_2d = -(a_val / c_val).real, -(a_val / c_val).imag
        rad = abs((1j / c_val).real)
        
        if 0.001 < rad < 10.0:
            pos = (cx_2d, cy_2d, 0) if FLAT_MODE else None # (Logic for globe goes here)
            if pos:
                create_mesh_obj(f"F_{depth}", mathutils.Vector(pos), rad, depth)

    for i, gen in enumerate(generators):
        if last_idx is not None and (i ^ 1) == last_idx: continue
        build(reflect(current_c, gen), depth + 1, i)

import mathutils
build([[0j, 1j], [1j, 0j]], 0, None)