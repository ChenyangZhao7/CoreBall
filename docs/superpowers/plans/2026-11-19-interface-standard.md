# 接口标准 v1.0 · 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把球的两个井冻结成同一套 φ30 接口，并用同一份数值改模型、文档和测试；顶部与底部载体用镜像插头，各自都能通电、能说话。

**Architecture:** 新增 `tools/interface_spec.py` 作为唯一数值源，只放常量与三个纯函数；`tools/interface_draw.py` 从它生成 `docs/interface.svg`；`build_ball.py`、`build_hub.py`、`build_desk_rig.py` 全部 import 它，不再各写一份尺寸。测试分三层：纯 Python 测数值与文档、无头 Blender 测球井、无头 Blender 测吊点插头。

**Tech Stack:** Python 3.11（仓库已有）、Blender 4.5 Python、SVG、标准库（不新增依赖）。

**Spec:** `docs/superpowers/specs/2026-11-17-interface-standard-design.md`

## Global Constraints

- 球径 φ80，壁厚 2；井 φ30.00（H8 +0.033/0）、深 5.00 ±0.10；**顶部与底部完全相同**。
- 插头 φ29.60 ±0.05、高 4.60 ±0.05；单边间隙 0.20（径向总间隙 0.40）。
- 键 3 个，角度 0° / 96° / 224°（0° = +X，从 +Z 看逆时针；两个井用同一球坐标系），半径 12.6，宽 3.0，径向长 3.0，高 2.3（槽深 2.0 + 插头轴向间隙 0.4 − 0.1 余量）；**键在载体插头上（凸）**。
- 键槽宽 3.4、径向长 3.4、深 2.0；**槽在球井底（凹）**；球身任何东西都不许凸出球面。
- 井深 5.00 的基准是**球顶切平面**（球坐标 z=±40），不是球面与井壁交线；井壁圆柱段实际约 2.1 mm。
- 触点 6 位、60° 均布（0/60/120/180/240/300），半径 9.0；焊盘 φ2.5，齐平井底。
- 头顶载体只焊 4 片（0°/60°/120°/180°）；脚底载体焊 6 片。
- 引脚：0° VBUS 5V / 60° GND / 120° TX（球→载体）/ 180° RX（载体→球）/ 240° VBUS / 300° GND。
- 插拔顺序：GND 针最长 → TX/RX 齐平 → VBUS 针最短（先接地、后上电）。
- 磁铁在载体插头上：3 个，30° / 150° / 270°，半径 10.0，N35 φ5×2；球侧 3 片 304 钢片 φ5×1.0，齐平井底；脱开力 20 ± 3 N。
- 摩擦环：硅胶 O 圈，中心线半径 14.75，线径 0.8（自由外径 15.15，对 φ30 井壁单边过盈 0.15），坐在插头鼻子的环槽里。
- 串口：3.3 V LVCMOS，115200 8N1，协议版本 `0x10`（v1），帧 `A5 5A VER TYPE LEN PAYLOAD CRC16-CCITT`；多字节字段**小端**；CRC-16/CCITT-FALSE（poly 0x1021，init 0xFFFF，不反射，xorout 0），覆盖 `VER..PAYLOAD`；`LEN` 只计 payload；WHO 请求为 `A5 5A 10 01 00 CRC`。
- 顶部与底部井机械完全一致，但两头的插头互为镜像：同一个插头翻过来不保证能插另一头。
- 磁铁角度与任一键/触点角度至少相隔 20°。
- 数值只改 `tools/interface_spec.py`；文档和模型跟着它走，不许另抄一份。
- Blender 不在 PATH 上，命令里的 `blender` 一律指 `C:\Users\21165\Apps\blender-4.5.16\blender-4.5.16-windows-x64\blender.exe`。
- 不新增第三方依赖；现有场景名、对象前缀 `if_` 不变（`build_desk_rig.py` 靠前缀导入球体对象）。

## Review Focus

- **球上出现凸起**：键或磁铁如果还画在球上，球会磕碰、放不平、滚不动 → Task 3 的测试断言场景里没有 `if_key_*` / `if_magnet_*`。
- **顶底两井不一致**：两个井必须是同一套 φ30；历史上顶部 φ26 就是靠人肉同步漏掉的 → Task 1 断言两个井共用同一个常量，Task 3 对两个井跑同一套半径/角度断言。
- **反插能插进去**：键距必须真的不等（96/128/136），否则反 180° 也能进，带电反接 → Task 1 断言三个间距。
- **带电插拔打火**：GND 先接触、VBUS 后接触，靠针长实现；模型里必须能看出长短 → Task 4 断言针的 z 顺序。
- **文档与模型漂移**：标准写 φ30、模型还是 φ26，是最贵的一种错 → Task 2 的测试读 `docs/04-接口标准.md`，Task 3/4 的测试从 `interface_spec` 取数。

