package org.citra.emu;

/** 仅用于编译期：不与产物打包（真实实现由 libmain.so 提供） */
public final class NativeLibrary {
    public static native void setCustomLayout(boolean isTopScreen, int left, int top, int right, int bottom);
    public static native boolean IsRunning();
    public static native void WindowChanged();
    public static native void setConfigInteger(String key, int value);
    public static native void setConfigString(String key, String value);
    public static native String getConfigString(String key);
    public static native void saveConfig();
}
