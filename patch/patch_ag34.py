#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AG 上架适配：把用户目录恒定钉在 /sdcard/citra-emu

背景（真机实测 + smali 证据）
--------------------------------------------------------------------------
d3/a.U(Context) 决定 CITRA 的用户目录，逻辑是：

    if (SDK_INT >= 29 && !Environment.isExternalStorageLegacy()) {
        a.b = 2;
        root = context.getExternalFilesDir(null);      // Android/data/.../files
    } else if (d3.m.h(ctx) && "mounted".equals(Environment.getExternalStorageState())) {
        a.b = 1;
        root = Environment.getExternalStorageDirectory();   // /storage/emulated/0
    } else { a.b = -1; root = null; }

关键点一：isExternalStorageLegacy() 对 targetSdk >= 30 是编译期常量、恒为 false。
          所以升 targetSdk 之后必然走第一支，目录整体挪到 Android/data/...，
          用户原来在 /sdcard/citra-emu/ 的存档、主题、ROM 全部"消失"。
          （这正是「升 34 后主题变黑底灰键」的真正原因，不是权限问题，改 appops 无效。）

关键点二：d3.m.h() 只查 WRITE_EXTERNAL_STORAGE。这个权限在 targetSdk >= 30
          上永远返回 denied，所以就算绕过第一支进到第二支，也只会拿到 null。

改动
--------------------------------------------------------------------------
1) U() 开头：跳过全部 SDK / 权限判定，直接 root = getExternalStorageDirectory()
2) mkdir 失败时：回退到 getExternalFilesDir()，避免 a.c 为 null 导致
   SetUserPath(null) 在 native 层空指针

寄存器占用（.locals 6）
--------------------------------------------------------------------------
v0=File  v1=File  v2=String("citra-emu")  v3=临时 int  v4=-1  v5=null
补丁 2 落在「v2 已变成 String」之后，所以整型状态标记必须用 v3，不能用 v2 —
第一版就是踩了这个坑，真机报 VerifyError: unexpected value in v2 ... expected Integer。

幂等：先从已有补丁块精确还原，再重新注入，可反复运行。
"""
import io
import os
import re
import sys

SMALI = sys.argv[1] if len(sys.argv) > 1 else 'dec/smali/d3/a.smali'
MINI = '# ==== AG34-PATCH ===='

# ---------------------------------------------------------------- 补丁 1
ANCHOR_1 = '''    const/4 v1, 0x1

    .line 4
    if-eq v0, v1, :cond_5
'''

PATCH_1 = ANCHOR_1 + '''    ''' + MINI + ''' root 恒定 /sdcard
    # 原本这里开始判 SDK_INT 和 isExternalStorageLegacy()，targetSdk>=30 时
    # 后者恒 false，会把用户目录切到 Android/data/...，导致老存档与主题失效。
    # 直接钉死公共存储根，路径与旧版完全一致，零迁移。
    const/4 v4, -0x1
    const/4 v5, 0x0
    const/4 v1, 0x1
    sput v1, Ld3/a;->b:I
    invoke-static {}, Landroid/os/Environment;->getExternalStorageDirectory()Ljava/io/File;
    move-result-object v0
    goto :goto_1
    ''' + MINI + ''' end
'''

# ---------------------------------------------------------------- 补丁 2
ANCHOR_2 = '''    if-nez v0, :cond_4

    .line 83
    .line 84
    sput v4, Ld3/a;->b:I

    .line 85
    .line 86
    return-void
'''

PATCH_2 = '''    if-nez v0, :cond_4

    ''' + MINI + ''' fallback 私有目录
    # 公共目录建不出来（用户没给「所有文件访问权限」）时退到应用私有目录，
    # 保证 a.c 非空 —— 否则后面的 SetUserPath(null) 会在 native 里空指针。
    # 注意：此处 v2 已被 cond_4 上方的 const-string 占成 String，状态位只能用 v3。
    const/4 v3, 0x2
    sput v3, Ld3/a;->b:I
    invoke-virtual {p0, v5}, Landroid/content/Context;->getExternalFilesDir(Ljava/lang/String;)Ljava/io/File;
    move-result-object v0
    if-eqz v0, :cond_ag34_fb
    sput v4, Ld3/a;->b:I
    return-void

    :cond_ag34_fb
    new-instance v1, Ljava/io/File;
    const-string v2, "citra-emu"
    invoke-direct {v1, v0, v2}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V
    invoke-virtual {v1}, Ljava/io/File;->mkdirs()Z
    goto :cond_4
    ''' + MINI + ''' end
    .line 83
    .line 84
    sput v4, Ld3/a;->b:I

    .line 85
    .line 86
    return-void
'''

BLOCK_RE = re.compile(r'[ \t]*# ==== AG34-PATCH[^\n]*\n.*?[ \t]*# ==== AG34-PATCH[^\n]*end[^\n]*\n', re.S)


def strip(src):
    """把之前注入的块整段删掉，回到原始 smali"""
    return BLOCK_RE.sub('', src)


def main():
    if not os.path.isfile(SMALI):
        print('ERR: %s not found' % SMALI)
        return 1
    raw = io.open(SMALI, encoding='utf-8').read()
    src = strip(raw)

    for name, anchor, patch in (('U() root', ANCHOR_1, PATCH_1),
                                ('U() fallback', ANCHOR_2, PATCH_2)):
        n = src.count(anchor)
        if n != 1:
            print('ERR: anchor "%s" matched %d times (need 1)' % (name, n))
            return 1
        src = src.replace(anchor, patch, 1)

    io.open(SMALI, 'w', encoding='utf-8', newline='\n').write(src)
    print('PATCHED ag34: %s (%d blocks)' % (SMALI, src.count(MINI) // 2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
