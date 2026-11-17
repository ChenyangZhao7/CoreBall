"""无头验收：指挥场景的父子关系、Hook、面板与禁区回弹。

用法：
  blender -b blender/out/cmd/coreball_command.blend --python-exit-code 1 --python blender/tests/test_command.py
"""
import bpy
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


# ---------- Task 1：控制层 ----------
if "CMD_TARGET" not in bpy.data.objects:
    fail("没有 CMD_TARGET")
if "HUB_ROOT" not in bpy.data.objects:
    fail("没有 HUB_ROOT")

t = bpy.data.objects["CMD_TARGET"]
if bpy.data.objects["ball_root"].parent != t:
    fail("ball_root 没挂到 CMD_TARGET")

hub_objs = list(bpy.data.collections["04_吊点"].objects)
bad = [o.name for o in hub_objs if o.parent != bpy.data.objects["HUB_ROOT"]]
if bad:
    fail("这些吊点对象没挂到 HUB_ROOT: %s" % bad)

before = bpy.data.objects["ball_root"].matrix_world.translation.copy()
hp = bpy.data.objects["hub_plate"].matrix_world.translation.copy()
t.location.x += 0.2
bpy.context.view_layer.update()
after = bpy.data.objects["ball_root"].matrix_world.translation
hp2 = bpy.data.objects["hub_plate"].matrix_world.translation
if abs((after - before).x - 0.2) > 1e-5:
    fail("球没跟着走")
if abs((hp2 - hp).x - 0.2) > 1e-5:
    fail("吊点没跟着走")

print("PASS")
