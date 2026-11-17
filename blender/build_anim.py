"""
CoreBall - 8 秒动画

打开已保存的工位场景，让球按"规划出的路径 + S 曲线节奏 + 4mm 回弹"走一遍，
直接输出 mp4。

用法：
  blender --background --python build_anim.py -- --out blender/out/anim
  blender --background --python build_anim.py -- --out blender/out/anim --test
"""

import bpy
import sys
import os
import math
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))

import plan  # noqa: E402

RIG = os.path.join(HERE, "out", "rig", "coreball_rig.blend")

# ---------------- 时间与路径 ----------------
FPS = 24
T_TRAVEL = 5.0          # 走完这段路用多久
T_TOTAL = 8.0
OVERSHOOT = 0.0035      # 约 4mm / 1139mm

bpy.ops.wm.open_mainfile(filepath=RIG)
sc = bpy.context.scene

PATH = plan.astar(plan.START, plan.GOAL, "steady")
if not PATH:
    raise RuntimeError("没找到路径")

# 弧长参数化
seg = [0.0]
for i in range(1, len(PATH)):
    seg.append(seg[-1] + math.hypot(PATH[i][0] - PATH[i - 1][0],
                                    PATH[i][1] - PATH[i - 1][1]))
TOTAL_LEN = seg[-1]


def pos_at(u):
    """u ∈ [0, 1.02]，按弧长取点，u>1 时沿末端方向外推"""
    d = u * TOTAL_LEN
    if d <= 0:
        return Vector((PATH[0][0], PATH[0][1], 0.0))
    if d <= TOTAL_LEN:
        for i in range(1, len(PATH)):
            if seg[i] >= d:
                f = (d - seg[i - 1]) / max(1e-6, seg[i] - seg[i - 1])
                x = PATH[i - 1][0] + f * (PATH[i][0] - PATH[i - 1][0])
                y = PATH[i - 1][1] + f * (PATH[i][1] - PATH[i - 1][1])
                return Vector((x, y, 0.0))
    dx = PATH[-1][0] - PATH[-2][0]
    dy = PATH[-1][1] - PATH[-2][1]
    n = math.hypot(dx, dy)
    over = d - TOTAL_LEN
    return Vector((PATH[-1][0] + dx / n * over, PATH[-1][1] + dy / n * over, 0.0))


def progress(t):
    if t <= 0:
        return 0.0
    if t < T_TRAVEL:
        s = t / T_TRAVEL
        return 10 * s ** 3 - 15 * s ** 4 + 6 * s ** 5
    dt = t - T_TRAVEL
    return 1.0 + OVERSHOOT * math.exp(-4.5 * dt) * math.cos(2 * math.pi * 1.2 * dt)


# ---------------- 收集要一起移动的东西 ----------------
# ---------------- 分组：底板组（跟线走）+ 偏航组（转头）----------------
YAW_NAMES = ["hub_plug", "breakaway_ring", "ball_root"] + ["plug_key_%d" % k for k in range(3)]
YAW_OBJS = [o for o in bpy.data.objects if o.name in YAW_NAMES]
MOVE_OBJS = [o for o in bpy.data.objects
             if o.name.startswith(("hub_", "lug_", "tether_")) and o.name not in YAW_NAMES]

root = bpy.data.objects.new("MOVE", None)
bpy.context.scene.collection.objects.link(root)

# 吊点顶板的初始世界坐标（mm）
HUB0 = Vector(bpy.data.objects["hub_plate"].location) * 1000.0

yaw_root = bpy.data.objects.new("YAW", None)
bpy.context.scene.collection.objects.link(yaw_root)
yaw_root.location = HUB0 * 0.001

for o in MOVE_OBJS:
    o.parent = root
    o.matrix_parent_inverse = root.matrix_world.inverted()
for o in YAW_OBJS:
    o.parent = yaw_root
    o.matrix_parent_inverse = yaw_root.matrix_world.inverted()

# ---------------- 线缆 ----------------
CABLES = []
for i in range(1, 5):
    ob = bpy.data.objects.get("cable_%d" % i)
    if ob:
        p0 = Vector(ob.data.splines[0].points[0].co[:3]) * 1000.0
        p1 = Vector(ob.data.splines[0].points[1].co[:3]) * 1000.0
        CABLES.append((ob, p0, p1 - HUB0))

