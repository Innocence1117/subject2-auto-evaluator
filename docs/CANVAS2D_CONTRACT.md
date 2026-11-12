# 轮廓坐标契约（王梓钰 → 叶惠坤）

> 目的：回答本周任务第 3 项「我导出的轮廓坐标能不能直接喂给 Canvas 2D 画法」。
> 结论：**能**。`tests/canvas2d_smoke.html` 用原生 Canvas 2D 消费同一份数据，逐条画出三个项目。

## 1. 数据在哪

| 文件 | 用途 |
|---|---|
| `track/track.wang.json` | **唯一真相源**：尺寸参数 + 解析圆弧，改尺寸只改这里 |
| `outline/outline.json` | 由生成器导出的轮廓坐标（几何 + 标注 + 元信息） |
| `outline/outline.js` | 同一份数据挂到 `window.TRACK_OUTLINE`，供 HTML 直接 `<script src>` 加载，绕开 `file://` 的 fetch 限制 |

生成方式（改完尺寸跑这两条）：

```bash
python scripts/generate_outline.py
/d/blender/blender.exe -b -P blender/build_white_models.py
python scripts/annotate_renders.py
```

## 2. 坐标系（与 `coords.md` / 规则表 §1 一致）

- 单位 **m**，角度 **rad**；内部不出现 cm / 度 / km/h。
- 每个项目各自局部坐标：`x` 为行车方向、`y` 为横向（左正）、`z` 竖直向上；右手系。
- **Canvas 2D 的 y 向下**，所以映射要翻转：

```js
const s  = Math.min(W / bboxW, H / bboxH) * 0.9;   // px per meter
const px = W / 2 + (x - cx) * s;
const py = H / 2 - (y - cy) * s;                    // 注意这里是减号
```

`renders/cameras.json` 里给了 Blender 正交相机的 `center` / `pxPerMeter`，
若想让 2D 图与 Blender 渲染图逐像素对齐，可以直接复用那组参数。

## 3. 数据结构

```
projects.<id>
  ground.type = "strip"   → ground.left / ground.right : [[x,y,z], ...]  (等长，桥接成条带)
  ground.type = "polygon" → ground.points               : [[x,y,z], ...]  (闭合多边形)
  lines[]                 → { id, kind, judge, width, left:[[x,y,z]...], right:[[x,y,z]...] }
  poles[]                 → { id, x, y, z, radius, height }   (仅坡道)
  arcs[]                  → { id, center:[x,y], outerRadius, innerRadius,
                              startAngle, endAngle, direction }  (仅曲线)
  annotations[]           → 渲染图尺寸标注，前端不用
```

`lines[].left/right` 是同一条标线两侧的轮廓点（间距 = `width`）。
画一条标线就是 `left` 正序 + `right` 逆序闭合成多边形后 `fill()`：

```js
ctx.beginPath();
line.left.forEach(([x, y], i) => i ? ctx.lineTo(px(x), py(y)) : ctx.moveTo(px(x), py(y)));
[...line.right].reverse().forEach(([x, y]) => ctx.lineTo(px(x), py(y)));
ctx.closePath(); ctx.fill();
```

`judge` 字段沿用规则表 §2：`'wheel'` = 车轮轧线（R02），`'body'` = 车身出线（R01）。
本周只画，不判定；12 月判定层接上后可直接复用同一个 `lineId`。

## 4. 两条硬约束

1. **曲线必须用解析圆，不要用导出的折线做判定。**
   `lines` 里的折线按 1.5° 采样，只供显示；`arcs` 才是判定依据
   （规则表 3.R02：128 段折线弦高 0.9cm，与 0.02m 容差同量级，会误判）。
   Canvas 2D 侧若要画弧，用 `ctx.arc(cx, cy, r, -endAngle, -startAngle)`（角度取负以适配 y 翻转）。
2. **标线判定界取外沿**：条带已经把 0.15m 线宽画出来了，别再按中心线 ±0.075 估。

## 5. 已核对 / 待确认

- ✅ `tests/canvas2d_smoke.html` 打开即画出三个项目，坐标全部有限值，无 NaN。
- ✅ `tests/verify.mjs` 会证伪：改 `track.wang.json` 任一尺寸而忘记重跑生成器，测试立刻红。
- ⚠️ 直角直段任务表写 6.71、GA 1029 现行下限 6.8，本周按 6.71 建模，等组内拍板。
- ⚠️ 坡道车道宽任务表未给，按 GA 1029 下限 3.2 建模，等谭云嘉的考场公示平面图。
