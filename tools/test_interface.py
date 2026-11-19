import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import interface_spec as I


def eq(a, b, msg):
    if a != b:
        raise SystemExit("FAIL: %s (%r != %r)" % (msg, a, b))


def angular_gap(a, b):
    d = abs((a - b) % 360.0)
    return min(d, 360.0 - d)


# 版本与包络：两井完全相同
eq(I.VERSION, "1.0", "版本")
eq(I.BALL_R, 40.0, "球半径")
eq((I.WELL_R, I.WELL_DEPTH), (15.0, 5.0), "井")
eq(round(I.WELL_R - I.PLUG_R, 3), 0.2, "单边间隙")
eq(I.PLUG_H, 4.6, "插头高")

# 键位：不等距 → 只有一种插法
eq(tuple(round((I.KEY_ANGLES[(i + 1) % 3] - I.KEY_ANGLES[i]) % 360.0, 1)
         for i in range(3)), (96.0, 128.0, 136.0), "键距")
eq(I.KEY_R, 12.6, "键半径")
eq((I.KEY_W, I.KEY_H), (3.0, 2.3), "键宽高")
eq((I.SLOT_W, I.SLOT_DEPTH), (3.4, 2.0), "键槽")

# 轴向：键必须放得进槽深 + 插头与井底的间隙
if I.KEY_H > (I.WELL_DEPTH - I.PLUG_H) + I.SLOT_DEPTH:
    raise SystemExit("FAIL: 键比槽深，插头会顶死")

# 触点：6 位 60°，头顶只用前 4 位
eq(I.PAD_ANGLES, (0.0, 60.0, 120.0, 180.0, 240.0, 300.0), "触点角")
eq(I.pad_angles(4), I.PAD_ANGLES[:4], "头顶 4 片")
eq(I.pad_angles(6), I.PAD_ANGLES, "脚底 6 片")
try:
    I.pad_angles(5)
except ValueError:
    pass
else:
    raise SystemExit("FAIL: 5 片应该报错")

# 引脚
eq(tuple(I.pin_function(i) for i in range(6)), I.PIN_NAMES, "引脚顺序")
eq(tuple(I.PIN_NAMES[i] for i in (0, 1, 2, 3)), ("VBUS", "GND", "TX", "RX"), "前四针")

# 磁铁与钢片
eq(tuple(I.MAGNET_ANGLES), (30.0, 150.0, 270.0), "磁铁角")
eq((I.MAGNET_R, I.MAGNET_D, I.MAGNET_H), (10.0, 5.0, 2.0), "磁铁")
eq((I.STEEL_D, I.STEEL_H), (5.0, 1.0), "钢片")

# 磁铁不与键/触点撞角度
for m in I.MAGNET_ANGLES:
    for a in I.KEY_ANGLES + I.PAD_ANGLES:
        if angular_gap(m, a) < 20.0:
            raise SystemExit("FAIL: 磁铁 %.0f° 离 %.0f° 太近" % (m, a))

# 径向：焊盘外缘 < 键槽内缘
if I.PAD_PITCH_R + I.PAD_D / 2 >= I.KEY_R - I.SLOT_W / 2:
    raise SystemExit("FAIL: 焊盘与键槽径向重叠")

# 摩擦环：O 圈必须对井壁有过盈，否则侧向保持只剩磁吸
eq((I.FRICTION_R, I.FRICTION_D), (14.75, 0.8), "摩擦环")
if not I.FRICTION_R + I.FRICTION_D / 2 > I.WELL_R:
    raise SystemExit("FAIL: O 圈没有过盈，侧向保持不足")

# 通信
eq(I.PROTO_VERSION, 0x10, "协议版本")
eq(I.BAUD, 115200, "波特率")

# 极坐标
x, y = I.polar(9.0, 90.0)
eq((round(x, 6), round(y, 6)), (0.0, 9.0), "polar")

# 接口图与正式标准
import interface_draw

s = interface_draw.svg()
eq(s.count('class="pad"'), 6, "图里 6 个焊盘")
eq(s.count('class="slot"'), 3, "图里 3 个键槽")
eq(s.count('class="magnet"'), 3, "图里 3 块磁铁")
for want in ("φ30.00", "5.00", "尺寸单位 mm", "键槽", "焊盘", "磁铁"):
    if want not in s:
        raise SystemExit("FAIL: 图里缺 %s" % want)

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(root, "docs", "04-接口标准.md"), encoding="utf-8") as f:
    doc = f.read()
for want in (I.VERSION, "φ80", "φ30.00", "H8", "0° / 96° / 224°",
             "%d 8N1" % I.BAUD, hex(I.PROTO_VERSION), "20 ± 3 N",
             "TX（球 → 载体）", "RX（载体 → 球）", "小端",
             "CRC-16/CCITT-FALSE", "0x1021", "0xFFFF", "14.75",
             "镜像", "球顶切平面", "所有尺寸单位 mm"):
    if want not in doc:
        raise SystemExit("FAIL: 标准里缺 %s" % want)
for name in I.PIN_NAMES:
    if name not in doc:
        raise SystemExit("FAIL: 标准里缺引脚 %s" % name)

print("PASS")
