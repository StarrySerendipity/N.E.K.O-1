# -*- coding: utf-8 -*-
"""从 Unihan_IRGSources.txt 提取 kTotalStrokes 生成 stroke_data.py"""
import io, os, sys

sys.stdout.reconfigure(encoding='utf-8')
src = os.path.join(os.environ['TEMP'], 'unihan', 'Unihan_IRGSources.txt')
strokes = {}
with io.open(src, encoding='utf-8') as f:
    for line in f:
        if line.startswith('#') or 'kTotalStrokes' not in line:
            continue
        parts = line.rstrip('\n').split('\t')
        if len(parts) >= 3 and parts[1] == 'kTotalStrokes':
            cp = int(parts[0][2:], 16)
            if 0x4E00 <= cp <= 0x9FFF:  # 仅 CJK 基本区
                v = parts[2].strip().split()[0]  # 多值取首
                try:
                    strokes[chr(cp)] = int(v)
                except ValueError:
                    pass
print('字数:', len(strokes))
checks = {'星': 9, '雷': 13, '雪': 11, '语': 9, '缘': 12, '物': 8, '李': 7, '王': 4, '燕': 16, '涛': 10}
for ch, v in checks.items():
    print(ch, strokes.get(ch), 'OK' if strokes.get(ch) == v else 'MISMATCH(expected %d)' % v)
groups = {}
for ch, n in strokes.items():
    groups.setdefault(n, []).append(ch)
out = ['"""全量汉字笔画数据（Unicode Unihan kTotalStrokes，CJK 基本区 U+4E00-U+9FFF）。', '',
       '由 Unicode 官方 Unihan 数据库生成，作为姓名五格笔画兜底字库。', '"""', 'from __future__ import annotations', '']
for n in sorted(groups):
    out.append('_S%d = "%s"' % (n, ''.join(sorted(groups[n]))))
out.append('')
out.append('GROUPS: dict[int, str] = {')
for n in sorted(groups):
    out.append('    %d: _S%d,' % (n, n))
out.append('}')
out.append('')
out.append('STROKES: dict[str, int] = {ch: n for n, chars in GROUPS.items() for ch in chars}')
out.append('')
dst = r'd:\N.E.K.O\N.E.K.O自强之路\2026.05.01\plugin\plugins\tarot\stroke_data.py'
with io.open(dst, 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
print('已生成:', dst, os.path.getsize(dst), 'bytes')
