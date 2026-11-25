# -*- coding: utf-8 -*-
"""合并工作台生成器（可选工具）
把多科的单科工作台合并成一个带科目切换条的工作台网页。
用法示例：
  python build_merged.py \
    --subject 数学 --root D:/小学/错题本/数学错题/孩子 --skill D:/skills/mistake-workbench \
    --subject 语文 --root D:/小学/错题本/语文错题/孩子 --skill D:/skills/chinese-workbench \
    --subject 英语 --root D:/小学/错题本/英语错题/孩子 --skill D:/skills/english-workbench \
    --out D:/小学/错题本/孩子的错题工作台.html
前提：各科先用本科目的 workbench.py build 生成过 工作台.html（本脚本会自动重新 build 刷新）。"""
import argparse, json, re, subprocess, sys
from pathlib import Path

def build_one(root, skill):
    script = Path(skill) / "scripts" / "workbench.py"
    r = subprocess.run([sys.executable, str(script), "build", "--root", str(root)],
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError(f"build 失败: {r.stderr[-500:]}")
    html = (Path(root) / "工作台.html").read_text(encoding="utf-8")
    m = re.search(r'<script id="payload" type="application/json">(.*?)</script>', html, re.S)
    if not m:
        raise RuntimeError(f"未找到 payload: {root}")
    return json.loads(m.group(1))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", action="append", required=True, help="科目名（可多次）")
    ap.add_argument("--root", action="append", required=True, help="该科目档案根目录（与科目一一对应）")
    ap.add_argument("--skill", action="append", required=True, help="该科目 skill 目录")
    ap.add_argument("--out", required=True, help="输出 HTML 路径")
    a = ap.parse_args()
    if not (len(a.subject) == len(a.root) == len(a.skill)):
        sys.exit("--subject/--root/--skill 数量必须一致")
    merged = {}
    for name, root, skill in zip(a.subject, a.root, a.skill):
        p = build_one(root, skill)
        merged[name] = p
        print(f"{name}: {len(p.get('notes', []))} 笔记, {len(p.get('quiz', []))} 题")
    tpl = (Path(a.skill[0]) / "assets" / "workbench.html").read_text(encoding="utf-8")
    html = tpl.replace("__WORKBENCH_PAYLOAD__", json.dumps({"subjects": merged}, ensure_ascii=False))
    out = Path(a.out)
    out.write_text(html, encoding="utf-8")
    print(f"✅ 合并工作台: {out}  ({out.stat().st_size // 1024} KB)")

if __name__ == "__main__":
    main()
