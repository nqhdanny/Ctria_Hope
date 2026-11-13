"""副屏缩小下移 + ABXY 重排：出对比稿（只出图，不动 ini / APK）。

副屏新位：390..1398 x 1380..2136  (1008x756，严格 4:3)
  - 顶边从转轴 1292 下移到 1380，让出 88px 上边框
  - 宽度从 1148 收到 1008，左右各留 40px 给按键
两稿差别只在 ABXY：
  1 = 原位不动（Y 左缘 1438，距屏 40px；A 右缘 1816，距机身边 12px）
  2 = 菱形居中到右面板并微缩到 ⌀132（左右各 35px，更均衡）
"""
import os
import skins_panel as sp

BOT = (390, 1380, 1398, 2136)
CY = 1796


def abxy(cx, s, r):
    return {
        'x': ((cx, CY - s), (r, r)),
        'y': ((cx - s, CY), (r, r)),
        'a': ((cx + s, CY), (r, r)),
        'b': ((cx, CY + s), (r, r)),
    }


def make(key, tag, cx=None, s=119, r=140):
    sp.SCR_BOT = BOT
    b = dict(sp.BTN)
    if cx is not None:
        b.update(abxy(cx, s, r))
    sp.BTN = b
    out = '../diag/var/%s_%s.png' % (tag, key)
    sp.render_full(key).save(out)
    return out


if __name__ == '__main__':
    os.makedirs('../diag/var', exist_ok=True)
    for key in ('aqua', 'cosmo', 'ice_white'):
        make(key, 'final', cx=None)                  # 十字键右移 + 副屏 992 + ABXY 分开
    print('done')