---

### Task 1: 单一数值源

**Files:**
- Create: `tools/interface_spec.py`
- Create: `tools/test_interface.py`

**Interfaces:**
- 常量：`VERSION="1.0"`、`BALL_R=40.0`、`WELL_R=15.0`、`WELL_DEPTH=5.0`、`PLUG_R=14.8`、`PLUG_H=4.6`、`KEY_ANGLES=(0.0,96.0,224.0)`、`KEY_R=12.6`、`KEY_W=3.0`、`KEY_H=2.3`、`SLOT_W=3.4`、`SLOT_DEPTH=2.0`、`PAD_ANGLES=(0.0,60.0,120.0,180.0,240.0,300.0)`、`PAD_PITCH_R=9.0`、`PAD_D=2.5`、`PIN_NAMES=("VBUS","GND","TX","RX","VBUS","GND")`、`MAGNET_ANGLES=(30.0,150.0,270.0)`、`MAGNET_R=10.0`、`MAGNET_D=5.0`、`MAGNET_H=2.0`、`STEEL_D=5.0`、`STEEL_H=1.0`、`FRICTION_R=14.3`、`FRICTION_D=0.5`、`PROTO_VERSION=0x10`、`BAUD=115200`
- `pad_angles(count: int) -> tuple[float, ...]`：`count` 只接受 4 或 6，返回 `PAD_ANGLES[:count]`，否则 `ValueError`
- `pin_function(index: int) -> str`：返回 `PIN_NAMES[index]`
- `polar(radius: float, angle_deg: float) -> tuple[float, float]`：`(r·cos, r·sin)`，角度用度

- [ ] **Step 1: 写失败测试**

`tools/test_interface.py`：

```python
import math
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


# 包络：两井完全相同
eq((I.WELL_R, I.WELL_DEPTH), (15.0, 5.0), "井")
eq(round(I.WELL_R - I.PLUG_R, 3), 0.2, "单边间隙")
eq(I.PLUG_H, 4.6, "插头高")

# 键位：不等距 → 只有一种插法
eq(tuple(round((I.KEY_ANGLES[(i + 1) % 3] - I.KEY_ANGLES[i]) % 360.0, 1)
         for i in range(3)), (96.0, 128.0, 136.0), "键距")

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

# 磁铁不与键/触点撞角度
for m in I.MAGNET_ANGLES:
    for a in I.KEY_ANGLES + I.PAD_ANGLES:
        if angular_gap(m, a) < 20.0:
            raise SystemExit("FAIL: 磁铁 %.0f° 离 %.0f° 太近" % (m, a))

# 径向：焊盘外缘 < 键槽内缘
if I.PAD_PITCH_R + I.PAD_D / 2 >= I.KEY_R - I.SLOT_W / 2:
    raise SystemExit("FAIL: 焊盘与键槽径向重叠")

# 极坐标
x, y = I.polar(9.0, 90.0)
eq((round(x, 6), round(y, 6)), (0.0, 9.0), "polar")

print("PASS")
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python tools/test_interface.py`
Expected: `ModuleNotFoundError: No module named 'interface_spec'`

- [ ] **Step 3: 实现 `tools/interface_spec.py`**

按 `Interfaces` 里的常量逐条写，再写三个纯函数。`pad_angles` 的非法值报 `ValueError("only 4 or 6 pads")`；`polar` 用 `math.radians`，返回 mm 单位。

- [ ] **Step 4: 跑测试确认通过**

Run: `python tools/test_interface.py`
Expected: `PASS`

- [ ] **Step 5: 提交**

```bash
git add tools/interface_spec.py tools/test_interface.py
git commit -m "feat: freeze interface v1.0 values in one module"
```

---

### Task 2: 接口图与正式标准

**Files:**
- Create: `tools/interface_draw.py`
- Create: `docs/04-接口标准.md`
- Create: `docs/interface.svg`（由脚本生成，不手改）
- Modify: `tools/test_interface.py`
- Modify: `docs/superpowers/specs/2026-11-17-interface-standard-design.md:3`（状态改为已批准）

**Interfaces:**
- `interface_draw.svg(size: int = 420) -> str`：返回完整 SVG 文本；焊盘元素带 `class="pad"`，键带 `class="key"`，磁铁带 `class="magnet"`；尺寸文字含 `φ30.00` 与 `5.00`
- `interface_draw.write(path: str, size: int = 420) -> None`：写 UTF-8 文件
- CLI：`python tools/interface_draw.py --out docs/interface.svg`

