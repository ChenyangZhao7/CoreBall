"""
CoreBall - 工位围合版（booth）参数化建模  v4

v4 变化：
  1. 正面（后墙，人正对的那面）也加电磁板 —— 三面各一块
  2. 线圈阵列加密（用程序化贴图，不生成几何体，可以任意密）
  3. 线圈不再凸出来：平齐嵌在板面下，只能看到浅浅的圆斑

用法：
  blender --background --python build_booth.py -- --out blender/out --render
"""

import bpy
import sys
import os
import math
from mathutils import Vector

# ============================================================
# 参数（mm）
# ============================================================
WALL_H   = 1900
WALL_T   = 20
BOOTH_W  = 1640
BOOTH_D  = 1100

DESK_W, DESK_D = 1560, 700
DESK_Z   = 740
DESK_T   = 25
DESK_CY  = 370

BALL_D   = 80
FLY_POS  = (430, 520, 1420)
HUB_GAP  = 60

NECK_POS = (0, 890, 1155)
NECK_R   = 300

# ---- 电磁板 ----
PANEL_T   = 26
PANEL_Y0, PANEL_Y1 = 200, 930        # 侧板沿墙方向
PANEL_Z0, PANEL_Z1 = 690, 1660       # 高度
BACK_X0, BACK_X1   = -420, 420       # 正面板宽度

COIL_PITCH = 40                      # 线圈间距（越小越密）
COIL_FACE_R = 15                     # 板面上可见圆斑半径

# ---- 固定对接口（左板顶部）----
DOCK_Y  = (PANEL_Y0 + PANEL_Y1) / 2
DOCK_Z  = PANEL_Z1 - 90
FUNNEL_R1 = 46
FUNNEL_R2 = 66

AX = BOOTH_W / 2
ANCHOR_Z = WALL_H - 70

CABLE_D = 4.0     # 视觉放大，真实 φ0.6
MM      = 0.001

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


def material(name, color, metallic=0.0, roughness=0.5, emission=None, strength=1.0, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = roughness
    if emission is not None:
        b.inputs["Emission Color"].default_value = (*emission, 1.0)
        b.inputs["Emission Strength"].default_value = strength
    if alpha < 1.0:
        b.inputs["Alpha"].default_value = alpha
        m.blend_method = 'BLEND'
    return m


def em_panel_material(name, base, dot, rough_base=0.55, rough_dot=0.28):
    """板面藏着线圈阵列：用程序化点阵，平齐不凸出，密度随便调"""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]

    tc = nt.nodes.new("ShaderNodeTexCoord")
    tc.location = (-900, 0)

    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.location = (-700, 0)
    vor.feature = 'F1'
    vor.inputs["Scale"].default_value = 1.0 / (COIL_PITCH * MM)
    vor.inputs["Randomness"].default_value = 0.0

    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.location = (-480, 0)
    ramp.color_ramp.interpolation = 'CONSTANT'
    ramp.color_ramp.elements[0].position = 0.26
    ramp.color_ramp.elements[1].position = 0.30

    col_mix = nt.nodes.new("ShaderNodeMix")
    col_mix.data_type = 'RGBA'
    col_mix.location = (-240, 120)
    col_mix.inputs[6].default_value = (*base, 1.0)
    col_mix.inputs[7].default_value = (*dot, 1.0)

    r_mix = nt.nodes.new("ShaderNodeMapRange")
    r_mix.location = (-240, -140)
    r_mix.inputs["To Min"].default_value = rough_base
    r_mix.inputs["To Max"].default_value = rough_dot

    nt.links.new(tc.outputs["Object"], vor.inputs["Vector"])
    nt.links.new(vor.outputs["Distance"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], col_mix.inputs[0])
    nt.links.new(ramp.outputs["Color"], r_mix.inputs["Value"])
    nt.links.new(col_mix.outputs[2], bsdf.inputs["Base Color"])
    nt.links.new(r_mix.outputs["Result"], bsdf.inputs["Roughness"])
    bsdf.inputs["Metallic"].default_value = 0.25
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


def cyl(name, center, radius, depth, mat, coll, direction=None, verts=32):
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
    _link(ob, coll)
    return ob


