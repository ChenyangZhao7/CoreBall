# Blender 三维指挥 · 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Blender 里拖一个控制空物体，球和吊点实时跟随、四根线实时重算，角上面板显示线长与张力，禁区自动回弹。

**Architecture:** 不重建模型。`build_command.py` 打开现成的 `coreball_rig.blend`，加控制层（空物体 + 父子关系 + 原生 Hook），另存为指挥场景。`cmd_runtime.py` 在启动时注册 depsgraph handler（算张力、弹禁区）和 2D 绘制 handler（用 `blf` 画面板）。张力数学直接 `import tools/tension.py`，不复制。

**Tech Stack:** Blender 4.5 Python API（`bpy`、`blf`）、现有 `tools/tension.py`。

**Spec:** `docs/superpowers/specs/2026-11-17-blender-command-design.md`

## Global Constraints

- Blender：`C:\Users\21165\Apps\blender-4.5.16\blender-4.5.16-windows-x64\blender.exe`
- Blender 场景内部单位是**米**；`tools/tension.py` 用**毫米**。只在边界转换，不混用。
- 输入场景：`blender/out/rig/coreball_rig.blend`（已有，不改它）。
- 产物：`blender/out/cmd/coreball_command.blend`。
- 不新增插件、不新增依赖、不复制模型对象。
- 吊点比球心高 **160 mm**（`HUB_GAP`）；线挂在吊点的 `lug_1..4` 上。
- 禁区：脖子 `(0, 890)` mm、半径 210 mm，作用于**球心**。
- 面板数字 = `tension.py` 在**吊点**位置算出的结果（因为线挂在吊点）。
- 本目录**不是 git 仓库**：不执行 git。
- 测试命令：`& $B -b blender\out\cmd\coreball_command.blend --python-exit-code 1 --python blender\tests\test_command.py`

## Review Focus

- **`CMD_TARGET` 拖到禁区圆心**：推离方向未定义 → 固定 +X，不产生 NaN。
- **吊点正好在锚点正下方**：零空间退化，`solve()` 抛异常 → 面板写「几何退化」，不让 handler 崩。
- **拖动时每帧写 location**：与 depsgraph handler 形成死循环 → 用重入标志挡住。
- **面板路径**：从 `.bat` 启动时工作目录不定 → 所有路径用 `__file__` 解析。
- **Hook 目标为空**（对象被改名/删除）：`.blend` 仍能打开 → 构建时缺对象要直接报错退出，不留半成品。

---

### Task 1: 控制层与父子关系

**Files:**
- Create: `blender/build_command.py`
- Create: `blender/tests/test_command.py`

**Interfaces:**
- Consumes: `coreball_rig.blend` 里的 `ball_root`、`04_吊点` 集合（25 个对象）
- Produces: `CMD_TARGET`（空物体，球心）、`HUB_ROOT`（空物体，球心 +160 mm）；`ball_root.parent = CMD_TARGET`；`04_吊点` 全部对象父级为 `HUB_ROOT`

- [ ] **Step 1: 写失败的测试**

`blender/tests/test_command.py`：

```python
import bpy, sys

def fail(msg):
    print("FAIL:", msg); sys.exit(1)

if "CMD_TARGET" not in bpy.data.objects: fail("没有 CMD_TARGET")
if "HUB_ROOT" not in bpy.data.objects: fail("没有 HUB_ROOT")
t = bpy.data.objects["CMD_TARGET"]
if bpy.data.objects["ball_root"].parent != t: fail("ball_root 没挂到 CMD_TARGET")
hub_objs = list(bpy.data.collections["04_吊点"].objects)
bad = [o.name for o in hub_objs if o.parent != bpy.data.objects["HUB_ROOT"]]
if bad: fail("这些吊点对象没挂到 HUB_ROOT: %s" % bad)

before = bpy.data.objects["ball_root"].matrix_world.translation.copy()
hp = bpy.data.objects["hub_plate"].matrix_world.translation.copy()
t.location.x += 0.2
bpy.context.view_layer.update()
after = bpy.data.objects["ball_root"].matrix_world.translation
hp2 = bpy.data.objects["hub_plate"].matrix_world.translation
if abs((after - before).x - 0.2) > 1e-5: fail("球没跟着走")
if abs((hp2 - hp).x - 0.2) > 1e-5: fail("吊点没跟着走")
print("PASS")
```

- [ ] **Step 2: 运行，确认失败**

Run: `& $B -b blender\out\rig\coreball_rig.blend --python-exit-code 1 --python blender\tests\test_command.py`
Expected: `FAIL: 没有 CMD_TARGET`

- [ ] **Step 3: 实现 `build_command.py`**

