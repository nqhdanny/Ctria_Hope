package org.citra.emu;

import android.app.Activity;
import android.app.WallpaperManager;
import android.app.WallpaperColors;
import android.content.res.ColorStateList;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.ColorFilter;
import android.graphics.LinearGradient;
import android.graphics.Paint;
import android.graphics.PixelFormat;
import android.graphics.Outline;
import android.graphics.RadialGradient;
import android.graphics.Rect;
import android.graphics.Shader;
import android.graphics.drawable.Drawable;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.RippleDrawable;
import android.os.Build;
import android.util.Log;
import android.view.View;
import android.view.ViewGroup;
import android.view.ViewOutlineProvider;
import android.view.ViewTreeObserver;
import android.view.Window;
import android.widget.TextView;

import java.lang.ref.WeakReference;
import java.lang.reflect.Method;
import java.util.WeakHashMap;

/**
 * 设置界面「跟随壁纸配色」的皮肤层。
 *
 * 做法：
 *   1) 用 WallpaperManager.getWallpaperColors() 取系统壁纸的主色（API 27+），
 *      拿不到就退回 Citra 橙。全程不申请任何权限。
 *   2) 主色转 HSL，压低饱和度当底 —— 暗壁纸出深底 + 白字，亮壁纸出浅底 + 黑字，
 *      顺便定好卡片底色、描边、强调色（勾选框 / 分组标题）。
 *   3) 背景是一层自绘 Drawable：纵向渐变 + 顶部柔光，比纯色有厚度。
 *   4) 列表项在 RecyclerView 里是动态创建的，所以这里监听 child attach +
 *      全局布局，把每个 item 改造成圆角半透明卡片并逐个子 View 上色。
 *
 * 所有入口都包 try/catch：这个类只负责好看，绝不能把设置界面搞崩。
 */
public final class SettingsSkin {
    private static final String TAG = "SettingsSkin";

    /** 已处理过的 item 根 View，避免重复 new Drawable（Weak 防泄漏） */
    private static final WeakHashMap<View, Boolean> DONE = new WeakHashMap<>();

    private static WeakReference<Activity> sAct;
    private static Object sRv;          // 当前挂过监听的 RecyclerView（Object，避免编译期依赖）
    private static boolean sPaletted;
    private static boolean sListenersAdded;

    // 调色板
    private static boolean sDark;
    private static int cFg;
    private static int cSub;
    private static int cAccent;
    private static int cCard;
    private static int cStroke;
    private static int cRipple;
    private static int cTop;
    private static int cBot;
    private static int cGlow;
    private static int cStatus;
    private static float sH;
    private static float sS;

    private SettingsSkin() {
    }

    // ------------------------------------------------------------------ 入口

    /** setContentView 之前：先把窗口底色定下来，避免白屏闪一下 */
    public static void preApply(Activity a) {
        try {
            if (a == null) {
                return;
            }
            computePalette(a.getApplicationContext());
            Window w = a.getWindow();
            w.setBackgroundDrawable(new ShellBg(cTop, cBot, cGlow));
            if (Build.VERSION.SDK_INT >= 21) {
                w.setStatusBarColor(cStatus);
                w.setNavigationBarColor(cBot);
            }
            setLightBars(w, !sDark);
            applyDialogTheme(a);
        } catch (Throwable t) {
            Log.w(TAG, "preApply failed", t);
        }
    }

    /** setContentView 之后：接管根视图背景、顶栏、列表项 */
    public static void attach(final Activity a) {
        try {
            if (a == null) {
                return;
            }
            sAct = new WeakReference<>(a);
            final View root = a.getWindow().getDecorView();
            // 首帧还没布局完，findViewById 可能拿不到 fragment 的 RecyclerView，
            // 所以再 post 一次 + 挂全局布局监听。
            root.post(new Runnable() {
                @Override
                public void run() {
                    try {
                        decorateRoot(a);
                        decorateToolbar(a);
                        scan(a);
                    } catch (Throwable t) {
                        Log.w(TAG, "post decorate failed", t);
                    }
                }
            });
            if (!sListenersAdded) {
                sListenersAdded = true;
                root.getViewTreeObserver().addOnGlobalLayoutListener(
                        new ViewTreeObserver.OnGlobalLayoutListener() {
                            @Override
                            public void onGlobalLayout() {
                                try {
                                    Activity act = sAct == null ? null : sAct.get();
                                    if (act == null) {
                                        return;
                                    }
                                    scan(act);
                                } catch (Throwable ignored) {
                                }
                            }
                        });
            }
        } catch (Throwable t) {
            Log.w(TAG, "attach failed", t);
        }
    }

