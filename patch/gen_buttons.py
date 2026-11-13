#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 Citra MMJ 自定义输入覆盖层主题素材（描边玻璃风格，参考 SuperDS64 3DS 控制布局）。

输出到 btn_out/，文件名与 Citra 的 InputOverlay.ResNames 一一对应：
  a/a_pressed b/x/y, start/select, l/r, zl/zr, home, one/two/three,
  dpad / dpad_pressed_one / dpad_pressed_two,
  joystick / joystick_pressed / joystick_range,
  c_stick / c_stick_pressed / c_stick_range

注意：Citra 会按「原资源宽度」归一化缩放，zip 里图片的像素尺寸不影响最终大小，
      只有「可见图形占画布的比例」决定视觉大小 —— 所以中心圆要比画布小一圈。
"""
import os
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

S = 4                      # 超采样倍数
OUT = 'btn_out'
FONT_BOLD = 'C:/Windows/Fonts/arialbd.ttf'
os.makedirs(OUT, exist_ok=True)

# 配色
RIM = (233, 241, 250)
RIM_HI = (255, 255, 255)
TEXT = (245, 249, 253)
SHADOW = (0, 0, 0)

CELL = 256                 # 目标画布


def _canvas(size=(CELL, CELL)):
    return Image.new('RGBA', (size[0] * S, size[1] * S), (0, 0, 0, 0))


def _font(px):
    return ImageFont.truetype(FONT_BOLD, px)


def _ring_from_mask(mask, width, color, alpha=255):
    """用膨胀-腐蚀得到形状边缘的描边环"""
    w = max(1, int(width))
    big = mask.filter(ImageFilter.MaxFilter(w * 2 + 1))
    small = mask.filter(ImageFilter.MinFilter(w * 2 + 1))
    ring = Image.new('L', mask.size, 0)
    ring.paste(big, (0, 0))
    ring = Image.subtract(ring, small) if hasattr(Image, 'subtract') else None
    if ring is None:
        import numpy as np
        b = np.array(big, dtype=np.int16)
        s2 = np.array(small, dtype=np.int16)
        ring = Image.fromarray(np.clip(b - s2, 0, 255).astype('uint8'))
    layer = Image.new('RGBA', mask.size, color + (0,))
    layer.putalpha(ring.point(lambda v: min(255, int(v * alpha / 255.0))))
    return layer


def _radial(size, center, r0, c0, r1, c1):
    """简易径向渐变（用圆锥/同心圆叠加，够用且快）"""
    import numpy as np
    w, h = size
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt((xx - center[0]) ** 2 + (yy - center[1]) ** 2) / r1
    d = np.clip(d, 0, 1)[..., None]
    a = (np.array(c0, dtype='float32')[None, None, :] * (1 - d)
         + np.array(c1, dtype='float32')[None, None, :] * d)
    a[..., 3] *= (1 - np.clip((d[..., 0] - 0.85) / 0.15, 0, 1))   # 边缘淡出
    return Image.fromarray(np.clip(a, 0, 255).astype('uint8'), 'RGBA')


def _drop_shadow(mask, blur, spread, alpha):
    m = mask.filter(ImageFilter.MaxFilter(spread * 2 + 1))
    m = m.filter(ImageFilter.GaussianBlur(blur))
    sh = Image.new('RGBA', mask.size, SHADOW + (0,))
    sh.putalpha(m.point(lambda v: int(v * alpha / 255.0)))
    return sh


def _finish(im, size=(CELL, CELL)):
    return im.resize(size, Image.LANCZOS)


def _draw_text(img, text, cx, cy, px, color=TEXT, shadow=2, tracking=0):
    d = ImageDraw.Draw(img)
    f = _font(px)
    if tracking:
        widths = [d.textlength(ch, font=f) for ch in text]
        total = sum(widths) + tracking * (len(text) - 1)
        x = cx - total / 2
        for ch, w in zip(text, widths):
            d.text((x, cy), ch, font=f, fill=color, anchor='lm',
                   stroke_width=shadow, stroke_fill=(0, 0, 0, 120))
            x += w + tracking
    else:
        d.text((cx, cy), text, font=f, fill=color, anchor='mm',
               stroke_width=shadow, stroke_fill=(0, 0, 0, 120))


# ---------------------------------------------------------------- 圆形按钮
def circle_button(letter, pressed=False, d_ratio=0.78):
    im = _canvas()
    W = im.size[0]
    D = W * d_ratio
    R = D / 2
    cx = cy = W / 2

    mask = Image.new('L', im.size, 0)
    ImageDraw.Draw(mask).ellipse([cx - R, cy - R, cx + R, cy + R], fill=255)

    # 外投影
    im.alpha_composite(_drop_shadow(mask, blur=10 * S // 2, spread=2 * S, alpha=70))

    # 玻璃填充
    if pressed:
        glass = _radial(im.size, (cx, cy * 0.94), R, (255, 255, 255, 26), R, (6, 9, 14, 165))
    else:
        glass = _radial(im.size, (cx, cy * 0.86), R, (255, 255, 255, 40), R, (12, 17, 25, 128))
    glass.putalpha(Image.composite(glass.getchannel('A'), Image.new('L', im.size, 0), mask))
    im.alpha_composite(glass)

    # 镜面高光（左上）
    spec = Image.new('L', im.size, 0)
    sr = R * 0.62
    sx, sy = cx - R * 0.34, cy - R * 0.46
    ImageDraw.Draw(spec).ellipse([sx - sr, sy - sr * 0.72, sx + sr, sy + sr * 0.72], fill=255)
    spec = spec.filter(ImageFilter.GaussianBlur(int(R * 0.30)))
    spec = Image.composite(spec, Image.new('L', im.size, 0), mask)
    sp = Image.new('RGBA', im.size, (255, 255, 255, 0))
    sp.putalpha(spec.point(lambda v: int(v * (0.30 if pressed else 0.20))))
    im.alpha_composite(sp)

    # 描边
    im.alpha_composite(_ring_from_mask(mask, 1.5 * S, RIM_HI if pressed else RIM,
                                       255 if pressed else 232))

    # 底部内阴影（增加立体感）
    bottom = Image.new('L', im.size, 0)
    ImageDraw.Draw(bottom).ellipse([cx - R * 0.94, cy + R * 0.10, cx + R * 0.94, cy + R * 1.02],
                                   fill=255)
    bottom = bottom.filter(ImageFilter.GaussianBlur(int(R * 0.16)))
    bottom = Image.composite(bottom, Image.new('L', im.size, 0), mask)
    bs = Image.new('RGBA', im.size, (0, 0, 0, 0))
    bs.putalpha(bottom.point(lambda v: int(v * 0.22)))
    im.alpha_composite(bs)

    # 顶部高光弧
    hi = Image.new('RGBA', im.size, (0, 0, 0, 0))
    hd = ImageDraw.Draw(hi)
    rr = R - 2.2 * S
    hd.arc([cx - rr, cy - rr, cx + rr, cy + rr], 198, 342,
           fill=(255, 255, 255, 150 if pressed else 105), width=int(1.6 * S))
    im.alpha_composite(hi)

    # 按压外发光
    if pressed:
        glow = mask.filter(ImageFilter.MaxFilter(int(1.5 * S) * 2 + 1)).filter(
            ImageFilter.GaussianBlur(4 * S))
        g = Image.new('RGBA', im.size, (255, 255, 255, 0))
        g.putalpha(glow.point(lambda v: int(v * 0.32)))
        im.alpha_composite(g)

    if letter:
        _draw_text(im, letter, cx, cy + R * 0.02, int(D * 0.44),
                   color=TEXT, shadow=int(0.9 * S))
    return _finish(im)


# ---------------------------------------------------------------- 胶囊按钮
def pill_button(text, pressed=False, canvas=(CELL, CELL), pill=(236, 96), px_ratio=0.52):
    im = _canvas(canvas)
    W, H = im.size
    pw, ph = pill[0] * S, pill[1] * S
    x0 = (W - pw) / 2
    y0 = (H - ph) / 2
    r = ph / 2

    mask = Image.new('L', im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([x0, y0, x0 + pw, y0 + ph], radius=r, fill=255)

    im.alpha_composite(_drop_shadow(mask, blur=9 * S // 2, spread=2 * S, alpha=70))
    if pressed:
        glass = _radial(im.size, (W / 2, y0 + ph * 0.35), ph,
                        (255, 255, 255, 56), ph * 5, (26, 34, 46, 140))
    else:
        glass = _radial(im.size, (W / 2, y0 + ph * 0.30), ph,
                        (255, 255, 255, 30), ph * 5, (16, 22, 30, 88))
    glass.putalpha(Image.composite(glass.getchannel('A'), Image.new('L', im.size, 0), mask))
    im.alpha_composite(glass)
    im.alpha_composite(_ring_from_mask(mask, 1.5 * S, RIM_HI if pressed else RIM, 255 if pressed else 230))

    if pressed:
        glow = mask.filter(ImageFilter.MaxFilter(int(1.4 * S) * 2 + 1)).filter(
            ImageFilter.GaussianBlur(4 * S))
        g = Image.new('RGBA', im.size, (255, 255, 255, 0))
        g.putalpha(glow.point(lambda v: int(v * 0.28)))
        im.alpha_composite(g)

    if text:
        _draw_text(im, text, W / 2, H / 2, int(ph * px_ratio), color=TEXT, shadow=int(0.8 * S))
    return _finish(im, canvas)


# ---------------------------------------------------------------- 十字键
def dpad(mode=0, d_ratio=0.90):
    """mode 0=普通 1=上按下 2=上+右按下（与官方素材语义一致）"""
    im = _canvas()
    W = im.size[0]
    Sd = W * d_ratio
    arm = Sd * 0.345
    cx = cy = W / 2
    half = Sd / 2
    off = arm / 2
    rad = arm * 0.30

    mask = Image.new('L', im.size, 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([cx - half, cy - off, cx + half, cy + off], radius=rad, fill=255)
    md.rounded_rectangle([cx - off, cy - half, cx + off, cy + half], radius=rad, fill=255)

    im.alpha_composite(_drop_shadow(mask, blur=5 * S, spread=2 * S, alpha=64))

    glass = _radial(im.size, (cx, cy * 0.85), Sd * 0.2, (255, 255, 255, 34), Sd * 0.75, (14, 20, 28, 96))
    glass.putalpha(Image.composite(glass.getchannel('A'), Image.new('L', im.size, 0), mask))
    im.alpha_composite(glass)

    # 按下方向：向内压暗 + 亮边
    if mode in (1, 2):
        arms = [(cx, cy - half, cx + off, cy + off)] if mode == 1 else \
               [(cx, cy - half, cx + off, cy + off), (cx - half, cy - off, cx + half, cy + off)]
        for a in arms:
            im2 = Image.new('L', im.size, 0)
            ImageDraw.Draw(im2).rectangle(a, fill=255)
            pressed_mask = Image.composite(im2, Image.new('L', im.size, 0), mask)
            dark = Image.new('RGBA', im.size, (0, 0, 0, 0))
            dark.putalpha(pressed_mask.point(lambda v: int(v * 0.55)))
            im.alpha_composite(dark)
            im.alpha_composite(_ring_from_mask(pressed_mask, 1.1 * S, RIM_HI, 190))

    im.alpha_composite(_ring_from_mask(mask, 1.5 * S, RIM, 215))

    # 四个方向的刻痕
    d = ImageDraw.Draw(im)
    tick = int(arm * 0.16)
    for (dx, dy, w2, h2) in [(0, -1, tick, arm * 0.36), (0, 1, tick, arm * 0.36),
                             (-1, 0, arm * 0.36, tick), (1, 0, arm * 0.36, tick)]:
        px = cx + dx * Sd * 0.30
        py = cy + dy * Sd * 0.30
        d.rounded_rectangle([px - w2 / 2, py - h2 / 2, px + w2 / 2, py + h2 / 2],
                            radius=tick / 2, fill=(0, 0, 0, 70))
    return _finish(im)


# ---------------------------------------------------------------- 摇杆
def stick(kind='base', d_ratio=0.74):
    im = _canvas()
    W = im.size[0]
    D = W * d_ratio
    R = D / 2
    cx = cy = W / 2

    if kind == 'range':
        g = _radial(im.size, (cx, cy), R * 0.2, (255, 255, 255, 26), R, (255, 255, 255, 0))
        im.alpha_composite(g)
        mask = Image.new('L', im.size, 0)
        ImageDraw.Draw(mask).ellipse([cx - R, cy - R, cx + R, cy + R], outline=255, width=int(1.2 * S))
        im.alpha_composite(_ring_from_mask(mask, 0.8 * S, RIM, 90))
        return _finish(im)

    mask = Image.new('L', im.size, 0)
    ImageDraw.Draw(mask).ellipse([cx - R, cy - R, cx + R, cy + R], fill=255)
    im.alpha_composite(_drop_shadow(mask, blur=6 * S, spread=2 * S, alpha=60))

    if kind == 'base':
        glass = _radial(im.size, (cx, cy * 0.86), R * 0.1, (255, 255, 255, 26), R, (10, 14, 20, 108))
        glass.putalpha(Image.composite(glass.getchannel('A'), Image.new('L', im.size, 0), mask))
        im.alpha_composite(glass)
        im.alpha_composite(_ring_from_mask(mask, 1.6 * S, RIM, 215))
        # 内圈参考线 + 中心点
        d2 = ImageDraw.Draw(im)
        ir = R * 0.52
        d2.ellipse([cx - ir, cy - ir, cx + ir, cy + ir], outline=(255, 255, 255, 46),
                   width=int(1.0 * S))
        cr = R * 0.055
        d2.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=(255, 255, 255, 70))
    else:  # pressed = 摇杆头
        glass = _radial(im.size, (cx, cy * 0.80), R * 0.1, (255, 255, 255, 92), R, (10, 14, 20, 205))
        glass.putalpha(Image.composite(glass.getchannel('A'), Image.new('L', im.size, 0), mask))
        im.alpha_composite(glass)
        im.alpha_composite(_ring_from_mask(mask, 1.8 * S, RIM_HI, 250))
        # 双高光，做出磨砂玻璃球感
        for (ox, oy, sc, al) in [(-0.30, -0.44, 0.52, 0.42), (0.26, 0.34, 0.26, 0.18)]:
            spec = Image.new('L', im.size, 0)
            sr = R * sc
            sx, sy = cx + R * ox, cy + R * oy
            ImageDraw.Draw(spec).ellipse([sx - sr, sy - sr * 0.7, sx + sr, sy + sr * 0.7], fill=255)
            spec = spec.filter(ImageFilter.GaussianBlur(int(R * 0.26)))
            spec = Image.composite(spec, Image.new('L', im.size, 0), mask)
            sp = Image.new('RGBA', im.size, (255, 255, 255, 0))
            sp.putalpha(spec.point(lambda v: int(v * al)))
            im.alpha_composite(sp)
    return _finish(im)


# ---------------------------------------------------------------- 主页键
def home_button(pressed=False):
    im = _canvas()
    W = im.size[0]
    D = W * 0.70
    R = D / 2
    cx = cy = W / 2
    mask = Image.new('L', im.size, 0)
    ImageDraw.Draw(mask).ellipse([cx - R, cy - R, cx + R, cy + R], fill=255)
    im.alpha_composite(_drop_shadow(mask, blur=5 * S, spread=2 * S, alpha=70))
    glass = _radial(im.size, (cx, cy * 0.9), R, (255, 255, 255, 30 if not pressed else 60),
                    R, (16, 22, 30, 100 if not pressed else 150))
    glass.putalpha(Image.composite(glass.getchannel('A'), Image.new('L', im.size, 0), mask))
    im.alpha_composite(glass)
    im.alpha_composite(_ring_from_mask(mask, 1.5 * S, RIM_HI if pressed else RIM, 240))

    # 房子图标（描边）
    d = ImageDraw.Draw(im)
    u = D * 0.085
    lw = int(1.5 * S)
    col = (250, 252, 255, 235)
    roof = [(cx, cy - u * 2.6), (cx + u * 2.6, cy + u * 0.1), (cx - u * 2.6, cy + u * 0.1)]
    d.line(roof + [roof[0]], fill=col, width=lw, joint='curve')
    d.line([(cx - u * 1.85, cy + u * 0.1), (cx - u * 1.85, cy + u * 2.2),
            (cx + u * 1.85, cy + u * 2.2), (cx + u * 1.85, cy + u * 0.1)],
           fill=col, width=lw, joint='curve')
    d.rectangle([cx - u * 0.7, cy + u * 0.9, cx + u * 0.7, cy + u * 2.2],
                outline=col, width=max(1, lw - 1))
    return _finish(im)


def save(im, name):
    im.save(os.path.join(OUT, name + '.png'))
    print('  %-22s %s' % (name + '.png', im.size))


def main():
    print('生成圆形字母键…')
    for letter in ['A', 'B', 'X', 'Y']:
        save(circle_button(letter, False), letter.lower())
        save(circle_button(letter, True), letter.lower() + '_pressed')

    print('生成肩键 / 功能键…')
    save(pill_button('L', False, (CELL, 128), (236, 96)), 'l')
    save(pill_button('L', True, (CELL, 128), (236, 96)), 'l_pressed')
    save(pill_button('R', False, (CELL, 128), (236, 96)), 'r')
    save(pill_button('R', True, (CELL, 128), (236, 96)), 'r_pressed')
    save(pill_button('ZL', False, (CELL, CELL), (214, 92)), 'zl')
    save(pill_button('ZL', True, (CELL, CELL), (214, 92)), 'zl_pressed')
    save(pill_button('ZR', False, (CELL, CELL), (214, 92)), 'zr')
    save(pill_button('ZR', True, (CELL, CELL), (214, 92)), 'zr_pressed')
    save(pill_button('START', False, (CELL, CELL), (232, 86), 0.42), 'start')
    save(pill_button('START', True, (CELL, CELL), (232, 86), 0.42), 'start_pressed')
    save(pill_button('SELECT', False, (CELL, CELL), (232, 86), 0.42), 'select')
    save(pill_button('SELECT', True, (CELL, CELL), (232, 86), 0.42), 'select_pressed')
    for n, label in [('one', '1'), ('two', '2'), ('three', '3')]:
        save(circle_button(label, False, 0.62), n)
        save(circle_button(label, True, 0.62), n + '_pressed')

    print('生成十字键…')
    save(dpad(0), 'dpad')
    save(dpad(1), 'dpad_pressed_one')
    save(dpad(2), 'dpad_pressed_two')

    print('生成摇杆…')
    save(stick('base'), 'joystick')
    save(stick('pressed'), 'joystick_pressed')
    save(stick('range'), 'joystick_range')
    save(stick('base'), 'c_stick')
    save(stick('pressed'), 'c_stick_pressed')
    save(stick('range'), 'c_stick_range')

    print('生成主页键…')
    save(home_button(False), 'home')
    save(home_button(True), 'home_pressed')

    print('完成 ->', OUT)


if __name__ == '__main__':
    main()
