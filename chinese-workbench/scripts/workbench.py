#!/usr/bin/env python3
"""语文错题工作台 · 本地 Markdown 档案工具。没有服务器、数据库或模型密钥。

命令：init / profile / list / check / build / media / append / pdf
语文版：课标四板块+六任务群；三层映射（需巩固/已具备/未覆盖）。
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

SCHEMA = 'sophie-chinese-workbench-v1'
SECTIONS = ('卷子', '错题', '易错点', '维度', '盲区', '练习', '日志', '档案')
MEDIA = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.pdf', '.mp3', '.m4a', '.wav', '.ogg', '.mp4', '.html', '.docx'}
WIKI = re.compile(r'(!?)\[\[([^\]\n]+)\]\]')
GENERATED = '<!-- generated: sophie-chinese-workbench-v1 -->'
LEVELS = ('扎实', '基本掌握', '需加强', '未考察')
TIERS = ('需巩固', '已具备', '未覆盖')
PITFALL_STATUS = ('活跃', '减少', '消失', '历史')
BLIND_STATUS = ('未覆盖', '已补练', '已有练习')
PRACTICE_STATUS = ('待作答', '已作答')
REQUIRED = {
    '卷子': ('id', 'subject', 'grade', 'unit', 'date', 'kind'),
    '错题': ('id', 'subject', 'grade', 'unit', 'date', 'status', 'cause', 'dimension'),
    '易错点': ('id', 'name', 'subject', 'dimension', 'cause', 'status', 'first_seen', 'last_seen'),
    '维度': ('subject', 'dimension', 'group', 'level', 'updated'),
    '盲区': ('id', 'name', 'subject', 'task_group', 'status', 'source'),
    '练习': ('id', 'subject', 'date', 'status', 'targets'),
}
SCORE = re.compile(r'(\d+\s*分(?![钟析类配开别工布段支离母数解]))|(等级\s*[：:]\s*[ABCDabcd优良中差])|(\d+\s*分\s*[/／]\s*\d+)')


def ensure_dir(path):
    path.mkdir(parents=True, exist_ok=True)
    if not path.is_dir():
        raise ValueError('这应当是文件夹：' + str(path))


def within(root, relative):
    rel = Path(relative)
    if rel.is_absolute() or '..' in rel.parts or '\\' in str(relative) or ':' in str(relative):
        raise ValueError('只接受档案内相对路径：' + str(relative))
    target = root / rel
    try:
        target.resolve().relative_to(root.resolve())
    except ValueError:
        raise ValueError('链接越出了档案：' + str(relative))
    return target


def require_vault(root):
    marker = within(root, '.错题工作台.json')
    if not marker.is_file():
        raise ValueError('该目录还没有初始化为错题工作台。请先核对目录并运行 init。')
    if json.loads(marker.read_text(encoding='utf-8')).get('schema') != SCHEMA:
        raise ValueError('无法识别档案版本，不覆盖现有目录。')


START_TEXT = '''# 语文错题工作台

这里保存孩子的语文卷子、错题、能力点、课标维度、盲区、练习和日志。新增材料和分析在选中这个文件夹的 AI 对话里进行；「工作台.html」是从这些 Markdown 生成的查看页。

## 孩子信息
<!-- profile:start -->
- 称呼：（未填）
- 年级学期：（未填）
- 语文教材：（未填）
<!-- profile:end -->

## 当前状态
（AI 每次整理后更新：最近一次整理、需巩固能力点、待作答练习、当前提升点）

## 怎么用
- 发卷子或错题照片，说「语文错题工作台，整理这张卷子」。
- 说「出练习」，得到孩子版和妈妈版两份可打印文档。
- 孩子做完拍照发回，说「批改练习」。
- 说「更新工作台」，重新生成页面。
- 说「看课标覆盖」，查六任务群哪些考过、哪些是盲区。

## 接续约定
AI 每次先读「开始.md」、相关卷子、能力点和最近日志再继续；不把聊天记忆当成已保存的档案。**口述优先**：具体错字、扣分、选项、篇名一律以家长口述为准，绝不用读图结果质疑口述。观察和推测分开写；不写分数和等级，只写掌握程度；出了题不算练了，家长说懂了不算掌握了。
'''


PROFILE_KEYS = ('child', 'grade', 'textbook')
PROFILE_LABELS = {'child': '称呼', 'grade': '年级学期', 'textbook': '语文教材'}


def title_of(root):
    pf = read_profile(root)
    child = pf.get('child', '')
    return (child + '的' if child else '') + '语文错题工作台'


def read_profile(root):
    marker = within(root, '.错题工作台.json')
    if not marker.is_file():
        return {}
    return json.loads(marker.read_text(encoding='utf-8')).get('profile', {})


def write_profile(root, values):
    require_vault(root)
    marker = within(root, '.错题工作台.json')
    data = json.loads(marker.read_text(encoding='utf-8'))
    profile = data.get('profile', {})
    for key in PROFILE_KEYS:
        if values.get(key):
            profile[key] = values[key].strip()
    data['profile'] = profile
    data['profile_updated'] = dt.date.today().isoformat()
    marker.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    start = within(root, '开始.md')
    text = start.read_text(encoding='utf-8') if start.exists() else START_TEXT
    block = '<!-- profile:start -->\n' + '\n'.join('- %s：%s' % (PROFILE_LABELS[k], profile.get(k, '（未填）')) for k in PROFILE_KEYS) + '\n<!-- profile:end -->'
    if '<!-- profile:start -->' in text and '<!-- profile:end -->' in text:
        text = re.sub(r'<!-- profile:start -->.*?<!-- profile:end -->', lambda m: block, text, count=1, flags=re.S)
    else:
        text = text.replace('## 当前状态', '## 孩子信息\n' + block + '\n\n## 当前状态', 1)
    start.write_text(text, encoding='utf-8')
    return {'root': str(root), 'profile': profile}


def initialize(root, values=None):
    ensure_dir(root)
    marker = within(root, '.错题工作台.json')
    if marker.exists():
        require_vault(root)
    else:
        if any(p for p in root.iterdir() if not p.name.startswith('.')):
            raise ValueError('目标目录不是空目录且没有档案标识，请先核对，不能自动接管。')
        marker.write_text(json.dumps({'schema': SCHEMA, 'created': dt.datetime.now().isoformat(timespec='seconds')}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for name in (*SECTIONS, '附件'):
        ensure_dir(within(root, name))
    start = within(root, '开始.md')
    if not start.exists():
        start.write_text(START_TEXT, encoding='utf-8')
    if values and any(values.get(k) for k in PROFILE_KEYS):
        write_profile(root, values)
    return {'root': str(root), 'start': str(start), 'ready': True, 'profile': read_profile(root)}


def parse_note(root, path):
    text = path.read_text(encoding='utf-8-sig')
    meta, body = {}, text
    if text.startswith('---\n'):
        parts = text.split('\n---\n', 1)
        if len(parts) != 2:
            raise ValueError('属性区没有结束：' + str(path.relative_to(root)))
        for line in parts[0][4:].splitlines():
            if not line.strip() or line.startswith('#'):
                continue
            if ':' not in line or line.startswith((' ', '\t', '-')):
                raise ValueError('请使用一行一个值的属性：' + str(path.relative_to(root)))
            key, value = line.split(':', 1)
            value = value.strip()
            if value.startswith('"'):
                value = json.loads(value)
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
            meta[key.strip()] = value
        body = parts[1]
    title = re.search(r'^#\s+(.+)$', body, re.M)
    relative = path.relative_to(root).as_posix()
    return {'path': relative, 'key': relative[:-3], 'title': title.group(1) if title else path.stem,
            'kind': relative.split('/')[0] if '/' in relative else '说明',
            'meta': meta, 'body': body, 'links': []}


def collect(root):
    require_vault(root)
    paths = [within(root, '开始.md')]
    for name in SECTIONS:
        folder = within(root, name)
        if folder.exists():
            paths.extend(sorted(folder.rglob('*.md')))
    notes, errors = [], []
    for path in paths:
        try:
            notes.append(parse_note(root, within(root, path.relative_to(root).as_posix())))
        except (ValueError, OSError, UnicodeError) as exc:
            errors.append(str(exc))
    ids = {}
    keys = {n['key'] for n in notes}
    pitfall_names = {n['meta'].get('name') for n in notes if n['kind'] == '易错点'}
    pitfall_ids = {n['meta'].get('id') for n in notes if n['kind'] == '易错点'}
    for note in notes:
        meta, kind = note['meta'], note['kind']
        for field in REQUIRED.get(kind, ()):
            if not meta.get(field):
                errors.append(note['path'] + ' 缺少属性 ' + field)
        for key in ('date', 'review_on', 'first_seen', 'last_seen', 'updated'):
            if meta.get(key):
                try:
                    dt.date.fromisoformat(meta[key])
                except ValueError:
                    errors.append(note['path'] + ' 日期格式不正确：' + key)
        if kind == '维度' and meta.get('level') and meta['level'] not in LEVELS:
            errors.append(note['path'] + ' level 只能是：' + ' / '.join(LEVELS))
        if kind == '易错点' and meta.get('status') and meta['status'] not in PITFALL_STATUS:
            errors.append(note['path'] + ' status 只能是：' + ' / '.join(PITFALL_STATUS))
        if kind == '盲区' and meta.get('status') and meta['status'] not in BLIND_STATUS:
            errors.append(note['path'] + ' status 只能是：' + ' / '.join(BLIND_STATUS))
        if kind == '练习' and meta.get('status') and meta['status'] not in PRACTICE_STATUS:
            errors.append(note['path'] + ' status 只能是：' + ' / '.join(PRACTICE_STATUS))
        if kind == '盲区' and meta.get('tier') and meta['tier'] not in TIERS:
            errors.append(note['path'] + ' tier 只能是：' + ' / '.join(TIERS))
        if kind in ('错题', '练习') and meta.get('pitfalls' if kind == '错题' else 'targets'):
            for item in re.split(r'[,，、]\s*', meta.get('pitfalls' if kind == '错题' else 'targets')):
                item = item.strip()
                if item and item not in pitfall_ids and item not in pitfall_names:
                    errors.append(note['path'] + ' 引用了不存在的易错点：' + item)
        if meta.get('id'):
            if meta['id'] in ids:
                errors.append('编号重复：' + meta['id'])
            ids[meta['id']] = note['path']
        if kind in ('维度', '卷子', '易错点', '盲区', '说明'):
            hit = SCORE.search(note['body'])
            if hit:
                errors.append(note['path'] + ' 出现了分数或等级（' + hit.group(0).strip() + '），只写掌握程度')
        for _embedded, raw in WIKI.findall(note['body']):
            target = raw.split('|', 1)[0].split('#', 1)[0].strip()
            try:
                candidate = within(root, target)
                if candidate.suffix.lower() in MEDIA:
                    if not candidate.is_file() or not target.startswith('附件/'):
                        raise ValueError('附件不存在或不在附件目录')
                    note['links'].append({'target': target, 'media': True})
                else:
                    key = target[:-3] if target.endswith('.md') else target
                    if key not in keys:
                        raise ValueError('链接对应的笔记不存在')
                    note['links'].append({'target': key, 'media': False})
            except ValueError as exc:
                errors.append(note['path'] + '：' + target + '（' + str(exc) + '）')
    return notes, list(dict.fromkeys(errors))


def events_from(body):
    out = []
    for line in body.splitlines():
        m = re.match(r'^\s*[-*]\s+(\d{4}-\d{2}-\d{2})\s*[：:·]?\s*(.*)$', line)
        if m:
            out.append({'date': m.group(1), 'text': m.group(2).strip()})
    return out


def read_images(root, notes):
    """把笔记引用的附件图片内嵌成 data URI，缩到合适尺寸，保证任何预览方式都能看清。"""
    import base64, io
    try:
        from PIL import Image
    except ImportError:
        Image = None
    targets = set()
    for n in notes:
        for _emb, raw in WIKI.findall(n['body']):
            t = raw.split('|', 1)[0].split('#', 1)[0].strip()
            if Path(t).suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'} and t.startswith('附件/'):
                targets.add(t)
        img = n['meta'].get('image', '')
        if img and Path(img).suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'}:
            targets.add(img)
    out = {}
    for t in sorted(targets):
        p = within(root, t)
        if not p.is_file() or p.stat().st_size > 25 * 1024 * 1024:
            continue
        try:
            if Image:
                im = Image.open(p).convert('RGB')
                im.thumbnail((1500, 1500))
                buf = io.BytesIO()
                im.save(buf, format='JPEG', quality=82)
                data = buf.getvalue()
            else:
                data = p.read_bytes()
            out[t] = 'data:image/jpeg;base64,' + base64.b64encode(data).decode('ascii')
        except (OSError, ValueError):
            continue
    return out


def read_quiz(root):
    """读 档案/闯关题库.md 里的 json 代码块，供工作台闯关页随机出题。"""
    path = within(root, '档案/闯关题库.md')
    if not path.is_file():
        return []
    text = path.read_text(encoding='utf-8')
    match = re.search(r'```json\s*([\s\S]*?)```', text)
    if not match:
        return []
    try:
        items = json.loads(match.group(1))
    except ValueError:
        return []
    return items if isinstance(items, list) else []


def build(root):
    notes, errors = collect(root)
    if errors:
        raise ValueError('\n'.join(errors))
    for n in notes:
        if n['kind'] == '易错点':
            n['events'] = events_from(n['body'])
    target = within(root, '工作台.html')
    if target.exists() and GENERATED not in target.read_text(encoding='utf-8')[:200]:
        raise ValueError('已存在同名页面且并非本工具生成，不能覆盖。')
    template = Path(__file__).resolve().parent.parent / 'assets' / 'workbench.html'
    payload = json.dumps({'title': title_of(root), 'profile': read_profile(root), 'builtAt': dt.datetime.now().isoformat(timespec='seconds'), 'notes': notes, 'quiz': read_quiz(root), 'images': read_images(root, notes)}, ensure_ascii=False)
    payload = payload.replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    html = template.read_text(encoding='utf-8')
    if html.count('__WORKBENCH_PAYLOAD__') != 1:
        raise ValueError('页面模板占位不唯一。')
    target.write_text(html.replace('__WORKBENCH_PAYLOAD__', payload), encoding='utf-8')
    return {'page': str(target), 'uri': target.as_uri(), 'notes': len(notes)}


def copy_media(root, source, name=None):
    require_vault(root)
    source = source.expanduser().resolve()
    suffix = source.suffix.lower()
    if suffix not in MEDIA or not source.is_file():
        raise ValueError('不支持的附件类型或附件不存在。')
    if source.stat().st_size > 100 * 1024 * 1024:
        raise ValueError('附件超过 100 MB。')
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    base = name if name else digest[:24]
    if '/' in base or base.startswith('.'):
        raise ValueError('附件名只能是文件名。')
    if name and not base.lower().endswith(suffix):
        base += suffix
    destination = within(root, '附件/' + base)
    ensure_dir(destination.parent)
    if destination.exists():
        if hashlib.sha256(destination.read_bytes()).hexdigest() != digest:
            raise ValueError('附件名称冲突，不覆盖：' + base)
    else:
        shutil.copy2(source, destination)
    return {'relative_path': destination.relative_to(root).as_posix(), 'sha256': digest}


def append_note(root, relative, addition):
    require_vault(root)
    path = within(root, relative)
    if path.suffix != '.md' or not path.is_file() or path.parts[-2] == '附件':
        raise ValueError('只能追加到档案中已存在的 Markdown 笔记。')
    text = addition.read_text(encoding='utf-8')
    if not text.strip():
        raise ValueError('追加内容为空。')
    with path.open('a', encoding='utf-8') as handle:
        handle.write('\n\n' + text.rstrip() + '\n')
    return {'appended': str(path), 'characters': len(text)}


CHROME = [
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
    'google-chrome', 'chromium', 'chromium-browser', 'msedge',
    r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
]


def to_pdf(html, pdf):
    html = html.expanduser().resolve()
    pdf = pdf.expanduser().resolve()
    if html.suffix.lower() != '.html' or not html.is_file():
        raise ValueError('要打印的必须是已存在的 .html 文件。')
    exe = next((c for c in CHROME if (Path(c).is_file() or shutil.which(c))), None)
    if not exe:
        raise ValueError('没找到 Chrome / Chromium / Edge，无法打印 PDF；可以在浏览器里打开 HTML 用「打印 → 存为 PDF」。')
    cmd = [exe, '--headless=new', '--no-sandbox', '--disable-gpu', '--no-pdf-header-footer',
           '--print-to-pdf=' + str(pdf), html.as_uri()]
    run = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if not pdf.is_file() or pdf.stat().st_size < 1000:
        raise ValueError('PDF 没有生成：' + (run.stderr or run.stdout)[-400:])
    return {'pdf': str(pdf), 'bytes': pdf.stat().st_size}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('init', 'profile', 'list', 'check', 'build', 'media', 'append'):
        c = commands.add_parser(name)
        c.add_argument('--root', required=True, type=Path)
        if name in ('init', 'profile'):
            c.add_argument('--child', help='孩子的称呼，可用化名')
            c.add_argument('--grade', help='年级学期，如「四年级上」')
            c.add_argument('--textbook', help='数学教材版本，如「北师大版」「人教版」「苏教版」')
        if name == 'media':
            c.add_argument('--source', required=True, type=Path)
            c.add_argument('--name', help='可读的附件文件名，不填则用内容摘要命名')
        if name == 'append':
            c.add_argument('--note', required=True)
            c.add_argument('--text-file', required=True, type=Path)
    p = commands.add_parser('pdf')
    p.add_argument('--html', required=True, type=Path)
    p.add_argument('--pdf', required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'pdf':
            result = to_pdf(args.html, args.pdf)
        else:
            root = args.root.expanduser().resolve()
            if args.command == 'init':
                result = initialize(root, {'child': args.child, 'grade': args.grade, 'textbook': args.textbook})
            elif args.command == 'profile':
                result = write_profile(root, {'child': args.child, 'grade': args.grade, 'textbook': args.textbook})
            elif args.command == 'build':
                result = build(root)
            elif args.command == 'media':
                result = copy_media(root, args.source, args.name)
            elif args.command == 'append':
                result = append_note(root, args.note, args.text_file)
            else:
                notes, errors = collect(root)
                if args.command == 'check':
                    result = {'notes': len(notes), 'errors': errors, 'valid': not errors}
                else:
                    result = {'root': str(root), 'notes': [{k: n[k] for k in ('path', 'title', 'kind', 'meta')} for n in notes], 'errors': errors}
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return 1 if errors else 0
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, UnicodeError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
