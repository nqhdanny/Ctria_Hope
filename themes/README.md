# Panel themes

Eight skins for the foldable layout. Each `.zip` is a complete Citra theme package
(39 files) rendered by `../patch/skins_panel.py` from the six-colour palettes in
`../patch/skins_design.py`.

| Theme | Character |
|---|---|
| `aqua-blue` | translucent water blue, the default for a fresh install |
| `coral-pink` | warm coral body, cream buttons |
| `cosmo-black` | black body, white markings, high contrast |
| `flare-red` | red body, dark recesses |
| `galaxy` | deep purple with a star gradient |
| `ice-white` | white body, pale grey recesses |
| `metallic-blue` | brushed blue metal |
| `snes` | grey body, purple accents, four-colour ABXY |

## Install

Themes ship inside the APK and are extracted to `citra-emu/theme/` on first launch, so
normally there is nothing to do. To add or replace one by hand:

```bash
adb push aqua-blue.zip /sdcard/citra-emu/theme/
```

Then pick it in **Settings → Core → Theme**, or set `theme_package = aqua-blue` in
`citra-emu/config/config-mmj.ini` and restart.

## Why the artwork is generated, not drawn

The panel has to line up with two independently placed screen rectangles, a hinge barrel
at a measured y coordinate, and button recesses that sit exactly where the touch controls
land. Hand-drawn bitmaps drift out of alignment the moment a layout constant changes; a
renderer cannot. Palettes are six values per skin, so adding a ninth theme is a table row,
not a design job.

All artwork is original to this project — no third-party imagery, no console wordmark. The
silk print on the lower shell reads `Fun in Hope`.

## Re-render

```bash
cd ../patch && python3 gen_theme.py     # rewrites ../themes/*.zip
```

Requires Pillow and numpy. If you changed anything in `HingeHelper.java`, you must
re-render — the skins are bitmaps of the same geometry.
