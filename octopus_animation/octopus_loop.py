import bpy
import numpy as np
from bpy.app.handlers import persistent

# ---------------- Settings ----------------
N_POINTS    = 10000
SPEED       = 3             # animation speed: 1, 3, 5, 10 ... (any number > 0)
BASE_FRAMES = 2400          # loop length at SPEED = 1
FRAME_START = 1
FPS         = 24
LINEAR      = True          # True = constant speed, False = original (eased) timing
# ------------------------------------------

N_FRAMES  = max(1, round(BASE_FRAMES / SPEED))   # one full loop; timeline shrinks with speed
LOOP_T    = 32 * np.pi      # exact period of the formula in t
FRAME_END = FRAME_START + N_FRAMES - 1

# Clear the scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# --- Time-independent part (computed once) ---
i = np.arange(N_POINTS)
x = i % 200
y = i / 55
k = 9 * np.cos(x / 8)
e = y / 8 - 12.5
r2 = k**2 + e**2
sin_a = np.sin(np.arctan2(k, e) * 7)


def compute_coords(t, idx=slice(None)):
    """Vertex positions for time t, shape (n, 3)."""
    k_, e_, r2_, s_ = k[idx], e[idx], r2[idx], sin_a[idx]
    d = r2_ / 99 + np.sin(t) / 6 + 0.5
    q = 99 - e_ * s_ / d + k_ * (3 + np.cos(d * d - t) * 2)
    c = d / 2 + e_ / 69 - t / 16
    co = np.empty((len(d), 3), dtype=np.float32)
    co[:, 0] = q * np.sin(c)
    co[:, 1] = (q + 19 * d) * np.cos(c)
    co[:, 2] = d * 10
    return co


# --- Constant-speed time mapping (arc-length reparametrisation) ---
def build_time_table(n_samples=20000, stride=7):
    """Table t <-> normalised distance travelled by the points over one loop."""
    ts = np.linspace(0.0, LOOP_T, n_samples + 1)
    probe = slice(None, None, stride)   # 7 is coprime to 200 and 55: no aliasing
    dist = np.zeros(n_samples + 1)
    prev = compute_coords(ts[0], probe)
    for n in range(1, n_samples + 1):
        cur = compute_coords(ts[n], probe)
        dist[n] = dist[n - 1] + np.linalg.norm(cur - prev, axis=1).mean()
        prev = cur
    return ts, dist / dist[-1]


TS, CUM = build_time_table() if LINEAR else (None, None)


def frame_to_t(frame):
    phase = (frame - FRAME_START) % N_FRAMES      # wraps: frame_end + 1 == frame_start
    s = phase / N_FRAMES                           # 0 <= s < 1
    if LINEAR:
        return float(np.interp(s, CUM, TS))        # equal distance per frame
    return s * LOOP_T


# --- Create the mesh (vertices only) ---
mesh = bpy.data.meshes.new("GeneratedMesh")
obj = bpy.data.objects.new("GeneratedObject", mesh)
bpy.context.collection.objects.link(obj)
mesh.vertices.add(N_POINTS)


@persistent
def update_points(scene, depsgraph=None):
    o = bpy.data.objects.get("GeneratedObject")
    if o is None:
        return
    t = frame_to_t(scene.frame_current)
    o.data.vertices.foreach_set("co", compute_coords(t).ravel())
    o.data.update()


# Remove old copies of the handler (so re-running the script doesn't stack them)
for h in list(bpy.app.handlers.frame_change_pre):
    if h.__name__ == "update_points":
        bpy.app.handlers.frame_change_pre.remove(h)
bpy.app.handlers.frame_change_pre.append(update_points)

# --- Timeline setup ---
scene = bpy.context.scene
scene.render.fps = FPS
scene.frame_start = FRAME_START
scene.frame_end = FRAME_END
scene.sync_mode = 'NONE'          # "Play Every Frame": no skipped frames during playback
scene.frame_set(FRAME_START)
update_points(scene)
