package org.citra.emu.overlay;

import android.content.Context;
import android.view.View;

/**
 * 编译期占位类，仅用于让 HingeHelper 通过 javac。
 * 运行时链接到 APK 里真正的 InputOverlay（该类被混淆过，方法名是 j()）。
 * 本文件不进产物 dex。
 */
public class InputOverlay extends View {
    public InputOverlay(Context context) {
        super(context);
    }

    /** 真机包里的 refreshControls，混淆后名为 j() */
    public void j() {
    }
}
