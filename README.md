# 科目二场地白模 · 坡道 / 曲线 / 直角

**王梓钰（三维资产）· 2026-11-11 — 11-15 周内交付 · 状态：计划完成，待组内尺寸确认**

本周任务分配 v3 中我的三项：① 三个场地白模；② 每个项目一张俯视正交渲染图 + 坡道额外一张侧视剖面图；
③ 与叶惠坤对接轮廓坐标能否直接喂给 Canvas 2D。渲染工具：**Blender 4.5.3 LTS**（本机 `D:\blender\blender.exe`）。

> 依据优先级：GA 1029—2022（场地尺寸）> GA 1026—2022（操作/评判条款）> 规则表 v0.4（单位/容差）> 任务表 v3。
> 尺寸核对、依据条款号、口径差异见 [`docs/DIMENSIONS.md`](docs/DIMENSIONS.md)。

## 交付清单

| 交付 | 文件 | 说明 |
|---|---|---|
| 白模 ×3 | `white_models/hill_start.blend`、`s_curve.blend`、`right_angle.blend` | 仅地面 + 标线（坡道另 2 根桩杆），0 材质 / 0 灯光 / 0 贴图 |
| 俯视正交图 ×3 | `renders/hill_top.png`、`s_curve_top.png`、`right_angle_top.png` | 各标 4 个关键尺寸，含 2m 比例尺 |
| 侧视剖面图 ×1 | `renders/hill_section.png` | 坡度是唯一俯视看不出来的量 |
| 原始渲染 | `renders/clean/*.png` | Blender 直接输出、未叠加标注，便于肉眼对比例 |
| 几何真相源 | `track/track.wang.json` | 待合并进林呈睿的 `track.json`，改尺寸只改这里 |
| 轮廓坐标 | `outline/outline.json` / `outline.js` | 供叶惠坤 Canvas 2D 消费；曲线另含解析圆弧 |
| 对接说明 | [`docs/CANVAS2D_CONTRACT.md`](docs/CANVAS2D_CONTRACT.md) + `tests/canvas2d_smoke.html` | 打开 HTML 即验证坐标可直接消费 |
| 能证伪的测试 | `tests/verify.mjs` | 11 条，改尺寸不重跑生成器会立刻变红 |

## 目录

```
track/track.wang.json          单一真相源（参数 + 解析圆 + 差异表 + 待确认）
scripts/generate_outline.py    真相源 -> outline.json / outline.js
scripts/annotate_renders.py    按相机参数给渲染图叠加尺寸标注
blender/build_white_models.py  Blender 后台脚本：造 .blend + 渲染 4 张正交图
outline/                       导出的轮廓坐标（含解析弧）
renders/                       4 张标注图 + clean/ 原始图 + cameras.json
white_models/                  3 个 .blend + manifest.json（仅 assets 分支）
tests/                         verify.mjs + canvas2d_smoke.html
docs/                          DIMENSIONS.md / CANVAS2D_CONTRACT.md
```

## 复现（Windows / Git Bash）

```bash
python -m pip install pillow          # 只用于尺寸标注叠加，Blender 不需要
python scripts/generate_outline.py
/d/blender/blender.exe -b -P blender/build_white_models.py
python scripts/annotate_renders.py
node --test tests/verify.mjs          # 期望 11 pass / 0 fail
```

改尺寸的正确姿势：只改 `track/track.wang.json` → 重跑上面 3 条生成命令 → 跑测试。
**不要**直接改 `.blend`、PNG 或 outline 文件；它们都是派生产物。

## 分支策略（本周纪律第 2 条：3D 资产不进主干）

| 分支 | 内容 |
|---|---|
| `main` | 真相源、脚本、文档、轮廓坐标、4 张渲染图、测试 |
| `assets` | `main` 全部内容 + `white_models/*.blend`（只有这里有 3D 资产） |

`.blend` 被 `main` 的 `.gitignore` 排除，只在 `assets` 分支强制加入。
对外/发群只需要 4 张 PNG 和一个链接，不需要让人下载 `.blend`。

## 本周纪律核对

1. ✅ AI 写的代码配了能证伪的测试：`tests/verify.mjs` 11 条全绿；把 `outerRadius` 改成 7.6 会立刻红 2 条。
2. ✅ 3D 资产不进主干，放 `assets` 分支。
3. ✅ 对外口径统一写「计划完成」，不写「已完成」。
4. ✅ 分工边界：只做坡道 / 曲线 / 直角；倒库、侧方、车模未碰。
5. ✅ 材质、光照、贴图、视频一律未做（manifest 断言 0/0/0）。
6. ✅ 三人共用 `track.wang.json` 出图，没有「我觉得应该是这么宽」。

## 待组内确认（4 条，见 DIMENSIONS.md §5）

直角直段 6.71 vs 国标 ≥6.8；坡道车道宽 3.2；桩杆线沿坡位置 17.0；竖曲线何时补。
四条都在 `track.wang.json` 的 `openQuestions` 里，拍板后改参数重跑即可。

## 推到 GitHub

**团队仓库**：<https://github.com/Innocence1117/subject2-auto-evaluator>（公开库，已接受邀请）
**我的账号**：`wzy-2008`，Git 身份 `王梓钰 <wzy-2008@users.noreply.github.com>`。

### 为什么不是普通 `git push`

本机网络里 `github.com` 的 CONNECT 隧道被代理拒绝（502），直连也超时，`git push` /
`git clone` 传输层不通；但 `api.github.com` 可达。所以主通道走 **GitHub Git Data API**
直接建 blob / tree / commit / ref，绕开 502：

```bash
python scripts/push_via_api.py --dry-run     # 先看计划，不写远端
python scripts/push_via_api.py               # 执行推送
```

Token 获取：<https://github.com/settings/tokens/new>，classic PAT 勾 `public_repo` 即可
（或 fine-grained PAT 只选本仓库 + `Contents: Read & Write`）。**不要把 token 贴进聊天**，
保存到仓库根目录 `.github_token`（已被 `.gitignore` 排除），或用环境变量 `GITHUB_TOKEN`，
或 `--token-file <路径>`。脚本会先 `GET /user` 校验身份，再逐文件上传并复用相同 blob。

`scripts/push_to_github.sh` 保留给网络正常、`github.com` 可达的机器使用。

### 分支映射（不覆盖组长的 `main`）

| 远程分支 | 来源 | 内容 |
|---|---|---|
| `wang-white-models` | 本地 `main` | 真相源、脚本、文档、轮廓坐标、4 张渲染图、测试（24 文件） |
| `assets` | 本地 `assets` | 上述全部 + `white_models/*.blend`（27 文件） |
| `main` | **不动** | 组长的 README 原样保留 |

两个分支都从远程 `main` 的提交派生，组长 review 后自行合并。白模直链：
<https://github.com/Innocence1117/subject2-auto-evaluator/tree/assets/white_models>

### 离线兜底

`subject2-white-models.bundle`（仓库同级目录）用 `git bundle` 打包了 `main` + `assets`
完整历史，可在任何能连 GitHub 的机器上一次性还原并推送：

```bash
git clone subject2-white-models.bundle subject2-white-models
cd subject2-white-models
git remote set-url origin https://github.com/Innocence1117/subject2-auto-evaluator.git
git push origin main:wang-white-models
git push origin assets
```

