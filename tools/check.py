# -*- coding: utf-8 -*-
"""语言包结构校验：确保两个语言文件自身自洽、彼此不打架（仅用标准库）

检查项：
  PH    占位符（{name}、%s、%1$s）在原文与译文里必须一致
  EMPTY 译文为空
  TRIM  译文首尾有多余空白
  DUP   重复键
  MO    mo 与 po 的键集合、译文必须逐条一致（防止改了 po 忘了编译）
  PO    带 msgctxt 的条目也要对齐（mo 里键是 ctxt\\x04msgid）
  TERM  术语表禁用译法（复用 tools/gloss.py）
  XFILE 同一个英文键在 Web 端与服务端译法不一致（语境词需登记豁免）

用法（仓库根目录执行）：
    python tools/check.py           # 只看失败项与统计
    python tools/check.py -v        # 连警告明细一起列
    python tools/check.py --json    # 机器可读
    python tools/check.py --strict  # 警告也视为失败
退出码：0 = 通过；1 = 有失败项（可直接用于 CI）
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import plexio  # noqa: E402

WEB_PATH = os.path.join(ROOT, 'Web Clients', 'zh.json')
PO_PATH = os.path.join(ROOT, 'Plex Media Server', 'plex.po')
MO_PATH = os.path.join(ROOT, 'Plex Media Server', 'plex.mo')
CONS_PATH = os.path.join(HERE, 'consistency.json')

# {name} / %s / %1$s / %(name)s 都算占位符
PH = re.compile(r'\{[^{}]*\}|%(?:\d+\$)?[sdf@]|%\(\w+\)[sd]')

errors = []
warns = []
stats = {}


def err(code, msg):
    errors.append((code, msg))


def warn(code, msg):
    warns.append((code, msg))


def ph_count(s):
    out = {}
    for m in PH.findall(s):
        out[m] = out.get(m, 0) + 1
    return out


def check_ph(where, rows):
    """rows: [(key, value)]"""
    bad = 0
    for k, v in rows:
        a, b = ph_count(k), ph_count(v)
        if a != b:
            bad += 1
            missing = {x: a[x] - b.get(x, 0) for x in a if a[x] != b.get(x, 0)}
            extra = {x: b[x] - a.get(x, 0) for x in b if b[x] != a.get(x, 0)}
            err('PH', '%s 占位符不一致：%s\n      原文 %r\n      译文 %r' % (
                where, json.dumps([missing, extra], ensure_ascii=False), k[:80], v[:80]))
    stats['ph_' + where] = bad
    return bad


# ---------- Web 端 ----------
web, dups = plexio.read_json(WEB_PATH)
if not isinstance(web, dict) or not web:
    err('JSON', 'Web Clients/zh.json 不是非空对象')
    web = {}
if dups:
    err('DUP', 'zh.json 有重复键 %d 个：%s' % (len(dups), dups[:5]))

rows = [(k, v) for k, v in web.items() if isinstance(v, str)]
non_str = [k for k, v in web.items() if not isinstance(v, str)]
if non_str:
    err('TYPE', 'zh.json 有 %d 个非字符串值：%s' % (len(non_str), non_str[:3]))

empty = [k for k, v in rows if not v.strip()]
if empty:
    err('EMPTY', 'zh.json 有 %d 条空译文：%s' % (len(empty), empty[:3]))

trim = [k for k, v in rows if v != v.strip()]
if trim:
    err('TRIM', 'zh.json 有 %d 条首尾空白：%s' % (len(trim), trim[:3]))

check_ph('web', rows)
stats['web'] = len(rows)

# ---------- 服务端 po / mo ----------
po_rows = plexio.read_po(PO_PATH)
po = {}
po_dups = []
for key, _c, _m, msgstr in po_rows:
    if key in po:
        po_dups.append(key)
    po[key] = msgstr
if po_dups:
    err('DUP', 'plex.po 有重复键 %d 个：%s' % (len(po_dups), po_dups[:5]))

# 第一条空 msgid 是 po 头（元信息），不参与校验
po_body = [(k, v) for k, v in po.items() if k]
if '' not in po:
    err('PO', 'plex.po 缺少 po 头（msgid ""）')

po_empty = [k for k, v in po_body if not v.strip()]
if po_empty:
    err('EMPTY', 'plex.po 有 %d 条空译文：%s' % (len(po_empty), po_empty[:3]))

check_ph('srv', po_body)
stats['srv_po'] = len(po_body)

try:
    mo = plexio.read_mo(MO_PATH)
except Exception as exc:                      # noqa: BLE001
    err('MO', 'plex.mo 读取失败：%s' % exc)
    mo = {}

if mo:
    mo_body = {k: v for k, v in mo.items() if k}
    po_map = dict(po_body)
    only_po = sorted(set(po_map) - set(mo_body))
    only_mo = sorted(set(mo_body) - set(po_map))
    diff = sorted(k for k in set(po_map) & set(mo_body) if po_map[k] != mo_body[k])
    if only_po:
        err('MO', 'mo 缺少 %d 条（改了 po 没重新编译？）：%s' % (len(only_po), [k[:40] for k in only_po[:3]]))
    if only_mo:
        err('MO', 'mo 多出 %d 条：%s' % (len(only_mo), [k[:40] for k in only_mo[:3]]))
    if diff:
        err('MO', 'mo 与 po 有 %d 条译文不一致：%s' % (len(diff), [k[:40] for k in diff[:3]]))
    stats['srv_mo'] = len(mo_body)

# ---------- 术语表 ----------
try:
    import gloss
    hits = gloss.scan()
    stats['term_hits'] = len(hits)
    for h in hits[:20]:
        err('TERM', '[%s] %s 禁用「%s」应为「%s」\n      %s' % (
            h['src'], h['key'][:60], h['bad'], h['want'], h['val'][:70]))
    if len(hits) > 20:
        err('TERM', '另有 %d 条术语命中未列出，跑 python tools/gloss.py -v 查看' % (len(hits) - 20))
except Exception as exc:                      # noqa: BLE001
    warn('TERM', '术语巡检未能运行（%s）' % exc)

# ---------- 跨端一致 ----------
allow = {}
if os.path.isfile(CONS_PATH):
    allow = {d['key']: d.get('why', '') for d in
             json.load(open(CONS_PATH, encoding='utf-8')).get('cross_file', [])}
shared = [k for k in web if k in po]
xdiff = [(k, web[k], po[k]) for k in shared if web[k] != po[k]]
unknown = [x for x in xdiff if x[0] not in allow]
stats['shared'] = len(shared)
stats['xfile'] = len(xdiff)
for k, a, b in unknown[:10]:
    warn('XFILE', '同一英文键两侧译法不同：%r\n      Web %r\n      服务端 %r' % (k[:60], a[:40], b[:40]))
if len(unknown) > 10:
    warn('XFILE', '另有 %d 处跨端差异未列出；确实属语境差异的请登记到 tools/consistency.json' % (len(unknown) - 10))

# 未翻译（译文与原文相同）仅作统计，不算问题
stats['same'] = sum(1 for k, v in rows if k == v)

# ---------- 输出 ----------
if '--json' in sys.argv:
    print(json.dumps({'ok': not errors, 'errors': errors, 'warns': warns, 'stats': stats},
                     ensure_ascii=False, indent=1))
else:
    print('Web 端  %5d 条    服务端 %5d 条（mo %d 条）' % (
        stats.get('web', 0), stats.get('srv_po', 0), stats.get('srv_mo', 0)))
    print('占位符差异 %d + %d    空译文 %d    术语命中 %d    跨端差异 %d/%d 已登记' % (
        stats.get('ph_web', 0), stats.get('ph_srv', 0), len(empty) + len(po_empty),
        stats.get('term_hits', 0), stats.get('xfile', 0) - len(unknown), stats.get('xfile', 0)))
    for code, msg in errors:
        print('  ✗ [%s] %s' % (code, msg))
    if errors:
        print('\n失败 %d 项' % len(errors))
    if warns:
        print('警告 %d 项%s' % (len(warns), '' if ('-v' in sys.argv or '--strict' in sys.argv) else '（-v 查看）'))
        if '-v' in sys.argv or '--strict' in sys.argv:
            for code, msg in warns:
                print('  ! [%s] %s' % (code, msg))
    print('\nRESULT %s' % ('PASS' if not errors else 'FAIL'))
    if not errors and warns:
        print('提示：警告不影响通过，但新出现的跨端差异建议登记或统一')

if errors:
    sys.exit(1)
if '--strict' in sys.argv and warns:
    sys.exit(1)
sys.exit(0)
