"""
CoreBall - 桌面立体场景（悬臂版）参数化建模

形态：夹桌门架 + 三面墙小舞台，吊在显示器上方
      四线缆绳驱动，四线汇于一个吊点，球磁吸挂在吊点下

用法：
  blender --background --python build_diorama.py -- --out blender/out --render
"""

import bpy
import sys
import os
import math
from mathutils import Vector

# ============================================================
# 参数（单位 mm）
# ============================================================
# ---- 舞台 ----
ST_W      = 420     # 宽（X）
ST_D      = 220     # 深（Y）
ST_H      = 380     # 高（Z）
BEAM      = 20      # 2020 型材截面
WALL_T    = 5       # 墙板

# ---- 球与吊点 ----
BALL_D    = 80
BALL_Z    = 150     # 球心离舞台底面高度
HUB_GAP   = 55      # 吊点高于球心
ANCHOR_IN = 28      # 锚点从顶角向内偏移

# ---- 舞台离桌高度 ----
STAGE_Z0  = 500

# ---- 桌与显示器 ----
DESK_W, DESK_D, DESK_T = 900, 700, 20
MON_W, MON_H, MON_T    = 560, 320, 22
MON_BOTTOM             = 95
MON_Y                  = -230

# ---- 门架 ----
POST_X    = 300
POST_Y    = -320
POST_TOP  = 890
CROSS_Z   = 885

CABLE_D   = 1.2
MM        = 0.001

# ============================================================
# 工具
# ============================================================
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.length_unit = 'MILLIMETERS'
    sc.render.engine = 'BLENDER_EEVEE_NEXT'
    sc.render.resolution_x = 1800
    sc.render.resolution_y = 1200


def collection(name):
    c = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    return c


def _link(ob, coll):
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    coll.objects.link(ob)


def material(name, color, metallic=0.0, roughness=0.5, emission=None, strength=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = roughness
    if emission is not None:
        b.inputs["Emission Color"].default_value = (*emission, 1.0)
        b.inputs["Emission Strength"].default_value = strength
    return m


def box(name, center, size, mat, coll, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=Vector(center) * MM)
    ob = bpy.context.object
    ob.name = name
    ob.scale = Vector(size) * MM
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat:
        ob.data.materials.append(mat)
    if bevel > 0:
        m = ob.modifiers.new("bevel", 'BEVEL')
        m.width = bevel * MM
        m.segments = 2
    _link(ob, coll)
    return ob


def cyl(name, center, radius, depth, mat, coll, direction=None, verts=32, bevel=0.0):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=verts, radius=radius * MM, depth=depth * MM,
        location=Vector(center) * MM)
    ob = bpy.context.object
    ob.name = name
    if direction is not None:
        ob.rotation_mode = 'QUATERNION'
        ob.rotation_quaternion = Vector(direction).normalized().to_track_quat('Z', 'Y')
    if mat:
        ob.data.materials.append(mat)
    if bevel > 0:
        m = ob.modifiers.new("bevel", 'BEVEL')
        m.width = bevel * MM
        m.segments = 2
    _link(ob, coll)
    return ob


def sphere(name, center, radius, mat, coll):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=48, ring_count=24, radius=radius * MM,
        location=Vector(center) * MM)
    ob = bpy.context.object
    ob.name = name
    ob.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    _link(ob, coll)
    return ob


def cable(name, p1, p2, radius, mat, coll):
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = radius * MM
    cu.bevel_resolution = 2
    sp = cu.splines.new('POLY')
    sp.points.add(1)
    sp.points[0].co = (*p1 * MM, 1.0)
    sp.points[1].co = (*p2 * MM, 1.0)
    ob = bpy.data.objects.new(name, cu)
    ob.data.materials.append(mat)
    coll.objects.link(ob)
    return ob


# 舞台局部坐标 -> 世界坐标
ST_ONLY = None
def S(p):
    """舞台内部坐标（0..W, 0..D, 0..H）转世界坐标"""
    ox, oy, oz = ST_ONLY
    return Vector((ox + p[0], oy + p[1], oz + p[2]))


# ============================================================
# 建
# ============================================================
reset_scene()

C_ALLOY = collection("00_型材")
C_PANEL = collection("01_墙板")
C_WINCH = collection("02_绞盘")
C_BALL  = collection("03_核心球")
C_CABLE = collection("04_线缆")
C_FURN  = collection("05_桌与显示器")
C_LIGHT = collection("06_灯光相机")

