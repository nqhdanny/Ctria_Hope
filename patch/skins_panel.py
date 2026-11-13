"""3DS 真机「面板造型」渲染器（设计稿阶段）。

和 skins_design.py 的区别：那个只画按键，背景靠纯色渐变托底；
这里把整块机身面板画出来 —— 屏幕嵌槽、按键凹井、肩键座、扬声器孔、
摄像头条、转轴端盖、丝印，全部按真机造型走。

输出：skin_preview/panel_<key>.png（整机预览，含模拟游戏画面）
      skin_preview/bg_<key>.jpg    （纯面板，即未来主题包里的 bg_portrait.jpg）
"""
import math
import os
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
import skins_design as sd

W, H = 1828, 2584
S = 2                      # 超采样倍数
W2, H2 = W * S, H * S

FONT_B = sd.FONT_BOLD

# ---- 布局（与 input-layout.ini / HingeHelper 实测一致，不要随手改） ----
# 上屏：TOP_INSET 是屏幕内容到机身侧边的距离（= 边框总宽）。
# 上屏严格 5:3，所以缩了宽必须同时缩高，垂直居中在原区域内。
# 28px 换算：内屏 1828 → 28/1828 = 0.015317，外屏 1264 折算 19px。
# 这个比例必须和 HingeHelper.TOP_INSET_RATIO 完全一致，否则背景边框和画面会错开。
TOP_INSET = 28
SCR_TOP_FULL = (0, 137, W, 1234)     # 上盖可用的整块区域（= HingeHelper 未缩进时的输出）
#   HingeHelper 把上屏底边从转轴(1292)上移 58px（TOP_HINGE_GAP_RATIO=0.045），
#   5:3 定高 1097 → 137..1234；再 inset 28 → 154..1217，离转轴 75px。


def _top_rect(inset):
    w = W - inset * 2
    h = int(round(w * 3 / 5.0))
    full_h = SCR_TOP_FULL[3] - SCR_TOP_FULL[1]
    y0 = SCR_TOP_FULL[1] + (full_h - h) // 2
    return (inset, y0, W - inset, y0 + h)


SCR_TOP = _top_rect(TOP_INSET)
# 下屏：缩到 992x744（严格 4:3），下移 88px 露出上边框，左右留白给两侧按键
SCR_BOT = (410, 1380, 1402, 2124)
SRC_SCR_BOT = (356, 1292, 1434, 2153)   # 旧截图里下屏的干净区域（左躲十字键、右躲 Y 键）
# 尺寸 = native 归一化后的真实显示尺寸（宽度固定，高度靠素材比例调），不是设计稿的目测值
BTN = {
    'l':      ((174, 1447), (233, 123)),
    'r':      ((1654, 1447), (233, 123)),
    'dpad':   ((201, 1796), (350, 350)),
    'stick':  ((201, 2196), (281, 281)),
    'x':      ((1618, 1680), (126, 126)),
    'y':      ((1508, 1796), (126, 126)),
    'a':      ((1727, 1796), (126, 126)),
    'b':      ((1618, 1912), (126, 126)),
    'home':   ((914, 2403), (129, 129)),
    'select': ((704, 2403), (112, 78)),
    'start':  ((1124, 2403), (112, 78)),
}
TOP_H = 196
BOT_Y = 1292
SCR_BOT_BOTTOM = 2153


# ---------------------------------------------------------------- 基础工具
def px(v):
    return int(round(v * S))


def _shift(a, dy, dx):
    if dy == 0 and dx == 0:
        return a
    out = np.zeros_like(a)
    h, w = a.shape
    ys_s = slice(max(0, -dy), h - max(0, dy))
    ys_d = slice(max(0, dy), h - max(0, -dy))
    xs_s = slice(max(0, -dx), w - max(0, dx))
    xs_d = slice(max(0, dx), w - max(0, -dx))
    out[ys_d, xs_d] = a[ys_s, xs_s]
    return out


def _blur(a, r):
    if r < 1:
        return a
    im = Image.fromarray(np.clip(a * 255.0, 0, 255).astype(np.uint8), 'L')
    return np.asarray(im.filter(ImageFilter.GaussianBlur(r)), dtype=np.float32) / 255.0


