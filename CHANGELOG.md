# Changelog

All notable changes to Ctria Hope. Version names follow the APK's `versionName`;
`versionCode` is given because Android uses it for upgrade decisions.

## [1.3.0] — unreleased

Repository publication release.

- **Fixed:** the in-app "Source code", "Licenses" and "Latest version" links pointed at a
  repository that did not exist. They now point here, so the GPL-2.0 §3 source offer
  actually resolves.
- **Fixed:** the update check queried the upstream Citra MMJ releases API and would have
  offered users a download of a *different* emulator. It now queries this repository.
- **Changed:** signing key subject is `CN=Ctria Hope` (was `CN=Hinge Adapt`) for new
  keystores. Existing keystores keep working — the certificate, not the subject, is what
  Android checks.
- **Build:** keystore password is no longer hard-coded in `build.sh`; it comes from
  `$KS_PASS`.

## [1.2.0] — 2026-11-12

GPL compliance release.

- **Added:** four license files inside the APK (`assets/licenses/`): project/attribution
  notice, full GPL-2.0 text, and the two bundled MIT texts. GPL-2.0 §1 requires the
  license to travel with the binary; earlier builds shipped only the MIT texts.
- **Changed:** About screen — the dead `citra-emu.org` link (the project shut down in
  March 2024) and the unrelated Weibo link were replaced by "Source code (GPL-2.0)" and
  "Licenses".
- **Changed:** panel skin silk print is `Fun in Hope`; no Nintendo wordmark anywhere in
  the artwork.

## [1.1.5] — 2026-11-12

AppGallery compatibility release. Nothing visual changed.

- **Changed:** `targetSdkVersion` 29 → 34.
- **Added:** `MANAGE_EXTERNAL_STORAGE`, and a first-launch gate that deep-links to the
  system "all files access" screen and recreates the activity on return.
- **Fixed:** with `targetSdk 34`, apps lose write access to shared storage, so themes,
  bundled games and the control layout could not be provisioned — a fresh install showed
  an empty list while an upgrade appeared fine (native code could still write). The gate
  closes that hole.
- **Fixed:** `isExternalStorageLegacy()` is a compile-time constant `false` at
  `targetSdk ≥ 30`, which made the app choose a different data directory; the path
  resolver is pinned to `citra-emu/` explicitly.
- **Fixed:** with the permission ungranted, `WallpaperManager.getDrawable()` returns null
  and the theme fell back to Citra orange; the fallback palette is now a neutral deep
  indigo, and low-saturation wallpapers no longer have their hue forced to orange.

## [1.0.3] — 2026-11-12

- **Fixed:** every touch control was mispositioned. The calibrated `input-layout.ini` had
  never been packaged — it was pushed by hand during development, so users got the
  upstream default layout. It now ships in `assets/config/` and is written to
  `citra-emu/config/` on first launch.
- **Added:** overwrite policy for that file — replace it when missing, still the upstream
  default, or clearly truncated; never overwrite a user-modified file.

## [1.0.2] — 2026-11-12

- **Fixed:** launch crash (`Activity.performResume → JNI → libmain.so → SIGSEGV`). The
  root cause was a native call made from `onResume` *before* `invoke-super`, i.e. before
  the native config object existed. No native calls remain in that phase.
- **Added:** provisioning trace at `citra-emu/bg-diag.txt` and palette trace at
  `citra-emu/skin-diag.txt`, because vendor ROMs suppress third-party logcat output.

## [1.0.1] — 2026-11-12

- **Removed:** bundled Flappy Bird — its screen orientation was rotated on this device.
- **Changed:** game directory unified to `citra-emu/Games`; an existing lowercase `games`
  folder is migrated on first launch, together with anything the user put in it.
- **Added:** the eight panel themes are packaged in the APK and extracted to
  `citra-emu/theme/` on first launch. A user who never picked a theme defaults to
  `aqua-blue`; an existing choice is respected.

## [1.0.0] — 2026-11-09

First installable build.

- Hinge-aware dual-screen layout for the 1828 × 2584 inner display.
- Wallpaper-derived theming for Settings, dialogs and the in-game running-settings dialog.
- Eight procedurally rendered panel skins.
- Bundled homebrew (T-Rex, 2048) so the list is never empty.
