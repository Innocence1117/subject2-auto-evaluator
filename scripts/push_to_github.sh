#!/usr/bin/env bash
# 把本地 main + assets 两个分支推到 GitHub。
# 用法： ./scripts/push_to_github.sh git@github.com:<org>/<repo>.git
# 前置：本机已配置 git 身份，且对目标仓库有推送权限（SSH key 或 credential helper）。
set -euo pipefail

REMOTE="${1:-}"
if [[ -z "$REMOTE" ]]; then
  echo "用法: $0 <git remote url>"
  echo "例:   $0 git@github.com:team/subject2.git"
  exit 1
fi

cd "$(dirname "$0")/.."

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "ERROR: 当前目录不是 git 仓库"; exit 1
fi
if [[ -z "$(git config user.name)" || -z "$(git config user.email)" ]]; then
  echo "ERROR: 请先配置 git 身份："
  echo "  git config user.name  \"王梓钰\""
  echo "  git config user.email \"wzy-2008@users.noreply.github.com\""
  exit 1
fi

if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "$REMOTE"
else
  git remote add origin "$REMOTE"
fi

for b in main assets; do
  if ! git rev-parse --verify "$b" >/dev/null 2>&1; then
    echo "ERROR: 缺少本地分支 $b"; exit 1
  fi
done

git push -u origin main
git push -u origin assets

echo ""
echo "已推送："
git remote get-url origin
git ls-remote --heads origin main assets
echo ""
echo "发群内容（对外口径用「计划完成」）："
echo "  assets 分支：3 个场地白模（坡道/曲线/直角）"
echo "  main 分支：4 张带尺寸的正交渲染图 + 轮廓坐标 + 测试"