- [ ] **Step 1: 追加失败测试**

在 `tools/test_interface.py` 的 `print("PASS")` 之前插入：

```python
# 接口图与正式标准
import interface_draw

s = interface_draw.svg()
eq(s.count('class="pad"'), 6, "图里 6 个焊盘")
eq(s.count('class="key"'), 3, "图里 3 个键")
eq(s.count('class="magnet"'), 3, "图里 3 块磁铁")
for want in ("φ30.00", "5.00"):
    if want not in s:
        raise SystemExit("FAIL: 图里缺 %s" % want)

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(root, "docs", "04-接口标准.md"), encoding="utf-8") as f:
    doc = f.read()
for want in ("v1.0", "φ80", "φ30.00", "H8", "0° / 96° / 224°", "115200 8N1",
             "0x10", "20 ± 3 N", "TX（球 → 载体）", "RX（载体 → 球）", "小端"):
    if want not in doc:
        raise SystemExit("FAIL: 标准里缺 %s" % want)
for name in I.PIN_NAMES:
    if name not in doc:
        raise SystemExit("FAIL: 标准里缺引脚 %s" % name)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python tools/test_interface.py`
Expected: `ModuleNotFoundError: No module named 'interface_draw'`

- [ ] **Step 3: 实现接口图生成器**

`tools/interface_draw.py`：从 `interface_spec` 取数，画井的俯视图（数学角度 → SVG 需 `y = cy - r·sin`）：

- `viewBox="0 0 420 420"`，中心 `(210,210)`，比例 `9 px/mm`（井 r15 → 135 px）
- 井圆 `r=15`；6 个焊盘 `r=1.25mm` 落在 `PAD_PITCH_R`；3 个键槽方块 3.4×3.4 落在 `KEY_R`；3 块磁铁 `r=2.5mm` 落在 `MAGNET_R`
- 每 60° 画一条 0° 参考线并标 `0°` 起点；标注 `φ30.00`、`深 5.00`、`0° / 96° / 224°`、引脚名
- 焊盘按 `PIN_NAMES` 标注；键用深灰、磁铁用金色、焊盘用铜色，元素类名按 `Interfaces` 写
- `main()` 读 `--out`，默认 `docs/interface.svg`；`write()` 用 `newline="\n"` 保证跨平台一致

生成：`python tools/interface_draw.py --out docs/interface.svg`

- [ ] **Step 4: 写 `docs/04-接口标准.md`**

必须是正式标准，不是设计讨论。章节顺序：

1. 标题 + 状态行：`v1.0 · 2026-11-19 · 已冻结`
2. 包络：球径 φ80、分割面 z=−12；井 φ30.00 H8、深 5.00、平面度 0.05、倒角 0.8×45°、同轴度 φ0.10；插头 φ29.60、高 4.60；单边间隙 0.20；插入力 ≤25 N、侧向保持 ≥8 N、寿命 ≥5000 次
3. 键位与防插反：0° / 96° / 224°，半径 12.6，键 3.0 × 2.3，槽 3.4 × 2.0，键在插头、槽在球；`![](interface.svg)`
4. 触点与引脚表：六位表，写清头顶 4 片、脚底 6 片；表头用 `TX（球 → 载体）`、`RX（载体 → 球）`
5. 磁吸：磁铁在插头侧 30° / 150° / 270°、r10、φ5×2；球侧钢片 φ5×1 齐平；脱开 20 ± 3 N；O 圈 r14.3、线径 0.5
6. 供电：头顶 5 V / 0.4 A，脚底 5 V / 3 A，峰值、纹波、软启动、反接保护
7. 串口：电平、`115200 8N1`、主从、帧格式 `A5 5A VER TYPE LEN PAYLOAD CRC16-CCITT`、CRC-16/CCITT-FALSE 参数（poly 0x1021、init 0xFFFF、不反射、xorout 0）、CRC 覆盖 `VER..PAYLOAD`、`LEN` 只计 payload、WHO 请求 `A5 5A 10 01 00 CRC`、类型 0x01–0x05、WHO 字段表、CMD/STATUS 载荷；注明多字节字段**小端**、所有尺寸单位 mm、井深基准是球顶切平面、两头插头互为镜像
8. 版本管理：机械包络永久冻结，改包络必须换键位；协议小版本只加字段
9. 验收：插拔 1000 次、拉脱 50 次、反插挡死、3 A 连续 10 分钟、带电热插拔 100 次
10. 变更表：一行 `v1.0 · 2026-11-19 · 冻结 · 两井统一为 φ30，键移到插头 · 球壳/吊点/全部载体`

