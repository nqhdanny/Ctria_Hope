# Privacy Policy — Ctria Hope

**Last updated: 13 November 2026**
**Applies to:** Ctria Hope (`org.citra.emu`), version 1.2.0 and later.

## The short version

Ctria Hope collects nothing. There is no account, no sign-in, no analytics, no
advertising, no crash reporting and no tracking of any kind. The app makes exactly one
kind of automatic network request — a version check against GitHub's public API — and
sends no information about you with it. Everything you load into the emulator stays on
your device.

| Question | Answer |
|---|---|
| Do you collect personal data? | No |
| Do you use analytics or ad SDKs? | No |
| Do you share data with third parties? | No |
| Can I use it offline? | Yes, entirely — only the optional update check needs a network |
| Do you need my email or phone number? | No |
| Is my data sent anywhere when I play? | No |

Because no personal data is collected, there is nothing for us to retain, sell, disclose,
or delete on your behalf.

## What the app stores on your device

All of it lives in `citra-emu/` in your device's shared storage, and only there:

| Data | Purpose | Removed by |
|---|---|---|
| `Games/` — game files you add | The games you play | Deleting the folder |
| `config/` — emulator settings | Resolution, shaders, controls, theme choice | Clearing app data |
| `saves/`, `states/`, `sdmc/` — save files and save states | Your progress | Deleting the folder |
| `theme/` — panel skins | The visual theme | Deleting the folder |
| `log/` — emulator logs, if enabled | Troubleshooting on your own device | Deleting the folder |

None of these files are uploaded anywhere by this app. Uninstalling the app leaves the
`citra-emu/` folder in place so you do not lose saves; delete it manually if you want it
gone.

## Device permissions and why each one is needed

Ctria Hope asks only for permissions the emulator core actually uses. You can deny any
of them and still run games; the corresponding feature simply will not work.

| Permission | Why the app asks for it |
|---|---|
| **All files access** (`MANAGE_EXTERNAL_STORAGE`) | Android 11+ hides shared storage from apps without it. The emulator must read the games you put in `citra-emu/Games` and write saves next to them. Without this, the game list is empty. Access is limited to files the emulator reads and writes; nothing is scanned, indexed, or transmitted. |
| `READ_/WRITE_EXTERNAL_STORAGE` | Same purpose on Android 10 and older. |
| **Camera** | Used only by the emulated 3DS camera — a game that shows a camera view sees the phone camera instead. Frames are passed to the emulated game in memory. The app does not take, store or upload photos. |
| **Microphone** | Used only by the emulated 3DS microphone for games that listen to it. Audio is passed to the emulated game in memory and is not recorded or transmitted. |
| **Vibrate** | Haptic feedback. |
| **Internet**, **network / Wi-Fi state** | The optional update check over HTTPS, and local or online multiplayer when *you* start it. |
| **Install shortcut** | Lets you put a shortcut to an individual game on your home screen. |

## Network activity, precisely

- **Update check.** The app may request
  `https://api.github.com/repos/nqhdanny/Ctria_Hope/releases/latest`. This is an
  ordinary HTTPS GET for a public JSON document. It contains no identifiers, no device
  information, no usage data. As with any HTTPS request, GitHub can see the IP address
  it came from; that request is governed by
  [GitHub's privacy statement](https://docs.github.com/site-policy/privacy-policies/github-privacy-statement).
- **Multiplayer.** If you configure a room server and join a room, the game data
  needed to play is exchanged with the peers and the room server *you* selected. This
  is off by default and only happens on your explicit action. We operate no servers and
  receive nothing.
- **Nothing else.** There is no background sync, no ping, no telemetry beacon.

## Third-party components

The app is built on Citra MMJ / Citra, which is GPL-2.0 software. Those projects do not
contain analytics or advertising either. Two MIT-licensed homebrew games are bundled
(see `licenses/`); they are offline single-player games with no network code. The
complete list of third-party components and their licenses is in
[`NOTICE.md`](NOTICE.md).

## Children

Ctria Hope is a general-purpose emulator and is not directed at children. It collects no
personal data from anyone, including children under 13, so it does not knowingly collect
anything from them either.

## Your rights

Regulations such as the GDPR and similar laws give you rights to access, correct, export
and erase your personal data. We hold none, so there is nothing to hand over or delete on
our side. Your game files, saves and settings are yours, on your device, under your
control; deleting the `citra-emu/` folder is a complete erasure of everything the app
ever wrote.

## Changes to this policy

If a future version starts collecting anything — it is not planned — this document will
be updated before that version ships, with the change called out in the app's release
notes. The date at the top is the date of the last substantive change.

## Contact

Questions about this policy, or about privacy in the app:
**https://github.com/nqhdanny/Ctria_Hope/issues**

---

*This policy is also available in Chinese: [PRIVACY.zh-CN.md](PRIVACY.zh-CN.md).*
