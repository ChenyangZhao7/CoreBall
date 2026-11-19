"""接口 v1.0：球的两个井。

用法：
  blender -b blender/out/ball/coreball_ball.blend --python-exit-code 1 --python blender/tests/test_interface_ball.py
"""
import math
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "tools"))
import interface_spec as I  # noqa: E402


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def at(name):
    ob = bpy.data.objects.get(name)
    if ob is None:
        fail("场景里没有 %s" % name)
    return ob


def mm(v):
    # 场景单位是米，接口标准是毫米
    return v * 1000.0


def polar(ob):
    p = ob.matrix_world.translation
    return math.hypot(p.x, p.y) * 1000.0, math.degrees(math.atan2(p.y, p.x)) % 360.0


def near(a, b, tol=0.5):
    return abs((a - b + 180.0) % 360.0 - 180.0) <= tol


FLOOR = I.BALL_R - I.WELL_DEPTH

for tag, sign, count in (("top", 1, 4), ("bot", -1, 6)):
    for k in range(count):
        name = "if_pad_%s_%d" % (tag, k)
        r, a = polar(at(name))
        if abs(r - I.PAD_PITCH_R) > 0.01:
            fail("%s 半径 %.2f" % (name, r))
        if not near(a, I.PAD_ANGLES[k]):
            fail("%s 角度 %.1f" % (name, a))
        z = at(name).matrix_world.translation.z
        if abs(mm(z) - sign * (FLOOR - 0.45)) > 0.6:
            fail("%s 没齐平井底" % name)
    if "if_pad_%s_%d" % (tag, count) in bpy.data.objects:
        fail("%s 多焊了一片" % tag)

    for k in range(3):
        name = "if_slot_%s_%d" % (tag, k)
        r, a = polar(at(name))
        if abs(r - I.KEY_R) > 0.01 or not near(a, I.KEY_ANGLES[k]):
            fail("%s 位置不对 r=%.2f a=%.1f" % (name, r, a))
        name = "if_steel_%s_%d" % (tag, k)
        r, a = polar(at(name))
        if abs(r - I.MAGNET_R) > 0.01 or not near(a, I.MAGNET_ANGLES[k]):
            fail("%s 位置不对 r=%.2f a=%.1f" % (name, r, a))

if any(n.startswith(("if_key_", "if_magnet_")) for n in bpy.data.objects.keys()):
    fail("球上出现了凸起：%s" % [n for n in bpy.data.objects.keys()
                               if n.startswith(("if_key_", "if_magnet_"))])

# 井口倒角只写在标准里，模型不建环：任何进入井口的几何体都会挡住 φ29.6 插头
rims = [n for n in bpy.data.objects.keys() if n.startswith("if_rim_")]
if rims:
    fail("井口不应有环：%s" % rims)

# 井底片 φ29.9（IF_R - 0.05）：盖住槽外缘，又给插头留 0.05 间隙
for tag in ("top", "bot"):
    disk = at("if_floor_%s" % tag)
    r = max(math.hypot(p.x, p.y) for p in
            (disk.matrix_world @ v.co for v in disk.data.vertices)) * 1000.0
    if abs(r - (I.WELL_R - 0.05)) > 0.02:
        fail("if_floor_%s 半径 %.2f，应为 %.2f" % (tag, r, I.WELL_R - 0.05))

# 井口通道里不许有球壳材料：井底平面以上、插头半径以内的球壳顶点都是侵入。
# 井底平面正好是球壳内表面与井底的交线，那是井底本身，不算通道。
for tag, sign in (("top", 1), ("bot", -1)):
    shell = at("shell_upper" if sign > 0 else "shell_lower")
    for v in shell.data.vertices:
        p = shell.matrix_world @ v.co
        z = abs(mm(p.z))
        r = math.hypot(p.x, p.y) * 1000.0
        if FLOOR + 0.01 < z < I.BALL_R + 0.5 and r < I.PLUG_R + 0.05:
            fail("%s 井口通道内有材料：r=%.2f z=%.2f" % (tag, r, z))

print("PASS")
