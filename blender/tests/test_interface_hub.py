"""接口 v1.0：吊点插头。

用法：
  blender -b blender/out/hub/coreball_hub.blend --python-exit-code 1 --python blender/tests/test_interface_hub.py
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


def radial(ob, c):
    # 量真实顶点半径；bound_box 的角点会把半径放大 sqrt(2)
    pts = [ob.matrix_world @ v.co for v in ob.data.vertices]
    return max(math.hypot(p.x - c.x, p.y - c.y) for p in pts) * 1000.0


def near(a, b, tol=0.5):
    return abs((a - b + 180.0) % 360.0 - 180.0) <= tol


plug = at("hub_plug")
c = plug.matrix_world.translation.copy()

# 鼻子 φ29.6
r = radial(plug, c)
if abs(r - I.PLUG_R) > 0.1:
    fail("鼻子半径 %.2f，应为 %.2f" % (r, I.PLUG_R))
if abs(mm(plug.dimensions.z) - I.PLUG_H) > 0.05:
    fail("鼻子高度 %.2f，应为 %.2f" % (mm(plug.dimensions.z), I.PLUG_H))

# 键、磁铁、针全部在插头上
for k in range(3):
    p = at("plug_key_%d" % k).matrix_world.translation
    if abs(math.hypot(p.x - c.x, p.y - c.y) * 1000.0 - I.KEY_R) > 0.05:
        fail("plug_key_%d 半径不对" % k)
    if not near(math.degrees(math.atan2(p.y - c.y, p.x - c.x)) % 360.0,
                I.KEY_ANGLES[k]):
        fail("plug_key_%d 角度不对" % k)

for k in range(3):
    p = at("plug_magnet_%d" % k).matrix_world.translation
    if abs(math.hypot(p.x - c.x, p.y - c.y) * 1000.0 - I.MAGNET_R) > 0.05:
        fail("plug_magnet_%d 半径不对" % k)
    if not near(math.degrees(math.atan2(p.y - c.y, p.x - c.x)) % 360.0,
                I.MAGNET_ANGLES[k]):
        fail("plug_magnet_%d 角度不对" % k)

heights = {}
for k in range(4):
    p = at("plug_pin_%d" % k).matrix_world.translation
    if abs(math.hypot(p.x - c.x, p.y - c.y) * 1000.0 - I.PAD_PITCH_R) > 0.05:
        fail("plug_pin_%d 半径不对" % k)
    if not near(math.degrees(math.atan2(p.y - c.y, p.x - c.x)) % 360.0,
                I.PAD_ANGLES[k]):
        fail("plug_pin_%d 角度不对" % k)
    heights[I.PIN_NAMES[k]] = p.z

# 先接地后上电：GND 最长（最低）→ TX/RX → VBUS 最短
if not (heights["GND"] < heights["TX"] < heights["VBUS"]):
    fail("针长顺序不对：%s" % heights)
if abs(heights["TX"] - heights["RX"]) > 0.001:
    fail("TX/RX 应该齐平：%s" % heights)

ring = at("friction_ring")
if abs(radial(ring, c) - (I.FRICTION_R + I.FRICTION_D / 2)) > 0.1:
    fail("摩擦环半径不对")

if any(n.startswith("hub_key_") for n in bpy.data.objects.keys()):
    fail("旧键还在")

print("PASS")
