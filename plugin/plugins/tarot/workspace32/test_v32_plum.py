# -*- coding: utf-8 -*-
"""V3.2 自测：梅花易数卦象卡片（六爻图）"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
REPO = r'd:\N.E.K.O\N.E.K.O自强之路\2026.05.01'
sys.path.insert(0, REPO)
sys.path.insert(0, REPO + r'\plugin\plugins')

import tarot as t
import tarot.yijing_data as yj

# 1. 验证变卦/互卦上下卦与卦名一致
for n1, n2 in [(3, 7), (8, 8), (1, 1), (123, 456), (5, 2), (9, 14)]:
    r = yj.divine(n1, n2)
    assert yj.HEXAGRAMS[(r.changed_upper, r.changed_lower)][0] == r.changed_name, f'变卦上下卦不符 {n1},{n2}'
    assert yj.HEXAGRAMS[(r.mutual_upper, r.mutual_lower)][0] == r.mutual_name, f'互卦上下卦不符 {n1},{n2}'
    text = t._build_plum_reading(n1, n2)
    assert '动爻' in text and '━' in text, f'卦象图缺失 {n1},{n2}'
    lines_art = [l for l in text.split('\n') if '━' in l]
    assert len(lines_art) == 18, f'应有3组×6爻=18行爻线，实得{len(lines_art)} ({n1},{n2})'
print('卦象一致性 + 爻线图 6 组用例全部通过')

# 2. 打印一份完整样例
print('\n===== 样例：3 与 7 =====')
print(t._build_plum_reading(3, 7))
print('\nALL TESTS PASSED')
