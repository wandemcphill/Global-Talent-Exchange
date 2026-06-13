# Phase V1 — Cloudinary Upload Elimination Proof

Date: 2026-06-13
Command evidence collected from: `git grep` on HEAD of `feature/original-visual-runtime`

---

## Grep Results

### `git grep "uploadRemoteImage"`

```
INGESTION_MEDIA_INTEGRATION_REPORT.md:13:  (before/after table — documentation only)
PLAYER_IMAGE_RESOLVER_REPORT.md:9:    (audit history — documentation only)
services/player-ingestion/src/images.js:95:      const uploaded = await uploadRemoteImage(...)
services/player-ingestion/src/images.js:149: async function uploadRemoteImage(url, playerId, source) {
services/player-ingestion/src/images.js:198:  uploadRemoteImage,
```

**Verdict for each match:**

| Match | File | Active? | Safe? |
|---|---|---|---|
| `.md` references | `INGESTION_MEDIA_INTEGRATION_REPORT.md`, `PLAYER_IMAGE_RESOLVER_REPORT.md` | Documentation | ✅ Cannot execute |
| `images.js:95` | Internal call inside `uploadRemoteImage()` body | Dead — function not called | ✅ |
| `images.js:149` | Function definition | Dead — no import exists | ✅ |
| `images.js:198` | `module.exports` | Dead — no file imports `./images` | ✅ |

### `git grep "resolveAndStoreImage"`

```
INGESTION_MEDIA_INTEGRATION_REPORT.md   — documentation
PLAYER_IMAGE_RESOLVER_REPORT.md         — documentation
services/player-ingestion/src/imageResolver.js:8,53  — comment/JSDoc only
services/player-ingestion/src/images.js:53,199       — function definition + export
```

**Verdict:** All matches are either documentation or the dead `images.js` file. No active call site.

### `git grep "cloudinary.uploader"`

```
services/player-ingestion/src/images.js:150:  return cloudinary.uploader.upload(url, {
```

**Verdict:** Single match. Lives inside `uploadRemoteImage()` in `images.js`. Unreachable — see import audit below.

### `git grep ".upload(" services/player-ingestion`

```
services/player-ingestion/src/images.js:150:  return cloudinary.uploader.upload(url, {
```

**Verdict:** Single match, same dead function.

---

## Import Audit — Proving images.js is Unreachable

```
git grep "require.*['\"]./images['\"]" -- services/player-ingestion
(no output)
```

Zero files import `./images`. The module is in the tree but has no entry point. Node.js cannot execute dead exports.

---

## Active Import Chain

Every active ingestion path imports `./imageResolver`:

```
jobs.js                  → require("./imageResolver") → resolvePlayerImage()
importLaunchLeagueBatch  → require("./imageResolver") → resolvePlayerImage()
importNamedPlayers       → require("./imageResolver") → resolvePlayerImage()
importTopEuropeanLeagues → require("./imageResolver") → resolvePlayerImage()
importYouthPlayers       → require("./imageResolver") → resolvePlayerImage()
backfillMarketplaceImages→ require("./imageResolver") → resolvePlayerImage()
```

`imageResolver.js::resolvePlayerImage()` contains zero network calls, zero Cloudinary SDK calls, zero HTTP requests.

---

## Answer: Can ingestion rebuild a fresh DB using only `gtex/players/{sportmonks_player_id}`?

**YES.**

Proof:

```js
// imageResolver.js — entire image resolution:
function resolvePlayerImage(player) {
  const publicId = getPlayerPublicId(player.playerId);   // "gtex/players/311129"
  const imageUrl = getPlayerImageUrl(player.playerId);   // Cloudinary delivery URL (no upload)
  return {
    imageUrl,
    storageKey: publicId,          // stored in DB as "gtex/players/311129"
    imageSource: "cloudinary_derived",
    rightsCleared: true,
  };
}
```

The ingestion pipeline:
1. Fetches player data from Sportmonks API (name, age, position, stats)
2. Calls `resolvePlayerImage({ playerId: sportmonksId })` — pure derivation, no network
3. Stores `storageKey = "gtex/players/{id}"` in the database
4. Image delivery URLs are constructed on-demand from the stored `storageKey`

No Cloudinary upload. No Cloudinary credentials required. No media download.
A completely fresh DB can be populated from Sportmonks alone.
