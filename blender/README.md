# Blender 白模生成脚本

`build_white_models.py` 是 **Blender 后台脚本**，不要直接用系统 Python 运行。

```bash
/d/blender/blender.exe -b -P blender/build_white_models.py
```

它做四件事：

1. 读 `outline/outline.json`（由 `track/track.wang.json` 生成），按项目分别重建干净场景。
2. 生成 `white_models/<project>.blend`：**仅地面 + 标线条带**，坡道另有 2 根桩杆；
   场景内 0 材质 / 0 灯光 / 0 贴图，只有对象显示色（Workbench 用，不是材质槽）。
3. 用 Workbench 引擎 + 正交相机渲染 4 张图到 `renders/clean/`。
   - 三张俯视（相机沿 −Z）
   - 一张坡道侧视剖面（相机沿 +Y）；地面是零厚度曲面，正侧视会被压成线，
     所以渲染时**临时**加一条 0.30m 厚剖面带，渲染完即删，**不写入 .blend**。
4. 写出 `renders/cameras.json`（相机中心 / orthoScale / pxPerMeter）和
   `white_models/manifest.json`（对象计数与 0/0/0 断言），供 `tests/verify.mjs` 核对。

尺寸标注不放在 Blender 场景里，而是由 `scripts/annotate_renders.py` 用同一组相机参数
在渲染图上精确叠加 —— 这样 .blend 保持干净的「白模」，标注也不会被误当成几何。

## 引擎与配色

- `BLENDER_WORKBENCH`，`light = FLAT`，`color_type = OBJECT`，白色 World 背景。
- 对象显示色：地面浅灰、边线深灰、控制线中灰、桩杆线近黑。
- 没有材质槽、没有灯光对象、没有贴图；可用 `manifest.json` 复核。

## 验收

```bash
node --test tests/verify.mjs
```

11 条测试会检查：尺寸与真相源一致、解析圆弧与折线吻合、`.blend` 存在且 0/0/0、
4 张标注图齐全、相机变换自洽、Canvas 2D 契约成立。