把 spec 第 3 行的 `状态：待批准` 改为 `状态：已批准（2026-11-19）`。

- [ ] **Step 5: 跑测试确认通过**

Run: `python tools/interface_draw.py --out docs/interface.svg; python tools/test_interface.py`
Expected: 生成 SVG，然后 `PASS`

- [ ] **Step 6: 提交**

```bash
git add tools/interface_draw.py docs/04-接口标准.md docs/interface.svg tools/test_interface.py docs/superpowers/specs/2026-11-17-interface-standard-design.md
git commit -m "docs: publish frozen interface standard v1.0 with drawing"
```

---

### Task 3: 球的两个井

**Files:**
- Modify: `blender/build_ball.py:1-15`（头注释）、`blender/build_ball.py:404-441`（接口段）
- Create: `blender/tests/test_interface_ball.py`

**Interfaces:**
- 对象（`tag` 为 `top` / `bot`）：`if_floor_{tag}`、`if_pad_{tag}_{k}`、`if_slot_{tag}_{k}`、`if_steel_{tag}_{k}`；不建 `if_rim_*`（φ29.6 插头要能进 φ30 井，任何环都不能侵入通道）
- 顶部 `k=0..3`，底部 `k=0..5`；两个井的槽与钢片都是 `k=0..2`
- 不再有 `if_key_*`

- [ ] **Step 1: 写失败测试**

`blender/tests/test_interface_ball.py`：

```python
"""接口 v1.0：球的两个井。

用法：
  blender -b blender/out/ball/coreball_ball.blend --python-exit-code 1 --python blender/tests/test_interface_ball.py
"""
import math
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "tools"))
import interface_spec as I  # noqa: E402


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def at(name):
    ob = bpy.data.objects.get(name)
    if ob is None:
        fail("场景里没有 %s" % name)
    return ob


def mm(v):
    # 场景单位是米，接口标准是毫米
    return v * 1000.0


def polar(ob):
    p = ob.matrix_world.translation
    return (math.hypot(p.x, p.y) * 1000.0,
            math.degrees(math.atan2(p.y, p.x)) % 360.0)


def near(a, b, tol=0.5):
    return abs((a - b + 180.0) % 360.0 - 180.0) <= tol


FLOOR = I.BALL_R - I.WELL_DEPTH

for tag, sign, count in (("top", 1, 4), ("bot", -1, 6)):
    for k in range(count):
        name = "if_pad_%s_%d" % (tag, k)
        r, a = polar(at(name))
        if abs(r - I.PAD_PITCH_R) > 0.01:
            fail("%s 半径 %.2f" % (name, r))
        if not near(a, I.PAD_ANGLES[k]):
            fail("%s 角度 %.1f" % (name, a))
        z = at(name).matrix_world.translation.z
        if abs(mm(z) - sign * (FLOOR - 0.45)) > 0.6:
            fail("%s 没齐平井底" % name)
    if "if_pad_%s_%d" % (tag, count) in bpy.data.objects:
        fail("%s 多焊了一片" % tag)

    for k in range(3):
        name = "if_slot_%s_%d" % (tag, k)
        r, a = polar(at(name))
        if abs(r - I.KEY_R) > 0.01 or not near(a, I.KEY_ANGLES[k]):
            fail("%s 位置不对 r=%.2f a=%.1f" % (name, r, a))
        name = "if_steel_%s_%d" % (tag, k)
        r, a = polar(at(name))
        if abs(r - I.MAGNET_R) > 0.01 or not near(a, I.MAGNET_ANGLES[k]):
            fail("%s 位置不对 r=%.2f a=%.1f" % (name, r, a))

if any(n.startswith(("if_key_", "if_magnet_")) for n in bpy.data.objects.keys()):
    fail("球上出现了凸起：%s" % [n for n in bpy.data.objects.keys()
                               if n.startswith(("if_key_", "if_magnet_"))])

print("PASS")
```

- [ ] **Step 2: 用旧模型跑一次确认失败**

Run:
```
blender -b --python blender/build_ball.py -- --out blender/out/ball
blender -b blender/out/ball/coreball_ball.blend --python-exit-code 1 --python blender/tests/test_interface_ball.py
```
Expected: `FAIL: if_pad_top_0 半径 7.80`（旧模型焊盘半径按 `radius*0.6` 算、角度从 45° 起；说明井还是旧的两套）

- [ ] **Step 3: 改 `build_ball.py`**

