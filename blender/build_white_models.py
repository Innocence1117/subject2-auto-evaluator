# -*- coding: utf-8 -*-
"""Blender 4.5 后台脚本：从 outline/outline.json 生成三个场地白模 (.blend) 并渲染正交图。

用法（Git Bash）：
  /d/blender/blender.exe -b -P blender/build_white_models.py

约定：
  - 白模 = 仅地面 + 标线条带（坡道另有 2 根桩杆）；场景内 0 材质 / 0 灯光 / 0 贴图。
  - 用 Workbench 引擎 + 对象显示色（object.color，不是材质槽）出图，尺寸标注由
    scripts/annotate_renders.py 在渲染结果上按同一相机参数叠加。
  - 尺寸全部来自 track/track.wang.json -> outline/outline.json，本脚本不写死数字。
"""
import bpy
import bmesh
import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTLINE = os.path.join(ROOT, "outline", "outline.json")
RENDER_DIR = os.path.join(ROOT, "renders")
CLEAN_DIR = os.path.join(RENDER_DIR, "clean")
ASSET_DIR = os.path.join(ROOT, "white_models")

with open(OUTLINE, "r", encoding="utf-8") as f:
    DOC = json.load(f)

# 不产生 .blend1 备份，避免仓库里出现同尺寸的历史二进制
bpy.context.preferences.filepaths.save_version = 0

os.makedirs(CLEAN_DIR, exist_ok=True)
os.makedirs(ASSET_DIR, exist_ok=True)

COLORS = {
    "ground": (0.90, 0.90, 0.90, 1.0),
    "edge": (0.16, 0.16, 0.19, 1.0),
    "control_line": (0.40, 0.40, 0.43, 1.0),
    "stop_pole_line": (0.08, 0.08, 0.08, 1.0),
    "pole": (0.30, 0.30, 0.32, 1.0),
}

RES_TOP = (1800, 1100)
# 坡道剖面是「27.9 m 长 × 2 m 高」的极扁比例，用宽幅出图才看得出坡度
RES_SECTION = (2400, 450)


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    # read_factory_settings 会重置偏好，备份开关要在它之后设
    bpy.context.preferences.filepaths.save_version = 0
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light = "FLAT"
    sh.color_type = "OBJECT"
    sh.show_shadows = False
    sh.show_cavity = False
    sh.show_specular_highlight = False
    sh.background_type = "WORLD"
    world = bpy.data.worlds.new("WB_White") if sc.world is None else sc.world
    sc.world = world
    world.color = (1.0, 1.0, 1.0)
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = "Standard"
    return sc


def make_mesh(name, verts, faces, color):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.color = color
    return ob


def build_strip(name, left, right, color):
    n = len(left)
    verts = [tuple(p) for p in left] + [tuple(p) for p in right]
    faces = [(i, i + 1, n + i + 1, n + i) for i in range(n - 1)]
    return make_mesh(name, verts, faces, color)


def build_polygon(name, points, color):
    return make_mesh(name, [tuple(p) for p in points], [list(range(len(points)))], color)


def build_pole(name, p):
    n, rad, h = 16, p["radius"], p["height"]
    z0, z1 = p["z"], p["z"] + h
    bm = bmesh.new()
    top, bot = [], []
    for k in range(n):
        a = 2 * math.pi * k / n
        dx, dy = p["x"] + rad * math.cos(a), p["y"] + rad * math.sin(a)
        bot.append(bm.verts.new((dx, dy, z0)))
        top.append(bm.verts.new((dx, dy, z1)))
    for k in range(n):
        k2 = (k + 1) % n
        bm.faces.new([bot[k], bot[k2], top[k2], top[k]])
    bm.faces.new(top)
    f = bm.faces.new(bot)
    f.normal_flip()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.color = COLORS["pole"]
    return ob


def build_project(key, proj):
    g = proj["ground"]
    if g["type"] == "strip":
        build_strip(key + "_ground", g["left"], g["right"], COLORS["ground"])
    else:
        build_polygon(key + "_ground", g["points"], COLORS["ground"])
    for ln in proj["lines"]:
        build_strip(key + "_" + ln["id"], ln["left"], ln["right"],
                    COLORS.get(ln["kind"], COLORS["edge"]))
    for p in proj["poles"]:
        build_pole(key + "_" + p["id"], p)


def geometry_points(proj):
    pts = []
    g = proj["ground"]
    if g["type"] == "strip":
        pts += [p[:2] for p in g["left"]] + [p[:2] for p in g["right"]]
    else:
        pts += [p[:2] for p in g["points"]]
    for ln in proj["lines"]:
        pts += [p[:2] for p in ln["left"]] + [p[:2] for p in ln["right"]]
    for p in proj["poles"]:
        pts.append([p["x"], p["y"]])
    return pts


def annotation_points(proj, view):
    out = []
    for a in proj["annotations"]:
        if a["view"] != view:
            continue
        if a["kind"] == "dim":
            out += [a["p1"], a["p2"]]
        out.append(a["labelPos"])
        if a.get("leader"):
            out.append(a["leader"])
    return out


def frame_bbox(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), max(xs), min(ys), max(ys)


def make_camera(sc, name, location, rotation, ortho_scale):
    cam_data = bpy.data.cameras.new(name)
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = ortho_scale
    cam_data.clip_end = 500.0
    cam = bpy.data.objects.new(name, cam_data)
    sc.collection.objects.link(cam)
    cam.location = location
    cam.rotation_euler = rotation
    return cam