def cone(name, center, r1, r2, depth, mat, coll, direction=(1, 0, 0), verts=40):
    bpy.ops.mesh.primitive_cone_add(
        vertices=verts, radius1=r1 * MM, radius2=r2 * MM, depth=depth * MM,
        location=Vector(center) * MM)
    ob = bpy.context.object
    ob.name = name
    ob.rotation_mode = 'QUATERNION'
    ob.rotation_quaternion = Vector(direction).normalized().to_track_quat('Z', 'Y')
    if mat:
        ob.data.materials.append(mat)
    _link(ob, coll)
    return ob


def sphere(name, center, radius, mat, coll):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=40, ring_count=20, radius=radius * MM,
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


def core_ball(name, c, coll, magnet_top=True):
    c = Vector(c)
    sphere(name, c, BALL_D / 2, M_SHELL, coll)
    bpy.ops.mesh.primitive_torus_add(
        major_radius=(BALL_D / 2 - 1.5) * MM, minor_radius=2.6 * MM,
        major_segments=64, minor_segments=12, location=c * MM)
    led = bpy.context.object
    led.name = name + "_led"
    led.data.materials.append(M_LED)
    bpy.ops.object.shade_smooth()
    _link(led, coll)
    if magnet_top:
        cyl(name + "_iron", c + Vector((0, 0, BALL_D / 2 - 3)), 16, 8, M_METAL, coll)


# ============================================================
# 建
# ============================================================
reset_scene()

C_WALL  = collection("00_围板")
C_PANEL = collection("01_电磁板")
C_DESK  = collection("02_桌与设备")
C_PERSON= collection("03_人")
C_BALL  = collection("04_球")
C_CABLE = collection("05_线缆")
C_WINCH = collection("06_绞盘")
C_ZONE  = collection("07_禁区")
C_LIGHT = collection("08_灯光相机")

M_WALL  = material("Wall_Panel", (0.84, 0.85, 0.86), 0.0, 0.52)
M_WALLIN= material("Wall_Inner", (0.72, 0.74, 0.77), 0.0, 0.45)
M_FRAME = material("Frame", (0.14, 0.15, 0.16), 0.6, 0.42)
M_EMB   = em_panel_material("EM_Board", (0.160, 0.185, 0.220), (0.120, 0.140, 0.170), 0.52, 0.42)
M_DOCK  = material("Dock", (0.60, 0.62, 0.65), 0.9, 0.25)
M_DESK  = material("Desk", (0.38, 0.30, 0.23), 0.0, 0.65)
M_METAL = material("Metal", (0.56, 0.57, 0.60), 0.9, 0.28)
M_DARK  = material("Dark", (0.07, 0.07, 0.08), 0.4, 0.45)
M_SCREEN= material("Screen", (0.02, 0.03, 0.05), 0.0, 0.20,
                   emission=(0.12, 0.19, 0.30), strength=0.9)
M_SKIN  = material("Skin", (0.46, 0.36, 0.31), 0.0, 0.70)
M_CLOTH = material("Cloth", (0.19, 0.21, 0.25), 0.0, 0.78)
M_SHELL = material("Core_Shell", (0.95, 0.955, 0.96), 0.05, 0.20)
M_LED   = material("Core_LED", (0.15, 0.75, 1.0), 0.0, 0.2,
                   emission=(0.15, 0.75, 1.0), strength=1.6)
M_MAG   = material("Magnet", (0.85, 0.70, 0.40), 0.95, 0.22)
M_CABLES= material("Cable", (0.58, 0.60, 0.63), 0.0, 0.30)
M_FLOOR = material("Floor", (0.055, 0.060, 0.068), 0.0, 0.85)
M_ZONE  = material("NoFly", (1.0, 0.38, 0.16), 0.0, 0.5,
                   emission=(1.0, 0.38, 0.16), strength=1.1, alpha=0.10)

# ---------------- 地面 ----------------
box("floor", (0, 1600, -10), (5200, 5200, 20), M_FLOOR, C_WALL)

# ---------------- 三面围板 ----------------
box("wall_back", (0, 0, WALL_H / 2),
    (BOOTH_W + 2 * WALL_T, WALL_T, WALL_H), M_WALL, C_WALL)
