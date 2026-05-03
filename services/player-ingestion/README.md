# GTEX Player Ingestion Worker

Node.js worker service for production Sportmonks ingestion, Cloudinary player image storage, incremental updates, and regen generation.

## What It Does

- Queues ingestion through BullMQ:
  - `leagueQueue`
  - `teamQueue`
  - `playerQueue`
  - `regenQueue`
- Fetches Sportmonks leagues, teams, and squad players.
- Upserts players into Postgres without duplicating `player_id`.
- Stores sync checkpoints in `sync_state`.
- Avoids hot updates by comparing a stable source hash.
- Prevents overlapping scheduled/startup runs with a Redis distributed lock.
- Stores all player images in Cloudinary.
- Falls back to the original rights-cleared remote image if Cloudinary is temporarily unavailable.
- Enriches players with football-game attributes: position, overall, potential, core skills, morale, fitness, traits, and personality.
- Evolves match-aware state from live data: form, sharpness, injuries, minutes played, last rating, transfers, and team strength.
- Runs an optional season engine: double round-robin fixtures, daily matchdays, standings, fatigue, injuries, recovery, transfer-window hooks, end-of-season reset, and regen intake.
- Supports concurrent simulation competitions with league, cup, and continental schedules.
- Seeds Manager AI for each team: lineup selection, tactical plans, in-match adaptation, substitutions, and pressure.
- Writes narrative and highlight feeds for match UI/playback without colliding with the Python app's existing public `match_events` table.
- Generates launch-safe text commentary and real-time UI payloads for every structured event.
- Tracks player chemistry, youth academy intakes, and scouting reports.
- Keeps audio commentary disabled by default; ElevenLabs keys can be added later without changing the text commentary path.
- Adds storage for team tactics and transfer records.
- Exposes a lightweight `/health` endpoint and optional Sentry crash reporting.
- Uses the image fallback chain:
  - Sportmonks image
  - Wikimedia image
  - AI generated face
- Generates youth regen players per league.

## Required Env

```env
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
SPORTMONKS_BASE_URL=https://api.sportmonks.com/v3/football
SPORTMONKS_API_TOKEN=...
CLOUDINARY_URL=cloudinary://...
```

Optional:

```env
SPORTMONKS_LEAGUE_IDS=8,564,82
INGESTION_CRON=0 */6 * * *
INGESTION_RUN_ON_START=true
INGESTION_LOCK_TTL_SECONDS=3600
INGESTION_RUN_TIMEOUT_SECONDS=3300
GTEX_REGENS_PER_LEAGUE=3
CLOUDINARY_PLAYER_FOLDER=gtex/players
AUDIO_COMMENTARY_ENABLED=false
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=
WIKIMEDIA_FALLBACK_ENABLED=true
WIKIMEDIA_RIGHTS_CLEARED_DEFAULT=false
SPORTMONKS_UPDATED_SINCE_SUPPORTED=false
HEALTH_SERVER_ENABLED=true
HEALTH_PORT=3000
SENTRY_DSN=
NODE_OPTIONS=--max-old-space-size=512
SEASON_ENGINE_ENABLED=false
SEASON_CRON=15 0 * * *
SEASON_FIXTURES_PER_DAY=1
SEASON_REGENS_PER_SEASON=12
SEASON_TRANSFERS_ENABLED=false
SEASON_TRANSFER_WINDOWS=2026-01-01:2026-01-31,2026-08-01:2026-08-31
```

## Commands

```bash
npm install
npm run migrate
npm run once
npm run worker
npm run scheduler
npm start
npm run season:create -- --name "GTEX 2026" --league-id 8 --start 2026-08-01
npm run competition:create -- --season-id 1 --name "GTEX Cup" --type cup --teams 1,2,3,4 --start 2026-08-05
npm run season:tick -- --date 2026-08-01
npm run season:standings -- --season-id 1
npm run scout:create -- --team-id 1 --region Nigeria --min-potential 75
npm run scout:run -- --assignment-id 1
```

