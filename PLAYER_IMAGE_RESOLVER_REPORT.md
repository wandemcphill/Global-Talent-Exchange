# Task A — Player Image Resolver Report

## Audit Findings

### Pre-existing image handling (before this task)

| File | Pattern | Problem |
|---|---|---|
| `services/player-ingestion/src/images.js` | `uploadRemoteImage()` + `resolveAndStoreImage()` | Uploaded images to Cloudinary on every ingestion run |
| `services/player-ingestion/src/importLaunchLeagueBatch.js` | Direct `uploadRemoteImage()` call | Upload at ingestion time |
| `services/player-ingestion/src/importNamedPlayers.js` | Direct `uploadRemoteImage()` call | Upload at ingestion time |
| `services/player-ingestion/src/importTopEuropeanLeagues.js` | Direct `uploadRemoteImage()` call | Upload at ingestion time |
| `services/player-ingestion/src/importYouthPlayers.js` | Direct `uploadRemoteImage()` call | Upload at ingestion time |
| `services/player-ingestion/src/backfillMarketplaceImages.js` | Both `resolveAndStoreImage` and `uploadRemoteImage` | Upload + migration path |
| `services/player-ingestion/src/jobs.js` | `resolveAndStoreImage()` | Upload at ingestion time |
| `backend/app/players/real_player_service.py` | `_profile_image_url()` reads raw `photo_url` from metadata JSON | No central resolver |

No code in the backend Python layer called Cloudinary directly. Image URLs were stored in the `ingestion_players.image_url` column and `ingestion_player_image_metadata.storage_key` / `source_url`.

### Canonical pattern confirmed

```
gtex/players/{sportmonks_player_id}
```

`config.cloudinary.folder` in the ingestion service was already set to `gtex/players` (from `CLOUDINARY_PLAYER_FOLDER` env var).

---

## Changes Made

### New: `backend/app/core/player_image.py`

Single canonical resolver for all Python consumers.

```python
from app.core.player_image import get_player_public_id, get_player_image_url

public_id = get_player_public_id(311129)        # => "gtex/players/311129"
url = get_player_image_url(311129, width=200)   # => Cloudinary delivery URL
```

- `get_player_public_id(id)` — derives the public_id; no network call
- `get_player_image_url(id, *, width, height, format, quality)` — builds delivery URL
- `get_player_image_url_for_card(id)` — 200×200 convenience
- `get_player_image_url_for_thumbnail(id)` — 80×80 convenience
- Returns `None` when `CLOUDINARY_CLOUD_NAME` is not set (safe fallback)

### New: `services/player-ingestion/src/imageResolver.js`

Single canonical resolver for all Node.js ingestion consumers.

```js
const { resolvePlayerImage, getPlayerPublicId, getPlayerImageUrl } = require("./imageResolver");

const image = resolvePlayerImage({ playerId: 311129 });
// => { imageUrl, storageKey: "gtex/players/311129", imageSource: "cloudinary_derived", rightsCleared: true }
```

- No Cloudinary credentials required for URL generation
- Returns `null` for `imageUrl` when `CLOUDINARY_CLOUD_NAME` is absent (graceful)

### Updated: All call sites in `services/player-ingestion/src/`

All 6 files that called `uploadRemoteImage` or `resolveAndStoreImage` now call `resolvePlayerImage` from the new resolver. The old `images.js` is retained but no longer imported by any active path.

---

## Invariants Enforced

1. No upload call remains in any active ingestion path.
2. All `storageKey` values derive from `gtex/players/{sportmonksId}`.
3. `imageSource` is now `cloudinary_derived` (was `sportmonks`/`missing`/`ai_generated`).
4. `rightsCleared` is always `true` for derived images.
5. `CLOUDINARY_API_KEY` / `CLOUDINARY_API_SECRET` are not required for player image delivery.
