#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修「游戏列表回调早于 Fragment 视图创建」导致的闪退（两处 NPE）

真机全栈（HOP-LX9 / EMUI16）：

    # 冷启动
    java.lang.NullPointerException: View.setVisibility(int) on a null object reference
      at c3.f0.f2(...)                     ← 切空状态视图，字段是 null
      at org.citra.emu.ui.MainActivity$d.G(...)
      at androidx.viewpager2.adapter.FragmentStateAdapter.I/N/t

    # 再启动
    java.lang.NullPointerException: 'void c3.f0$b.H(java.util.List)' on a null object reference
      at c3.f0.f2(...)                     ← adapter 还没建出来就往里塞数据
      at org.citra.emu.ui.MainActivity$d.G(...)

成因：MainActivity$d 是 ViewPager2 的 FragmentStateAdapter，它为每一页缓存了一个
「待投递列表」；createFragment() 拿到 Fragment 后**立刻**把列表喂给 f2()。而 f2()
还要切「空状态提示 / 重试按钮 / RecyclerView」的可见性。这时 Fragment 的
onViewCreated 还没跑，adapter 与那几个视图全是 null → NPE。

为什么时快时慢：首次安装要解 10 MB 主题、扫目录，回调来得晚，躲过了；
二次启动一切就绪、回调瞬间到达，正好撞在 onCreateView 之前。

修法（两层，都不丢数据）：
  1. 入口判 adapter(d0)：为 null 直接返回 —— 此刻无能为力，后续扫描会重新投递；
  2. 逐处判视图：每处 setVisibility 前单独判空 —— 视图没建好就跳过，数据照常提交。

幂等策略：**只执行一次**。本文件一旦出现标记就直接返回成功，不再尝试"回退重插"。
需要重新生成时，从干净的反编译树恢复 c3/f0.smali 再跑：
    cp /tmp/chk/smali/c3/f0.smali dec/smali/c3/f0.smali
（早期版本做过"先删后插"的自动回退，结果把 6 处守卫删掉却留下了孤立标签，
  导致 dexlib2 报标签未落点。不做回退反而更稳。）
"""
import io
import re
import sys

P = 'dec/smali/c3/f0.smali'
TARGET = '.method public f2(Ljava/util/List;)V'
MARK = 'AG-NPE-F2'

IGET = re.compile(r'^\s*iget-object v0, p0, Lc3/f0;->(\w+):L[^;]+;$')
SETVIS = re.compile(r'^\s*invoke-virtual \{v0, v\d+\}, Landroid/view/View;->setVisibility\(I\)V$')
NOISE = re.compile(r'^\s*(\.line \d+|\.local|\.end local|#.*)?$')

ENTRY = '''    # AG-NPE-F2 入口守卫：adapter 未就绪时直接返回，避免 NullPointerException
    iget-object v0, p0, Lc3/f0;->d0:Lc3/f0$b;

    if-nez v0, :ag_f2_entry

    return-void

    :ag_f2_entry
'''


def verify(src):
    entry = src.count(':ag_f2_entry') - 1
    guards = src.count('if-eqz v0, :ag_f2_ok')
    labels = src.count(':ag_f2_ok') - guards
    ok = (entry == 1 and guards == labels and guards >= 5
          and 'if-nez v0, :ag_f2_entry' in src)
    print('  列表回调判空: 入口 %d / 逐处 %d（标签落点 %d）%s'
          % (entry, guards, labels, 'OK' if ok else 'FAIL'))
    return ok


def main():
    src = io.open(P, encoding='utf-8').read()
    if MARK in src:
        print('  列表回调判空: 已注入，跳过')
        return 0 if verify(src) else 1

    before = src.count('setVisibility(I)V')

    i = src.index(TARGET)
    j = src.index('.end method', i)
    block = src[i:j]

    loc = block.index('.locals')
    loc_end = block.index('\n', loc)
    block = block[:loc_end + 1] + '\n' + ENTRY + block[loc_end + 1:]

    lines = block.splitlines()
    out = []
    n = 0
    idx = 0
    while idx < len(lines):
        ln = lines[idx]
        m = IGET.match(ln)
        if m:
            k = idx + 1
            while k < len(lines) and NOISE.match(lines[k]):
                k += 1
            if k < len(lines) and SETVIS.match(lines[k]):
                n += 1
                out.append('    # AG-NPE-F2: 视图未建好就不碰（%s）' % m.group(1))
                out.append(ln)
                out.append('')
                out.append('    if-eqz v0, :ag_f2_ok%d   # null 就跳过这次 setVisibility' % n)
                while idx < k:
                    idx += 1
                    out.append(lines[idx])
                out.append('')
                out.append('    :ag_f2_ok%d' % n)
                idx += 1
                continue
        out.append(ln)
        idx += 1

    src = src[:i] + '\n'.join(out) + src[j:]
    io.open(P, 'w', encoding='utf-8', newline='\n').write(src)

    chk = io.open(P, encoding='utf-8').read()
    if chk.count('setVisibility(I)V') != before:
        print('  FAIL: setVisibility 数量变了，拒绝写入')
        return 1
    return 0 if verify(chk) else 1


if __name__ == '__main__':
    sys.exit(main())
