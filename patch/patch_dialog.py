#!/usr/bin/env python3
# 让设置界面的弹窗跟随「深色底」：
#   往 dec/res/values/styles.xml 追加 CitraDialogDark + OverlayDialogDark 两个 style，
#   并把配套的 citra_dialog_bg.xml 拷进 dec/res/drawable/。
#   运行时由 SettingsSkin.preApply() 在深色壁纸下 applyStyle(OverlayDialogDark)。
#
# 幂等：以 CitraDialogDark 是否已存在为准，已存在就整段替换。
import io
import os
import shutil

STYLES = 'dec/res/values/styles.xml'
DRAWABLE_DIR = 'dec/res/drawable'
SRC_BG = 'patch/res/citra_dialog_bg.xml'
BG_NAME = 'citra_dialog_bg.xml'

BLOCK = '''
    <!-- ==== SettingsSkin: 深色壁纸下的弹窗主题（由补丁注入，非原始资源） ==== -->
    <style name="CitraDialogDark" parent="@style/Theme.AppCompat.Dialog.Alert">
        <item name="android:windowBackground">@drawable/citra_dialog_bg</item>
        <item name="android:textColorPrimary">#FFF3F6FA</item>
        <item name="android:textColor">#FFF3F6FA</item>
        <item name="android:textColorSecondary">#FFA6B0C0</item>
        <item name="android:textColorHint">#66FFFFFF</item>
        <item name="android:colorAccent">#FFFFFFFF</item>
        <item name="colorAccent">#FFFFFFFF</item>
        <item name="colorPrimary">#FF2A2F3A</item>
        <item name="colorSurface">#FF1C2028</item>
        <item name="android:colorBackground">#FF1C2028</item>
    </style>
    <style name="OverlayDialogDark" parent="@android:style/Theme">
        <item name="alertDialogTheme">@style/CitraDialogDark</item>
        <item name="android:alertDialogTheme">@style/CitraDialogDark</item>
        <item name="android:datePickerDialogTheme">@style/CitraDialogDark</item>
        <item name="android:timePickerDialogTheme">@style/CitraDialogDark</item>
    </style>
    <!-- ==== /SettingsSkin ==== -->
'''

src = io.open(STYLES, encoding='utf-8').read()
mark = '<!-- ==== SettingsSkin'
endmark = '<!-- ==== /SettingsSkin ==== -->'
if mark in src:
    a = src.index(mark)
    b = src.index(endmark) + len(endmark)
    src = src[:a] + src[b:]
src = src.replace('</resources>', BLOCK + '</resources>')
io.open(STYLES, 'w', encoding='utf-8', newline='\n').write(src)

os.makedirs(DRAWABLE_DIR, exist_ok=True)
shutil.copyfile(SRC_BG, os.path.join(DRAWABLE_DIR, BG_NAME))

print('PATCHED dialog theme ->', STYLES, '+', os.path.join(DRAWABLE_DIR, BG_NAME))
