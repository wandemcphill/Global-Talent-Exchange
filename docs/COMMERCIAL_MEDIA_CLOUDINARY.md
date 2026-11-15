# GTEX Commercial Advertising Network — Cloudinary Media Storage & Delivery

This document describes the Cloudinary media storage, access control, CDN delivery, and S3-to-Cloudinary migration architecture for the **GTEX Commercial Advertising Network**.

---

## 1. Required Environment Variables

Commercial advertising media provider selection is controlled explicitly by `GTE_COMMERCIAL_MEDIA_PROVIDER` without affecting non-commercial GTEX storage or `GTE_GENERATED_MEDIA_BASE_URL` (which remains dedicated to regen portraits).

| Environment Variable | Required in Production | Default / Example | Purpose |
|---|---|---|---|
| `GTE_COMMERCIAL_NETWORK_ENABLED` | Yes | `true` | Enables the GTEX Commercial Advertising Network routes and catalog. |
| `GTE_COMMERCIAL_MEDIA_PROVIDER` | Yes | `cloudinary` | Selects Cloudinary as the primary storage & CDN provider for new commercial uploads (`cloudinary`, `s3`, or `local_disk` in local dev/test). |
| `CLOUDINARY_CLOUD_NAME` | Yes | `<your-cloud-name>` | Cloudinary account cloud name. |
| `CLOUDINARY_API_KEY` | Yes | `<your-api-key>` | Cloudinary API key for server-side signed uploads & admin operations. |
| `CLOUDINARY_API_SECRET` | Yes | `<your-api-secret>` | Cloudinary API secret (server-side only; never exposed to the browser). |
| `GTE_S3_BUCKET` / `GTE_S3_*` | Optional (Legacy) | `eu-central-1` | Retained for backward-compatible reads of historical S3-backed media and S3-to-Cloudinary migration. |
| `GTE_3D_STADIUM_ADS_ENABLED` | Optional | `false` | Keeps `stadium_perimeter` closed while 3D stadium gameplay is not open. |

### Production Fail-Safe Behaviour
- When `GTE_COMMERCIAL_MEDIA_PROVIDER=cloudinary` is configured in production/staging (`GTE_APP_ENV` in `production`, `prod`, `release`, `staging`) and any of `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, or `CLOUDINARY_API_SECRET` is missing, commercial uploads fail closed (`HTTP 503`) rather than silently writing to ephemeral Render container disk or database BLOBs.
- New commercial uploads never store raw file bytes in `AdvertiserMediaAsset.data`.

---

## 2. Render Service Configuration

In `render.yaml`, the `gtex-api` service declares:
```yaml
      - key: GTE_COMMERCIAL_NETWORK_ENABLED
        value: "true"
      - key: GTE_COMMERCIAL_MEDIA_PROVIDER
        value: "cloudinary"
      - key: CLOUDINARY_CLOUD_NAME
        sync: false
      - key: CLOUDINARY_API_KEY
        sync: false
      - key: CLOUDINARY_API_SECRET
        sync: false
```
In the Render Dashboard for `gtex-api`, set the secret values for `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, and `CLOUDINARY_API_SECRET`.

---

## 3. Cloudinary Folder Structure & Resource Types

All commercial advertising assets are organized by asset kind and isolated by `workspace_id` with unpredictable unique public IDs (`{folder}/{workspace_id}/{sanitized_stem}-{timestamp}-{random_hex}`):

| Asset Kind | Cloudinary Folder Hierarchy | Cloudinary `resource_type` | Max Size | Supported Formats |
|---|---|---|---|---|
| `logo` | `gtex/commercial/brands/logos/{workspace_id}` | `image` | 5 MB | PNG, JPEG, WebP |
| `brand_image` | `gtex/commercial/brands/creatives/{workspace_id}` | `image` | 15 MB | PNG, JPEG, WebP |
| `music_artwork` | `gtex/commercial/music/artwork/{workspace_id}` | `image` | 10 MB | PNG, JPEG, WebP |
| `brand_video` | `gtex/commercial/brands/videos/{workspace_id}` | `video` | 50 MB | MP4, WebM (strictly silent; max 45s) |
| `music_audio` | `gtex/commercial/music/audio/{workspace_id}` | `video` | 50 MB | MP3/MPEG, WAV, OGG, M4A/MP4, AAC (max 420s) |

> **Important:** Per official Cloudinary specifications, audio files (`music_audio`) are uploaded and delivered using `resource_type="video"` (never `image` or `raw`).

---

## 4. Upload, Privacy, and Delivery Flows

