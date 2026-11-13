"""按 3DS 真机配色与材质渲染虚拟按键皮肤（设计稿预览用）。"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1828, 2584
PAD = 12          # 外阴影留白
SS = 3            # 超采样倍数

FONT_BOLD = 'C:/Windows/Fonts/arialbd.ttf'
FONT_REG = 'C:/Windows/Fonts/arial.ttf'


# ---------------------------------------------------------------- 调色板
SKINS = {
    'cosmo': dict(
        cn='宇宙黑', en='Cosmo Black', year='2011 · 初代 3DS 首发',
        body=(0x2A, 0x2A, 0x33), light=(0x46, 0x47, 0x54), dark=(0x14, 0x14, 0x1A),
        letter=(0xF4, 0xF4, 0xF6), letter_mode='white',
        stick=(0x30, 0x32, 0x39), stick_rim=(0x53, 0x56, 0x60),
        bg=(0x0B, 0x0B, 0x10), gloss=0.55, metal=False,
    ),
    'aqua': dict(
        cn='水波蓝', en='Aqua Blue', year='2011 · 初代 3DS 首发',
        body=(0x2B, 0xB0, 0xC6), light=(0x6F, 0xDA, 0xE6), dark=(0x14, 0x74, 0x88),
        letter=(0xF6, 0xFD, 0xFF), letter_mode='white',
        stick=(0x33, 0x36, 0x3B), stick_rim=(0x57, 0x5B, 0x63),
        bg=(0x06, 0x16, 0x1A), gloss=0.62, metal=False,
    ),
    'flare_red': dict(
        cn='火焰红', en='Flare Red', year='2011 · 初代 3DS',
        body=(0xB0, 0x25, 0x2E), light=(0xE2, 0x4C, 0x51), dark=(0x66, 0x0E, 0x16),
        letter=(0xF8, 0xF2, 0xEE), letter_mode='white',
        stick=(0x33, 0x33, 0x38), stick_rim=(0x57, 0x57, 0x5E),
        bg=(0x12, 0x05, 0x07), gloss=0.62, metal=False,
    ),
    'ice_white': dict(
        cn='冰白', en='Ice White', year='2011 · 初代 3DS',
        body=(0xE8, 0xE5, 0xDC), light=(0xFC, 0xFB, 0xF7), dark=(0xB6, 0xB0, 0xA3),
        letter=(0x4A, 0x4A, 0x52), letter_mode='dark',
        stick=(0x4A, 0x4A, 0x50), stick_rim=(0x74, 0x74, 0x7C),
        bg=(0x14, 0x13, 0x11), gloss=0.55, metal=False,
    ),
    'coral_pink': dict(
        cn='珊瑚粉', en='Coral Pink', year='2011 · 初代 3DS',
        body=(0xEE, 0x9C, 0xAE), light=(0xFF, 0xC9, 0xD5), dark=(0xB8, 0x64, 0x79),
        letter=(0xFD, 0xF6, 0xF8), letter_mode='white',
        stick=(0x3A, 0x34, 0x38), stick_rim=(0x5E, 0x55, 0x5A),
        bg=(0x18, 0x0A, 0x0D), gloss=0.60, metal=False,
    ),
    'metallic_blue': dict(
        cn='金属蓝', en='Metallic Blue', year='2014 · New 3DS XL 首发',
        body=(0x1E, 0x4E, 0x9C), light=(0x52, 0x88, 0xDA), dark=(0x0E, 0x28, 0x5C),
        letter=(0xF2, 0xF4, 0xF8), letter_mode='color',
        stick=(0x2F, 0x33, 0x3A), stick_rim=(0x54, 0x59, 0x62),
        bg=(0x05, 0x0A, 0x18), gloss=0.40, metal=True,
    ),
    'snes': dict(
        cn='SNES 版', en='SNES Edition', year='2017 · New 3DS XL 限定',
        body=(0x5A, 0x50, 0x74), light=(0x88, 0x7C, 0xA6), dark=(0x2E, 0x27, 0x40),
        letter=(0xF6, 0xF3, 0xFA), letter_mode='color',
        stick=(0x38, 0x34, 0x44), stick_rim=(0x5C, 0x56, 0x6C),
        bg=(0x0A, 0x08, 0x10), gloss=0.42, metal=True,
    ),
    'galaxy': dict(
        cn='星云紫', en='New Galaxy Style', year='2016 · New 3DS XL 限定',
        body=(0x22, 0x18, 0x3A), light=(0x46, 0x34, 0x6C), dark=(0x0D, 0x08, 0x1C),
        letter=(0xF2, 0xF0, 0xFA), letter_mode='color',
        stick=(0x2B, 0x2A, 0x36), stick_rim=(0x4E, 0x4B, 0x5E),
        bg=(0x08, 0x05, 0x14), gloss=0.45, metal=True, stars=True,
    ),
}

# New 3DS 系列的彩色字母
LETTER_COLOR = {
    'a': (0xEE, 0x4B, 0x3E),
    'b': (0xF5, 0xC8, 0x1C),
    'x': (0x79, 0xC6, 0xFF),
    'y': (0x54, 0xC0, 0x4A),
}


def lerp(c1, c2, t):
    return tuple(int(round(c1[i] + (c2[i] - c1[i]) * t)) for i in range(3))


def vertical_gradient(w, h, top, mid, bottom, split=0.55):
    """上亮-中体色-下暗的塑料渐变"""
    arr = np.zeros((h, w, 4), dtype=np.uint8)
    ys = np.arange(h, dtype=np.float32) / max(1, h - 1)
    for y in range(h):
        t = ys[y]
        c = lerp(top, mid, t / split) if t < split else lerp(mid, bottom, (t - split) / (1 - split))
        arr[y, :, 0:3] = c
        arr[y, :, 3] = 255
    return Image.fromarray(arr, 'RGBA')


def shape_mask(size, kind, arm_ratio=0.36, radius_ratio=0.10):
    """返回 alpha 掩膜：circle / cross / pill"""
    m = Image.new('L', (size, size), 0)
    d = ImageDraw.Draw(m)
    if kind == 'circle':
        d.ellipse([0, 0, size - 1, size - 1], fill=255)
    elif kind == 'cross':
        w = int(size * arm_ratio)
        c = size // 2
        r = int(size * radius_ratio)
        # 横臂与竖臂并集，用两个圆角矩形
        d.rounded_rectangle([0, c - w // 2, size - 1, c + w // 2], radius=r, fill=255)
        d.rounded_rectangle([c - w // 2, 0, c + w // 2, size - 1], radius=r, fill=255)
    return m


def plastic(size, skin, pressed=False, kind='circle', arm_ratio=0.36):
    """画一颗塑料键帽（不含字母）"""
    S = size * SS
    m = shape_mask(S, kind, arm_ratio)
    body, light, dark = skin['body'], skin['light'], skin['dark']
    if pressed:
        body, light = lerp(body, (0, 0, 0), 0.12), lerp(light, (0, 0, 0), 0.10)
        dark = lerp(dark, (0, 0, 0), 0.10)

    grad = vertical_gradient(S, S, light, body, dark, split=0.48)
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    img.paste(grad, (0, 0), m)

    # 金属细纹（New 3DS XL 的拉丝质感）
    if skin['metal']:
        arr = np.array(img).astype(np.int16)
        rng = np.random.default_rng(7)
        rows = rng.normal(0, 3.0, S).astype(np.int16)
        arr[:, :, 0:3] = np.clip(arr[:, :, 0:3] + rows[:, None, None], 0, 255)
        arr[:, :, 3] = np.array(img)[:, :, 3]
        img = Image.fromarray(arr.astype(np.uint8), 'RGBA')

    # 外轮廓：稍深的边
    edge = m.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(SS * 0.6))
    edge_col = Image.new('RGBA', (S, S), lerp(dark, (0, 0, 0), 0.45) + (0,))
    edge_col.putalpha(edge.point(lambda v: int(v * 0.85)))
    img.alpha_composite(edge_col)

    # 高光：左上弧（玻璃感）
    hl = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hl)
    g = skin['gloss']
    if kind == 'circle':
        inset = S * 0.10
        hd.arc([inset, inset, S - inset, S - inset], 195, 330,
               fill=(255, 255, 255, int(120 * g)), width=int(SS * 1.6))
        # 顶部大面积柔光
        soft = Image.new('L', (S, S), 0)
        ImageDraw.Draw(soft).ellipse([S * 0.16, S * 0.04, S * 0.84, S * 0.52], fill=255)
        soft = soft.filter(ImageFilter.GaussianBlur(S * 0.10))
        soft = soft.point(lambda v: int(v * 0.30 * g))
        hl.paste(Image.new('RGBA', (S, S), (255, 255, 255, 255)), (0, 0), soft)
    else:
        hd.rounded_rectangle([S * 0.10, S * 0.10, S * 0.90, S * 0.90], radius=int(S * 0.06),
                             outline=(255, 255, 255, int(70 * g)), width=int(SS * 1.4))
    img.alpha_composite(Image.composite(hl, Image.new('RGBA', (S, S), (0, 0, 0, 0)), m))

    # 底部内阴影
    sh = Image.new('L', (S, S), 0)
    ImageDraw.Draw(sh).ellipse([S * 0.06, S * 0.44, S * 0.94, S * 1.02], fill=255)
    sh = sh.filter(ImageFilter.GaussianBlur(S * 0.09)).point(lambda v: int(v * 0.35))
    sh = Image.composite(sh, Image.new('L', (S, S), 0), m)
    img.alpha_composite(Image.merge('RGBA', [
        Image.new('L', (S, S), 0), Image.new('L', (S, S), 0), Image.new('L', (S, S), 0), sh]))

    # 外投影，保证压在白屏上也有轮廓
    shadow = m.filter(ImageFilter.GaussianBlur(S * 0.045))
    sd = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    sd.paste(Image.new('RGBA', (S, S), (0, 0, 0, 150)), (0, 0), shadow.point(lambda v: int(v * 0.55)))
    out = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    out.alpha_composite(sd, (0, int(S * 0.012)))
    out.alpha_composite(img)

    # 边缘轮廓光：让暗色皮肤在纯黑背景上也能看出形体
    er = m.filter(ImageFilter.MinFilter(int(SS * 2) + 1))
    rim = Image.new('L', (S, S), 0)
    rim.paste(m, (0, 0))
    rim = Image.fromarray(np.clip(np.array(rim, dtype=np.int16) - np.array(er, dtype=np.int16), 0, 255).astype(np.uint8))
    rim = rim.point(lambda v: int(v * 0.55))
    rim_col = Image.new('RGBA', (S, S), lerp(light, (255, 255, 255), 0.45) + (0,))
    rim_col.putalpha(rim)
    out.alpha_composite(rim_col)
    return out.resize((size, size), Image.LANCZOS)


def put_letter(img, ch, color, stroke=0):
    S = img.size[0]
    f = ImageFont.truetype(FONT_BOLD, int(S * 0.40))
    layer = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    bb = d.textbbox((0, 0), ch, font=f)
    tx = (S - (bb[2] - bb[0])) / 2 - bb[0]
    ty = (S - (bb[3] - bb[1])) / 2 - bb[1]
    # 阴刻：右下 1px 深色
    d.text((tx + S * 0.004, ty + S * 0.005), ch, font=f, fill=(0, 0, 0, 130))
    d.text((tx, ty), ch, font=f, fill=color + (255,),
           stroke_width=stroke, stroke_fill=(0, 0, 0, 170))
    img.alpha_composite(layer)
    return img


def face_button(ch, skin, pressed=False, size=300):
    cap = plastic(size, skin, pressed, 'circle')
    colored = skin['letter_mode'] == 'color' and ch.lower() in LETTER_COLOR
    if colored:
        col = LETTER_COLOR[ch.lower()]
    else:
        col = skin['letter']
    return put_letter(cap, ch.upper(), col, stroke=int(size * 0.022) if colored else 0)


def dpad(skin, pressed=0, size=400):
    """pressed: 0 无 / 1 单方向 / 2 对角"""
    cap = plastic(size, skin, pressed > 0, 'cross', arm_ratio=0.38)
    S = cap.size[0]
    d = ImageDraw.Draw(cap)
    c = S / 2
    lc = skin['letter']          # 箭头跟字母同色，白机身上才不会白得看不见
    # 中心圆凹槽
    r = S * 0.115
    d.ellipse([c - r, c - r, c + r, c + r], outline=lc + (46,), width=max(2, int(S * 0.010)))
    # 四个方向的浅浮雕箭头
    a = S * 0.055
    off = S * 0.300
    base = [(0.0, -a), (-a * 0.85, a * 0.62), (a * 0.85, a * 0.62)]
    for ang in (0, 90, 180, 270):
        rad = math.radians(ang)
        ca, sa = math.cos(rad), math.sin(rad)
        cx0 = c + (0 if ang in (0, 180) else (off if ang == 90 else -off))
        cy0 = c + (-off if ang == 0 else (off if ang == 180 else 0))
        pts = []
        for (bx, by) in base:
            pts.append((cx0 + bx * ca - by * sa, cy0 + bx * sa + by * ca))
        d.polygon(pts, fill=lc + (128 if pressed else 68,))
    return cap


def stick(skin, pressed=False, size=340):
    S = size
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    base = Image.new('RGBA', (S, S), skin['stick'] + (255,))
    m = Image.new('L', (S, S), 0)
    ImageDraw.Draw(m).ellipse([S * 0.02, S * 0.02, S * 0.98, S * 0.98], fill=255)
    img.paste(base, (0, 0), m)
    d = ImageDraw.Draw(img)
    # 同心橡胶纹
    for i, k in enumerate((0.82, 0.66, 0.50)):
        r = S * 0.5 * k
        d.ellipse([S / 2 - r, S / 2 - r, S / 2 + r, S / 2 + r],
                  outline=lerp(skin['stick'], (255, 255, 255), 0.10) + (90 - i * 18,),
                  width=max(1, int(S * 0.006)))
    # 顶部高光
    hl = Image.new('L', (S, S), 0)
    ImageDraw.Draw(hl).ellipse([S * 0.22, S * 0.10, S * 0.78, S * 0.46], fill=255)
    hl = hl.filter(ImageFilter.GaussianBlur(S * 0.06)).point(lambda v: int(v * (0.20 if pressed else 0.34)))
    img.alpha_composite(Image.merge('RGBA', [Image.new('L', (S, S), 255)] * 3 + [hl]))
    # 外圈
    d.ellipse([S * 0.02, S * 0.02, S * 0.98, S * 0.98],
              outline=skin['stick_rim'] + (200,), width=max(2, int(S * 0.012)))
    # 投影
    sh = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    sm = Image.new('L', (S, S), 0)
    ImageDraw.Draw(sm).ellipse([S * 0.04, S * 0.04, S * 0.96, S * 0.96], fill=255)
    sh.paste(Image.new('RGBA', (S, S), (0, 0, 0, 130)), (0, 0),
             sm.filter(ImageFilter.GaussianBlur(S * 0.05)).point(lambda v: int(v * 0.6)))
    out = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    out.alpha_composite(sh)
    out.alpha_composite(img)
    # 轮廓光：深色机身上靠它读得出球形
    er = m.filter(ImageFilter.MinFilter(9))
    rim = np.clip(np.array(m, dtype=np.int16) - np.array(er, dtype=np.int16), 0, 255).astype(np.uint8)
    rim_l = Image.fromarray(rim, 'L').point(lambda v: int(v * 0.55))
    out.paste(Image.new('RGBA', (S, S), lerp(skin['stick_rim'], (255, 255, 255), 0.45) + (255,)),
              (0, 0), rim_l)
    return out


def pill(skin, label, w, h, pressed=False, round_r=None):
    S_w, S_h = w * SS, h * SS
    m = Image.new('L', (S_w, S_h), 0)
    r = int(min(S_h, S_w) * (round_r if round_r else 0.42))
    ImageDraw.Draw(m).rounded_rectangle([0, 0, S_w - 1, S_h - 1], radius=r, fill=255)
    grad = vertical_gradient(S_w, S_h, skin['light'], skin['body'], skin['dark'], 0.5)
    img = Image.new('RGBA', (S_w, S_h), (0, 0, 0, 0))
    img.paste(grad, (0, 0), m)
    # 轮廓
    edge = ImageDraw.Draw(img)
    edge.rounded_rectangle([0, 0, S_w - 1, S_h - 1], radius=r,
                           outline=lerp(skin['dark'], (0, 0, 0), 0.35) + (200,), width=max(2, int(SS * 1.2)))
    # 顶部高光条
    hl = Image.new('L', (S_w, S_h), 0)
    ImageDraw.Draw(hl).rounded_rectangle([S_w * 0.06, S_h * 0.10, S_w * 0.94, S_h * 0.46],
                                        radius=int(r * 0.8), fill=255)
    hl = hl.filter(ImageFilter.GaussianBlur(SS * 3)).point(lambda v: int(v * 0.22))
    img.alpha_composite(Image.merge('RGBA', [Image.new('L', (S_w, S_h), 255)] * 3 + [hl]))
    # 文字（自动收缩到 84% 宽度内）
    if label:
        d = ImageDraw.Draw(img)
        size_px = int(S_h * 0.56)
        f = ImageFont.truetype(FONT_BOLD, size_px)
        while size_px > 8:
            f = ImageFont.truetype(FONT_BOLD, size_px)
            bb = d.textbbox((0, 0), label, font=f)
            if (bb[2] - bb[0]) <= S_w * 0.84:
                break
            size_px -= 2
        bb = d.textbbox((0, 0), label, font=f)
        d.text(((S_w - (bb[2] - bb[0])) / 2 - bb[0], (S_h - (bb[3] - bb[1])) / 2 - bb[1]),
               label, font=f, fill=skin['letter'] + (238,))
    sh = Image.new('RGBA', (S_w, S_h), (0, 0, 0, 0))
    sh.paste(Image.new('RGBA', (S_w, S_h), (0, 0, 0, 120)), (0, 0),
             m.filter(ImageFilter.GaussianBlur(SS * 3)).point(lambda v: int(v * 0.5)))
    out = Image.new('RGBA', (S_w, S_h), (0, 0, 0, 0))
    out.alpha_composite(sh)
    out.alpha_composite(img)
    er = m.filter(ImageFilter.MinFilter(int(SS * 2) + 1))
    rim = Image.fromarray(np.clip(np.array(m, dtype=np.int16) - np.array(er, dtype=np.int16),
                                  0, 255).astype(np.uint8))
    rim_col = Image.new('RGBA', (S_w, S_h), lerp(skin['light'], (255, 255, 255), 0.45) + (0,))
    rim_col.putalpha(rim.point(lambda v: int(v * 0.50)))
    out.alpha_composite(rim_col)
    return out.resize((w, h), Image.LANCZOS)


def home_button(skin, size=130, pressed=False):
    cap = plastic(size, skin, pressed, 'circle')
    S = cap.size[0]
    d = ImageDraw.Draw(cap)
    c = S / 2
    r = S * 0.215
    w = max(2, int(S * 0.026))
    col = skin['letter'] + (225,)
    # 屋顶
    d.line([(c - r, c - r * 0.05), (c, c - r), (c + r, c - r * 0.05)], fill=col, width=w, joint='curve')
    # 屋身
    d.line([(c - r * 0.74, c - r * 0.05), (c - r * 0.74, c + r * 0.82)], fill=col, width=w)
    d.line([(c + r * 0.74, c - r * 0.05), (c + r * 0.74, c + r * 0.82)], fill=col, width=w)
    d.line([(c - r * 0.74, c + r * 0.82), (c + r * 0.74, c + r * 0.82)], fill=col, width=w)
    return cap


# ---------------------------------------------------------------- 合成
def base_plate(frame='diag/back_v13.png'):
    """取出干净的底图：两屏保留，其余全黑"""
    src = Image.open(frame).convert('RGB')
    plate = Image.new('RGB', (W, H), (0, 0, 0))
    plate.paste(src.crop((0, 196, W, 1292)), (0, 196))
    plate.paste(src.crop((339, 1292, 1488, 2153)), (339, 1292))
    return plate


def render_skin(skin_key, backdrop=False, frame='diag/back_v13.png'):
    sk = SKINS[skin_key]
    plate = base_plate(frame).convert('RGBA')
    if backdrop:
        bgm = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        # 压暗一档：做成"背光面"的机身，避免按键与背景同色糊在一起
        c_top = lerp(sk['light'], (0, 0, 0), 0.62)
        c_mid = lerp(sk['body'], (0, 0, 0), 0.58)
        c_bot = lerp(sk['dark'], (0, 0, 0), 0.40)
        g = vertical_gradient(W, H, c_top, c_mid, c_bot, 0.35)
        bgm.paste(g, (0, 0))
        # 只保留两屏之外的区域
        keep = Image.new('L', (W, H), 255)
        kd = ImageDraw.Draw(keep)
        kd.rectangle([0, 196, W, 1292], fill=0)
        kd.rectangle([339, 1292, 1488, 2153], fill=0)
        bgm.putalpha(keep.point(lambda v: int(v * 0.92)))
        plate.alpha_composite(bgm)
        if sk.get('stars'):
            rng = np.random.default_rng(11)
            st = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            d2 = ImageDraw.Draw(st)
            for _ in range(420):
                sx, sy = rng.integers(0, W), rng.integers(0, H)
                if 196 <= sy <= 1292 or (1292 <= sy <= 2153 and 339 <= sx <= 1488):
                    continue
                rr = float(rng.uniform(0.8, 3.0))
                al = int(rng.uniform(40, 165))
                d2.ellipse([sx - rr, sy - rr, sx + rr, sy + rr], fill=(255, 255, 255, al))
            plate.alpha_composite(st)

    def put(im, cx, cy):
        plate.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

    put(pill(sk, 'L', 233, 101), 174, 1395)
    put(pill(sk, 'R', 233, 101), 1654, 1395)
    put(dpad(sk, 0, 330), 174, 1796)
    put(stick(sk, False, 281), 283, 2196)
    put(face_button('x', sk, False, 152), 1627, 1680)
    put(face_button('y', sk, False, 152), 1508, 1796)
    put(face_button('a', sk, False, 152), 1746, 1796)
    put(face_button('b', sk, False, 152), 1627, 1912)
    put(pill(sk, 'SELECT', 153, 78, round_r=0.5), 704, 2403)
    put(pill(sk, 'START', 153, 78, round_r=0.5), 1124, 2403)
    put(home_button(sk, 129), 914, 2403)
    return plate.convert('RGB')


if __name__ == '__main__':
    import os
    os.makedirs('skin_preview', exist_ok=True)
    for k in SKINS:
        for bd in (False, True):
            img = render_skin(k, backdrop=bd)
            name = 'skin_preview/%s%s.png' % (k, '_bg' if bd else '')
            img.save(name, quality=93)
            print('saved', name, img.size)