    // ------------------------------------------------------------- 调色板

    private static void computePalette(android.content.Context ctx) {
        if (sPaletted) {
            return;
        }
        sPaletted = true;

        float[] hsl = null;
        String from = "fallback";
        try {
            hsl = hslFromWallpaper(ctx);
            if (hsl != null) {
                from = "wallpaper";
            }
        } catch (Throwable t) {
            Log.w(TAG, "wallpaper sampling failed", t);
        }
        if (hsl == null) {
            try {
                if (Build.VERSION.SDK_INT >= 27) {
                    int seed = wallpaperSeed(ctx);
                    if (seed != 0 && Color.alpha(seed) != 0) {
                        hsl = toHsl(seed);
                        from = "wallpaper-colors";
                    }
                }
            } catch (Throwable t) {
                Log.w(TAG, "wallpaper colors unavailable", t);
            }
        }
        if (hsl == null) {
            // 兜底取深蓝紫而不是 Citra 橙：橙底配青色面板皮肤完全不搭，
            // 而且 EMUI 上壁纸取色失败是常态，兜底色实际上就是用户看到的样子。
            hsl = toHsl(0xFF4A5799);
        }

        float h = hsl[0];
        float s = hsl[1];
        float l = hsl[2];
        sH = h;
        sS = s;
        // 雾面壁纸饱和度可能很低，但色相仍然有信息量 —— 只补饱和，不改色相。
        // （原来这里把 h 硬掰成 42，蓝紫壁纸会被染成土黄，已实测踩过。）
        if (s < 0.06f) {
            s = 0.14f;
        }

        sDark = l < 0.55f;
        if (sDark) {
            cTop = fromHsl(h, Math.min(s, 0.30f), 0.150f);
            cBot = fromHsl(h, Math.min(s, 0.20f), 0.055f);
            cStatus = cTop;
            cGlow = withAlpha(fromHsl(h, Math.min(1f, s * 1.15f + 0.15f), 0.58f), 24);
            cFg = 0xFFF3F6FA;
            cSub = 0xFF9AA6B6;
            cAccent = fromHsl(h, Math.min(1f, s * 1.10f + 0.30f), 0.66f);
            cCard = 0x12FFFFFF;      // 白 7%
            cStroke = 0x26FFFFFF;    // 白 15%
            cRipple = 0x33FFFFFF;
        } else {
            cTop = fromHsl(h, Math.min(s, 0.26f), 0.955f);
            cBot = fromHsl(h, Math.min(s, 0.34f), 0.855f);
            cStatus = fromHsl(h, Math.min(s, 0.26f), 0.975f);
            cGlow = withAlpha(fromHsl(h, Math.min(1f, s * 1.10f + 0.20f), 0.62f), 34);
            cFg = 0xFF15181D;
            cSub = 0xFF5A6474;
            cAccent = fromHsl(h, Math.min(1f, s * 1.05f + 0.35f), 0.36f);
            cCard = 0xECFFFFFF;      // 白 92%
            cStroke = 0xFFFFFFFF;
            cRipple = 0x1F000000;
        }
        diag("FINAL from=" + from + " h=" + Math.round(h) + " s=" + Math.round(s * 100)
                + " l=" + Math.round(l * 100) + " dark=" + sDark);
        Log.i(TAG, from + " h=" + Math.round(h) + " s=" + Math.round(s * 100)
                + " l=" + Math.round(l * 100) + " dark=" + sDark
                + " accent=#" + Integer.toHexString(cAccent));
    }

