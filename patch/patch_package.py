#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 applicationId 从 org.citra.emu 改成 com.ctriahope.emu。

只动 AndroidManifest 的 package 属性与两个 provider 的 authority，
**不动** smali 里的 Java 包名 —— 因为 libmain.so 用 org/citra/emu/... 这种路径
注册 JNI native 方法，改类包名会让整个应用在 NativeLibrary.<clinit> 崩掉。

authority 必须一起改：smali 里是 getPackageName() + ".filesprovider" 拼出来的
（dec/smali/org/citra/emu/ui/GameFilePickerActivity$a.smali），
清单不同步的话 FileProvider.getUriForFile() 会抛 IllegalArgumentException。
"""
import io
import os
import sys

OLD = 'org.citra.emu'
NEW = 'com.ctriahope.emu'
MANIFEST = 'dec/AndroidManifest.xml'

# 只替换这两处 + 根节点 package 属性；android:name="org.citra.emu.XxxActivity" 一律不动
AUTHORITIES = ('filesprovider', 'userpathprovider')


def main():
    if not os.path.isfile(MANIFEST):
        print('ERR: %s not found (run from the build root)' % MANIFEST)
        return 1

    s = io.open(MANIFEST, encoding='utf-8').read()
    before = s

    # 1) 根节点 package 属性。只匹配带引号的那一个，避免误伤类名。
    s = s.replace('package="%s"' % OLD, 'package="%s"' % NEW)

    # 2) provider authority
    for a in AUTHORITIES:
        s = s.replace('android:authorities="%s.%s"' % (OLD, a),
                      'android:authorities="%s.%s"' % (NEW, a))

    if s == before:
        # 幂等：已经改过就明确报告，而不是静默通过
        if 'package="%s"' % NEW in s:
            print('package: already %s' % NEW)
            return 0
        print('ERR: nothing replaced — manifest layout changed?')
        return 1

    io.open(MANIFEST, 'w', encoding='utf-8', newline='\n').write(s)

    # 自检：确认类名没被顺带改掉
    problems = []
    if s.count('package="%s"' % NEW) != 1:
        problems.append('package attribute count != 1')
    if 'android:name="org.citra.emu.ui.MainActivity"' not in s:
        problems.append('MainActivity class name damaged')
    for a in AUTHORITIES:
        if 'android:authorities="%s.%s"' % (NEW, a) not in s:
            problems.append('authority %s not rewritten' % a)
    if 'android:name="org.citra.emu.UserPathProvider"' not in s:
        problems.append('provider class name was rewritten (must stay)')

    if problems:
        print('ERR: ' + '; '.join(problems))
        return 1

    print('package: %s -> %s (authorities moved, class names untouched)' % (OLD, NEW))
    return 0


if __name__ == '__main__':
    sys.exit(main())
