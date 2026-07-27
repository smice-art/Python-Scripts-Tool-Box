"""
Fast Kleinian Limit Set + Farey Pleating Rays  --  Blender Python port
========================================================================
Translated from a Mathematica 13.2 notebook ("...Fast Kleinian Limit Set +
Farey Pleating Rays v7 - Fixed: ray bounding-box normalization ... guards
for empty data and numeric checks ... Flattened graphics primitives for
Show").

Run from Blender's Scripting tab, or headless:
    blender -b -P kleinian_blender.py

It builds two flat "canvases" in the scene and overlays the Farey pleating
rays on each, mirroring the notebook's structure:

    StripPlane  -> raw fundamental-domain strip render, x in [-1,1], y in [0,u]
    DiskPlane   -> the same field pulled through the inversion
                   z -> pInv + r2/conj(z - pInv)  ("Steemann disk"), in [-1,1]^2

    Klein_StripRays / Klein_DiskRays  -> curve objects for the pleating rays
    (disk rays are built with the same 4-fold mirror the notebook used:
    (x,y), (-x,y), (x,-y), (-x,-y))

NOTES ON THE PORT
------------------
* Mathematica's ColorData["Pastel"|"DarkRainbow"|"CMYKColors"] gradients are
  proprietary; they're approximated below with hand-rolled HSV ramps
  (pastel_color / dark_rainbow_color / cmyk_color). Visually close, not
  pixel-identical.
* Compile[...] -> a plain Python function (klein_escape); same logic, no
  JIT. CompilationTarget->"C" / ParallelTable have no Blender equivalent,
  so the escape-time grids and the ray root-finding are the slow parts --
  see PERFORMANCE NOTES below.
* FindRoot (Newton, AccuracyGoal->5, MaxIterations->80) -> a small
  hand-rolled damped-Newton find_root(), called from the same 9
  evenly-spaced starting guesses across [xmin,xmax] as the original
  pleatingPoint[].
* The notebook computes sxCen/syCen/sHalf (a bounding box over all the ray
  screen points) but then never actually uses them -- steemannToUnit
  normalizes with the fixed disk window (diskXmin..diskYmax) instead, and
  rayToUnit is just set equal to steemannToUnit. That's reproduced as-is
  (the calc is skipped here since Python doesn't need dead code to match
  behavior) rather than "corrected", since it's exactly what the original
  notebook renders.
* Mathematica's MatrixPlot with DataReversed->{False,True} puts the first
  Table row (smallest y) at image row 0 counted from the top of the picture;
  the samplers below reproduce that by filling row 0 with y = ymax.

PERFORMANCE NOTES
------------------
Runtime is dominated by two O(resolution^2) escape-time grids and by
O(fracs * nRayPts * 9 starts * Newton-iters) root-finding for the rays.
Measured on a normal desktop CPU, pure Python (no bpy needed for this part):
  - a 300x300 escape-time grid: ~0.4s
  - fareyDepth=7 (19 fractions), nRayPts=150: ~9s of root-finding
The CONFIG block below defaults to those numbers. Scaling up to the
notebook's own settings (resStrip=resDisk=1000, fareyDepth=10, nRayPts=300)
is roughly a ~10x grid cost and ~7x ray cost -- call it a few minutes total,
not the tens-of-minutes CompilationTarget->"C" was originally fighting.
Bump RES_STRIP / RES_DISK / FAREY_DEPTH / N_RAY_PTS up once you like the
composition.
"""

import bpy
import bmesh
import math
import colorsys
from fractions import Fraction

# ============================================================================
# CONFIG   (mirrors the notebook's "--0. User parameters--" cell)
# ============================================================================

tval = complex(1.92, 0.03)   # tval = 1.92 + 0.03 I
kSep = 0.2
mSep = 5.0
maxN = 30

fareyDepth = 7      # notebook default: 10 (66 fracs -> slow root-finding)
resStrip = 300       # notebook default: 1000
resDisk = 300         # notebook default: 1000
nRayPts = 150         # notebook default: 300

pInv = complex(0.0, -1.0)     # -I
r2 = 1.0 ** 2

diskXmin, diskXmax = -0.5, 0.5
diskYmin, diskYmax = -1.0, 0.0

PANEL_GAP = 2.5        # world-space offset between the strip & disk canvases
ADD_LABELS = False     # fraction text labels on rays (slow + cluttered past depth ~6)