box("wall_back_in", (0, WALL_T / 2, WALL_H / 2),
    (BOOTH_W, 2, WALL_H - 40), M_WALLIN, C_WALL)

for sx in (-1, 1):
    box(f"wall_side_{sx}", (sx * AX, BOOTH_D / 2, WALL_H / 2),
        (WALL_T, BOOTH_D, WALL_H), M_WALL, C_WALL)
    box(f"wall_side_in_{sx}", (sx * (AX - WALL_T / 2), BOOTH_D / 2, WALL_H / 2),
        (2, BOOTH_D - 40, WALL_H - 40), M_WALLIN, C_WALL)

for sx in (-1, 1):
    for y in (0, BOOTH_D):
        box(f"edge_{sx}_{y}", (sx * AX, y, WALL_H / 2), (36, 36, WALL_H), M_FRAME, C_WALL)
box("edge_top_back", (0, 0, WALL_H), (BOOTH_W + 2 * WALL_T, 36, 36), M_FRAME, C_WALL)
for sx in (-1, 1):
    box(f"edge_top_{sx}", (sx * AX, BOOTH_D / 2, WALL_H),
        (36, BOOTH_D, 36), M_FRAME, C_WALL)

# ---------------- 电磁板：三块 ----------------
PANEL_CY = (PANEL_Y0 + PANEL_Y1) / 2
PANEL_DY = PANEL_Y1 - PANEL_Y0
PANEL_CZ = (PANEL_Z0 + PANEL_Z1) / 2
PANEL_DZ = PANEL_Z1 - PANEL_Z0
BACK_CX  = (BACK_X0 + BACK_X1) / 2
BACK_DX  = BACK_X1 - BACK_X0

def add_panel(name, normal, center, size):
    """挂一块电磁板：板体 + 边框"""
    box(f"{name}_board", center, size, M_EMB, C_PANEL, bevel=3)
    n = Vector(normal)
    # 边框：沿两个切向各两根
    if abs(n.x) > 0.5:
        frame_x = center[0] + n.x * 6
        for dz in (-1, 1):
            box(f"{name}_fz{dz}", (frame_x, center[1], center[2] + dz * (size[2] / 2 + 10)),
                (size[0] + 22, size[1] + 34, 20), M_FRAME, C_PANEL, bevel=2)
        for dy in (-1, 1):
            box(f"{name}_fy{dy}", (frame_x, center[1] + dy * (size[1] / 2 + 10), center[2]),
                (size[0] + 22, 20, size[2]), M_FRAME, C_PANEL, bevel=2)
    else:
        frame_y = center[1] + n.y * 6
        for dz in (-1, 1):
            box(f"{name}_fz{dz}", (center[0], frame_y, center[2] + dz * (size[2] / 2 + 10)),
                (size[0] + 34, size[1] + 22, 20), M_FRAME, C_PANEL, bevel=2)
        for dx in (-1, 1):
            box(f"{name}_fx{dx}", (center[0] + dx * (size[0] / 2 + 10), frame_y, center[2]),
                (20, size[1] + 22, size[2]), M_FRAME, C_PANEL, bevel=2)

for side in (-1, 1):
    x_inner = side * (AX - WALL_T / 2)
    add_panel(f"em_{side}", (side, 0, 0),
              (x_inner - side * PANEL_T / 2, PANEL_CY, PANEL_CZ),
              (PANEL_T, PANEL_DY, PANEL_DZ))

# 正面（后墙，人正对的那面）
add_panel("em_back", (0, 1, 0),
          (BACK_CX, WALL_T / 2 + PANEL_T / 2, PANEL_CZ),
          (BACK_DX, PANEL_T, PANEL_DZ))

# ---------------- 固定对接口（左板顶部）----------------
PANEL_FACE_X = -AX + WALL_T / 2 + PANEL_T
DOCK_CX = PANEL_FACE_X + BALL_D / 2
DOCK_Y  = (PANEL_Y0 + PANEL_Y1) / 2
DOCK_Z  = PANEL_Z1 - 90

box("dock_bracket", (PANEL_FACE_X - 14, DOCK_Y, DOCK_Z + 72),
    (28, 60, 150), M_FRAME, C_PANEL, bevel=2)
