# Changelog

All notable changes to Ctria Hope. Version names follow the APK's `versionName`;
`versionCode` is given because Android uses it for upgrade decisions.

## [1.4.0] — 2026-11-13

AppGallery compliance release. Every change below exists because a store review
requires it, not because the app needed it.

- **Removed the in-app update check.** Huawei's App Review Guidelines §3.9 forbid an
  app from updating itself or pulling code from another source, and the co-marketing
  agreement treats "link out to a non-Huawei distribution channel" as a fineable
  violation. The `Latest Version` row no longer runs an `AsyncTask`, no longer calls
  `api.github.com`, and no longer appears: the row now opens the privacy policy.
- **Privacy policy now ships inside the APK** (`assets/privacy/PRIVACY.txt`, English /
  Russian / Chinese) and is readable offline at **Settings → About → Privacy policy**.
  Reviews require the policy to be reachable, and require it to match the declared
  permissions line by line; a file in the package cannot 404.
- **Licenses open in-app** rather than in a browser (GPL-2.0 text plus the bundled MIT
  texts). The only remaining external link is the source-code offer, which is a licence
  obligation.
- **Renamed to Ctria Hope**: `android:label`, `app_name` and a new set of icons. The
  previous name and artwork were upstream Citra brand assets — GPL grants a code
  licence, not a trademark one.
- **Removed `android:isGame="true"` and `android:appCategory="game"`.** Declaring an
  emulator as a game routes it into the game category, which requires a publishing
  licence in mainland China and a different review track elsewhere. It is a tool.
- **First-run storage dialog localised** into English / Russian / Chinese; a permission
  prompt has to explain itself in the language of the market it ships to.
- **Removed a commercial game name** from an es-ES help string.

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