- 顶部加 `sys.path` 指向 `../tools`，`import interface_spec as I`
- 头注释第 5、11 行改成：顶部与底部同一套 φ30 井、键在载体、球上只有槽与钢片
- 接口段用单一常量：`IF_R = I.WELL_R`、`IF_DEPTH = I.WELL_DEPTH`；删掉 `IF_R_TOP/IF_R_BOT`
- `interface(tag, sign, count)`：
  - 井底片 `if_floor_{tag}` 加厚到 2.4（中心 `zf - sign*1.2`），半径 `IF_R - 0.05`（φ29.9，盖住槽的外缘），给 2.0 深的槽留材料
  - 电池上移到 z=−26.5（原 −27 会与加厚后的底井片重叠 0.4 mm）
  - 焊盘 `if_pad_{tag}_{k}` 用 `I.PAD_ANGLES[k]`、`I.PAD_PITCH_R`、半径 `I.PAD_D/2`；中心 `zf - sign*0.45`、深 0.9 → 顶面正好在井底
  - 槽：先造 3.4×3.4×2.6 的切块（从槽底向上多 0.6 穿出井底，避免切块顶面与井底片顶面共面——共面时 EXACT boolean 会留一层盖面），`boolean_diff` 切井底片（切块会被删掉）；再在槽底放 3.0×3.0×0.2 的深色标记 `if_slot_{tag}_{k}`，中心 `zf - sign*(2.0 - 0.1)`——它既是渲染里的凹槽底，也是测试的锚点
  - 钢片 `if_steel_{tag}_{k}`：`cyl` 半径 `I.STEEL_D/2`、厚 `I.STEEL_H`，中心 `zf - sign*I.STEEL_H/2` 与井底齐平；位置 `polar(I.MAGNET_R, I.MAGNET_ANGLES[k])`
  - 删除原来的 `if_key_{tag}_{k}`
  - 井口倒角（0.8×45°）只写在标准里，模型不建环——任何进入井口的几何体都会挡住 φ29.6 插头；测试断言 `if_rim_*` 不存在，并检查球壳在井口通道内没有材料
- 调用改为 `interface("top", 1, 4)` / `interface("bot", -1, 6)`

- [ ] **Step 4: 重建并跑测试**

Run:
```
blender -b --python blender/build_ball.py -- --out blender/out/ball
blender -b blender/out/ball/coreball_ball.blend --python-exit-code 1 --python blender/tests/test_interface_ball.py
```
Expected: `PASS`

- [ ] **Step 5: 提交**

```bash
git add blender/build_ball.py blender/tests/test_interface_ball.py blender/out/ball/coreball_ball.blend
git commit -m "feat: unify ball wells to phi30 with slots and steel plates"
```

---

### Task 4: 吊点插头（含工位场景里的那只）

**Files:**
- Modify: `blender/build_hub.py:198-214`
- Modify: `blender/build_desk_rig.py:319-327`
- Modify: `blender/build_anim.py:77`
- Create: `blender/tests/test_interface_hub.py`

**Interfaces:**
- `hub_plug`：插入井里的鼻子，φ29.6 × 4.6，顶面在球顶 `BOT-14`
- `hub_plug_body`：肩部，φ34 × 12，坐在球面之上
- `plug_key_{k}`：3 个，半径 `KEY_R`，角度 `KEY_ANGLES[k]`，落在鼻子高度内
- `plug_magnet_{k}`：3 个，半径 `MAGNET_R`，角度 `MAGNET_ANGLES[k]`，嵌在鼻子端面
- `plug_pin_{k}`：4 个，半径 `PAD_PITCH_R`，角度 `PAD_ANGLES[k]`，从鼻子端面往下伸；GND 最长、VBUS 最短
- `friction_ring`：鼻子中段 O 圈，中心线 `FRICTION_R`，线径 `FRICTION_D`

- [ ] **Step 1: 写失败测试**

`blender/tests/test_interface_hub.py`：

