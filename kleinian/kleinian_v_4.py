import bpy
import bmesh
import math
import cmath
import mathutils

# --- SETTINGS ---
SHAPE_TYPE = 2   # 2 = Sphere, 3 = Cube
MAX_DEPTH = 5    
RAD_SCALE = 1.0  
DIST_EPSILON = 0.005 

# --- Math Constants ---
ta = complex(1.958591030, -0.011278560)
tb = 2.001 # Tweak to break perfect symmetry 

tab = 0.5 * (ta * tb - cmath.sqrt(ta**2 * tb**2 - 4 * (ta**2 + tb**2)))
z0 = (tab - 2) * tb / (tb * tab - 2 * ta + 2j * tab)

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
    m = [[c[0][0]*conj_a[1][1] - c[0][1]*conj_a[1][0], -c[0][0]*conj_a[0][1] + c[0][1]*conj_a[0][0]],
         [c[1][0]*conj_a[1][1] - c[1][1]*conj_a[1][0], -c[1][0]*conj_a[0][1] + c[1][1]*conj_a[0][0]]]
    return [[a[0][0]*m[0][0] + a[0][1]*m[1][0], a[0][0]*m[0][1] + a[0][1]*m[1][1]],
            [a[1][0]*m[0][0] + a[1][1]*m[1][0], a[1][0]*m[0][1] + a[1][1]*m[1][1]]]

# --- Cleanup ---
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

spawned_locations = []

def create_mesh_obj(name, loc, rad, depth):
    # Overlap Check
    for other_loc in spawned_locations:
        if (loc - other_loc).length < DIST_EPSILON:
            return None
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
    
    # --- SIZE-BASED COLORING ---
    mat = bpy.data.materials.new(name=f"Mat_{depth}")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    
    # Map radius to a color range
    # Large radius -> Blue/Cyan | Small radius -> Pink/Red
    color_factor = max(0.0, min(1.0, rad * 2.0)) 
    bsdf.inputs['Base Color'].default_value = (1.0 - color_factor, 0.2, color_factor, 1.0)
    
    # Optional: Make smaller ones glow slightly
    if rad < 0.1:
        bsdf.inputs['Emission Color'].default_value = (1.0, 0.2, 0.5, 1.0)
        bsdf.inputs['Emission Strength'].default_value = 0.5
        
    obj.data.materials.append(mat)
    return obj

def build(current_c, depth, last_idx):
    if depth > MAX_DEPTH: return
    
    a_val, c_val = current_c[0][0], current_c[1][0]
    if abs(c_val) > 1e-9:
        cx_2d, cy_2d = -(a_val / c_val).real, -(a_val / c_val).imag
        rad = abs((1j / c_val).real)
        
        if 0.001 < rad < 10.0:
            create_mesh_obj(f"F_{depth}", mathutils.Vector((cx_2d, cy_2d, 0)), rad, depth)

    for i, gen in enumerate(generators):
        if last_idx is not None and (i ^ 1) == last_idx: continue
        build(reflect(current_c, gen), depth + 1, i)

build([[0j, 1j], [1j, 0j]], 0, None)
print("Colorful Clean Gasket Done.")