box("dock_arm", (PANEL_FACE_X + 4, DOCK_Y, DOCK_Z + 72),
    (40, 22, 22), M_DOCK, C_PANEL, bevel=2)

cone("dock_funnel", (PANEL_FACE_X + 16, DOCK_Y, DOCK_Z),
     FUNNEL_R1, FUNNEL_R2, 32, M_DOCK, C_PANEL, direction=(1, 0, 0))

bpy.ops.mesh.primitive_torus_add(
    major_radius=(BALL_D / 2 + 2) * MM, minor_radius=5 * MM,
    major_segments=48, minor_segments=10,
    location=Vector((DOCK_CX, DOCK_Y, DOCK_Z)) * MM,
    rotation=(0, math.pi / 2, 0))
ring = bpy.context.object
ring.name = "dock_ring"
ring.data.materials.append(M_DOCK)
bpy.ops.object.shade_smooth()
_link(ring, C_PANEL)

# ---------------- 桌 ----------------
box("desk_top", (0, DESK_CY, DESK_Z - DESK_T / 2),
    (DESK_W, DESK_D, DESK_T), M_DESK, C_DESK, bevel=4)
for sx in (-1, 1):
    for ly in (-1, 1):
        box(f"desk_leg_{sx}_{ly}",
            (sx * (DESK_W / 2 - 70), DESK_CY + ly * (DESK_D / 2 - 70),
             (DESK_Z - DESK_T) / 2),
            (48, 48, DESK_Z - DESK_T), M_FRAME, C_DESK)

MON_Y = 200
box("monitor", (0, MON_Y, DESK_Z + 200), (620, 26, 360), M_DARK, C_DESK, bevel=3)
box("monitor_scr", (0, MON_Y + 15, DESK_Z + 200), (596, 2, 336), M_SCREEN, C_DESK)
box("monitor_neck", (0, MON_Y - 30, DESK_Z + 95), (52, 22, 190), M_DARK, C_DESK)
box("monitor_base", (0, MON_Y - 30, DESK_Z + 6), (280, 190, 12), M_DARK, C_DESK, bevel=3)
box("keyboard", (0, DESK_CY + 60, DESK_Z + 8), (430, 140, 16), M_DARK, C_DESK, bevel=3)

# ---------------- 人 ----------------
box("chair_seat", (0, 1000, 600), (440, 400, 60), M_CLOTH, C_PERSON, bevel=20)
box("torso", (0, 900, 850), (380, 230, 460), M_CLOTH, C_PERSON, bevel=30)
box("shoulders", (0, 890, 1075), (430, 210, 110), M_CLOTH, C_PERSON, bevel=35)
cyl("neck", (0, 890, 1150), 52, 80, M_SKIN, C_PERSON)
sphere("head", (0, 890, 1280), 105, M_SKIN, C_PERSON)
for sx in (-1, 1):
    box(f"upperarm_{sx}", (sx * 215, 890, 950), (95, 100, 230), M_CLOTH, C_PERSON, bevel=25)
    box(f"forearm_{sx}", (sx * 205, 790, 830), (90, 280, 85), M_CLOTH, C_PERSON, bevel=25)
    box(f"thigh_{sx}", (sx * 105, 760, 630), (170, 360, 150), M_CLOTH, C_PERSON, bevel=30)
    box(f"shin_{sx}", (sx * 105, 640, 320), (150, 160, 420), M_CLOTH, C_PERSON, bevel=25)

# ---------------- 禁区 ----------------
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=NECK_R * MM,
                                      location=Vector(NECK_POS) * MM)
zone = bpy.context.object
zone.name = "nofly_zone"
zone.data.materials.append(M_ZONE)
wf = zone.modifiers.new("wf", 'WIREFRAME')
wf.thickness = 2.5 * MM
wf.use_replace = True
_link(zone, C_ZONE)

# ---------------- 飞行中的球 + 吊点 ----------------
fly_c = Vector(FLY_POS)
hub_c = fly_c + Vector((0, 0, HUB_GAP))
core_ball("fly_ball", fly_c, C_BALL)

cyl("hub_plate", hub_c, 30, 8, M_DARK, C_BALL)
cyl("hub_cup", hub_c - Vector((0, 0, 11)), 18, 16, M_MAG, C_BALL)
cyl("hub_ring", hub_c - Vector((0, 0, 19)), 22, 4, M_DOCK, C_BALL)

