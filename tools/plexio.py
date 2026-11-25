# -*- coding: utf-8 -*-
"""Plex 语言文件读写（随仓库分发，仅用标准库）

Web 端是 JSON（键 = 英文原文，值 = 译文）；服务端是 gettext 的 po/mo
（键 = msgid，带 msgctxt 时为 ctxt\\x04msgid，与 mo 内部的键一致）。
"""
import json
import struct

_ESC = {'n': '\n', 't': '\t', 'r': '\r', '"': '"', '\\': '\\'}


def _unescape(s):
    out, i = [], 0
    while i < len(s):
        if s[i] == '\\' and i + 1 < len(s):
            out.append(_ESC.get(s[i + 1], s[i + 1]))
            i += 2
        else:
            out.append(s[i])
            i += 1
    return ''.join(out)


def unquote(s):
    """把 po 里的一行（可能有多段引号）还原成字符串"""
    import re
    return _unescape(''.join(re.findall(r'"((?:[^"\\]|\\.)*)"', s)))


def read_json(path):
    """读 JSON；同时检出重复键（json 模块默认静默后者覆盖前者）"""
    dups = []

    def hook(pairs):
        seen = set()
        for k, _ in pairs:
            if k in seen:
                dups.append(k)
            seen.add(k)
        return dict(pairs)

    with open(path, encoding='utf-8') as fh:
        data = json.load(fh, object_pairs_hook=hook)
    return data, dups


def read_po(path):
    """返回 [(key, msgctxt, msgid, msgstr)]，保持文件顺序"""
    import re
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
                kw, val = m.group(1), unquote(m.group(2))
                if kw == 'msgctxt':
                    ctxt, cur = val, None
                elif kw == 'msgid':
                    msgid, cur = val, 'id'
                elif kw.startswith('msgstr'):
                    msgstr, cur = val, 'str'
                else:
                    cur = None
            elif line.startswith('"'):
                if cur == 'id':
                    msgid = (msgid or '') + unquote(line)
                elif cur == 'str':
                    msgstr = (msgstr or '') + unquote(line)
        if msgid is None:
            continue
        key = (ctxt + '\x04' + msgid) if ctxt else msgid
        rows.append((key, ctxt, msgid, msgstr or ''))
    return rows


def read_mo(path):
    """读 GNU MO（支持大小端），返回 {key: msgstr}"""
    b = open(path, 'rb').read()
    if len(b) < 20:
        raise ValueError('不是有效的 MO 文件（长度不足）')
    magic = struct.unpack('<I', b[:4])[0]
    if magic == 0x950412de:
        e = '<'
    elif magic == 0xde120495:
        e = '>'
    else:
        raise ValueError('MO 魔数不对：0x%08x' % magic)
    _, n, off_o, off_t = struct.unpack(e + 'IIII', b[4:20])
    out = {}
    for i in range(n):
        ln, op = struct.unpack(e + 'II', b[off_o + i * 8: off_o + i * 8 + 8])
        key = b[op:op + ln].decode('utf-8')
        ln2, op2 = struct.unpack(e + 'II', b[off_t + i * 8: off_t + i * 8 + 8])
        out[key] = b[op2:op2 + ln2].decode('utf-8')
    return out


def find_upstream(directory):
    """在给定目录里找官方基线的两个文件，容忍常见命名"""
    import os
    cands = {
        'web': ['zh_json', 'zh.json', 'Web Clients/zh.json'],
        'mo': ['plex_mo', 'plex.mo', 'Plex Media Server/plex.mo'],
    }
    found = {}
    for slot, names in cands.items():
        for name in names:
            p = os.path.join(directory, name)
            if os.path.isfile(p):
                found[slot] = p
                break
    return found
