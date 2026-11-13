package org.citra.emu;

import android.app.Activity;
import android.content.Context;
import android.content.SharedPreferences;
import android.os.Build;
import android.os.Environment;
import android.util.Log;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.lang.reflect.Field;
import java.util.ArrayList;
import java.util.List;

/**
 * 把随包的免费开源家用机游戏（.3dsx）释放到存储卡并登记进游戏库。
 *
 * 分两步，缺一不可：
 *   ensure()    —— onCreate 最开头（super 之前）释放文件，早于任何 UI 扫描；
 *   onResumed() —— onResume 里（super 之后）写配置 + 触发一次列表刷新。
 *
 * 为什么必须这么分（真机实测结论）：
 *   1. 游戏列表由 MainActivity$e 这个 AsyncTask 扫描目录生成，扫描读的是 native 的
 *      game_storage_path 配置；native 配置在 onCreate 阶段还没加载（getConfigString 返回空），
 *      所以在 onCreate 里 setConfigString 白费，必须等 onResume。
 *   2. 光写配置不会刷新列表，必须调用 MainActivity.t0()（下拉刷新走的同一个方法）。
 *      t0 是混淆名，只能用反射，避免和 smali 耦合。
 *
 * 游戏取自各项目 GitHub Release 的原始产物，代码与素材均为项目原创，MIT 许可，
 * 许可证全文随包附带（assets/free-games/LICENSES.txt）。
 * 另外把 8 套面板主题（assets/themes/*.zip）解到 citra-emu/theme/，装完即有皮肤。
 *
 * 硬性约束：永不抛异常（onCreate 里抛出去就是启动闪退）。
 */
public final class BundledGames {

    private static final String TAG = "BundledGames";
    private static final String PREFS = "bundled_games";
    /** v4：游戏目录从 games 改成 Games，key 跟着换，老设备会自动重算并迁移 */
    private static final String KEY_DIR = "dir_v5";
    private static final String KEY_CONFIGURED = "configured_v4";
    private static final String GAMES_DIR = "Games";
    private static final String LEGACY_GAMES_DIR = "games";
    private static final String THEME_DIR = "theme";
    private static final String DEFAULT_THEME = "aqua-blue";
    /** 上游默认布局的指纹；命中说明用户还没用上我们标定的按键位置，可以安全覆盖 */
    private static final String STOCK_LAYOUT_MARK = "button_l_portrait=-90,40,100";

    private BundledGames() {
    }

    // ------------------------------------------------------------ 第一步：释放

    /** 释放随包游戏到存储卡。幂等，文件已存在就只做几次 stat。 */
    public static void ensure(Context context) {
        dbg("=== ensure enter ===");
        try {
            Context app = context.getApplicationContext();
            SharedPreferences sp = app.getSharedPreferences(PREFS, Context.MODE_PRIVATE);

            File dir = null;
            String saved = sp.getString(KEY_DIR, null);
            if (saved != null) {
                File f = new File(saved);
                if (f.isDirectory() && new File(f, "TRexGame.3dsx").isFile()) {
                    dir = f;
                }
            }
            if (dir == null) {
                dir = preferDir(app);
                if (dir != null) {
                    sp.edit().putString(KEY_DIR, dir.getAbsolutePath()).apply();
                }
            }
            dbg("dir=" + dir);
            if (dir == null) {
                return;
            }
            if (!dir.isDirectory() && !dir.mkdirs()) {
                dbg("mkdir failed");
                return;
            }

            String[] assets;
            try {
                assets = app.getAssets().list("free-games");
            } catch (Throwable t) {
                dbg("list assets failed: " + t);
                return;
            }
            if (assets == null) {
                return;
            }
            for (String name : assets) {
                if (!name.endsWith(".3dsx")) {
                    continue;
                }
                File out = new File(dir, name);
                if (out.isFile() && out.length() > 0) {
                    continue;
                }
                if (copyAsset(app, "free-games/" + name, out)) {
                    dbg("copied " + name + " (" + out.length() + "B)");
                }
            }
            extractThemes(app);
            ensureLayout(app);
        } catch (Throwable t) {
            dbg("ensure failed: " + t);
            Log.w(TAG, "ensure failed", t);
        }
    }

    /**
     * 是否已获得「所有文件访问权限」。
     *
     * 有它就完全不需要再靠 createNewFile 试探写权限 —— 实测这个试探在授权刚生效时
     * 会假失败，把游戏目录判到 Android/data/.../files/Games，用户看到的就是空列表。
     * 反射调用是因为编译用的 android.jar 版本低于 API 30。
     */
    private static boolean hasAllFiles() {
        try {
            if (Build.VERSION.SDK_INT < 30) {
                return false;
            }
            java.lang.reflect.Method m = Environment.class.getMethod("isExternalStorageManager");
            Object r = m.invoke(null);
            return r instanceof Boolean && (Boolean) r;
        } catch (Throwable t) {
            return false;
        }
    }

