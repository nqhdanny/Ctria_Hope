#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按 com.superds64.plus 的按键语言重绘 Citra MMJ 输入覆盖层主题：
  · 双线描边、内部透明、灰色系
  · 十字键 = 大圆 + 四枚盾形箭头 + 四角小圆点
  · 摇杆   = 双环
  · 肩键   = 豆形轮廓 + 字母
  · 功能键 = 圆环 + 内嵌圆角框 + 文字
输出 btn_out2/，文件名与 InputOverlay.ResNames 对齐。
"""
import os
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

S = 4
CELL = 256
OUT = 'btn_v3'
FONT = 'C:/Windows/Fonts/arialbd.ttf'
os.makedirs(OUT, exist_ok=True)

STROKE = (214, 222, 232, 238)
STROKE_DIM = (152, 162, 176, 205)
GLYPH = (226, 233, 241, 246)
HALO = (0, 0, 0, 90)


def canvas(size=(CELL, CELL)):
    return Image.new('RGBA', (size[0] * S, size[1] * S), (0, 0, 0, 0))


def font(px):
    return ImageFont.truetype(FONT, max(8, int(px)))


def finish(im, size=(CELL, CELL)):
    return im.resize(size, Image.LANCZOS)


def ring(mask, width, color, alpha=255):
    w = max(1, int(width))
    big = np.array(mask.filter(ImageFilter.MaxFilter(w * 2 + 1)), dtype=np.int16)
    small = np.array(mask.filter(ImageFilter.MinFilter(w * 2 + 1)), dtype=np.int16)
    r = Image.fromarray(np.clip(big - small, 0, 255).astype('uint8'))
    layer = Image.new('RGBA', mask.size, color[:3] + (0,))
    layer.putalpha(r.point(lambda v: min(255, int(v * alpha / 255.0))))
    return layer


def halo(mask, blur, alpha):
    m = mask.filter(ImageFilter.GaussianBlur(blur))
    h = Image.new('RGBA', mask.size, HALO[:3] + (0,))
    h.putalpha(m.point(lambda v: int(v * alpha / 255.0)))
    return h


def dual_ring(mask, width, color, alpha=255, dark=(0, 0, 0, 150)):
    """双线描边：外侧深色轮廓 + 内侧浅色主线，保证白底/亮底也能看清"""
    out = Image.new('RGBA', mask.size, (0, 0, 0, 0))
    out.alpha_composite(ring(mask, width * 2.15, dark[:3], dark[3]))
    out.alpha_composite(ring(mask, width, color[:3], alpha))
    return out



def plate(mask, alpha):
    """半透明暗色底板：Citra 的按键压在游戏画面上，纯描边在亮底会看不见"""
    g = Image.new('RGBA', mask.size, (8, 11, 16, 0))
    g.putalpha(mask.point(lambda v: int(v * alpha / 255.0)))
    return g


def text(img, s, cx, cy, px, color=GLYPH, tracking=0, stroke=0):
    d = ImageDraw.Draw(img)
    f = font(px)
    if tracking:
        ws = [d.textlength(ch, font=f) for ch in s]
        total = sum(ws) + tracking * (len(s) - 1)
        x = cx - total / 2
        for ch, w in zip(s, ws):
            d.text((x, cy), ch, font=f, fill=color, anchor='lm',
                   stroke_width=stroke, stroke_fill=(0, 0, 0, 160))
            x += w + tracking
    else:
        d.text((cx, cy), s, font=f, fill=color, anchor='mm',
               stroke_width=stroke, stroke_fill=(0, 0, 0, 160))


# ------------------------------------------------------------ 盾形臂
def shield_path(cx, cy, r_tip, r_out, half_w, angle_deg):
    """返回屏幕坐标下的盾形多边形点列。angle 0=上 90=右 180=下 270=左
    局部坐标 +y 指向「外侧」。"""
    a = math.radians(angle_deg)
    ux, uy = math.sin(a), -math.cos(a)      # 外法向
    vx, vy = math.cos(a), math.sin(a)       # 切向
    hw = half_w
    sh = r_tip + (r_out - r_tip) * 0.46     # 肩部高度
    rad = min(hw * 0.55, (r_out - sh) * 0.55)

    local = []
    # 尖端
    local.append((0.0, r_tip))
    # 右侧肩
    local.append((hw, sh))
    local.append((hw, r_out - rad))
    for t in np.linspace(0, math.pi / 2, 10):
        local.append((hw - rad + math.cos(t) * rad, r_out - rad + math.sin(t) * rad))
    # 外侧平边
    for t in np.linspace(1, 0, 8):
        local.append((-hw + rad + t * (2 * hw - 2 * rad), r_out))
    for t in np.linspace(math.pi / 2, math.pi, 10):
        local.append((-hw + rad + math.cos(t) * rad, r_out - rad + math.sin(t) * rad))
    local.append((-hw, r_out - rad))
    local.append((-hw, sh))

    out = []
    for (x, y) in local:
        out.append((cx + x * vx + y * ux, cy + x * vy + y * uy))
    return out


def draw_arm(img, cx, cy, r_tip, r_out, half_w, angle, lit=False, base_stroke=2.2 * S):
    m = Image.new('L', img.size, 0)
    pts = shield_path(cx, cy, r_tip, r_out, half_w, angle)
    ImageDraw.Draw(m).polygon(pts, fill=255)
    img.alpha_composite(halo(m, 4 * S, 55))
    img.alpha_composite(ring(m, base_stroke * (1.25 if lit else 1.0),
                             STROKE if lit else STROKE_DIM, 250 if lit else 215))

    # 内部三角
    a = math.radians(angle)
    ux, uy = math.sin(a), -math.cos(a)
    vx, vy = math.cos(a), math.sin(a)
    d = r_tip + (r_out - r_tip) * 0.50
    h = half_w * 0.46
    tri = Image.new('L', img.size, 0)
    ImageDraw.Draw(tri).polygon([
        (cx + ux * (d + h * 1.15), cy + uy * (d + h * 1.15)),
        (cx + ux * (d - h * 0.55) + vx * h, cy + uy * (d - h * 0.55) + vy * h),
        (cx + ux * (d - h * 0.55) - vx * h, cy + uy * (d - h * 0.55) - vy * h),
    ], fill=255)
    g = Image.new('RGBA', img.size, GLYPH[:3] + (0,))
    g.putalpha(tri.point(lambda v: int(v * (1.0 if lit else 0.85))))
    img.alpha_composite(g)


# ------------------------------------------------------------ 十字键
def dpad(mode=0):
    im = canvas()
    W = im.size[0]
    cx = cy = W / 2
    R = W * 0.472

    m = Image.new('L', im.size, 0)
    ImageDraw.Draw(m).ellipse([cx - R, cy - R, cx + R, cy + R], fill=255)
    im.alpha_composite(halo(m, 6 * S, 95))
    im.alpha_composite(plate(m, 105))
    im.alpha_composite(dual_ring(m, 1.3 * S, STROKE_DIM, 200))

    r_out = R * 0.660
    r_tip = R * 0.150
    half_w = R * 0.265
    lit = {1: [0], 2: [0, 90]}.get(mode, [])
    for a in (0, 90, 180, 270):
        draw_arm(im, cx, cy, r_tip, r_out, half_w, a, lit=(a in lit))

    d = ImageDraw.Draw(im)
    dr = R * 0.050
    for k in range(4):
        ang = math.radians(45 + 90 * k)
        px, py = cx + math.cos(ang) * R * 0.655, cy + math.sin(ang) * R * 0.655
        d.ellipse([px - dr, py - dr, px + dr, py + dr],
                  outline=STROKE_DIM[:3] + (185,), width=max(1, int(1.5 * S)))
    return finish(im)


# ------------------------------------------------------------ 字母圆键
def face_button(letter, pressed=False, d_ratio=0.80):
    im = canvas()
    W = im.size[0]
    R = W * d_ratio / 2
    cx = cy = W / 2
    m = Image.new('L', im.size, 0)
    ImageDraw.Draw(m).ellipse([cx - R, cy - R, cx + R, cy + R], fill=255)
    im.alpha_composite(halo(m, 6 * S, 105))
    im.alpha_composite(plate(m, 130 if pressed else 105))
    if pressed:
        g = Image.new('RGBA', im.size, (255, 255, 255, 0))
        g.putalpha(m.point(lambda v: int(v * 0.20)))
        im.alpha_composite(g)
    im.alpha_composite(dual_ring(m, 1.3 * S, STROKE, 250 if pressed else 240))
    r2 = R - 4.6 * S
    m2 = Image.new('L', im.size, 0)
    ImageDraw.Draw(m2).ellipse([cx - r2, cy - r2, cx + r2, cy + r2], fill=255)
    im.alpha_composite(ring(m2, 0.8 * S, STROKE_DIM, 110))
    text(im, letter, cx, cy + 1 * S, R * 0.95, color=(255, 255, 255, 250), stroke=int(0.7 * S))
    return finish(im)


# ------------------------------------------------------------ 豆形肩键
def bean_mask(im, x0, y0, w, h):
    m = Image.new('L', im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=h * 0.50, fill=255)
    # 底部波浪缺口
    notch = Image.new('L', im.size, 0)
    ImageDraw.Draw(notch).ellipse([x0 + w * 0.30, y0 + h * 0.72,
                                   x0 + w * 1.10, y0 + h * 1.55], fill=255)
    notch = notch.filter(ImageFilter.GaussianBlur(2 * S))
    arr = np.array(m, dtype=np.int16) - (np.array(notch, dtype=np.int16) * 55 // 100)
    return Image.fromarray(np.clip(arr, 0, 255).astype('uint8'))


def shoulder(label, pressed=False, size=(CELL, 128)):
    im = canvas(size)
    W, H = im.size
    m = bean_mask(im, W * 0.05, H * 0.12, W * 0.90, H * 0.76)
    b = m.point(lambda v: 255 if v > 128 else 0)
    im.alpha_composite(halo(b, 5 * S, 55))
    im.alpha_composite(plate(b, 125 if pressed else 105))
    if pressed:
        g = Image.new('RGBA', im.size, (255, 255, 255, 0))
        g.putalpha(b.point(lambda v: int(v * 0.18)))
        im.alpha_composite(g)
    im.alpha_composite(ring(b, 2.3 * S, STROKE, 240))
    inner = b.filter(ImageFilter.MinFilter(int(5 * S) | 1))
    im.alpha_composite(ring(inner, 0.8 * S, STROKE_DIM, 95))
    text(im, label, W * 0.5, H * 0.44, H * 0.36, color=(255, 255, 255, 248), stroke=int(0.6 * S))
    return finish(im, size)


# ------------------------------------------------------------ 功能小键
def sys_button(label, pressed=False, size=(CELL, CELL), px=0.19):
    im = canvas(size)
    W, H = im.size
    cx, cy = W / 2, H / 2
    R = W * 0.41
    m = Image.new('L', im.size, 0)
    ImageDraw.Draw(m).ellipse([cx - R, cy - R, cx + R, cy + R], fill=255)
    im.alpha_composite(halo(m, 5 * S, 95))
    if pressed:
        g = Image.new('RGBA', im.size, (255, 255, 255, 0))
        g.putalpha(m.point(lambda v: int(v * 0.18)))
        im.alpha_composite(g)
    im.alpha_composite(dual_ring(m, 1.25 * S, STROKE_DIM, 220))
    pad = W * 0.085
    m2 = Image.new('L', im.size, 0)
    ImageDraw.Draw(m2).rounded_rectangle([cx - R + pad, cy - R + pad,
                                          cx + R - pad, cy + R - pad],
                                         radius=R * 0.34, fill=255)
    im.alpha_composite(ring(m2, 1.3 * S, STROKE, 195))
    if label:
        # 自动缩字号，保证文字落在内框里
        maxw = (2 * R - 2 * pad) * 0.86
        px_size = W * px
        f = font(px_size)
        while f.getlength(label) > maxw and px_size > 8:
            px_size *= 0.94
            f = font(px_size)
        text(im, label, cx, cy, px_size, color=(255, 255, 255, 245),
             tracking=W * 0.006)
    return finish(im, size)


# ------------------------------------------------------------ 摇杆
def stick(kind='base', d_ratio=0.88):
    im = canvas()
    W = im.size[0]
    R = W * d_ratio / 2
    cx = cy = W / 2
    m = Image.new('L', im.size, 0)
    ImageDraw.Draw(m).ellipse([cx - R, cy - R, cx + R, cy + R], fill=255)

    if kind == 'range':
        g = Image.new('RGBA', im.size, (255, 255, 255, 0))
        g.putalpha(m.filter(ImageFilter.GaussianBlur(6 * S)).point(lambda v: int(v * 0.14)))
        im.alpha_composite(g)
        im.alpha_composite(ring(m, 0.9 * S, STROKE_DIM, 85))
        return finish(im)

    im.alpha_composite(halo(m, 6 * S, 95))
    im.alpha_composite(plate(m, 105))
    im.alpha_composite(dual_ring(m, 1.25 * S, STROKE_DIM, 200))
    r2 = R * (0.66 if kind == 'base' else 0.56)
    m2 = Image.new('L', im.size, 0)
    ImageDraw.Draw(m2).ellipse([cx - r2, cy - r2, cx + r2, cy + r2], fill=255)
    if kind == 'pressed':
        g = Image.new('RGBA', im.size, (255, 255, 255, 0))
        g.putalpha(m2.point(lambda v: int(v * 0.24)))
        im.alpha_composite(g)
    im.alpha_composite(dual_ring(m2, 1.2 * S, STROKE, 235))
    return finish(im)


# ------------------------------------------------------------ 主页键
def home_button(pressed=False):
    im = canvas()
    W = im.size[0]
    R = W * 0.36
    cx = cy = W / 2
    m = Image.new('L', im.size, 0)
    ImageDraw.Draw(m).ellipse([cx - R, cy - R, cx + R, cy + R], fill=255)
    im.alpha_composite(halo(m, 5 * S, 95))
    if pressed:
        g = Image.new('RGBA', im.size, (255, 255, 255, 0))
        g.putalpha(m.point(lambda v: int(v * 0.20)))
        im.alpha_composite(g)
    im.alpha_composite(dual_ring(m, 1.25 * S, STROKE_DIM, 215))
    d = ImageDraw.Draw(im)
    u = R * 0.34
    lw = max(1, int(1.7 * S))
    col = (242, 247, 252, 240)
    d.line([(cx - u, cy - u * 0.18), (cx, cy - u * 1.0), (cx + u, cy - u * 0.18)],
           fill=col, width=lw, joint='curve')
    d.line([(cx - u * 0.70, cy - u * 0.30), (cx - u * 0.70, cy + u * 0.78),
            (cx + u * 0.70, cy + u * 0.78), (cx + u * 0.70, cy - u * 0.30)],
           fill=col, width=lw, joint='curve')
    return finish(im)



def fade_y(out):
    """Y 键压入下屏的那一段做线性渐隐（侵入 55px，素材 256 画布中 75.2px）"""
    import numpy as np
    for name in ('y.png', 'y_pressed.png'):
        p = os.path.join(out, name)
        im = Image.open(p).convert('RGBA')
        a = np.array(im).astype(np.float32)
        xs = np.arange(im.width, dtype=np.float32)
        start = im.width * (1 - 0.80) / 2.0
        end = start + 75.2
        t = np.clip((xs - start) / (end - start), 0.0, 1.0)
        a[:, :, 3] = a[:, :, 3] * t[None, :]
        Image.fromarray(a.astype(np.uint8), 'RGBA').save(p)
        print('  faded %s  %.1f -> %.1f' % (name, start, end))

def save(im, name):
    im.save(os.path.join(OUT, name + '.png'))
    print('  %-24s %s' % (name + '.png', im.size))


def main():
    print('字母键…')
    for L in ['A', 'B', 'X', 'Y']:
        save(face_button(L, False), L.lower())
        save(face_button(L, True), L.lower() + '_pressed')

    print('肩键…')
    save(shoulder('L', False), 'l')
    save(shoulder('L', True), 'l_pressed')
    save(shoulder('R', False), 'r')
    save(shoulder('R', True), 'r_pressed')
    save(sys_button('ZL', False, (CELL, CELL), 0.22), 'zl')
    save(sys_button('ZL', True, (CELL, CELL), 0.22), 'zl_pressed')
    save(sys_button('ZR', False, (CELL, CELL), 0.22), 'zr')
    save(sys_button('ZR', True, (CELL, CELL), 0.22), 'zr_pressed')

    print('功能键…')
    save(sys_button('START', False, (CELL, CELL), 0.155), 'start')
    save(sys_button('START', True, (CELL, CELL), 0.155), 'start_pressed')
    save(sys_button('SELECT', False, (CELL, CELL), 0.155), 'select')
    save(sys_button('SELECT', True, (CELL, CELL), 0.155), 'select_pressed')
    for n, lab in [('one', '1'), ('two', '2'), ('three', '3')]:
        save(face_button(lab, False, 0.64), n)
        save(face_button(lab, True, 0.64), n + '_pressed')

    print('十字键…')
    save(dpad(0), 'dpad')
    save(dpad(1), 'dpad_pressed_one')
    save(dpad(2), 'dpad_pressed_two')

    print('摇杆…')
    for prefix in ('joystick', 'c_stick'):
        save(stick('base'), prefix)
        save(stick('pressed'), prefix + '_pressed')
        save(stick('range'), prefix + '_range')

    print('主页键…')
    save(home_button(False), 'home')
    save(home_button(True), 'home_pressed')
    fade_y(OUT)
    print('完成 ->', OUT)


if __name__ == '__main__':
    main()
