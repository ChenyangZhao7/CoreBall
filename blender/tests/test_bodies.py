"""两个身体的无头验收。

用法：
  blender -b blender/out/cmd/coreball_command.blend --python-exit-code 1 --python blender/tests/test_bodies.py
"""
import bpy
import sys
import os
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


# ---------- 小车在场景里 ----------
for name in ("ROVER_ROOT", "rover_mesh", "TGT_ROVER_NEAR", "TGT_ROVER_HOME"):
    if name not in bpy.data.objects:
        fail("场景里没有 %s" % name)

if (bpy.data.objects["ROVER_ROOT"].matrix_world.translation
        - Vector((0.600, 0.250, 0.0))).length > 0.01:
    fail("ROVER_ROOT 位置不对：%s" % (bpy.data.objects["ROVER_ROOT"].matrix_world.translation,))

if (bpy.data.objects["TGT_ROVER_NEAR"].matrix_world.translation
        - Vector((-0.450, 0.650, 0.0))).length > 0.001:
    fail("TGT_ROVER_NEAR 位置不对")

mats = [m.name for m in bpy.data.objects["rover_mesh"].data.materials]
if "ROVER_LED" not in mats:
    fail("核心灯没接 ROVER_LED 材质：%s" % mats)

dg = bpy.context.evaluated_depsgraph_get()
ev = bpy.data.objects["rover_mesh"].evaluated_get(dg)
zmin = min((ev.matrix_world @ v.co).z for v in ev.data.vertices)
if abs(zmin) > 0.002:
    fail("轮子没贴地：zmin=%.4f m" % zmin)


# ---------- 运行时换身 ----------
import cmd_runtime as R

if R.BODY["active"] != "winch":
    fail("默认不是吊索")

start_loc = tuple(bpy.data.objects["CMD_TARGET"].location)
R.apply_intent({"intent": "mount_rover"})
if R.BODY["active"] != "rover":
    fail("没换到小车")
if not bpy.data.objects["ball_root"].hide_viewport:
    fail("球没藏起来")

R._last = 0.0
R._tick()
if R.STATE["body"] != "rover":
    fail("面板没切到小车")

R.apply_intent({"intent": "come"})
if not R.MOVE["active"]:
    fail("小车没收到过来")
if abs(R.MOVE["p1"][0] - (-450.0)) > 1.0 or abs(R.MOVE["p1"][2]) > 1.0:
    fail("小车目标不对：%s" % (R.MOVE["p1"],))

R.apply_intent({"intent": "up"})
if "升降" not in (R.STATE["last"] or ""):
    fail("小车升降没拒绝：%s" % (R.STATE["last"],))

R.apply_intent({"intent": "mount_winch"})
if R.BODY["active"] != "winch":
    fail("没换回吊索")
if bpy.data.objects["ball_root"].hide_viewport:
    fail("球没回来")
if tuple(bpy.data.objects["CMD_TARGET"].location) != start_loc:
    fail("球的位置被换了：%s" % (tuple(bpy.data.objects["CMD_TARGET"].location),))

print("PASS")
