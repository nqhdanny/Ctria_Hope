package org.citra.emu;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.DialogInterface;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.provider.Settings;
import android.util.Log;

import java.lang.reflect.Method;

/**
 * 首启引导用户授予「所有文件访问权限」（MANAGE_EXTERNAL_STORAGE）。
 *
 * 为什么必须有这一步
 * ------------------------------------------------------------------------
 * targetSdk 提到 34 之后，实测（真机 + 落盘诊断）三件事同时成立：
 *
 *   1. Java 层写 /sdcard/citra-emu 被拦 —— BundledGames 释放主题、内置游戏、
 *      按键布局全部静默失败。新装用户会看到一个空列表和黑底灰键。
 *   2. WallpaperManager.getDrawable() 返回 null（未授权时），设置界面配色
 *      退化到兜底色，看起来和壁纸毫无关系。
 *   3. native 侧仍然能写（libcitra 走的是原始 fd），所以老用户升级时
 *      看不出问题，只有全新安装才暴露 —— 这个坑最容易漏。
 *
 * 授权之后三项同时恢复，已逐项实测。
 *
 * 这是「特殊权限」，没有运行时弹窗，只能跳系统设置页让用户手动打开。
 * 模拟器类应用（RetroArch 等）普遍采用同一做法，AppGallery 审核时需要
 * 在应用描述里说明用途：仅用于读取用户自备的游戏 ROM、存档与皮肤。
 */
public final class StorageGate {

    private static final String TAG = "StorageGate";

    /** API 30 常量，编译用的 android.jar 版本较低，这里写字符串常量 */
    private static final String ACTION_ALL_FILES =
            "android.settings.MANAGE_APP_ALL_FILES_ACCESS_PERMISSION";
    private static final String ACTION_ALL_FILES_LIST =
            "android.settings.MANAGE_ALL_FILES_ACCESS_PERMISSION";

    private static boolean sAsking = false;
    /** 用户从设置页返回后需要重启一次，让 onCreate 里的释放流程重跑 */
    private static boolean sPendingRestart = false;

    private StorageGate() {
    }

    /** 反射调用 Environment.isExternalStorageManager()，避免 compileSdk 过低编不过 */
    private static boolean granted() {
        if (Build.VERSION.SDK_INT < 30) {
            // Android 10 及以下没有这个权限概念，老逻辑够用
            return true;
        }
        try {
            Method m = Environment.class.getMethod("isExternalStorageManager");
            Object r = m.invoke(null);
            return r instanceof Boolean && (Boolean) r;
        } catch (Throwable t) {
            Log.w(TAG, "isExternalStorageManager unavailable", t);
            // 拿不到就当已授权，别把用户挡在门外
            return true;
        }
    }

    /** 在 MainActivity.onCreate 里调，位置要在 BundledGames.ensure() 之前 */
    public static void ensure(final Activity a) {
        if (a == null || granted()) {
            return;
        }
        if (sAsking) {
            return;
        }
        sAsking = true;
        try {
            new AlertDialog.Builder(a, android.R.style.Theme_DeviceDefault_Dialog_Alert)
                    .setTitle("File access required")
                    .setMessage("Citra keeps games, saves and themes in the"
                            + " \"citra-emu\" folder on your storage.\n\n"
                            + "On the next screen please allow access to manage all files,"
                            + " otherwise the game list and panel themes cannot be prepared.")
                    .setCancelable(false)
                    .setPositiveButton("Open settings", new DialogInterface.OnClickListener() {
                        @Override
                        public void onClick(DialogInterface d, int which) {
                            openSettings(a);
                        }
                    })
                    .setNegativeButton("Later", new DialogInterface.OnClickListener() {
                        @Override
                        public void onClick(DialogInterface d, int which) {
                            sAsking = false;
                        }
                    })
                    .show();
        } catch (Throwable t) {
            Log.w(TAG, "dialog failed", t);
            sAsking = false;
            openSettings(a);
        }
    }

    /** 从系统设置页回来后调；已授权就重启一次，让资源释放流程重跑 */
    public static void onResume(final Activity a) {
        if (a == null) {
            return;
        }
        sAsking = false;
        if (!sPendingRestart) {
            return;
        }
        if (!granted()) {
            return;
        }
        sPendingRestart = false;
        try {
            a.recreate();
        } catch (Throwable t) {
            Log.w(TAG, "recreate failed", t);
        }
    }

    private static void openSettings(Activity a) {
        sPendingRestart = true;
        try {
            Intent i = new Intent(ACTION_ALL_FILES);
            i.setData(Uri.parse("package:" + a.getPackageName()));
            a.startActivity(i);
        } catch (Throwable t) {
            // 部分 ROM 不认带包名的 action，退到列表页
            try {
                a.startActivity(new Intent(ACTION_ALL_FILES_LIST));
            } catch (Throwable t2) {
                try {
                    a.startActivity(new Intent(
                            Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                            Uri.parse("package:" + a.getPackageName())));
                } catch (Throwable t3) {
                    Log.w(TAG, "cannot open storage settings", t3);
                }
            }
        }
    }
}
