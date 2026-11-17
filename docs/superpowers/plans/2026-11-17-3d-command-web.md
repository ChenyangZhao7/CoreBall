# 三维指挥网页 · 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 做一个双击就能打开的单文件网页，用鼠标把球指到三维空间里任意位置，四根线实时重算线长与张力，禁区实时挡住它。

**Architecture:** 全部代码在一个 `web/command.html` 里。纯数学放在 `<script id="core">` 中，挂到 `globalThis.CoreBall`；Node 测试从这个块里把函数取出来跑，因此交付物仍是单文件。渲染用 Canvas 2D + 画家算法（`buildScene` 产出按深度排序的图元，`paint` 画出来），不依赖任何外部库。

**Tech Stack:** 原生 HTML/CSS/JS、Canvas 2D、Node 内置 `node:test`（仅测试用，不进入交付物）。

**Spec:** `docs/superpowers/specs/2026-11-17-3d-command-demo-design.md`

## Global Constraints

- 交付物是**单文件** `web/command.html`：没有外链脚本、样式、字体、图片；断网可用。
- 不使用 `Three.js`、npm 包、CDN。
- 全部数值单位：毫米（mm）、牛顿（N）、秒（s）。坐标与参数表一致。
- 核心常量必须与 `tools/tension.py` 一致：`MASS_KG = 0.50`、`TETHER_UP = 0.60`、`T_MIN = 0.30`、`T_MAX = 20.0`。
- 锚点：`[-760,217,1729] [760,217,1729] [-603,850,1729] [603,850,1729]`。
- 禁区：脖子 `(0,890)` 半径 210 的竖直圆柱，向上无限。
- 默认位：`(-380,520,1300)`。
- 速度上限 356 mm/s（五次多项式 S 曲线，峰值系数 1.875）。
- 本目录**不是 git 仓库**：不执行任何 `git` 命令。每个任务以测试通过作为检查点。
- 测试命令统一为：`node --test web/test`（在项目根目录运行）。

## Review Focus

- **目标与球重合（距离 < 5 mm）**：`moveProfile` 的 `T` 会变成 0，除零后位置变 NaN。期望：直接判到位，不抖、不报错。
- **目标正好在禁区轴线上**：推离方向未定义。期望：固定沿 +X 推到边界，不产生 NaN。
- **相机的 pitch 到 ±90°**：上方向量退化，画面翻转或全黑。期望：内部把 pitch 夹到 ±89°。
- **目标在相机背后**：投影深度 ≤ 0 时线会穿帮。期望：该图元不画。
- **画布尺寸为 0**（窗口被折叠/初始化时序）：投影除零。期望：跳过绘制帧，不抛异常。

---

### Task 1: 单文件骨架 + 几何与张力核心

**Files:**
- Create: `web/command.html`
- Create: `web/test/harness.mjs`
- Create: `web/test/core.test.mjs`

**Interfaces:**
- Consumes: 无
- Produces:
  - `CoreBall.ANCHORS: number[4][3]`、`CoreBall.MASS_KG`、`CoreBall.TETHER_UP`、`CoreBall.T_MIN`、`CoreBall.T_MAX`
  - `CoreBall.lineLengths(p: number[3]) -> number[4]`
  - `CoreBall.solveTension(p: number[3]) -> { T: number[4], margin: number, closed: boolean, W: number[3] }`
  - `loadCore()`（测试用）返回上面的 `CoreBall` 对象

- [ ] **Step 1: 写失败的测试**

`web/test/harness.mjs`：

```js
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

export function loadCore() {
  const html = readFileSync(new URL('../command.html', import.meta.url), 'utf8');
  const m = html.match(/<script id="core">([\s\S]*?)<\/script>/);
  if (!m) throw new Error('command.html 里没有 <script id="core">');
  const sandbox = {};
  vm.runInNewContext(m[1], sandbox);
  return sandbox.CoreBall;
}
```

`web/test/core.test.mjs`：

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { loadCore } from './harness.mjs';

const C = loadCore();
const ROOT = fileURLToPath(new URL('../..', import.meta.url));

