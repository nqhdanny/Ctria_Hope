# Layout & control calibration

Everything in this document was measured on a HUAWEI Pura X Max (`HOP-LX9`), inner
display **1828 × 2584 @ 440 dpi**, portrait, hinge crease centred at **y ≈ 1292**.

## 1. The geometry problem

The 3DS top screen is 400 × 240, i.e. **5:3**. The bottom screen is 320 × 240, **4:3**,
and it is the touch surface. On a 1828 × 2584 panel you cannot give both their native
aspect and keep them adjacent — the fold is in the middle, and the touch surface has to
end up where thumbs actually reach, which is the lower third, not the exact middle.

Ctria Hope therefore does not scale the pair as one image. It places two independent
rectangles:

| Screen | Rectangle (left, top, right, bottom) | Size | Aspect |
|---|---|---|---|
| Top (game picture) | `28, 212, 1800, 1275` | 1772 × 1063 | ≈ 5:3 |
| Bottom (touch surface) | `410, 1380, 1402, 2124` | 992 × 744 | ≈ 4:3 |

with a hard constraint that the picture stops **58 px above the crease** (`1275 + 58 =
1333`, crease at 1292 measured including the panel's dead band) so the fold line never
cuts through the image.

The horizontal budget on the bottom screen, in full:

```
15 | 366 | 14 | 15 | 992 | 15 | 14 | 382 | 15  =  1828
```

That 366 px gutter is not padding — it is where the D-pad, circle pad and ABXY cluster
live, which is why the touch screen keeps its native aspect instead of being stretched to
the full width.

## 2. Constants

All of them are ratios of the real display metrics, so the layout degrades gracefully on
other foldables instead of hard-coding pixels.

| Constant | Value | Meaning | On this device |
|---|---|---|---|
| `SIDE_MARGIN_RATIO` | 0.1855 | left/right gutter for the bottom screen | 366 px |
| `BOT_WIDTH_FILL` | 0.86336 | bottom screen width relative to available width | 992 px |
| `BOT_TOP_GAP_RATIO` | 0.068111 | bottom screen offset from the half-screen line | 88 px |
| `BOT_CENTER_NUDGE` | −0.003829 | optical centring correction | −7 px |
| `TOP_INSET_RATIO` | 0.015317 | top screen inset on all sides | 28 px |
| `TOP_HINGE_GAP_RATIO` | 0.045 | quiet zone between the picture and the crease | 58 px |

The placement sequence in `HingeHelper.push()` is: `fitArea` → `snapBottomTo` →
`insetTop` (move up 58 px, then inset 28 px, landing at `154 … 1217` for the game picture
itself).

## 3. Touch controls

`input-layout.ini` uses Citra's native format: coordinates are **integer percentages**
with the origin at the horizontal centre line, positive y downward, and a scale factor per
button. Only integers are accepted.

| Button | Portrait value | Notes |
|---|---|---|
| `button_l_portrait` | `-81,12,88,1` | aligned to the physical shoulder recess |
| `button_r_portrait` | `81,12,88,1` | mirrored |
| `dpad_portrait` | `-81,39,110,1` | |
| `joystick_portrait` | `-79,70,180,1` | large, sits below the D-pad |
| `x / y / a / b` | scale `95` | right cluster |
| `home` | `0,86,173` | |
| `select` | `-23,86,105` | |
| `start` | `23,86,105` | |

1 % ≈ 9.14 px at this width. Button art is scaled *proportionally*, so the third field
(scale) is relative to each button's own baseline size — you cannot apply one multiplier
across buttons.

### How these numbers were obtained

Not by eye. The reliable method is a **magenta calibration pass**:

1. temporarily tint each button texture magenta and rebuild;
2. run a game, allow the overlay to display, screenshot;
3. measure the magenta rectangle in pixels;
4. convert back to percentages and to the real button scale;
5. remove the tint, rebuild, verify.

Guessing produces layouts that look plausible on a screenshot and are unusable in the
hand — the first shipped build did exactly that, with every button in the wrong place.

## 4. Theme panel geometry

The skins are rendered bitmaps that have to line up with the live picture, so
`skins_panel.py` draws to the same coordinates the runtime uses:

| Part | Geometry |
|---|---|
| Top aperture | `SCR_TOP_FULL = (0, 137, 1828, 1234)`, fixed to 5:3 then inset |
| Bottom aperture | `SCR_BOT = (410, 1380, 1402, 2124)` |
| L / R | centres `(174, 1447)` / `(1654, 1447)`, 233 × 123 |
| D-pad | centre `(201, 1796)`, 350 |
| Circle pad | centre `(201, 2196)`, 281 |
| X / Y / A / B | 126 each, centres 1618 / 1508 / 1727 / 1618 |
| HOME / SELECT | `(914, 2403)` 129 / `(704, 2403)` 112 |
| Silk print | `Fun in Hope` at `(914, 2528)`, 44 px |

`TOP_INSET = 28` must equal `TOP_INSET_RATIO × width`, otherwise the artwork frame and the
picture edge disagree by a few pixels — which reads as a smeared border and looks like a
rendering bug.

## 5. If you retarget another device

1. Measure the inner display and the crease position.
2. Adjust only the ratios in `HingeHelper.java`; keep the sequence order.
3. Re-render the skins (`gen_theme.py`) — mandatory, they are bitmaps.
4. Recalibrate the controls with the magenta pass.
5. Verify on hardware: the picture must not touch the crease, the touch surface must be
   fully reachable one-handed, and no overlay button may cover it.

## 6. Traps worth knowing

| Symptom | Cause |
|---|---|
| Game list empty after install | The provisioning has to finish *before* the native layer scans, and the native scan is triggered by `MainActivity`'s internal state, not by preferences alone. Copy assets synchronously, then reflect the private field. |
| Crash in `onCreate` when saving config | The native config object is not initialised yet — `saveConfig()` there is a SIGSEGV. Write the ini file directly instead. |
| Theme silently not applied | With `targetSdk 34` the app cannot read `citra-emu/theme/` without all-files access. Grant it, or the skins are invisible and the UI falls back to plain colours. |
| Wallpaper colours reported wrong | The platform palette extractor mis-reads this panel; sample the wallpaper bitmap directly, discard low-saturation and near-black/near-white pixels, and derive hue as a vector sum. |
| Overlay menus turn into a circle-with-arrow glyph | Vendor theming of the overflow icon. Draw a three-dot icon yourself. |
| Panel art and live picture drift apart | `skins_panel.py` constants were not updated together with `HingeHelper.java`. |
