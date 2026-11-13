#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修上游的进度回调竞态崩溃（必现 → 间歇必现）

真机日志（HOP-LX9 / EMUI16）：
    FATAL EXCEPTION: main
    java.lang.NullPointerException: Attempt to invoke virtual method
        'void android.view.View.setVisibility(int)' on a null object reference
        at org.citra.emu.ui.MainActivity$d.G(...)
    ... FrameLayout.onLayout ...

栈里报的是内部类，实际物理代码被 R8 内联进了 MainActivity.y0(String,long,long)：
这个方法是进度回调，一进来就
    iget-object p1, p0, MainActivity;->v:ProgressBar
    invoke-virtual {p1, 0}, View;->setVisibility(I)V

而 v / w 两个字段是在 onCreate 里 findViewById 才赋值的。库扫描任务在 onCreate
早期就启动了，进度回调先于 findViewById 触发 → p1 为 null → NPE。

3 次冷启动复现 2 次（am force-stop 后立刻 start 最容易命中）。华为的兼容性自动化
测试就是这种节奏，不修的话过审时会被判"应用闪退"。

修法：在 y0 入口加两个空判断，视图没准备好就直接返回 —— 只是不画进度，功能不受影响。
"""
import io
import sys

P = 'dec/smali/org/citra/emu/ui/MainActivity.smali'
MARK = '# AG-NPE-GUARD'
TARGET = '.method public y0(Ljava/lang/String;JJ)V'

GUARD = """{mark}: 视图未就绪时直接返回（上游进度回调竞态，见 patch_crash_guard.py）
    iget-object v0, p0, Lorg/citra/emu/ui/MainActivity;->v:Landroid/widget/ProgressBar;

    if-eqz v0, :ag_views_ok

    return-void

    :ag_views_ok
    iget-object v0, p0, Lorg/citra/emu/ui/MainActivity;->w:Landroid/widget/TextView;

    if-eqz v0, :ag_views_ok2

    return-void

    :ag_views_ok2
""".format(mark=MARK)


def main():
    src = io.open(P, encoding='utf-8').read()

    if MARK in src:
        print('  进度回调空判断: 已存在 OK')
        return 0

    i = src.index(TARGET)
    j = src.index('.locals 3', i) + len('.locals 3')
    src = src[:j] + '\n\n    ' + GUARD.rstrip() + src[j:]

    io.open(P, 'w', encoding='utf-8', newline='\n').write(src)

    chk = io.open(P, encoding='utf-8').read()
    ok = chk.count(MARK) == 1 and 'ag_views_ok2' in chk
    print('  进度回调空判断: 注入 %s' % ('OK' if ok else 'FAIL'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