M_ALLOY = material("Alu_2020", (0.72, 0.73, 0.75), metallic=0.85, roughness=0.32)
M_PANEL = material("Panel_PVC", (0.88, 0.89, 0.90), 0.0, 0.62)
M_MOTOR = material("Motor", (0.09, 0.09, 0.10), 0.35, 0.45)
M_SPOOL = material("Spool", (0.26, 0.27, 0.29), 0.7, 0.35)
M_CABLE = material("Dyneema", (0.60, 0.62, 0.65), 0.0, 0.28)
M_SHELL = material("Core_Shell", (0.95, 0.955, 0.96), 0.05, 0.22)
M_LED   = material("Core_LED", (0.15, 0.75, 1.0), 0.0, 0.2,
                   emission=(0.15, 0.75, 1.0), strength=1.4)
M_MAG   = material("Magnet", (0.85, 0.72, 0.45), 0.95, 0.25)
M_DESK  = material("Desk", (0.30, 0.24, 0.19), 0.0, 0.72)
M_SCREEN= material("Screen", (0.02, 0.03, 0.05), 0.0, 0.22,
                   emission=(0.10, 0.16, 0.26), strength=0.55)
M_BEZEL = material("Bezel", (0.07, 0.07, 0.08), 0.4, 0.45)
M_FLOOR = material("Floor", (0.045, 0.048, 0.052), 0.0, 0.9)

# ---------------- 桌面 / 显示器 ----------------
box("desk", (0, 0, -DESK_T / 2), (DESK_W, DESK_D, DESK_T), M_DESK, C_FURN, bevel=2)
box("floor", (0, 0, -DESK_T - 400), (3000, 2400, 20), M_FLOOR, C_FURN)

# 显示器
mon_c = (0, MON_Y, MON_BOTTOM + MON_H / 2)
box("monitor_body", mon_c, (MON_W, MON_T, MON_H), M_BEZEL, C_FURN, bevel=3)
box("monitor_screen", (0, MON_Y + MON_T / 2 + 1, MON_BOTTOM + MON_H / 2),
    (MON_W - 20, 2, MON_H - 20), M_SCREEN, C_FURN)
# 支架
box("monitor_neck", (0, MON_Y - 40, (MON_BOTTOM) / 2), (60, 20, MON_BOTTOM), M_BEZEL, C_FURN)
cyl("monitor_base", (0, MON_Y - 40, 4), 110, 8, M_BEZEL, C_FURN, verts=48)

# ---------------- 门架（夹桌）----------------
for sx in (-POST_X, POST_X):
    beam_post = box(f"post_{sx}", (sx, POST_Y, POST_TOP / 2),
                    (BEAM, BEAM, POST_TOP), M_ALLOY, C_ALLOY, bevel=1.5)
    # 桌沿夹
    box(f"clamp_{sx}", (sx, POST_Y, -DESK_T / 2),
        (70, 90, DESK_T + 30), M_MOTOR, C_ALLOY, bevel=2)
    cyl(f"clamp_knob_{sx}", (sx, POST_Y + 55, -DESK_T / 2),
        14, 30, M_MOTOR, C_ALLOY, direction=(0, 1, 0))

# 顶梁
box("crossbar", (0, POST_Y, CROSS_Z), (POST_X * 2 + BEAM, BEAM, BEAM),
    M_ALLOY, C_ALLOY, bevel=1.5)

# ---------------- 舞台本体 ----------------
# 舞台中心对齐显示器，后沿与门架齐平
ST_ONLY = (-ST_W / 2, POST_Y, STAGE_Z0)
ox, oy, oz = ST_ONLY

def sb(name, center, size, mat, coll, bevel=0.0):
    """舞台局部坐标盒子"""
    return box(name, S(center), size, mat, coll, bevel)

# 4 立柱
for i, (x, y) in enumerate([(0, 0), (ST_W, 0), (0, ST_D), (ST_W, ST_D)], 1):
    sb(f"st_post_{i}", (x, y, ST_H / 2), (BEAM, BEAM, ST_H), M_ALLOY, C_ALLOY, bevel=1.5)

