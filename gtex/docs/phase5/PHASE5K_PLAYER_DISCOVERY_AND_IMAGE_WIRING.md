# Phase 5K — Player discovery and image wiring boundary

## Purpose

Move the shipped app forward while production database writes are temporarily unavailable.

## Verified problem

The live Transfer Market provider currently fetches `/players/markets` for the initial player surface, but only calls the real-player discovery endpoint `/players` when the user has entered a search string. This means a production database can contain a large real-player universe while the default market screen renders zero players when there are no active share markets.

The frontend already has a live `PlayerService.getPlayers()` implementation backed by `GET /players`, and the backend already exposes a real-player universe query service filtered to `Player.is_real_player = true`.

## Scope

- Always load the real-player discovery page for the initial market browse state, not only when search text is present.
- Continue overlaying active share markets on the real-player discovery results.
- Keep discovery and tradability distinct: a player can be visible without a live share market.
- Do not invent players, clubs, leagues, market status, valuation, or images.
- Do not modify production database state.
- Keep existing pagination behavior and current market/transfer-listing surfaces intact.

## Image investigation boundary

The `Player` frontend mapper already accepts `image_url`, `portrait_url`, and profile-image variants from the player payload and nested summary/metadata fields. The remaining image problem must therefore be verified against the real backend response and Cloudinary object availability when production read access is available.

Do not hardcode a replacement image URL merely because the UI is missing a portrait.

## Blocked production verification

Until the production database becomes write-capable again, we cannot truthfully execute ingestion repair, re-publish missing real players, repair country/club data, or verify database-backed image rows in production.

## Next production pass

1. Verify the actual `GET /players` total and page contents.
2. Verify the active share-market total separately.
3. Verify clubs/leagues/countries separately rather than treating the player count as proof.
4. Sample real player image URLs and verify Cloudinary HTTP availability.
5. Repair ingestion/publication/issuance only after write access is restored.
