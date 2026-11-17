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
