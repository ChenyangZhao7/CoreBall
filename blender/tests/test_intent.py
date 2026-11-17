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

print("PASS")
