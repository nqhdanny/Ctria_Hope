# Building Ctria Hope

This build is produced by **decompiling a released Citra MMJ APK, injecting patches, and
repacking**. It is not compiled from the C++ tree — that would be a different project.
Everything below reproduces the shipped APK from the base package identified in
[`../NOTICE.md`](../NOTICE.md) §2.

## 1. Prerequisites

| Component | Version | Used for |
|---|---|---|
| JDK | 17 | compiling the patch classes, `keytool`, `apksigner` |
| Android SDK build-tools | 34.0.0 | `d8`, `zipalign`, `apksigner`, `aapt2` |
| Android platform | `android-34` `android.jar` | classpath for `javac` / `d8` |
| apktool | 2.9.x (`apktool.jar`) | decode / rebuild |
| Python | 3.8+ | injection scripts |
| Pillow + numpy | current | only if you re-render the panel skins |
| Base APK | Citra MMJ `3eb22034a` (versionCode 3932) | the thing being patched |

## 2. Working directory layout

```bash
mkdir -p ~/hinge && cd ~/hinge
cp /path/to/base.apk .
java -jar apktool.jar d -f -s base.apk -o dec      # -s: keep classes.dex as-is
cp -r /path/to/Ctria_Hope/patch        ./patch
cp -r /path/to/Ctria_Hope/themes       ./themes
cp -r /path/to/Ctria_Hope/free-games   ./free-games
cp -r /path/to/Ctria_Hope/licenses     ./licenses
cp /path/to/apktool.jar                ./apktool.jar
```

`dec/classes.dex` must stay untouched. Every modification lives in the patched smali, the
patched manifest/resources, or the appended `classes2.dex`. That is what keeps rebuilds
diffable and reproducible.

## 3. Build

```bash
export JAVA_HOME=/path/to/jdk-17
export ANDROID_HOME=/path/to/android-sdk
export KS_PASS='choose-a-password'          # optional, see §5
bash patch/build.sh                          # -> ./citra-hinge.apk
```

What the script does, in order:

| Step | Action |
|---|---|
| 1 | `javac --release 8` compiles `HingeHelper`, `BundledGames`, `StorageGate`, `SettingsSkin` against two stubs (`NativeLibrary`, `InputOverlay`) that exist only to satisfy the compiler |
| 2 | `d8 --min-api 24` converts those classes to `work/dex/classes.dex`, excluding the stubs |
| 3 | Clears stale assets, then copies `free-games/*.3dsx`, `themes/*.zip`, `input-layout.ini`, `config-mmj.ini` into `dec/assets/` |
| 4 | `gen_licenses.py` writes the four license files into `dec/assets/licenses/` |
| 5 | Ten idempotent injectors patch the manifest, smali call sites, styles and the About screen |
| 6 | `apktool b dec` repacks |
| 7 | The patch dex is appended to the zip as `classes2.dex` |
| 8 | `zipalign -p 4`, then `apksigner sign` (v1+v2) |

Every `patch_*.py` first strips its own previous block, then re-inserts it. Re-running the
whole script any number of times produces the same tree.

## 4. Verifying a build

```bash
BT=$ANDROID_HOME/build-tools/34.0.0
$BT/aapt2 dump badging citra-hinge.apk | head -6      # package / versionCode / targetSdk
$BT/aapt2 dump permissions citra-hinge.apk           # must match PRIVACY.md
$BT/apksigner verify --print-certs citra-hinge.apk | head -3
unzip -l citra-hinge.apk | grep -E 'licenses/|free-games/|themes/' | head
sha256sum citra-hinge.apk
```

Expected: `targetSdkVersion 34`, ten permissions (see `PRIVACY.md`), four files under
`assets/licenses/`, two `.3dsx` files, eight theme zips.

## 5. Signing

The script generates a keystore on first run if `$KS_FILE` (default `hinge.jks`) does not
exist, using `$KS_PASS` (default `ctria-hope-dev`).

> **Do not ship a build signed with the default password.** Set `KS_PASS`, and keep the
> keystore out of version control — `.gitignore` already excludes `*.jks`.
>
> Android identifies an app by package name **and** signing certificate. Losing the
> keystore means you can never publish an update to existing users; leaking it means
> someone else can. Back it up somewhere safe and private.

## 6. Re-rendering the themes

```bash
cd patch
python3 gen_theme.py        # -> ../themes/*.zip, eight skins x 39 files
```

Palettes live in `skins_design.py` (six colours per skin). Geometry that has to match the
device — screen apertures, button centres, silk print position — lives in
`skins_panel.py` and **must stay in sync with `HingeHelper.java`**; the panel is a
rendered bitmap, so if the layout constants change without re-rendering, the artwork and
the live picture drift apart.

## 7. Installing for testing

```bash
adb install -r citra-hinge.apk
adb shell am start -n com.ctriahope.emu/org.citra.emu.ui.MainActivity
adb logcat -c && adb logcat | grep -Ei 'citra|hinge|AndroidRuntime'
```

On a first install, grant the all-files-access prompt. To inspect what the app wrote:

```bash
adb shell cat /sdcard/citra-emu/bg-diag.txt     # provisioning trace
adb shell cat /sdcard/citra-emu/skin-diag.txt   # wallpaper palette trace
adb shell ls /sdcard/citra-emu/Games /sdcard/citra-emu/theme
```

Note that some vendor ROMs (EMUI among them) suppress third-party app output in `logcat`.
That is why the two diagnosis files above are written to disk instead — when a device
looks like it "did nothing", read the files, not the log.