`npm start` runs workers and scheduler in one process. For production, it is cleaner to run workers and scheduler as separate services if traffic grows.

The scheduler and startup trigger both use the same Redis lock. If a previous ingestion cycle is still running, the next cycle logs `ingestion_lock_skipped` and exits without queuing duplicate work. Successful cycles update `sync_state` with key `players` after the queues are idle.

## Database

Migration file:

```text
services/player-ingestion/migrations/001_players_sync_state.sql
```

It creates:

- `players`
- `sync_state`
- `tactics`
- `transfers`
- operational indexes

The requested `players` columns are present. Extra operational columns keep incremental updates safe: `source_hash`, `source_provider`, `league_id`, `team_id`, and `image_source`.

Match-aware fields are added by `003_match_influence_state.sql`: `form`, `sharpness`, `is_injured`, `injury_return_date`, `minutes_played`, and `last_match_rating`. The worker recalculates `teams.strength` after player updates and records Sportmonks team changes in `transfers`.

Season tables are added by `004_season_engine.sql`: `seasons`, `fixtures`, and `standings`. The season engine is disabled by default in Render until `SEASON_ENGINE_ENABLED=true` is set.

Competition, manager, narrative, and highlight tables are added by `005_competitions_manager_narrative_highlights.sql`. They use prefixed names (`season_competitions`, `season_managers`, `season_match_events`) because the Python backend already owns app-facing competition and match-event tables.

Relationships, youth academies, scouting, and optional audio fields are added by `006_universe_relationships_scouting_audio.sql`. Chemistry is stored in `season_player_relationships`; youth intake state in `season_youth_academies`; scouting assignments and reports in `season_scouting_assignments` and `season_scouting_reports`.

## Match/Tactics Scope

The existing GTEX Python backend already owns the public match engine, scouting, transfer market, and player progression flows. This Node worker does not replace those systems. It provides ingestion-ready football attributes and pure helper logic in `src/simulation.js` so downstream workers can consume the same tactical/trait model without duplicating player ingestion.

Use `repository.getMatchTeamSnapshot(teamId)` plus `simulation.buildMatchPlayer(player)` when the match engine needs current state. Injured players are filtered from snapshots, while form and sharpness alter effective stats and stamina.

`src/seasonEngine.js` uses the same match snapshot path. Played fixtures write results, standings, player fatigue, injury risk, form updates, and team strength back to the database. Automatic AI transfers are behind `SEASON_TRANSFERS_ENABLED` to keep the world stable for launch.

Manager AI lives in `src/managerAI.js`; narratives in `src/narrativeEngine.js`; structured highlight/event generation in `src/highlightEvents.js`. Highlight rows include `animation_key` so a future playback surface can map events cleanly without exposing launch-blocked 3D routes.

Text commentary lives in `src/commentaryEngine.js`; optional audio metadata is brokered through `src/audioCommentary.js` and remains disabled until audio storage/streaming is explicitly approved. Flutter can consume the stored `live_payload` shape directly: `{ minute, event, player, team, score, commentary }`.

Chemistry lives in `src/relationships.js`; youth generation in `src/youthAcademy.js`; scouting filters and reports in `src/scoutingNetwork.js` and `src/scoutingService.js`.

## Production Notes

- Do not set `SPORTMONKS_BASE_URL` to the full URL with `api_token`; keep the token in `SPORTMONKS_API_TOKEN`.
- Do not hotlink Sportmonks/Wikimedia images in app UI. This worker uploads them to Cloudinary and stores the Cloudinary URL.
- The remote-image fallback is only a safety net for temporary Cloudinary failures; the next successful run will replace it with the CDN URL.
- If Sportmonks `updated_since` filters are not available on your plan, leave `SPORTMONKS_UPDATED_SINCE_SUPPORTED=false`; the worker still compares stable hashes before updating rows.
