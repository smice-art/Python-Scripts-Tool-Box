import bpy
import bmesh
import random

# --- SETTINGS ---
num_colors = 10
obj = bpy.context.active_object

def create_random_materials(target_obj, count):
    # Clear existing material slots
    target_obj.data.materials.clear()
    
    mats = []
    for i in range(count):
        mat_name = f"RandomMat_{i}"
        # Create a new material
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        
        # Get the Principled BSDF node
        bsdf = nodes.get("Principled BSDF")
        if bsdf:
            # Generate a random bright color
            random_color = (random.random(), random.random(), random.random(), 1.0)
            bsdf.inputs['Base Color'].default_value = random_color
        
        target_obj.data.materials.append(mat)
        mats.append(mat)
    return mats

def assign_materials_to_islands(target_obj):
    if target_obj.type != 'MESH':
        print("Please select a mesh object.")
        return

    # 1. Create the materials
    create_random_materials(target_obj, num_colors)

    # 2. Use BMesh to find islands
    bm = bmesh.new()
    bm.from_mesh(target_obj.data)
    bm.faces.ensure_lookup_table()

    # Find islands (groups of connected faces)
    islands = []
    unvisited_faces = set(bm.faces)
    
    while unvisited_faces:
        # Start a new island
        face = unvisited_faces.pop()
        island = [face]
        
        # Grow the island by finding neighbors
        queue = [face]
        while queue:
            f = queue.pop(0)
            for edge in f.edges:
                for n_face in edge.link_faces:
                    if n_face in unvisited_faces:
                        unvisited_faces.remove(n_face)
                        island.append(n_face)
                        queue.append(n_face)
        islands.append(island)

    print(f"Found {len(islands)} islands. Assigning {num_colors} colors...")

    # 3. Randomly assign a material index to each island
    for island in islands:
        random_index = random.randint(0, num_colors - 1)
        for face in island:
            face.material_index = random_index

    # Write the data back to the mesh
    bm.to_mesh(target_obj.data)
    bm.free()
    target_obj.data.update()

assign_materials_to_islands(obj)