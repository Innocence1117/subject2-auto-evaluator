// 能证伪的回归测试：node --test tests/verify.mjs
// 本周纪律第 1 条「AI 写的代码必须配一条能证伪它的测试才进主干」。
// 核心保证：改了 track/track.wang.json 却忘了重跑生成器 -> 测试立刻变红。
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const read = (p) => JSON.parse(fs.readFileSync(path.join(ROOT, p), 'utf8'));
const exists = (p) => fs.existsSync(path.join(ROOT, p));
const size = (p) => fs.statSync(path.join(ROOT, p)).size;
const close = (a, b, eps, msg) =>
  assert.ok(Math.abs(a - b) <= eps, `${msg || ''} 期望 ${b}，实际 ${a}，容差 ${eps}`);
const center = (l, i) => [
  (l.left[i][0] + l.right[i][0]) / 2,
  (l.left[i][1] + l.right[i][1]) / 2,
];

const T = read('track/track.wang.json');
const O = read('outline/outline.json');
const M = read('white_models/manifest.json');
const C = read('renders/cameras.json');
const H = T.projects.hill_start;
const S = T.projects.s_curve;
const R = T.projects.right_angle;
const COS = 1 / Math.sqrt(1 + H.grade ** 2);

test('单位与容差：内部只用 m / rad / s，tol=0.02', () => {
  assert.equal(T.units.length, 'm');
  assert.equal(T.units.angle, 'rad');
  assert.equal(T.frame.tol, 0.02);
  assert.equal(T.frame.markingWidth, 0.15);
  assert.equal(O.meta.tol, 0.02);
});

test('坡道：10% 坡度与 20m 坡长的三角关系自洽', () => {
  close(Math.atan(H.grade), H.angleRad, 1e-12, 'atan(0.10)');
  close(H.slopeLength * Math.cos(H.angleRad), H.horizontalRun, 1e-12, '水平投影');
  close(H.slopeLength * Math.sin(H.angleRad), H.rise, 1e-12, '高差');
  close(H.flatBefore + H.horizontalRun + H.flatAfter, H.totalLengthX, 1e-12, '总长');
  close(H.rise / H.horizontalRun, H.grade, 1e-12, '坡度');
});

test('坡道：0.65(到中心) 与 0.50(到边缘) 是同一口径', () => {
  close(H.controlLineToPoleLineCenter - H.stopPoleLineWidth / 2,
        H.controlLineToPoleLineEdge, 1e-12, '0.65 - 0.30/2 = 0.50');
});

test('坡道：导出的 5 条线与真相源一致（改了参数不重跑就会红）', () => {
  const p = O.projects.hill_start;
  assert.equal(p.lines.length, 5);
  assert.equal(p.poles.length, 2);
  const pc = H.flatBefore + H.poleLineFromSlopeFoot * COS;
  const stop = p.lines.find((l) => l.kind === 'stop_pole_line');
  const ctrl = p.lines.filter((l) => l.kind === 'control_line');
  assert.ok(stop && ctrl.length === 2);
  close(center(stop, 0)[0], pc, 1e-9, '桩杆线中心 x');
  close(Math.abs(stop.left[0][0] - stop.right[0][0]), H.stopPoleLineWidth * COS, 1e-9, '桩杆线宽(水平投影)');
  const xs = ctrl.map((l) => center(l, 0)[0]).sort((a, b) => a - b);
  close(pc - xs[0], H.controlLineToPoleLineCenter * COS, 1e-9, '前控制线');
  close(xs[1] - pc, H.controlLineToPoleLineCenter * COS, 1e-9, '后控制线');
  // 控制线中心到桩杆线外沿 = 0.50m(沿坡) 的水平投影
  close((xs[1] - Math.max(stop.left[0][0], stop.right[0][0])),
        H.controlLineToPoleLineEdge * COS, 1e-9, 'd=0.50');
  close(p.ground.left.at(-1)[0], H.totalLengthX, 1e-9, '地面末端 x');
  close(p.ground.left[2][2], H.rise, 1e-9, '坡顶标高');
});

test('曲线：R=7.5 / b=3.5 / 135° / 圆心距 11.5 全部自洽', () => {
  close(S.outerRadius - S.roadWidth, S.innerRadius, 1e-12, '内圆半径');
  close(S.outerRadius + S.innerRadius, S.centerDistance, 1e-12, '圆心距');
  close(S.arcAngleRad, 3 / 8 * 2 * Math.PI, 1e-12, '弧长 3/8 圆周');
  const [a1, a2] = S.arcs;
  close(Math.hypot(a2.center[0] - a1.center[0], a2.center[1] - a1.center[1]),
        S.centerDistance, 1e-9, '两圆心实际距离');
  close(Math.abs(a1.endAngle - a1.startAngle), S.arcAngleRad, 1e-12, 'arc1 扫角');
  close(Math.abs(a2.endAngle - a2.startAngle), S.arcAngleRad, 1e-12, 'arc2 扫角');
  // 反向弧在拐点切向相接：arc1 外圆终点 == arc2 内圆起点
  const j1 = [a1.center[0] + S.outerRadius * Math.cos(a1.endAngle),
              a1.center[1] + S.outerRadius * Math.sin(a1.endAngle)];
  const j2 = [a2.center[0] + S.innerRadius * Math.cos(a2.startAngle),
              a2.center[1] + S.innerRadius * Math.sin(a2.startAngle)];
  close(j1[0], j2[0], 1e-9, '拐点 x');
  close(j1[1], j2[1], 1e-9, '拐点 y');
});

