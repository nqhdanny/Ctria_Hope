package org.citra.emu;

import android.app.Activity;
import android.content.res.AssetManager;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.PorterDuff;
import android.graphics.PorterDuffXfermode;
import android.graphics.Rect;
import android.graphics.drawable.BitmapDrawable;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.view.View;

import java.io.InputStream;
import java.lang.ref.WeakReference;

import org.citra.emu.overlay.InputOverlay;

/**
 * Pura X Max 折叠屏适配：转轴对齐双屏布局。
 *
 * 内屏（短边 >= 1500px 且 长宽比 1.2~1.6）时：以转轴为分界，
 *   上屏贴上半区底边、下屏贴下半区顶边，两屏在转轴上无缝相接，
 *   外侧留对称黑边，等效真机 3DS 的「上盖 / 下盖」。
 * 外屏（折叠态）时：按 Citra 原生 DefaultFrameLayout 复刻，行为不变。
 *
 * 重要：native 的 setCustomLayout() 末尾会执行 s_render_window->UpdateLayout()，
 * 而 s_render_window 只在 BootGame() 里创建（main_android.cpp:62），
 * s_is_running 在其之后才置 true（main_android.cpp:128）。
 * 因此只有在 NativeLibrary.IsRunning() == true 时调用才安全，
 * 否则必然空指针 SIGSEGV（fault addr 0x70），表现为进游戏立刻闪退。
 */
public final class HingeHelper {
    private static final String TAG = "HingeLayout";

    private static final int TOP_W = 400;
    private static final int TOP_H = 240;
    private static final int BOT_W = 320;
    private static final int BOT_H = 240;

    private static final float TOP_AR = (float) TOP_H / TOP_W; // 0.6
    private static final float BOT_AR = (float) BOT_H / BOT_W; // 0.75

    private static final int RETRY_MS = 200;
    private static final int MAX_RETRY = 150; // 最多等 30s

    /** 下屏底部留白占「下半区高度」的比例（0.333 → 下屏底 2154，下屏高 862） */
    private static final float BOTTOM_MARGIN_RATIO = 0.333f;

    /**
     * 上屏四周留出的边框宽度，占窗口宽度的比例。
     * 0.015317 → 内屏 1828 宽时每侧 28px，外屏 1264 宽时 19px。
     *
     * 原来上屏是 0..1828 顶满两侧，看起来像游戏画面直接贴在壳上；
     * 缩进一圈后屏幕才像嵌在上盖里。**必须和 skins_panel.TOP_INSET 用同一个比例**，
     * 否则主题背景上的边框和实际画面会错开。
     */
    private static final float TOP_INSET_RATIO = 0.015317f;

    /**
     * 上屏底边与转轴的距离，占「半屏高」的比例。
     * 0.045 → 内屏 58px（缩进后底边落在 1217，离转轴 75px；原来只留 17px）。
     *
     * 为什么必须留：折叠时转轴附近有一段弯折过渡区，画面贴到转轴就会被一起折弯，
     * 上屏最下面几行字会跟着变形。原来 17px 等于没留。
     */
    private static final float TOP_HINGE_GAP_RATIO = 0.045f;

    /**
     * 下屏左右各留白占窗口宽度的比例。
     * 0.1855 → 每侧 339px，fitArea 先取到可用宽 1150px → 最大矩形 1149x862。
     * 两侧 339px 竖条：左 = L + 方向盘 350 + 摇杆 281；右 = R + ABXY 菱形 + 主页。
     */
    private static final float SIDE_MARGIN_RATIO = 0.1855f;

    /**
     * 下屏再收缩：宽度占「fitArea 最大矩形」的比例。
     * 0.86336 → 1149 * 0.86336 = 992，高度按 4:3 得 744。
     * 为什么必须缩：十字键素材是 350 满幅（四周没有透明边），而左侧条只有 339px，
     * 不缩的话十字键必然被屏幕左边缘裁掉。缩 156px 后左右两侧各腾出约 40px。
     */
    private static final float BOT_WIDTH_FILL = 0.86336f;

