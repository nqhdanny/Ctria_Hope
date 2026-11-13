# Bundled homebrew

The `.3dsx` files here are open-source, legally redistributable homebrew. They exist so a
fresh install has something to run instead of an empty list. Both are **unmodified
upstream release builds** — nothing was patched, re-signed or edited.

| File | Game | Genre | Size | Author | Source | License |
|---|---|---|---|---|---|---|
| `TRexGame.3dsx` | T-Rex Game 3DS | endless runner | 1.3 MB | BlyZeDev | https://github.com/BlyZeDev/T-Rex-Game-3DS | MIT |
| `2048-port-3ds.3dsx` | 2048 | puzzle | 136 KB | 0rientd | https://github.com/0rientd/2048-port-3ds | MIT |

Full license texts: [`licenses/`](licenses/), also shipped inside the APK.

`.3dsx` runs directly — no install step, unlike `.cia`. Copy the file into
`citra-emu/Games` and it appears in the list.

## Tested and playable, but not bundled

Two more homebrew titles were installed on hardware and confirmed *playable* — not just
loadable. They stay out of the APK to keep the download small; [`docs/GAMES.md`](../docs/GAMES.md)
has the download links and the per-title notes.

| Game | License | Size | Controls |
|---|---|---|---|
| Block Blast | Zlib | 214 KB | touch |
| Trogdor Reburninated | MIT | 2.5 MB | START + D-pad; audio needs `sdmc/3ds/Trogdor-RB/` |

### Tested and removed

Four titles were dropped after hardware testing. Two never get past their own boot screen,
two render correctly but ignore every input — which is worse, because it looks like a bug in
the emulator:

| Game | License | Why |
|---|---|---|
| Balatro3DS | GPL-3.0 | stops on the author's own *NO GAME* screen; needs its resource folder |
| Bottomless Block Barrage | GPL-3.0 | `.3ds` image, both screens black — encrypted, needs a key table |
| Cookie Collector | CC0 | five presses of X left `You have: 0 cookies` unchanged |
| Craftus Reloaded | MIT | D-pad, circle pad and touch all fail to move the menu selection |

## Why only two

The rule applied was: **both the code and every asset must be original to the project.**
That excludes a lot of popular homebrew that is otherwise tempting:

| Excluded | Reason |
|---|---|
| Sonic Mania / Sonic CD / Sonic 1&2 ports | reverse-engineered commercial games |
| Super Metroid native ports, Mario Odyssey demakes | Nintendo IP |
| Any decompilation-based project | open code, but still needs the original game's assets |
| GPL-3.0 homebrew (Super Haxagon, 3D Pong, …) | redistributing the binary requires shipping its source too; better as a separate download |
| Engine ports (OpenJazz, TheXTech, …) | unplayable without the original game's data files |
| Any 3DS ROM or CIA | not distributable, full stop |

The bar is deliberately conservative: an emulator shipping bundled content is exactly the
kind of thing that attracts takedown requests, and one questionable file would put the
whole package at risk.

## Removed

`flappy.3dsx` (Flappy Bird 3DS, MIT) was dropped in 1.0.1 — the screen orientation was
rotated on this device, which looked like a layout bug. It is not a licensing problem and
can be re-added if that upstream issue is fixed.
