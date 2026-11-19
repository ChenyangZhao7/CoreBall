"""接口 v1.0：工位场景里的吊点插头（球是导入的真实球）。

用法：
  blender -b blender/out/rig/coreball_rig.blend --python-exit-code 1 --python blender/tests/test_interface_rig.py
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


def top(ob):
    return max(mm((ob.matrix_world @ v.co).z) for v in ob.data.vertices)


def bottom(ob):
    return min(mm((ob.matrix_world @ v.co).z) for v in ob.data.vertices)


def radial(ob, c):
    pts = [ob.matrix_world @ v.co for v in ob.data.vertices]
    return max(math.hypot(p.x - c.x, p.y - c.y) for p in pts) * 1000.0


ball_top = mm(at("ball_root").matrix_world.translation.z) + I.BALL_R
well_floor = ball_top - I.WELL_DEPTH

plug = at("hub_plug")
c = plug.matrix_world.translation.copy()

# 插头鼻子顶面 = 球顶切平面（球心 + 半径）
if abs(top(plug) - ball_top) > 0.01:
    fail("插头顶面 %.2f，应为球顶 %.2f" % (top(plug), ball_top))

# 插头端面 = 井底 + 0.4
end = bottom(plug)
if abs(end - (well_floor + 0.4)) > 0.02:
    fail("插头端面 %.2f，应在井底 %.2f 上方 0.4" % (end, well_floor))

# 键尖 = 槽底 + 0.1（键高 = 槽深 + 0.4 间隙 − 0.1 余量）
slot_bottom = well_floor - I.SLOT_DEPTH
key_tip = min(bottom(at("plug_key_%d" % k)) for k in range(3))
if abs(key_tip - (slot_bottom + 0.1)) > 0.02:
    fail("键尖 %.2f，应离槽底 %.2f 上方 0.1" % (key_tip, slot_bottom))

# 摩擦环外半径 > 井半径：O 圈对井壁有过盈
ring_r = radial(at("friction_ring"), c)
if not ring_r > I.WELL_R:
    fail("摩擦环外半径 %.2f，没有过盈（井半径 %.2f）" % (ring_r, I.WELL_R))

print("PASS")