    /**
     * 下屏顶边相对转轴下移量，占「半屏高」的比例。
     * 0.068111 → 内屏下移 88px（1292 → 1380），露出下屏上边框 + 整根转轴。
     * 原来下屏顶边死死贴在转轴上，看起来像「转轴被屏幕吃掉」。
     */
    private static final float BOT_TOP_GAP_RATIO = 0.068111f;

    /**
     * 下屏水平中心相对窗口中心的偏移（占窗口宽度比例，负值左移）。
     * -0.003829 → 内屏左移 7px（中心 906）。右侧要塞 ABXY 菱形，比左侧十字键更宽，
     * 所以整体偏左一点，两侧留白才能对称。
     */
    private static final float BOT_CENTER_NUDGE = -0.003829f;

    /**
     * 按键尺寸的归一化基准宽度（内屏竖持宽度）。
     * 外屏只有 1264 宽，是内屏的 69%，而按键尺寸是绝对像素 —— 不缩放的话
     * 外屏上方向盘(327)比侧条(234)还宽，会压掉大半个下屏。
     *
     * 真机 release 包里 InputOverlay 是混淆过的：sControllerScale 变成字段 `o`，
     * 且由 native config `input_overlay_scale` 赋值，尺寸正比于 (o + 70)。
     * 所以不能用静态字段，只能改 config 再让它重建。
     */
    private static final float SCALE_BASE_WIDTH = 1828f;
    private static final int SCALE_BASE_VALUE = 40; // 内屏默认 o=0x28
    /**
     * 实测标定：内屏 o=40 时方向盘 327px，外屏 o=6 时只有 168px。
     * 即每单位 o 约 4.68px，据此反算「目标 327*w/1828」对应的 o。
     */
    private static final float SCALE_PX_PER_UNIT = 4.676f;
    private static final float SCALE_REF_DIAMETER = 327f;

    // 刻意不使用任何静态初始化块：注入点没有 try/catch 包裹，
    // <clinit> 一旦抛错会直接带走整个进程。
    private static Handler sHandler;
    private static Runnable sTask;
    private static int sW;
    private static int sH;
    private static int sTry;

    private static WeakReference<Activity> sActivity;
    private static String sBackdropKey;
    private static int sLastScaleW = -1;

    private HingeHelper() {
    }

    private static Handler handler() {
        if (sHandler == null) {
            sHandler = new Handler(Looper.getMainLooper());
        }
        return sHandler;
    }

    /** 由 EmulationActivity.surfaceChanged 调用 */
    public static void apply(Activity activity, int w, int h) {
        try {
            if (activity != null) {
                sActivity = new WeakReference<>(activity);
            }
            if (w <= 0 || h <= 0) {
                return;
            }
            sW = w;
            sH = h;
            sTry = 0;
            Handler handler = handler();
            if (sTask == null) {
                sTask = new Runnable() {
                    @Override
                    public void run() {
                        try {
                            step();
                        } catch (Throwable t) {
                            Log.w(TAG, "step failed", t);
                        }
                    }
                };
            }
            handler.removeCallbacks(sTask);
            handler.post(sTask);
        } catch (Throwable t) {
            Log.w(TAG, "apply failed", t);
        }
    }

    private static void step() {
        int w = sW;
        int h = sH;
        if (w <= 0 || h <= 0) {
            return;
        }
        if (!NativeLibrary.IsRunning()) {
            if (++sTry <= MAX_RETRY) {
                sHandler.postDelayed(sTask, RETRY_MS);
            } else {
                Log.w(TAG, "give up: not running, surface=" + w + "x" + h);
            }
            return;
        }
        try {
            push(w, h);
        } catch (Throwable t) {
            Log.w(TAG, "push failed", t);
        }
    }

