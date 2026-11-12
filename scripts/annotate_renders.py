#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在 Blender 正交渲染图上叠加尺寸标注，产出本周要发群里的 4 张图。

标注坐标与白模几何同源（outline/outline.json），并用 renders/cameras.json
里的相机参数做精确的世界坐标 -> 像素坐标变换，不是手画。
"""
import json
import math
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTLINE = os.path.join(ROOT, "outline", "outline.json")
CAMERAS = os.path.join(ROOT, "renders", "cameras.json")
RENDER_DIR = os.path.join(ROOT, "renders")

FONT_PATH = "C:/Windows/Fonts/simhei.ttf"
if not os.path.exists(FONT_PATH):
    FONT_PATH = "C:/Windows/Fonts/simsun.ttc"

BLUE = (24, 88, 165)
BLUE_LIGHT = (214, 229, 246)
INK = (28, 32, 38)
GRAY = (95, 103, 112)
WHITE = (255, 255, 255)

PAD_TOP, PAD_BOTTOM = 130, 86

TITLES = {
    "hill_top": "坡道定点停车与起步 · 俯视正交图",
    "hill_section": "坡道定点停车与起步 · 侧视剖面图",
    "s_curve_top": "曲线行驶 · 俯视正交图",
    "right_angle_top": "直角转弯 · 俯视正交图",
}
SUBTITLE = "白模：仅地面与标线，无材质 / 光照 / 贴图　·　单位 m　·　计划完成，待组内尺寸确认"
FOOTER = ("尺寸依据：GA 1029—2022 表10/11/12、图9/10/11　·　"
          "GA 1026—2022 5.2 / 6.2.3　·　规则表 v0.4　·　本周任务分配 v3　|　王梓钰 2026-11-15")

with open(OUTLINE, "r", encoding="utf-8") as f:
    DOC = json.load(f)
with open(CAMERAS, "r", encoding="utf-8") as f:
    CAMS = json.load(f)


def fnt(size):
    return ImageFont.truetype(FONT_PATH, size)


def w2p(cam, p):
    res_x, res_y = cam["res"]
    cx, cy = cam["center"]
    s = cam["pxPerMeter"]
    return (res_x / 2.0 + (p[0] - cx) * s,
            res_y / 2.0 - (p[1] - cy) * s + PAD_TOP)


def text_box(draw, pos, text, font, fill=INK, box=WHITE, outline=BLUE_LIGHT, pad=7):
    x, y = pos
    bb = draw.textbbox((0, 0), text, font=font)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    left, top = x - w / 2 - pad, y - h / 2 - pad
    right, bottom = x + w / 2 + pad, y + h / 2 + pad
    draw.rounded_rectangle([left, top, right, bottom], radius=5,
                           fill=box, outline=outline, width=1)
    draw.text((x - w / 2, y - h / 2 - bb[1]), text, font=font, fill=fill)
    return left, top, right, bottom


def arrow(draw, tip, direction, color=BLUE, size=9):
    dx, dy = direction
    n = math.hypot(dx, dy)
    if n < 1e-6:
        return
    ux, uy = dx / n, dy / n
    px, py = -uy, ux
    a = (tip[0] - ux * size + px * size * 0.45, tip[1] - uy * size + py * size * 0.45)
    b = (tip[0] - ux * size - px * size * 0.45, tip[1] - uy * size - py * size * 0.45)
    draw.polygon([tip, a, b], fill=color)


def draw_dim(draw, cam, a, font):
    p1 = w2p(cam, a["p1"])
    p2 = w2p(cam, a["p2"])
    draw.line([p1, p2], fill=BLUE, width=2)
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    n = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / n, dx / n
    for p in (p1, p2):
        draw.line([(p[0] - nx * 8, p[1] - ny * 8),
                   (p[0] + nx * 8, p[1] + ny * 8)], fill=BLUE, width=2)
    arrow(draw, p1, (dx, dy))
    arrow(draw, p2, (-dx, -dy))
    lp = w2p(cam, a["labelPos"])
    if a.get("leader"):
        ld = w2p(cam, a["leader"])
        draw.line([lp, ld], fill=BLUE, width=1)
        draw.ellipse([ld[0] - 3, ld[1] - 3, ld[0] + 3, ld[1] + 3], fill=BLUE)
    text_box(draw, lp, a["label"], font, fill=BLUE)


def draw_note(draw, cam, a, font):
    lp = w2p(cam, a["labelPos"])
    ld = w2p(cam, a["leader"])
    draw.line([lp, ld], fill=BLUE, width=1)
    draw.ellipse([ld[0] - 4, ld[1] - 4, ld[0] + 4, ld[1] + 4], fill=BLUE)
    text_box(draw, lp, a["label"], font, fill=BLUE)


def scale_bar(draw, cam, res_x, canvas_h):
    s = cam["pxPerMeter"]
    length = 2.0 * s
    x1 = res_x - 46
    x0 = x1 - length
    y = canvas_h - PAD_BOTTOM - 30
    draw.line([(x0, y), (x1, y)], fill=INK, width=3)
    for x in (x0, x1):
        draw.line([(x, y - 6), (x, y + 6)], fill=INK, width=3)
    draw.text((x0, y - 26), "2 m", font=fnt(18), fill=INK)


for name, cam in CAMS.items():
    clean_path = os.path.join(ROOT, cam["clean"])
    clean = Image.open(clean_path).convert("RGB")
    res_x, res_y = cam["res"]
    canvas_h = res_y + PAD_TOP + PAD_BOTTOM
    canvas = Image.new("RGB", (res_x, canvas_h), WHITE)
    canvas.paste(clean, (0, PAD_TOP))
    draw = ImageDraw.Draw(canvas)

    # 页眉 / 页脚
    draw.text((34, 22), TITLES[name], font=fnt(34), fill=INK)
    draw.text((34, 70), SUBTITLE, font=fnt(19), fill=GRAY)
    draw.line([(34, 104), (res_x - 34, 104)], fill=(225, 229, 234), width=2)
    draw.line([(34, canvas_h - PAD_BOTTOM + 8), (res_x - 34, canvas_h - PAD_BOTTOM + 8)],
              fill=(225, 229, 234), width=2)
    draw.text((34, canvas_h - PAD_BOTTOM + 24), FOOTER, font=fnt(18), fill=GRAY)

    proj = DOC["projects"][cam["project"]]
    anns = [a for a in proj["annotations"] if a["view"] == cam["view"]]
    for a in anns:
        if a["kind"] == "dim":
            draw_dim(draw, cam, a, fnt(21))
        else:
            draw_note(draw, cam, a, fnt(21))
    scale_bar(draw, cam, res_x, canvas_h)

    out = os.path.join(RENDER_DIR, name + ".png")
    canvas.save(out)
    print("已标注:", name, "->", os.path.relpath(out, ROOT),
          "尺寸标注 %d 条" % len(anns))
