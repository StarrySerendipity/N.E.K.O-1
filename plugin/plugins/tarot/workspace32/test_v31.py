# -*- coding: utf-8 -*-
"""V3.1 自测：78 张全卡组、图片落盘、抽牌渲染、姓名五格"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
REPO = r'd:\N.E.K.O\N.E.K.O自强之路\2026.05.01'
sys.path.insert(0, REPO)
sys.path.insert(0, REPO + r'\plugin\plugins')

import tarot as t

cards = t._TAROT_CARDS
print('卡组总数:', len(cards))
assert len(cards) == 78, '卡组应为 78 张'
ids = [c['id'] for c in cards]
assert len(set(ids)) == 78, 'id 重复'

import os
static_img = os.path.join(REPO, r'plugin\plugins\tarot\static\image')
missing = []
for c in cards:
    img = c.get('image')
    assert img, f"缺 image 字段: {c['name']}"
    if not os.path.isfile(os.path.join(static_img, img.replace('/', os.sep))):
        missing.append(img)
print('图片缺失:', missing if missing else '无（78/78 齐全）')
assert not missing

# 抽牌 + 构建结果
draw = t._draw_cards(3)
print('抽牌样例:', [(d['card']['name'], d['card']['image'], d['is_reversed']) for d in draw])
reading = t._build_reading('three_card', '测试问题')
assert len(reading['cards']) == 3
assert all('image' in c['card'] for c in reading['cards'])
print('three_card 构建 OK, 第一张:', reading['cards'][0]['card']['name'], reading['cards'][0]['orientation'])

# 小阿卡纳抽查
minor = [c for c in cards if c['arcana'] == 'minor']
print('小阿卡纳数:', len(minor), '| 示例:', minor[0]['name'], minor[0]['name_en'], minor[-1]['name'], minor[-1]['name_en'])

# 姓名五格
for n in ['星缘物语', '李白', '王小明', '司马相如', '欧阳娜娜']:
    r = t._build_name_reading(n)
    status = 'OK' if r else 'FAIL'
    print(f'姓名五格 [{n}]:', status)
    assert r, f'{n} 分析失败'
print('缺字提示测试:', end=' ')
r = t._build_name_reading('骉龘')  # 生僻叠字也可能在 Unihan 基本区之外
print('OK(有结果)' if r else 'None(走友好提示)')
print('\nALL TESTS PASSED')
