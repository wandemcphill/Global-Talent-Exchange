# Final polish and special coach pass

## Implemented in this pass

### 1. Creator and admin premium copy sweep
- Upgraded creator dashboard into a clearer `Creator command deck`.
- Upgraded creator profile into a clearer `Creator profile deck`.
- Added premium intro state panels to both creator surfaces.
- Added retry actions to creator error states.
- Added creator-specific empty states for no competitions.
- Tightened manager admin wording so it reads more like a premium control tower.
- Renamed manager search copy to coach-oriented language where appropriate.

### 2. Manager market state cleanup
- Renamed the top app bar from `Managers Market` to `Coach Exchange`.
- Tightened empty/error headings for team assignment and catalog filter states.
- Improved bench and filter copy so the coach lane reads more intentionally.

### 3. Special coach added
Added a custom special coach to the backend seed catalog:
- Name: `Tunde Oni`
- Nationality signal: `Nigeria`
- Mentality: `balanced`
- Adapted tactics: `counter_attack`, `technical_build_up`, `set_piece_focus`, `youth_development_system`
- Adapted traits: `develops_young_players`, `tactical_flexibility`, `technical_coaching`, `quick_substitution`
- Philosophy summary now captures the requested formation family and style: 3-4-3, 4-1-2-1-2 diamond, 4-4-2, 3-4-1-2, short passing through the middle, and counters against stronger teams.

### 4. Test coverage
Added a backend test to assert the seeded coach exists with the expected adapted mentality, tactics, traits, and philosophy markers.

## Files changed
- `backend/app/manager_market/seed_catalog.py`
- `backend/tests/manager_market/test_seed_catalog.py`
- `frontend/lib/screens/creators/creator_dashboard_screen.dart`
- `frontend/lib/screens/creators/creator_profile_screen.dart`
- `frontend/lib/screens/admin/manager_admin_screen.dart`
- `frontend/lib/screens/manager_market_screen.dart`

## Notes
- The tactical/trait template was adapted to the existing manager-market vocabulary so the new coach remains compatible with current scoring and recommendation logic.
- I also kept cleanup standards by excluding `__pycache__`, `.pyc`, and `.pyo` from the rebuilt project archive.