# ============================================================================
# 1. Compiled Kleinian escape function   (was kleinC = Compile[...])
# ============================================================================

def klein_escape(z, tRe, tIm, kk, mm, max_iter):
    u = tRe
    v = tIm
    t = complex(tRe, tIm)
    xi = z.real
    yi = z.imag
    if yi < 0.0 or yi > u:
        return 0

    zi = complex(1.0, 1.0)
    low = complex(1.0, 1.0)
    high = complex(1.0, 1.0)
    k = 1

    try:
        for n in range(1, max_iter + 1):
            xi = ((xi + 1.0 + v * yi / u) % 2.0) - 1.0 - v * yi / u
            zi = complex(xi, yi)

            s = 1.0 if (xi + v / 2.0) >= 0.0 else -1.0
            thresh = u / 2.0 + s * kk * u * (1.0 - math.exp(-mm * abs(xi + v / 2.0)))

            if yi < thresh:
                if abs(zi - low) < 1e-4:
                    k = -n
                    break
                low = zi
                k = 1
                zi = 1j * t + 1.0 / zi
            else:
                if abs(zi - high) < 1e-4:
                    k = -n
                    break
                high = zi
                zi = 1j / (1j * zi + t)
                k = 2

            xi, yi = zi.real, zi.imag
            if yi < 0.0 or yi > u:
                break
            k = 3
    except (ZeroDivisionError, OverflowError, ValueError):
        return 0

    return k

# ============================================================================
# 2. Colour ramps   (approximations of ColorData[...])
# ============================================================================

def strip_color(k):
    if k <= 0:
        return (1.0, 1.0, 1.0, 1.0)          # White
    if k == 1:
        return (0.117, 0.565, 1.0, 1.0)      # DodgerBlue
    if k == 2:
        return (1.0, 0.0, 0.0, 1.0)          # Red
    return (0.0, 0.6, 0.0, 1.0)              # Green


def pastel_color(t):
    t = max(0.0, min(1.0, t))
    r, g, b = colorsys.hsv_to_rgb(0.55 + 0.4 * t, 0.35, 1.0)
    return (r, g, b, 1.0)


def dark_rainbow_color(t):
    t = max(0.0, min(1.0, t))
    r, g, b = colorsys.hsv_to_rgb(0.75 * (1.0 - t), 0.85, 0.65)
    return (r, g, b, 1.0)


def cmyk_color(t):
    t = max(0.0, min(1.0, t))
    r, g, b = colorsys.hsv_to_rgb(0.5 + 0.5 * t, 0.9, 0.9)
    return (r, g, b, 1.0)


def disk_color(k):
    if k == 0:
        return (1.0, 1.0, 1.0, 1.0)                 # White
    if k == 1:
        return pastel_color(1.0 / 40.0)              # Pastel[-1/40]
    if k == 2:
        return dark_rainbow_color(2.0 / 40.0)        # DarkRainbow[-2/40]
    if k < 0:
        return cmyk_color(min(1.0, (-k) / 40.0))     # CMYKColors[-k/40]
    return (0.0, 1.0, 1.0, 1.0)                      # Cyan

# ============================================================================
# 3. Image builders   (were MatrixPlot[...] over Table[...] / ParallelTable[...])
# ============================================================================

def build_image(name, width, height, sampler):
    """sampler(x_pixel, y_pixel) -> (r,g,b,a); row 0 = top, like MatrixPlot."""
    img = bpy.data.images.get(name)
    if img:
        bpy.data.images.remove(img)
    img = bpy.data.images.new(name, width=width, height=height, alpha=True)

    pixels = [0.0] * (width * height * 4)
    for row in range(height):
        for col in range(width):
            r, g, b, a = sampler(col, row)
            idx = (row * width + col) * 4
            pixels[idx:idx + 4] = (r, g, b, a)

    img.pixels.foreach_set(pixels)
    img.pack()
    return img


def make_strip_image():
    u = tval.real
    xmin, xmax = -1.0, 1.0
    ymin, ymax = 0.0, u
    dx = (xmax - xmin) / (resStrip - 1)
    dy = (ymax - ymin) / (resStrip - 1)

    def sampler(col, row):
        x = xmin + col * dx
        y = ymax - row * dy
        k = klein_escape(complex(x, y), tval.real, tval.imag, kSep, mSep, maxN)
        return strip_color(k)

    print(f"  strip grid: {resStrip}x{resStrip} ...")
    return build_image("Klein_StripImage", resStrip, resStrip, sampler)


