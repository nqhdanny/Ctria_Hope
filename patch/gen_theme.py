"""生成 8 套 Citra 主题包（.zip）：面板背景 + 全套按键素材。

素材规格必须严格守住（改了就会动布局）：
  圆键类 / 功能键 / 十字 / 摇杆 / home -> 256x256
  肩键 L/R                        -> 256x128
  bg_portrait.jpg                 -> 1828x2584

native 的缩放在 EmulationActivity.getInputBitmap()：
  scale *= oriWidth / dstWidth;  dstWidth *= scale; dstHeight *= scale
=> 显示宽度恒定（由 sControllerScale 决定），**高度 = 显示宽度 × 素材高/素材宽**。
所以形状只能靠"画布内内容的宽高比"调，不能靠改素材宽度。
START/SELECT 的显示宽度被锁在 ~112px（内置图宽 × 0.14 × (o+50)/100 × 0.8），
所以内容按 232x162 画 → 显示 112x78，高度与设计稿一致。
"""
import io
import os
import zipfile

from PIL import Image, ImageDraw

import skins_design as sd
import skins_panel as sp

CELL = 256
SHOULDER = (256, 128)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'themes')

# zip 文件名 = 设置里显示的名字
NAME = {
    'cosmo': 'cosmo-black',
    'aqua': 'aqua-blue',
    'flare_red': 'flare-red',
    'ice_white': 'ice-white',
    'coral_pink': 'coral-pink',
    'metallic_blue': 'metallic-blue',
    'snes': 'snes',
    'galaxy': 'galaxy',
}


def center(im, box=(CELL, CELL)):
    """贴到指定画布中央"""
    if isinstance(box, int):
        box = (box, box)
    cv = Image.new('RGBA', box, (0, 0, 0, 0))
    cv.alpha_composite(im, ((box[0] - im.width) // 2, (box[1] - im.height) // 2))
    return cv


def ring_range(size, skin, pressed=False):
    """摇杆的行程指示环（类似 default 的 *_range.png）"""
    cv = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(cv)
    col = sd.lerp(skin['light'], (255, 255, 255), 0.35)
    d.ellipse([2, 2, size - 3, size - 3], outline=col + (70,), width=max(2, size // 90))
    d.ellipse([size * 0.34, size * 0.34, size * 0.66, size * 0.66],
              outline=col + (40,), width=max(1, size // 140))
    return cv


def build_assets(key):
    """返回 {文件名: PIL.Image}"""
    sk = sd.SKINS[key]
    a = {}

    # 字母键 232 见方（default 是 232/256 = 0.906）
    for ch in 'ABXY':
        a[ch.lower()] = center(sd.face_button(ch, sk, False, 232))
        a[ch.lower() + '_pressed'] = center(sd.face_button(ch, sk, True, 232))

    # combo 键 1/2/3，默认素材占 0.742
    for n, lab in (('one', '1'), ('two', '2'), ('three', '3')):
        a[n] = center(sd.face_button(lab, sk, False, 190))
        a[n + '_pressed'] = center(sd.face_button(lab, sk, True, 190))

    # 肩键：256x128 铺满
    for side in ('L', 'R'):
        for pr in (False, True):
            a[side.lower() + ('_pressed' if pr else '')] = center(
                sd.pill(sk, side, 256, 135, pressed=pr, round_r=0.42), SHOULDER)

    # ZL / ZR（竖屏布局不显示，但主题要齐）
    for side in ('ZL', 'ZR'):
        a[side.lower()] = center(sd.pill(sk, side, 232, 150, round_r=0.36))
        a[side.lower() + '_pressed'] = center(sd.pill(sk, side, 232, 150, pressed=True, round_r=0.36))

    # SELECT / START：宽 232 × 高 162 → 显示 112x78
    # 画布直接做成 256x178：显示幅面 = 素材比例，这样才是扁胶囊
    for lab in ('SELECT', 'START'):
        a[lab.lower()] = sd.pill(sk, lab, 256, 178, round_r=0.5)
        a[lab.lower() + '_pressed'] = sd.pill(sk, lab, 256, 178, pressed=True, round_r=0.5)

    # 十字键：跨整个画布
    a['dpad'] = sd.dpad(sk, 0, CELL)
    a['dpad_pressed_one'] = sd.dpad(sk, 1, CELL)
    a['dpad_pressed_two'] = sd.dpad(sk, 2, CELL)

    # 摇杆 / C 摇杆（252，default 是 0.984）
    for prefix in ('joystick', 'c_stick'):
        a[prefix] = center(sd.stick(sk, False, 252))
        a[prefix + '_pressed'] = center(sd.stick(sk, True, 252))
        a[prefix + '_range'] = ring_range(CELL, sk)

    # HOME：default 占 0.805
    a['home'] = center(sd.home_button(sk, 206))
    a['home_pressed'] = center(sd.home_button(sk, 206, pressed=True))
    return a


def build_backdrops(key):
    panel = sp.render_panel(key).convert('RGB')
    buf = io.BytesIO()
    panel.save(buf, 'JPEG', quality=92, optimize=True)
    land = panel.resize((2584, 1828), Image.LANCZOS)
    buf2 = io.BytesIO()
    land.save(buf2, 'JPEG', quality=88, optimize=True)
    return buf.getvalue(), buf2.getvalue()


def write_zip(key):
    name = NAME[key]
    assets = build_assets(key)
    portrait, landscape = build_backdrops(key)
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name + '.zip')
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for fn in sorted(assets):
            b = io.BytesIO()
            assets[fn].save(b, 'PNG', optimize=True)
            z.writestr(fn + '.png', b.getvalue())
        z.writestr('bg_portrait.jpg', portrait)
        z.writestr('bg_landscape.jpg', landscape)
    print('%-14s %-16s %7.1f KB  %d files' % (
        name, sd.SKINS[key]['cn'], os.path.getsize(path) / 1024, len(assets) + 2))
    return path


if __name__ == '__main__':
    for k in sd.SKINS:
        write_zip(k)
    print('->', os.path.abspath(OUT))
