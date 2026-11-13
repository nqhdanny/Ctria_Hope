#!/usr/bin/env python3
# 注入存储权限引导：
#   onCreate  的 invoke-super 之前 → StorageGate.ensure(this)
#              必须排在 BundledGames.ensure() 之前：没授权时释放逻辑会静默失败，
#              先弹窗让用户去授权，授权回来 recreate 后才真正写出文件。
#   onResume  的 invoke-super 之前 → StorageGate.onResume(this)
#              从系统设置页返回后检查一次，已授权就 recreate() 重跑 onCreate。
#
# 依赖 patch_games.py 已经跑过（以 BundledGames 那两行为锚点）。
# 幂等：先删旧注入再重插。
import io

P = 'dec/smali/org/citra/emu/ui/MainActivity.smali'
CLS = 'Lorg/citra/emu/StorageGate;'

JOBS = [
    dict(
        mark='.method protected onCreate(Landroid/os/Bundle;)V',
        anchor='invoke-static {p0}, Lorg/citra/emu/BundledGames;->ensure(Landroid/content/Context;)V',
        call='invoke-static {p0}, %s->ensure(Landroid/app/Activity;)V' % CLS,
        label='onCreate/ensure',
    ),
    dict(
        mark='.method protected onResume()V',
        anchor='invoke-static {p0}, Lorg/citra/emu/BundledGames;->onResumeBegin(Landroid/app/Activity;)V',
        call='invoke-static {p0}, %s->onResume(Landroid/app/Activity;)V' % CLS,
        label='onResume/onResume',
    ),
]

src = io.open(P, encoding='utf-8').read()

# 清掉旧注入
src = '\n'.join(ln for ln in src.splitlines()
                if 'StorageGate;->' not in ln) + '\n'

for job in JOBS:
    i = src.index(job['mark'])
    j = src.index('.end method', i)
    block = src[i:j]
    assert job['anchor'] in block, '%s 里没找到 BundledGames 锚点' % job['label']
    if job['label'].startswith('onCreate'):
        # 插在 BundledGames 之前
        block = block.replace(job['anchor'], job['call'] + '\n\n    ' + job['anchor'], 1)
    else:
        # 插在 BundledGames 之后（仍早于 invoke-super）
        block = block.replace(job['anchor'], job['anchor'] + '\n\n    ' + job['call'], 1)
    src = src[:i] + block + src[j:]

io.open(P, 'w', encoding='utf-8', newline='\n').write(src)
print('PATCHED storage gate')

# 校验顺序：ensure 必须在 BundledGames.ensure 之前
chk = io.open(P, encoding='utf-8').read()
i = chk.index(JOBS[0]['mark'])
body = chk[i:chk.index('.end method', i)].splitlines()
sg = next(k for k, ln in enumerate(body) if 'StorageGate;->' in ln)
bg = next(k for k, ln in enumerate(body) if 'BundledGames;->' in ln)
print('onCreate: StorageGate 行 %d / BundledGames 行 %d  %s'
      % (sg, bg, 'OK' if sg < bg else 'FAIL'))