test('默认位四根线长', () => {
  const want = [648.27, 1255.17, 585.38, 1122.15];
  C.lineLengths([-380, 520, 1300]).forEach((L, i) => assert.ok(Math.abs(L - want[i]) < 0.5));
});

test('默认位张力与最松余量', () => {
  const r = C.solveTension([-380, 520, 1300]);
  const want = [2.7002, 1.3384, 2.1137, 1.3384];
  r.T.forEach((T, i) => assert.ok(Math.abs(T - want[i]) < 0.02));
  assert.ok(Math.abs(r.margin - 1.3384) < 0.02);
  assert.equal(r.closed, true);
});

test('低处贴墙点判为力封闭失效', () => {
  const r = C.solveTension([-700, 300, 1150]);
  assert.equal(r.closed, false);
  assert.ok(Math.abs(r.margin - 0.1669) < 0.02);
});

test('与 tools/tension.py 逐点一致（线长 < 2 mm，张力 < 0.05 N）', () => {
  for (const p of [[-380, 520, 1300], [0, 890, 1450], [-700, 300, 1150]]) {
    const out = execFileSync('python', ['tools/tension.py', ...p.map(String)], { cwd: ROOT, encoding: 'utf8' });
    const py = [...out.matchAll(/L=\s*([\d.]+) mm\s+T=\s*(-?[\d.]+) N/g)];
    assert.equal(py.length, 4);
    const r = C.solveTension(p);
    C.lineLengths(p).forEach((L, i) => {
      assert.ok(Math.abs(L - Number(py[i][1])) <= 2, `线长 ${i + 1}`);
      assert.ok(Math.abs(r.T[i] - Number(py[i][2])) <= 0.05, `张力 ${i + 1}`);
    });
  }
});
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `node --test web/test`
Expected: FAIL，`ENOENT ... command.html`

- [ ] **Step 3: 实现骨架与核心**

`web/command.html` 骨架：

```html
<!doctype html>
<html lang="zh"><head><meta charset="utf-8">
<title>CoreBall · 三维指挥</title>
<style>html,body{margin:0;height:100%;background:#0a0d10;overflow:hidden;color:#d7dbe0}
canvas{display:block}#hud{position:fixed;left:14px;bottom:14px;font:13px/1.6 ui-monospace,Consolas,monospace;
color:#9fb0bf;white-space:pre}</style>
</head><body>
<canvas id="cv"></canvas>
<div id="hud"></div>
<script id="core">
// ===== 纯数学：无 DOM 依赖，测试直接从这里加载 =====
const ANCHORS = [[-760,217,1729],[760,217,1729],[-603,850,1729],[603,850,1729]];
const MASS_KG = 0.50, TETHER_UP = 0.60, T_MIN = 0.30, T_MAX = 20.0;

function lineLengths(p) {
  return ANCHORS.map(a => Math.hypot(a[0]-p[0], a[1]-p[1], a[2]-p[2]));
}

function solveTension(p) { /* 见 Step 3 说明 */ }

globalThis.CoreBall = { ANCHORS, MASS_KG, TETHER_UP, T_MIN, T_MAX, lineLengths, solveTension };
</script>
<script>
// ===== 应用（逐步补全）=====
</script>
</body></html>
```

`solveTension` 照搬 `tools/tension.py` 的算法：单位方向 → 最小范数特解 `Tp` → 零空间 `n` → 枚举六对交点取 max-min 的 λ。3×3 求逆用伴随矩阵。`W = [0, 0, MASS_KG*9.81 - TETHER_UP]`。

- [ ] **Step 4: 运行测试，确认通过**

Run: `node --test web/test`
Expected: PASS，4 个测试全绿

---

### Task 2: 运动曲线与禁区推离

**Files:**
- Modify: `web/command.html`（`<script id="core">` 内）
- Create: `web/test/motion.test.mjs`

**Interfaces:**
- Consumes: `CoreBall.*`（Task 1）
- Produces:
  - `CoreBall.NECK: { x: number, y: number, r: number }` = `{0, 890, 210}`
  - `CoreBall.moveProfile(d: number) -> { T: number, pos(t: number): number, vel(t: number): number }`
  - `CoreBall.pushOutOfNeck(p: number[3]) -> number[3]`

