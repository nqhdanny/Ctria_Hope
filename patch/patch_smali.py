#!/usr/bin/env python3
# 在 EmulationActivity.surfaceChanged 末尾插入 HingeHelper.apply(activity, w, h) 调用
import sys, io

P = 'dec/smali/org/citra/emu/ui/EmulationActivity.smali'
MARK = '.method public surfaceChanged(Landroid/view/SurfaceHolder;III)V'
OLD = 'invoke-static {p3, p4}, Lorg/citra/emu/HingeHelper;->apply(II)V'
NEW = 'invoke-static {p0, p3, p4}, Lorg/citra/emu/HingeHelper;->apply(Landroid/app/Activity;II)V'

src = io.open(P, encoding='utf-8').read()

if OLD in src:
    src = src.replace(OLD, NEW)
    io.open(P, 'w', encoding='utf-8', newline='\n').write(src)
    print('REPATCHED -> Activity signature')
elif NEW in src:
    print('ALREADY_PATCHED')
else:
    i = src.index(MARK)
    j = src.index('.end method', i)
    block = src[i:j]
    k = block.rindex('return-void')
    patched = block[:k] + '\n    ' + NEW + '\n' + block[k:]
    src = src[:i] + patched + src[j:]
    io.open(P, 'w', encoding='utf-8', newline='\n').write(src)
    print('PATCHED first time')

# 回读校验
chk = io.open(P, encoding='utf-8').read()
i2 = chk.index(MARK)
j2 = chk.index('.end method', i2)
print('--- patched method ---')
print(chk[i2:j2])
