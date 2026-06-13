# Task B — Ingestion Media Integration Report

## Summary

All ingestion pipelines have been migrated from upload-based image handling to derivation-only using the canonical resolver (`imageResolver.js`).

## Before / After

| File | Before | After |
|---|---|---|
| `jobs.js` | `resolveAndStoreImage(player, {allowAiFallback: true})` | `resolvePlayerImage(player)` |
| `jobs.js` | `resolveAndStoreImage(player, {allowAiFallback: isRegen})` | `resolvePlayerImage(player)` (via `resolvePlayerImageWithCache`) |
| `importLaunchLeagueBatch.js` | `uploadRemoteImage(url, playerId, "sportmonks")` | `resolvePlayerImage(player)` |
| `importNamedPlayers.js` | `uploadRemoteImage(url, playerId, "sportmonks")` | `resolvePlayerImage(player)` |
| `importTopEuropeanLeagues.js` | `uploadRemoteImage(url, playerId, "sportmonks")` | `resolvePlayerImage(player)` |
| `importYouthPlayers.js` | `uploadRemoteImage(url, playerId, "sportmonks")` | `resolvePlayerImage(player)` |
| `backfillMarketplaceImages.js` | `resolveAndStoreImage` + `uploadRemoteImage` | `resolvePlayerImage(player)` |

## Canonical Player Import Flow

```
Sportmonks API
    ↓
Fetch player data (name, age, position, stats, sportmonksId)
    ↓
resolvePlayerImage({ playerId: sportmonksId })
    ↓  (no network call — pure derivation)
{ storageKey: "gtex/players/{id}", imageSource: "cloudinary_derived", rightsCleared: true }
    ↓
repository.upsertPlayer({ ...player, imageUrl, imageSource, rightsCleared })
    ↓
repository.upsertAppPlayerImageMetadata({ storageKey, ... })
```

## Removed

- Cloudinary upload calls from all ingestion pipelines
- Wikimedia fallback download path (no longer triggered by ingestion)
- AI face fallback upload path (no longer triggered by ingestion)
- `resolveAndStoreImage` import from active call sites
- `uploadRemoteImage` import from all active call sites

## Notes

- `images.js` is retained with the old functions exported for any external scripts that may reference it, but no active import path uses it.
- `backfillMarketplaceImages.js::upgradeRemoteFallbackImages` now re-derives the Cloudinary public_id rather than re-uploading.
- The `isReusableImageUrl` guard in `importLaunchLeagueBatch.js` is superseded: all images are now `cloudinary_derived` and always reusable.
- `CLOUDINARY_API_KEY` and `CLOUDINARY_API_SECRET` are only needed if you ever need to perform admin operations on Cloudinary (deletion, transformation). Not required for ingestion or delivery.