### Secure Upload Workflow (`POST /api/v2/advertiser/media/upload`)
1. Authenticates the advertiser user and verifies workspace membership and `manage_campaigns` permission.
2. Validates file magic bytes / MIME signature, file size limits, image dimensions, audio/video duration, and enforces that `brand_video` creatives contain no audio stream.
3. Uploads the asset to Cloudinary using server-side SHA-1 parameter signing (`backend/app/storage/cloudinary.py`).
4. Persists `storage_provider="cloudinary"`, `storage_key=<public_id>`, `data=None`, `access_classification="draft"`, and Cloudinary metadata (`secure_url`, `resource_type`, `cloudinary_asset_id`, `cloudinary_version`, `format`, `bytes`, `width`, `height`, `duration`, `original_filename`) in `AdvertiserMediaAsset`.
5. **Compensating Cleanup:** If the Cloudinary upload succeeds but the database commit fails, the backend immediately issues a compensating `CloudinaryObjectStorage.delete()` call so no orphaned asset is left behind.

### Asset Privacy & Publication Controls
- Newly uploaded media starts with `access_classification="draft"`.
- Unauthenticated requests to `/api/v2/public/ads/media/{asset_id}` for draft, rejected, paused, expired, or unpaid campaigns are rejected with `403 Forbidden`.
- Advertisers can preview their own draft media in the Advertiser Workspace Portal using workspace authentication or the HMAC-signed preview URL (`preview_url` / `?token=...`).
- Cross-workspace isolation is enforced: one advertiser workspace cannot view, attach, or delete another workspace's private media.
- Once a campaign is **approved**, **active**, **paid** in NGN, within its delivery window, and (for music promotions) **rights-verified**:
  - `sync_campaign_media_access` transitions the campaign's media to `access_classification="public_campaign"`.
  - Public campaign feeds (`/api/v2/public/ads/campaigns`, `/api/v2/public/ads/music/rotation`, `/api/v2/public/ads/music/promotions`) emit the direct Cloudinary CDN `secure_url` (`https://res.cloudinary.com/...`).
  - Requests to `/api/v2/public/ads/media/{asset_id}` return a `307 Temporary Redirect` to the Cloudinary CDN URL with `Cache-Control: public, max-age=86400`.

### Lifecycle & Orphan Detection
- **List Workspace Media:** `GET /api/v2/advertiser/media`
- **Delete Workspace Media:** `DELETE /api/v2/advertiser/media/{asset_id}` (returns `409 Conflict` if the asset is attached to an active or under-review campaign; otherwise deletes from Cloudinary and removes the DB row).
- **Admin Orphan Detection:** `GET /api/v2/admin/advertising/media/orphans` lists Cloudinary objects under `gtex/commercial/` that are not referenced by any `AdvertiserMediaAsset` record without performing destructive auto-deletion.

---

## 5. S3 / Legacy BLOB to Cloudinary Migration & Rollback

### Running the Migration Utility

1. **Dry-Run Mode (Inspect & Verify Without Uploading):**
   ```bash
   python backend/scripts/migrate_commercial_media_to_cloudinary.py \
     --database-url "$DATABASE_URL" \
     --dry-run \
     --batch-size 50
   ```
2. **Live Migration Run:**
   ```bash
   python backend/scripts/migrate_commercial_media_to_cloudinary.py \
     --database-url "$DATABASE_URL" \
     --batch-size 50 \
     --max-retries 3
   ```
   Optional filters: `--workspace-id <id>` or `--asset-id <id>`.

### Migration Safety Guarantees
- **Idempotent:** Already-migrated records (`storage_provider="cloudinary"`) are skipped cleanly on repeat runs with zero duplicate uploads.
- **Checksum & Size Verified:** SHA-256 and byte length are verified before and after upload.
- **Non-Destructive:** Source S3 objects and legacy database BLOBs are **never** deleted during migration, and `metadata_json.migration` records `previous_storage_provider` and `previous_storage_key`.
- **Mixed-Provider Reads:** During and after migration, `CommercialNetworkService` serves Cloudinary records via Cloudinary CDN, unmigrated `s3` records via `S3ObjectStorage`, and historical `database` records via BLOB fallback.

### Rollback Procedure
Because source S3 objects and `metadata_json.migration` (`previous_storage_provider`, `previous_storage_key`) are preserved:
1. Set `GTE_COMMERCIAL_MEDIA_PROVIDER=s3` on `gtex-api` if reverting new uploads to S3.
2. Any migrated record can be reverted to its prior provider/key using `metadata_json->'migration'->>'previous_storage_provider'` and `metadata_json->'migration'->>'previous_storage_key'`.

---

## 6. Operational Checks & Known Limitations

- **3D Stadium Perimeter Placement (`stadium_perimeter`):** Closed and non-bookable by default while 3D stadium gameplay is not open (`GTE_3D_STADIUM_ADS_ENABLED=false`). Historical database rows remain compatible.
- **Silent Brand Videos:** Brand video uploads (`brand_video`) are inspected for audio track atoms (`soun`, `mp4a`, `Opus`, `Vorbis`); videos containing audio tracks are rejected with `422 Unprocessable Entity`.
