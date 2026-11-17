"""指挥场景的运行时：面板刷新 + 禁区回弹。

由 指挥.bat 用 `blender <blend> --python cmd_runtime.py` 启动。
直接双击 .blend 不会跑这个文件：线和球照样跟随，只是没有面板。

所有数值单位：毫米（界面）与米（Blender），在边界转换。
"""
import sys
import json
import math
import socket
import threading
import queue
import time
from pathlib import Path

import bpy
import blf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tools"))

import tension as T  # noqa: E402

ACTIONS_PATH = HERE / "actions.json"

HUB_GAP_MM = 160.0      # 球心 → 吊点中心
NECK_X, NECK_Y = 0.0, 890.0
NECK_R = 210.0
ANCHOR_Z = 1729.0       # 四个锚点同高；吊点落在这个平面上，零空间退化


def load_actions(path=None):
    p = Path(path) if path else ACTIONS_PATH
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or not isinstance(data.get("actions"), dict):
        raise ValueError("动作表缺少 actions")
    return data


def resolve(actions, src, key):
    table = (actions.get("bindings") or {}).get(src) or {}
    return table.get(str(key))


def intent_point(actions, name, points, current_mm):
    act = (actions.get("actions") or {}).get(name)
    if not act:
        return None
    if "target" in act:
        p = points.get(act["target"])
        return list(p) if p is not None else None
    if "delta" in act:
        return [current_mm[i] + float(act["delta"][i]) for i in range(3)]
    return None


def move_profile(d, vmax=356.0, rebound=4.0):
    """五次多项式 S 曲线 + 到位后 4mm 越冲再收住。d 毫米，vmax 毫米/秒。"""
    if d <= 1e-9:
        return {"T": 0.0, "pos": lambda t: 0.0}
    dur = 1.875 * d / vmax
    settle = 0.4

    def pos(t):
        if t <= 0:
            return 0.0
        if t < dur:
            u = t / dur
            x = d * (10 * u ** 3 - 15 * u ** 4 + 6 * u ** 5)
        elif t <= dur + settle:
            # 平滑越冲：起点和终点都是 0 斜率，峰值就是 rebound
            x = d + 0.5 * rebound * (1 - math.cos(2 * math.pi * (t - dur) / settle))
        else:
            x = d
        return x

    return {"T": dur, "pos": pos}


def start_move(p0, p1, style, now):
    d = ((p1[0] - p0[0]) ** 2 + (p1[1] - p0[1]) ** 2 + (p1[2] - p0[2]) ** 2) ** 0.5
    return {
        "active": d > 0.5,
        "p0": list(p0), "p1": list(p1), "d": d, "t0": now,
        "hes": float(style.get("hesitate", 0.0)),
        "profile": move_profile(d, float(style.get("vmax", 356.0)),
                                float(style.get("rebound", 4.0))),
    }


def move_at(m, now):
    if not m.get("active"):
        return list(m["p1"])
    t = now - m["t0"] - m["hes"]
    if t < 0:
        return list(m["p0"])
    prof = m["profile"]
    if t > prof["T"] + 1.0:
        m["active"] = False
        return list(m["p1"])
    f = prof["pos"](t) / m["d"] if m["d"] > 0 else 1.0
    return [m["p0"][i] + (m["p1"][i] - m["p0"][i]) * f for i in range(3)]


def scene_points():
    """所有 TGT_xxx 空物体 → {xxx: [x,y,z] mm}，用户可以自己在 Blender 里拖。"""
    pts = {}
    for ob in bpy.data.objects:
        if ob.name.startswith("TGT_"):
            p = ob.matrix_world.translation
            pts[ob.name[4:].lower()] = [p.x * 1000.0, p.y * 1000.0, p.z * 1000.0]
    return pts


def current_ball_mm():
    t = bpy.data.objects.get("CMD_TARGET")
    if t is None:
        return [0.0, 0.0, 0.0]
    p = t.matrix_world.translation
    return [p.x * 1000.0, p.y * 1000.0, p.z * 1000.0]


def route_intent(actions, msg, points, current_mm):
    name = msg.get("intent")
    conf = float(msg.get("conf", 1.0))
    if conf < float(actions.get("min_conf", 0.0)):
        return {"kind": "ignored"}
    act = (actions.get("actions") or {}).get(name)
    if act is None:
        return {"kind": "unknown", "name": name}
    if act.get("hold"):
        return {"kind": "hold", "name": name}
    if act.get("face"):
        return {"kind": "face", "name": name, "who": act["face"]}
    p = intent_point(actions, name, points, current_mm)
    if p is None:
        return {"kind": "bad_target", "name": name}
    return {"kind": "move", "name": name, "point": p,
            "style": (actions.get("styles") or {}).get(act.get("style", "normal"), {})}


def start_udp(port=4590, q=None):
    """后台线程只收包进队列，绝不碰 bpy。"""
    q = q if q is not None else INTENT_Q

    def loop():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.bind(("127.0.0.1", port))
        except OSError as e:
            print("CoreBall: UDP 端口 %d 打不开：%s" % (port, e))
            return
        while True:
            data, _ = s.recvfrom(8192)
            try:
                msg = json.loads(data.decode("utf-8"))
            except Exception:
                continue
            if isinstance(msg, dict) and msg.get("intent"):
                try:
                    q.put_nowait(msg)
                except queue.Full:
                    pass

    t = threading.Thread(target=loop, daemon=True)
    t.start()
    return t


def begin_move(point_mm, style):
    MOVE.clear()
    MOVE.update(start_move(current_ball_mm(), point_mm, style, time.monotonic()))


