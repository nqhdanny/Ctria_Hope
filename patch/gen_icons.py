#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 Ctria Hope 自有图标 → patch/icons/

为什么必须换：上游图标是 Citra 的品牌资产，GPL 给的是代码许可，不含商标；
带着别人的图标上架，审核侧就是"仿冒/未授权使用品牌"的现成理由。

图形：一块深靛蓝底板上，按真机比例叠放 3DS 的两块屏（上 5:3、下 4:3），
中间一条青色转轴光带 —— 也就是这个项目做的事：把双屏塞进折叠屏。

输出：
  icons/mipmap-<density>/ic_citra.png              传统图标（含底板）
  icons/mipmap-<density>/ic_launcher_foreground.png 自适应图标前景（透明，内容在安全区）
  icons/ctria-hope-512.png                          商店用 512×512

只用 Pillow；不依赖 numpy。
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

# 调色板与 skins_design.py 的 aqua-blue 一套同源
BG_TOP = (11, 16, 48)
BG_BOT = (42, 58, 130)
SCREEN_TOP = (234, 244, 255)
SCREEN_BOT = (247, 251, 255)
ACCENT = (79, 209, 232)
ACCENT_DIM = (34, 120, 150)

MASTER = 1024


def vgrad(w, h, top, bot):
    img = Image.new('RGB', (1, h))
    px = img.load()
    for y in range(h):
        t = y / max(1, h - 1)
        px[0, y] = (int(top[0] + (bot[0] - top[0]) * t),
                    int(top[1] + (bot[1] - top[1]) * t),
                    int(top[2] + (bot[2] - top[2]) * t))
    return img.resize((w, h), Image.BILINEAR)


def glow(size, color, radius, alpha):
    layer = Image.new('RGBA', size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.ellipse([size[0] / 2 - radius, size[1] / 2 - radius,
               size[0] / 2 + radius, size[1] / 2 + radius],
              fill=color + (alpha,))
    return layer.filter(ImageFilter.GaussianBlur(radius / 2.2))


def draw_screens(img, scale=1.0, cx=None, cy=None):
    """在 img 上画两块屏 + 转轴。scale=1 时占画布约 66%。"""
    w, h = img.size
    cx = w / 2 if cx is None else cx
    cy = h / 2 if cy is None else cy
    d = ImageDraw.Draw(img, 'RGBA')

    top_w = 560 * scale
    top_h = top_w * 3 / 5          # 5:3
    gap = 46 * scale
    bot_w = 420 * scale
    bot_h = bot_w * 3 / 4          # 4:3

    total = top_h + gap + bot_h
    y0 = cy - total / 2
    r1 = max(6, int(20 * scale))
    r2 = max(6, int(16 * scale))

    # 屏体：外发光先铺一层
    pad = 14 * scale
    for box, rad in (
            ([cx - top_w / 2 - pad, y0 - pad, cx + top_w / 2 + pad, y0 + top_h + pad], r1),
            ([cx - bot_w / 2 - pad, y0 + top_h + gap - pad, cx + bot_w / 2 + pad,
              y0 + top_h + gap + bot_h + pad], r2)):
        d.rounded_rectangle(box, radius=int(rad + pad), fill=ACCENT_DIM + (46,))

    # 上屏（渐变：左上偏亮）
    top_img = vgrad(int(top_w), int(top_h), (255, 255, 255), SCREEN_TOP)
    mask = Image.new('L', top_img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, top_img.size[0] - 1, top_img.size[1] - 1],
                                           radius=r1, fill=255)
    img.paste(top_img, (int(cx - top_w / 2), int(y0)), mask)

    # 上屏中央一枚播放三角：让"这是一块在放东西的屏"一眼可读
    tri = 44 * scale
    tcx, tcy = cx, y0 + top_h / 2
    d.polygon([(tcx - tri * 0.42, tcy - tri * 0.55),
               (tcx - tri * 0.42, tcy + tri * 0.55),
               (tcx + tri * 0.6, tcy)],
              fill=ACCENT + (225,))

    # 下屏
    bot_img = vgrad(int(bot_w), int(bot_h), SCREEN_BOT, (222, 236, 250))
    mask2 = Image.new('L', bot_img.size, 0)
    ImageDraw.Draw(mask2).rounded_rectangle([0, 0, bot_img.size[0] - 1, bot_img.size[1] - 1],
                                            radius=r2, fill=255)
    img.paste(bot_img, (int(cx - bot_w / 2), int(y0 + top_h + gap)), mask2)

    # 转轴光带
    hy0 = y0 + top_h + gap * 0.28
    hy1 = y0 + top_h + gap * 0.72
    d.rounded_rectangle([cx - top_w / 2 - 6, hy0, cx + top_w / 2 + 6, hy1],
                        radius=int((hy1 - hy0) / 2), fill=ACCENT + (235,))
    # 轴心三个小孔，一眼看出是折叠结构
    for k in (-1, 0, 1):
        r = 7 * scale
        x = cx + k * 150 * scale
        d.ellipse([x - r, (hy0 + hy1) / 2 - r, x + r, (hy0 + hy1) / 2 + r],
                  fill=BG_TOP + (200,))
    return img


def full_icon(size=MASTER):
    img = vgrad(size, size, BG_TOP, BG_BOT).convert('RGBA')
    img.alpha_composite(glow((size, size), ACCENT, size * 0.34, 26))
    # 左上高光
    hi = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(hi).ellipse([-size * 0.35, -size * 0.45, size * 0.85, size * 0.55],
                               fill=(120, 170, 255, 34))
    img.alpha_composite(hi.filter(ImageFilter.GaussianBlur(size * 0.12)))
    draw_screens(img, scale=size / MASTER * 0.98)
    return img


def foreground(size=MASTER):
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    # 自适应图标安全区：内容收在中间约 58%
    draw_screens(img, scale=size / MASTER * 0.86)
    return img


DENSITIES = [('mdpi', 48, 108), ('hdpi', 72, 162), ('xhdpi', 96, 216),
             ('xxhdpi', 144, 324), ('xxxhdpi', 192, 432)]


def main():
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icons')
    full = full_icon()
    fg = foreground()

    for name, legacy, adapt in DENSITIES:
        d = os.path.join(out, 'mipmap-' + name)
        if not os.path.isdir(d):
            os.makedirs(d)
        full.resize((legacy, legacy), Image.LANCZOS).save(
            os.path.join(d, 'ic_citra.png'), 'PNG', optimize=True)
        fg.resize((adapt, adapt), Image.LANCZOS).save(
            os.path.join(d, 'ic_launcher_foreground.png'), 'PNG', optimize=True)
        print('  %-10s ic_citra %3d  foreground %3d' % (name, legacy, adapt))

    full.resize((512, 512), Image.LANCZOS).save(
        os.path.join(out, 'ctria-hope-512.png'), 'PNG', optimize=True)
    print('  store icon: icons/ctria-hope-512.png')
    print('GEN icons -> %s' % out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