# 底框 4 根
sb("st_bot_back",  (ST_W / 2, 0, BEAM / 2),        (ST_W, BEAM, BEAM), M_ALLOY, C_ALLOY, bevel=1.5)
sb("st_bot_front", (ST_W / 2, ST_D, BEAM / 2),     (ST_W, BEAM, BEAM), M_ALLOY, C_ALLOY, bevel=1.5)
sb("st_bot_left",  (0, ST_D / 2, BEAM / 2),        (BEAM, ST_D, BEAM), M_ALLOY, C_ALLOY, bevel=1.5)
sb("st_bot_right", (ST_W, ST_D / 2, BEAM / 2),     (BEAM, ST_D, BEAM), M_ALLOY, C_ALLOY, bevel=1.5)

# 顶框 4 根（绞盘的安装平面）
sb("st_top_back",  (ST_W / 2, 0, ST_H - BEAM / 2),    (ST_W, BEAM, BEAM), M_ALLOY, C_ALLOY, bevel=1.5)
sb("st_top_front", (ST_W / 2, ST_D, ST_H - BEAM / 2), (ST_W, BEAM, BEAM), M_ALLOY, C_ALLOY, bevel=1.5)
sb("st_top_left",  (0, ST_D / 2, ST_H - BEAM / 2),    (BEAM, ST_D, BEAM), M_ALLOY, C_ALLOY, bevel=1.5)
sb("st_top_right", (ST_W, ST_D / 2, ST_H - BEAM / 2), (BEAM, ST_D, BEAM), M_ALLOY, C_ALLOY, bevel=1.5)

# 底板
sb("st_base", (ST_W / 2, ST_D / 2, BEAM / 2), (ST_W - BEAM, ST_D - BEAM, WALL_T), M_PANEL, C_PANEL)

# 背 + 左右 三面墙
sb("st_wall_back",  (ST_W / 2, 0, ST_H / 2),     (ST_W - BEAM, WALL_T, ST_H - 2 * BEAM), M_PANEL, C_PANEL)
sb("st_wall_left",  (0, ST_D / 2, ST_H / 2),     (WALL_T, ST_D - BEAM, ST_H - 2 * BEAM), M_PANEL, C_PANEL)
sb("st_wall_right", (ST_W, ST_D / 2, ST_H / 2),  (WALL_T, ST_D - BEAM, ST_H - 2 * BEAM), M_PANEL, C_PANEL)

# 吊挂：顶梁 -> 舞台顶框
for hx in (-ST_W / 2 + 70, ST_W / 2 - 70):
    box(f"hang_{hx}", (hx, POST_Y, (CROSS_Z + STAGE_Z0 + ST_H) / 2),
        (16, 16, CROSS_Z - (STAGE_Z0 + ST_H)), M_ALLOY, C_ALLOY, bevel=1.0)

# ---------------- 核心球 + 吊点 ----------------
ball_local = Vector((ST_W / 2, ST_D * 0.42, BALL_Z))
ball_c = S(ball_local)
hub_c = ball_c + Vector((0, 0, HUB_GAP))

sphere("core_ball", ball_c, BALL_D / 2, M_SHELL, C_BALL)

# 灯带
bpy.ops.mesh.primitive_torus_add(
    major_radius=(BALL_D / 2 - 1.5) * MM, minor_radius=2.6 * MM,
    major_segments=64, minor_segments=12, location=ball_c * MM)
led = bpy.context.object
led.name = "core_led_ring"
led.data.materials.append(M_LED)
bpy.ops.object.shade_smooth()
_link(led, C_BALL)

# 球顶对接口（磁吸）
cyl("ball_socket", ball_c + Vector((0, 0, BALL_D / 2 - 2)), 15, 6, M_MAG, C_BALL)

# 吊点盘 + 磁吸
cyl("hub_plate", hub_c, 26, 8, M_SPOOL, C_BALL)
cyl("hub_magnet", hub_c - Vector((0, 0, 9)), 13, 12, M_MAG, C_BALL)

# ---------------- 绞盘 + 线 ----------------
anchors = [
    S((ANCHOR_IN, ANCHOR_IN, ST_H - BEAM - ANCHOR_IN)),
    S((ST_W - ANCHOR_IN, ANCHOR_IN, ST_H - BEAM - ANCHOR_IN)),
    S((ANCHOR_IN, ST_D - ANCHOR_IN, ST_H - BEAM - ANCHOR_IN)),
    S((ST_W - ANCHOR_IN, ST_D - ANCHOR_IN, ST_H - BEAM - ANCHOR_IN)),
]