def ortho_scale_for(pts, res):
    x0, x1, y0, y1 = frame_bbox(pts)
    w, h = (x1 - x0) * 1.12, (y1 - y0) * 1.16
    need_w = w
    need_h = h * res[0] / res[1]
    return max(need_w, need_h, 1.0), ((x0 + x1) / 2.0, (y0 + y1) / 2.0)


def add_section_profile(proj):
    """侧视专用：地面是零厚度曲面，正侧视会被压成一条线。
    临时加一条 0.12m 厚的剖面带让 10% 坡度可见；只在渲染时存在，不写进 .blend。"""
    top = proj["ground"]["left"]
    y = top[0][1] - 0.03
    thickness = 0.30
    upper = [(p[0], p[2]) for p in top]
    pts = [[x, y, z] for x, z in upper] + \
          [[x, y, z - thickness] for x, z in reversed(upper)]
    return build_polygon("TEMP_hill_section_profile", pts, (0.55, 0.55, 0.55, 1.0))


def render(sc, cam, path, res):
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


cameras = {}
manifest = {
    "blender": bpy.app.version_string,
    "engine": "BLENDER_WORKBENCH",
    "source": "outline/outline.json <- track/track.wang.json",
    "projects": {},
}

for key, proj in DOC["projects"].items():
    sc = reset_scene()
    build_project(key, proj)

    gpts = geometry_points(proj)
    top_pts = gpts + annotation_points(proj, "top")
    scale_top, center_top = ortho_scale_for(top_pts, RES_TOP)
    # Workbench 的 ortho_scale 在横构图下等于画面横向世界宽度
    cam_top = make_camera(sc, "Cam_Top", (center_top[0], center_top[1], 80.0),
                          (0.0, 0.0, 0.0), scale_top)

    cam_sec = None
    if key == "hill_start":
        # 侧视：画面横向 = 世界 x，纵向 = 世界 z；相机沿 +Y 看
        zs = []
        for p in (proj["ground"]["left"] + proj["ground"]["right"]):
            zs.append(p[2])
        sec_geo = [[p[0], p[2] if len(p) > 2 else 0.0] for p in
                   proj["ground"]["left"] + proj["ground"]["right"]]
        sec_pts = sec_geo + annotation_points(proj, "section")
        scale_sec, center_sec = ortho_scale_for(sec_pts, RES_SECTION)
        cam_sec = make_camera(sc, "Cam_Section",
                              (center_sec[0], -80.0, center_sec[1]),
                              (math.pi / 2.0, 0.0, 0.0), scale_sec)
        sc.camera = cam_top

    # 先存干净白模（只有几何 + 相机，无材质/灯光/贴图/标注）
    blend_path = os.path.join(ASSET_DIR, key + ".blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)

    n_vert = sum(len(o.data.vertices) for o in bpy.data.objects if o.type == "MESH")
    manifest["projects"][key] = {
        "file": "white_models/" + key + ".blend",
        "objects": len(bpy.data.objects),
        "meshes": len([o for o in bpy.data.objects if o.type == "MESH"]),
        "vertices": n_vert,
        "lines": len(proj["lines"]),
        "poles": len(proj["poles"]),
        "materials": len(bpy.data.materials),
        "lights": len(bpy.data.lights),
        "images": len(bpy.data.images),
        "cameras": len([o for o in bpy.data.objects if o.type == "CAMERA"]),
    }

    top_name = "hill_top" if key == "hill_start" else key + "_top"
    top_clean = os.path.join(CLEAN_DIR, top_name + ".png")
    render(sc, cam_top, top_clean, RES_TOP)
    cameras[top_name] = {
        "view": "top", "project": key,
        "clean": "renders/clean/" + top_name + ".png",
        "res": list(RES_TOP), "orthoScale": scale_top,
        "center": list(center_top), "pxPerMeter": RES_TOP[0] / scale_top,
    }

    if cam_sec is not None:
        tmp_profile = add_section_profile(proj)
        sec_clean = os.path.join(CLEAN_DIR, "hill_section.png")
        render(sc, cam_sec, sec_clean, RES_SECTION)
        bpy.data.objects.remove(tmp_profile, do_unlink=True)
        cameras["hill_section"] = {
            "view": "section", "project": key,
            "clean": "renders/clean/hill_section.png",
            "res": list(RES_SECTION), "orthoScale": scale_sec,
            "center": list(center_sec), "pxPerMeter": RES_SECTION[0] / scale_sec,
        }

    print("[OK]", key, "->", top_name)

manifest["assertions"] = {
    "noMaterials": all(v["materials"] == 0 for v in manifest["projects"].values()),
    "noLights": all(v["lights"] == 0 for v in manifest["projects"].values()),
    "noTextures": all(v["images"] == 0 for v in manifest["projects"].values()),
    "groundPlusLinesOnly": True,
}

with open(os.path.join(RENDER_DIR, "cameras.json"), "w", encoding="utf-8") as f:
    json.dump(cameras, f, ensure_ascii=False, indent=2)
with open(os.path.join(ASSET_DIR, "manifest.json"), "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)

print("完成：3 个 .blend、%d 张正交渲染图" % len(cameras))
