# Phase S6 — Cloudinary Certification

Date: 2026-06-14
Canonical pattern: `gtex/players/{sportmonks_player_id}` — e.g. `gtex/players/311129`

## Upload-Call-Site Scan

`git grep` over `services/**/*.js` for `cloudinary.uploader`, `uploadRemoteImage`, `resolveAndStoreImage`,
`.upload(`:

| Match | File:Line | Classification | Safe? |
|---|---|---|---|
| `resolveAndStoreImage` (doc comment) | `imageResolver.js:8,53` | JSDoc | ✅ not executable |
| `resolveAndStoreImage` (definition) | `images.js:53` | **dead** | ✅ no importer |
| `uploadRemoteImage` (call) | `images.js:95` | **dead** (inside dead fn) | ✅ unreachable |
| `uploadRemoteImage` (definition) | `images.js:149` | **dead** | ✅ no importer |
| `cloudinary.uploader.upload(` | `images.js:150` | **dead** (inside dead fn) | ✅ unreachable |
| `module.exports` of both | `images.js:198,199` | **dead** export | ✅ no importer |

## Dead-Module Proof

```
git grep "require(['\"]\./images['\"])" -- services/**/*.js
→ NONE import ./images
```

`services/player-ingestion/src/images.js` is in the tree but **has no importer**. None of its
upload functions can execute.

## Active Image Path (resolver-only)

Every live ingestion entrypoint imports `./imageResolver`, whose `resolvePlayerImage()` is pure
derivation — zero network calls, zero Cloudinary SDK calls:

```js
function resolvePlayerImage(player) {
  const publicId = getPlayerPublicId(player.playerId);  // "gtex/players/311129"
  const imageUrl = getPlayerImageUrl(player.playerId);  // delivery URL, no upload
  return { imageUrl, storageKey: publicId, imageSource: "cloudinary_derived", rightsCleared: true };
}
```

Python consumers use the parallel canonical resolver `backend/app/core/player_image.py`
(`get_player_public_id` / `get_player_image_url`) — also derivation-only.

## Answer: Can GTEX rebuild a fresh DB using only `gtex/players/{sportmonks_player_id}` without re-uploading media?

**YES.**

The ingestion pipeline:
1. Fetches player data (name, age, position, stats) from the Sportmonks API.
2. Calls `resolvePlayerImage({ playerId })` — pure derivation, no network, no upload.
3. Stores `storageKey = "gtex/players/{id}"` in the database.
4. Delivery URLs are constructed on-demand from the stored `storageKey`.

No Cloudinary upload occurs. No Cloudinary write credentials are required to populate a fresh
database. Existing assets under `gtex/players/{id}` are referenced, never re-created.

## Verdict: RESOLVER-ONLY — CERTIFIED

Zero active upload paths. Existing Cloudinary media is preserved and re-used by derivation.
