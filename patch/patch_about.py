#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改造 About 页面，让它成为 GPL 合规的「源码入口」

原状（真机 + smali 确认）
--------------------------------------------------------------------------
AboutActivity 有三个按钮：
  Citra Official Website   -> https://citra-emu.org/          ← 2024-03 已关停，死链
  open_weibo               -> https://weibo.com/1725027100     ← MMJ 作者微博
  latest_version           -> github.com/weihuoya/citra/...    ← 上游仓库

改造后
--------------------------------------------------------------------------
  Source code (GPL-2.0)    -> 我们的仓库根
  Licenses                 -> 仓库里的许可文件
  Latest version           -> 我们的 releases

这样应用内任何一个用户都能两步拿到「完整对应源码」，满足 GPL-2.0 §3
对二进制分发的 source offer 要求；同时把死链和跟本项目无关的微博入口去掉，
审核时也不会因为死链被挑。

幂等：URL 直接做字符串替换，strings.xml 按 name 定位。
"""
import io
import os
import re
import sys

SMALI = 'dec/smali/org/citra/emu/ui/AboutActivity.smali'
STRINGS = 'dec/res/values/strings.xml'

SOURCE_URL = 'https://github.com/nqhdanny/Ctria_Hope'

# 本工程以前用过的仓库地址。仓库定名之后 SOURCE_URL 变了，
# 只匹配「上游原始 URL」的映射表会一次生效后永久失效——这里必须把历史地址也收编。
LEGACY_URLS = ['https://github.com/FunInHope/citra-hinge']

# 旧 URL -> 新 URL（按顺序匹配，具体 URL 必须排在通配之前）
URL_MAP = [
    # 上游的版本检查接口必须改到我们自己的仓库：否则 app 会把 MMJ 的新版本
    # 当成"有更新"推给用户，点下去下的是别人的 APK。
    ('https://api.github.com/repos/weihuoya/citra/releases/latest',
     'https://api.github.com/repos/nqhdanny/Ctria_Hope/releases/latest'),
    ('https://github.com/weihuoya/citra/releases/latest', SOURCE_URL + '/releases/latest'),
    ('https://weibo.com/1725027100', SOURCE_URL + '/tree/main/licenses'),
    ('https://citra-emu.org/', SOURCE_URL),
    # 历史仓库地址：先处理带路径的变体，再由下面的前缀替换收尾
    ('https://github.com/FunInHope/citra-hinge/blob/main/licenses/LICENSE.txt',
     SOURCE_URL + '/tree/main/licenses'),
    ('https://github.com/FunInHope/citra-hinge/releases/latest',
     SOURCE_URL + '/releases/latest'),
] + [(u, SOURCE_URL) for u in LEGACY_URLS]

# 按钮文案：资源名 -> 新文案
TEXT_MAP = [
    ('citra_official_website', 'Source code (GPL-2.0)'),
    ('open_weibo', 'Licenses'),
]


def patch_smali():
    # 版本检查的 URL 在内部类里（AboutActivity$b），不在 AboutActivity 本体，
    # 只改一个文件会漏掉"检查更新"用的接口。
    targets = [SMALI, SMALI.replace('.smali', '$b.smali')]
    ok = True
    for path in targets:
        if not os.path.isfile(path):
            print('ERR: %s not found' % path)
            ok = False
            continue
        s = io.open(path, encoding='utf-8').read()
        for old, new in URL_MAP:
            if old in s:
                s = s.replace(old, new)
                print('  URL  [%s] %s -> %s' % (os.path.basename(path), old, new))
            elif new in s:
                print('  URL  [%s] already -> %s' % (os.path.basename(path), new))
        io.open(path, 'w', encoding='utf-8', newline='\n').write(s)
    return ok


def patch_strings():
    if not os.path.isfile(STRINGS):
        print('ERR: %s not found' % STRINGS)
        return False
    s = io.open(STRINGS, encoding='utf-8').read()
    for name, text in TEXT_MAP:
        pat = re.compile(r'<string name="%s">.*?</string>' % re.escape(name), re.S)
        if not pat.search(s):
            print('  WARN: string "%s" not found' % name)
            continue
        s = pat.sub('<string name="%s">%s</string>' % (name, text), s, count=1)
        print('  TEXT %s = %s' % (name, text))
    io.open(STRINGS, 'w', encoding='utf-8', newline='\n').write(s)
    return True


def main():
    ok = patch_smali()
    ok = patch_strings() and ok
    print('PATCHED about' if ok else 'FAILED about')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