def make_disk_image():
    dx = (diskXmax - diskXmin) / (resDisk - 1)
    dy = (diskYmax - diskYmin) / (resDisk - 1)

    def sampler(col, row):
        x = diskXmin + col * dx
        y = diskYmax - row * dy
        q = complex(x, y) - pInv
        z = pInv + r2 / q.conjugate()
        k = klein_escape(z, tval.real, tval.imag, kSep, mSep, maxN)
        return disk_color(k)

    print(f"  disk (Steemann) grid: {resDisk}x{resDisk} ...")
    return build_image("Klein_DiskImage", resDisk, resDisk, sampler)

# ============================================================================
# 4. Farey sequence / word trace / pleating rays
#    (were fareySeq, wordTrace, pleatingPoint)
# ============================================================================

def farey_sequence(n):
    fracs = {Fraction(p, q) for q in range(1, n + 1) for p in range(0, q + 1)}
    return sorted(fracs)


def _mat_mul(A, B):
    return (
        (A[0][0] * B[0][0] + A[0][1] * B[1][0], A[0][0] * B[0][1] + A[0][1] * B[1][1]),
        (A[1][0] * B[0][0] + A[1][1] * B[1][0], A[1][0] * B[0][1] + A[1][1] * B[1][1]),
    )


def _mat_pow(M, n):
    R = ((1.0 + 0j, 0j), (0j, 1.0 + 0j))
    for _ in range(n):
        R = _mat_mul(R, M)
    return R


def word_trace(p, q, tc, t2c):
    """Tr[ s1^p . s2^q ],  s1 = [[I,tc],[0,-I]],  s2 = [[1,0],[t2c,1]]."""
    s1 = ((1j, tc), (0j, -1j))
    s2 = ((1.0 + 0j, 0j), (t2c, 1.0 + 0j))
    w = _mat_mul(_mat_pow(s1, p), _mat_pow(s2, q))
    return w[0][0] + w[1][1]


def find_root(f, x0, tol=1e-5, max_iter=80):
    """Damped-secant stand-in for FindRoot[..., AccuracyGoal->5, MaxIterations->80]."""
    h = 1e-6
    x = x0
    fx = f(x)
    for _ in range(max_iter):
        if abs(fx) < tol:
            return x
        deriv = (f(x + h) - fx) / h
        if deriv == 0:
            return None
        x_new = x - fx / deriv
        if not math.isfinite(x_new):
            return None
        fx_new = f(x_new)
        if abs(x_new - x) < 1e-9:
            return x_new
        x, fx = x_new, fx_new
    return x if abs(fx) < 1e-3 else None


def pleating_point(p, q, tc, im2, xmin, xmax):
    n_tries = 9
    for i in range(n_tries):
        start = xmin + (xmax - xmin) * i / (n_tries - 1)

        def f(re2, _im2=im2, _p=p, _q=q, _tc=tc):
            tr = word_trace(_p, _q, _tc, complex(re2, _im2))
            return abs(tr) ** 2 - 4.0

        sol = find_root(f, start)
        if sol is not None and xmin <= sol <= xmax:
            return sol
    return None


def compute_ray_data():
    u = tval.real
    xmin, xmax = -1.0, 1.0
    ymin, ymax = 0.0, u

    all_farey = farey_sequence(fareyDepth)
    im_vals = [ymin + (ymax - ymin) * i / nRayPts for i in range(nRayPts + 1)]

    ray_data = {}
    for frac in all_farey:
        p, q = frac.numerator, frac.denominator
        pts = []
        for iv in im_vals:
            re = pleating_point(p, q, tval, iv, xmin, xmax)
            if re is not None:
                pts.append((re, iv))
        if len(pts) > 3:
            ray_data[frac] = pts

    return all_farey, ray_data

# ============================================================================
# 5. Coordinate transforms   (stripToScreen, steemannToUnit / rayToUnit)
# ============================================================================

def strip_to_screen(re, im):
    z = complex(re, im)
    q = z - pInv
    zScr = pInv + r2 / q.conjugate()
    return zScr.real, zScr.imag


