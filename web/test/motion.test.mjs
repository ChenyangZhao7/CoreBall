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

test('落定时回退 4mm 再收住', () => {
  const d = 400, m = C.moveProfile(d);
  let dip = 0;
  for (let t = 0.9 * m.T; t <= 2.5 * m.T; t += 0.005) dip = Math.max(dip, d - m.pos(t));
  assert.ok(dip >= 3 && dip <= 7, `回退=${dip}`);
  assert.ok(Math.abs(m.pos(2.5 * m.T) - d) < 0.5);
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