    /**
     * 游戏目录：统一用 citra-emu/Games（与用户在文件管理器里看到的目录名一致）。
     *
     * 老版本用的是小写 games，这里做一次就地迁移，省得用户重装后列表变空：
     *   - 只有老目录   → 整目录改名
     *   - 两个都有     → 把老目录里的文件并过去，再删空的
     * 用户自己塞进 games 的 ROM 也会一起搬过来。
     */
    private static File preferDir(Context app) {
        try {
            File sd = Environment.getExternalStorageDirectory();
            if (sd != null) {
                File root = new File(sd, "citra-emu");
                File dir = new File(root, GAMES_DIR);
                File legacy = new File(root, LEGACY_GAMES_DIR);
                if (legacy.isDirectory()) {
                    if (!dir.exists()) {
                        if (legacy.renameTo(dir)) {
                            dbg("migrated games -> Games (rename)");
                        } else {
                            migrateDir(legacy, dir);
                        }
                    } else {
                        migrateDir(legacy, dir);
                    }
                }
                if (dir.isDirectory() || dir.mkdirs()) {
                    if (hasAllFiles()) {
                        dbg("preferDir: public (all-files granted) " + dir);
                        return dir;
                    }
                    // 没拿到特殊权限时才退化成写试探（部分 ROM 上 mkdirs 会假成功）
                    File probe = new File(dir, ".w");
                    boolean ok = false;
                    try {
                        ok = probe.createNewFile() || probe.isFile();
                        probe.delete();
                    } catch (Throwable t) {
                        dbg("probe failed: " + t);
                    }
                    dbg("preferDir: probe=" + ok + " -> " + dir);
                    if (ok) {
                        return dir;
                    }
                }
            }
        } catch (Throwable ignored) {
        }
        try {
            File dir = new File(app.getExternalFilesDir(null), GAMES_DIR);
            if (dir.isDirectory() || dir.mkdirs()) {
                dbg("preferDir: FALLBACK to app-private " + dir);
                return dir;
            }
        } catch (Throwable ignored) {
        }
        dbg("preferDir: no writable dir");
        return null;
    }

    /** 把 src 里的文件逐个挪到 dst（同名以 dst 为准），挪完删掉空目录 */
    private static void migrateDir(File src, File dst) {
        try {
            if (!dst.isDirectory() && !dst.mkdirs()) {
                return;
            }
            File[] kids = src.listFiles();
            if (kids != null) {
                for (File k : kids) {
                    File to = new File(dst, k.getName());
                    if (!to.exists() && !k.renameTo(to)) {
                        if (k.isFile()) {
                            copyFile(k, to);
                            k.delete();
                        }
                    }
                }
            }
            File[] left = src.listFiles();
            if (left != null && left.length == 0) {
                src.delete();
                dbg("removed empty legacy dir");
            }
        } catch (Throwable t) {
            dbg("migrateDir failed: " + t);
        }
    }

    private static void copyFile(File from, File to) {
        InputStream in = null;
        OutputStream os = null;
        try {
            in = new FileInputStream(from);
            os = new FileOutputStream(to);
            byte[] buf = new byte[64 * 1024];
            int n;
            while ((n = in.read(buf)) > 0) {
                os.write(buf, 0, n);
            }
        } catch (Throwable t) {
            dbg("copyFile " + from.getName() + " failed: " + t);
        } finally {
            try {
                if (in != null) {
                    in.close();
                }
            } catch (Throwable ignored) {
            }
            try {
                if (os != null) {
                    os.close();
                }
            } catch (Throwable ignored) {
            }
        }
    }

    /**
     * 按键布局：把随包标定好的 input-layout.ini 落到 /sdcard/citra-emu/config/。
     *
     * 为什么必须有这一步：这个文件不在 native 的首启拷贝清单里，1.0.0 之前一直靠
     * push_all.sh 手工 adb push，用户自己装就只会拿到上游默认布局（L/R 位置完全不对）。
     *
     * 覆盖策略：文件不存在、或内容还是上游默认（指纹命中）、或小得离谱 → 用我们的；
     * 用户改过的就不动，避免把人家手调的布局冲掉。
     */
    private static void ensureLayout(Context app) {
        try {
            File sd = Environment.getExternalStorageDirectory();
            if (sd == null) {
                return;
            }
            File cfg = new File(new File(sd, "citra-emu"), "config");
            if (!cfg.isDirectory() && !cfg.mkdirs()) {
                return;
            }
            File ini = new File(cfg, "input-layout.ini");
            boolean need = !ini.isFile() || ini.length() < 512 || looksStock(ini);
            if (!need) {
                dbg("layout kept (user modified)");
                return;
            }
            if (copyAsset(app, "config/input-layout.ini", ini)) {
                dbg("layout installed (" + ini.length() + "B)");
            }
        } catch (Throwable t) {
            dbg("ensureLayout failed: " + t);
        }
    }

