# Phase D8 — Cloudinary Certification

Date: 2026-06-14
Canonical pattern: `gtex/players/{sportmonks_player_id}` — e.g. `gtex/players/311129`

## Upload elimination (after port)
All 6 ingestion upload entrypoints now derive instead of upload:
`jobs.js`, `importNamedPlayers.js`, `importYouthPlayers.js`, `importTopEuropeanLeagues.js`,
`importLaunchLeagueBatch.js`, `backfillMarketplaceImages.js` → `require("./imageResolver").resolvePlayerImage`.

```
grep uploadRemoteImage|resolveAndStoreImage|require("./images")  (excl images.js, tests)
→ only doc comments remain; NONE import ./images  (images.js is dead)
```

`imageResolver.resolvePlayerImage(player)` is pure derivation:
```js
{ imageUrl: getPlayerImageUrl(playerId), storageKey: "gtex/players/{id}",
  imageSource: "cloudinary_derived", rightsCleared: true }
```
No network, no Cloudinary SDK, no credentials needed.

## Answer: Fresh DB rebuild without uploads?
**YES.** Ingestion fetches Sportmonks player data, derives `storageKey = gtex/players/{id}`, stores it.
Delivery URLs are built on-demand. Existing Cloudinary assets are referenced, never re-created.

## Verdict: RESOLVER-ONLY — CERTIFIED