    private static void push(int w, int h) {
        int[] top;
        int[] bot;
        if (h >= w) {
            // 竖持：转轴水平，上下分屏。上屏贴转轴上沿，下屏缩小后下移给按键腾位。
            // 内屏(1828x2584)与外屏(1264x1848)走同一套比例，全部按屏宽/屏高换算。
            int half = h / 2;
            top = fitArea(TOP_W, TOP_H, 0, 0, w, half);
            snapBottomTo(top, half - Math.round(half * TOP_HINGE_GAP_RATIO));
            insetTop(top, w, half);
            int bottom = h - Math.round(half * BOTTOM_MARGIN_RATIO);
            int side = Math.round(w * SIDE_MARGIN_RATIO);
            bot = fitArea(BOT_W, BOT_H, side, half, w - side, bottom);
            shrinkBottom(bot, w, half);
        } else {
            // 横持：转轴垂直，左右分屏
            int half = w / 2;
            top = fitArea(TOP_W, TOP_H, 0, 0, half, h);
            snapRightTo(top, half);
            bot = fitArea(BOT_W, BOT_H, half, 0, w, h);
            snapLeftTo(bot, half);
        }

        clamp(top, w, h);
        clamp(bot, w, h);

        Log.i(TAG, "push " + w + "x" + h
                + " top=" + str(top) + " bot=" + str(bot));

        if (!NativeLibrary.IsRunning()) {
            return;
        }
        NativeLibrary.setCustomLayout(true, top[0], top[1], top[2], top[3]);
        if (!NativeLibrary.IsRunning()) {
            return;
        }
        NativeLibrary.setCustomLayout(false, bot[0], bot[1], bot[2], bot[3]);
        tuneControllerScale(w);
        Log.i(TAG, "ok");
    }

    /**
     * 让虚拟按键随屏宽等比缩放。内屏(1828)保持默认，外屏(1264)缩到约 69%。
     * 做法是改 native config 的 input_overlay_scale，再调 InputOverlay.j()
     * （混淆后的 refreshControls）让它按新值重建按钮。
     */
    private static void tuneControllerScale(int w) {
        if (sLastScaleW == w) {
            return;
        }
        int target = Math.round(SCALE_BASE_VALUE
                - (SCALE_REF_DIAMETER * (1f - (float) w / SCALE_BASE_WIDTH)) / SCALE_PX_PER_UNIT);
        if (target > SCALE_BASE_VALUE) {
            target = SCALE_BASE_VALUE;
        }
        if (target < 0) {
            target = 0;
        }
        Activity activity = sActivity == null ? null : sActivity.get();
        if (activity == null) {
            return;
        }
        View overlay = activity.findViewById(
                activity.getResources().getIdentifier(
                        "surface_input_overlay", "id", activity.getPackageName()));
        if (!(overlay instanceof InputOverlay)) {
            return;
        }
        NativeLibrary.setConfigInteger("input_overlay_scale", target);
        ((InputOverlay) overlay).j();
        sLastScaleW = w;
        Log.i(TAG, "controllerScale=" + target + " for w=" + w);
    }

    /**
     * 给 InputOverlay 铺"中间挖空"的碳纤维背景。
     *
     * 黑区由 SurfaceView 自己渲染成黑色，XML 背景会被它盖住；而 InputOverlay 是
     * SurfaceView 之上的 View，它的 background 会盖住游戏画面 —— 所以把上下两屏
     * 对应的矩形挖成透明，游戏画面从洞里透出来，其余地方显示纹理。
     */
    private static void applyBackdrop(int w, int h, int[] top, int[] bot) {
        Activity activity = sActivity == null ? null : sActivity.get();
        if (activity == null) {
            return;
        }
        View overlay = activity.findViewById(
                activity.getResources().getIdentifier(
                        "surface_input_overlay", "id", activity.getPackageName()));
        if (overlay == null) {
            return;
        }
        String key = w + "x" + h + "|" + top[0] + "," + top[1] + "," + top[2] + "," + top[3]
                + "|" + bot[0] + "," + bot[1] + "," + bot[2] + "," + bot[3];
        if (key.equals(sBackdropKey) && overlay.getBackground() != null) {
            return;
        }
        Bitmap backdrop = buildBackdrop(activity, w, h, top, bot);
        if (backdrop == null) {
            return;
        }
        overlay.setBackground(new BitmapDrawable(activity.getResources(), backdrop));
        sBackdropKey = key;
        Log.i(TAG, "backdrop " + w + "x" + h);
    }

