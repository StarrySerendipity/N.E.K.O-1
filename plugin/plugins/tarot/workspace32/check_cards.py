# -*- coding: utf-8 -*-
import re, sys
sys.stdout.reconfigure(encoding='utf-8')
txt = open(r'd:\N.E.K.O\N.E.K.O自强之路\2026.05.01\plugin\plugins\tarot\__init__.py', encoding='utf-8').read()
for m in re.finditer(r'"id": (\d+), "name": "([^"]+)", "name_en": "([^"]+)"', txt):
    print(m.group(1), m.group(2), m.group(3))
data = open(r'd:\N.E.K.O\N.E.K.O自强之路\2026.05.01\plugin\plugins\tarot\static\image\rws\m00.jpg', 'rb').read(3)
print('JPEG magic:', data == b'\xff\xd8\xff')
