#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AG 上架适配：targetSdk 提到 34 + 声明 MANAGE_EXTERNAL_STORAGE

为什么要 MANAGE_EXTERNAL_STORAGE
--------------------------------------------------------------------------
Citra 需要 /sdcard/citra-emu/ 下的自由读写（ROM、存档、主题、屏幕布局）。
targetSdk >= 30 之后：
  - WRITE_EXTERNAL_STORAGE 形同虚设（永远 denied）
  - 分区存储把裸路径访问全部拦掉
所以只能走 MANAGE_EXTERNAL_STORAGE（"所有文件访问权限"），这也是模拟器类
应用的通行做法（RetroArch 等同样如此）。

注意：这个权限是特殊权限，不能靠运行时弹窗申请，必须跳系统设置页由用户手动开。
AppGallery 审核会要求说明用途，描述里必须写清楚"仅用于读取用户自备的游戏
ROM 与存档"。
"""
import io
import os
import re
import sys

YML = 'dec/apktool.yml'
MANIFEST = 'dec/AndroidManifest.xml'

MARK = 'AG34'


def patch_yml():
    if not os.path.isfile(YML):
        print('ERR: %s not found' % YML)
        return False
    s = io.open(YML, encoding='utf-8').read()
    m = re.search(r'^\s*targetSdkVersion:\s*(\d+)', s, re.M)
    if not m:
        print('ERR: targetSdkVersion not found in %s' % YML)
        return False
    cur = int(m.group(1))
    if cur == 34:
        print('  targetSdkVersion: already 34')
        return True
    s = re.sub(r'^(\s*targetSdkVersion:\s*)\d+', r'\g<1>34', s, count=1, flags=re.M)
    io.open(YML, 'w', encoding='utf-8', newline='\n').write(s)
    print('  targetSdkVersion: %d -> 34' % cur)
    return True


def patch_manifest():
    if not os.path.isfile(MANIFEST):
        print('ERR: %s not found' % MANIFEST)
        return False
    s = io.open(MANIFEST, encoding='utf-8').read()
    if 'MANAGE_EXTERNAL_STORAGE' in s:
        print('  MANAGE_EXTERNAL_STORAGE: already declared')
        return True
    # 挂在 READ_EXTERNAL_STORAGE 后面，保持权限区块连续
    m = re.search(r'^([ \t]*)<uses-permission[^>]*READ_EXTERNAL_STORAGE[^>]*/>[ \t]*$',
                  s, re.M)
    if not m:
        print('ERR: READ_EXTERNAL_STORAGE anchor not found')
        return False
    indent = m.group(1)
    add = '\n%s<uses-permission android:name="android.permission.MANAGE_EXTERNAL_STORAGE"/>' % indent
    s = s[:m.end()] + add + s[m.end():]
    io.open(MANIFEST, 'w', encoding='utf-8', newline='\n').write(s)
    print('  MANAGE_EXTERNAL_STORAGE: added')
    return True


def main():
    ok = patch_yml()
    ok = patch_manifest() and ok
    print('PATCHED %s env' % MARK if ok else 'FAILED %s env' % MARK)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
