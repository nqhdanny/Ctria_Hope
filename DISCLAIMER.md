# Legal Notice & Disclaimer — Ctria Hope

**Last updated: 13 November 2026**

## 1. Not affiliated with Nintendo

Ctria Hope is an independent, unofficial project. It is **not** affiliated with,
authorised by, endorsed by, sponsored by, or in any way connected to Nintendo Co., Ltd.,
Nintendo of Europe, or any of their subsidiaries.

"Nintendo", "Nintendo 3DS", "3DS" and the names of Nintendo's games are trademarks of
Nintendo. They appear in this project only where they are unavoidable to describe what
the software does — namely emulating Nintendo 3DS hardware. The artwork in this
repository does not reproduce Nintendo's logo, wordmark, or trade dress: the panel skins
that imitate the console body carry the project's own silk print, **`Fun in Hope`**,
precisely so that nothing on screen claims to be a Nintendo product.

## 2. Not affiliated with Huawei

Ctria Hope is likewise not affiliated with, endorsed by, or supported by Huawei
Technologies Co., Ltd. It was developed against a HUAWEI Pura X Max because that device's
foldable display is what the layout targets, and nothing more should be read into it.

## 3. No game ROMs, no system files, no keys

This project contains **no** commercial game data of any kind. Specifically, it does not
include, bundle, link to, download, decrypt, or help obtain:

- any Nintendo 3DS game ROM, CIA, 3DSX dump, or eShop content,
- any 3DS system file (NAND image, `boot9.bin`, `boot11.bin`, `secret sector`, `movable.sed`),
- any encryption key, title key, or key-derivation utility,
- any BIOS, firmware, or copyrighted asset extracted from a console.

The only games shipped inside the APK are two **MIT-licensed homebrew** titles whose full
license texts are included in [`licenses/`](licenses/) — original works, freely
redistributable, not derived from any commercial product.

The emulator does not ship a key table, shared system fonts, a NAND image, DSP firmware
or any other console-derived data. Earlier builds inherited those from the upstream
Android fork; they were removed in 1.4.1 — see [`CHANGELOG.md`](CHANGELOG.md). What this
means in practice: encrypted retail titles cannot be decrypted, and some games render
blank text, until you supply your own `aes_keys.txt` and shared font in
`citra-emu/sysdata/`. That is the intended posture — those files must come from a console
you own, not from us.

Everything else you run is supplied by you. If you do not own a copy of a game, you have
no right to play it, and this project gives you no means to acquire one.

## 4. Your responsibility for what you run

Emulation law differs by jurisdiction. In most countries, emulating hardware is lawful;
downloading or distributing a game you do not own is not. Whether you may dump a game you
own is a separate question that depends on where you live. **You are responsible** for
ensuring that the files you load into this emulator were obtained lawfully in your
jurisdiction. The authors of this project cannot verify, and do not verify, what you load
into it.

## 5. No warranty

This program is free software, distributed under the GNU General Public License v2.0 or
later, **without any warranty**, to the extent permitted by law:

> This program is distributed in the hope that it will be useful, but WITHOUT ANY
> WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
> PARTICULAR PURPOSE. See the GNU General Public License for more details.

The authors are not liable for data loss, corrupted save files, damaged devices, voided
warranties, or any other damage arising from the use of this software. Back up your saves.

## 6. License compliance (GPL-2.0)

Ctria Hope is a derivative work of Citra (GPL-2.0-or-later) via Citra MMJ. It is
distributed under the same license, and **no additional restriction** is placed on it, as
GPL-2.0 §6 requires.

If you obtained a copy of the compiled application (APK), you are entitled to the
corresponding source code. That source is this repository, at the tag matching the
version you are running; the base APK hash, the upstream commit and the exact build
recipe are listed in [`NOTICE.md`](NOTICE.md) and [`docs/BUILD.md`](docs/BUILD.md). Inside
the app, **Settings → About → “Source code (GPL-2.0)”** links here directly.

If you redistribute this application, you must:

1. ship the full GPL-2.0 text with it (§1),
2. provide the corresponding source, or a written offer valid for three years (§3),
3. keep the license intact and add no further restrictions (§6),
4. not imply that the original authors endorse your redistribution.

## 7. Trademarks of others

All other product names, logos and brands mentioned in this repository are the property
of their respective owners and are used only for identification and reference.

## 8. Notice and takedown

If you hold rights to material you believe is being infringed by this repository, open an
issue at
**https://github.com/nqhdanny/Ctria_Hope/issues**
with enough detail to identify the material, and it will be reviewed promptly. Content
that turns out to infringe will be removed, and if the objection is to the project as a
whole, distribution will stop.

## 9. No legal advice

This document is a plain-language statement of how the project sees its own position. It
is not legal advice, and it does not create any obligation on the part of the authors
beyond what the GPL-2.0 and applicable law already impose.

---

*中文版：[DISCLAIMER.zh-CN.md](DISCLAIMER.zh-CN.md)*
