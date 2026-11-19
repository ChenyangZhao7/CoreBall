"""
CoreBall - 核心球初步设计  φ80

布局：
  顶部   φ30 井（与底部同一套：4 触点 + 3 键槽 + 3 钢片；键在载体上）
  上壳   3 个麦克风孔（纬度 +32°，间距 59mm）
         点阵窗口 26 × 15.6（10 × 6 像素），中心在赤道
  分割    z = -12（不在赤道，因为脸在那儿）
  下壳   喇叭网（纬度 -22°）
  底部   φ30 井（与顶部同一套：6 触点 + 3 键槽 + 3 钢片；键在载体上）

用法：
  blender --background --python build_ball.py -- --out blender/ball --render
"""

import bpy
import bmesh
import sys
import os
import math
from math import sin, cos, pi, radians
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools"))
import interface_spec as I  # noqa: E402

# ============================================================
# 参数（mm）
# ============================================================
R          = 40.0      # 球半径
WALL       = 2.0       # 壳厚
SPLIT_Z    = -12.0     # 上下壳分割面

# 窗口
WIN_W, WIN_H = 30.0, 18.0
WIN_CORNER = 5.0
WIN_Z      = 0.0       # 窗口中心高度（在赤道）
PIX_COLS, PIX_ROWS = 12, 7
PIX_PITCH  = 2.4
PIX_SIZE   = 2.3
DISH_R     = 19.0      # 面窗凹槽半径
DISH_DEPTH = 2.6

# 麦克风
MIC_LAT    = 32.0
MIC_LONS   = (0.0, 120.0, 240.0)
MIC_R      = 1.6

# 喇叭网
SPK_Z      = -22.0
SPK_W, SPK_H = 22.0, 12.0
SPK_HOLES_X, SPK_HOLES_Y = 9, 4

MM = 0.001

# ============================================================
# 工具
# ============================================================
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.length_unit = 'MILLIMETERS'
    sc.render.engine = 'BLENDER_EEVEE_NEXT'
    sc.render.resolution_x = 1800
    sc.render.resolution_y = 1800


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