WIRES = []
for name, which in (("wire_1", "end"), ("wire_2", "start")):
    ob = bpy.data.objects.get(name)
    if ob:
        p0 = Vector(ob.data.splines[0].points[0].co[:3]) * 1000.0
        p1 = Vector(ob.data.splines[0].points[1].co[:3]) * 1000.0
        WIRES.append((ob, which, p0, p1))

PULLEY_OFF = Vector((0.0, 0.0, 46.0))     # 吊点顶部小滑轮相对吊点中心

# ---------------- 灯带渐变 ----------------
led = bpy.data.materials.get("Core_LED")
if led:
    s = led.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]


def yaw_at(t):
    """转头：路上看着前方，快到时转回来看着你"""
    eps = 0.06
    p1 = pos_at(progress(t + eps))
    p0 = pos_at(progress(t - eps))
    vx, vy = p1.x - p0.x, p1.y - p0.y
    if abs(vx) + abs(vy) < 1e-6:
        return 0.0
    a = math.degrees(math.atan2(-vx, vy))
    a = max(-55.0, min(55.0, a))
    if t > T_TRAVEL - 1.2:
        f = max(0.0, (T_TRAVEL - t) / 1.2)
        a *= f
    return a


def apply(frame):
    t = (frame - 1) / FPS
    p = progress(t)
    pos = pos_at(p)
    hub = Vector((pos.x, pos.y, HUB0.z))

    root.location = (hub - HUB0) * 0.001
    yaw_root.location = hub * 0.001
    yaw_root.rotation_euler = (0.0, 0.0, math.radians(yaw_at(t)))

    # 灯带：前 1.5 秒从暗到亮，之后呼吸
    if led:
        if t < 1.5:
            v = 1.6 * (t / 1.5) ** 2
        else:
            v = 1.6 + 0.35 * math.sin((t - 1.5) * 2.4)
        s.default_value = max(0.02, v)

    for ob, p0, off in CABLES:
        pt = ob.data.splines[0].points[1]
        v = hub + off
        pt.co = (v.x * 0.001, v.y * 0.001, v.z * 0.001, 1.0)

    for ob, which, p0, p1 in WIRES:
        pt = ob.data.splines[0].points[1 if which == "end" else 0]
        v = hub + PULLEY_OFF
        pt.co = (v.x * 0.001, v.y * 0.001, v.z * 0.001, 1.0)


def on_frame(scene, *a):
    apply(scene.frame_current)


bpy.app.handlers.frame_change_pre.clear()
bpy.app.handlers.frame_change_pre.append(on_frame)

# ---------------- 渲染设置 ----------------
argv = sys.argv
out_dir = os.path.join(HERE, "out", "anim")
test = False
if "--" in argv:
    rest = argv[argv.index("--") + 1:]
    if "--out" in rest:
        out_dir = rest[rest.index("--out") + 1]
    test = "--test" in rest

os.makedirs(out_dir, exist_ok=True)

sc.render.engine = 'BLENDER_EEVEE_NEXT'
sc.render.resolution_x = 960
sc.render.resolution_y = 540
sc.render.resolution_percentage = 100
sc.render.fps = FPS
sc.frame_start = 1
sc.frame_end = int(T_TOTAL * FPS)
sc.eevee.taa_render_samples = 16

# 相机：稍微拉远一点，让整段路都在画面里
cam = bpy.data.objects.get("Cam")
tgt = bpy.data.objects.get("CamTgt")
if cam:
    cam.location = Vector((900, 3300, 2250)) * 0.001
    cam.data.lens = 40
if tgt:
    tgt.location = Vector((0, 520, 1180)) * 0.001

if test:
    for f in (1, 40, 90, 150):
        sc.frame_set(f)
        sc.render.filepath = os.path.join(out_dir, "test_%03d.png" % f)
        sc.render.image_settings.file_format = 'PNG'
        bpy.ops.render.render(write_still=True)
        print("test frame", f)
else:
    sc.render.image_settings.file_format = 'FFMPEG'
    sc.render.ffmpeg.format = 'MPEG4'
    sc.render.ffmpeg.codec = 'H264'
    sc.render.ffmpeg.constant_rate_factor = 'HIGH'
    sc.render.filepath = os.path.join(out_dir, "coreball.mp4")
    bpy.ops.render.render(animation=True)
    print("video:", os.path.join(out_dir, "coreball.mp4"))
