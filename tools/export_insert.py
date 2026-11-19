"""Build a short plug-insert demo and export it as GLB.

Usage (from the repo root):
  blender -b --python tools/export_insert.py
"""
import os
import sys

import bpy
from mathutils import Matrix, Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import interface_spec as I  # noqa: E402

BALL = os.path.join(ROOT, "blender", "out", "ball", "coreball_ball.blend")
HUB = os.path.join(ROOT, "blender", "out", "hub", "coreball_hub.blend")
OUT = os.path.join(ROOT, "web", "models", "insert.glb")

bpy.ops.wm.open_mainfile(filepath=BALL)
for ob in list(bpy.data.objects):
    if ob.type in {'LIGHT', 'CAMERA'} or ob.name == "floor":
        bpy.data.objects.remove(ob, do_unlink=True)

names = []
with bpy.data.libraries.load(HUB, link=False) as (src, dst):
    names = [n for n in src.objects
             if n.startswith(("hub_plug", "plug_key", "plug_magnet", "plug_pin",
                              "friction_ring", "breakaway"))]
    dst.objects = names

objs = []
for ob in dst.objects:
    if ob is None:
        continue
    bpy.context.scene.collection.objects.link(ob)
    objs.append(ob)

bpy.context.view_layer.update()
plug = bpy.data.objects.get("hub_plug")
if plug is None:
    raise SystemExit("hub_plug not found")

end_z = plug.matrix_world.translation.z - (I.PLUG_H / 2.0) * 0.001
delta = Vector((0.0, 0.0, (I.BALL_R - I.WELL_DEPTH + 0.4) * 0.001)) - \
    Vector((plug.matrix_world.translation.x, plug.matrix_world.translation.y, end_z))

for ob in objs:
    ob.matrix_world = Matrix.Translation(delta) @ ob.matrix_world

bpy.context.view_layer.update()

root = bpy.data.objects.new("DEMO_PLUG", None)
bpy.context.scene.collection.objects.link(root)
for ob in objs:
    ob.parent = root
    ob.matrix_parent_inverse = Matrix.Identity(4)

# 收拢状态在 +40 mm，第 30 帧压入，之后保持
sc = bpy.context.scene
sc.render.fps = 24
sc.frame_start = 1
sc.frame_end = 60
root.location = (0.0, 0.0, 0.045)
root.keyframe_insert("location", frame=1)
root.location = (0.0, 0.0, 0.0)
root.keyframe_insert("location", frame=30)
root.keyframe_insert("location", frame=60)
act = root.animation_data.action
act.name = "Insert"
for fc in act.fcurves:
    for kp in fc.keyframe_points:
        kp.interpolation = 'BEZIER'
        kp.easing = 'EASE_IN_OUT'

os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=OUT,
    export_format='GLB',
    export_apply=True,
    export_animations=True,
    export_frame_range=True,
    export_force_sampling=True,
    export_yup=True,
    export_cameras=False,
    export_lights=False,
)
print("exported", OUT, "%.1f MB" % (os.path.getsize(OUT) / 1e6))
