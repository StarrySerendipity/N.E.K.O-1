# -*- coding: utf-8 -*-
"""V3.2 自测：十二星座星图卡片接入"""
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
REPO = r'd:\N.E.K.O\N.E.K.O自强之路\2026.05.01'
sys.path.insert(0, REPO)
sys.path.insert(0, REPO + r'\plugin\plugins')

import tarot as t

STATIC_IMG = os.path.join(REPO, r'plugin\plugins\tarot\static\image')

# 1. 12 星座全部带 image 字段且图片文件真实存在
assert len(t._ZODIAC_SIGNS) == 12, '星座数量应为12'
for sign, info in t._ZODIAC_SIGNS.items():
    img = info.get('image')
    assert img and img.startswith('zodiac/'), f'{sign} 缺 image 字段'
    path = os.path.join(STATIC_IMG, img.replace('/', os.sep))
    assert os.path.isfile(path), f'{sign} 图片不存在: {path}'
    assert os.path.getsize(path) > 50000, f'{sign} 图片过小可疑: {path}'
print('12 星座 image 字段 + 星图文件齐全')

# 2. 运势报告嵌入星图 markdown，URL 与图片文件一致
for sign in t._ZODIAC_SIGNS:
    text = t._build_horoscope_reading(sign)
    url = f'/plugin/tarot/ui/image/{t._ZODIAC_SIGNS[sign]["image"]}'
    assert f'![{sign}星图]({url})' in text, f'{sign} 运势未嵌入星图'
    assert url.count('.png') == 1
print('12 星座运势报告全部嵌入星图链接')

# 3. 打印一份完整样例
print('\n===== 样例：天蝎座 =====')
print(t._build_horoscope_reading('天蝎座')[:600])
print('\nALL TESTS PASSED')