def face_person():
    t = bpy.data.objects.get("CMD_TARGET")
    head = bpy.data.objects.get("PERSON_HEAD")
    if t is None or head is None:
        return
    d = head.matrix_world.translation - t.matrix_world.translation
    yaw = math.atan2(d.x, d.y)          # 球脸朝 +Y
    br = bpy.data.objects.get("ball_root")
    if br is not None:
        br.rotation_euler = (0.0, 0.0, yaw)


def apply_intent(msg):
    try:
        actions = load_actions()
    except Exception:
        STATE["last"] = "动作表坏了"
        return
    r = route_intent(actions, msg, scene_points(), current_ball_mm())
    kind = r["kind"]
    if kind == "move":
        begin_move(r["point"], r["style"])
        STATE["last"] = r["name"]
    elif kind == "hold":
        MOVE["active"] = False
        STATE["last"] = "停"
    elif kind == "face":
        face_person()
        STATE["last"] = "看我"
    elif kind == "unknown":
        STATE["last"] = "不认识的指令"
    elif kind == "ignored":
        STATE["last"] = "置信度太低"
    else:
        STATE["last"] = "目标点不存在"


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
    # Blender 坐标是 float32，轴线上的点带 ~1e-5 mm 噪声；
    # 阈值取得比噪声大，避免把噪声放大成错误方向。
    if r < 0.5:
        return (NECK_X + NECK_R, NECK_Y, z)
    k = NECK_R / r
    return (NECK_X + dx * k, NECK_Y + dy * k, z)


def panel_origin(region_h):
    """面板左上角在视口里的位置：避开标题栏、Text Info 和左侧工具栏。"""
    return (110, region_h - 200)


# ---------------- 运行时 ----------------
STATE = {"hub_mm": None, "res": None, "blocked": False, "last": None}
INTENT_Q = queue.Queue(maxsize=64)
MOVE = {"active": False}
_busy = False
_last = 0.0
_HANDLER = None
_TIMERS = {"on": False}


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
            # 同一帧里 HUB_ROOT 还没跟上，直接用夹紧后的球心推吊点
            hub_mm = (c[0], c[1], c[2] + HUB_GAP_MM)
        else:
            STATE["blocked"] = False
            hw = h.matrix_world.translation
            hub_mm = (hw.x * 1000.0, hw.y * 1000.0, hw.z * 1000.0)
        try:
            if abs(hub_mm[2] - ANCHOR_Z) < 1.0:
                raise ValueError("吊点与锚点同高，零空间退化")
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
        x0, top = panel_origin(bpy.context.region.height)
    except Exception:
        x0, top = panel_origin(800)
    lines = hud_lines(STATE["hub_mm"], STATE["res"], STATE["blocked"])
    res = STATE["res"]
    if res is None or STATE["blocked"]:
        color = (0.85, 0.70, 0.30, 1.0)
    elif res["margin"] < T.T_MIN:
        color = (0.85, 0.30, 0.28, 1.0)
    else:
        color = (0.78, 0.84, 0.90, 1.0)
    blf.size(0, 13)
    for i, ln in enumerate(lines):
        blf.color(0, *color)
        blf.position(0, x0, top - i * 17, 0)
        blf.draw(0, ln)


def _move_tick():
    if MOVE.get("active"):
        p = move_at(MOVE, time.monotonic())
        c = clamp_ball(p)
        t = bpy.data.objects.get("CMD_TARGET")
        if t is not None:
            t.location = (c[0] / 1000.0, c[1] / 1000.0, c[2] / 1000.0)
    return 1.0 / 60.0


def _intent_tick():
    while True:
        try:
            msg = INTENT_Q.get_nowait()
        except queue.Empty:
            break
        apply_intent(msg)
    return 0.05


_KEYCODES = {
    "0": "ZERO", "1": "ONE", "2": "TWO", "3": "THREE", "4": "FOUR",
    "5": "FIVE", "6": "SIX", "7": "SEVEN", "8": "EIGHT", "9": "NINE",
}


class CMDBALL_OT_intent(bpy.types.Operator):
    bl_idname = "cmdball.intent"
    bl_label = "CoreBall Intent"
    intent: bpy.props.StringProperty()

    def execute(self, context):
        apply_intent({"intent": self.intent, "src": "key"})
        return {'PASS_THROUGH'}


def register_keys(actions):
    kc = bpy.context.window_manager.keyconfigs.addon
    if kc is None:
        return
    km = kc.keymaps.get("3D View")
    if km is None:
        km = kc.keymaps.new(name="3D View", space_type='VIEW_3D')
    for k, name in ((actions.get("bindings") or {}).get("key") or {}).items():
        code = _KEYCODES.get(str(k))
        if code is None:
            continue
        kmi = km.keymap_items.new("cmdball.intent", code, 'PRESS')
        kmi.properties.intent = name


def register():
    global _HANDLER, _last
    if _tick not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_tick)
    if _HANDLER is None:
        _HANDLER = bpy.types.SpaceView3D.draw_handler_add(_draw, (), 'WINDOW', 'POST_PIXEL')
    try:
        bpy.utils.register_class(CMDBALL_OT_intent)
    except ValueError:
        pass
    try:
        register_keys(load_actions())
    except Exception as e:
        print("CoreBall: 动作表没读成，键盘没绑：", e)
    start_udp(4590)
    if not _TIMERS["on"]:
        bpy.app.timers.register(_move_tick, persistent=True)
        bpy.app.timers.register(_intent_tick, persistent=True)
        _TIMERS["on"] = True
    _last = 0.0
    _tick()
    print("CoreBall 指挥运行时已启动：拖 CMD_TARGET，或按键 1/2/3/4/5/0")


if __name__ == "__main__":
    register()