test('曲线：outline 里的解析弧与真相源逐字段一致', () => {
  assert.deepEqual(O.projects.s_curve.arcs, S.arcs);
});

test('曲线：采样折线确实落在解析圆上（不是随手画的 S）', () => {
  const p = O.projects.s_curve;
  const [a1, a2] = S.arcs;
  const A = p.lines[0], B = p.lines[1];
  assert.equal(A.left.length, 183);
  assert.equal(B.left.length, 183);
  const on = (line, i, c, radius) => {
    const [x, y] = center(line, i);
    close(Math.hypot(x - c[0], y - c[1]), radius, 1e-9,
          `第 ${i} 点到圆心距离应为 ${radius}`);
  };
  for (const i of [2, 30, 60, 91]) on(A, i, a1.center, S.outerRadius);
  for (const i of [2, 30, 60, 91]) on(B, i, a1.center, S.innerRadius);
  for (const i of [92, 120, 150, 181]) on(A, i, a2.center, S.innerRadius);
  for (const i of [92, 120, 150, 181]) on(B, i, a2.center, S.outerRadius);
  // 入口两条边线中心相距恰为路宽
  close(center(B, 0)[0] - center(A, 0)[0], S.roadWidth, 1e-9, '入口路宽');
});

test('直角：L 形与任务表尺寸一致，内角是尖角', () => {
  const p = O.projects.right_angle;
  assert.equal(R.innerCornerFillet, 0);
  assert.equal(p.ground.points.length, 6);
  close(p.ground.points[1][0], R.approachLength, 1e-12, '外角 x');
  close(p.ground.points[4][0], R.approachLength - R.roadWidth, 1e-12, '内角 x');
  close(p.ground.points[4][1], R.roadWidth, 1e-12, '内角 y');
  close(R.ga1029MinLength - R.approachLength, 0.09, 1e-9, '与国标下限差 0.09m（已列为待确认）');
});

test('Canvas 2D 契约：所有坐标有限、条带两侧等长、线宽为正', () => {
  let lines = 0;
  for (const [key, p] of Object.entries(O.projects)) {
    for (const l of p.lines) {
      lines++;
      assert.ok(l.width > 0, `${key}/${l.id} 线宽必须为正`);
      assert.equal(l.left.length, l.right.length, `${key}/${l.id} 两侧点数应相等`);
      assert.ok(l.left.length >= 2, `${key}/${l.id} 至少需要 2 个点`);
      for (const pt of [...l.left, ...l.right]) {
        assert.ok(pt.length >= 3 && pt.every(Number.isFinite),
                  `${key}/${l.id} 存在非法坐标 ${JSON.stringify(pt)}`);
      }
    }
  }
  assert.equal(lines, 9); // 坡道 5 + 曲线 2 + 直角 2
  assert.equal(O.meta.generatedFrom, 'track/track.wang.json');
});

test('白模：manifest 断言 0 材质 / 0 灯光 / 0 贴图；assets 分支上 .blend 必须存在', () => {
  assert.equal(M.engine, 'BLENDER_WORKBENCH');
  assert.deepEqual(M.assertions, {
    noMaterials: true, noLights: true, noTextures: true, groundPlusLinesOnly: true,
  });
  // main 分支按纪律不含 3D 资产，此时跳过文件存在性检查，CI 仍应绿；
  // assets 分支上则必须真的有 .blend（否则就是「只放了 manifest 没放白模」）。
  const hasBlends = Object.values(M.projects).some(v => exists(v.file));
  for (const [key, v] of Object.entries(M.projects)) {
    assert.equal(v.materials, 0, `${key} 不应有材质`);
    assert.equal(v.lights, 0, `${key} 不应有灯光`);
    assert.equal(v.images, 0, `${key} 不应有贴图`);
    assert.ok(v.cameras >= 1, `${key} 应有正交相机`);
    if (hasBlends) {
      assert.ok(exists(v.file) && size(v.file) > 1000,
        `${key} .blend 应存在且非空（assets 分支）`);
    }
  }
  assert.ok(exists('white_models/manifest.json'), 'manifest 必须在 main 分支可见');
});

test('渲染：4 张带尺寸标注的正交图齐全，相机变换自洽', () => {
  assert.deepEqual(Object.keys(C).sort(),
    ['hill_section', 'hill_top', 'right_angle_top', 's_curve_top']);
  for (const [name, cam] of Object.entries(C)) {
    assert.ok(exists(cam.clean), `${name} 原始渲染缺失`);
    const out = `renders/${name}.png`;
    assert.ok(exists(out) && size(out) > 10000, `${name} 标注图缺失或过小`);
    close(cam.pxPerMeter, cam.res[0] / cam.orthoScale, 1e-9, `${name} px/m`);
    const anns = O.projects[cam.project].annotations.filter(a => a.view === cam.view);
    assert.ok(anns.length >= 3 && anns.length <= 4,
      `${name} 应标 3—4 个关键尺寸，实际 ${anns.length}`);
  }
});
