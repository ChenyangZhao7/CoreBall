# 交互层实现计划（键盘 → 意图 → 动作）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在已建好的指挥场景里加「人 + 命名点 + 意图协议 + 动作表 + 键盘/网络驱动 + 表情/朝向」，让球能被命令着动，而不是只能被拖。

**Architecture:** `actions.json` 是可读的动作表；UDP 4590 收意图（键盘驱动也走同一个队列）；Blender 主线程用 timer 按 S 曲线执行移动；HUD 显示最近意图与状态。识别进程以后接，协议不变。

**Tech Stack:** Blender 4.5 Python、标准库 `socket`/`threading`/`queue`/`json`。

**Spec:** `docs/superpowers/specs/2026-11-17-interaction-design.md`

## Global Constraints

- 不新增第三方依赖（Blender 自带 Python + 标准库）。
- 所有单位仍然是 Blender 米 / 界面毫米，只在边界转换。
- 意图协议：UDP `127.0.0.1:4590`，一行一个 JSON。
- 动作表：`blender/actions.json`，用户可改，代码不得写死动作名。
- 移动必须过 S 曲线、禁区回弹、张力检查；不准瞬移。
- 后台线程只碰队列，绝不碰 `bpy`。
- 不是 git 仓库以外的限制：本仓库已初始化 git，用 feature 分支。
- 测试：`& $B -b blender\out\cmd\coreball_command.blend --python-exit-code 1 --python blender\tests\test_intent.py`

## Review Focus

- `actions.json` 缺字段/写坏：必须报错但不崩，HUD 写「动作表坏了」。
- UDP 收到非 JSON / 超大包：丢弃并继续监听，不崩线程。
- 移动途中来新指令：新指令覆盖旧的，从当前位置重新起算，不跳变。
- `hesitate` 期间来 `stop`：必须立刻取消。
- 目标点被用户拖到禁区里：落点仍要在边界上。

---

### Task 1: 场景里的人与命名点

**Files:** `blender/build_command.py`、`blender/tests/test_intent.py`

**Interfaces:** `PERSON_HEAD`（空物体，人的头）、`TGT_HOME`、`TGT_NEAR`（空物体，可拖）

- [ ] 测试：三个对象存在；`PERSON_HEAD` 在 `(0, 890, 1250)`±5mm；`TGT_NEAR` 在 `(-380,520,1300)`±1mm；`TGT_HOME` 在 `(-430,760,1420)`±1mm。
- [ ] 实现：在 `build_command.py` 里加人体（躯干胶囊 + 头球 + 视线箭头）和两个目标空物体；跑 build；测试从 FAIL 到 PASS。

### Task 2: 动作表与目标解析

**Files:** `blender/actions.json`、`blender/cmd_runtime.py`、`blender/tests/test_intent.py`

**Interfaces:**
- `load_actions(path) -> dict`（坏文件抛 `ValueError`）
- `resolve(actions, src, key) -> str | None`
- `intent_point(actions, name, points, current_mm) -> [x,y,z] | None`（`target` 查命名点；`delta` 相加）

- [ ] 测试：`key "1" → "come"`；`"9" → None`；`come` 解析到 `TGT_NEAR`；`up` 在当前点上加 `[0,0,120]`；`actions.json` 语法坏时抛 `ValueError`。
- [ ] 实现：建动作表（spec §3.2 的版本）；三个纯函数。
- [ ] 测试 PASS。

### Task 3: 移动引擎（犹豫 + S 曲线 + 回弹）

**Files:** `blender/cmd_runtime.py`、`blender/tests/test_intent.py`

**Interfaces:** `move_profile(d, vmax, rebound) -> {T, pos(t)}`；`MOVE` 状态 + `start_move(p0, p1, style, now)`

- [ ] 测试：`d=1139, vmax=356` 时 `T≈6.0`、峰值 `356±2`、`pos(0.5)≈6`；`rebound=4` 时最大超出 `3–5mm`；`start_move` 在 `hesitate=0.35` 时前 0.35s 位置不变。
- [ ] 实现：五次多项式 + 阻尼回落；timer 每帧更新 `CMD_TARGET`。
- [ ] 测试 PASS。

### Task 4: 意图通道（UDP + 键盘）

**Files:** `blender/cmd_runtime.py`、`blender/tests/test_intent.py`

**Interfaces:** `start_udp(port, q)`；`handle_intent(msg)`；keymap 用 `bpy.app.timers` 读一个全局按键缓冲

- [ ] 测试：起一个监听在随机端口，发 `{"intent":"come"}`，1 秒内队列里取到；发 `not json` 不崩且队列为空；发未知意图时 `STATE["last"] == "不认识的指令"`。
- [ ] 实现：后台线程 + `queue.Queue`；键盘用 `bpy.types.SpaceView3D` 的 keymap 或 `event` 钩子（取最简可行）。
- [ ] 测试 PASS。

### Task 5: 表情、朝向、HUD 与收尾

**Files:** `blender/cmd_runtime.py`、`blender/build_command.py`、`README.md`

**Interfaces:** `face_person()`（转 `ball_root` 朝 `PERSON_HEAD`）；`set_expression(name)`（`idle` / `listening` / `acting`）

- [ ] 测试：`face_person` 在球位于人左侧时 yaw 约 +90°；`set_expression` 改的是球灯带材质的 emission 强度（读回值验证）。
- [ ] 实现：材质发光 + `ball_root.rotation_euler.z`；HUD 加一行「指令：xxx」。
- [ ] 端到端：键盘 1/2/3/4/5/0 全部生效；`echo` 一条 UDP 也生效；README 补一行。
- [ ] 测试 PASS。

## 自查

- spec 的 7 条完成标准 → Task 1（人/命名点）、2（可改动作表）、3（犹豫/回弹）、4（UDP/未知指令）、5（表情/朝向/禁区）。
- Review Focus 五条 → Task 2（坏表）、4（坏包/未知）、3（移动中覆盖）、3（stop）、3（落点夹紧）。
- 已知偏离：spec 说 `detour` 沿用 `plan.py` 的 A*；本期直线 + 禁区推离，`detour` 只保留参数不生效。Ruling 记入 ledger。
