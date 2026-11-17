"""指挥场景的运行时：面板刷新 + 禁区回弹。

由 指挥.bat 用 `blender <blend> --python cmd_runtime.py` 启动。
直接双击 .blend 不会跑这个文件：线和球照样跟随，只是没有面板。

所有数值单位：毫米（界面）与米（Blender），在边界转换。
"""
import sys
from pathlib import Path

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


def hud_lines(hub_mm, res):
    pos = "吊点 (%d, %d, %d)" % (hub_mm[0], hub_mm[1], hub_mm[2])
    if res is None:
        return [pos, "线长 mm  —", "张力 N   —", status_text(None)]
    lengths = "线长 mm  " + " ".join("%4.0f" % v for v in res["lengths"])
    force = "张力 N   " + " ".join("%4.2f" % v for v in res["T"])
    tail = "最松 %.2f N · %s" % (res["margin"], status_text(res))
    return [pos, lengths, force, tail]
