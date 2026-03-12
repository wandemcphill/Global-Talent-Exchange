Backend follow-up: align `/api/clubs/{club_id}/dynasty` with the detector-based dynasty schema.

Current mismatch

- `/api/clubs/{club_id}/dynasty` still returns legacy `ClubDynastyView` from `backend/app/segments/clubs/segment_clubs.py`.
- That payload is `progress` plus `milestones`, not the richer detector profile already exposed by:
  - `/api/clubs/{club_id}/dynasty/history`
  - `/api/clubs/{club_id}/eras`
  - `/api/leaderboards/dynasties`
- The frontend currently compensates by calling `/dynasty/history` and merging the richer fields back into the overview flow.

Target contract

- Make `/api/clubs/{club_id}/dynasty` return `ClubDynastyProfileView` from `backend/app/club_identity/dynasty/api/schemas.py`.
- Keep the response fields aligned with the existing detector outputs:
  - `club_id`
  - `club_name`
  - `dynasty_status`
  - `current_era_label`
  - `active_dynasty_flag`
  - `dynasty_score`
  - `active_streaks`
  - `last_four_season_summary`
  - `reasons`
  - `current_snapshot`
  - `dynasty_timeline`
  - `eras`
  - `events`

Recommended backend steps

1. Move the canonical `/api/clubs/{club_id}/dynasty` handler onto `DynastyQueryService.get_profile`.
2. Return `ClubDynastyProfileView.model_validate(profile)` instead of `ClubDynastyView(progress=..., milestones=...)`.
3. Preserve the old progress-and-milestones data only if another live consumer still needs it.
4. If legacy consumers exist, expose that payload on a separate compatibility endpoint instead of keeping the canonical club dynasty route split across two schemas.
5. Add backend tests that assert `/api/clubs/{club_id}/dynasty` matches the same snake_case profile shape used by the dynasty module schemas.

Frontend cleanup once backend lands

1. Remove the legacy payload detection in `dynasty_api_repository.dart`.
2. Stop enriching overview data from `/dynasty/history` during normal profile loads.
3. Keep the history-to-eras fallback only for `/api/clubs/{club_id}/eras` outages.