- [ ] **Step 1: 写失败的测试**

`web/test/motion.test.mjs`：

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { loadCore } from './harness.mjs';

const C = loadCore();

test('1139mm 的时长与峰值速度', () => {
  const m = C.moveProfile(1139);
  assert.ok(Math.abs(m.T - 6.0) < 0.02, `T=${m.T}`);
  let vmax = 0;
  for (let t = 0; t <= 1.5 * m.T; t += 0.005) vmax = Math.max(vmax, m.vel(t));
  assert.ok(Math.abs(vmax - 356) < 2, `vmax=${vmax}`);
});

test('前 0.5 秒只走 6mm，99% 在 5.38 秒', () => {
  const m = C.moveProfile(1139);
  assert.ok(Math.abs(m.pos(0.5) - 6) < 1);
  let t99 = 0;
  for (let t = 0; t <= 1.5 * m.T; t += 0.002) if (m.pos(t) >= 1139 * 0.99) { t99 = t; break; }
  assert.ok(Math.abs(t99 - 5.38) < 0.1, `t99=${t99}`);
});

test('落定回弹 4mm 后收住', () => {
  const m = C.moveProfile(400);
  let over = 0;
  for (let t = 0; t <= 2.5 * m.T; t += 0.005) over = Math.max(over, m.pos(t) - 400);
  assert.ok(over >= 3 && over <= 5, `overshoot=${over}`);
  assert.ok(Math.abs(m.pos(2.5 * m.T) - 400) < 0.5);
});

test('距离为 0 不除零', () => {
  const m = C.moveProfile(0);
  assert.equal(m.T, 0);
  assert.equal(m.pos(0), 0);
  assert.ok(Number.isFinite(m.pos(1)));
});

test('禁区推离：内部、外部、轴线上', () => {
  assert.deepEqual(C.pushOutOfNeck([0, 600, 1200]), [0, 600, 1200]);
  const a = C.pushOutOfNeck([0, 700, 1200]);
  assert.ok(Math.abs(Math.hypot(a[0], a[1] - 890) - 210) < 1e-6);
  const b = C.pushOutOfNeck([0, 890, 1200]);
  assert.ok(Math.abs(Math.hypot(b[0], b[1] - 890) - 210) < 1e-6);
  assert.equal(b[2], 1200);
  assert.ok(b.every(Number.isFinite));
});
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `node --test web/test/motion.test.mjs`
Expected: FAIL，`C.moveProfile is not a function`

- [ ] **Step 3: 实现**

`moveProfile(d)`：`T = 1.875 * d / 356`；`u = t / T`，`pos = d * (10u³ - 15u⁴ + 6u⁵)`，`vel = d * (30u² - 60u³ + 30u⁴) / T`。当 `t > 0.92T` 叠加与 `tools/curves.py` 相同的阻尼项：`amp=4, zeta=4.5, w=2π*1.2`。`d === 0` 时返回 `{T:0, pos:()=>0, vel:()=>0}`。

`pushOutOfNeck(p)`：计算 `dx=p[0]-0, dy=p[1]-890, r=hypot`。若 `r >= 210` 原样返回；若 `r < 1e-6` 沿 +X 推到 `[210,890,p[2]]`；否则按比例放大到 210。

- [ ] **Step 4: 运行测试，确认通过**

Run: `node --test web/test`
Expected: PASS

---

### Task 3: 相机、投影与拾取

**Files:**
- Modify: `web/command.html`（core 内）
- Create: `web/test/camera.test.mjs`