    /**
     * 直接从壁纸位图上统计主色相。
     *
     * 为什么不能只靠 WallpaperColors：实测这台机器的壁纸是深蓝紫雾面，
     * 系统却把 primary 报成了黄色（大概是底部那道黄光），照它上色整页变成土黄，
     * 和壁纸完全不搭。自己采样一遍色相才靠得住。
     *
     * 过滤规则：透明像素、近黑近白、低饱和（雾面/白底）都不参与统计，
     * 色相用 sin/cos 向量累加，避免 0/360 附近取平均出错。
     */
    /** 诊断落盘：EMUI 会过滤第三方应用的 logcat，日志抓不到，只能写文件 */
    private static void diag(String msg) {
        try {
            java.io.File dir = new java.io.File(
                    android.os.Environment.getExternalStorageDirectory(), "citra-emu");
            dir.mkdirs();
            java.io.FileWriter w = new java.io.FileWriter(
                    new java.io.File(dir, "skin-diag.txt"), true);
            w.write(new java.text.SimpleDateFormat("HH:mm:ss", java.util.Locale.US)
                    .format(new java.util.Date()) + "  " + msg + "\n");
            w.close();
        } catch (Throwable ignored) {
        }
    }

    private static float[] hslFromWallpaper(android.content.Context ctx) {
        WallpaperManager wm = WallpaperManager.getInstance(ctx);
        if (wm == null) {
            return null;
        }
        android.graphics.drawable.Drawable d = null;
        try {
            d = wm.getDrawable();
        } catch (Throwable t) {
            Log.w(TAG, "getDrawable threw: " + t);
        }
        if (d == null) {
            // targetSdk >= 33 起这个 API 对普通应用可能直接给 null，必须记下来
            diag("getDrawable -> null");
            return null;
        }
        diag("getDrawable -> " + d.getClass().getName()
                + " " + d.getIntrinsicWidth() + "x" + d.getIntrinsicHeight());
        final int n = 48;
        android.graphics.Bitmap bmp = android.graphics.Bitmap.createBitmap(
                n, n, android.graphics.Bitmap.Config.ARGB_8888);
        try {
            Canvas c = new Canvas(bmp);
            d.setBounds(0, 0, n, n);
            d.draw(c);
        } catch (Throwable t) {
            bmp.recycle();
            return null;
        }
        double sx = 0;
        double sy = 0;
        double sw = 0;
        double ss = 0;
        double sl = 0;
        for (int y = 0; y < n; y++) {
            for (int x = 0; x < n; x++) {
                int p = bmp.getPixel(x, y);
                if (Color.alpha(p) < 128) {
                    continue;
                }
                float[] hsl = toHsl(p);
                if (hsl[1] < 0.18f || hsl[2] < 0.08f || hsl[2] > 0.96f) {
                    continue;
                }
                // 中间调权重最高：纯高饱和和死黑都带偏色相
                float w = hsl[2] > 0.5f ? (1f - hsl[2]) : hsl[2];
                w = hsl[1] * w * 4f + 0.02f;
                double rad = Math.toRadians(hsl[0]);
                sx += Math.cos(rad) * w;
                sy += Math.sin(rad) * w;
                sw += w;
                ss += hsl[1] * w;
                sl += hsl[2] * w;
            }
        }
        bmp.recycle();
        diag("sampled weight=" + Math.round(sw));
        if (sw < 1.0) {
            diag("sampling too few pixels -> null");
            return null;
        }
        float hue = (float) Math.toDegrees(Math.atan2(sy, sx));
        if (hue < 0) {
            hue += 360f;
        }
        return new float[]{hue, (float) (ss / sw), (float) (sl / sw)};
    }

    /** 单独成一个方法：API 27 的类只在这里被引用，低版本不会触发类校验 */
    private static int wallpaperSeed(android.content.Context ctx) {
        WallpaperManager wm = WallpaperManager.getInstance(ctx);
        if (wm == null) {
            return 0;
        }
        WallpaperColors wc = wm.getWallpaperColors(WallpaperManager.FLAG_SYSTEM);
        if (wc == null) {
            return 0;
        }
        Color pc = wc.getPrimaryColor();
        if (pc != null) {
            return pc.toArgb();
        }
        return 0;
    }

    /**
     * 深色底时把弹窗（主题选择 / 分辨率列表 / 输入框）也换成深色板。
     * 这是常规的 theme overlay：必须在 setContentView 之前 apply 才生效，
     * 所以挂在 preApply 里。浅色壁纸什么都不做，保持 AppCompat 的白卡。
     */
    private static void applyDialogTheme(Activity a) {
        if (!sDark) {
            return;
        }
        try {
            int sid = a.getResources().getIdentifier(
                    "OverlayDialogDark", "style", a.getPackageName());
            if (sid != 0) {
                a.getTheme().applyStyle(sid, true);
            }
        } catch (Throwable t) {
            Log.w(TAG, "dialog overlay failed", t);
        }
    }