def darken(canvas, mask_l, amt):
    """按灰度遮罩压暗（amt 0~1）"""
    if amt <= 0:
        return
    m = mask_l.point(lambda v: int(v * amt))
    canvas.paste((0, 0, 0), (0, 0), m)


def lighten(canvas, mask_l, amt, color=(255, 255, 255)):
    if amt <= 0:
        return
    m = mask_l.point(lambda v: int(v * amt))
    canvas.paste(color, (0, 0), m)


# ---------------------------------------------------------------- 质感
def tex_gloss(canvas, skin, bands):
    """亮面塑料的斜向柔光带（bands: [(y0,y1), ...] 逻辑坐标）"""
    g = skin.get('gloss', 0.5)
    if g <= 0:
        return
    for (y0, y1) in bands:
        h = px(y1 - y0)
        w = px(W)
        ys = np.arange(h, dtype=np.float32)[:, None]
        xs = np.arange(w, dtype=np.float32)[None, :]
        t = xs * 0.93 + ys * 0.36
        m = np.exp(-((t - w * 0.22) / (w * 0.34)) ** 2) * 0.20 * g
        m += np.exp(-((t - w * 0.86) / (w * 0.10)) ** 2) * 0.13 * g
        m = np.clip(m, 0, 1)
        layer = Image.fromarray((m * 255).astype(np.uint8), 'L')
        canvas.paste((255, 255, 255), (0, px(y0)), layer)


def tex_bloom(canvas, skin, box, strength=0.07):
    """一大团柔光（灯箱反射），让塑料表面有起伏"""
    x0, y0, x1, y1 = box
    w, h = px(x1 - x0), px(y1 - y0)
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = w * 0.42, h * 0.38
    rx, ry = w * 0.55, h * 0.55
    m = np.exp(-(((xs - cx) / rx) ** 2 + ((ys - cy) / ry) ** 2) * 2.4) * strength
    layer = Image.fromarray((np.clip(m, 0, 1) * 255).astype(np.uint8), 'L')
    canvas.paste((255, 255, 255), (px(x0), px(y0)), layer)


def tex_metal(canvas, skin, bands):
    """New 3DS XL 的金属漆：细密竖向拉丝"""
    if not skin.get('metal'):
        return
    rng = np.random.default_rng(3)
    for (y0, y1) in bands:
        h, w = px(y1 - y0), px(W)
        col = rng.normal(0, 6.0, w).astype(np.float32)
        col = np.convolve(col, np.ones(7) / 7, mode='same')      # 拉丝要细而长
        arr = np.repeat(col[None, :], h, axis=0)
        arr = np.clip(arr * 2.6 + 128, 0, 255).astype(np.uint8)
        layer = Image.fromarray(arr, 'L')
        layer = layer.point(lambda v: int(min(255, abs(v - 128) * 0.55)))
        canvas.paste((255, 255, 255), (0, px(y0)), layer)