**Interfaces:**
- Consumes: 无
- Produces:
  - `CoreBall.makeCamera({ yaw, pitch, dist, target }) -> Camera`，`Camera = { eye:[3], target:[3], fw:[3], right:[3], up:[3], fov:number }`；`yaw`/`pitch` 单位为度，`pitch` 内部夹到 `[-89, 89]`
  - `CoreBall.project(p, cam, w, h) -> { x, y, depth, scale }`，`depth <= 0` 表示在相机背后
  - `CoreBall.rayFromScreen(sx, sy, cam, w, h) -> { o:[3], d:[3] }`
  - `CoreBall.planeHit(ray, z) -> [3] | null`
  - `CoreBall.pickTarget(sx, sy, cam, w, h, ghost) -> boolean`（屏幕距离 ≤ 14 px）

- [ ] **Step 1: 写失败的测试**

`web/test/camera.test.mjs`：

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { loadCore } from './harness.mjs';

const C = loadCore();
const T = [-200, 500, 1250];
const cam = C.makeCamera({ yaw: 35, pitch: 22, dist: 3600, target: T });

test('相机目标点投到画面正中', () => {
  const s = C.project(T, cam, 1200, 800);
  assert.ok(Math.abs(s.x - 600) < 0.5 && Math.abs(s.y - 400) < 0.5);
  assert.ok(s.depth > 0);
});

test('更近的点投影更大', () => {
  const near = C.project([T[0], T[1], T[2] + 500], cam, 1200, 800);
  const far = C.project([T[0], T[1], T[2] - 1500], cam, 1200, 800);
  assert.ok(near.scale > far.scale);
});

test('背后的点 depth <= 0', () => {
  const behind = [cam.eye[0] + cam.fw[0] * -1000, cam.eye[1] + cam.fw[1] * -1000, cam.eye[2] + cam.fw[2] * -1000];
  assert.ok(C.project(behind, cam, 1200, 800).depth <= 0);
});

test('pitch 到 90 度被夹住，不产生 NaN', () => {
  const c = C.makeCamera({ yaw: 0, pitch: 90, dist: 3000, target: T });
  const s = C.project(T, c, 1200, 800);
  assert.ok(Number.isFinite(s.x) && Number.isFinite(s.y));
});

test('屏幕 → 射线 → 平面 → 投影 回到原屏幕点', () => {
  const ray = C.rayFromScreen(840, 260, cam, 1200, 800);
  const hit = C.planeHit(ray, 1200);
  assert.ok(hit);
  const s = C.project(hit, cam, 1200, 800);
  assert.ok(Math.abs(s.x - 840) < 1 && Math.abs(s.y - 260) < 1);
});

test('命中检测：幽灵点附近 10px 为真，远处为假', () => {
  const g = C.project(T, cam, 1200, 800);
  assert.equal(C.pickTarget(g.x + 10, g.y, cam, 1200, 800, T), true);
  assert.equal(C.pickTarget(g.x + 80, g.y, cam, 1200, 800, T), false);
});

test('画布为 0 时不抛异常', () => {
  const s = C.project(T, cam, 0, 0);
  assert.ok(Number.isFinite(s.x) && Number.isFinite(s.y));
});
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `node --test web/test/camera.test.mjs`
Expected: FAIL，`makeCamera is not a function`

- [ ] **Step 3: 实现**

`makeCamera`：`p = clamp(pitch, -89, 89)` 转弧度；`eye = target + dist * [cos p * sin yaw, -cos p * cos yaw, sin p]`；`fw = normalize(target - eye)`；`right = normalize(cross(fw, worldUp))`；`up = cross(right, fw)`。`fov = 45`。

`project`：`d = p - eye`；`depth = dot(d, fw)`；`scale = (h / 2) / tan(fov/2) / depth`（`depth <= 0` 时返回 `depth`，`scale = 0`）；`x = w/2 + dot(d, right) * scale`，`y = h/2 - dot(d, up) * scale`。`w` 或 `h` 为 0 时 `x=y=w/2`。

`rayFromScreen`：反向用同一组基。

`planeHit`：`t = (z - o[2]) / d[2]`；`t <= 0` 返回 `null`。

`pickTarget`：`hypot(sx - g.x, sy - g.y) <= 14`。

- [ ] **Step 4: 运行测试，确认通过**

Run: `node --test web/test`
Expected: PASS

---

### Task 4: 场景装配与绘制

