# -*- coding: utf-8 -*-
"""生成 README 里的翻译进度表（仅用标准库）

数字来自 tools/progress.json（由 tools/upstream_diff.py --write 更新），
有官方新版文件时也可以现场算：

    python tools/progress.py                      # 打印
    python tools/progress.py --write              # 写回 README 标记区
    python tools/progress.py --upstream ../ext/out --write   # 先按基线重算再写
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import plexio  # noqa: E402

PROG_PATH = os.path.join(HERE, 'progress.json')
README = os.path.join(ROOT, 'README.md')
BEGIN = '<!-- progress:begin -->'
END = '<!-- progress:end -->'


def recount(upstream_dir):
    """现场按官方基线重算改造量"""
    found = plexio.find_upstream(upstream_dir)
    if 'web' not in found or 'mo' not in found:
        raise SystemExit('基线目录里缺 zh_json / plex_mo')
    up_web, _ = plexio.read_json(found['web'])
    up_mo = {k: v for k, v in plexio.read_mo(found['mo']).items() if k}
    repo_web, _ = plexio.read_json(os.path.join(ROOT, 'Web Clients', 'zh.json'))
    repo_srv = {k: v for k, _c, _m, v in
                plexio.read_po(os.path.join(ROOT, 'Plex Media Server', 'plex.po')) if k}

    def diverged(up, cur):
        keys = set(up) & set(cur)
        return sum(1 for k in keys if up[k] != cur[k])

    return {
        'updated': __import__('datetime').date.today().isoformat(),
        'web': {'total': len(up_web), 'diverged': diverged(up_web, repo_web)},
        'srv': {'total': len(up_mo), 'diverged': diverged(up_mo, repo_srv)},
    }


def render(prog):
    w, s = prog['web'], prog['srv']
    t_total, t_div = w['total'] + s['total'], w['diverged'] + s['diverged']

    def pct(a, b):
        return '%.1f%%' % (100.0 * a / b) if b else '—'

    lines = [
        '| 语言文件 | 条目 | 已改写 | 沿用官方 | 完成度 |',
        '|---|---:|---:|---:|---:|',
        '| `Web Clients/zh.json` | %d | %d | %d | **%s** |' % (
            w['total'], w['diverged'], w['total'] - w['diverged'], pct(w['diverged'], w['total'])),
        '| `Plex Media Server/plex.po` | %d | %d | %d | **%s** |' % (
            s['total'], s['diverged'], s['total'] - s['diverged'], pct(s['diverged'], s['total'])),
        '| 合计 | %d | %d | %d | **%s** |' % (
            t_total, t_div, t_total - t_div, pct(t_div, t_total)),
        '',
        '> 统计口径：与新版本官方译文逐条比对，「已改写」= 与官方不同的条目。'
        '由 `tools/progress.py` 生成%s，请勿手改。' % (
            '（基于 %s）' % prog['upstream'] if prog.get('upstream') else ''),
    ]
    return '\n'.join(lines)


def write_readme(block):
    txt = open(README, encoding='utf-8').read()
    if BEGIN not in txt or END not in txt:
        raise SystemExit('README.md 里没有 %s / %s 标记' % (BEGIN, END))
    head, rest = txt.split(BEGIN, 1)
    _, tail = rest.split(END, 1)
    new = head + BEGIN + '\n' + block + '\n' + END + tail
    open(README, 'w', encoding='utf-8').write(new)


def main(argv=None):
    ap = argparse.ArgumentParser(description='生成 README 翻译进度表')
    ap.add_argument('--upstream', help='官方基线目录（给出则现场重算）')
    ap.add_argument('--write', action='store_true', help='写回 README')
    ap.add_argument('--check', action='store_true',
                    help='只校验 README 里的表格与 progress.json 是否一致（CI 用）')
    ap.add_argument('--json', action='store_true', help='输出原始数字')
    args = ap.parse_args(argv)

    if args.upstream:
        prog = recount(args.upstream)
        if args.write:
            json.dump(prog, open(PROG_PATH, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    else:
        prog = json.load(open(PROG_PATH, encoding='utf-8'))

    if args.json:
        print(json.dumps(prog, ensure_ascii=False, indent=1))
        return 0

    block = render(prog)
    if args.check:
        txt = open(README, encoding='utf-8').read()
        if BEGIN not in txt or END not in txt:
            print('README.md 缺少进度标记')
            return 1
        cur = txt.split(BEGIN, 1)[1].split(END, 1)[0].strip()
        if cur != block.strip():
            print('README 进度表与 tools/progress.json 不一致，跑 python tools/progress.py --write')
            return 1
        print('进度表一致')
        return 0
    if args.write:
        write_readme(block)
        print('已写回 README.md（更新日期 %s）' % prog.get('updated', '—'))
    else:
        print(block)
    return 0


if __name__ == '__main__':
    sys.exit(main())