def tex_stars(canvas, skin, boxes):
    if not skin.get('stars'):
        return
    rng = np.random.default_rng(17)
    lay = Image.new('RGBA', (W2, H2), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    # 星云斑
    for _ in range(5):
        cx, cy = rng.uniform(0, W), rng.uniform(BOT_Y + 40, H)
        rr = rng.uniform(180, 460)
        col = rng.choice([(120, 90, 190), (80, 130, 210), (200, 140, 200)])
        d.ellipse([px(cx - rr), px(cy - rr * 0.55), px(cx + rr), px(cy + rr * 0.55)],
                  fill=tuple(col) + (46,))
    lay = lay.filter(ImageFilter.GaussianBlur(px(38)))
    canvas.paste(lay.convert('RGB'), (0, 0), lay.split()[-1])
    # 星点
    d2 = ImageDraw.Draw(canvas)
    for _ in range(520):
        sx, sy = rng.uniform(0, W), rng.uniform(BOT_Y, H)
        rr = float(rng.uniform(0.6, 2.6))
        al = int(rng.uniform(0.25, 1.0) * 255)
        d2.ellipse([px(sx - rr), px(sy - rr), px(sx + rr), px(sy + rr)],
                   fill=(255, 255, 255))
    # 上面那圈白点是纯色覆盖，改为低强度叠层
    # （见下方 stars_overlay 修正）


def stars_overlay(canvas, skin):
    if not skin.get('stars'):
        return
    rng = np.random.default_rng(17)
    lay = Image.new('L', (W2, H2), 0)
    d = ImageDraw.Draw(lay)
    for _ in range(520):
        sx, sy = rng.uniform(0, W), rng.uniform(BOT_Y, H)
        rr = float(rng.uniform(0.6, 2.6))
        al = int(rng.uniform(0.20, 1.0) * 165)
        d.ellipse([px(sx - rr), px(sy - rr), px(sx + rr), px(sy + rr)], fill=al)
    canvas.paste((255, 255, 255), (0, 0), lay)


def edge_shade(canvas, amt_side=0.30, amt_top=0.45, amt_bot=0.60, side_w=13):
    """机身边缘压暗，做出侧壁弧度的暗示"""
    lay = Image.new('L', (W2, H2), 0)
    d = ImageDraw.Draw(lay)
    for i in range(px(side_w)):
        a = int(255 * amt_side * (1 - i / px(side_w)) ** 1.8)
        d.line([(i, 0), (i, H2)], fill=a)
        d.line([(W2 - 1 - i, 0), (W2 - 1 - i, H2)], fill=a)
    for i in range(px(24)):
        a = int(255 * amt_top * (1 - i / px(24)) ** 1.6)
        d.line([(0, i), (W2, i)], fill=a)
    for i in range(px(30)):
        a = int(255 * amt_bot * (1 - i / px(30)) ** 1.7)
        d.line([(0, H2 - 1 - i), (W2, H2 - 1 - i)], fill=a)
    canvas.paste((0, 0, 0), (0, 0), lay)


def tex_grain(canvas, skin, sigma=4.0):
    """极轻微表面颗粒：去掉大面积色块的塑料感，也顺手压掉渐变色带"""
    noise = Image.effect_noise((W2, H2), sigma).convert('RGB')
    out = ImageChops.add(canvas, noise, scale=1.0, offset=-128)
    canvas.paste(out, (0, 0))


# ---------------------------------------------------------------- 凹陷
def edge_rim(canvas, skin, width=3, amt=0.40):
    """侧边倒角亮线：暗色皮肤全靠它撑形体"""
    lay = Image.new('L', (W2, H2), 0)
    d = ImageDraw.Draw(lay)
    n = px(width)
    for i in range(n):
        a = int(255 * amt * (1 - i / n) ** 1.2)
        d.line([(i, 0), (i, H2)], fill=a)
        d.line([(W2 - 1 - i, 0), (W2 - 1 - i, H2)], fill=a)
    canvas.paste(sd.lerp(skin['light'], (255, 255, 255), 0.5), (0, 0), lay)

def recess(canvas, box, shape='rrect', radius=12, depth=0.42, off=7,
           soft=9, top=0.58, bottom=0.20, pad=74, ring_amt=0.085):
    """在面板上挖一个凹槽（圆角矩形或圆），自带内阴影 + 底沿反光 + 外沿倒角"""
    x0, y0, x1, y1 = box
    X0, Y0 = max(0, px(x0 - pad)), max(0, px(y0 - pad))
    X1, Y1 = min(W2, px(x1 + pad)), min(H2, px(y1 + pad))
    if X1 <= X0 or Y1 <= Y0:
        return
    reg = canvas.crop((X0, Y0, X1, Y1))
    w, h = reg.size
    m = Image.new('L', (w, h), 0)
    d = ImageDraw.Draw(m)
    b = [px(x0) - X0, px(y0) - Y0, px(x1) - X0 - 1, px(y1) - Y0 - 1]
    if shape == 'circle':
        d.ellipse(b, fill=255)
    elif shape == 'cross':
        mx, my = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        arm = (b[2] - b[0]) * 0.43
        rr = (b[2] - b[0]) * 0.10
        d.rounded_rectangle([b[0], my - arm / 2, b[2], my + arm / 2], radius=rr, fill=255)
        d.rounded_rectangle([mx - arm / 2, b[1], mx + arm / 2, b[3]], radius=rr, fill=255)
    else:
        d.rounded_rectangle(b, radius=px(radius), fill=255)

    ma = np.asarray(m, dtype=np.float32) / 255.0
    arr = np.asarray(reg, dtype=np.float32)
    if arr.ndim == 2:
        arr = np.repeat(arr[..., None], 3, axis=2)
    arr = arr * (1.0 - ma[..., None] * depth)

    o = px(off)
    top_band = _blur(np.clip(ma - _shift(ma, o, int(o * 0.5)), 0, 1), px(soft) * 0.8)
    arr = arr * (1.0 - top_band[..., None] * top)
    bot_band = _blur(np.clip(ma - _shift(ma, -o, -int(o * 0.5)), 0, 1), px(soft) * 0.7)
    arr = arr * (1.0 - bot_band[..., None] * 0.05) + 255.0 * bot_band[..., None] * bottom

    dil = np.asarray(m.filter(ImageFilter.MaxFilter(px(4) * 2 + 1)), dtype=np.float32) / 255.0
    ring = _blur(np.clip(dil - ma, 0, 1), px(1.6))
    arr = arr + 255.0 * ring[..., None] * ring_amt

    canvas.paste(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)), (X0, Y0))


