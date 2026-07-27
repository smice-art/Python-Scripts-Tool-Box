import bpy
import bmesh
import math
from mathutils import Matrix, Vector

# --- Parameters & Constants ---
alpha = math.acos(-math.sqrt(5) / 5)

# The surface control points from your Mathematica script
surface_data = [
    [(0.11, 0.35, 1.0), (0.16, 0.33, 1.0), (0.23, 0.35, 0.99), (0.3, 0.38, 0.96), (0.35, 0.43, 0.9), (0.29, 0.42, 0.8), (0.22, 0.37, 0.7), (0.14, 0.34, 0.62), (0.078, 0.296, 0.585)],
    [(0.0, 0.0, 1.0), (0.13, 0.09, 1.0), (0.29, 0.22, 0.99), (0.4, 0.33, 0.95), (0.41, 0.45, 0.88), (0.31, 0.47, 0.77), (0.2, 0.43, 0.65), (0.08, 0.4, 0.56), (-0.019, 0.398, 0.526)],
    [(0.36, 0.0, 1.0), (0.39, 0.11, 1.0), (0.45, 0.23, 0.99), (0.49, 0.35, 0.95), (0.47, 0.45, 0.86), (0.36, 0.52, 0.73), (0.22, 0.5, 0.59), (0.13, 0.48, 0.48), (0.07, 0.489, 0.437)]
]

def get_rotation_matrix(axis, angle):
    if axis == 'Z':
        return Matrix.Rotation(angle, 4, 'Z')
    elif axis == 'Y':
        return Matrix.Rotation(angle, 4, 'Y')
    elif axis == 'X':
        return Matrix.Rotation(angle, 4, 'X')

def create_arm_mesh(bm, transform_matrix):
    """Creates the patch based on the surface grid and applies a transform."""
    rows = len(surface_data)
    cols = len(surface_data[0])
    
    # Create vertices for this specific arm
    verts = []
    for r in range(rows):
        row_verts = []
        for c in range(cols):
            scale_factor = 0.9  # Reduce to 0.8 or 0.7 to pull parts apart
            v_orig = Vector(surface_data[r][c])
            v_orig.x *= scale_factor
            v_orig.y *= scale_factor
            # Apply the rotation/transformation matrix
            v_transformed = transform_matrix @ v_orig
            row_verts.append(bm.verts.new(v_transformed))
        verts.append(row_verts)
    
    # Create faces (quads) between the grid points
    for r in range(rows - 1):
        for c in range(cols - 1):
            bm.faces.new((
                verts[r][c], 
                verts[r+1][c], 
                verts[r+1][c+1], 
                verts[r][c+1]
            ))

# --- Main Generation ---
mesh = bpy.data.meshes.new("SymmetricSurface")
obj = bpy.data.objects.new("SymmetricSurface", mesh)
bpy.context.collection.objects.link(obj)

bm = bmesh.new()

# The 'face' group: 5 rotations around Z
psi_steps = [i * 0.4 * math.pi for i in range(5)] # 0 to 1.6Pi in steps of 0.4Pi

def add_face_group(base_transform):
    for psi in psi_steps:
        m_psi = get_rotation_matrix('Z', psi)
        create_arm_mesh(bm, base_transform @ m_psi)

# 1. Standard face group
add_face_group(Matrix.Identity(4))

# 2. Rotated face group (RotateShape[face, 0, Pi, 0])
m_mirror = get_rotation_matrix('Y', math.pi)
add_face_group(m_mirror)

# 3. Intermediate groups (The Table logic)
for psi in psi_steps:
    # First intermediate: RotateShape[face, 0, Pi - alpha, psi + Pi/5]
    m1 = get_rotation_matrix('Z', psi + math.pi/5) @ get_rotation_matrix('Y', math.pi - alpha)
    add_face_group(m1)
    
    # Second intermediate: RotateShape[face, Pi/5, alpha, psi]
    # Note: RotateShape order can be tricky; here we follow the Z-Y-Z logic
    m2 = get_rotation_matrix('Z', psi) @ get_rotation_matrix('Y', alpha) @ get_rotation_matrix('Z', math.pi/5)
    add_face_group(m2)

# Finalize
bm.to_mesh(mesh)
bm.free()