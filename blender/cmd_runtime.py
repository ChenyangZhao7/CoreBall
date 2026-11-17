"""指挥场景的运行时：面板刷新 + 禁区回弹。

由 指挥.bat 用 `blender <blend> --python cmd_runtime.py` 启动。
直接双击 .blend 不会跑这个文件：线和球照样跟随，只是没有面板。

所有数值单位：毫米（界面）与米（Blender），在边界转换。
"""
import sys
from pathlib import Path

import bpy
import blf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tools"))

import tension as T  # noqa: E402

HUB_GAP_MM = 160.0      # 球心 → 吊点中心
NECK_X, NECK_Y = 0.0, 890.0
NECK_R = 210.0


def status_text(res):
    if res is None:
        return "几何退化"
    if res["margin"] >= T.T_MIN:
        return "力封闭正常"
    return "力封闭失效（最松 %.2f N）" % res["margin"]


def status_color(res):
    if res is None:
        return (0.85, 0.70, 0.30, 1.0)
    if res["margin"] >= T.T_MIN:
        return (0.35, 0.78, 0.52, 1.0)
    return (0.85, 0.30, 0.28, 1.0)


def hud_lines(hub_mm, res, blocked=False):
    pos = "吊点 (%d, %d, %d)" % (hub_mm[0], hub_mm[1], hub_mm[2])
    if res is None:
        lines = [pos, "线长 mm  —", "张力 N   —", status_text(None)]
    else:
        lengths = "线长 mm  " + " ".join("%4.0f" % v for v in res["lengths"])
        force = "张力 N   " + " ".join("%4.2f" % v for v in res["T"])
        lines = [pos, lengths, force,
                 "最松 %.2f N · %s" % (res["margin"], status_text(res))]
    if blocked:
        lines[-1] = "安全层否决 · " + lines[-1]
    return lines


def clamp_ball(p):
    """把球心推出脖子圆柱；圆柱内沿最短方向推到 r=210。"""
    x, y, z = p
    dx, dy = x - NECK_X, y - NECK_Y
    r = (dx * dx + dy * dy) ** 0.5
    if r >= NECK_R:
        return (x, y, z)
    if r < 1e-6:
        return (NECK_X + NECK_R, NECK_Y, z)
    k = NECK_R / r
    return (NECK_X + dx * k, NECK_Y + dy * k, z)


# ---------------- 运行时 ----------------
STATE = {"hub_mm": None, "res": None, "blocked": False}
_busy = False
_last = 0.0
_HANDLER = None


def _tick(scene=None, depsgraph=None):
    global _busy, _last
    import time
    if _busy:
        return
    now = time.monotonic()
    if now - _last < 0.05:
        return
    _last = now
    _busy = True
    try:
        t = bpy.data.objects.get("CMD_TARGET")
        h = bpy.data.objects.get("HUB_ROOT")
        if t is None or h is None:
            return
        p = t.matrix_world.translation
        p_mm = (p.x * 1000.0, p.y * 1000.0, p.z * 1000.0)
        c = clamp_ball(p_mm)
        moved = max(abs(c[i] - p_mm[i]) for i in range(3))
        if moved > 1e-3:
            t.location = (c[0] / 1000.0, c[1] / 1000.0, c[2] / 1000.0)
            STATE["blocked"] = True
        else:
            STATE["blocked"] = False
        hw = h.matrix_world.translation
        hub_mm = (hw.x * 1000.0, hw.y * 1000.0, hw.z * 1000.0)
        try:
            res = T.solve(hub_mm)
        except Exception:
            res = None
        STATE.update(hub_mm=hub_mm, res=res)
    finally:
        _busy = False


def _draw():
    if STATE["hub_mm"] is None:
        return
    try:
        top = bpy.context.region.height - 24
    except Exception:
        top = 560
    lines = hud_lines(STATE["hub_mm"], STATE["res"], STATE["blocked"])
    blf.size(0, 13)
    for i, ln in enumerate(lines):
        blf.color(0, *(0.78, 0.84, 0.90, 1.0) if i < 3 else status_color(STATE["res"]))
        blf.position(0, 18, top - i * 17, 0)
        blf.draw(0, ln)


def register():
    global _HANDLER
    if _tick not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_tick)
    if _HANDLER is None:
        _HANDLER = bpy.types.SpaceView3D.draw_handler_add(_draw, (), 'WINDOW', 'POST_PIXEL')
    print("CoreBall 指挥运行时已启动：拖 CMD_TARGET")


if __name__ == "__main__":
    register()
