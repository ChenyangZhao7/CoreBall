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

print("PASS")