cable_len = []
for i, a in enumerate(anchors, 1):
    to_hub = (hub_c - a).normalized()
    box(f"pulley_{i}", a, (12, 12, 12), M_SPOOL, C_WINCH)
    cyl(f"spool_{i}", a, 14, 20, M_SPOOL, C_WINCH, direction=to_hub)

    # 电机装在顶框外侧
    outward = Vector((0, 0, 0))
    if a.x < S((ST_W / 2, 0, 0)).x: outward.x = -1
    else: outward.x = 1
    if a.y < S((0, ST_D / 2, 0)).y: outward.y = -1
    else: outward.y = 1
    motor_c = a + Vector((outward.x * 34, outward.y * 34, 26))
    box(f"motor_{i}", motor_c, (42.3, 42.3, 42), M_MOTOR, C_WINCH, bevel=1.0)

    # 吊点上的挂耳：朝向该锚点，线正好接在挂耳上
    d = a - hub_c
    d.z = 0
    d.normalize()
    lug_pos = hub_c + d * 20
    cyl(f"hub_lug_{i}", lug_pos, 4.5, 14, M_SPOOL, C_BALL, direction=d)

    cable(f"cable_{i}", a, lug_pos, CABLE_D / 2, M_CABLE, C_CABLE)
    cable_len.append((a - lug_pos).length)

# ============================================================
# 灯光 / 相机
# ============================================================
world = bpy.data.worlds.new("World")
bpy.context.scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.030, 0.034, 0.042, 1.0)
world.node_tree.nodes["Background"].inputs[1].default_value = 1.0

def area_light(name, loc, energy, size, color):
    d = bpy.data.lights.new(name, 'AREA')
    d.energy = energy
    d.size = size * MM
    d.color = color
    ob = bpy.data.objects.new(name, d)
    ob.location = Vector(loc) * MM
    C_LIGHT.objects.link(ob)
    return ob

aim = Vector((0, -120, 560))
k1 = area_light("key",  (-520, 1350, 1300), 30, 500, (1.0, 0.96, 0.90))
k2 = area_light("fill", (1050, 900, 820), 10, 400, (0.72, 0.84, 1.0))
k3 = area_light("rim",  (240, -980, 1050), 16, 400, (0.55, 0.88, 1.0))

for lt in (k1, k2, k3):
    e = bpy.data.objects.new(f"aim_{lt.name}", None)
    e.location = aim * MM
    C_LIGHT.objects.link(e)
    c = lt.constraints.new('TRACK_TO')
    c.target = e
    c.track_axis = 'TRACK_NEGATIVE_Z'
    c.up_axis = 'UP_Y'

cam_data = bpy.data.cameras.new("Camera")
cam_data.lens = 50
cam_data.dof.use_dof = True
cam_data.dof.focus_distance = 2.47
cam_data.dof.aperture_fstop = 8.0
cam = bpy.data.objects.new("Camera", cam_data)
cam.location = Vector((1150, 2000, 1150)) * MM
C_LIGHT.objects.link(cam)
bpy.context.scene.camera = cam

tgt = bpy.data.objects.new("CamTarget", None)
tgt.location = Vector((0, -100, 540)) * MM
C_LIGHT.objects.link(tgt)
c = cam.constraints.new('TRACK_TO')
c.target = tgt
c.track_axis = 'TRACK_NEGATIVE_Z'
c.up_axis = 'UP_Y'

# 合成：灯带辉光
sc = bpy.context.scene
sc.use_nodes = True
tree = sc.node_tree
for n in list(tree.nodes):
    tree.nodes.remove(n)
rl = tree.nodes.new("CompositorNodeRLayers")
gl = tree.nodes.new("CompositorNodeGlare")
gl.glare_type = 'FOG_GLOW'
gl.quality = 'HIGH'
gl.threshold = 1.0
gl.size = 7
cp = tree.nodes.new("CompositorNodeComposite")
tree.links.new(rl.outputs["Image"], gl.inputs["Image"])
tree.links.new(gl.outputs["Image"], cp.inputs["Image"])

# ============================================================
# 输出
# ============================================================
argv = sys.argv
try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    HERE = os.getcwd()
out_dir = os.path.join(HERE, "out")
do_render = False
if "--" in argv:
    rest = argv[argv.index("--") + 1:]
    if "--out" in rest:
        out_dir = rest[rest.index("--out") + 1]
    do_render = "--render" in rest

os.makedirs(out_dir, exist_ok=True)
blend_path = os.path.join(out_dir, "coreball_diorama.blend")
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(blend_path))