def mesh_obj(name, verts, faces, mat, coll, smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([Vector(v) * MM for v in verts], [], faces)
    me.validate()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    if mat:
        ob.data.materials.append(mat)
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    # 统一法线
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    return ob


def box(name, center, size, mat, coll, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=Vector(center) * MM)
    ob = bpy.context.object
    ob.name = name
    ob.scale = Vector(size) * MM
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat:
        ob.data.materials.append(mat)
    if bevel > 0:
        m = ob.modifiers.new("bev", 'BEVEL')
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


def torus(name, center, major, minor, mat, coll, axis='Z', seg=64, mseg=12, arc=None):
    """arc=(起始角度, 结束角度) 时生成一段圆弧环"""
    verts, faces = [], []
    if arc is None:
        a0, a1, closed = 0.0, 2 * pi, True
        n = seg
    else:
        a0, a1, closed = radians(arc[0]), radians(arc[1]), False
        n = seg
    steps = n if closed else n + 1
    idx = []
    for i in range(steps):
        t = a0 + (a1 - a0) * (i / n)
        ring = []
        for j in range(mseg):
            p = 2 * pi * j / mseg
            # 圆环截面
            rr = major + minor * cos(p)
            zz = minor * sin(p)
            ring.append(len(verts))
            verts.append((rr * cos(t), rr * sin(t), zz))
        idx.append(ring)
    for i in range(steps if closed else steps - 1):
        i2 = (i + 1) % steps
        for j in range(mseg):
            j2 = (j + 1) % mseg
            faces.append((idx[i][j], idx[i2][j], idx[i2][j2], idx[i][j2]))
    ob = mesh_obj(name, verts, faces, mat, coll)
    ob.location = Vector(center) * MM
    if axis == 'Y':
        ob.rotation_euler = (pi / 2, 0, 0)
    elif axis == 'X':
        ob.rotation_euler = (0, pi / 2, 0)
    return ob


def spherical_shell(name, r_out, r_in, z_lo, z_hi, mat, coll, seg=80, rings=40):
    """双面球壳（有厚度），z_lo..z_hi 之间"""
    t0 = math.acos(max(-1.0, min(1.0, z_hi / r_out)))
    t1 = math.acos(max(-1.0, min(1.0, z_lo / r_out)))
    verts, faces = [], []
    outer, inner = [], []
    for i in range(rings + 1):
        t = t0 + (t1 - t0) * i / rings
        ro, ri = [], []
        for j in range(seg):
            p = 2 * pi * j / seg
            ro.append(len(verts))
            verts.append((r_out * sin(t) * cos(p), r_out * sin(t) * sin(p), r_out * cos(t)))
        for j in range(seg):
            p = 2 * pi * j / seg
            ri.append(len(verts))
            verts.append((r_in * sin(t) * cos(p), r_in * sin(t) * sin(p), r_in * cos(t)))
        outer.append(ro)
        inner.append(ri)
    for i in range(rings):
        for j in range(seg):
            j2 = (j + 1) % seg
            faces.append((outer[i][j], outer[i][j2], outer[i + 1][j2], outer[i + 1][j]))
            faces.append((inner[i][j], inner[i + 1][j], inner[i + 1][j2], inner[i][j2]))
    for j in range(seg):
        j2 = (j + 1) % seg
        faces.append((outer[0][j], inner[0][j], inner[0][j2], outer[0][j2]))
        faces.append((outer[rings][j], outer[rings][j2], inner[rings][j2], inner[rings][j]))
    return mesh_obj(name, verts, faces, mat, coll)


def boolean_diff(target, cutter):
    mod = target.modifiers.new("cut", 'BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.solver = 'EXACT'
    mod.object = cutter
    bpy.context.view_layer.objects.active = target
    target.select_set(True)
    try:
        bpy.ops.object.modifier_apply(modifier=mod.name)
    except Exception as e:
        target.modifiers.remove(mod)
        print("boolean failed:", target.name, e)
    bpy.data.objects.remove(cutter, do_unlink=True)


# ============================================================
# 建
# ============================================================
reset()

C_SHELL = collection("00_球壳")
C_FACE  = collection("01_面窗")
C_PORT  = collection("02_接口与网孔")
C_INNER = collection("03_内部")
C_LIGHT = collection("04_灯光相机")

M_SHELL = material("Shell", (0.93, 0.935, 0.94), 0.02, 0.36)
M_SHELL_IN = material("Shell_Inner", (0.55, 0.56, 0.58), 0.1, 0.55)
M_BEZEL = material("Bezel", (0.26, 0.27, 0.29), 0.85, 0.32)
M_GLASS = material("Window_Glass", (0.015, 0.02, 0.03), 0.15, 0.08)
M_PIX   = material("Pixel", (0.10, 0.80, 1.0), 0.0, 0.30,
                   emission=(0.10, 0.80, 1.0), strength=5.0)
M_PIXOFF= material("Pixel_Off", (0.035, 0.04, 0.05), 0.0, 0.45)
M_GRILL = material("Grille", (0.05, 0.055, 0.06), 0.3, 0.5)
M_DARK  = material("Dark", (0.06, 0.065, 0.075), 0.35, 0.48)
M_METALD= material("Metal_Dark", (0.20, 0.21, 0.23), 0.9, 0.35)
M_ALLOY = material("Alloy", (0.72, 0.74, 0.77), 0.9, 0.30)
M_METAL = material("Metal", (0.62, 0.64, 0.67), 0.95, 0.22)
M_MAG   = material("Magnet", (0.86, 0.72, 0.42), 0.95, 0.20)
M_PCB   = material("PCB", (0.06, 0.22, 0.16), 0.2, 0.55)
M_BATT  = material("Battery", (0.22, 0.24, 0.28), 0.5, 0.45)
M_SPK   = material("Speaker", (0.10, 0.10, 0.11), 0.3, 0.55)
M_FLOOR = material("Floor", (0.05, 0.055, 0.06), 0.0, 0.85)

# ---------------- 球壳 ----------------
# 上壳：SPLIT_Z .. R
upper = spherical_shell("shell_upper", R, R - WALL, SPLIT_Z, R - 0.2,
                        M_SHELL, C_SHELL)
# 下壳：-(R) .. SPLIT_Z
lower = spherical_shell("shell_lower", R, R - WALL, -(R - 0.2), SPLIT_Z,
                        M_SHELL, C_SHELL)

# ---------------- 麦克风孔 ----------------
for lon in MIC_LONS:
    la, lo = radians(MIC_LAT), radians(lon)
    nx = cos(la) * sin(lo)
    ny = cos(la) * cos(lo)
    nz = sin(la)
    p = Vector((R * nx, R * ny, R * nz))
    c = cyl(f"cut_mic_{lon}", p + Vector((nx, ny, nz)) * 12, MIC_R, 24,
            None, C_SHELL, direction=(nx, ny, nz), verts=20)
    boolean_diff(upper, c)

# ---------------- 面窗（球面贴合）----------------
def in_round_rect(u, v, w, h, c):
    if abs(u) > w / 2 or abs(v) > h / 2:
        return False
    dx = max(abs(u) - (w / 2 - c), 0.0)
    dy = max(abs(v) - (h / 2 - c), 0.0)
    return dx * dx + dy * dy <= c * c


def surface_patch(name, r, w, h, corner, mat, coll, azimuth=0.0, z_center=0.0,
                  nu=40, nv=24, offset=0.0, mask=None):
    """球面圆角矩形补片：尺寸按毫米；azimuth 0 = 正面(+Y)，180 = 背面(-Y)"""
    th0 = math.acos(max(-1.0, min(1.0, z_center / r)))
    s0 = max(1e-6, math.sin(th0))
    az = math.radians(azimuth)
    verts, faces, grid = [], [], []
    for i in range(nv + 1):
        v = -h / 2 + h * i / nv
        row = []
        for j in range(nu + 1):
            u = -w / 2 + w * j / nu
            th = th0 - v / r
            ph = az + u / (r * s0)
            rr = r + offset
            row.append(len(verts))
            verts.append((rr * sin(th) * sin(ph),
                          rr * sin(th) * cos(ph),
                          rr * cos(th)))
        grid.append(row)
    for i in range(nv):
        for j in range(nu):
            uc = -w / 2 + w * (j + 0.5) / nu
            vc = -h / 2 + h * (i + 0.5) / nv
            if not in_round_rect(uc, vc, w, h, corner):
                continue
            if mask is not None and not mask(uc, vc):
                continue
            faces.append((grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j]))
    return mesh_obj(name, verts, faces, mat, coll)


FRAME_W = 1.4

# 玻璃：圆角矩形，贴球面
surface_patch("window_glass", R, WIN_W, WIN_H, WIN_CORNER, M_GLASS, C_FACE,
              azimuth=0.0, z_center=WIN_Z, nu=150, nv=92, offset=0.06)

# 边框：外圈圆角矩形减去内圈，得到一圈等的框
surface_patch("window_bezel", R, WIN_W + 2 * FRAME_W, WIN_H + 2 * FRAME_W,
              WIN_CORNER + FRAME_W, M_BEZEL, C_FACE,
              azimuth=0.0, z_center=WIN_Z, nu=170, nv=106, offset=0.17,
              mask=lambda u, v: not in_round_rect(u, v, WIN_W, WIN_H, WIN_CORNER))

# 像素点阵
PATTERNS = {
    "dot": [
        "............",
        ".####..####.",
        ".####..####.",
        ".####..####.",
        ".####..####.",
        "............",
        "............",
    ],
    "narrow": [
        "............",
        "............",
        ".####..####.",
        "............",
        "............",
        "............",
        "............",
    ],
    "heart": [
        "............",
        "..##....##..",
        ".####..####.",
        "..##....##..",
        "............",
        "............",
        "............",
    ],
}

pix_objs = {}
for pname, rows in PATTERNS.items():
    grp = []
    for r_i, row in enumerate(rows):
        for c_i, ch in enumerate(row):
            if ch != "#":
                continue
            x = (c_i - (PIX_COLS - 1) / 2) * PIX_PITCH
            z = WIN_Z + ((PIX_ROWS - 1) / 2 - r_i) * PIX_PITCH
            if not in_round_rect(x, z - WIN_Z, WIN_W - 3.5, WIN_H - 3.5, WIN_CORNER - 1.2):
                continue
            ys = math.sqrt(max(1.0, (R + 0.05) ** 2 - x * x - z * z)) + 0.25
            ob = box(f"px_{pname}_{r_i}_{c_i}", (x, ys, z),
                     (PIX_SIZE, 0.5, PIX_SIZE), M_PIX, C_FACE)
            grp.append(ob)
    pix_objs[pname] = grp

# 只显示 dot
for pname, grp in pix_objs.items():
    for ob in grp:
        ob.hide_render = (pname != "dot")
        ob.hide_viewport = (pname != "dot")

# ---------------- 喇叭网 ----------------
for i in range(SPK_HOLES_X):
    for j in range(SPK_HOLES_Y):
        x = (i - (SPK_HOLES_X - 1) / 2) * (SPK_W / SPK_HOLES_X)
        z = SPK_Z + ((SPK_HOLES_Y - 1) / 2 - j) * (SPK_H / SPK_HOLES_Y)
        # 落在球面上
        rr = math.sqrt(max(1.0, R * R - x * x - z * z))
        cyl(f"spk_{i}_{j}", (x, rr - 0.7, z), 0.9, 1.4, M_GRILL, C_PORT,
            direction=(x, rr, z), verts=12)

# ---------------- 接口（顶 / 底，球永远是母座）----------------
# 两井同一套：井杯内径 φ30 × 5 深；键在载体上，球上只有键槽与钢片
IF_R = I.WELL_R
IF_DEPTH = I.WELL_DEPTH
CUP_OUT = I.WELL_R + I.CUP_WALL      # 井杯外径 31.6
SHELL_HOLE = CUP_OUT + 0.05          # 球壳开孔略大，避免与杯壁共面


def cut_well(sign):
    shell = upper if sign > 0 else lower
    cz = sign * (R - IF_DEPTH) + sign * 20
    c = cyl(f"cut_well_{sign}", (0, 0, cz), SHELL_HOLE, 40, None, C_SHELL,
            direction=(0, 0, 1), verts=64)
    boolean_diff(shell, c)


cut_well(1)
cut_well(-1)


def interface(tag, sign, count):
    zf = sign * (R - IF_DEPTH)
    # 6061 整体井杯：井底 + 井壁一件，压入球壳；键扭矩、磁吸力和 3A 热量都走杯体
    # 井底：2.4 厚，给 2.0 深的键槽留材料
    floor = cyl(f"if_cup_floor_{tag}", (0, 0, zf - sign * 1.2), CUP_OUT, 2.4,
                M_METALD, C_PORT, direction=(0, 0, 1), verts=64)
    # 井壁：内径 φ30、壁厚 0.8，从井底到井口
    wall = cyl(f"if_cup_wall_{tag}", (0, 0, zf + sign * 1.05), CUP_OUT, 2.1,
               M_METALD, C_PORT, direction=(0, 0, 1), verts=64)
    hole = cyl(f"cut_cup_{tag}", (0, 0, zf + sign * 1.05), IF_R, 2.2,
               None, C_PORT, direction=(0, 0, 1), verts=64)
    boolean_diff(wall, hole)
    # 杯壁根部圆角，降低法兰/杯壁交界处的应力集中
    torus(f"if_cup_fillet_{tag}", (0, 0, zf), CUP_OUT - 0.35, 0.35,
          M_ALLOY, C_PORT, axis='Z', seg=64, mseg=8)
    # 触点焊盘：微凸 0.05，落位时产生一点擦拭
    for k in range(count):
        x, y = I.polar(I.PAD_PITCH_R, I.PAD_ANGLES[k])
        cyl(f"if_pad_{tag}_{k}", (x, y, zf - sign * (0.45 - I.PAD_DOME)),
            I.PAD_D / 2, 0.9, M_MAG, C_PORT, direction=(0, 0, 1), verts=16)
    # 键槽：切块切井底片（切块会被 boolean_diff 删掉），槽底留深色标记
    for k, ang in enumerate(I.KEY_ANGLES):
        x, y = I.polar(I.KEY_R, ang)
        # 切块高出井底 0.6：与井底片顶面共面时 boolean 会留下盖面，槽就不通了
        depth = I.SLOT_DEPTH + 0.6
        cutter = box(f"cut_slot_{tag}_{k}",
                     (x, y, zf - sign * (I.SLOT_DEPTH - depth / 2)),
                     (I.SLOT_W, I.SLOT_W, depth), None, C_PORT)
        boolean_diff(floor, cutter)
        box(f"if_slot_{tag}_{k}", (x, y, zf - sign * (I.SLOT_DEPTH - 0.1)),
            (3.0, 3.0, 0.2), M_DARK, C_PORT)
    # 钢片：430 不锈钢，与井底齐平
    for k, ang in enumerate(I.MAGNET_ANGLES):
        x, y = I.polar(I.MAGNET_R, ang)
        cyl(f"if_steel_{tag}_{k}", (x, y, zf - sign * (I.STEEL_H / 2 - 0.02)),
            I.STEEL_D / 2, I.STEEL_H, M_METAL, C_PORT,
            direction=(0, 0, 1), verts=24)


# 井口倒角 0.8×45° 写在标准里；井杯壁本身就是井口，不再额外加环。
# 杯壁内径 = φ30 > 插头 φ29.6，不会挡插头。
interface("top", 1, 4)
interface("bot", -1, 6)

# ---------------- 内部骨架：6061 分型环 + 六柱 ----------------
# 环在分割面 z=-12；上下各 3 根柱把顶杯/底杯的拉力和插拔力传到环。
# 柱角度不是 120° 均布，装反 120° 对不上。
FRAME_Z = SPLIT_Z


def drill(name, target, center, radius, depth, verts=16):
    c = cyl(name, center, radius, depth, None, C_INNER, verts=verts)
    boolean_diff(target, c)


ring = cyl("frame_ring", (0, 0, FRAME_Z), 34.5, 6, M_ALLOY, C_INNER, verts=64)
ring_hole = cyl("cut_frame_ring", (0, 0, FRAME_Z), 27.0, 6.2, None, C_INNER,
                verts=64)
boolean_diff(ring, ring_hole)


def strut(name, r1, z1, a1, r2, z2, a2, radius=2.5):
    p1 = Vector((r1 * cos(radians(a1)), r1 * sin(radians(a1)), z1))
    p2 = Vector((r2 * cos(radians(a2)), r2 * sin(radians(a2)), z2))
    d = p2 - p1
    cyl(name, (p1 + p2) / 2, radius, d.length, M_ALLOY, C_INNER,
        direction=d, verts=16)
    # 柱两端的抱箍（杯侧、环侧）
    for k, t in enumerate((0.10, 0.90)):
        c = p1 + d * t
        cyl(f"{name}_clamp{k}", c, 3.8, 1.2, M_ALLOY, C_INNER,
            direction=d, verts=16)


for k, ang in enumerate((45.0, 155.0, 265.0)):
    strut(f"frame_col_top_{k}", 32, FRAME_Z + 3, ang, 14, 32.6, ang)
for k, ang in enumerate((30.0, 150.0, 270.0)):
    strut(f"frame_col_bot_{k}", 32, FRAME_Z - 3, ang, 14, -32.6, ang)

# 环上 6 个壳固定凸台（上下各 3），真实攻丝孔（M2.5 底孔 φ2.1）
for side, angles in ((1, (100, 210, 320)), (-1, (90, 210, 330))):
    for k, ang in enumerate(angles):
        x, y = I.polar(31.0, ang)
        zc = FRAME_Z + side * 3.0
        boss = cyl(f"frame_boss_{side}_{k}", (x, y, zc + side * 1.0), 2.6, 2.0,
                   M_ALLOY, C_INNER, verts=16)
        drill(f"drill_boss_{side}_{k}", boss, (x, y, zc + side * 1.0), 1.05, 3.2)
        drill(f"drill_ring_{side}_{k}", ring, (x, y, zc - side * 2.0), 1.05, 4.0)

# 主板 4 个支柱（z=-9 → 6）
for k, (sx, sy) in enumerate(((-15, -15), (15, -15), (-15, 15), (15, 15))):
    cyl(f"pcb_standoff_{k}", (sx, sy, -1.5), 2.2, 15.0, M_ALLOY, C_INNER,
        verts=16)

# 电池托架：底托 + 两侧轨 + 环下横梁 + 压条
box("battery_tray", (0, -4, -32.3), (36, 24, 1.6), M_ALLOY, C_INNER, bevel=0.5)
for k, sx in enumerate((-17.5, 17.5)):
    box(f"tray_rail_{k}", (sx, -4, -24.0), (1.4, 24, 16.0),
        M_ALLOY, C_INNER, bevel=0.3)
box("tray_crossbar", (0, -4, -15.8), (40, 28, 1.6), M_ALLOY, C_INNER,
    bevel=0.3)
box("battery_strap", (0, -4, -18.9), (34, 3, 1.0), M_ALLOY, C_INNER,
    bevel=0.3)

# ---------------- 走线（示意）：顶杯 4 线、底杯 6 线、环到主板 ----------------
def cable(name, pts, radius=1.1):
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = radius * MM
    cu.bevel_resolution = 2
    sp = cu.splines.new('POLY')
    sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        sp.points[i].co = (p[0] * MM, p[1] * MM, p[2] * MM, 1.0)
    ob = bpy.data.objects.new(name, cu)
    ob.data.materials.append(M_DARK)
    C_INNER.objects.link(ob)
    return ob


a = radians(45.0)
cable("cable_top", [(14 * cos(a), 14 * sin(a), 32.0),
                    (19 * cos(a), 19 * sin(a), 19.0),
                    (19 * cos(a), 19 * sin(a), 7.0)])
box("conn_top", (19 * cos(a), 19 * sin(a), 6.6), (5, 4, 1.6),
    M_METALD, C_INNER, bevel=0.3)

a = radians(270.0)
cable("cable_bot", [(14 * cos(a), 14 * sin(a), -32.0),
                    (22 * cos(a), 22 * sin(a), -20.0),
                    (27 * cos(a), 27 * sin(a), -13.0)])
box("conn_ring", (27 * cos(a), 27 * sin(a), -12.0), (6, 5, 2.0),
    M_METALD, C_INNER, bevel=0.3)
cable("cable_ring_pcb", [(27 * cos(a), 27 * sin(a), -10.5),
                         (20 * cos(a), 20 * sin(a), -2.0),
                         (14 * cos(a), 14 * sin(a), 6.0)])

# ---------------- 球顶红外接收环 ----------------
for k in range(8):
    a = radians(k * 45.0)
    lat = radians(50.0)
    nx, ny, nz = cos(lat) * sin(a), cos(lat) * cos(a), sin(lat)
    p = Vector((R * nx, R * ny, R * nz))
    n = p.normalized()
    cyl(f"ir_port_{k}", p - n * 0.7, 1.5, 1.4, M_DARK, C_PORT,
        direction=n, verts=16)

# ---------------- 背面服务面 ----------------
# 背面 = -Y。所有开孔集中在这里，正面保持干净。
M_LEDST = material("StatusLED", (1.0, 0.62, 0.18), 0.0, 0.3,
                   emission=(1.0, 0.62, 0.18), strength=2.4)

def back_surf(u, v, z_center):
    """背面上局部坐标 (u,v) 对应的球面点与法线"""
    th0 = math.acos(max(-1.0, min(1.0, z_center / R)))
    s0 = max(1e-6, math.sin(th0))
    th = th0 - v / R
    ph = pi + u / (R * s0)
    p = Vector((R * sin(th) * sin(ph), R * sin(th) * cos(ph), R * cos(th)))
    return p, p.normalized()

def back_disc(name, radius, z, mat, coll, depth=1.2, protrude=0.0, u=0.0,
              verts=36):
    p, n = back_surf(u, 0.0, z)
    c = p + n * (protrude - depth / 2)
    return cyl(name, c, radius, depth, mat, coll, direction=n, verts=verts)

# 散热阵列：孔径从中心向边缘递减
VENT_CZ = 22.5
for i in range(5):
    for j in range(9):
        u = (j - 4) * 2.7 + (1.35 if i % 2 else 0.0)
        v = (2 - i) * 2.7
        d = math.hypot(u, v)
        if d > 11.0:
            continue
        rad = 1.35 - d * 0.042
        p, n = back_surf(u, v, VENT_CZ)
        cyl(f"vent_{i}_{j}", p - n * 0.6, rad, 1.2, M_GRILL, C_PORT,
            direction=n, verts=14)

# 一排服务件：复位针孔 / USB-C / 状态灯
SERV_Z = 13.0
surface_patch("usb_slot", R, 9.0, 3.4, 1.7, M_GRILL, C_PORT,
              azimuth=180.0, z_center=SERV_Z, offset=0.16,
              nu=48, nv=18)
surface_patch("usb_frame", R, 10.8, 5.2, 2.6, M_METALD, C_PORT,
              azimuth=180.0, z_center=SERV_Z, offset=0.30, nu=56, nv=22,
              mask=lambda u, v: not in_round_rect(u, v, 9.0, 3.4, 1.7))

back_disc("reset_pin", 1.1, SERV_Z, M_GRILL, C_PORT, depth=1.0, protrude=-0.15,
          u=-13.0, verts=16)
back_disc("status_ring", 2.9, SERV_Z, M_BEZEL, C_PORT, depth=1.0, protrude=0.05,
          u=13.0)
back_disc("status_led", 1.7, SERV_Z, M_LEDST, C_PORT, depth=1.0, protrude=0.16,
          u=13.0)

# 电源键：避开分割线
back_disc("power_ring", 4.6, -7.2, M_BEZEL, C_PORT, depth=1.4, protrude=0.05)
back_disc("power_btn", 3.8, -7.2, M_DARK, C_PORT, depth=1.5, protrude=0.38)

# ---------------- 内部 ----------------
# 电池（竖向放在中下；-27 会与加厚后的底井片重叠 0.4 mm）
box("battery", (0, -4, -25.5), (34, 22, 12), M_BATT, C_INNER, bevel=2)
# 主板（水平；z=6 给上柱让出通道）
box("pcb_main", (0, 0, 6), (44, 44, 1.6), M_PCB, C_INNER, bevel=0.5)
# 副板（竖直，靠后）
box("pcb_power", (0, -18, -6), (36, 1.6, 26), M_PCB, C_INNER, bevel=0.5)
# 喇叭
cyl("speaker", (0, 22, SPK_Z), 13, 6, M_SPK, C_INNER, direction=(0, 1, 0), verts=40)
# 麦克风胶囊
for lon in MIC_LONS:
    la, lo = radians(MIC_LAT), radians(lon)
    nx, ny, nz = cos(la) * sin(lo), cos(la) * cos(lo), sin(la)
    p = Vector((nx, ny, nz)) * (R - 5.5)
    cyl(f"mic_{int(lon)}", p, 2.6, 4.0, M_METAL, C_INNER,
        direction=(nx, ny, nz), verts=20)

# ---------------- 地面 ----------------
box("floor", (0, 0, -R - 14), (600, 600, 2), M_FLOOR, C_LIGHT)

# ============================================================
# 灯光 / 相机
# ============================================================
world = bpy.data.worlds.new("World")
bpy.context.scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.018, 0.021, 0.028, 1.0)
world.node_tree.nodes["Background"].inputs[1].default_value = 1.0