流程：`open_mainfile(rig)` → 建 `CMD_TARGET`（`empty_display_type='SPHERE'`、`empty_display_size=0.06`，位置 `ball_root` 世界坐标）→ 建 `HUB_ROOT`（同位置 +0.16 Z）→ `ball_root.parent = CMD_TARGET` 并设 `matrix_parent_inverse = target.matrix_world.inverted()` → 遍历 `04_吊点` 按同样方式挂到 `HUB_ROOT` → `save_as_mainfile(out/cmd/coreball_command.blend)`。参数用 `-- --out <dir>`，默认 `blender/out/cmd`。

- [ ] **Step 4: 构建并跑测试**

Run: `& $B -b --python blender\build_command.py -- --out blender\out\cmd`
Run: `& $B -b blender\out\cmd\coreball_command.blend --python-exit-code 1 --python blender\tests\test_command.py`
Expected: `PASS`

---

### Task 2: 四线与供电线跟随

**Files:**
- Modify: `blender/build_command.py`
- Modify: `blender/tests/test_command.py`

**Interfaces:**
- Consumes: Task 1 的 `CMD_TARGET`、`HUB_ROOT`
- Produces: `cable_1..4` 各一个 `HOOK` 修改器，`object = lug_1..4`，`vertex_indices = {1}`；`wire_1` 索引 `{1}`、`wire_2` 索引 `{0}` hook 到 `tether_sheave`

- [ ] **Step 1: 加测试**

在 `test_command.py` 的 `PASS` 之前追加：

```python
def endpoint_world(name, idx):
    ob = bpy.data.objects[name]
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    cu = ev.to_curve(dg)
    return ev.matrix_world @ cu.splines[0].points[idx].co.xyz

for i in range(1, 5):
    ob = bpy.data.objects["cable_%d" % i]
    hooks = [m for m in ob.modifiers if m.type == 'HOOK']
    if not hooks or hooks[0].object.name != "lug_%d" % i: fail("cable_%d 没 hook 到 lug_%d" % (i, i))

bpy.data.objects["CMD_TARGET"].location.y -= 0.25
bpy.context.view_layer.update()
for i in range(1, 5):
    a = endpoint_world("cable_%d" % i, 1)
    b = bpy.data.objects["lug_%d" % i].matrix_world.translation
    if (a - b).length > 0.0005: fail("cable_%d 末端离挂耳 %.2f mm" % (i, (a - b).length * 1000))
```

- [ ] **Step 2: 运行，确认失败**

Run: test on the Task 1 blend
Expected: `FAIL: cable_1 没 hook 到 lug_1`

- [ ] **Step 3: 实现**

建 hook：`m = ob.modifiers.new("hook_lug", 'HOOK')`；`m.object = lug`；`m.matrix_inverse = lug.matrix_world.inverted()`；`m.vertex_indices_set([1])`。供电线同理。若 `bpy.data.objects[名]` 不存在，`raise` 并退出（不留半成品）。

- [ ] **Step 4: 重建并跑测试**

Expected: `PASS`

---

### Task 3: 张力数学与面板文本

**Files:**
- Create: `blender/cmd_runtime.py`
- Modify: `blender/tests/test_command.py`

**Interfaces:**
- Consumes: `tools/tension.py` 的 `solve(point)->{lengths,T,margin,closed}`；`HUB_ROOT`
- Produces:
  - `hud_lines(hub_mm: tuple, res: dict) -> list[str]`（第一行坐标，第二行四根线长，第三行四根张力，第四行最松与状态）
  - `status_text(res) -> str`：`力封闭正常` / `力封闭失效（最松 x.xx N）` / `几何退化`
  - `status_color(res) -> (r, g, b, a)`：正常绿、失效红、退化黄
  - `register()`：注册 handler（Task 4 用）

- [ ] **Step 1: 加测试**

```python
from cmd_runtime import hud_lines, status_text, status_color
res = T.solve((-380.0, 520.0, 1460.0))
lines = hud_lines((-380.0, 520.0, 1460.0), res)
joined = "\n".join(lines)
for want in ["-380", "520", "1460", "555", "1210", "481", "1071", "3.69", "2.05"]:
    if want not in joined: fail("面板缺 %s" % want)
bad = T.solve((-700.0, 300.0, 1150.0 + 160))
if "失效" not in status_text(bad): fail("失效没写出来")
if status_color(bad)[0] < 0.6: fail("失效没变红")
```

- [ ] **Step 2: 运行，确认失败**

Expected: `ModuleNotFoundError: cmd_runtime`（测试里 `sys.path.insert(0, blender 目录)`）

- [ ] **Step 3: 实现**

`cmd_runtime.py` 顶部用 `pathlib.Path(__file__)` 解析 `../tools` 并 `sys.path.insert`，`import tension as T`。`hud_lines` 用 `"%7.0f"` 对齐。`status_color` 返回 `(0.35,0.78,0.52,1)` / `(0.85,0.30,0.28,1)` / `(0.85,0.70,0.30,1)`。

