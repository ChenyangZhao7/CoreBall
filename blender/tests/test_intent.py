"""交互层无头验收。

用法：
  blender -b blender/out/cmd/coreball_command.blend --python-exit-code 1 --python blender/tests/test_intent.py
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


# ---------- Task 1：人与命名点 ----------
for name in ("PERSON_HEAD", "TGT_HOME", "TGT_NEAR"):
    if name not in bpy.data.objects:
        fail("场景里没有 %s" % name)

def near(vec, want, tol_mm=5.0):
    return (Vector(vec) - Vector(want)).length * 1000.0 <= tol_mm

if not near(bpy.data.objects["PERSON_HEAD"].matrix_world.translation, (0, 0.890, 1.250)):
    fail("PERSON_HEAD 位置不对：%s" % (bpy.data.objects["PERSON_HEAD"].matrix_world.translation,))
if not near(bpy.data.objects["TGT_NEAR"].matrix_world.translation, (-0.380, 0.520, 1.300), 1.0):
    fail("TGT_NEAR 位置不对")
if not near(bpy.data.objects["TGT_HOME"].matrix_world.translation, (-0.430, 0.760, 1.420), 1.0):
    fail("TGT_HOME 位置不对")


# ---------- Task 2：动作表 ----------
from cmd_runtime import load_actions, resolve, intent_point, ACTIONS_PATH
import tempfile

A = load_actions(ACTIONS_PATH)
if resolve(A, "key", "1") != "come":
    fail("按键 1 没映射到 come")
if resolve(A, "key", "9") is not None:
    fail("未知按键不该有映射")

pts = {"near": [-380.0, 520.0, 1300.0], "home": [-430.0, 760.0, 1420.0]}
if intent_point(A, "come", pts, [0, 0, 0]) != pts["near"]:
    fail("come 没解析到 near")
u = intent_point(A, "up", pts, [-100.0, 500.0, 1300.0])
if u != [-100.0, 500.0, 1420.0]:
    fail("up 的 delta 不对：%s" % (u,))
if intent_point(A, "nope", pts, [0, 0, 0]) is not None:
    fail("未知动作应返回 None")

bad = os.path.join(tempfile.gettempdir(), "bad_actions.json")
with open(bad, "w", encoding="utf-8") as f:
    f.write("{not json")
try:
    load_actions(bad)
    fail("坏动作表应该抛 ValueError")
except ValueError:
    pass

print("PASS")