    private static boolean looksStock(File f) {
        BufferedReader r = null;
        try {
            r = new BufferedReader(new InputStreamReader(new FileInputStream(f), "UTF-8"));
            String line;
            while ((line = r.readLine()) != null) {
                if (line.contains(STOCK_LAYOUT_MARK)) {
                    return true;
                }
            }
        } catch (Throwable ignored) {
        } finally {
            try {
                if (r != null) {
                    r.close();
                }
            } catch (Throwable ignored) {
            }
        }
        return false;
    }

    /**
     * 把随包的 8 套面板主题解到 /sdcard/citra-emu/theme/。
     * 装完就有皮肤可选，不需要再用 adb 推。已存在且非空的跳过，用户自己换过的不会被覆盖。
     */
    private static void extractThemes(Context app) {
        try {
            File sd = Environment.getExternalStorageDirectory();
            if (sd == null) {
                return;
            }
            File dir = new File(new File(sd, "citra-emu"), THEME_DIR);
            if (!dir.isDirectory() && !dir.mkdirs()) {
                dbg("theme mkdir failed");
                return;
            }
            String[] names;
            try {
                names = app.getAssets().list("themes");
            } catch (Throwable t) {
                dbg("list themes failed: " + t);
                return;
            }
            if (names == null) {
                return;
            }
            int n = 0;
            for (String name : names) {
                if (!name.endsWith(".zip")) {
                    continue;
                }
                File out = new File(dir, name);
                if (out.isFile() && out.length() > 0) {
                    continue;
                }
                if (copyAsset(app, "themes/" + name, out)) {
                    n++;
                }
            }
            dbg("themes extracted: " + n + " -> " + dir);
        } catch (Throwable t) {
            dbg("extractThemes failed: " + t);
        }
    }

    private static boolean copyAsset(Context context, String name, File out) {
        InputStream in = null;
        OutputStream os = null;
        try {
            in = context.getAssets().open(name);
            os = new FileOutputStream(out);
            byte[] buf = new byte[64 * 1024];
            int n;
            while ((n = in.read(buf)) > 0) {
                os.write(buf, 0, n);
            }
            return true;
        } catch (Throwable t) {
            dbg("copy " + name + " failed: " + t);
            return false;
        } finally {
            try {
                if (in != null) {
                    in.close();
                }
            } catch (Throwable ignored) {
            }
            try {
                if (os != null) {
                    os.close();
                }
            } catch (Throwable ignored) {
            }
        }
    }

    // ------------------------------------------------------------ 第二步：登记 + 刷新

    /**
     * onResume 最开头调（**super 之前**）。
     *
     * 主界面 onResume 里有这么一段：`if (this.s != null) { C = 0; new MainActivity$e(this, s).execute(FALSE); s = null; }`
     * —— 也就是「拿到一个新目录 → 扫一遍 → 刷列表」。s 是私有字段，我们在这里填上内置游戏目录，
     * 原生流程就会替我们扫描并刷新，不需要自己造 AsyncTask、也不依赖列表 adapter 是否就绪。
     */
    public static void onResumeBegin(Activity activity) {
        try {
            final Context app = activity.getApplicationContext();
            final SharedPreferences sp = app.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
            String path = sp.getString(KEY_DIR, null);
            if (path == null) {
                return;
            }
            if (!new File(path).isDirectory()) {
                return;
            }

            // 只写配置文件，绝不在这里碰 NativeLibrary。
            //
            // 为什么（真机崩溃栈证据）：本方法注入在 onResume 的 invoke-super **之前**，
            // 此时 native 侧配置对象还没建好，任何 getConfigString / saveConfig 都会
            // 在 libmain.so 里空指针（Activity.performResume → JNI → SIGSEGV fault addr 0x0）。
            // ini 写完，下次冷启动 native 自己会读；本次列表靠下面的反射字段刷新。
            if (!sp.getBoolean(KEY_CONFIGURED, false)) {
                writeIni(path);
                sp.edit().putBoolean(KEY_CONFIGURED, true).apply();
            }

            // 每次启动都交给主界面扫一遍：这样即使 kill 过进程，列表也是齐的
            Field f = activity.getClass().getDeclaredField("s");
            f.setAccessible(true);
            f.set(activity, path);
            dbg("queued scan: " + path);
        } catch (Throwable t) {
            dbg("onResumeBegin failed: " + t);
            Log.w(TAG, "onResumeBegin failed", t);
        }
    }

