#!/bin/bash
# 把这个文件夹复制到电脑上已有的 Skill 目录（Claude Code / Codex / WorkBuddy）。
cd "$(dirname "$0")" || exit 1
SRC="$(pwd)"
NAME="mistake-workbench"
done_any=0
for base in "$HOME/.claude/skills" "$HOME/.codex/skills" "$HOME/.workbuddy/skills" "$HOME/.agents/skills"; do
  if [ -d "$base" ]; then
    rm -rf "$base/$NAME"
    mkdir -p "$base/$NAME"
    cp -R "$SRC"/. "$base/$NAME"/
    rm -rf "$base/$NAME/.git"
    echo "已安装到 $base/$NAME"
    done_any=1
  fi
done
if [ "$done_any" = 0 ]; then
  mkdir -p "$HOME/.claude/skills/$NAME"
  cp -R "$SRC"/. "$HOME/.claude/skills/$NAME"/
  echo "没找到已有的 Skill 目录，已装到 $HOME/.claude/skills/$NAME"
fi
echo
echo "装好了。打开你的 AI（Claude Code / Codex / WorkBuddy），选中一个空文件夹，说：错题工作台，帮我分析这套卷子"
read -r -p "按回车关闭 " _