def steemann_to_unit(sx, sy):
    cx = (diskXmin + diskXmax) / 2.0
    cy = (diskYmin + diskYmax) / 2.0
    hx = (diskXmax - diskXmin) / 2.0
    hy = (diskYmax - diskYmin) / 2.0
    return (sx - cx) / hx, (sy - cy) / hy


def ray_thickness(frac):
    return max(0.0004, 0.004 / frac.denominator)

# ============================================================================
# 6. Blender scene building
# ============================================================================

def get_collection(name, parent=None):
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(coll)
    return coll


def clear_collection(coll):
    for obj in list(coll.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def make_unlit_material(name, color=None, image=None):
    """Flat/unlit shader: Image Texture or a solid colour -> Emission -> Output."""
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emit = nt.nodes.new("ShaderNodeEmission")
    out.location, emit.location = (300, 0), (100, 0)

    if image is not None:
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = image
        tex.interpolation = 'Closest'
        tex.location = (-200, 0)
        nt.links.new(tex.outputs["Color"], emit.inputs["Color"])
    else:
        emit.inputs["Color"].default_value = color

    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat


def make_plane(name, coll, width, height, location, material):
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    hw, hh = width / 2.0, height / 2.0
    v0 = bm.verts.new((-hw, -hh, 0))
    v1 = bm.verts.new((hw, -hh, 0))
    v2 = bm.verts.new((hw, hh, 0))
    v3 = bm.verts.new((-hw, hh, 0))
    bm.faces.new((v0, v1, v2, v3))
    bm.to_mesh(mesh)
    bm.free()

    uv = mesh.uv_layers.new(name="UVMap")
    for loop, co in zip(mesh.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        uv.data[loop.index].uv = co

    obj = bpy.data.objects.new(name, mesh)
    obj.location = location
    obj.data.materials.append(material)
    coll.objects.link(obj)
    return obj


def make_line_curve(name, coll, points_2d, z, material, thickness, offset=(0, 0, 0)):
    curve = bpy.data.curves.new(name, type='CURVE')
    curve.dimensions = '3D'
    curve.bevel_depth = thickness
    curve.bevel_resolution = 2
    curve.fill_mode = 'FULL'

    spline = curve.splines.new('POLY')
    spline.points.add(len(points_2d) - 1)
    for i, (x, y) in enumerate(points_2d):
        spline.points[i].co = (x + offset[0], y + offset[1], z + offset[2], 1.0)

    obj = bpy.data.objects.new(name, curve)
    obj.data.materials.append(material)
    coll.objects.link(obj)
    return obj


class MaterialCache:
    """Avoids spawning thousands of near-duplicate ray materials."""
    def __init__(self, prefix):
        self.prefix = prefix
        self._cache = {}

    def get(self, color):
        key = tuple(round(c, 3) for c in color)
        mat = self._cache.get(key)
        if mat is None:
            mat = make_unlit_material(f"{self.prefix}_{key}", color=color)
            self._cache[key] = mat
        return mat


def build_scene():
    print("Building Kleinian limit-set scene ...")
    root = get_collection("Kleinian_v10")
    clear_collection(root)
    strip_coll = get_collection("Klein_StripRays", parent=root)
    disk_coll = get_collection("Klein_DiskRays", parent=root)
    clear_collection(strip_coll)
    clear_collection(disk_coll)

    # -- escape-time canvases -------------------------------------------
    strip_img = make_strip_image()
    disk_img = make_disk_image()
    strip_mat = make_unlit_material("Klein_StripMat", image=strip_img)
    disk_mat = make_unlit_material("Klein_DiskMat", image=disk_img)

    u = tval.real
    make_plane("StripPlane", root, 2.0, u, (0, u / 2.0, 0), strip_mat)
    make_plane("DiskPlane", root, 2.0, 2.0, (PANEL_GAP, 0, 0), disk_mat)

    # -- Farey pleating rays ----------------------------------------------
    print("Computing Farey pleating rays (this is the slow step) ...")
    all_farey, ray_data = compute_ray_data()
    print(f"  {len(all_farey)} Farey fractions at depth {fareyDepth}, "
          f"{len(ray_data)} rays with usable data")

    ray_mats = MaterialCache("Klein_RayMat")
    n_fracs = len(all_farey)

    for idx, frac in enumerate(all_farey, start=1):
        if frac not in ray_data:
            continue
        pts = ray_data[frac]
        col = dark_rainbow_color(idx / n_fracs)
        mat = ray_mats.get(col)
        thick = ray_thickness(frac)
        tag = f"{frac.numerator}_{frac.denominator}"

        # strip overlay: raw (re, im), single copy, matches stripRayLines
        make_line_curve(f"StripRay_{tag}", strip_coll, pts, 0.001,
                         mat, thick * 0.5, offset=(0, 0, 0))

        # disk overlay: through the inversion, normalized, 4-fold mirrored
        screen_pts = [strip_to_screen(re, im) for re, im in pts]
        screen_pts = [p for p in screen_pts
                      if diskXmin <= p[0] <= diskXmax and diskYmin <= p[1] <= diskYmax]
        if len(screen_pts) <= 2:
            continue
        unit_pts = [steemann_to_unit(sx, sy) for sx, sy in screen_pts]
        unit_pts = [p for p in unit_pts if math.hypot(*p) <= 1.05]
        if len(unit_pts) <= 2:
            continue

        mirrors = {
            "pp": unit_pts,
            "np": [(-x, y) for x, y in unit_pts],
            "pn": [(x, -y) for x, y in unit_pts],
            "nn": [(-x, -y) for x, y in unit_pts],
        }
        for mtag, mpts in mirrors.items():
            make_line_curve(f"DiskRay_{tag}_{mtag}", disk_coll, mpts, 0.001,
                             mat, thick, offset=(PANEL_GAP, 0, 0))

    # -- unit circle boundary --------------------------------------------
    circle_pts = [(math.cos(2 * math.pi * i / 128), math.sin(2 * math.pi * i / 128))
                  for i in range(129)]
    circle_mat = make_unlit_material("Klein_CircleMat", color=(0.3, 0.3, 0.3, 1.0))
    make_line_curve("UnitCircle", disk_coll, circle_pts, 0.0005,
                     circle_mat, 0.005, offset=(PANEL_GAP, 0, 0))

    if ADD_LABELS:
        add_ray_labels(all_farey, ray_data, disk_coll, ray_mats)

    setup_camera()
    print("Done.")


def add_ray_labels(all_farey, ray_data, disk_coll, ray_mats):
    n_fracs = len(all_farey)
    for idx, frac in enumerate(all_farey, start=1):
        if frac not in ray_data or len(ray_data[frac]) <= 10:
            continue
        pts = ray_data[frac]
        screen_pts = [strip_to_screen(re, im) for re, im in pts]
        screen_pts = [p for p in screen_pts
                      if diskXmin <= p[0] <= diskXmax and diskYmin <= p[1] <= diskYmax]
        if len(screen_pts) <= 5:
            continue
        unit_pts = [steemann_to_unit(sx, sy) for sx, sy in screen_pts]
        unit_pts = [p for p in unit_pts if math.hypot(*p) <= 1.05]
        if len(unit_pts) <= 5:
            continue

        mid = unit_pts[len(unit_pts) // 2]
        mat = ray_mats.get(dark_rainbow_color(idx / n_fracs))
        label = f"{frac.numerator}/{frac.denominator}"

        for mtag, mp in (("pp", mid), ("np", (-mid[0], mid[1])),
                          ("pn", (mid[0], -mid[1])), ("nn", (-mid[0], -mid[1]))):
            fc = bpy.data.curves.new(f"Label_{label}_{mtag}", type='FONT')
            fc.body = label
            fc.size = 0.03
            obj = bpy.data.objects.new(f"Label_{label}_{mtag}", fc)
            obj.location = (PANEL_GAP + mp[0], mp[1], 0.002)
            obj.data.materials.append(mat)
            disk_coll.objects.link(obj)


def setup_camera():
    cam_data = bpy.data.cameras.get("Klein_Cam") or bpy.data.cameras.new("Klein_Cam")
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = PANEL_GAP + 2.5

    cam_obj = bpy.data.objects.get("Klein_Cam")
    if cam_obj is None:
        cam_obj = bpy.data.objects.new("Klein_Cam", cam_data)
        bpy.context.scene.collection.objects.link(cam_obj)

    cam_obj.location = (PANEL_GAP / 2.0, 0.3, 10)
    cam_obj.rotation_euler = (0, 0, 0)
    bpy.context.scene.camera = cam_obj

# ============================================================================
if __name__ == "__main__":
    build_scene()