```python
"""接口 v1.0：吊点插头。

用法：
  blender -b blender/out/hub/coreball_hub.blend --python-exit-code 1 --python blender/tests/test_interface_hub.py
"""
import math
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "tools"))
import interface_spec as I  # noqa: E402


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def at(name):
    ob = bpy.data.objects.get(name)
    if ob is None:
        fail("场景里没有 %s" % name)
    return ob


def mm(v):
    # 场景单位是米，接口标准是毫米
    return v * 1000.0


def radial(ob, c):
    # 量真实顶点半径；bound_box 的角点会把半径放大 sqrt(2)
    pts = [ob.matrix_world @ v.co for v in ob.data.vertices]
    return max(math.hypot(p.x - c.x, p.y - c.y) for p in pts) * 1000.0


def near(a, b, tol=0.5):
    return abs((a - b + 180.0) % 360.0 - 180.0) <= tol


plug = at("hub_plug")
c = plug.matrix_world.translation.copy()

# 鼻子 φ29.6
r = radial(plug, c)
if abs(r - I.PLUG_R) > 0.1:
    fail("鼻子半径 %.2f，应为 %.2f" % (r, I.PLUG_R))
if abs(mm(plug.dimensions.z) - I.PLUG_H) > 0.05:
    fail("鼻子高度 %.2f，应为 %.2f" % (mm(plug.dimensions.z), I.PLUG_H))

# 键、磁铁、针全部在插头上
face_mm = mm(c.z) - I.PLUG_H / 2
for k in range(3):
    p = at("plug_key_%d" % k).matrix_world.translation
    if abs(math.hypot(p.x - c.x, p.y - c.y) * 1000.0 - I.KEY_R) > 0.05:
        fail("plug_key_%d 半径不对" % k)
    if not near(math.degrees(math.atan2(p.y - c.y, p.x - c.x)) % 360.0,
                I.KEY_ANGLES[k]):
        fail("plug_key_%d 角度不对" % k)
    if abs(mm(p.z) - (face_mm - I.KEY_H / 2)) > 0.2:
        fail("plug_key_%d 没从插头端面伸出，够不到键槽" % k)

for k in range(3):
    p = at("plug_magnet_%d" % k).matrix_world.translation
    if abs(math.hypot(p.x - c.x, p.y - c.y) * 1000.0 - I.MAGNET_R) > 0.05:
        fail("plug_magnet_%d 半径不对" % k)
    if not near(math.degrees(math.atan2(p.y - c.y, p.x - c.x)) % 360.0,
                I.MAGNET_ANGLES[k]):
        fail("plug_magnet_%d 角度不对" % k)

heights = {}
for k in range(4):
    p = at("plug_pin_%d" % k).matrix_world.translation
    if abs(math.hypot(p.x - c.x, p.y - c.y) * 1000.0 - I.PAD_PITCH_R) > 0.05:
        fail("plug_pin_%d 半径不对" % k)
    if not near(math.degrees(math.atan2(p.y - c.y, p.x - c.x)) % 360.0,
                I.PAD_ANGLES[k]):
        fail("plug_pin_%d 角度不对" % k)
    heights[I.PIN_NAMES[k]] = p.z

# 先接地后上电：GND 最长（最低）→ TX/RX → VBUS 最短
if not (heights["GND"] < heights["TX"] < heights["VBUS"]):
    fail("针长顺序不对：%s" % heights)
if abs(heights["TX"] - heights["RX"]) > 0.001:
    fail("TX/RX 应该齐平：%s" % heights)

ring = at("friction_ring")
if abs(radial(ring, c) - (I.FRICTION_R + I.FRICTION_D / 2)) > 0.1:
    fail("摩擦环半径不对")

if any(n.startswith("hub_key_") for n in bpy.data.objects.keys()):
    fail("旧键还在")

print("PASS")
```

- [ ] **Step 2: 用旧模型跑一次确认失败**

Run:
```
blender -b --python blender/build_hub.py -- --out blender/out/hub
blender -b blender/out/hub/coreball_hub.blend --python-exit-code 1 --python blender/tests/test_interface_hub.py
```
Expected: `FAIL: 鼻子半径 11.50，应为 14.80`

- [ ] **Step 3: 改 `build_hub.py`**

- 顶部 import `interface_spec as I`（`HERE` 已存在，把 `tools` 加进 `sys.path`）
- 保留 `BOT` 作为球顶参考：球顶 = `BOT - 14`（球心 `BOT-54`、半径 40）
- 删掉原 `hub_plug` 的 11.5×12，改为两只：
  - `hub_plug`：`cyl(..., (H.x,H.y,BOT-16.3), I.PLUG_R, I.PLUG_H, ...)`，鼻子跨 `BOT-18.6 .. BOT-14`
  - `hub_plug_body`：`cyl(..., (H.x,H.y,BOT-8), 17, 12, ...)`，肩部跨 `BOT-14 .. BOT-2`
