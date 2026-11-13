#!/usr/bin/env python3
# 注入「设置界面跟随壁纸配色」：
#   1) SettingsActivity.onCreate 里 **invoke-super 之后** → SettingsSkin.preApply(this)
#      窗口底色要早于 setContentView，否则会先闪一帧白底。
#   2) setContentView 之后 → SettingsSkin.attach(this)
#      attach 内部会 post 到下一帧，等 toolbar / fragment 都就绪再上色。
#
# 幂等：每次先删旧注入再插。
import io

P = 'dec/smali/org/citra/emu/settings/SettingsActivity.smali'

JOBS = [
    dict(
        mark='.method protected onCreate(Landroid/os/Bundle;)V',
        anchor='invoke-super {p0, p1}, Landroidx/fragment/app/e;->onCreate(Landroid/os/Bundle;)V',
        call='invoke-static {p0}, Lorg/citra/emu/SettingsSkin;->preApply(Landroid/app/Activity;)V',
        before=False,
        label='onCreate/preApply',
    ),
    dict(
        mark='.method protected onCreate(Landroid/os/Bundle;)V',
        anchor='invoke-virtual {p0, v0}, Landroidx/appcompat/app/c;->setContentView(I)V',
        call='invoke-static {p0}, Lorg/citra/emu/SettingsSkin;->attach(Landroid/app/Activity;)V',
        before=False,
        label='onCreate/attach',
    ),
]

src = io.open(P, encoding='utf-8').read()

src = '\n'.join(ln for ln in src.splitlines()
                if 'Lorg/citra/emu/SettingsSkin;->' not in ln) + '\n'

for job in JOBS:
    i = src.index(job['mark'])
    j = src.index('.end method', i)
    block = src[i:j]
    assert job['anchor'] in block, '%s 里没找到 %s' % (job['label'], job['anchor'])
    if job['before']:
        block = block.replace(job['anchor'], job['call'] + '\n\n    ' + job['anchor'], 1)
    else:
        block = block.replace(job['anchor'], job['anchor'] + '\n\n    ' + job['call'], 1)
    src = src[:i] + block + src[j:]

io.open(P, 'w', encoding='utf-8', newline='\n').write(src)
print('PATCHED SettingsActivity')