- [ ] **Step 4: 跑测试**

Expected: `PASS`

---

### Task 4: 禁区回弹与两个 handler

**Files:**
- Modify: `blender/cmd_runtime.py`
- Modify: `blender/tests/test_command.py`

**Interfaces:**
- Produces: `clamp_ball(p_mm) -> p_mm`；`register()` 注册 `depsgraph_update_post` 与 `SpaceView3D.draw_handler_add`；模块级 `STATE` 缓存 `{target, hub, res, blocked}`

- [ ] **Step 1: 加测试**

```python
from cmd_runtime import clamp_ball
a = clamp_ball((0.0, 890.0, 1300.0))
if abs((a[0]**2 + (a[1]-890.0)**2) ** 0.5 - 210.0) > 1e-6: fail("轴线没推到 210")
b = clamp_ball((-380.0, 520.0, 1300.0))
if b != (-380.0, 520.0, 1300.0): fail("禁区外被误推")
```

- [ ] **Step 2: 运行，确认失败**

Expected: `ImportError: cannot import name 'clamp_ball'`

- [ ] **Step 3: 实现**

`clamp_ball`：半径 < 210 时按比例推到 210；`r < 1e-6` 时用 +X。`depsgraph_update_post` handler：读 `CMD_TARGET` 世界坐标（米→毫米）、夹禁区、写回（用 `_busy` 标志防重入）；读 `HUB_ROOT` 世界坐标，`T.solve` 包 `try/except`（退化时置 `res=None`）；写 `STATE`；节流 50 ms。`draw` handler：`blf.size(font, 13)`、逐行 `blf.position` / `blf.draw`，颜色取 `status_color`。

- [ ] **Step 4: 跑测试**

Expected: `PASS`

---

### Task 5: 启动器、README 与端到端

**Files:**
- Create: `blender/指挥.bat`
- Modify: `README.md`
- Modify: `blender/tests/test_command.py`（最终把全部断言串起来）

**Interfaces:**
- Consumes: 以上全部
- Produces: 双击即用的入口

- [ ] **Step 1: 写启动器**

```bat
@echo off
set "B=C:\Users\21165\Apps\blender-4.5.16\blender-4.5.16-windows-x64\blender.exe"
start "" "%B%" "%~dp0out\cmd\coreball_command.blend" --python "%~dp0cmd_runtime.py"
```

- [ ] **Step 2: 更新 README**

目录里加一行：

```
blender/
  build_command.py     指挥场景：拖 CMD_TARGET，四线实时跟随
  cmd_runtime.py       面板与禁区（由 指挥.bat 启动）
  指挥.bat             双击进入指挥场景
```

- [ ] **Step 3: 全量无头测试**

Run: `& $B -b --python blender\build_command.py -- --out blender\out\cmd`
Run: `& $B -b blender\out\cmd\coreball_command.blend --python-exit-code 1 --python blender\tests\test_command.py`
Expected: `PASS`

- [ ] **Step 4: 手动验收**

1. 双击 `blender\指挥.bat`，Blender 打开。
2. 选 `CMD_TARGET`，`G` 拖动：球、吊点、四线跟随；面板数字实时变。
3. 默认位读数应为 `555 / 1210 / 481 / 1071 mm`、`3.69 / 2.05 / 2.76 / 2.05 N`、最松 `2.05 N`（吊点 `-380, 520, 1460`）。
4. 拖到球心 `(-700, 300, 1150)`：面板变红，写「力封闭失效」。
5. 拖到 `(0, 890, 1300)`：自动弹到 `(210, 890, 1300)`，写「安全层否决」。
6. 中键转视角、滚轮、`Numpad 0` 进相机视角，线不穿帮。

---

## 自查

- 设计六条目标 → Task 1（拖）、2（线跟随）、3（面板）、4（禁区/刷新）、5（入口）。
- Review Focus 五条 → 轴线（Task 4）、退化（Task 3 的 try/except + Task 4）、重入（Task 4）、路径（Task 3 用 `__file__`）、缺对象（Task 2 直接 raise）。
- 数字：默认吊点 `(-380,520,1460)` 的 `tension.py` 输出 = `555.5/1209.9/480.6/1071.2`、`3.69/2.05/2.76/2.05`、余量 `2.05`。

## 与已批准设计的一处修正

设计里完成标准第 2 条写的是「球心 `(-380,520,1300)` 的 648/1255/585/1122」。但四根线物理上挂在**吊点**（球心 +160 mm）的挂耳上，按球心算会低估约 90–160 mm、张力差 30%。实现按**吊点**算，所以默认位读数是 `555/1210/481/1071`。这是修正，不是跑偏。
