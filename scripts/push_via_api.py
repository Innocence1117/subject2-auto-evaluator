#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通过 GitHub Git Data API 把本地 main / assets 两个分支推到组长仓库。

为什么不用 git push：
  当前环境里 github.com 的 CONNECT 隧道被代理拒绝（502），git 传输层不通；
  但 api.github.com 可达，所以改用 REST Git Data API 直接建 blob/tree/commit/ref。

分支策略（不覆盖组长的 main）：
  远程 assets            <- 本地 assets（完整交付：脚本/文档/渲染图/坐标/测试 + 3 个 .blend）
  远程 wang-white-models <- 本地 main  （同上，但不含 .blend，便于审阅 diff）
  远程 main              <- 保持不动

Token 获取（classic PAT 最简单）：
  https://github.com/settings/tokens/new  勾选 public_repo（本仓库是 public）
  或 fine-grained PAT：只选 Innocence1117/subject2-auto-evaluator，Contents: Read & Write
  不要把 token 贴进聊天，保存到 .github_token 文件或用环境变量 GITHUB_TOKEN。

用法：
  python scripts/push_via_api.py --dry-run
  python scripts/push_via_api.py
  python scripts/push_via_api.py --token-file C:/path/to/token.txt
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "https://api.github.com"
DEFAULT_REPO = "Innocence1117/subject2-auto-evaluator"

# (远程分支, 本地分支, 提交信息)
PLAN = [
    ("wang-white-models", "main",
     "W0 白模交付：尺寸真相源、Blender 脚本、4 张标注正交图、Canvas 2D 契约与测试\n\n"
     "不含 .blend（3D 资产按本周纪律只放 assets 分支）。\n"
     "尺寸依据见 docs/DIMENSIONS.md，几何唯一真相源为 track/track.wang.json。"),
    ("assets", "assets",
     "assets: 三个场地 Blender 白模（坡道/曲线/直角）\n\n"
     "hill_start.blend / s_curve.blend / right_angle.blend\n"
     "仅地面 + 标线，0 材质 / 0 灯光 / 0 贴图；尺寸全部由 track.json -> outline.json 生成。"),
]


def git(*args: str) -> bytes:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, stdout=subprocess.PIPE
    ).stdout


def branch_files(branch: str) -> dict[str, bytes]:
    """从 git 对象库读文件，不依赖当前工作区 checkout 状态。"""
    out = git("ls-tree", "-r", "-z", branch)
    files: dict[str, bytes] = {}
    for rec in out.split(b"\0"):
        if not rec:
            continue
        meta, path = rec.split(b"\t", 1)
        sha = meta.split()[2].decode()
        files[path.decode("utf-8")] = git("cat-file", "blob", sha)
    return files


def gh(method: str, path: str, token: str, payload=None, allow_404=False):
    url = API + path
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "subject2-white-model-uploader",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        if allow_404 and e.code == 404:
            return None
        detail = e.read().decode("utf-8", "ignore")[:900]
        hint = ""
        if e.code in (401, 403):
            hint = ("\n提示：token 无效或权限不足。classic PAT 需 public_repo 权限；"
                    "fine-grained PAT 需选中本仓库并给 Contents: Read & Write；"
                    "账号需已接受仓库邀请成为协作者。")
        raise SystemExit(f"GitHub API {method} {path} -> HTTP {e.code}{hint}\n{detail}")
    except urllib.error.URLError as e:
        raise SystemExit(f"网络错误 {method} {path}: {e.reason}\n"
                        "（api.github.com 需可达；当前环境已验证可达）")


def read_token(explicit: str | None) -> str:
    if explicit:
        p = Path(explicit)
        if not p.exists():
            raise SystemExit(f"token 文件不存在：{p}")
        return p.read_text(encoding="utf-8").strip()
    for var in ("GITHUB_TOKEN", "GH_TOKEN"):
        if os.environ.get(var, "").strip():
            return os.environ[var].strip()
    p = ROOT / ".github_token"
    if p.exists():
        return p.read_text(encoding="utf-8").strip()
    raise SystemExit(
        "未找到 GitHub token。三选一：\n"
        f"  1) 写入 {p}（已加入 .gitignore，不会提交）\n"
        "  2) 设置环境变量 GITHUB_TOKEN\n"
        "  3) --token-file <路径>\n"
        "生成地址：https://github.com/settings/tokens/new  （classic PAT 勾 public_repo）"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=DEFAULT_REPO, help="owner/repo")
    ap.add_argument("--token-file", default=None)
    ap.add_argument("--dry-run", action="store_true", help="只打印计划，不写远端")
    args = ap.parse_args()

    for local in ("main", "assets"):
        if subprocess.run(["git", "rev-parse", "--verify", local], cwd=ROOT,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
            raise SystemExit(f"缺少本地分支 {local}")

    print(f"目标仓库 : https://github.com/{args.repo}")
    print("分支映射 :")
    for remote, local, _ in PLAN:
        n = len(branch_files(local))
        size = sum(len(v) for v in branch_files(local).values())
        print(f"  本地 {local:<7} -> 远程 {remote:<20} {n:>2} 文件 / {size/1024/1024:.2f} MiB")
    print("  远程 main 保持不动（组长的 README 不会被覆盖）")

    if args.dry_run:
        print("\n[dry-run] 未发起任何写操作。")
        return 0

    token = read_token(args.token_file)
    who = gh("GET", "/user", token)
    print(f"\n认证身份 : {who.get('login')}  (name: {who.get('name') or '-'})")

    base = gh("GET", f"/repos/{args.repo}/git/ref/heads/main", token)
    base_sha = base["object"]["sha"]
    base_tree = gh("GET", f"/repos/{args.repo}/git/commits/{base_sha}", token)["tree"]["sha"]
    print(f"基线提交 : {base_sha[:10]}（远程 main）")

    blob_cache: dict[bytes, str] = {}
    for remote_branch, local_branch, message in PLAN:
        files = branch_files(local_branch)
        entries = []
        for i, (path, data) in enumerate(sorted(files.items()), 1):
            if data not in blob_cache:
                r = gh("POST", f"/repos/{args.repo}/git/blobs", token,
                       {"content": base64.b64encode(data).decode("ascii"), "encoding": "base64"})
                blob_cache[data] = r["sha"]
            entries.append({"path": path, "mode": "100644", "type": "blob",
                            "sha": blob_cache[data]})
            if i % 10 == 0 or i == len(files):
                print(f"  [{remote_branch}] blob {i}/{len(files)}")

        tree = gh("POST", f"/repos/{args.repo}/git/trees", token,
                  {"base_tree": base_tree, "tree": entries})
        commit = gh("POST", f"/repos/{args.repo}/git/commits", token,
                    {"message": message, "tree": tree["sha"], "parents": [base_sha]})
        ref_path = f"/repos/{args.repo}/git/ref/heads/{remote_branch}"
        if gh("GET", ref_path, token, allow_404=True) is None:
            gh("POST", f"/repos/{args.repo}/git/refs", token,
               {"ref": f"refs/heads/{remote_branch}", "sha": commit["sha"]})
            action = "新建"
        else:
            gh("PATCH", ref_path, token, {"sha": commit["sha"], "force": False})
            action = "更新"
        print(f"  [{remote_branch}] {action}成功 commit={commit['sha'][:10]}")

    print("\n完成。链接：")
    for remote, _, _ in PLAN:
        print(f"  https://github.com/{args.repo}/tree/{remote}")
    print(f"  3 个白模：https://github.com/{args.repo}/tree/assets/white_models")
    return 0


if __name__ == "__main__":
    sys.exit(main())