# ---------------------------------------------------------------- 细节零件
def bezel(canvas, skin, box, width=15, radius=10):
    """屏幕嵌槽：外圈深色边框"""
    x0, y0, x1, y1 = box
    d = ImageDraw.Draw(canvas)
    col = sd.lerp(skin['dark'], (0, 0, 0), 0.62)
    d.rounded_rectangle([px(x0) - px(width), px(y0) - px(width),
                         px(x1) + px(width) - 1, px(y1) + px(width) - 1],
                        radius=px(radius + width), fill=col)
    # 外沿倒角高光
    d.rounded_rectangle([px(x0) - px(width), px(y0) - px(width),
                         px(x1) + px(width) - 1, px(y1) + px(width) - 1],
                        radius=px(radius + width),
                        outline=sd.lerp(skin['light'], (255, 255, 255), 0.25), width=px(2))


def top_frame(canvas, skin, box, side=24, gap=7):
    """上屏窄边框：屏幕四周留一圈机身 + 一道极窄的黑色嵌缝。

    `side`   屏幕内容到机身侧边的距离（视觉上的“边框宽度”）
    `gap`    屏幕亮起前的那道黑缝（真机玻璃与外壳之间的接缝）

    注意别在屏幕外侧画整圈描边：上边会画到摄像头条上，出现一条横贯全宽的亮线。
    只用「缝内侧一道高光 + 外侧一道投影」来做出嵌进去的感觉。
    """
    x0, y0, x1, y1 = box
    d = ImageDraw.Draw(canvas)
    # 黑缝
    col = sd.lerp(skin['dark'], (0, 0, 0), 0.86)
    d.rounded_rectangle([px(x0) - px(gap), px(y0) - px(gap),
                         px(x1) + px(gap) - 1, px(y1) + px(gap) - 1],
                        radius=px(3), fill=col)
    # 缝外侧一圈接触阴影：让黑缝看起来是压进面板里，而不是贴上去的
    sh = Image.new('RGBA', (W2, H2), (0, 0, 0, 0))
    sd_ = ImageDraw.Draw(sh)
    sd_.rounded_rectangle([px(x0) - px(gap + 7), px(y0) - px(gap + 7),
                           px(x1) + px(gap + 6), px(y1) + px(gap + 6)],
                          radius=px(6), fill=(0, 0, 0, 120))
    sd_.rounded_rectangle([px(x0) - px(gap), px(y0) - px(gap),
                           px(x1) + px(gap) - 1, px(y1) + px(gap) - 1],
                          radius=px(3), fill=(0, 0, 0, 0))
    sh = sh.filter(ImageFilter.GaussianBlur(px(5)))
    canvas.paste(sh.convert('RGB'), (0, 0), sh.split()[-1])
    # 重新压一遍黑缝（上面的模糊会吃掉内侧）
    d.rounded_rectangle([px(x0) - px(gap), px(y0) - px(gap),
                         px(x1) + px(gap) - 1, px(y1) + px(gap) - 1],
                        radius=px(3), fill=col)
    # 缝内沿朝上的高光（光从上方来）。暗色机身本身太暗，这条线不加强就等于没有。
    amt = 0.62 if lum(skin['body']) < 90 else 0.45
    hi = sd.lerp(skin['light'], (255, 255, 255), amt)
    d.line([(px(x0 - gap), px(y0 + 1)), (px(x1 + gap), px(y0 + 1))],
           fill=hi, width=max(1, px(1.2)))
    d.line([(px(x0 + 1), px(y0 + gap)), (px(x0 + 1), px(y1 - gap))],
           fill=hi, width=max(1, px(1.0)))


