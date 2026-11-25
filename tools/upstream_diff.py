# -*- coding: utf-8 -*-
"""上游增量比对：Plex 发布新版后，算出「这一版要处理哪些字符串」（仅用标准库）

官方语言文件来自新版 deb，解包后通常在这两个位置：
    Resources/Plug-ins-*/WebClient.bundle/Contents/Resources/translations/zh.json
    Resources/locale/zh_CN/LC_MESSAGES/plex.mo
把它们拷到一个目录（默认文件名 zh_json / plex_mo 也认 zh.json / plex.mo），然后：

    python tools/upstream_diff.py --upstream /path/to/upstream
    python tools/upstream_diff.py --upstream /path/to/upstream --tm 5      # 每条给 5 个相似译法
    python tools/upstream_diff.py --upstream /path/to/upstream --write      # 同时更新 tools/progress.json

输出的三类：
    新增  上游有、仓库没有 → 必须翻译（附翻译记忆候选：库内相似原文的现成译法）
    消失  仓库有、上游已删 → 可以从语言文件里移除
    沿用  两侧都有、仓库值与上游新值不同 → 要么我们改过（正常），要么官方改了（要复核）
          只有后一类需要人看，工具会把「疑似官方改译」的挑出来：译文与上游旧值无法比对时，
          用「译文里不含本版新增词」这类信号并不可靠，所以这里只做计数，不臆断。
"""
import argparse
import difflib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import plexio  # noqa: E402

WEB_PATH = os.path.join(ROOT, 'Web Clients', 'zh.json')
PO_PATH = os.path.join(ROOT, 'Plex Media Server', 'plex.po')
PROG_PATH = os.path.join(HERE, 'progress.json')


def load_repo():
    web, _ = plexio.read_json(WEB_PATH)
    srv = {k: v for k, _c, _m, v in plexio.read_po(PO_PATH) if k}
    return web, srv


def tm_candidates(key, pool, n=3):
    """翻译记忆：库内与这条原文最像的几条，供人工改写参考"""
    if not n:
        return []
    out = []
    for cand in difflib.get_close_matches(key, list(pool), n=n, cutoff=0.72):
        out.append((cand, pool[cand]))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description='对比官方新版语言文件与仓库当前译文')
    ap.add_argument('--upstream', required=True, help='含 zh_json 与 plex_mo（或 zh.json 与 plex.mo）的目录')
    ap.add_argument('--tm', type=int, default=0, help='为新增条目列出几条相似译法（默认 0）')
    ap.add_argument('--write', action='store_true', help='把统计写入 tools/progress.json')
    ap.add_argument('--json', action='store_true', help='机器可读输出')
    args = ap.parse_args(argv)

    found = plexio.find_upstream(args.upstream)
    if 'web' not in found or 'mo' not in found:
        print('在 %s 里没找到官方基线：需要 zh_json 与 plex_mo（或 zh.json 与 plex.mo）' % args.upstream)
        print('已找到：%s' % (found or '无'))
        return 2

    up_web, _ = plexio.read_json(found['web'])
    up_mo = {k: v for k, v in plexio.read_mo(found['mo']).items() if k}
    repo_web, repo_srv = load_repo()

    report = {'upstream': found, 'web': {}, 'srv': {}}
    for name, up, cur in (('web', up_web, repo_web), ('srv', up_mo, repo_srv)):
        added = sorted(set(up) - set(cur))
        gone = sorted(set(cur) - set(up))
        same_en = [k for k in set(up) & set(cur) if up[k] == cur[k]]          # 我们没动过
        changed = [k for k in set(up) & set(cur) if up[k] != cur[k]]           # 我们改过（或官方改过）
        report[name] = {'added': added, 'gone': gone,
                        'followed': len(same_en), 'diverged': len(changed)}

        print('\n===== %s =====' % ('Web Clients' if name == 'web' else 'Plex Media Server'))
        print('上游 %d 条 / 仓库 %d 条' % (len(up), len(cur)))
        print('  新增 %d 条（要翻译）' % len(added))
        print('  消失 %d 条（可移除）' % len(gone))
        print('  沿官方 %d 条 / 已改写 %d 条（%.1f%%）' % (
            len(same_en), len(changed), 100.0 * len(changed) / max(len(up), 1)))

        for k in added:
            print('\n  [新增] %s' % (k[:120].replace('\x04', ' › ')))
            print('         官方译法：%s' % (up[k][:100] or '（空）'))
            for cand, val in tm_candidates(k, cur, args.tm):
                print('         可参考：%s\n                 → %s' % (cand[:70], val[:70]))

        for k in gone:
            print('\n  [消失] %s' % k[:120].replace('\x04', ' › '))

    if args.write:
        prog = {'upstream': os.path.basename(args.upstream.rstrip('/\\')),
                'web': {'total': len(up_web), 'diverged': report['web']['diverged']},
                'srv': {'total': len(up_mo), 'diverged': report['srv']['diverged']}}
        json.dump(prog, open(PROG_PATH, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('\n已更新 tools/progress.json（接着跑 python tools/progress.py --write 刷新 README）')

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