# ---------------- 停在对接口上的球 ----------------
dock_c = Vector((DOCK_CX, DOCK_Y, DOCK_Z))
core_ball("dock_ball", dock_c, C_BALL, magnet_top=False)

# ---------------- 锚点 / 绞盘 / 线 ----------------
anchors = [
    Vector((-AX + 100, 100, ANCHOR_Z)),
    Vector((AX - 100, 100, ANCHOR_Z)),
    Vector((-AX + 100, BOOTH_D - 100, ANCHOR_Z)),
    Vector((AX - 100, BOOTH_D - 100, ANCHOR_Z)),
]

cable_len = []
for i, a in enumerate(anchors, 1):
    box(f"winch_mount_{i}", a, (72, 72, 26), M_FRAME, C_WINCH, bevel=2)
    box(f"motor_{i}", (a.x, a.y, a.z + 36), (42.3, 42.3, 46), M_DARK, C_WINCH, bevel=2)
    cyl(f"spool_{i}", (a.x, a.y, a.z - 6), 16, 22, M_METAL, C_WINCH,
        direction=(hub_c - a))

    d = a - hub_c
    d.z = 0
    d.normalize()
    lug = hub_c + d * 24
    cyl(f"hub_lug_{i}", lug, 5, 16, M_METAL, C_BALL, direction=d)
    cable(f"cable_{i}", a, lug, CABLE_D / 2, M_CABLES, C_CABLE)
    cable_len.append((a - lug).length)

# ============================================================
# 灯光 / 相机
# ============================================================
world = bpy.data.worlds.new("World")
bpy.context.scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.020, 0.024, 0.031, 1.0)
world.node_tree.nodes["Background"].inputs[1].default_value = 1.0

aim = Vector((0, 600, 1100))

def area_light(name, loc, energy, size, color):
    d = bpy.data.lights.new(name, 'AREA')
    d.energy = energy
    d.size = size * MM
    d.color = color
    ob = bpy.data.objects.new(name, d)
    ob.location = Vector(loc) * MM
    C_LIGHT.objects.link(ob)
    return ob

lights = [
    area_light("key",  (-1700, 2400, 2700), 110, 1000, (1.0, 0.96, 0.90)),
    area_light("fill", (2100, 1800, 1900), 38, 800, (0.72, 0.84, 1.0)),
    area_light("rim",  (500, -1400, 2400), 55, 800, (0.55, 0.88, 1.0)),
    area_light("top",  (0, 1300, 3200), 40, 1400, (0.85, 0.90, 1.0)),
]
for lt in lights:
    e = bpy.data.objects.new(f"aim_{lt.name}", None)
    e.location = aim * MM
    C_LIGHT.objects.link(e)
    c = lt.constraints.new('TRACK_TO')
    c.target = e
    c.track_axis = 'TRACK_NEGATIVE_Z'
    c.up_axis = 'UP_Y'

cam_data = bpy.data.cameras.new("Camera")
cam_data.lens = 40
cam = bpy.data.objects.new("Camera", cam_data)
cam.location = Vector((200, 3600, 2350)) * MM
C_LIGHT.objects.link(cam)
bpy.context.scene.camera = cam

tgt = bpy.data.objects.new("CamTarget", None)
tgt.location = Vector((0, 560, 980)) * MM
C_LIGHT.objects.link(tgt)
c = cam.constraints.new('TRACK_TO')
c.target = tgt
c.track_axis = 'TRACK_NEGATIVE_Z'
c.up_axis = 'UP_Y'

sc = bpy.context.scene
sc.use_nodes = True
tree = sc.node_tree
for n in list(tree.nodes):
    tree.nodes.remove(n)
rl = tree.nodes.new("CompositorNodeRLayers")
gl = tree.nodes.new("CompositorNodeGlare")
gl.glare_type = 'FOG_GLOW'
gl.quality = 'HIGH'
gl.threshold = 0.9
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

nn_side = int(PANEL_DY / COIL_PITCH) * int(PANEL_DZ / COIL_PITCH)
nn_back = int(BACK_DX / COIL_PITCH) * int(PANEL_DZ / COIL_PITCH)

