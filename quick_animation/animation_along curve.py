import bpy

# Get selected objects
selected_objs = bpy.context.selected_objects

sphere = None
curve = None

# Identify mesh and curve
for obj in selected_objs:
    if obj.type == 'MESH':
        sphere = obj
    elif obj.type == 'CURVE':
        curve = obj

if not sphere or not curve:
    raise Exception("Please select both a Mesh (Sphere) and a Curve object.")

# 1. Enable Path Animation on the curve
curve.data.use_path = True

# 2. Add or retrieve Follow Path constraint
follow_path = None
for constraint in sphere.constraints:
    if constraint.type == 'FOLLOW_PATH':
        follow_path = constraint
        break

if not follow_path:
    follow_path = sphere.constraints.new(type='FOLLOW_PATH')

# 3. Configure constraint
follow_path.target = curve
follow_path.use_fixed_location = True

# CRITICAL FIX: Reset the sphere's world location so the constraint snaps it directly onto the curve
sphere.location = (0, 0, 0)

# 4. Animate Offset Factor
start_frame = 1
mid_frame = 259
end_frame = 518

# Frame 1: Start (0.0)
# 4. Animate Offset Factor directly on the constraint
start_frame = 1
mid_frame = 259
end_frame = 518

# Frame 1: Start (0.0)
follow_path.offset_factor = 0.0
follow_path.keyframe_insert(data_path="offset_factor", frame=start_frame)

# Frame 259: End (1.0)
follow_path.offset_factor = 1.0
follow_path.keyframe_insert(data_path="offset_factor", frame=mid_frame)

# Frame 518: Return to Start (0.0)
follow_path.offset_factor = 0.0
follow_path.keyframe_insert(data_path="offset_factor", frame=end_frame)

# Sync timeline range
bpy.context.scene.frame_start = start_frame
bpy.context.scene.frame_end = end_frame

print("Fixed! Sphere snapped directly to path.")