    // --------------------------------------------------------- 根视图 / 顶栏

    private static void decorateRoot(Activity a) {
        // 只画窗口这一层：渐变基准是「整屏高度」。
        // 如果同时给 content 根 View 再铺一层，它从状态栏下沿开始重新渐变，
        // 会在状态栏底下切出一条明显的亮带（实测过）。
        a.getWindow().setBackgroundDrawable(new ShellBg(cTop, cBot, cGlow));
    }

    private static void decorateToolbar(Activity a) {
        View tb = a.findViewById(id(a, "toolbar"));
        if (tb == null) {
            return;
        }
        tb.setBackgroundColor(Color.TRANSPARENT);
        if (tb instanceof android.widget.Toolbar) {
            return;
        }
        try {
            // androidx Toolbar：标题 / 溢出图标都要按底色反色
            Object t = tb;
            Method setTitleColor = tb.getClass().getMethod("setTitleTextColor", int.class);
            setTitleColor.invoke(t, cFg);
            // 溢出菜单：EMUI 的 Toolbar 在这个主题下画出来是「圆圈 + 下箭头」，
            // 看着像下载按钮。索性自己画三个点，颜色跟标题同一支。
            try {
                Method setOverflow = tb.getClass().getMethod("setOverflowIcon", Drawable.class);
                setOverflow.invoke(t, new MoreIcon(cFg));
            } catch (Throwable ignored) {
            }
        } catch (Throwable ignored) {
        }
    }

    // ------------------------------------------------------ 游戏内运行设置

    /**
     * 游戏里「菜单 → Settings」弹出的那个运行中设置框（dialog_running_settings）。
     *
     * 它是平台 AlertDialog + 自定义 view，不进 SettingsActivity，所以拿不到上面那套
     * 窗口级皮肤；这里单独接管：换深色圆角板、标题条上色、列表项卡片化。
     *
     * 注入点在 DialogFragment.onCreateDialog 的 return 之前，此时 view 已经 inflate
     * 但还没 attach，所以上色动作 post 到 decorView 上，等真正显示时执行。
     */
    public static void applyDialog(final android.app.Dialog d) {
        if (d == null) {
            return;
        }
        try {
            final android.content.Context ctx = d.getContext();
            computePalette(ctx);
            Window w = d.getWindow();
            if (w == null) {
                return;
            }
            final View decor = w.getDecorView();
            decor.post(new Runnable() {
                @Override
                public void run() {
                    skinRunningDialog(d, ctx);
                }
            });
        } catch (Throwable t) {
            Log.w(TAG, "applyDialog failed", t);
        }
    }

    private static void skinRunningDialog(android.app.Dialog d, android.content.Context ctx) {
        try {
            Window w = d.getWindow();
            if (w == null) {
                return;
            }
            GradientDrawable plate = new GradientDrawable();
            plate.setShape(GradientDrawable.RECTANGLE);
            plate.setCornerRadius(dp(ctx, 26));
            plate.setColor(fromHsl(sH, Math.min(sS, 0.22f), 0.105f));
            w.setBackgroundDrawable(plate);

            View decor = w.getDecorView();
            int bar = fromHsl(sH, Math.min(sS, 0.30f), 0.165f);
            final int radius = dp(ctx, 26);

            // 标题条是一块直角矩形，会把 dialog 的圆角啃掉。
            // 把内容层裁成圆角，标题条自然跟着圆。
            View content = decor.findViewById(android.R.id.content);
            if (content != null) {
                content.setClipToOutline(true);
                content.setOutlineProvider(new ViewOutlineProvider() {
                    @Override
                    public void getOutline(View v, Outline outline) {
                        outline.setRoundRect(0, 0, v.getWidth(), v.getHeight(), radius);
                    }
                });
            }

            // 标题是 alignBottom 到右侧内存数字的，本身撑不高。
            // 想加高标题条只能给 text_info 加 padding（title 会被它顶起来）；
            // 直接给 title 加 padding 会把内容区压成 0，文字直接消失。
            View title = decor.findViewById(idOf(ctx, "text_title"));
            if (title != null) {
                title.setBackgroundColor(bar);
                if (title instanceof TextView) {
                    ((TextView) title).setTextColor(cFg);
                }
            }
            View info = decor.findViewById(idOf(ctx, "text_info"));
            if (info != null) {
                info.setBackgroundColor(bar);
                if (info instanceof TextView) {
                    ((TextView) info).setTextColor(cAccent);
                }
                info.setPadding(dp(ctx, 8), dp(ctx, 8), dp(ctx, 14), dp(ctx, 8));
            }

            View rv = decor.findViewById(idOf(ctx, "list_settings"));
            if (rv == null) {
                return;
            }
            rv.setBackground(null);
            if (rv instanceof ViewGroup) {
                ViewGroup g = (ViewGroup) rv;
                g.setClipToPadding(false);
                g.setPadding(dp(ctx, 8), dp(ctx, 6), dp(ctx, 8), dp(ctx, 6));
                for (int i = 0; i < g.getChildCount(); i++) {
                    styleRunningItem(g.getChildAt(i));
                }
            }
            hookList(rv, true);
            Log.i(TAG, "running dialog skinned");
        } catch (Throwable t) {
            Log.w(TAG, "skinRunningDialog failed", t);
        }
    }

