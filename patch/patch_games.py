#!/usr/bin/env python3
# 注入内置游戏的释放 / 登记逻辑：
#   1) MainActivity.onCreate 的 **invoke-super 之前** → BundledGames.ensure(this)
#      必须早于任何 UI 扫描；放 super 之后 = 首次启动扫到空目录。
#   2) MainActivity.onResume 的 **invoke-super 之后** → BundledGames.onResumed(this)
#      native 配置要到 onResume 才加载完，写 game_storage_path 必须在这一步；
#      写完还要调 t0() 刷新列表，列表才会出现条目。
#
# 幂等：每次都先删掉旧注入，再按正确位置重插（dec/ 是复用的，不能只插一次）。
import io

P = 'dec/smali/org/citra/emu/ui/MainActivity.smali'

JOBS = [
    dict(
        mark='.method protected onCreate(Landroid/os/Bundle;)V',
        anchor='invoke-super {p0, p1}, Landroidx/fragment/app/e;->onCreate(Landroid/os/Bundle;)V',
        call='invoke-static {p0}, Lorg/citra/emu/BundledGames;->ensure(Landroid/content/Context;)V',
        before=True,
        label='onCreate/ensure',
    ),
    dict(
        mark='.method protected onResume()V',
        anchor='invoke-super {p0}, Landroidx/fragment/app/e;->onResume()V',
        call='invoke-static {p0}, Lorg/citra/emu/BundledGames;->onResumeBegin(Landroid/app/Activity;)V',
        before=True,
        label='onResume/onResumeBegin',
    ),
]

src = io.open(P, encoding='utf-8').read()

# 先清掉所有旧注入行
src = '\n'.join(ln for ln in src.splitlines()
                if 'Lorg/citra/emu/BundledGames;->' not in ln) + '\n'

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
print('PATCHED both')

# 校验
chk = io.open(P, encoding='utf-8').read()
for job in JOBS:
    i2 = chk.index(job['mark'])
    body = chk[i2:chk.index('.end method', i2)].splitlines()
    call_at = next(k for k, ln in enumerate(body) if 'BundledGames;->' in ln)
    anchor_at = next(k for k, ln in enumerate(body) if 'invoke-super' in ln)
    ok = call_at < anchor_at if job['before'] else call_at > anchor_at
    print('%-22s 注入行 %2d / super 行 %2d  %s' % (job['label'], call_at, anchor_at,
                                                 'OK' if ok else 'FAIL'))
