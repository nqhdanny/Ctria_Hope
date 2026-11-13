#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成应用内隐私政策 → dec/assets/privacy/PRIVACY.txt

为什么要应用内一份：华为审核要求隐私政策"可访问"，且要求政策里的每一条都与
实际权限、实际行为对得上。把文本随包分发、从「关于」页直接打开，既不依赖网络，
审核员也不可能点不到。

内容必须与仓库里的 PRIVACY.md / PRIVACY.zh-CN.md 保持一致 —— 审核员会逐条比对。
三语（英 / 俄 / 中）按目标市场排列：俄罗斯是第一投放市场。
"""
import io
import os
import sys

OUT_DIR = 'dec/assets/privacy'
OUT = os.path.join(OUT_DIR, 'PRIVACY.txt')
URL = 'https://github.com/nqhdanny/Ctria_Hope/blob/main/PRIVACY.md'

TEXT = u'''CTRIA HOPE - PRIVACY POLICY
Last updated: 13 November 2026
Applies to: Ctria Hope (org.citra.emu) 1.4.0 and later
Full text: %(url)s
================================================================================

SUMMARY

Ctria Hope collects nothing. There is no account, no sign-in, no analytics, no
advertising, no crash reporting and no tracking of any kind. The app makes no
automatic network requests at all. Everything you load into the emulator stays
on your device.

  Personal data collected ............ none
  Analytics or advertising SDKs ...... none
  Data shared with third parties ..... none
  Works fully offline ................ yes
  Email or phone number required ..... no


WHAT IS STORED ON YOUR DEVICE

All of it lives in the citra-emu/ folder on your storage, and only there:
  Games/     the game files you add
  config/    emulator settings (resolution, shaders, controls, theme)
  saves/     save files and save states
  states/    save states
  sdmc/      emulated SD card contents
  theme/     panel skins

None of these are uploaded anywhere. Uninstalling leaves the folder in place so
that you do not lose saves; delete it manually if you want it gone.


PERMISSIONS AND WHY EACH ONE IS NEEDED

  All files access (MANAGE_EXTERNAL_STORAGE)
      Android 11+ hides shared storage from apps without it. The emulator must
      read the games you put in citra-emu/Games and write saves next to them.
      Without this permission the game list is empty. Access is limited to the
      files the emulator reads and writes; nothing is scanned, indexed or sent.

  Storage read/write (Android 10 and older)
      Same purpose on older systems.

  Camera
      Used only by the emulated 3DS camera. Frames are handed to the emulated
      game in memory. The app never takes, stores or uploads photos.

  Microphone
      Used only by the emulated 3DS microphone. Audio is handed to the emulated
      game in memory and is never recorded or transmitted.

  Vibrate
      Haptic feedback.

  Internet / network state
      Only for multiplayer games that you configure and start yourself. There is
      no update check, no telemetry, no ping.

  Install shortcut
      Lets you put a shortcut to an individual game on your home screen.


NETWORK ACTIVITY

None happens on its own. If, and only if, you configure a room server and join a
room, the game data needed to play is exchanged with the peers and the server you
chose. We operate no servers and receive nothing. There is no background sync.


THIRD-PARTY COMPONENTS

The app is built on Citra MMJ / Citra, both GPL-2.0 software with no analytics or
advertising. Two MIT-licensed homebrew games are bundled; they are offline
single-player games with no network code. License texts are included in the app.


CHILDREN

Ctria Hope is a general-purpose emulator and is not directed at children. It
collects no personal data from anyone.


YOUR RIGHTS

Because no personal data is collected, there is nothing held on our side to
access, export or erase. Your games, saves and settings are yours, on your device.
Deleting the citra-emu/ folder erases everything the app ever wrote.


CHANGES

If a future version ever starts collecting anything, this document will be
updated before that version ships and the change will be called out in the
release notes.


CONTACT

%(url)s


================================================================================
RU - ПОЛИТИКА КОНФИДЕНЦИАЛЬНОСТИ
Обновлено: 13 ноября 2026 г.
Полный текст: %(url)s
================================================================================

Ctria Hope не собирает никаких данных. Нет учётной записи, нет входа, нет
аналитики, нет рекламы, нет отчётов о сбоях и нет отслеживания. Приложение не
выполняет автоматических сетевых запросов. Всё, что вы загружаете в эмулятор,
остаётся на вашем устройстве.

ХРАНИТСЯ НА УСТРОЙСТВЕ
Всё находится в папке citra-emu/ и никуда не отправляется:
  Games/     добавленные вами файлы игр
  config/    настройки эмулятора
  saves/     сохранения
  states/    снимки состояния
  theme/     темы оформления
При удалении приложения папка сохраняется, чтобы вы не потеряли сохранения.

РАЗРЕШЕНИЯ И ИХ НАЗНАЧЕНИЕ
  Доступ ко всем файлам - Android 11+ скрывает общую память. Без него эмулятор
      не увидит игры в citra-emu/Games и не запишет сохранения.
  Камера - только для эмулируемой камеры 3DS, кадры передаются игре в памяти.
  Микрофон - только для эмулируемого микрофона, звук не записывается и не
      передаётся.
  Вибрация - тактильная отдача.
  Интернет - только для сетевой игры, которую вы настраиваете сами. Проверки
      обновлений нет.
  Ярлык на рабочем столе - ярлык отдельной игры.

ДЕТИ
Приложение не адресовано детям и не собирает персональные данные ни у кого.

КОНТАКТЫ
%(url)s


================================================================================
ZH - 隐私政策
最后更新：2026 年 11 月 13 日
完整版本：%(url)s
================================================================================

Ctria Hope 不收集任何数据：没有账号、没有登录、没有统计、没有广告、没有崩溃
上报、没有任何追踪。应用不会进行任何自动网络请求。你导入模拟器的一切内容都只
留在你自己的设备上。

设备上存了什么
全部位于 citra-emu/ 目录，不会上传：Games/（游戏文件）、config/（模拟器设置）、
saves/（存档）、states/（即时存档）、theme/（面板主题）。卸载应用不会删除该目录，
如需彻底清除请手动删除。

权限与用途
  所有文件访问 - Android 11+ 默认隐藏共享存储，没有该权限读不到游戏、写不了存档。
  相机 - 仅用于模拟 3DS 摄像头，画面在内存中交给游戏，不拍照、不存储、不上传。
  麦克风 - 仅用于模拟 3DS 麦克风，不录音、不上传。
  振动 - 触感反馈。
  网络 - 仅用于你自己配置并发起的联机对战；没有更新检查。
  创建桌面快捷方式 - 把单个游戏放到桌面。

儿童
通用模拟器，不面向儿童；不收集任何人的个人数据。

联系方式
%(url)s
''' % {'url': URL}


def main():
    if not os.path.isdir('dec'):
        print('ERR: dec/ not found, run from the build root')
        return 1
    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)
    io.open(OUT, 'w', encoding='utf-8', newline='\n').write(TEXT)
    print('  %s  %d B' % (OUT, os.path.getsize(OUT)))
    print('PATCHED privacy -> %s' % OUT)
    return 0


if __name__ == '__main__':
    sys.exit(main())