os.makedirs(out_dir, exist_ok=True)
blend_path = os.path.join(out_dir, "coreball_booth.blend")
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(blend_path))

with open(os.path.join(out_dir, "bom_booth.md"), "w", encoding="utf-8") as f:
    f.write("# CoreBall 工位围合版 BOM\n\n| 件 | 规格 | 用途 |\n|---|---|---|\n")
    f.write("| 后围板 | %d × %d | 板 + 框 |\n" % (BOOTH_W + 2 * WALL_T, WALL_H))
    f.write("| 侧围板 | %d × %d ×2 | 板 + 框 |\n" % (BOOTH_D, WALL_H))
    f.write("| 电磁板 | 侧 %d×%d ×2，正 %d×%d ×1 | 板体 %d 厚 |\n"
            % (PANEL_DY, PANEL_DZ, BACK_DX, PANEL_DZ, PANEL_T))
    f.write("| 线圈 | 间距 %d mm，侧板各约 %d，正板约 %d，合计约 %d | 埋在板面下 |\n"
            % (COIL_PITCH, nn_side, nn_back, nn_side * 2 + nn_back))
    f.write("| 固定对接口 | 1 套（漏斗 φ%d→φ%d） | 绳→板交接 |\n"
            % (FUNNEL_R1 * 2, FUNNEL_R2 * 2))
    f.write("| NEMA17 | 4 台 | 绞盘 |\n")
    f.write("| 线 | 4 根 %s mm | φ0.6 大力马 |\n"
            % " / ".join("%.0f" % L for L in cable_len))
    f.write("| 球壳 | φ%d | 3D 打印 |\n" % BALL_D)
    f.write("\n## 关键尺寸\n\n")
    f.write("- 工位：%d 宽 × %d 深 × %d 高\n" % (BOOTH_W, BOOTH_D, WALL_H))
    f.write("- 侧板面 x = ±%.0f，正板面 y = %.0f\n"
            % (abs(PANEL_FACE_X), WALL_T / 2 + PANEL_T))
    f.write("- 对接口：y=%.0f z=%.0f，球心 x=%.0f\n" % (DOCK_Y, DOCK_Z, DOCK_CX))
    f.write("- 飞行位：%s\n" % (FLY_POS,))
    f.write("- 禁区：%s，半径 %d\n" % (NECK_POS, NECK_R))

print("=" * 56)
print("线圈：侧各 %d，正 %d，合计 %d，间距 %d mm" % (nn_side, nn_back, nn_side * 2 + nn_back, COIL_PITCH))
print("对接口: y=%.0f z=%.0f 球心x=%.0f" % (DOCK_Y, DOCK_Z, DOCK_CX))
print("线长:", ", ".join("%.0f" % L for L in cable_len), "mm")
print("blend:", os.path.abspath(blend_path))
print("=" * 56)

if do_render:
    sc.render.filepath = os.path.abspath(os.path.join(out_dir, "view_overview.png"))
    sc.render.image_settings.file_format = 'PNG'
    bpy.ops.render.render(write_still=True)
    print("render:", sc.render.filepath)

    cam2d = bpy.data.cameras.new("CamDock")
    cam2d.lens = 50
    cam2d.dof.use_dof = True
    cam2d.dof.focus_distance = 1.1
    cam2d.dof.aperture_fstop = 2.4
    cam2 = bpy.data.objects.new("CamDock", cam2d)
    cam2.location = Vector((-280, 1560, 1780)) * MM
    C_LIGHT.objects.link(cam2)
    t2 = bpy.data.objects.new("CamDockTarget", None)
    t2.location = Vector((DOCK_CX + 20, DOCK_Y, DOCK_Z - 10)) * MM
    C_LIGHT.objects.link(t2)
    c2 = cam2.constraints.new('TRACK_TO')
    c2.target = t2
    c2.track_axis = 'TRACK_NEGATIVE_Z'
    c2.up_axis = 'UP_Y'
    sc.camera = cam2
    sc.render.resolution_x = 1600
    sc.render.resolution_y = 1600
    sc.render.filepath = os.path.abspath(os.path.join(out_dir, "view_dock.png"))
    bpy.ops.render.render(write_still=True)
    print("dock:", sc.render.filepath)
