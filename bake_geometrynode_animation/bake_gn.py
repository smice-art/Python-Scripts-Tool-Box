import bpy

# --- SETTINGS ---
obj = bpy.context.active_object
scene = bpy.context.scene
start_frame = scene.frame_start
end_frame = scene.frame_end

def bake_with_master_basis():
    if not obj:
        print("Please select the GN object.")
        return

    depsgraph = bpy.context.evaluated_depsgraph_get()
    
    # PHASE 1: Find the frame with the MOST vertices
    print("Scanning for max vertex count...")
    max_verts = 0
    target_frame = start_frame
    
    for f in range(start_frame, end_frame + 1):
        scene.frame_set(f)
        eval_obj = obj.evaluated_get(depsgraph)
        temp_mesh = bpy.data.meshes.new_from_object(eval_obj)
        if len(temp_mesh.vertices) > max_verts:
            max_verts = len(temp_mesh.vertices)
            target_frame = f
        bpy.data.meshes.remove(temp_mesh)

    print(f"Max vertices ({max_verts}) found on frame {target_frame}. Creating Master Mesh...")

    # PHASE 2: Create the Master (Bake) Object
    scene.frame_set(target_frame)
    eval_obj = obj.evaluated_get(depsgraph)
    master_mesh = bpy.data.meshes.new_from_object(eval_obj)
    bake_obj = bpy.data.objects.new(obj.name + "_MasterBake", master_mesh)
    scene.collection.objects.link(bake_obj)
    
    # Initialize Basis
    bake_obj.shape_key_add(name="Basis")

    # PHASE 3: Bake every frame into a Shape Key
    for f in range(start_frame, end_frame + 1):
        scene.frame_set(f)
        eval_obj = obj.evaluated_get(depsgraph)
        current_mesh = bpy.data.meshes.new_from_object(eval_obj)
        
        # Add Shape Key
        sk = bake_obj.shape_key_add(name=f"Frame_{f}")
        
        # Move vertices
        num_current_verts = len(current_mesh.vertices)
        for i in range(max_verts):
            if i < num_current_verts:
                # Move to actual position
                sk.data[i].co = current_mesh.vertices[i].co
            else:
                # "Hide" extra vertices at origin
                sk.data[i].co = (0, 0, 0)
        
        # Keyframe influence
        sk.value = 1.0
        sk.keyframe_insert(data_path='value', frame=f)
        if f > start_frame:
            sk.value = 0.0
            sk.keyframe_insert(data_path='value', frame=f-1)
        if f < end_frame:
            sk.value = 0.0
            sk.keyframe_insert(data_path='value', frame=f+1)
            
        bpy.data.meshes.remove(current_mesh)
        print(f"Baked frame {f}")

    print("Bake Complete! You can now export the '_MasterBake' object.")

bake_with_master_basis()