def screen_cut(canvas, box, radius=9):
    x0, y0, x1, y1 = box
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle([px(x0), px(y0), px(x1) - 1, px(y1) - 1],
                        radius=px(radius), fill=(0, 0, 0))


def hinge_caps(canvas, skin):
    """转轴：真机 XL 是整根横贯的圆柱。下屏下移后，这条铰链第一次完整露出来。

    画法：竖向按「顶部高光 → 桶身渐暗 → 底部反光」做剖面，
    横向再叠一道两端暗、中间亮的受光，最后压一条接触阴影把它和下半机身分开。
    """
    top, bot = px(BOT_Y), px(BOT_Y + 62)
    n = bot - top
    xs = np.arange(W2, dtype=np.float32) / max(1, W2 - 1)
    hshade = (0.74 + 0.26 * np.clip(np.sin(np.pi * xs), 0, 1) ** 0.55)[None, :, None]

    # 桶身和机身同色、只暗一档；真正拉开层次的是顶沿镜面线 + 底部接触阴影
    base = np.array(sd.lerp(skin['dark'], skin['body'], 0.70), dtype=np.float32)
    deep = base * 0.72
    hi = np.array(sd.lerp(skin['light'], (255, 255, 255), 0.35), dtype=np.float32)

    arr = np.zeros((n, W2, 3), dtype=np.float32)
    for i in range(n):
        t = i / max(1, n - 1)
        if t < 0.10:                       # 顶沿镜面高光
            c = sd.lerp(hi, base, (t / 0.10) ** 0.5)
        elif t < 0.55:                     # 受光面，缓暗
            c = sd.lerp(base, base * 0.94, (t - 0.10) / 0.45)
        elif t < 0.86:                     # 背光面转深
            c = sd.lerp(base * 0.94, deep, (t - 0.55) / 0.31)
        else:                              # 底沿反光
            c = sd.lerp(deep, hi, ((t - 0.86) / 0.14) ** 1.4 * 0.5)
        arr[i] = np.array(c, dtype=np.float32)
    arr = arr * hshade
    canvas.paste(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)), (0, top))

    # 接触阴影：转轴压在下半机身上的暗带，靠它把上下两块壳体分开
    s0, s1 = bot, bot + px(13)
    m = np.linspace(0.62, 0.0, s1 - s0, dtype=np.float32)[:, None, None]
    reg = np.asarray(canvas.crop((0, s0, W2, s1)), dtype=np.float32)
    canvas.paste(Image.fromarray(np.clip(reg * (1 - m), 0, 255).astype(np.uint8)), (0, s0))


def shell_lip(canvas, skin, seam=True):
    """上盖下沿与屏幕的接缝：一道渐暗 + 一条倒角亮线。

    上屏缩进后（TOP_INSET>0），屏幕不再顶到 TOP_H，这道线就会横穿边框区域、
    看起来像把上盖切开——真机上摄像头条与屏框是同一块面，所以这时不画。
    """
    if not seam:
        return
    lay = Image.new('L', (W2, H2), 0)
    d = ImageDraw.Draw(lay)
    n = px(16)
    for i in range(n):
        d.line([(0, px(TOP_H) - n + i), (W2, px(TOP_H) - n + i)],
               fill=int(215 * (i / max(1, n - 1)) ** 1.6))
    canvas.paste((0, 0, 0), (0, 0), lay)
    d2 = ImageDraw.Draw(canvas)
    d2.line([(0, px(TOP_H) - n - 1), (W2, px(TOP_H) - n - 1)],
            fill=sd.lerp(skin['light'], (255, 255, 255), 0.40), width=max(1, px(1.4)))


