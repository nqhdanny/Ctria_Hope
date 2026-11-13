#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AppGallery 合规改造（幂等）

四件事，全部为了过华为审核：

1. AboutActivity.onCreate 末尾挂上 AgCompliance.apply(this)
   → 把"检查更新"那一行改成应用内隐私政策；许可改成应用内阅读。
2. AboutActivity$b 的 doInBackground 直接返回 null
   → 即使有别的路径触发，也不会再发 api.github.com 请求。
3. AndroidManifest：
     android:label="Citra"       → "Ctria Hope"
     删除 android:isGame="true"  → 华为据此判定"游戏"类目；游戏类在中国大陆要版号，
                                   海外区也走联运审核。本应用是模拟器工具，必须去掉。
     删除 android:appCategory="game"
4. strings.xml：
     app_name  Citra → Ctria Hope
     西班牙语帮助文本里的 "como Mario 3D Land" 换成中性表述（审核扫品牌词时的噪声）

幂等：所有替换先判存在，重复执行结果一致。
"""
import io
import re
import sys

ABOUT = 'dec/smali/org/citra/emu/ui/AboutActivity.smali'
ABOUT_B = 'dec/smali/org/citra/emu/ui/AboutActivity$b.smali'
MANIFEST = 'dec/AndroidManifest.xml'
STRINGS = 'dec/res/values/strings.xml'

CALL = 'invoke-static {p0}, Lorg/citra/emu/AgCompliance;->apply(Landroid/app/Activity;)V'
APP_NAME = 'Ctria Hope'


def patch_about_call():
    src = io.open(ABOUT, encoding='utf-8').read()
    src = '\n'.join(ln for ln in src.splitlines() if 'AgCompliance;->' not in ln) + '\n'

    i = src.index('.method protected onCreate(Landroid/os/Bundle;)V')
    j = src.index('.end method', i)
    block = src[i:j]
    k = block.rindex('return-void')
    block = block[:k] + CALL + '\n\n    ' + block[k:]
    src = src[:i] + block + src[j:]
    io.open(ABOUT, 'w', encoding='utf-8', newline='\n').write(src)

    chk = io.open(ABOUT, encoding='utf-8').read()
    i = chk.index('.method protected onCreate(Landroid/os/Bundle;)V')
    body = chk[i:chk.index('.end method', i)]
    n = body.count('AgCompliance;->')
    print('  AboutActivity.onCreate: AgCompliance 调用 %d 处 %s' % (n, 'OK' if n == 1 else 'FAIL'))
    return n == 1


def patch_checker():
    """把版本检查的 doInBackground 变成空实现。"""
    src = io.open(ABOUT_B, encoding='utf-8').read()
    head = '.method protected varargs a([Ljava/lang/Void;)Ljava/lang/String;'
    i = src.index(head)
    j = src.index('.end method', i) + len('.end method')
    body = src[i:j]
    if len(body.splitlines()) <= 5 and 'const/4 v0, 0x0' in body:
        print('  AboutActivity$b.a: 已是空实现 OK')
        return True
    new = (head + '\n'
           '    .locals 1\n\n'
           '    const/4 v0, 0x0\n\n'
           '    return-object v0\n'
           '.end method')
    src = src[:i] + new + src[j:]
    io.open(ABOUT_B, 'w', encoding='utf-8', newline='\n').write(src)
    chk = io.open(ABOUT_B, encoding='utf-8').read()
    i = chk.index(head)
    body = chk[i:chk.index('.end method', i)]
    ok = 'return-object v0' in body and 'api.github.com' not in body
    print('  AboutActivity$b.a: 网络请求已移除 %s' % ('OK' if ok else 'FAIL'))
    return ok


def patch_manifest():
    src = io.open(MANIFEST, encoding='utf-8').read()
    before = src

    src = src.replace('android:appCategory="game" ', '')
    src = src.replace(' android:isGame="true"', '')
    src = re.sub(r'android:label="Citra"', 'android:label="%s"' % APP_NAME, src)

    if src != before:
        io.open(MANIFEST, 'w', encoding='utf-8', newline='\n').write(src)

    chk = io.open(MANIFEST, encoding='utf-8').read()
    ok_label = 'android:label="%s"' % APP_NAME in chk
    ok_game = 'isGame' not in chk and 'appCategory' not in chk
    print('  manifest: label=%s %s / isGame 已移除 %s'
          % (APP_NAME, 'OK' if ok_label else 'FAIL', 'OK' if ok_game else 'FAIL'))
    return ok_label and ok_game


def patch_strings():
    src = io.open(STRINGS, encoding='utf-8').read()
    pat = re.compile(r'<string name="app_name">[^<]*</string>')
    if pat.search(src):
        src = pat.sub('<string name="app_name">%s</string>' % APP_NAME, src, count=1)

    n = src.count('como Mario 3D Land')
    src = src.replace('en algunos juegos como Mario 3D Land',
                      'en algunos titulos exigentes')
    src = src.replace('como Mario 3D Land', 'en algunos titulos exigentes')

    io.open(STRINGS, 'w', encoding='utf-8', newline='\n').write(src)
    chk = io.open(STRINGS, encoding='utf-8').read()
    ok_name = ('<string name="app_name">%s</string>' % APP_NAME) in chk
    ok_mario = 'Mario' not in chk
    print('  strings: app_name=%s %s / 品牌词清理 %s (改 %d 处)'
          % (APP_NAME, 'OK' if ok_name else 'FAIL', 'OK' if ok_mario else 'FAIL', n))
    return ok_name and ok_mario


def patch_colors():
    """自适应图标的底板颜色：上游是 Citra 橙，换成本项目的深靛蓝。"""
    p = 'dec/res/values/colors.xml'
    src = io.open(p, encoding='utf-8').read()
    pat = re.compile(r'<color name="ic_launcher_background">[^<]*</color>')
    if pat.search(src):
        src = pat.sub('<color name="ic_launcher_background">#ff0b1030</color>', src, count=1)
        io.open(p, 'w', encoding='utf-8', newline='\n').write(src)
    chk = io.open(p, encoding='utf-8').read()
    ok = '#ff0b1030' in chk
    print('  colors: ic_launcher_background = #ff0b1030 %s' % ('OK' if ok else 'FAIL'))
    return ok


def patch_auto_check():
    """
    onCreate 末尾有一段"进页面就自动查更新"的代码：
        new-instance p1, AboutActivity$b
        invoke-direct ... <init>
        new-array v0, ... [Ljava/lang/Void;
        invoke-virtual {p1, v0}, Landroid/os/AsyncTask;->execute(...)
    它会在 AgCompliance.apply() 之后把按钮文字改写成 "Latest Version(Network error)"，
    并把刚改好的 "Privacy policy" 覆盖掉。整段删掉 —— 一个不进网络、不改标签的页面
    才是过审需要的。
    """
    src = io.open(ABOUT, encoding='utf-8').read()
    start_mark = 'new-instance p1, Lorg/citra/emu/ui/AboutActivity$b;'
    end_mark = '->execute([Ljava/lang/Object;)Landroid/os/AsyncTask;'

    if start_mark not in src:
        done = '# AG-COMPLIANCE: 自动更新检查已移除' in src
        print('  自动更新检查: %s' % ('已移除 OK' if done else '未找到注入点，跳过'))
        return True

    i = src.index(start_mark)
    j = src.index(end_mark, i) + len(end_mark)
    src = src[:i] + '# AG-COMPLIANCE: 自动更新检查已移除（华为审核指南 3.9）\n    ' + src[j:]
    io.open(ABOUT, 'w', encoding='utf-8', newline='\n').write(src)

    chk = io.open(ABOUT, encoding='utf-8').read()
    ok = (start_mark not in chk) and ('AboutActivity$b;-><init>' not in chk)
    print('  自动更新检查: 已从 onCreate 移除 %s' % ('OK' if ok else 'FAIL'))
    return ok


def main():
    ok = patch_about_call()
    ok = patch_auto_check() and ok
    ok = patch_checker() and ok
    ok = patch_manifest() and ok
    ok = patch_strings() and ok
    ok = patch_colors() and ok
    print('PATCHED ag-compliance' if ok else 'FAILED ag-compliance')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
