#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 Ctria Hope 自有图标 → patch/icons/

为什么必须自绘：上游图标是 Citra 的品牌资产，GPL 只给代码许可，不含商标；
带别人的图标上架，审核侧就是"仿冒 / 未授权使用品牌"的现成理由。

图形（1.4.4 起）：等轴测视角的「打开的双屏设备」——上盖绕铰链张开 106°、
整体左旋 45°，纯线条描绘（暖白底 + 深红线 + 一枚实心播放三角）。
刻意不做十字键 / 摇杆 / 肩键 / 品牌配色：外观上不指向任何在售机型。

输出：
  icons/mipmap-<density>/ic_citra.png               传统图标（含底板）
  icons/mipmap-<density>/ic_launcher_foreground.png 自适应图标前景（透明）
  icons/ctria-hope-512.png                          商店用 512×512

只用 Pillow；不依赖 numpy。
"""
import math
import os
import sys

from PIL import Image, ImageDraw

MASTER = 1024
SS = 4                       # 超采样，保证线条平滑

# 暖白底板 / 深红线（与商店图标同一套色）
BG_TOP = (255, 249, 246)
BG_BOT = (251, 233, 227)
LINE = (190, 20, 16)
LINE_SOFT = (190, 20, 16, 170)

# 几何（模型单位，随后按画布归一化）
YAW = 45.0
ELEV = 30.0
OPEN = 106.0
W, D, T, H = 520.0, 346.0, 18.0, 286.0
BEZ = 46.0
RAD = 54.0
W_MAIN = 60.0
W_SUB = 34.0


def _proj(yaw, elev):
    a, b = math.radians(yaw), math.radians(elev)
    ca, sa, cb, sb = math.cos(a), math.sin(a), math.cos(b), math.sin(b)
    return lambda x, y, z: ((x * ca - y * sa), (x * sa + y * ca) * sb - z * cb)


def _rrect(u0, v0, u1, v1, r, n=12):
    pts = []
    for cx, cy, t0, t1 in ((u0 + r, v0 + r, math.pi, 1.5 * math.pi),
                           (u1 - r, v0 + r, 1.5 * math.pi, 2 * math.pi),
                           (u1 - r, v1 - r, 0, 0.5 * math.pi),
                           (u0 + r, v1 - r, 0.5 * math.pi, math.pi)):
        for i in range(n + 1):
            t = t0 + (t1 - t0) * i / n
            pts.append((cx + r * math.cos(t), cy + r * math.sin(t)))
    pts.append(pts[0])
    return pts


def _vgrad(w, h, top, bot):
    img = Image.new('RGB', (1, h))
    px = img.load()
    for y in range(h):
        t = y / max(1, h - 1)
        px[0, y] = tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3))
    return img.resize((w, h), Image.BILINEAR)


def draw_device(canvas_px, fill_ratio=0.80, line_w=W_MAIN, sub_w=W_SUB):
    """在透明画布上画设备线条，返回 RGBA。fill_ratio = 设备占画布比例。"""
    S = canvas_px * SS
    P = _proj(YAW, ELEV)
    th = math.radians(OPEN)
    ct, st = math.cos(th), math.sin(th)

    def L(u, vv, off=0.0):
        return (u, vv * ct, T + vv * st + off)

    probe = [L(0, 0), L(W, 0), L(0, H), L(W, H),
             (0, 0, T), (W, 0, T), (0, D, T), (W, D, T)]
    pj = [P(*q) for q in probe]
    minx, maxx = min(q[0] for q in pj), max(q[0] for q in pj)
    miny, maxy = min(q[1] for q in pj), max(q[1] for q in pj)
    span = max(maxx - minx, maxy - miny)
    k = (S * fill_ratio) / span
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2

    def Q(q):
        x, y = P(*q)
        return ((x - cx) * k + S / 2, (y - cy) * k + S / 2)

    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    wm = max(2, int(line_w * SS / 3))
    ws = max(2, int(sub_w * SS / 3))

    def stroke(pts3, width, color):
        pts = [Q(p) for p in pts3]
        d.line(pts, fill=color, width=width, joint='curve')
        for p in (pts[0], pts[-1]):
            d.ellipse([p[0] - width / 2, p[1] - width / 2,
                       p[0] + width / 2, p[1] + width / 2], fill=color)

    # 底座顶面
    stroke([(u, vv, T) for u, vv in _rrect(0, 0, W, D, RAD)], wm, LINE + (255,))
    # 上盖外壳 + 两屏内框
    stroke([L(u, vv) for u, vv in _rrect(0, 0, W, H, RAD)], wm, LINE + (255,))
    stroke([L(u, vv, 1) for u, vv in _rrect(BEZ, BEZ, W - BEZ, H - BEZ, max(10, RAD - 10))],
           ws, LINE_SOFT)
    stroke([(u, vv, T + 1) for u, vv in _rrect(BEZ, BEZ, W - BEZ, D - BEZ, max(10, RAD - 10))],
           ws, LINE_SOFT)

    # 播放三角
    cxx, cyy, s = W / 2, H * 0.52, 40
    tri = [L(cxx - s * 0.42, cyy - s * 0.60, 1), L(cxx + s * 0.60, cyy, 1),
           L(cxx - s * 0.42, cyy + s * 0.60, 1)]
    d.polygon([Q(p) for p in tri], fill=LINE + (255,))

    return img.resize((canvas_px, canvas_px), Image.LANCZOS)


def full_icon(size=MASTER):
    """带底板的正方形图标。"""
    bg = _vgrad(size, size, BG_TOP, BG_BOT).convert('RGBA')
    dev = draw_device(size, fill_ratio=0.80)
    bg.alpha_composite(dev)
    return bg


def foreground(size=MASTER):
    """自适应图标前景：透明，内容收在安全区（约 62%）。"""
    return draw_device(size, fill_ratio=0.62)


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