def speaker_holes(canvas, skin, x, ytop, ybot, n=3):
    d = ImageDraw.Draw(canvas)
    hole = sd.lerp(skin['dark'], (0, 0, 0), 0.72)
    hi = sd.lerp(skin['light'], (255, 255, 255), 0.30)
    span = (ybot - ytop)
    for i in range(n):
        cy = ytop + span * (i + 0.5) / n
        d.rounded_rectangle([px(x - 3.4), px(cy - 17), px(x + 3.4), px(cy + 17)],
                            radius=px(3.4), fill=hole)
        d.rounded_rectangle([px(x - 3.4), px(cy - 17), px(x + 3.4), px(cy + 17)],
                            radius=px(3.4), outline=hi, width=max(1, px(0.9)))


def camera_bar(canvas, skin):
    """上屏上方的摄像头条：双摄 + 3D 灯 + 丝印"""
    d = ImageDraw.Draw(canvas)
    ring = sd.lerp(skin['light'], (255, 255, 255), 0.35)
    for cx in (736, 1092):
        cy = 100
        d.ellipse([px(cx - 17), px(cy - 17), px(cx + 17), px(cy + 17)], fill=(0, 0, 0))
        d.ellipse([px(cx - 17), px(cy - 17), px(cx + 17), px(cy + 17)],
                  outline=ring, width=px(2.4))
        d.ellipse([px(cx - 9), px(cy - 9), px(cx + 9), px(cy + 9)],
                  fill=(0x10, 0x12, 0x1A))
        d.ellipse([px(cx - 5), px(cy - 6), px(cx + 2), px(cy + 1)],
                  fill=(0x2C, 0x3A, 0x52))
    # 3D 指示灯
    lay = Image.new('RGBA', (W2, H2), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)
    ld.ellipse([px(914 - 16), px(100 - 16), px(914 + 16), px(100 + 16)],
               fill=(120, 255, 180, 46))
    lay = lay.filter(ImageFilter.GaussianBlur(px(10)))
    canvas.paste(lay.convert('RGB'), (0, 0), lay.split()[-1])
    d.ellipse([px(914 - 6), px(100 - 6), px(914 + 6), px(100 + 6)],
              fill=(150, 255, 195))
    f = ImageFont.truetype(FONT_B, px(24))
    d.text((px(946), px(86)), '3D', font=f, fill=sd.lerp(skin['letter'], skin['body'], 0.55))


