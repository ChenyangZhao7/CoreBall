# 一个核心，两个身体 · 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 同一句「过来」，在吊索上飞、在小车上开；换身体时记忆和未完成的目标都不丢；做不到的自由度明确拒绝。

**Architecture:** `body.py` 存两份身体描述与意图映射（纯函数）；`cmd_runtime.py` 维护「当前身体」和两个目标物体；`brain.py` 用 `memory/state.json` 记当前目标，并支持 `mount` 指令。小机器人完全封闭，只有一颗核心灯。

**Tech Stack:** Blender 4.5 Python、标准库、现有 UDP 通道。

**Spec:** `docs/superpowers/specs/2026-11-17-two-bodies-design.md`

## Global Constraints

- 不新增依赖。
- 意图名不变（come/back/up/down/left/right/look/stop）+ 新增 mount_rover / mount_winch。
- 小机器人只在地面动（x/y + 朝向），没有 z。
- 换身是瞬时切换 + 灯光变化，不做动画。
- 两个身体的目标物体：`CMD_TARGET`（吊索）、`ROVER_ROOT`（小车）。
- 测试：`python tools/test_body.py` 与 `blender -b ... --python blender/tests/test_bodies.py`。

## Review Focus

- 换身时正在移动：新身体要从自己的位置继续，不跳到旧身体的位置。
- 小车上「升/降」：必须返回拒绝原因，不能静默不动。
- 换回吊索后球的位置：保持卸下前的坐标。
- 未 mount 时给小车发指令：应被忽略（当前身体不是它）。
- 没有 `ROVER_ROOT` 的旧场景：打开要不崩，只报缺对象。

---

### Task 1: 身体描述与意图映射

**Files:** `body.py`、`tools/test_body.py`

**Interfaces:**
- `BODIES: dict[str, dict]`，字段 `class/name/can/axes`
- `supports(body, intent) -> bool`
- `map_intent(body, intent, points, current_mm) -> dict | None`，返回 `{"kind":"move"|"face"|"hold"|"refuse", ...}`

- [ ] 测试：吊索支持 `up`，小车不支持；`map_intent("rover","up")["kind"] == "refuse"` 且 `reason` 含「升降」；`come` 在两具身体上解析到不同命名点；未知意图返回 `None`。
- [ ] 实现并跑 `python tools/test_body.py` → PASS。

### Task 2: 小车模型与命名点

**Files:** `blender/build_command.py`、`blender/tests/test_bodies.py`

**Interfaces:** `ROVER_ROOT`、`rover_mesh`、`TGT_ROVER_NEAR`、`TGT_ROVER_HOME`、`CORE_LIGHT`

- [ ] 测试：对象存在；`ROVER_ROOT` 在 `(600,250,0)` 附近 10mm；轮子最低点 ≈ 0。
- [ ] 实现：车身盒子 + 两轮 + 万向轮 + 顶部核心灯（复用 LED 材质），合并成一个网格；重建 → PASS。

### Task 3: 运行时换身

**Files:** `blender/cmd_runtime.py`、`blender/tests/test_bodies.py`

**Interfaces:** `BODY["active"]`、`apply_intent` 支持 `{"intent":"mount_rover"}`；`route_intent` 返回 `{"kind":"mount","body":...}`

- [ ] 测试：默认 `winch`；`mount_rover` 后 `BODY["active"]=="rover"` 且 `ball_root.hide_viewport` 为真；`come` 落在 `TGT_ROVER_NEAR`；`up` 返回 refuse；换回后 `ball_root` 可见且位置不变。
- [ ] 实现并跑场景测试 → PASS。

### Task 4: 大脑的当前目标与 mount

**Files:** `brain.py`、`blender/actions.json`、`tools/test_brain.py`

**Interfaces:** `save_goal/load_goal`（`memory/state.json`）；`--mount {winch,rover}`；`phrase_intent` 认识「换到车上 / 换回吊索」

- [ ] 测试：写完再读一致；`phrase_intent("换到车上") == "mount_rover"`；`mount_rover` 不再被当成未知意图。
- [ ] 实现：`ALLOWED` 加两个 mount；`reply_once` 成功后写 `state.json`；`--mount` 先发 mount 再补发上一条未完成目标。
- [ ] `python tools/test_brain.py` → PASS。

### Task 5: 六个演示步骤与收尾

**Files:** `README.md`、`docs/...`（不改 spec）

- [ ] 无头串一遍：mount rover → come → up(refuse) → mount winch，断言状态。
- [ ] README 补「换身」用法。
- [ ] 手动：Blender 里说/发六条，观察。

## 自查

- spec 的 6 条演示 → Task 3（换身/拒绝）、Task 4（记忆与目标）、Task 5（串联）。
- Review Focus 五条 → Task 3（移动中换身、拒绝、位置、旧场景）、Task 2（缺对象）。