aim = Vector((0, 0, 0))

def area(name, loc, energy, size, color):
    d = bpy.data.lights.new(name, 'AREA')
    d.energy = energy
    d.size = size * MM
    d.color = color
    ob = bpy.data.objects.new(name, d)
    ob.location = Vector(loc) * MM
    C_LIGHT.objects.link(ob)
    e = bpy.data.objects.new(f"aim_{name}", None)
    e.location = aim * MM
    C_LIGHT.objects.link(e)
    c = ob.constraints.new('TRACK_TO')
    c.target = e
    c.track_axis = 'TRACK_NEGATIVE_Z'
    c.up_axis = 'UP_Y'
    return ob

area("key",  (-180, 200, 160), 1.6, 120, (1.0, 0.96, 0.90))
area("fill", (230, 120, 60), 0.55, 100, (0.70, 0.84, 1.0))
area("rim",  (60, -220, 120), 0.9, 100, (0.55, 0.88, 1.0))

cam_data = bpy.data.cameras.new("Cam")
cam_data.lens = 100
cam = bpy.data.objects.new("Cam", cam_data)
cam.location = Vector((150, 250, 95)) * MM
C_LIGHT.objects.link(cam)
bpy.context.scene.camera = cam
tgt = bpy.data.objects.new("CamTgt", None)
tgt.location = Vector((0, 0, 2)) * MM
C_LIGHT.objects.link(tgt)
c = cam.constraints.new('TRACK_TO')
c.target = tgt
c.track_axis = 'TRACK_NEGATIVE_Z'
c.up_axis = 'UP_Y'

