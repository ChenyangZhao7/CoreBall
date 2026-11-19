"""Export browser-friendly GLB previews from the built Blender scenes.

Usage (from the repo root):
  blender -b --python tools/export_models.py

Outputs to web/models/:
  ball.glb    球（两个井、焊盘、键槽、钢片）
  hub.glb     吊点 + 插头
  rig.glb     工位 + 球 + 吊点（整机）
"""
import os
import sys

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "web", "models")
os.makedirs(OUT, exist_ok=True)

SCENES = (
    ("ball", os.path.join(ROOT, "blender", "out", "ball", "coreball_ball.blend")),
    ("hub", os.path.join(ROOT, "blender", "out", "hub", "coreball_hub.blend")),
    ("rig", os.path.join(ROOT, "blender", "out", "rig", "coreball_rig.blend")),
)


def strip(keep_floor=False):
    for ob in list(bpy.data.objects):
        if ob.type in {'LIGHT', 'CAMERA'}:
            bpy.data.objects.remove(ob, do_unlink=True)
            continue
        if ob.type == 'EMPTY' and ob.name.startswith(("aim_", "Cam")):
            bpy.data.objects.remove(ob, do_unlink=True)
            continue
        if not keep_floor and ob.name == "floor":
            bpy.data.objects.remove(ob, do_unlink=True)


def export(name, blend):
    bpy.ops.wm.open_mainfile(filepath=blend)
    strip()
    path = os.path.join(OUT, name + ".glb")
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format='GLB',
        export_apply=True,
        export_animations=False,
        export_yup=True,
        export_cameras=False,
        export_lights=False,
    )
    size = os.path.getsize(path) / 1e6
    print("exported %s (%.1f MB)" % (path, size))


for name, blend in SCENES:
    if not os.path.exists(blend):
        print("missing:", blend)
        continue
    export(name, blend)
