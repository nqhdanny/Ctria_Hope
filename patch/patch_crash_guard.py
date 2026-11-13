#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修上游进度回调的崩溃（MainActivity.y0）

    java.lang.NullPointerException: View.setVisibility(int) on a null object reference
      at MainActivity$d.G(...)
      at Choreographer...

y0(String,long,long) 是进度回调，一进来就 progressBar.setVisibility()，
而 v / w 两个字段在 onCreate 里才 findViewById。扫描任务早于视图赋值时回调先到 → NPE。

⚠ 分支语义（这里踩过坑）：
     if-eqz v0, :label   →  v0 == 0（null）时跳转
     if-nez v0, :label   →  v0 != 0（非空）时跳转
  想要"非空继续、为空返回"，必须用 if-nez 跳到继续标签：
     iget-object v0, ...->v:
     if-nez v0, :ok
     return-void
     :ok
  写成 if-eqz 会让"空"的情况继续执行、让"正常"的情况提前返回 —— 既崩又丢功能。
"""
import io
import re
import sys

P = 'dec/smali/org/citra/emu/ui/MainActivity.smali'
TARGET = '.method public y0(Ljava/lang/String;JJ)V'
MARK = '# AG-NPE-GUARD'

GUARD = '''{mark}: 视图未就绪就直接返回（上游进度回调竞态）
    iget-object v0, p0, Lorg/citra/emu/ui/MainActivity;->v:Landroid/widget/ProgressBar;

    if-nez v0, :ag_views_ok

    return-void

    :ag_views_ok
    iget-object v0, p0, Lorg/citra/emu/ui/MainActivity;->w:Landroid/widget/TextView;

    if-nez v0, :ag_views_ok2

    return-void

    :ag_views_ok2
'''.format(mark=MARK)


def strip_previous(src):
    """把上一次插入的守卫整块删掉（从注释到 :ag_views_ok2），可逆。"""
    lines = src.splitlines()
    out = []
    i = 0
    while i < len(lines):
        if MARK in lines[i]:
            # 注意：要停在该 *标签行* 上，不能停在任何含 ':ag_views_ok2' 的行——
            # 跳转指令 `if-nez v0, :ag_views_ok2` 也含这个名字，早停会留下半个块。
            while i < len(lines) and lines[i].strip() != ':ag_views_ok2':
                i += 1
            i += 1
            continue
        out.append(lines[i])
        i += 1
    return '\n'.join(out) + '\n'


def main():
    src = io.open(P, encoding='utf-8').read()
    src = strip_previous(src)

    i = src.index(TARGET)
    j = src.index('.end method', i)
    block = src[i:j]

    loc = block.index('.locals')
    loc_end = block.index('\n', loc)
    block = block[:loc_end + 1] + '\n    ' + GUARD.rstrip() + block[loc_end + 1:]

    src = src[:i] + block + src[j:]
    io.open(P, 'w', encoding='utf-8', newline='\n').write(src)

    chk = io.open(P, encoding='utf-8').read()
    ok = chk.count('if-nez v0, :ag_views_ok') == 2 and 'if-eqz v0, :ag_views_ok' not in chk
    print('  进度回调判空: %s' % ('OK' if ok else 'FAIL'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
