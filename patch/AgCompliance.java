package org.citra.emu;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.util.TypedValue;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ScrollView;
import android.widget.TextView;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;

/**
 * AppGallery compliance hooks for the About screen.
 *
 * Why this class exists
 * ---------------------------------------------------------------------------
 * Huawei's App Review Guidelines forbid an app from updating itself or pointing
 * the user at a download channel outside AppGallery:
 *
 *   Guideline 3.9  an app must not bypass the review mechanism to update itself,
 *                  and must not download / install / execute code from other
 *                  sources that modifies the app.
 *   Co-marketing agreement: "self-upgrade to a non-Huawei channel package" or
 *                  "link out to a distribution platform other than Huawei" is a
 *                  fineable violation.
 *
 * Upstream Citra (and therefore this build) ships an About screen with a
 * "Latest Version" row that calls api.github.com and then offers the user a
 * GitHub download link. On AppGallery that single row is enough to be rejected.
 *
 * So the row is rebound here, at runtime, to something both compliant and more
 * useful: an in-app privacy policy. The license rows are rebound to in-app text
 * viewers as well, so the only remaining external link is the GPL-2.0 source
 * code offer, which is a licence obligation and cannot be removed.
 *
 * Everything is wrapped in try/catch: if the About layout ever changes shape,
 * the screen must still open, it just silently keeps upstream behaviour.
 */
public final class AgCompliance {

    private static final String PRIVACY_ASSET = "privacy/PRIVACY.txt";
    private static final String LICENSE_ASSET = "licenses/LICENSE.txt";
    private static final String GPL_ASSET = "licenses/GPL-2.0.txt";

    private AgCompliance() {
    }

    /** Called at the end of AboutActivity.onCreate(). */
    public static void apply(final Activity a) {
        bind(a, "btn_latest_version", "Privacy policy", PRIVACY_ASSET, null);
        bind(a, "btn_open_weibo", "Licenses (GPL-2.0)", LICENSE_ASSET, GPL_ASSET);
        // btn_official_website is left alone on purpose: it is the GPL-2.0
        // correspondence-of-source link, and removing it would break a licence
        // obligation. It points at a source repository, not at an APK download.
        hide(a, "latest_version_progress");
    }

    private static void bind(final Activity a, final String idName, final String title,
                             final String asset, final String asset2) {
        try {
            final View v = find(a, idName);
            if (v == null) {
                return;
            }
            retitle(v, title);
            v.setOnClickListener(new View.OnClickListener() {
                @Override
                public void onClick(View view) {
                    StringBuilder sb = new StringBuilder();
                    sb.append(read(a, asset));
                    if (asset2 != null) {
                        sb.append("\n\n\n").append(read(a, asset2));
                    }
                    show(a, title, sb.toString());
                }
            });
        } catch (Throwable t) {
            // never let a compliance tweak break the About screen
        }
    }

    private static View find(Activity a, String name) {
        try {
            int id = a.getResources().getIdentifier(name, "id", a.getPackageName());
            return id == 0 ? null : a.findViewById(id);
        } catch (Throwable t) {
            return null;
        }
    }

    private static void hide(Activity a, String name) {
        try {
            View v = find(a, name);
            if (v != null) {
                v.setVisibility(View.GONE);
            }
        } catch (Throwable t) {
        }
    }

    /** Replace the label of the row, and drop a stale version subtitle if present. */
    private static void retitle(View v, String title) {
        try {
            if (v instanceof TextView) {
                ((TextView) v).setText(title);
                return;
            }
            walk(v, title);
        } catch (Throwable t) {
        }
    }

    private static boolean walk(View v, String title) {
        if (v instanceof TextView) {
            ((TextView) v).setText(title);
            return true;
        }
        if (v instanceof ViewGroup) {
            ViewGroup g = (ViewGroup) v;
            for (int i = 0; i < g.getChildCount(); i++) {
                if (walk(g.getChildAt(i), title)) {
                    return true;
                }
            }
        }
        return false;
    }

    private static void show(Activity a, String title, String body) {
        try {
            TextView tv = new TextView((Context) a);
            int pad = (int) TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, 18,
                    a.getResources().getDisplayMetrics());
            tv.setPadding(pad, pad, pad, pad);
            tv.setTextSize(TypedValue.COMPLEX_UNIT_SP, 13);
            tv.setTextIsSelectable(true);
            tv.setText(body);

            ScrollView sv = new ScrollView((Context) a);
            sv.addView(tv);

            new AlertDialog.Builder((Context) a)
                    .setTitle(title)
                    .setView(sv)
                    .setPositiveButton("OK", null)
                    .show();
        } catch (Throwable t) {
        }
    }

    private static String read(Activity a, String asset) {
        InputStream in = null;
        try {
            in = a.getAssets().open(asset);
            ByteArrayOutputStream bos = new ByteArrayOutputStream();
            byte[] buf = new byte[8192];
            int n;
            while ((n = in.read(buf)) > 0) {
                bos.write(buf, 0, n);
            }
            return bos.toString("UTF-8");
        } catch (Throwable t) {
            return "(document unavailable)";
        } finally {
            try {
                if (in != null) {
                    in.close();
                }
            } catch (Throwable ignored) {
            }
        }
    }
}