- `plug_key_{k}`：`box` `I.KEY_W`×`I.KEY_W`×`I.KEY_H`，位置 `(H.x + KEY_R·cos, H.y + KEY_R·sin, BOT-18.6 - I.KEY_H/2)`；用 `I.polar`。键必须从插头端面往井里伸（端面 `BOT-18.6`），不能埋在鼻子里——`KEY_R + KEY_W/2 = 14.1 < PLUG_R`，放在鼻子中心就会整段消失
- `plug_magnet_{k}`：`cyl` 半径 `I.MAGNET_D/2`、厚 `I.MAGNET_H`，中心 z=`BOT-18.6+I.MAGNET_H/2`（嵌进端面、底面齐平）
- `plug_pin_{k}`：`cyl` 半径 0.75（针筒 φ1.5）、长度 GND 1.8 / TX·RX 1.3 / VBUS 0.8；中心 z = `BOT-18.6 - 长度/2`，让 GND 最低。长度表示**未压缩**的 pogo 行程，插入后会压回；hub 场景的球是实心示意球，针尖埋进球体属预期，加注释说明
- `friction_ring`：`torus(..., (H.x,H.y,BOT-16.3), I.FRICTION_R, I.FRICTION_D/2, ...)`（鼻子中段，自由外径 15.15 对井壁过盈 0.15）
- `breakaway` 外移成可见环：原来 14.5/1.8 会被 φ34 肩部整个盖住；改为中心线 18.2、minor 0.8，仍留在球顶平面 `BOT-14`
- `build_anim.py` 的 `YAW_NAMES` 补进 `hub_plug_body`、`plug_magnet_0..2`、`plug_pin_0..3`、`friction_ring`、`breakaway`（否则偏航时它们不跟转）

- [ ] **Step 4: 改 `build_desk_rig.py` 的同一只插头**

工位场景里 `plug_z` 是插头肩部中心（跨 `plug_z-6 .. plug_z+6`）。球顶必须从真实球心推导：`BALL_TOP = BALL_POS[2] + I.BALL_R`（=1340），`plug_z = BALL_TOP + 6`（即 `CARRIAGE_Z - 51`，不是 -52）——用 `plug_z-6` 当球顶会低 1 mm，插头端面落到井底下方 0.6、键穿过井底片。按 Task 3/4 同样的公式改：`hub_plug` 鼻子（中心 `BALL_TOP - I.PLUG_H/2`）、`hub_plug_body` 肩（中心 `plug_z`）、`plug_key`（从端面 `BALL_TOP - I.PLUG_H` 往下伸 `KEY_H`）、`plug_magnet`、`plug_pin`（未压缩长度，加注释）、`friction_ring`；`breakaway_ring` 同样外移到中心线 18.2、minor 0.8、z=`BALL_TOP`；删掉旧的 11.5 插头与 9.0 半径的键。不要改 `PREFIX`（`if_` 前缀照旧能导入球体）。

- [ ] **Step 5: 重建并跑测试**

Run:
```
blender -b --python blender/build_hub.py -- --out blender/out/hub
blender -b blender/out/hub/coreball_hub.blend --python-exit-code 1 --python blender/tests/test_interface_hub.py
```
Expected: `PASS`

- [ ] **Step 6: 提交**

```bash
git add blender/build_hub.py blender/build_desk_rig.py blender/build_anim.py blender/tests/test_interface_hub.py blender/out/hub/coreball_hub.blend
git commit -m "feat: hub plug matches frozen interface (keys, magnets, pins)"
```

---

### Task 5: 同步既有文档

**Files:**
- Modify: `docs/01-设计决定.md`（决定 10；末尾追加 25、26）
- Modify: `docs/03-参数表.md:20-21, 153-160`
- Modify: `TODO.md`

- [ ] **Step 1: 改参数表**

- 第 20 行 → `| 顶部接口 | φ30 井，深 5，4 触点 | 与底部同一标准 |`
- 第 21 行 → `| 底部接口 | φ30 井，深 5，6 触点 | 与顶部同一标准 |`
- 在接口两行后补：`| 接口键位 | 3 键 0° / 96° / 224°，r12.6 | 键在载体，槽在球 |`、`| 触点 | 6 位 60° 均布，r9.0，焊盘 φ2.5 | 头顶只用前 4 位 |`、`| 磁吸 | 3 磁铁 30° / 150° / 270°，r10 | 球侧只放钢片 |`、`| 串口 | 115200 8N1，3.3 V | 球为主，载体自述 |`
- 「待定」里删掉 `- 接口的引脚定义与 ID 电阻值` 与 `- 载体侧的插头结构（三锥销的锥度）`

- [ ] **Step 2: 改设计决定**

- 决定 10 的「两触点」改为「四片触点（VBUS / GND / TX / RX）」
- 末尾追加两条，格式与前面一致（决定 / 为什么 / 代价）：
  - **25 一套接口，两种焊装**：两个井都 φ30、同一副键；头顶载体只焊 4 片，脚底焊 6 片。为什么：只有一种井、一张图；顶部与底部插头互为镜像。代价：头顶井 +4 mm，两类载体各备一种镜向插头。
  - **26 数据线用串口，不用 I2C**：为什么：头顶要控制偏航和伸缩，必须双向；「自我介绍」天然是一段话。代价：每根线只能一对一，不能挂菊花链。

