import bpy
import math
import cmath

# --- SETTINGS ---
SHAPE_TYPE = 1   # 1 = Torus, 2 = Sphere, 3 = Cube
FLAT_MODE = True # True = Flat 2D (Mathematica style), False = 3D Globe
MAX_DEPTH = 4    
RAD_SCALE = 1.0  # Increase this if shapes look too small

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
if bpy.context.object and bpy.context.object.mode == 'EDIT':
    bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# --- Shape Generator ---
def add_my_shape(loc, rad):
    if SHAPE_TYPE == 1:
        bpy.ops.mesh.primitive_torus_add(location=loc, major_radius=rad, minor_radius=rad*0.05)
    elif SHAPE_TYPE == 2:
        bpy.ops.mesh.primitive_uv_sphere_add(radius=rad * RAD_SCALE, location=loc, segments=16, ring_count=8)
    elif SHAPE_TYPE == 3:
        bpy.ops.mesh.primitive_cube_add(size=rad * 2 * RAD_SCALE, location=loc)
    
    bpy.ops.object.shade_smooth()

# --- Recursive Loop ---
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
            
            add_my_shape(pos, rad)

    for i, gen in enumerate(generators):
        if last_idx is not None and (i ^ 1) == last_idx: continue
        build(reflect(current_c, gen), depth + 1, i)

# Start
build([[0j, 1j], [1j, 0j]], 0, None)
print("Finished without errors.")