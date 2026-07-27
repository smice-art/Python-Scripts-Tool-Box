import bpy
import bmesh
import math
import cmath

# --- SETTINGS ---
SHAPE_TYPE = 1   # 1 = Torus, 2 = Sphere, 3 = Cube
FLAT_MODE = True 
MAX_DEPTH = 4    
RAD_SCALE = 1.0  
VARIETY_BOOST = 0.05 # Adds a tiny unique scale shift to each generation

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

# --- Cleanup ---
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

def create_mesh_obj(name, loc, rad, depth):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    # Variety adjustment: Each depth level gets a slightly different multiplier
    # This prevents the "25 identical cubes" problem
    unique_rad = rad * (1.0 - (depth * VARIETY_BOOST))
    
    bm = bmesh.new()
    if SHAPE_TYPE == 2:
        bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=12, radius=unique_rad * RAD_SCALE)
    elif SHAPE_TYPE == 3:
        bmesh.ops.create_cube(bm, size=unique_rad * 2 * RAD_SCALE)
    
    bm.to_mesh(mesh)
    bm.free()
    
    obj.location = loc
    
    # FALLBACK FOR TORUS (because bmesh doesn't have a simple torus op)
    if SHAPE_TYPE == 1:
        bpy.data.objects.remove(obj)
        bpy.ops.mesh.primitive_torus_add(location=loc, major_radius=unique_rad, minor_radius=unique_rad*0.05)
    
    return obj

def build(current_c, depth, last_idx):
    if depth > MAX_DEPTH: return
    
    a_val, c_val = current_c[0][0], current_c[1][0]
    if abs(c_val) > 1e-9:
        cx_2d, cy_2d = -(a_val / c_val).real, -(a_val / c_val).imag
        rad = abs((1j / c_val).real)
        
        if 0.005 < rad < 5.0:
            if FLAT_MODE:
                pos = (cx_2d, cy_2d, 0)
            else:
                lon, lat = cx_2d * 1.5, cy_2d * 1.5
                r = 3.0
                pos = (r*math.cos(lat)*math.cos(lon), r*math.cos(lat)*math.sin(lon), r*math.sin(lat))
            
            create_mesh_obj(f"Fractal_{depth}", pos, rad, depth)

    for i, gen in enumerate(generators):
        if last_idx is not None and (i ^ 1) == last_idx: continue
        build(reflect(current_c, gen), depth + 1, i)

build([[0j, 1j], [1j, 0j]], 0, None)