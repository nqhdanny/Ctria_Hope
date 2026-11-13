# Getting games into Ctria Hope

Three facts cover almost everything:

1. **Six games are already there.** They are unpacked from the APK on first launch — nothing to download.
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

Homebrew `.3dsx` needs neither — which is why the six bundled games run on a completely fresh install with no keys and no fonts. Verified.

## 5. Games verified on hardware

Tested one by one on a **HUAWEI Pura X Max** (inner display 1828×2584). All are open-source licensed.

| Game | Licence | Size | Notes |
|---|---|---|---|
| **2048** (bundled) | MIT | 133 KB | Number merging, touch |
| **T-Rex** (bundled) | MIT | 1.3 MB | Chrome dino runner |
| **Cookie Collector** | CC0 | 197 KB | Idle/text game, press X |
| **Block Blast** | Zlib | 214 KB | Block puzzle, touch, sound |
| **Trogdor Reburninated** | MIT | 2.5 MB | Side-scrolling action; **audio needs its data folder** |
| **Craftus Reloaded** | MIT + CC BY-SA textures | 387 KB | 3D sandbox builder, the heaviest of the set |

Two that did **not** work, so you don't waste time:

- **Balatro3DS** (GPL-3.0, 17 MB `.3dsx`) — loads, then stops on the author's own *NO GAME* screen; it needs the resource folder, the single-file build is not self-contained.
- **Bottomless Block Barrage** (GPL-3.0, `.3ds`) — both screens stay black. `.3ds` images of this kind are usually encrypted.

Trogdor's audio and save data live outside the executable; put the whole `Trogdor-RB` folder at:

```
/sdcard/citra-emu/sdmc/3ds/Trogdor-RB/
```

Without it the game still runs — silently, and without saving.

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

This guide covers one thing: putting games **you legally own** into the emulator. The app ships no ROM, no key table and no console firmware. The six bundled games are original open-source works, their licence texts ship inside the APK and live in [`licenses/`](../licenses/).

If you have no console and no cartridge, the bundled games plus community homebrew are a complete experience — and they need no keys at all.
