"""从 coreball_rig.blend 生成「三维指挥」场景。

用法：
  blender -b --python blender/build_command.py -- --out blender/out/cmd

做的事：
  1. 打开现成工位场景（不重建任何模型）
  2. 加 CMD_TARGET（球心）和 HUB_ROOT（球心 +160）
  3. 球和整个吊点挂到控制点上，拖动即跟随
  4. 四根承力线和两根供电线用 Hook 挂到真实端点
  5. 另存为 coreball_command.blend
"""
import bpy
import os
import sys
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
RIG = os.path.join(HERE, "out", "rig", "coreball_rig.blend")
HUB_GAP = 0.160          # 米；球心到吊点中心
C_CMD = "07_指挥"


def parse_out():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    out = os.path.join(HERE, "out", "cmd")
    for i, a in enumerate(argv):
        if a == "--out" and i + 1 < len(argv):
            out = argv[i + 1]
    return os.path.abspath(out)


def reparent(ob, parent):
    """改父级但保持世界位置不变。"""
    bpy.context.view_layer.update()
    mw = ob.matrix_world.copy()
    ob.parent = parent
    ob.matrix_parent_inverse = Matrix.Identity(4)
    ob.matrix_basis = parent.matrix_world.inverted() @ mw
    bpy.context.view_layer.update()


def need(name):
    ob = bpy.data.objects.get(name)
    if ob is None:
        raise RuntimeError("场景里缺少对象 %r，拒绝生成半成品" % name)
    return ob


def hook(ob, index, target_obj):
    """把曲线的一个控制点挂到某个对象的当前世界上。"""
    m = ob.modifiers.new("hook_" + target_obj.name, 'HOOK')
    m.object = target_obj
    m.matrix_inverse = target_obj.matrix_world.inverted()
    m.vertex_indices_set([index])


def empty(name, loc, size, kind='SPHERE'):
    ob = bpy.data.objects.new(name, None)
    ob.empty_display_type = kind
    ob.empty_display_size = size
    ob.show_name = True
    coll.objects.link(ob)
    ob.location = loc
    return ob


def main():
    out_dir = parse_out()
    print("打开:", RIG)
    bpy.ops.wm.open_mainfile(filepath=RIG)

    global coll
    coll = bpy.data.collections.get(C_CMD)
    if coll is None:
        coll = bpy.data.collections.new(C_CMD)
        bpy.context.scene.collection.children.link(coll)

    ball_root = need("ball_root")
    ball_pos = ball_root.matrix_world.translation.copy()

    target = empty("CMD_TARGET", ball_pos, 0.06)
    hub_root = empty("HUB_ROOT", ball_pos + Vector((0, 0, HUB_GAP)), 0.05, 'PLAIN_AXES')

    reparent(ball_root, target)
    reparent(hub_root, target)

    hub_coll = bpy.data.collections.get("04_吊点")
    if hub_coll is None:
        raise RuntimeError("找不到集合 04_吊点")
    for ob in list(hub_coll.objects):
        reparent(ob, hub_root)

    for i in range(1, 5):
        hook(need("cable_%d" % i), 1, need("lug_%d" % i))

    sheave = need("tether_sheave")
    hook(need("wire_1"), 1, sheave)
    hook(need("wire_2"), 0, sheave)

    for ob in bpy.context.view_layer.objects:
        ob.select_set(False)
    target.select_set(True)
    bpy.context.view_layer.objects.active = target

    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "coreball_command.blend")
    tmp = path + ".tmp.blend"
    bpy.ops.wm.save_as_mainfile(filepath=tmp)
    os.replace(tmp, path)
    print("已保存:", path)


if __name__ == "__main__":
    main()