    /** 运行设置项：比设置页更紧凑的卡片（这些 item 自带 10dp padding） */
    private static void styleRunningItem(View item) {
        if (item == null || DONE.containsKey(item)) {
            return;
        }
        DONE.put(item, Boolean.TRUE);
        try {
            android.content.Context ctx = item.getContext();
            GradientDrawable card = new GradientDrawable();
            card.setShape(GradientDrawable.RECTANGLE);
            card.setCornerRadius(dp(ctx, 12));
            card.setColor(cCard);
            card.setStroke(Math.max(1, dp(ctx, 0.7f)), cStroke);
            item.setBackground(new RippleDrawable(ColorStateList.valueOf(cRipple), card, null));

            // 列表高度是写死的 350dp，7 项要能一次看全：
            // 靠压 item 自身的上下 padding + 1dp 卡片间距挤回来
            item.setPadding(dp(ctx, 10), dp(ctx, 5), dp(ctx, 10), dp(ctx, 5));
            ViewGroup.LayoutParams lp = item.getLayoutParams();
            if (lp instanceof ViewGroup.MarginLayoutParams) {
                ViewGroup.MarginLayoutParams m = (ViewGroup.MarginLayoutParams) lp;
                m.leftMargin = dp(ctx, 8);
                m.rightMargin = dp(ctx, 8);
                m.topMargin = dp(ctx, 1);
                m.bottomMargin = dp(ctx, 1);
                item.setLayoutParams(m);
            }

            View name = item.findViewById(idOf(ctx, "text_setting_name"));
            if (name instanceof TextView) {
                ((TextView) name).setTextColor(cFg);
            }
            View value = item.findViewById(idOf(ctx, "text_setting_value"));
            if (value instanceof TextView) {
                ((TextView) value).setTextColor(cAccent);
            }
            View btn = item.findViewById(idOf(ctx, "button_setting"));
            if (btn instanceof TextView) {
                ((TextView) btn).setTextColor(cAccent);
            }
            View cb = item.findViewById(idOf(ctx, "checkbox"));
            if (cb != null) {
                try {
                    Method m = cb.getClass().getMethod("setButtonTintList", ColorStateList.class);
                    m.invoke(cb, checkboxTint());
                } catch (Throwable ignored) {
                }
            }
            View sb = item.findViewById(idOf(ctx, "seekbar"));
            if (sb != null) {
                try {
                    Method pr = sb.getClass().getMethod("setProgressTintList", ColorStateList.class);
                    pr.invoke(sb, ColorStateList.valueOf(cAccent));
                    Method th = sb.getClass().getMethod("setThumbTintList", ColorStateList.class);
                    th.invoke(sb, ColorStateList.valueOf(cAccent));
                } catch (Throwable ignored) {
                }
            }
        } catch (Throwable t) {
            Log.w(TAG, "styleRunningItem failed", t);
        }
    }

    // ------------------------------------------------------------- 列表项

