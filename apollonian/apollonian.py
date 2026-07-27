import bpy
import cmath
import math

# --- STEP 1: DEFINE THE CIRCLE CLASS ---
class GasketCircle:
    def __init__(self, x, y, r, curvature):
        self.x = x
        self.y = y
        self.radius = abs(r)
        self.curvature = curvature
        # Represent center position as a complex number (z = x + iy)
        self.z = complex(x, y)

    def __repr__(self):
        return f"Circle(x={self.x:.3f}, y={self.y:.3f}, r={self.radius:.3f})"

# --- STEP 2: DESCARTES' THEOREM CALCULATIONS ---
def get_next_curvature(c1, c2, c3):
    """Calculates the two possible curvatures for a fourth tangent circle."""
    k1, k2, k3 = c1.curvature, c2.curvature, c3.curvature
    sum_k = k1 + k2 + k3
    product_k = k1*k2 + k2*k3 + k3*k1
    
    # Avoid domain errors with negative products (precision padding)
    sqrt_part = 2 * math.sqrt(max(0, product_k))
    return [sum_k + sqrt_part, sum_k - sqrt_part]

def complex_descartes(c1, c2, c3, k4):
    """Calculates the two possible complex centers (z4) for a given curvature k4."""
    zk1 = c1.z * c1.curvature
    zk2 = c2.z * c2.curvature
    zk3 = c3.z * c3.curvature
    
    sum_zk = zk1 + zk2 + zk3
    product_zk = zk1*zk2 + zk2*zk3 + zk3*zk1
    sqrt_part = 2 * cmath.sqrt(product_zk)
    
    z4_a = (sum_zk + sqrt_part) / k4
    z4_b = (sum_zk - sqrt_part) / k4
    return [z4_a, z4_b]

def is_tangent(c1, c2):
    """Checks if two circles are mathematically tangent within a tolerance limit."""
    dist = math.hypot(c1.x - c2.x, c1.y - c2.y)
    r_sum = c1.radius + c2.radius
    r_diff = abs(c1.radius - c2.radius)
    # Check for external tangency or internal bounding tangency
    return math.isclose(dist, r_sum, abs_tol=1e-4) or math.isclose(dist, r_diff, abs_tol=1e-4)

def find_valid_circle(c1, c2, c3, all_circles, min_radius):
    """Finds new valid tangent circles using Descartes' theorem formulas."""
    new_found = []
    k4_options = get_next_curvature(c1, c2, c3)
    
    for k4 in k4_options:
        if k4 <= 0 or (1.0 / k4) < min_radius:
            continue
            
        r4 = 1.0 / k4
        z4_options = complex_descartes(c1, c2, c3, k4)
        
        for z4 in z4_options:
            pot_circle = GasketCircle(z4.real, z4.imag, r4, k4)
            
            # Verify the math: must be tangent to all three parents
            if is_tangent(pot_circle, c1) and is_tangent(pot_circle, c2) and is_tangent(pot_circle, c3):
                # Avoid adding identical overlapping circles
                duplicate = False
                for existing in all_circles:
                    if math.hypot(pot_circle.x - existing.x, pot_circle.y - existing.y) < 1e-4 and math.isclose(pot_circle.radius, existing.radius, abs_tol=1e-4):
                        duplicate = True
                        break
                if not duplicate:
                    new_found.append(pot_circle)
    return new_found

# --- STEP 3: RECURSIVE GENERATOR QUEUE ---
def generate_gasket(max_depth=4, min_radius=0.02):
    """Generates an array of all gasket circle metadata."""
    # Outer bounding circle (negative curvature because it encloses everything)
    c0 = GasketCircle(0, 0, 1.0, -1.0)
    
    # Three inner tangent circles filling the space
    r_inner = 1.0 / (1.0 + 2.0 / math.sqrt(3))  # ~0.4641
    dist_inner = 1.0 - r_inner
    
    c1 = GasketCircle(0, dist_inner, r_inner, 1.0/r_inner)
    c2 = GasketCircle(-dist_inner * math.sqrt(3)/2, -dist_inner/2, r_inner, 1.0/r_inner)
    c3 = GasketCircle(dist_inner * math.sqrt(3)/2, -dist_inner/2, r_inner, 1.0/r_inner)
    
    all_circles = [c0, c1, c2, c3]
    
    # Queue up initial triplets of triplets to check
    queue = [
        (c0, c1, c2, 0), (c0, c2, c3, 0), (c0, c3, c1, 0),
        (c1, c2, c3, 0)
    ]
    
    while queue:
        ca, cb, cc, depth = queue.pop(0)
        if depth >= max_depth:
            continue
            
        new_circles = find_valid_circle(ca, cb, cc, all_circles, min_radius)
        for nc in new_circles:
            all_circles.append(nc)
            # Add new triplets combinations to continue recursion
            queue.append((ca, cb, nc, depth + 1))
            queue.append((ca, cc, nc, depth + 1))
            queue.append((cb, cc, nc, depth + 1))
            
    return all_circles

# --- STEP 4: BLENDER MESH GENERATION ---
def create_mesh_circle(circle_data, vertices=64):
    """Spawns an actual curve circle object in the Blender 3D View."""
    # Using curve circles looks cleaner than heavy geometry meshes
    bpy.ops.curve.primitive_bezier_circle_add(
        radius=circle_data.radius, 
        location=(circle_data.x, circle_data.y, 0)
    )
    obj = bpy.context.active_object
    obj.name = f"GasketCircle_R_{circle_data.radius:.3f}"
    
    # Extrude a tiny bit to make it visible as a wire or flat band
    obj.data.extrude = 0.005 

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    # Clear preexisting default mesh data to keep scene tidy
    if "Cube" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["Cube"], do_unlink=True)
        
    print("Calculating Gasket Packings...")
    # Adjust depth (higher = more iterations/smaller circles, but takes longer)
    circles = generate_gasket(max_depth=4, min_radius=0.01)
    
    print(f"Spawning {len(circles)} circles into Blender...")
    for c in circles:
        create_mesh_circle(c)
        
    print("Done!")