**Files:**
- Modify: `web/command.html`（core 内加 `buildScene`，应用脚本加 `paint`）
- Create: `web/test/scene.test.mjs`

**Interfaces:**
- Consumes: `ANCHORS`、`solveTension`、`project`、`NECK`
- Produces:
  - `CoreBall.buildScene(state) -> Prim[]`，其中
    `state = { p: number[3], ghost: number[3], ghostBlocked: boolean, margin: number, closed: boolean, time: number }`，
    `Prim = { kind:'line', pts:[3][], color:string, width:number } | { kind:'disc', p:[3], r:number, color:string } | { kind:'poly', pts:[3][], fill:string } | { kind:'cyl', center:[2], r:number, z0:number, z1:number, fill:string }`，
    返回值按**深度从远到近**排序（远者先画）
  - `CoreBall.cableColor(margin: number) -> string`：`≥1.0` 返回 `'#4fa87f'`；`≥0.3` 返回 `'#e0b060'`；否则 `'#d9534f'`
  - `CoreBall.hudText(state) -> string`

- [ ] **Step 1: 写失败的测试**

`web/test/scene.test.mjs`：

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { loadCore } from './harness.mjs';

const C = loadCore();
const base = { p: [-380,520,1300], ghost: [-380,520,1300], ghostBlocked: false, margin: 1.34, closed: true, time: 0 };

test('四根线，颜色跟随最松余量', () => {
  const s = C.buildScene(base);
  assert.equal(s.filter(x => x.kind === 'line' && x.width === 2).length, 4);
  assert.equal(C.cableColor(1.34), '#4fa87f');
  assert.equal(C.cableColor(0.5), '#e0b060');
  assert.equal(C.cableColor(0.17), '#d9534f');
  const red = C.buildScene({ ...base, margin: 0.17, closed: false });
  assert.equal(red.filter(x => x.color === '#d9534f').length >= 4, true);
});

test('场景里有球、锚点、禁区圆柱、桌子和显示器', () => {
  const s = C.buildScene(base);
  assert.ok(s.some(x => x.kind === 'disc' && x.r === 40));
  assert.ok(s.some(x => x.kind === 'cyl' && x.r === 210));
  assert.ok(s.some(x => x.kind === 'poly'));
});

test('按深度从远到近排序', () => {
  const s = C.buildScene(base);
  const depth = x => (x.depth === undefined ? 0 : x.depth);
  for (let i = 1; i < s.length; i++) assert.ok(depth(s[i - 1]) >= depth(s[i]));
});

test('目标被禁区挡住时幽灵点变红', () => {
  const s = C.buildScene({ ...base, ghostBlocked: true });
  assert.ok(s.some(x => x.kind === 'disc' && x.r === 6 && x.color === '#d9534f'));
});

test('HUD 文本里有一切该有的数', () => {
  const t = C.hudText(base);
  assert.match(t, /\(-380, 520, 1300\)/);
  assert.match(t, /648/);
  assert.match(t, /2\.70/);
  assert.match(t, /1\.34/);
});
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `node --test web/test/scene.test.mjs`
Expected: FAIL，`buildScene is not a function`

- [ ] **Step 3: 实现**

`buildScene` 依次产生：地面网格（`line`，width=1）、桌子（`poly`）、显示器（`poly`）、禁区圆柱（`cyl`）、四个锚点（`disc` r=6）、四根线（`line` width=2）、球（`disc` r=40）、幽灵点（`disc` r=6）。每个图元附 `depth = project(...).depth`，按 depth 降序排。`paint(ctx, prims, cam, w, h)` 直接按序画，`depth <= 0` 的跳过；球用径向渐变（中心 `#cfe3f0` → 边缘 `#2c3a46`）画出体积感。

- [ ] **Step 4: 运行测试，确认通过**

Run: `node --test web/test`
Expected: PASS

---

### Task 5: 交互、循环、README 与整体验收

**Files:**
- Modify: `web/command.html`（应用脚本）
- Modify: `README.md`（目录里加 `web/command.html` 一行）
- Create: `web/test/ui.test.mjs`