    private static Bitmap buildBackdrop(Activity activity, int w, int h, int[] top, int[] bot) {
        Bitmap src = loadWallpaper(activity);
        if (src == null) {
            return null;
        }
        try {
            Bitmap base = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888);
            Canvas canvas = new Canvas(base);
            float scale = Math.max((float) w / src.getWidth(), (float) h / src.getHeight());
            int dw = Math.round(src.getWidth() * scale);
            int dh = Math.round(src.getHeight() * scale);
            // 顶部对齐：只取原图上半部的纯碳纤维，避开右下角的橙红光带
            canvas.drawBitmap(src,
                    new Rect(0, 0, src.getWidth(), src.getHeight()),
                    new Rect((w - dw) / 2, 0, (w - dw) / 2 + dw, dh),
                    new Paint(Paint.FILTER_BITMAP_FLAG));
            Paint clear = new Paint();
            clear.setXfermode(new PorterDuffXfermode(PorterDuff.Mode.CLEAR));
            canvas.drawRect(top[0], top[1], top[2], top[3], clear);
            canvas.drawRect(bot[0], bot[1], bot[2], bot[3], clear);
            return base;
        } catch (Throwable t) {
            Log.w(TAG, "backdrop failed", t);
            return null;
        } finally {
            src.recycle();
        }
    }

    private static Bitmap loadWallpaper(Activity activity) {
        InputStream in = null;
        try {
            AssetManager assets = activity.getAssets();
            in = assets.open("wallpaper.jpg");
            return BitmapFactory.decodeStream(in);
        } catch (Throwable t) {
            Log.w(TAG, "no wallpaper", t);
            return null;
        } finally {
            if (in != null) {
                try {
                    in.close();
                } catch (Throwable ignored) {
                }
            }
        }
    }

    private static boolean isFoldableInner(int w, int h) {
        int min = Math.min(w, h);
        int max = Math.max(w, h);
        float ar = (float) max / min;
        return min >= 1500 && ar >= 1.2f && ar <= 1.6f;
    }

    /** 在指定区域内等比放大到最大并居中，返回 {l,t,r,b} */
    private static int[] fitArea(int imgW, int imgH, int l, int t, int r, int b) {
        int aw = r - l;
        int ah = b - t;
        if (aw <= 0 || ah <= 0) {
            return new int[]{l, t, l, t};
        }
        float scale = Math.min(aw / (float) imgW, ah / (float) imgH);
        int sw = Math.round(imgW * scale);
        int sh = Math.round(imgH * scale);
        if (sw > aw) {
            sw = aw;
        }
        if (sh > ah) {
            sh = ah;
        }
        int sl = l + (aw - sw) / 2;
        int st = t + (ah - sh) / 2;
        return new int[]{sl, st, sl + sw, st + sh};
    }

    /**
     * 上屏四周缩进一圈，做出「屏幕嵌在上盖里」的边框。
     *
     * 只缩宽不行：上屏是 5:3，宽缩了高必须跟着缩，否则 native 会把画面拉伸变形。
     * 所以按「新宽 → 新高」重算，再以原矩形中心为基准居中。
     * 内屏 1828 宽：inset 28 → 1772x1063，落在 28..1800 × 212..1275。
     */
    private static void insetTop(int[] rect, int w, int half) {
        int inset = Math.round(w * TOP_INSET_RATIO);
        int nw = (rect[2] - rect[0]) - inset * 2;
        if (nw <= 0) {
            return;
        }
        int nh = Math.round(nw * TOP_AR);
        int cx = (rect[0] + rect[2]) / 2;
        int cy = (rect[1] + rect[3]) / 2;
        rect[0] = cx - nw / 2;
        rect[1] = cy - nh / 2;
        rect[2] = rect[0] + nw;
        rect[3] = rect[1] + nh;
    }

    private static void snapBottomTo(int[] rect, int y) {
        int dy = y - rect[3];
        rect[1] += dy;
        rect[3] += dy;
    }

    /**
     * 下屏收缩成 992x744 并把顶边从转轴下移 88px（内屏数值）。
     * fitArea 给出的只是「可用区域内最大矩形」，那会让下屏顶边贴死转轴、
     * 左右挤满按键条；这里按比例收回，四周才有面板边框。
     */
    private static void shrinkBottom(int[] rect, int w, int half) {
        int bw = rect[2] - rect[0];
        int nw = Math.round(bw * BOT_WIDTH_FILL);
        int nh = Math.round(nw * BOT_AR);
        int cx = (rect[0] + rect[2]) / 2 + Math.round(w * BOT_CENTER_NUDGE);
        int top = half + Math.round(half * BOT_TOP_GAP_RATIO);
        rect[0] = cx - nw / 2;
        rect[1] = top;
        rect[2] = rect[0] + nw;
        rect[3] = top + nh;
    }

    private static void snapRightTo(int[] rect, int x) {
        int dx = x - rect[2];
        rect[0] += dx;
        rect[2] += dx;
    }

    private static void snapLeftTo(int[] rect, int x) {
        int dx = x - rect[0];
        rect[0] += dx;
        rect[2] += dx;
    }

    private static void clamp(int[] rect, int w, int h) {
        if (rect[0] < 0) {
            rect[0] = 0;
        }
        if (rect[1] < 0) {
            rect[1] = 0;
        }
        if (rect[2] > w) {
            rect[2] = w;
        }
        if (rect[3] > h) {
            rect[3] = h;
        }
        if (rect[2] <= rect[0]) {
            rect[2] = rect[0] + 1;
        }
        if (rect[3] <= rect[1]) {
            rect[3] = rect[1] + 1;
        }
    }

    private static String str(int[] r) {
        return r[0] + "," + r[1] + "," + r[2] + "," + r[3]
                + " [" + (r[2] - r[0]) + "x" + (r[3] - r[1]) + "]";
    }

    /** 逐行复刻 Layout::DefaultFrameLayout（framebuffer_layout.cpp），用于外屏 */
    private static int[][] defaultLayout(int w, int h) {
        int halfH = h / 2;
        int[] top = maxRectangle(w, halfH, TOP_AR);
        int[] bot = maxRectangle(w, halfH, BOT_AR);

        float windowAr = (float) h / w;
        float emuAr = TOP_AR * 2.0f;
        if (windowAr < emuAr) {
            // 左右留边
            translateX(top, (w - (top[2] - top[0])) / 2);
            translateX(bot, (w - (bot[2] - bot[0])) / 2);
            translateY(bot, halfH);
        } else {
            // 上下留边：下屏按上屏高度重算宽度
            int[] b2 = maxRectangle(w, top[3] - top[1], BOT_AR);
            translateX(b2, ((top[2] - top[0]) - (b2[2] - b2[0])) / 2);
            translateY(b2, top[3] - top[1]);
            bot = b2;
        }
        return new int[][]{top, bot};
    }

    /** 复刻 maxRectangle：从 (0,0) 起按宽高上限取最大等比矩形 */
    private static int[] maxRectangle(int aw, int ah, float ar) {
        float scale = Math.min((float) aw, ah / ar);
        return new int[]{0, 0, Math.round(scale), Math.round(scale * ar)};
    }

    private static void translateX(int[] rect, int dx) {
        rect[0] += dx;
        rect[2] += dx;
    }

    private static void translateY(int[] rect, int dy) {
        rect[1] += dy;
        rect[3] += dy;
    }
}