    private static void scan(final Activity a) {
        final View root = a.getWindow().getDecorView();
        View rv = root.findViewById(id(a, "list_settings"));
        if (rv == null) {
            return;
        }
        if (rv != sRv) {
            sRv = rv;
            // 列表原本写死 @color/background_color（白底），不清掉会盖住壁纸渐变
            rv.setBackground(null);
            if (rv instanceof ViewGroup) {
                ViewGroup g = (ViewGroup) rv;
                g.setClipToPadding(false);
                g.setPadding(g.getPaddingLeft(), dp(a, 10),
                        g.getPaddingRight(), dp(a, 28));
            }
            hookList(rv, false);
        }
        if (rv instanceof ViewGroup) {
            ViewGroup g = (ViewGroup) rv;
            for (int i = 0; i < g.getChildCount(); i++) {
                styleItem(g.getChildAt(i));
            }
        }
    }

    /**
     * 滚动时新 item 会不断 attach 进来。
     * 不挂 OnChildAttachStateChangeListener 的原因：这个包的 androidx 被 R8 一起混淆了，
     * 接口全名 Class.forName 拿不到（实测 ClassNotFoundException）。
     * 也不能只靠 layout 监听：RecyclerView 滚动时走的是 offsetChildren，不重新 layout，
     * 只会补 attach 新 child（实测出现黑字压在深底上的漏项）。
     *
     * 所以用两层纯 View 的原生能力兜底：
     *   - ViewGroup.OnHierarchyChangeListener：child 一加进容器就上色；
     *   - OnPreDrawListener：每帧绘制前扫一遍，命中 DONE 的直接返回，成本可忽略。
     */
    private static void hookList(View rv, final boolean running) {
        try {
            if (rv instanceof ViewGroup) {
                ((ViewGroup) rv).setOnHierarchyChangeListener(
                        new ViewGroup.OnHierarchyChangeListener() {
                            @Override
                            public void onChildViewAdded(View parent, View child) {
                                if (running) {
                                    styleRunningItem(child);
                                } else {
                                    styleItem(child);
                                }
                            }

                            @Override
                            public void onChildViewRemoved(View parent, View child) {
                            }
                        });
            }
        } catch (Throwable t) {
            Log.w(TAG, "hierarchy listener failed", t);
        }
        try {
            final ViewGroup g = (rv instanceof ViewGroup) ? (ViewGroup) rv : null;
            rv.getViewTreeObserver().addOnPreDrawListener(
                    new ViewTreeObserver.OnPreDrawListener() {
                        @Override
                        public boolean onPreDraw() {
                            try {
                                if (g != null) {
                                    for (int i = 0; i < g.getChildCount(); i++) {
                                        if (running) {
                                            styleRunningItem(g.getChildAt(i));
                                        } else {
                                            styleItem(g.getChildAt(i));
                                        }
                                    }
                                }
                            } catch (Throwable ignored) {
                            }
                            return true;
                        }
                    });
            Log.i(TAG, "hooked recyclerview");
        } catch (Throwable t) {
            Log.w(TAG, "predraw hook failed", t);
        }
    }

    private static void styleItem(View item) {
        if (item == null || DONE.containsKey(item)) {
            return;
        }
        DONE.put(item, Boolean.TRUE);
        try {
            Activity a = sAct == null ? null : sAct.get();
            if (a == null) {
                return;
            }
            boolean header = item.findViewById(id(a, "text_header_name")) != null;

            if (header) {
                styleHeader(item, a);
                return;
            }

            // 卡片：圆角 + 半透明底 + 1px 描边，外面套 ripple
            GradientDrawable card = new GradientDrawable();
            card.setShape(GradientDrawable.RECTANGLE);
            card.setCornerRadius(dp(a, 18));
            card.setColor(cCard);
            card.setStroke(Math.max(1, dp(a, 0.7f)), cStroke);
            item.setBackground(new RippleDrawable(ColorStateList.valueOf(cRipple), card, null));
            item.setClipToOutline(false);

            ViewGroup.LayoutParams lp = item.getLayoutParams();
            if (lp instanceof ViewGroup.MarginLayoutParams) {
                ViewGroup.MarginLayoutParams m = (ViewGroup.MarginLayoutParams) lp;
                m.leftMargin = dp(a, 14);
                m.rightMargin = dp(a, 14);
                m.topMargin = dp(a, 6);
                m.bottomMargin = dp(a, 6);
                item.setLayoutParams(m);
            }

            tintText(item, a, "text_setting_name", cFg, -1);
            tintText(item, a, "text_setting_description", cSub, -1);
            tintText(item, a, "text_setting_value", cAccent, 1);

            View cb = item.findViewById(id(a, "checkbox"));
            if (cb != null) {
                Object o = cb;
                try {
                    Method m = cb.getClass().getMethod("setButtonTintList", ColorStateList.class);
                    m.invoke(o, checkboxTint());
                } catch (Throwable ignored) {
                }
            }
            View sb = item.findViewById(id(a, "seekbar"));
            if (sb != null) {
                try {
                    Method p = sb.getClass().getMethod("setProgressTintList", ColorStateList.class);
                    p.invoke(sb, ColorStateList.valueOf(cAccent));
                    Method t = sb.getClass().getMethod("setThumbTintList", ColorStateList.class);
                    t.invoke(sb, ColorStateList.valueOf(cAccent));
                } catch (Throwable ignored) {
                }
            }
        } catch (Throwable t) {
            Log.w(TAG, "styleItem failed", t);
        }
    }

