import bpy

# User variables
base_name = "shader-name"
start_index = 1

# Get all materials to rename (you can filter here)
materials_to_rename = list(bpy.data.materials)

# Get all existing names to avoid duplication
existing_names = {mat.name for mat in bpy.data.materials}

index = start_index
for mat in materials_to_rename:
    while True:
        suffix = f".{index:03}"
        new_name = f"{base_name}{suffix}"
        if new_name not in existing_names:
            break
        index += 1

    mat.name = new_name
    existing_names.add(new_name)
    index += 1

print("Renaming complete starting at index", start_index)