def silk(canvas, skin, text, cx, cy, size=40, alpha=0.30):
    lay = Image.new('RGBA', (W2, H2), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    f = ImageFont.truetype(FONT_B, px(size))
    bb = d.textbbox((0, 0), text, font=f)
    col = sd.lerp(skin['light'], (255, 255, 255), 0.55)
    d.text((px(cx) - (bb[2] - bb[0]) / 2 - bb[0], px(cy) - (bb[3] - bb[1]) / 2 - bb[1]),
           text, font=f, fill=col + (int(255 * alpha),))
    canvas.paste(lay.convert('RGB'), (0, 0), lay.split()[-1])


def grille(canvas, skin, cx, cy, n=9, gap=17, r=4.2):
    """下屏正下方的扬声器格栅（左右侧空间被按键占满，只能放这一条）"""
    d = ImageDraw.Draw(canvas)
    hole = sd.lerp(skin['dark'], (0, 0, 0), 0.78)
    hi = sd.lerp(skin['light'], (255, 255, 255), 0.26)
    x0 = cx - (n - 1) * gap / 2
    for i in range(n):
        x = x0 + i * gap
        d.ellipse([px(x - r), px(cy - r), px(x + r), px(cy + r)], fill=hole)
        d.arc([px(x - r), px(cy - r), px(x + r), px(cy + r)], 190, 350, fill=hi, width=max(1, px(0.9)))


# ---------------------------------------------------------------- 主渲染
def lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def render_panel(key):
    sk = sd.SKINS[key]
    light, body, dark = sk['light'], sk['body'], sk['dark']
    dark_body = lum(body) < 90          # 暗色皮肤：凹槽靠"亮边"读出来，不靠压暗
    canvas = Image.new('RGB', (W2, H2), (0, 0, 0))

    # 上盖（摄像头条 + 上屏所在的这块板）：同一块塑料，必须一段渐变画完。
    # 分成两段会在 196 处留下一条亮度对不上的接缝，缩进后正好横穿边框。
    canvas.paste(sd.vertical_gradient(px(W), px(BOT_Y), light, body,
                                      sd.lerp(body, dark, 0.42), 0.24).convert('RGB'),
                 (0, 0))
    # 下半机身
    canvas.paste(sd.vertical_gradient(px(W), px(H - BOT_Y), light, body, dark,
                                      0.20).convert('RGB'), (0, px(BOT_Y)))

    # 暗色皮肤整体抬一档，机身与键帽之间才有明度差；极亮皮肤反过来压一点防过曝
    if dark_body:
        lighten(canvas, Image.new('L', (W2, H2), 255), 0.055, (255, 255, 255))
    elif lum(body) >= 200:
        darken(canvas, Image.new('L', (W2, H2), 255), 0.055)

    tex_gloss(canvas, sk, [(0, BOT_Y), (BOT_Y, H)])
    tex_metal(canvas, sk, [(0, BOT_Y), (BOT_Y, H)])
    tex_bloom(canvas, sk, (0, BOT_Y, W, 2380), 0.16 if dark_body else 0.085)
    tex_bloom(canvas, sk, (0, 0, W, BOT_Y), 0.10 if dark_body else 0.05)
    stars_overlay(canvas, sk)
    edge_shade(canvas, amt_side=0.42 if dark_body else 0.30)

    tex_grain(canvas, sk)
    edge_rim(canvas, sk, amt=0.42 if dark_body else 0.20)

    # 屏幕嵌槽
    bezel(canvas, sk, SCR_BOT, width=15, radius=10)
    screen_cut(canvas, SCR_BOT, radius=9)
    if TOP_INSET > 0:
        top_frame(canvas, sk, SCR_TOP, side=TOP_INSET, gap=max(4, TOP_INSET // 4))
    screen_cut(canvas, SCR_TOP, radius=0)

    # 转轴端盖
    hinge_caps(canvas, sk)

    def well(box, shape='rrect', radius=12, depth=0.42, off=7, soft=9):
        if dark_body:
            recess(canvas, box, shape, radius=radius, depth=depth * 0.62, off=off,
                   soft=soft, top=0.66, bottom=0.34, ring_amt=0.20)
        else:
            recess(canvas, box, shape, radius=radius, depth=depth, off=off,
                   soft=soft, top=0.58, bottom=0.20, ring_amt=0.085)

    # 按键凹井
    for k in ('l', 'r'):
        (cx, cy), (bw, bh) = BTN[k]
        well((cx - bw / 2 - 11, cy - bh / 2 - 11, cx + bw / 2 + 11, cy + bh / 2 + 11),
             'rrect', radius=42, depth=0.38, off=6, soft=8)
    (cx, cy), (bw, bh) = BTN['dpad']
    well((cx - 183, cy - 183, cx + 183, cy + 183), 'cross', depth=0.38, off=8, soft=15)
    # 滑杆是凸起件：只做一圈浅平台 + 落影，不挖深井（侵入屏幕时更自然）
    (cx, cy), _ = BTN['stick']
    well((cx - 144, cy - 144, cx + 144, cy + 144), 'circle',
         depth=0.26, off=7, soft=16)
    for k in ('x', 'y', 'a', 'b'):
        (cx, cy), (bw, bh) = BTN[k]
        rw = bw / 2 + 16          # 凹槽跟着键径走，缩键时不会留下大一圈的坑
        well((cx - rw, cy - rw, cx + rw, cy + rw), 'circle', depth=0.20, off=5, soft=8)
    (cx, cy), (bw, bh) = BTN['home']
    well((cx - 77, cy - 77, cx + 77, cy + 77), 'circle', depth=0.32, off=5, soft=7)
    for k in ('select', 'start'):
        (cx, cy), (bw, bh) = BTN[k]
        well((cx - bw / 2 - 10, cy - bh / 2 - 9, cx + bw / 2 + 10, cy + bh / 2 + 9),
             'rrect', radius=44, depth=0.32, off=5, soft=7)

    # 零件
    shell_lip(canvas, sk, seam=(TOP_INSET <= 0))
    camera_bar(canvas, sk)
    grille(canvas, sk, W / 2, 2204, 11, gap=19, r=5.0)
    silk(canvas, sk, 'Fun in Hope', W / 2, 2528, size=44,
         alpha=0.50 if dark_body else 0.42)
    silk(canvas, sk, sk['en'].upper(), W / 2, 2568, size=18,
         alpha=0.28 if dark_body else 0.20)

    return canvas.resize((W, H), Image.LANCZOS)


def paste_buttons(img, key):
    sk = sd.SKINS[key]
    lb = lum(sk['body'])
    # 浅色机身：键帽是哑光同色，比亮面机身低一档才读得出；越白要压得越多
    f = 0.22 if lb >= 200 else (0.16 if lb >= 90 else 0.08)
    if f:
        sk = dict(sk)
        sk['body'] = sd.lerp(sk['body'], (0, 0, 0), f)
        sk['light'] = sd.lerp(sk['light'], (0, 0, 0), f * 0.6)
        sk['dark'] = sd.lerp(sk['dark'], (0, 0, 0), f)
    img = img.convert('RGBA')

    def put(im, cx, cy):
        img.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

    put(sd.pill(sk, 'L', *BTN['l'][1]), *BTN['l'][0])
    put(sd.pill(sk, 'R', *BTN['r'][1]), *BTN['r'][0])
    put(sd.dpad(sk, 0, BTN['dpad'][1][0]), *BTN['dpad'][0])
    put(sd.stick(sk, False, 281), *BTN['stick'][0])
    for k in ('x', 'y', 'a', 'b'):
        put(sd.face_button(k, sk, False, BTN[k][1][0]), *BTN[k][0])
    put(sd.home_button(sk, BTN['home'][1][0]), *BTN['home'][0])
    put(sd.pill(sk, 'SELECT', *BTN['select'][1], round_r=0.5), *BTN['select'][0])
    put(sd.pill(sk, 'START', *BTN['start'][1], round_r=0.5), *BTN['start'][0])
    return img.convert('RGB')


def paste_game(img, frame='../diag/back_v13.png'):
    if not os.path.exists(frame):
        print('!! frame missing:', frame)
        return img
    src = Image.open(frame).convert('RGB')
    img = img.copy()
    # 截图里的上屏是满宽的，缩窄后要等比铺到新框，不能直接裁
    top = src.crop(SCR_TOP_FULL)
    want = (SCR_TOP[2] - SCR_TOP[0], SCR_TOP[3] - SCR_TOP[1])
    if top.size != want:
        top = top.resize(want, Image.LANCZOS)
    img.paste(top, (SCR_TOP[0], SCR_TOP[1]))
    # 截图里的下屏还是旧位置，先按旧框裁下来，再等比铺到新框
    bot = src.crop(SRC_SCR_BOT)
    if bot.size != (SCR_BOT[2] - SCR_BOT[0], SCR_BOT[3] - SCR_BOT[1]):
        bot = bot.resize((SCR_BOT[2] - SCR_BOT[0], SCR_BOT[3] - SCR_BOT[1]), Image.LANCZOS)
    img.paste(bot, (SCR_BOT[0], SCR_BOT[1]))
    return img


def render_full(key, game=True):
    """面板 → 游戏画面 → 按键（真机上按钮 overlay 永远在最上层，别搞反）"""
    panel = render_panel(key)
    if game:
        panel = paste_game(panel)
    return paste_buttons(panel, key)


if __name__ == '__main__':
    os.makedirs('skin_preview', exist_ok=True)
    for k in sd.SKINS:
        p = render_panel(k)
        p.save('skin_preview/bg_%s.jpg' % k, quality=92)
        f = render_full(k, game=True)
        f.save('skin_preview/panel_%s.png' % k)
        print('ok', k, f.size)