    private static void styleHeader(View item, Activity a) {
        item.setBackgroundColor(Color.TRANSPARENT);
        ViewGroup.LayoutParams lp = item.getLayoutParams();
        if (lp instanceof ViewGroup.MarginLayoutParams) {
            ViewGroup.MarginLayoutParams m = (ViewGroup.MarginLayoutParams) lp;
            m.leftMargin = dp(a, 14);
            m.rightMargin = dp(a, 14);
            item.setLayoutParams(m);
        }
        View tv = item.findViewById(id(a, "text_header_name"));
        if (tv instanceof TextView) {
            TextView t = (TextView) tv;
            t.setTextColor(cAccent);
            t.setLetterSpacing(0.06f);     // 分组标题疏排一点，像真机的丝印
            t.setTextSize(12.5f);
            t.setAllCaps(true);
        }
    }

    private static void tintText(View parent, Activity a, String name, int color, int alpha) {
        View v = parent.findViewById(id(a, name));
        if (!(v instanceof TextView)) {
            return;
        }
        TextView t = (TextView) v;
        t.setTextColor(color);
        if (alpha > 0) {
            t.setAlpha(1f);
        }
    }

    private static ColorStateList checkboxTint() {
        int off = withAlpha(sDark ? 0xFFFFFFFF : 0xFF000000, 90);
        int[][] states = new int[][]{
                new int[]{android.R.attr.state_checked},
                new int[]{}
        };
        return new ColorStateList(states, new int[]{cAccent, off});
    }

    // ------------------------------------------------------------- 背景层

    /** 三个竖点，用来替换 ROM 那个不像「更多」的溢出图标 */
    private static final class MoreIcon extends Drawable {
        private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        private int color;

        MoreIcon(int color) {
            this.color = color;
            paint.setColor(color);
        }

        @Override
        public void draw(Canvas canvas) {
            Rect b = getBounds();
            float r = Math.min(b.width(), b.height()) * 0.085f;
            float cx = b.exactCenterX();
            float cy = b.exactCenterY();
            for (int i = -1; i <= 1; i++) {
                canvas.drawCircle(cx, cy + i * r * 3.4f, r, paint);
            }
        }

        @Override
        public void setAlpha(int alpha) {
            paint.setColor(color);
            paint.setAlpha(alpha);
        }

        @Override
        public void setColorFilter(ColorFilter cf) {
            paint.setColorFilter(cf);
        }

        @Override
        public int getOpacity() {
            return PixelFormat.TRANSLUCENT;
        }

        @Override
        public int getIntrinsicWidth() {
            return 72;
        }

        @Override
        public int getIntrinsicHeight() {
            return 72;
        }
    }

    /** 纵向渐变 + 顶部柔光。两层 shader 一次画完，滚动时零分配。 */
    private static final class ShellBg extends Drawable {
        private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final int top;
        private final int bot;
        private final int glow;
        private Shader base;
        private Shader halo;
        private int lastW = -1;
        private int lastH = -1;

        ShellBg(int top, int bot, int glow) {
            this.top = top;
            this.bot = bot;
            this.glow = glow;
        }

