# -*- coding: utf-8 -*-
"""术语表巡检工具（随仓库分发，无第三方依赖）

按 tools/glossary.json 检查：
  1. 禁用译法（ban）——已做「标准译法同时出现则豁免」与 exceptions 白名单
  2. 格式规范——半角引号、半角省略号 ...、中文语境的半角标点、「你」

用法（在仓库根目录执行）：
    python tools/gloss.py            # 汇总
    python tools/gloss.py -v         # 逐条明细
    python tools/gloss.py --json     # 机器可读
退出码：0 = 无命中；1 = 有命中（可直接用于提交前检查/CI）
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GLOSS_PATH = os.path.join(ROOT, 'tools', 'glossary.json')
CJK = r'\u4e00-\u9fff'
_ESC = {'n': '\n', 't': '\t', '"': '"', '\\': '\\'}


def _unescape(s):
    out = []
    i = 0
    while i < len(s):
        if s[i] == '\\' and i + 1 < len(s):
            out.append(_ESC.get(s[i + 1], s[i + 1]))
            i += 2
        else:
            out.append(s[i])
            i += 1
    return ''.join(out)


def _unquote(s):
    return _unescape(''.join(re.findall(r'"((?:[^"\\]|\\.)*)"', s)))


def parse_po(path):
    """返回 [(key, msgstr)]，key 为 ctxt\x04msgid 或 msgid"""
    raw = open(path, encoding='utf-8').read()
    rows = []
    for blk in re.split(r'\n[ \t]*\n', raw):
        blk = blk.strip('\n')
        if not blk.strip() or blk.lstrip().startswith('#'):
            continue
        ctxt = msgid = msgstr = None
        cur = None
        for line in blk.split('\n'):
            line = line.rstrip()
            m = re.match(r'^(msgctxt|msgid_plural|msgid|msgstr(?:\[\d+\])?)\s+(.*)$', line)
            if m:
                kw, val = m.group(1), _unquote(m.group(2))
                if kw == 'msgctxt':
                    ctxt = val
                    cur = None
                elif kw == 'msgid':
                    msgid = val
                    cur = 'id'
                elif kw.startswith('msgstr'):
                    msgstr = val
                    cur = 'str'
                else:
                    cur = None
            elif line.startswith('"'):
                if cur == 'id':
                    msgid = (msgid or '') + _unquote(line)
                elif cur == 'str':
                    msgstr = (msgstr or '') + _unquote(line)
        if not msgid:
            continue
        rows.append(((ctxt + '\x04' + msgid) if ctxt else msgid, msgstr or ''))
    return rows


def load_pairs():
    web = json.load(open(os.path.join(ROOT, 'Web Clients', 'zh.json'), encoding='utf-8'))
    srv = dict(parse_po(os.path.join(ROOT, 'Plex Media Server', 'plex.po')))
    return web, srv


def scan(gloss=None):
    gloss = gloss or json.load(open(GLOSS_PATH, encoding='utf-8'))
    web, srv = load_pairs()
    hits = []
    for t in gloss['terms']:
        for bad in t.get('ban') or []:
            for fname, d in (('web', web), ('srv', srv)):
                for k, v in d.items():
                    # 标准译法已在文中时不再报（如「数字录像机」含「录像机」）
                    if bad in v and t['zh'] not in v:
                        hits.append({'src': fname, 'key': k, 'term': t['en'],
                                     'want': t['zh'], 'bad': bad, 'val': v})
    exc = gloss.get('exceptions') or []

    def _exc(h):
        for e in exc:
            if e['src'] in ('any', h['src']) and e['key_contains'].lower() in h['key'].lower():
                return True
        return False

    hits = [h for h in hits if not _exc(h)]

    for fname, d in (('web', web), ('srv', srv)):
        for k, v in d.items():
            if re.search(r'[' + CJK + r'][\"\u0027]|[\"\u0027][' + CJK + r']', v):
                hits.append({'src': fname, 'key': k, 'term': 'QUOTE', 'want': '“”',
                             'bad': '半角引号', 'val': v})
            if '...' in v:
                hits.append({'src': fname, 'key': k, 'term': 'ELLIPSIS', 'want': '…',
                             'bad': '...', 'val': v})
            if re.search(r'[\u4e00-\u9fff]\s*,\s*|[\u4e00-\u9fff]\s*;\s*', v):
                hits.append({'src': fname, 'key': k, 'term': 'PUNCT', 'want': '中文标点',
                             'bad': '半角标点', 'val': v})
            if '你' in v.replace('你们', ''):
                hits.append({'src': fname, 'key': k, 'term': 'YOU', 'want': '您',
                             'bad': '你', 'val': v})
    return hits


def main(argv):
    hits = scan()
    if '--json' in argv:
        print(json.dumps(hits, ensure_ascii=False, indent=1))
        return 0 if not hits else 1
    groups = {}
    for h in hits:
        groups.setdefault((h['term'], h['bad']), []).append(h)
    for (term, bad), items in sorted(groups.items(), key=lambda x: -len(x[1])):
        print('%-22s 禁用「%s」 → 应为「%s」  命中 %d 条' % (
            term, bad, items[0]['want'], len(items)))
        if '-v' in argv:
            for h in items:
                print('    [%s] %s\n         %s' % (h['src'], h['key'][:80], h['val'][:90]))
    print('\n合计命中 %d 条' % len(hits))
    return 0 if not hits else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