# 辉光
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
out_dir = os.path.join(HERE, "out", "ball")
do_render = False
if "--" in argv:
    rest = argv[argv.index("--") + 1:]
    if "--out" in rest:
        out_dir = rest[rest.index("--out") + 1]
    do_render = "--render" in rest

os.makedirs(out_dir, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(os.path.join(out_dir, "coreball_ball.blend")))

if do_render:
    def shoot(path, cam_loc, tgt_loc, lens, res=1800):
        cam.location = Vector(cam_loc) * MM
        tgt.location = Vector(tgt_loc) * MM
        cam_data.lens = lens
        sc.render.resolution_x = res
        sc.render.resolution_y = res
        sc.render.filepath = os.path.abspath(os.path.join(out_dir, path))
        sc.render.image_settings.file_format = 'PNG'
        bpy.ops.render.render(write_still=True)
        print("shot:", path)

    # 1) 三个视角：正面 / 四分之三 / 背面
    shoot("view_front.png", (0, 265, 3), (0, 0, 3), 90)
    shoot("ball_hero.png", (150, 250, 95), (0, 0, 2), 85)
    shoot("view_rear.png", (-185, -235, 45), (0, 0, -8), 85)
    shoot("view_back_detail.png", (-70, -225, 62), (0, 0, 5), 100)
    shoot("view_top.png", (30, -90, 300), (0, 0, 8), 95)

    # 2) 正面三种表情
    for pname in ("dot", "narrow", "heart"):
        for k, grp in pix_objs.items():
            for ob in grp:
                ob.hide_render = (k != pname)
        shoot(f"face_{pname}.png", (0, 260, 3), (0, 40, 1), 100, res=1200)

    # 恢复 dot
    for k, grp in pix_objs.items():
        for ob in grp:
            ob.hide_render = (k != "dot")

    # 3) 爆炸：上壳 + 脸 整体抬起
    top_group = [o for o in bpy.data.objects
                 if o.name.startswith(("bez_", "px_", "window_"))]
    top_group.append(upper)
    for ob in top_group:
        ob.location.z += 46 * MM
    bpy.data.objects["pcb_main"].location.z = (12 + 18) * MM
    shoot("ball_explode.png", (200, 290, 200), (0, 0, 14), 80)

print("done:", os.path.abspath(out_dir))