        private void ensure(Rect b) {
            if (b.width() == lastW && b.height() == lastH) {
                return;
            }
            lastW = b.width();
            lastH = b.height();
            base = new LinearGradient(0, 0, 0, b.height(),
                    new int[]{top, mid(top, bot, 0.55f), bot}, null, Shader.TileMode.CLAMP);
            halo = new RadialGradient(b.width() * 0.5f, -b.height() * 0.06f,
                    Math.max(1f, b.height() * 0.52f),
                    glow, withAlpha(glow, 0), Shader.TileMode.CLAMP);
        }

        @Override
        public void draw(Canvas canvas) {
            Rect b = getBounds();
            ensure(b);
            paint.setShader(base);
            canvas.drawRect(b, paint);
            paint.setShader(halo);
            canvas.drawRect(b, paint);
            paint.setShader(null);
        }

        @Override
        public void setAlpha(int alpha) {
            paint.setAlpha(alpha);
        }

        @Override
        public void setColorFilter(ColorFilter cf) {
            paint.setColorFilter(cf);
        }

        @Override
        public int getOpacity() {
            return PixelFormat.OPAQUE;
        }
    }

    // --------------------------------------------------------------- 工具

    private static int id(Activity a, String name) {
        return a.getResources().getIdentifier(name, "id", a.getPackageName());
    }

    private static int idOf(android.content.Context ctx, String name) {
        return ctx.getResources().getIdentifier(name, "id", ctx.getPackageName());
    }

    private static int dp(android.content.Context ctx, float v) {
        return Math.round(v * ctx.getResources().getDisplayMetrics().density);
    }

    private static int dp(Activity a, float v) {
        return Math.round(v * a.getResources().getDisplayMetrics().density);
    }

    private static int withAlpha(int color, int alpha) {
        return (color & 0x00FFFFFF) | ((alpha & 0xFF) << 24);
    }

    private static int mid(int a, int b, float t) {
        int r = (int) (Color.red(a) + (Color.red(b) - Color.red(a)) * t);
        int g = (int) (Color.green(a) + (Color.green(b) - Color.green(a)) * t);
        int bl = (int) (Color.blue(a) + (Color.blue(b) - Color.blue(a)) * t);
        return Color.rgb(r, g, bl);
    }

    /** RGB → HSL，h 0..360，s/l 0..1 */
    private static float[] toHsl(int color) {
        float r = Color.red(color) / 255f;
        float g = Color.green(color) / 255f;
        float b = Color.blue(color) / 255f;
        float max = Math.max(r, Math.max(g, b));
        float min = Math.min(r, Math.min(g, b));
        float l = (max + min) / 2f;
        float h;
        float s;
        if (max == min) {
            h = 0;
            s = 0;
        } else {
            float d = max - min;
            s = l > 0.5f ? d / (2f - max - min) : d / (max + min);
            if (max == r) {
                h = (g - b) / d + (g < b ? 6f : 0f);
            } else if (max == g) {
                h = (b - r) / d + 2f;
            } else {
                h = (r - g) / d + 4f;
            }
            h *= 60f;
        }
        return new float[]{h, s, l};
    }

    private static int fromHsl(float h, float s, float l) {
        h = ((h % 360f) + 360f) % 360f;
        float c = (1f - Math.abs(2f * l - 1f)) * s;
        float x = c * (1f - Math.abs((h / 60f) % 2f - 1f));
        float m = l - c / 2f;
        float r;
        float g;
        float b;
        if (h < 60) {
            r = c; g = x; b = 0;
        } else if (h < 120) {
            r = x; g = c; b = 0;
        } else if (h < 180) {
            r = 0; g = c; b = x;
        } else if (h < 240) {
            r = 0; g = x; b = c;
        } else if (h < 300) {
            r = x; g = 0; b = c;
        } else {
            r = c; g = 0; b = x;
        }
        return Color.rgb(clamp255((r + m) * 255f),
                clamp255((g + m) * 255f), clamp255((b + m) * 255f));
    }

    private static int clamp255(float v) {
        int i = Math.round(v);
        return i < 0 ? 0 : (i > 255 ? 255 : i);
    }

    private static void setLightBars(Window w, boolean light) {
        if (Build.VERSION.SDK_INT < 23) {
            return;
        }
        try {
            View d = w.getDecorView();
            int flags = d.getSystemUiVisibility();
            if (light) {
                flags |= View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR;
            } else {
                flags &= ~View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR;
            }
            d.setSystemUiVisibility(flags);
        } catch (Throwable ignored) {
        }
    }
}
