#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成随包许可文件 → dec/assets/licenses/

GPL-2.0 §1 要求：分发二进制时**必须随副本附带许可全文**和版权声明。
之前 1.0.x / 1.1.x 的 APK 里只有内置游戏的 MIT 文本，没有 GPL 全文，
这一条是硬性不合规 —— 审核员和任何用户都能据此投诉。

这里生成四份：
  LICENSE.txt       总说明（上游、源码地址、无 ROM 声明）
  GPL-2.0.txt       GPL 全文
  MIT-TRexGame.txt  内置游戏许可
  MIT-2048.txt      内置游戏许可

SOURCE_URL 是唯一需要按实际仓库改的常量。
"""
import io
import os
import shutil
import sys

OUT = 'dec/assets/licenses'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ←←← 仓库地址：定了之后改这一行，重跑 build.sh 即可
SOURCE_URL = 'https://github.com/nqhdanny/Ctria_Hope'

LICENSE_TXT = '''Citra Hinge — License Information
=================================

This application is a fork of Citra MMJ, itself a fork of Citra.
It is distributed under the GNU General Public License, version 2 or later.


Upstream projects
-----------------
Citra (Nintendo 3DS emulator)
    Copyright (C) 2013-2024 Citra Emulator Project
    License: GNU GPL v2.0 or later
    https://github.com/citra-emu/citra

Citra MMJ (Android fork by weihuoya)
    License: GNU GPL v2.0 or later
    https://github.com/weihuoya/citra


Source code
-----------
The complete corresponding source code of this build is available here:

    %s

That repository contains every modification made for this app: the smali
patch scripts, the Java patches, the build pipeline, the theme renderer,
and instructions for rebuilding this exact APK from the upstream package.
You may redistribute and modify it under the same license.


GNU General Public License v2
-----------------------------
The full text is included in this folder as GPL-2.0.txt.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
General Public License for more details.


Bundled homebrew games
----------------------
2048 for 3DS        MIT    https://github.com/0rientd/2048-port-3ds
T-Rex Game 3DS      MIT    https://github.com/BlyZeDev/T-Rex-Game-3DS

Both are original works released under the MIT license; the full texts
are included in this folder. They are bundled so that a fresh install
has something to run immediately.


Panel themes
------------
All eight panel skins (cosmo, aqua, flare red, ice white, coral pink,
metallic blue, snes, galaxy) were created specifically for this project
by rendering them from source. They are released under GPL-2.0, same as
the rest of this work, and the renderer is part of the source repository.


No game ROMs
------------
This application does not include, download, or link to any commercial
Nintendo 3DS game or any Nintendo system file. Users must supply their
own legally obtained games and system files.
''' % SOURCE_URL


def main():
    if not os.path.isdir('dec'):
        print('ERR: dec/ not found, run from the build root')
        return 1
    os.makedirs(OUT, exist_ok=True)

    io.open(os.path.join(OUT, 'LICENSE.txt'), 'w',
            encoding='utf-8', newline='\n').write(LICENSE_TXT)

    # GPL 全文：优先用发布包里那份，其次从工程根找
    gpl = None
    for cand in (os.path.join(ROOT, 'release/citra-hinge-1.0.0/licenses/GPL-2.0.txt'),
                 os.path.join(ROOT, 'licenses/GPL-2.0.txt'),
                 'GPL-2.0.txt'):
        if os.path.isfile(cand):
            gpl = cand
            break
    if gpl:
        shutil.copyfile(gpl, os.path.join(OUT, 'GPL-2.0.txt'))
        print('  GPL-2.0.txt <- %s' % gpl)
    else:
        print('  WARN: GPL-2.0.txt not found, license file will miss the full text')

    # 内置游戏的 MIT 文本，改名成可读的名字
    mapping = [('free-games/licenses/TRexGame-LICENSE.txt', 'MIT-TRexGame.txt'),
               ('free-games/licenses/2048-LICENSE.txt', 'MIT-2048.txt')]
    for src, dst in mapping:
        if os.path.isfile(src):
            shutil.copyfile(src, os.path.join(OUT, dst))
            print('  %s <- %s' % (dst, src))
        else:
            print('  WARN: %s missing' % src)

    for f in sorted(os.listdir(OUT)):
        p = os.path.join(OUT, f)
        print('  assets/licenses/%-20s %6d B' % (f, os.path.getsize(p)))
    print('PATCHED licenses -> %s' % OUT)
    return 0


if __name__ == '__main__':
    sys.exit(main())