    /** 把新目录并进已有的分号列表；父目录已覆盖就不重复加 */
    private static String merge(String existing, String dirPath) {
        StringBuilder sb = new StringBuilder();
        boolean covered = false;
        if (existing != null) {
            for (String s : existing.split(";")) {
                if (s.isEmpty()) {
                    continue;
                }
                sb.append(s).append(';');
                if (s.equals(dirPath) || dirPath.startsWith(s.endsWith("/") ? s : s + "/")) {
                    covered = true;
                }
            }
        }
        if (!covered) {
            sb.append(dirPath).append(';');
        }
        return sb.toString();
    }

    /**
     * 兜底：直接改 config-mmj.ini。
     * native 的 saveConfig() 在配置未就绪时会 SIGSEGV 把进程干掉（onCreate 阶段实测），
     * 这里再写一遍文件，保证下次启动一定读得到。
     */
    private static void writeIni(String dirPath) {
        try {
            File sd = Environment.getExternalStorageDirectory();
            if (sd == null) {
                return;
            }
            File configDir = new File(new File(sd, "citra-emu"), "config");
            if (!configDir.isDirectory() && !configDir.mkdirs()) {
                return;
            }
            File ini = new File(configDir, "config-mmj.ini");
            List<String> lines = new ArrayList<String>();
            if (ini.isFile()) {
                BufferedReader r = new BufferedReader(
                        new InputStreamReader(new FileInputStream(ini), "UTF-8"));
                String line;
                while ((line = r.readLine()) != null) {
                    lines.add(line);
                }
                r.close();
            }
            int keyAt = -1;
            int coreAt = -1;
            for (int i = 0; i < lines.size(); i++) {
                String t = lines.get(i).trim();
                if (keyAt < 0 && t.startsWith("game_storage_path")) {
                    keyAt = i;
                }
                if (coreAt < 0 && t.equalsIgnoreCase("[Core]")) {
                    coreAt = i;
                }
            }
            if (keyAt >= 0) {
                String old = lines.get(keyAt);
                String val = old.indexOf('=') >= 0 ? old.substring(old.indexOf('=') + 1).trim() : "";
                lines.set(keyAt, "game_storage_path = " + merge(val, dirPath));
            } else if (coreAt >= 0) {
                lines.add(coreAt + 1, "game_storage_path = " + dirPath + ";");
            } else {
                if (!lines.isEmpty()) {
                    lines.add("");
                }
                lines.add("[Core]");
                lines.add("game_storage_path = " + dirPath + ";");
            }

            // 主题：用户没选过（值为空）才写默认值，选过的绝不覆盖
            int themeAt = -1;
            for (int i = 0; i < lines.size(); i++) {
                if (lines.get(i).trim().startsWith("theme_package")) {
                    themeAt = i;
                    break;
                }
            }
            if (themeAt >= 0) {
                String old = lines.get(themeAt);
                String val = old.indexOf('=') >= 0 ? old.substring(old.indexOf('=') + 1).trim() : "";
                if (val.isEmpty()) {
                    lines.set(themeAt, "theme_package = " + DEFAULT_THEME);
                }
            } else {
                for (int i = 0; i < lines.size(); i++) {
                    if (lines.get(i).trim().startsWith("game_storage_path")) {
                        lines.add(i + 1, "theme_package = " + DEFAULT_THEME);
                        break;
                    }
                }
            }
            StringBuilder sb = new StringBuilder();
            for (String line : lines) {
                sb.append(line).append('\n');
            }
            FileOutputStream os = new FileOutputStream(ini);
            os.write(sb.toString().getBytes("UTF-8"));
            os.close();
            dbg("ini ok");
        } catch (Throwable t) {
            dbg("ini failed: " + t);
        }
    }

    // ------------------------------------------------------------ 调试

    private static void dbg(String msg) {
        Log.i(TAG, msg);
        // EMUI 会过滤第三方应用的 logcat，排查期同时落一份文件
        try {
            java.io.File dir = new java.io.File(
                    Environment.getExternalStorageDirectory(), "citra-emu");
            dir.mkdirs();
            java.io.FileWriter w = new java.io.FileWriter(
                    new java.io.File(dir, "bg-diag.txt"), true);
            w.write(new java.text.SimpleDateFormat("HH:mm:ss", java.util.Locale.US)
                    .format(new java.util.Date()) + "  " + msg + "\n");
            w.close();
        } catch (Throwable ignored) {
        }
    }

}
