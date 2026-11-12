#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 track/track.wang.json 生成 outline/outline.json 与 outline.js。

单一真相源：track/track.wang.json。本脚本不写死任何尺寸数字，
所有几何（含白模、渲染标注、Canvas 2D 轮廓）都由该 JSON 推导。
改尺寸只需改 track.wang.json 再跑一次本脚本 + Blender 脚本。
"""
import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACK_PATH = os.path.join(ROOT, "track", "track.wang.json")
OUT_DIR = os.path.join(ROOT, "outline")

with open(TRACK_PATH, "r", encoding="utf-8") as f:
    T = json.load(f)

V = T["vehicle"]
P = T["projects"]
COS_A = 1.0 / math.sqrt(1.0 + P["hill_start"]["grade"] ** 2)  # cos(atan(0.10))
LINE_W = T["frame"]["markingWidth"]
STEP_DEG = 1.5  # 显示用折线采样步长；判定层用解析圆，不用它


# ---------- 通用几何工具 ----------
def sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def norm(a):
    n = math.hypot(a[0], a[1])
    return (a[0] / n, a[1] / n)


def perp(a):
    return (-a[1], a[0])


def offset_band(path, width, zfun):
    """把 2D 折线扩成 width 宽的条带，返回左右两排 [x,y,z] 点（miter 连接）。"""
    left, right = [], []
    half = width / 2.0
    for i, p in enumerate(path):
        if i == 0:
            n = perp(norm(sub(path[1], path[0])))
            m, s = n, half
        elif i == len(path) - 1:
            n = perp(norm(sub(path[-1], path[-2])))
            m, s = n, half
        else:
            n1 = perp(norm(sub(p, path[i - 1])))
            n2 = perp(norm(sub(path[i + 1], p)))
            m = norm((n1[0] + n2[0], n1[1] + n2[1]))
            d = m[0] * n1[0] + m[1] * n1[1]
            s = half / d if abs(d) > 1e-9 else half
        dx, dy = m[0] * s, m[1] * s
        left.append([p[0] + dx, p[1] + dy, zfun(p[0] + dx, p[1] + dy)])
        right.append([p[0] - dx, p[1] - dy, zfun(p[0] - dx, p[1] - dy)])
    return left, right


def sample_arc(center, radius, a0, a1, direction, step_deg=STEP_DEG):
    """解析圆弧采样（仅用于显示/导出；判定层必须用 arc 描述本身）。"""
    sweep = abs(a1 - a0)
    n = max(2, int(math.ceil(sweep / math.radians(step_deg))))
    out = []
    for k in range(n + 1):
        t = k / n
        a = a0 + (a1 - a0) * t
        out.append([center[0] + radius * math.cos(a), center[1] + radius * math.sin(a)])
    return out


def dim(view, p1, p2, label, label_pos, leader=None):
    return {
        "view": view, "kind": "dim",
        "p1": [round(p1[0], 4), round(p1[1], 4)],
        "p2": [round(p2[0], 4), round(p2[1], 4)],
        "label": label,
        "labelPos": [round(label_pos[0], 4), round(label_pos[1], 4)],
        "leader": [round(leader[0], 4), round(leader[1], 4)] if leader else None,
    }


def note(view, label, label_pos, leader):
    return {
        "view": view, "kind": "note",
        "label": label,
        "labelPos": [round(label_pos[0], 4), round(label_pos[1], 4)],
        "leader": [round(leader[0], 4), round(leader[1], 4)],
    }


# ---------- 坡道 ----------
H = P["hill_start"]
H_LANE = H["laneWidth"] / 2.0
H_X_FOOT = H["flatBefore"]
H_X_TOP = H["flatBefore"] + H["horizontalRun"]
H_X_END = H["totalLengthX"]
H_RISE = H["rise"]
H_PC = H_X_FOOT + H["poleLineFromSlopeFoot"] * COS_A  # 桩杆线中心（水平 x）
H_STOP_W = H["stopPoleLineWidth"] * COS_A
H_CTRL_OFF = H["controlLineToPoleLineCenter"] * COS_A
H_LINE_W = LINE_W * COS_A


def hill_z(x, y=0.0):
    if x <= H_X_FOOT:
        return 0.0
    if x >= H_X_TOP:
        return H_RISE
    return (x - H_X_FOOT) * H["grade"]


def hill_z_line(x, y=0.0):
    return hill_z(x) + 0.01


def hill_project():
    xs = [0.0, H_X_FOOT, H_X_TOP, H_X_END]
    ground = {
        "type": "strip",
        "left": [[x, -H_LANE, hill_z(x)] for x in xs],
        "right": [[x, H_LANE, hill_z(x)] for x in xs],
    }

    def make_line(lid, kind, path, width):
        l, r = offset_band(path, width, hill_z_line)
        return {"id": lid, "kind": kind, "judge": "body", "width": round(width, 6),
                "left": l, "right": r}

    edge_path = [[x, 0.0] for x in xs]
    lines = []
    # 两条边线：沿 x 的折线，条带宽度沿 y
    for side, sign in (("left", 1.0), ("right", -1.0)):
        ep = [[x, sign * H_LANE] for x in xs]
        l, r = offset_band(ep, LINE_W, hill_z_line)
        lines.append({"id": "hill_edge_" + side, "kind": "edge", "judge": "body",
                      "width": LINE_W, "left": l, "right": r})
    # 停车桩杆线（0.30m，例外线宽）
    lp, rp = offset_band([[H_PC, -H_LANE], [H_PC, H_LANE]], H_STOP_W, hill_z_line)
    lines.append({"id": "hill_stop_pole_line", "kind": "stop_pole_line", "judge": "body",
                  "width": round(H_STOP_W, 6), "left": lp, "right": rp})
    # 前后两条停车控制线，各距桩杆线中心 0.65m
    for tag, x in (("before", H_PC - H_CTRL_OFF), ("after", H_PC + H_CTRL_OFF)):
        lp, rp = offset_band([[x, -H_LANE], [x, H_LANE]], H_LINE_W, hill_z_line)
        lines.append({"id": "hill_control_line_" + tag, "kind": "control_line", "judge": "body",
                      "width": round(H_LINE_W, 6), "left": lp, "right": rp})

    poles = [
        {"id": "hill_pole_" + s, "x": round(H_PC, 6), "y": sign * (H_LANE + 0.25),
         "z": round(hill_z(H_PC), 6), "radius": H["poleRadius"], "height": H["poleHeight"]}
        for s, sign in (("left", 1.0), ("right", -1.0))
    ]

    ann = [
        dim("top", [H_X_FOOT, -2.55], [H_X_TOP, -2.55],
            "坡面长 L=20.00 m（俯视投影 19.90 m）", [13.9, -3.25]),
        dim("top", [1.15, -H_LANE], [1.15, H_LANE],
            "车道宽 b1=3.20 m", [1.15, 2.25]),
        dim("top", [H_PC - H_STOP_W / 2, 2.55], [H_PC + H_STOP_W / 2, 2.55],
            "桩杆线宽 b2=0.30 m", [H_PC - 4.6, 3.25],
            leader=[H_PC, 2.75]),
        dim("top", [H_PC, 4.05], [H_PC + H_CTRL_OFF, 4.05],
            "S=0.65 m（到边缘 d=0.50 m）", [H_PC + 4.6, 4.75],
            leader=[H_PC + H_CTRL_OFF / 2, 4.15]),
        dim("section", [H_X_FOOT, -1.15], [H_X_TOP, -1.15],
            "坡面长 L=20.00 m / 水平投影 19.90 m", [13.9, -1.85]),
        dim("section", [H_X_TOP + 1.2, 0.0], [H_X_TOP + 1.2, H_RISE],
            "高差 Δh=1.99 m", [H_X_TOP + 3.6, 1.0]),
        note("section", "坡度 i=10%（5.71°）", [8.0, 3.1], leader=[11.0, 0.7]),
        dim("section", [H_X_FOOT, 2.35], [H_PC, 2.35],
            "l2=17.00 m（沿坡，标准仅给下限 6.71 m）", [(H_X_FOOT + H_PC) / 2, 3.05]),
    ]
    return {"label": H["label"], "ground": ground, "lines": lines, "poles": poles,
            "arcs": [], "annotations": ann}


# ---------- 曲线行驶 ----------
S = P["s_curve"]
A1, A2 = S["arcs"][0], S["arcs"][1]
C1, C2 = A1["center"], A2["center"]
S_ENTRY, S_EXIT = S["entryStraight"], S["exitStraight"]
S_EXIT_INNER_X = C2[0] + A2["innerRadius"]
S_EXIT_OUTER_X = C2[0] + A2["outerRadius"]
S_EXIT_Y = C2[1]


def s_flat(x, y=0.0):
    return 0.01


def curve_project():
    a1o = sample_arc(C1, A1["outerRadius"], A1["startAngle"], A1["endAngle"], A1["direction"])
    a1i = sample_arc(C1, A1["innerRadius"], A1["startAngle"], A1["endAngle"], A1["direction"])
    a2i = sample_arc(C2, A2["innerRadius"], A2["startAngle"], A2["endAngle"], A2["direction"])
    a2o = sample_arc(C2, A2["outerRadius"], A2["startAngle"], A2["endAngle"], A2["direction"])

    edge_a = [[0.0, S_ENTRY], [0.0, 0.0]] + a1o[1:] + a2i[1:] + [[S_EXIT_INNER_X, S_EXIT_Y - S_EXIT]]
    edge_b = [[S["roadWidth"], S_ENTRY], [S["roadWidth"], 0.0]] + a1i[1:] + a2o[1:] + [[S_EXIT_OUTER_X, S_EXIT_Y - S_EXIT]]

    def band(lid, path):
        l, r = offset_band(path, LINE_W, s_flat)
        return {"id": lid, "kind": "edge", "judge": "wheel", "width": LINE_W,
                "left": l, "right": r}

    lines = [band("curve_edge_A", edge_a), band("curve_edge_B", edge_b)]

    allpts = edge_a + edge_b
    xs = [p[0] for p in allpts]
    ys = [p[1] for p in allpts]
    m = 1.5
    ground = {"type": "polygon", "points": [
        [min(xs) - m, min(ys) - m, 0.0], [max(xs) + m, min(ys) - m, 0.0],
        [max(xs) + m, max(ys) + m, 0.0], [min(xs) - m, max(ys) + m, 0.0]]}

    arcs = [
        {"id": "arc1", "center": C1, "outerRadius": A1["outerRadius"],
         "innerRadius": A1["innerRadius"], "startAngle": A1["startAngle"],
         "endAngle": A1["endAngle"], "direction": A1["direction"]},
        {"id": "arc2", "center": C2, "outerRadius": A2["outerRadius"],
         "innerRadius": A2["innerRadius"], "startAngle": A2["startAngle"],
         "endAngle": A2["endAngle"], "direction": A2["direction"]},
    ]

    ann = [
        dim("top", [C1[0], C1[1]], [C1[0], C1[1] - A1["outerRadius"]],
            "外圆半径 R=7.50 m", [C1[0] + 2.1, -3.6]),
        dim("top", [0.0, 1.8], [S["roadWidth"], 1.8],
            "路宽 b=3.50 m", [1.75, 2.65]),
        dim("top", C1, C2, "两圆心距 11.50 m = R + r", [12.4, -5.6]),
        note("top", "两段反向弧各 135°（3/8 圆周），内圆 4.00 m",
             [6.0, -12.6], leader=[10.5, -3.9]),
    ]
    return {"label": S["label"], "ground": ground, "lines": lines, "poles": [],
            "arcs": arcs, "annotations": ann}


# ---------- 直角转弯 ----------
R = P["right_angle"]
RL, RB = R["approachLength"], R["roadWidth"]


def ra_flat(x, y=0.0):
    return 0.01


def right_angle_project():
    outer = [[0.0, 0.0], [RL, 0.0], [RL, RL]]
    inner = [[0.0, RB], [RL - RB, RB], [RL - RB, RL]]

    def band(lid, path):
        l, r = offset_band(path, LINE_W, ra_flat)
        return {"id": lid, "kind": "edge", "judge": "wheel", "width": LINE_W,
                "left": l, "right": r}

    lines = [band("ra_edge_outer", outer), band("ra_edge_inner", inner)]
    ground = {"type": "polygon", "points": [
        [0.0, 0.0, 0.0], [RL, 0.0, 0.0], [RL, RL, 0.0],
        [RL - RB, RL, 0.0], [RL - RB, RB, 0.0], [0.0, RB, 0.0]]}

    ann = [
        dim("top", [0.0, -0.95], [RL, -0.95],
            "转弯前直段 l=6.71 m（任务表）", [RL / 2, -1.75]),
        dim("top", [-0.95, 0.0], [-0.95, RB],
            "路宽 b=3.60 m", [-2.6, 2.6]),
        dim("top", [RL + 0.95, 0.0], [RL + 0.95, RL],
            "直角边长 l=6.71 m", [RL + 3.4, RL / 2]),
        note("top", "内角 90° 尖角（图11 无倒角）", [2.4, RL + 1.5],
             leader=[RL - RB, RB]),
    ]
    return {"label": R["label"], "ground": ground, "lines": lines, "poles": [],
            "arcs": [], "annotations": ann}


# ---------- 输出 ----------
doc = {
    "meta": {
        "schema": "outline/0.1",
        "generatedFrom": "track/track.wang.json",
        "owner": T["owner"],
        "week": T["week"],
        "units": T["units"],
        "frame": T["frame"],
        "tol": T["frame"]["tol"],
        "markingWidth": LINE_W,
        "content": "仅地面与标线（坡道另有 2 根桩杆）；无材质、无灯光、无贴图",
        "analyticNote": "曲线 arcs 为解析圆，判定层必须使用它；lines 中的折线只供显示与 Canvas 2D，勿用于判定",
        "sources": T["sourcePriority"],
        "canvas2d": {
            "contract": "docs/CANVAS2D_CONTRACT.md",
            "coordinates": "局部米制；top 视图直接取 [x,y]，y 向上；Canvas 2D 需做 y 翻转与缩放",
            "primitives": "lines[].left/right 组成条带，按顺序 lineTo 闭合即可；arcs 可用 ctx.arc"
        }
    },
    "projects": {
        "hill_start": hill_project(),
        "s_curve": curve_project(),
        "right_angle": right_angle_project(),
    },
    "openQuestions": T["openQuestions"],
}

os.makedirs(OUT_DIR, exist_ok=True)
with open(os.path.join(OUT_DIR, "outline.json"), "w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False, indent=2)
with open(os.path.join(OUT_DIR, "outline.js"), "w", encoding="utf-8") as f:
    f.write("// 自动生成，勿手改。源：track/track.wang.json -> scripts/generate_outline.py\n")
    f.write("window.TRACK_OUTLINE = ")
    json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
    f.write(";\n")

for name, proj in doc["projects"].items():
    print(f"{name}: ground={proj['ground']['type']} lines={len(proj['lines'])} "
          f"poles={len(proj['poles'])} arcs={len(proj['arcs'])} "
          f"annotations={len(proj['annotations'])}")
print("已写出 outline/outline.json 与 outline/outline.js")
