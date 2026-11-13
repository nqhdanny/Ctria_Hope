# Getting games into Ctria Hope

Three facts cover almost everything:

1. **Two games are already there** — 2048 and T-Rex, unpacked from the APK on first launch. Two more
   homebrew titles are verified to run (section 5); those are a download away.
2. **Adding your own game is one file copy** into `citra-emu/Games`.
3. **Only encrypted retail titles need keys**, and those keys can only come from your own console.

---

## 1. Supported formats

| Format | What it is | Key table needed |
|---|---|---|
| `.3dsx` | The standard homebrew format. Small, never encrypted. | No |
| `.cia` | Installable package format. It does **not** need to be installed — it loads directly. | Only if it wraps a retail title |
| `.3ds` | Cartridge image (CCI). Every partition in a retail cart is AES-CTR encrypted. | Yes, unless already decrypted |

> **Rule of thumb:** a game that opens to a **solid black screen, no sound, no error** is almost always an encrypted image without a key table. See section 4.

## 2. Where to find games

The only test that matters: **does the project state a licence?** MIT, GPL, CC0, Zlib → download it, keep it, pass it on. No licence → all rights reserved, don't redistribute.

| Source | Notes |
|---|---|
| **Universal-DB** — `db.universal-team.net` | Index of 3DS homebrew with version, licence and a direct download for each entry. Easiest starting point. |
| **GitHub** — topic `3ds-homebrew` | Look at Releases for `.3dsx` / `.cia`. The licence is shown in the repo sidebar. |
| **itch.io** — tag `3ds` | Small games by independent authors, some shipped as `3dsx`. |
| **GBAtemp / 4PDA** | Forum release threads, good for obscure titles. 4PDA is the Russian-language community. |

Do not use "complete ROM set" sites. Beyond the legal problem, they are a common vector for malware, and store review treats distributing pirated content as an automatic rejection.

## 3. Putting a file in place

One directory:

```
/sdcard/citra-emu/Games/
```

In a file manager this reads as **Internal storage → citra-emu → Games**.

1. Download the file on the phone, or copy it over by USB.
2. Move it into `citra-emu/Games`. Keep the extension; non-ASCII names work, but avoid `? * : " < > |`.
3. Return to the app and pull to refresh. If nothing happens, kill the app from recents and open it again.

If the folder does not exist yet, launch the app once — it creates the whole tree.

> **If the app shows an empty list and asks for file access**, grant **"manage all files"**. Without it the app can only see its private directory and will never find what you put in `citra-emu/Games`. After granting, it rebuilds the directories and unpacks the bundled games.

## 4. Keys and fonts — only for encrypted titles

**Where they come from.** Retail 3DS data is encrypted with AES-CTR; decryption needs KeyX/KeyY, and KeyY is derived from each cartridge's unique ID. Those keys exist in no legitimate public distribution — only on a console you own (the community-standard extraction tool documents the procedure). Anyone who has the game file necessarily has the keys; they come out of the same dump.

**Where they go:**

```
/sdcard/citra-emu/sysdata/
├─ aes_keys.txt          decrypt retail titles
├─ cbf_std.bcfnt         system font (only if text renders blank)
├─ cbf_zh-Hans-CN.bcfnt  optional, Chinese
└─ cbf_ko-Hang-KR.bcfnt  optional, Korean
```

Create `sysdata` yourself if it is not there. The file names are case-sensitive and must match exactly.

| Symptom | Missing | Put this there |
|---|---|---|
| Black screen, silence, no error | key table | `aes_keys.txt` |
| Game runs, all text is blank boxes | system font | `cbf_std.bcfnt` |
| Chinese/Korean text shows as `?` | language font | `cbf_zh-Hans-CN.bcfnt` etc. |

Homebrew `.3dsx` needs neither — which is why both bundled games run on a completely fresh install with no keys and no fonts. Verified.

## 5. Games verified on hardware

Verified by *playing* them, not by watching them load. A title that renders but ignores input is
not playable, and two of those were removed for exactly that.

| Game | Licence | Size | Controls | Notes |
|---|---|---|---|---|
| **2048** (bundled) | MIT | 133 KB | touch | number merging |
| **T-Rex** (bundled) | MIT | 1.3 MB | touch | Chrome dino runner |
| **Block Blast** | Zlib | 214 KB | touch | block puzzle, sound |
| **Trogdor Reburninated** | MIT | 2.5 MB | START + D-pad | audio needs `sdmc/3ds/Trogdor-RB/` |

The pattern is worth knowing before you download: **touch-first titles work; a deep D-pad menu is
where this emulator gets stuck.**

Trogdor keeps its audio and save data outside the executable. Put the whole `Trogdor-RB` folder at:

```
/sdcard/citra-emu/sdmc/3ds/Trogdor-RB/
```

Without it the game still runs — silently, and without saving.

### Four that were removed

Two never load, two load and ignore input. Both failure modes are recorded here so you don't
repeat the tests:

| Game | Licence | Why |
|---|---|---|
| Balatro3DS | GPL-3.0 | loads, then stops on the author's own *NO GAME* screen — needs its resource folder; the single-file build is not self-contained |
| Bottomless Block Barrage | GPL-3.0 | `.3ds` image, both screens stay black — encrypted, needs a key table |
| Cookie Collector | CC0 | renders fine, but five presses of X left `You have: 0 cookies` unchanged |
| Craftus Reloaded | MIT | title and world menu render, but D-pad, circle pad and touch all fail to move the selection — three screenshots, byte-identical |

## 6. Troubleshooting

| Symptom | Fix |
|---|---|
| New game does not appear | Restart the app; confirm the file is in `citra-emu/Games` and not in `Download`; confirm it is not still a `.zip` |
| Black screen on launch | Encrypted image without `aes_keys.txt`, or the `.3dsx` needs a real CFW console |
| Text renders blank | Missing `cbf_std.bcfnt` |
| Runs but stutters | Lower the resolution scale to 1×; 3D titles like Craftus are heavy by nature |
| Saves disappeared | Saves live under `citra-emu/sdmc`; back up the whole `citra-emu` folder before uninstalling |
| Permission prompt keeps returning | Settings → Apps → Ctria Hope → Permissions → allow all-files access |

## 7. Scope

This guide covers one thing: putting games **you legally own** into the emulator. The app ships no ROM, no key table and no console firmware. The two bundled games are original open-source works, their licence texts ship inside the APK and live in [`licenses/`](../licenses/).

If you have no console and no cartridge, the bundled games plus community homebrew are a complete experience — and they need no keys at all.
