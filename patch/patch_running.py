#!/usr/bin/env python3
# 游戏内「菜单 → Settings」的运行设置框（c3/s0 = DialogFragment，onCreateDialog = k2）
# 在 return 之前注入 SettingsSkin.applyDialog(dialog)，把白底黄头换成深色板。
#
# 幂等：先删旧注入再插。
import io

P = 'dec/smali/c3/s0.smali'
MARK = '.method public k2(Landroid/os/Bundle;)Landroid/app/Dialog;'
CALL = 'invoke-static {p1}, Lorg/citra/emu/SettingsSkin;->applyDialog(Landroid/app/Dialog;)V'
RET = 'return-object p1'

src = io.open(P, encoding='utf-8').read()
src = '\n'.join(ln for ln in src.splitlines() if 'SettingsSkin;->applyDialog' not in ln) + '\n'

i = src.index(MARK)
j = src.index('.end method', i)
block = src[i:j]
assert RET in block, 'k2 里没找到 return-object p1'
k = block.index(RET)
block = block[:k] + '    ' + CALL + '\n\n    ' + block[k:]
src = src[:i] + block + src[j:]

io.open(P, 'w', encoding='utf-8', newline='\n').write(src)

chk = io.open(P, encoding='utf-8').read()
i2 = chk.index(MARK)
body = chk[i2:chk.index('.end method', i2)].splitlines()
call_at = next(n for n, ln in enumerate(body) if 'applyDialog' in ln)
ret_at = next(n for n, ln in enumerate(body) if RET in ln)
print('PATCHED running dialog: 注入行 %d / return 行 %d  %s'
      % (call_at, ret_at, 'OK' if call_at < ret_at else 'FAIL'))
