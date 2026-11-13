#!/usr/bin/env python3
# 把 AndroidManifest 里所有 <activity> 锁定为竖屏（用户要求：不支持横屏）
import re
import io

P = 'dec/AndroidManifest.xml'
src = io.open(P, encoding='utf-8').read()


def fix(m):
    tag = m.group(0)
    if 'android:screenOrientation' in tag:
        return re.sub(r'android:screenOrientation="[^"]*"',
                      'android:screenOrientation="portrait"', tag)
    return tag.replace('<activity', '<activity android:screenOrientation="portrait"', 1)


out = re.sub(r'<activity(?![-\w])[^>]*>', fix, src, flags=re.S)
io.open(P, 'w', encoding='utf-8', newline='\n').write(out)

total = len(re.findall(r'android:screenOrientation="portrait"', out))
print('portrait activities:', total)
for m in re.finditer(r'<activity(?![-\w])[^>]*>', out, flags=re.S):
    tag = m.group(0)
    name = re.search(r'android:name="([^"]*)"', tag)
    if name and ('Emulation' in name.group(1) or 'MainActivity' in name.group(1)):
        print('  ', name.group(1), '->',
              'portrait' if 'android:screenOrientation="portrait"' in tag else 'MISSED')