**Interfaces:**
- Consumes: Task 1–4 的全部
- Produces:
  - `CoreBall.dragTarget(cam, sx, sy, z, ghost) -> number[3]`（在 `z` 平面上求交，再 `pushOutOfNeck`）
  - `CoreBall.initialState() -> state`（`p = ghost = [-380,520,1300]`）

- [ ] **Step 1: 写失败的测试**

`web/test/ui.test.mjs`：

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { loadCore } from './harness.mjs';

const C = loadCore();
const cam = C.makeCamera({ yaw: 35, pitch: 22, dist: 3600, target: [-200,500,1250] });

test('拖目标点落在指定的高度上', () => {
  const g = C.project([-380,520,1300], cam, 1200, 800);
  const p = C.dragTarget(cam, g.x + 60, g.y + 20, 1300, [-380,520,1300]);
  assert.ok(Math.abs(p[2] - 1300) < 1e-6);
});

test('拖进禁区会被推回边界', () => {
  const p = C.dragTarget(cam, 600, 400, 1300, [0, 890, 1300]);
  assert.ok(Math.hypot(p[0], p[1] - 890) >= 210 - 1e-6);
});

test('初始状态在默认位', () => {
  assert.deepEqual(C.initialState().p, [-380, 520, 1300]);
});
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `node --test web/test/ui.test.mjs`
Expected: FAIL

- [ ] **Step 3: 实现交互与循环**

`requestAnimationFrame` 主循环：`dt` 限幅到 0.05 s；当前段用 `moveProfile(dist)` 缓存的 `{d, p0, p1, t0}`，每帧 `s = profile.pos((now - t0)/1000)` 沿直线插值，再 `pushOutOfNeck`；到达后把 `p` 设在终点。

事件：
- `pointerdown` 命中幽灵点 → 拖动模式；否则 → 环绕模式
- `pointermove` 拖动：`ghost = dragTarget(cam, x, y, ghost[2], ghost)`；环绕：`yaw += dx*0.4`，`pitch = clamp(pitch - dy*0.3, -89, 89)`
- `wheel`：`dist = clamp(dist * (1 + dy*0.001), 1500, 8000)`
- `keydown`：方向键微调 `ghost` 的 X/Y 各 10 mm，`PageUp/PageDown` 改 Z 各 10 mm，空格回到默认位
- 高度滑杆：`<input type="range" min="900" max="1500" step="5">`，值写进 `ghost[2]`

每帧：`state.margin = solveTension(p).margin`；`hud.textContent = hudText(state)`；`paint(ctx, buildScene(state), cam, w, h)`。

- [ ] **Step 4: 运行全部测试**

Run: `node --test web/test`
Expected: 全部 PASS

- [ ] **Step 5: 手动验收（设计文档 §完成标准）**

打开 `web/command.html`：

1. 拖到默认位附近，HUD 线长显示 `648 / 1255 / 585 / 1122`，张力 `2.70 / 1.34 / 2.11 / 1.34`。
2. 拖进红色禁区圆柱，球停在边界，HUD 写「安全层否决」。
3. 拖到 `(-700, 300, 1150)`，四根线变红，HUD 写「最松张力不足，物理上绷不住」。
4. 转到球背后、滚轮拉近，线不穿帮；滚轮拉到最远再拉回，不跳变。
5. 断网（拔网线/关 Wi-Fi）重新打开，功能不变。

- [ ] **Step 6: 更新 README**

在目录代码块里加一行：

```
web/       command.html  三维指挥：拖动目标点，四线实时解算
```

---

## 自查

- 设计文档每条目标都有对应任务：能拖（Task 5）、S 曲线与回弹（Task 2）、线长/张力（Task 1）、禁区（Task 2 + 5）、背后不穿帮（Task 3）、单文件离线（Global Constraints）。
- 五条 Review Focus 都有测试：距离 0（Task 2）、轴线（Task 2）、pitch 90（Task 3）、背后投影（Task 3）、画布 0（Task 3）。
- 数值对照由 Task 1 直接调用 `tools/tension.py` 验证，不靠手抄。