- [ ] **Step 3: 改 TODO**

P0 第 1 条的四个复选框改成 `[x]`，并在标题下加一行 `已冻结：接口标准 v1.0（2026-11-19，docs/04-接口标准.md）`。

- [ ] **Step 4: 检查没有旧数字残留**

Run: `git grep -n -E "φ26|13\.0|IF_R_TOP|11\.5" -- docs blender ":(exclude)blender/out"`
Expected: 无输出（`11.5` 若在无关尺寸里出现，人工确认后保留）

- [ ] **Step 5: 提交**

```bash
git add docs/01-设计决定.md docs/03-参数表.md TODO.md
git commit -m "docs: sync decisions and parameter table with interface v1.0"
```

---

### Task 6: 全量重建与回归

**Files:**
- Modify: `blender/out/ball/coreball_ball.blend`、`blender/out/hub/coreball_hub.blend`、`blender/out/rig/coreball_rig.blend`、`blender/out/cmd/coreball_command.blend`（重建产物）

- [ ] **Step 1: 按依赖顺序重建**

```
blender -b --python blender/build_ball.py -- --out blender/out/ball
blender -b --python blender/build_hub.py -- --out blender/out/hub
blender -b --python blender/build_desk_rig.py -- --out blender/out/rig
blender -b --python blender/build_command.py -- --out blender/out/cmd
```
Expected: 四条都正常结束；`build_desk_rig.py` 打印 `appended ball objects:` 且数量与之前同量级（新对象只多了 6 个槽标记 + 6 片钢片）

- [ ] **Step 2: 跑全部接口测试**

```
python tools/test_interface.py
blender -b blender/out/ball/coreball_ball.blend --python-exit-code 1 --python blender/tests/test_interface_ball.py
blender -b blender/out/hub/coreball_hub.blend --python-exit-code 1 --python blender/tests/test_interface_hub.py
```
Expected: 三次 `PASS`

- [ ] **Step 3: 跑既有回归**

```
python tools/test_body.py
python tools/test_brain.py
blender -b blender/out/cmd/coreball_command.blend --python-exit-code 1 --python blender/tests/test_command.py
blender -b blender/out/cmd/coreball_command.blend --python-exit-code 1 --python blender/tests/test_intent.py
blender -b blender/out/cmd/coreball_command.blend --python-exit-code 1 --python blender/tests/test_bodies.py
```
Expected: 五次 `PASS`

- [ ] **Step 4: 肉眼一眼**

打开 `blender/out/ball/coreball_ball.blend`：两个井看起来一样大；球上没有任何凸起；井底能看见 6 点（上 4 下 6）、3 条槽、3 片钢片。打开 `blender/out/hub/coreball_hub.blend`：插头有 3 个键、3 块磁铁、4 根针、一圈 O 圈。

- [ ] **Step 5: 提交重建产物**

```bash
git add blender/out/ball/coreball_ball.blend blender/out/hub/coreball_hub.blend blender/out/rig/coreball_rig.blend blender/out/cmd/coreball_command.blend
git commit -m "chore: rebuild scenes with frozen interface v1.0"
```

---

## 自查

**Spec 覆盖：**

| Spec 节 | 落在哪 |
|---|---|
| §8.1 包络 | Task 1 常量、Task 2 标准、Task 3/4 模型 |
| §8.2 键位 | Task 1 间距测试、Task 2 图、Task 3 槽、Task 4 键 |
| §8.3 触点 | Task 1 角度/半径、Task 3 焊盘数量与位置 |
| §8.4 引脚 | Task 1 `PIN_NAMES`、Task 2 表、Task 4 针角度 |
| §8.5 磁吸 | Task 1 角距测试、Task 3 钢片、Task 4 磁铁与 O 圈 |
| §8.6 供电 | Task 2 标准 §6 |
| §8.7 串口 | Task 2 标准 §7（本计划只冻结文档，不做固件） |
| §8.8 版本管理 | Task 2 变更表、spec 状态行 |
| §10 与现状差异 | Task 3/4/5 |
| §11 验收 | Task 2 标准 §9（物理验收，自动化只覆盖几何） |

**Review Focus 的五条** → Task 3（球上无凸起、两井同半径）、Task 1（键距、磁铁角距）、Task 4（针长顺序）、Task 2（文档数值）。

**已知不做：** 协议固件、物理样件、SMT 焊盘阵列——spec §12 明确留给实现者；本计划只保证「图纸、模型、测试」三者一致。
