"""
CoreBall - 接口标准 v1.0 的单一数值源

所有尺寸单位为 mm，角度单位为度。
Blender 模型、标准文档、接口图都从这里取数，不要另抄一份。

用法：
  import interface_spec as I
  x, y = I.polar(I.PAD_PITCH_R, I.PAD_ANGLES[0])
"""

import math

VERSION = "1.0"

# ---------------- 球与井 ----------------
BALL_R     = 40.0          # 球半径
WELL_R     = 15.0          # 井半径
WELL_DEPTH = 5.0           # 井深

# ---------------- 插头 ----------------
PLUG_R = 14.8              # 单边间隙 0.2
PLUG_H = 4.6

# ---------------- 键位（不等距，只有一种插法） ----------------
KEY_ANGLES = (0.0, 96.0, 224.0)
KEY_R      = 12.6
KEY_W      = 3.0
KEY_H      = 2.3           # 槽深 2.0 + 插头轴向间隙 0.4，留 0.1 余量

SLOT_W     = 3.4
SLOT_DEPTH = 2.0

# ---------------- 触点 ----------------
# 6 位 60°；头顶只用前 4 位，脚底用全部 6 位
PAD_ANGLES  = (0.0, 60.0, 120.0, 180.0, 240.0, 300.0)
PAD_PITCH_R = 9.0
PAD_D       = 2.5

# ---------------- 引脚 ----------------
PIN_NAMES = ("VBUS", "GND", "TX", "RX", "VBUS", "GND")

# ---------------- 磁铁与钢片 ----------------
# 磁铁偏开键与触点的角度，避免吸错面
MAGNET_ANGLES = (30.0, 150.0, 270.0)
MAGNET_R = 10.0
MAGNET_D = 5.0
MAGNET_H = 2.0

STEEL_D = 5.0
STEEL_H = 1.0

# ---------------- 摩擦面 ----------------
# 硅胶 O 圈坐在插头鼻子的环槽里：中心线 14.75，线径 0.8
# 自由外径 15.15，对 φ30 井壁单边过盈 0.15
FRICTION_R = 14.75
FRICTION_D = 0.8

# ---------------- 通信 ----------------
PROTO_VERSION = 0x10
BAUD = 115200


# ---------------- 纯函数 ----------------

def pad_angles(count):
    """头顶取 4 片，脚底取 6 片，其它数量直接报错。"""
    if count not in (4, 6):
        raise ValueError("only 4 or 6 pads")
    return PAD_ANGLES[:count]


def pin_function(index):
    """按针位取功能名。"""
    return PIN_NAMES[index]


def polar(radius, angle_deg):
    """度 → (x, y)，单位 mm。"""
    a = math.radians(angle_deg)
    return (radius * math.cos(a), radius * math.sin(a))