rows = [
    ("2020 铝型材", "4 × %d mm" % ST_H, "舞台立柱"),
    ("2020 铝型材", "4 × %d mm" % ST_W, "舞台上下框（前后）"),
    ("2020 铝型材", "4 × %d mm" % (ST_D - BEAM), "舞台上下框（左右）"),
    ("2020 铝型材", "2 × %d mm" % POST_TOP, "门架立柱"),
    ("2020 铝型材", "1 × %d mm" % (POST_X * 2 + BEAM), "门架顶梁"),
    ("桌沿夹", "2 套", "免打孔固定"),
    ("5mm PVC 板", "%d × %d" % (ST_W - BEAM, ST_D - BEAM), "舞台底板"),
    ("5mm PVC 板", "%d × %d" % (ST_W - BEAM, ST_H - 2 * BEAM), "背板"),
    ("5mm PVC 板", "%d × %d ×2" % (ST_D - BEAM, ST_H - 2 * BEAM), "侧板"),
    ("NEMA17 步进", "4 台", "绞盘"),
    ("卷筒 φ28", "4 个", "绕线"),
    ("大力马线 φ0.4", "4 × %.0f mm（当前位）" % max(cable_len), "四线汇一吊点"),
    ("球壳", "φ%d mm" % BALL_D, "3D 打印，上下半球"),
    ("WS2812", "约 %d mm" % int(math.pi * (BALL_D - 3)), "球赤道一圈"),
    ("磁吸对接口", "1 套", "球顶 <-> 吊点"),
]

with open(os.path.join(out_dir, "bom.md"), "w", encoding="utf-8") as f:
    f.write("# CoreBall 悬臂版 BOM\n\n| 件 | 规格 | 用途 |\n|---|---|---|\n")
    for a, b, c2 in rows:
        f.write("| %s | %s | %s |\n" % (a, b, c2))
    f.write("\n## 线长（当前球位）\n\n")
    for i, L in enumerate(cable_len, 1):
        f.write("- 线 %d：%.1f mm\n" % (i, L))
    f.write("\n## 关键尺寸\n\n")
    f.write("- 舞台内腔：%d × %d × %d mm\n" % (ST_W, ST_D, ST_H))
    f.write("- 舞台净空：%d × %d × %d mm\n" % (ST_W - BEAM, ST_D - BEAM, ST_H - 2 * BEAM))
    f.write("- 舞台底面离桌：%d mm\n" % STAGE_Z0)
    f.write("- 球心离舞台底：%d mm\n" % BALL_Z)
    f.write("- 吊点高于球心：%d mm\n" % HUB_GAP)
    f.write("- 球直径：%d mm\n" % BALL_D)
    f.write("- 桌面占用：仅门架两根立柱（%d mm 间距，贴后沿）\n" % (POST_X * 2))

print("=" * 52)
print("舞台净空: %d x %d x %d" % (ST_W - BEAM, ST_D - BEAM, ST_H - 2 * BEAM))
print("线长:", ", ".join("%.0f" % L for L in cable_len), "mm")
print("blend:", os.path.abspath(blend_path))
print("=" * 52)

if do_render:
    sc.render.filepath = os.path.abspath(os.path.join(out_dir, "render.png"))
    sc.render.image_settings.file_format = 'PNG'
    bpy.ops.render.render(write_still=True)
    print("render:", sc.render.filepath)

    # 近景：球 + 吊点 + 磁吸
    cam2_data = bpy.data.cameras.new("CameraClose")
    cam2_data.lens = 85
    cam2_data.dof.use_dof = True
    cam2_data.dof.focus_distance = 0.62
    cam2_data.dof.aperture_fstop = 2.8
    cam2 = bpy.data.objects.new("CameraClose", cam2_data)
    cam2.location = Vector((360, 250, 800)) * MM
    C_LIGHT.objects.link(cam2)
    tgt2 = bpy.data.objects.new("CamTarget2", None)
    tgt2.location = ball_c * MM
    C_LIGHT.objects.link(tgt2)
    c2 = cam2.constraints.new('TRACK_TO')
    c2.target = tgt2
    c2.track_axis = 'TRACK_NEGATIVE_Z'
    c2.up_axis = 'UP_Y'
    sc.camera = cam2
    sc.render.resolution_x = 1600
    sc.render.resolution_y = 1600
    sc.render.filepath = os.path.abspath(os.path.join(out_dir, "render_closeup.png"))
    bpy.ops.render.render(write_still=True)
    print("closeup:", sc.render.filepath)
