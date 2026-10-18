# N53 — National Team API Contract Fix Report

Date: 2026-06-14
Branch: main (working branch `deployment/supabase-cloudflare`, fast-forwards to main)

## Problem

`tools/audit/check_api_contract_violations.py` reported exactly 2 violations:

```
frontend/lib/data/national_team_api.dart -> /api/national/countries
frontend/lib/data/national_team_api.dart -> /api/national/teams
```

Root cause (pre-existing on main, proven by checking out base `c45d422d`): the
frontend called `/api/national/countries` and `/api/national/teams`, which are
**not declared in the contract and not served by the backend**. They would 404 at
runtime. The correct, already-existing backend endpoints are:

```
/api/market/nationalities      (declared alias of /api/v2/market/nationalities)
/api/market/national-teams     (declared alias of /api/v2/market/national-teams)
```

## 1. Backend response schemas (inspected)

`backend/app/market/router.py` → `backend/app/market/service.py`.

**`GET /api/market/nationalities`** → top-level JSON **array**, each element:

| key | type | notes |
|---|---|---|
| `country_code` | str | e.g. `"NG"` |
| `slug` | str | slug of display name |
| `display_name` | str | e.g. `"Nigeria"` |
| `flag_url` | str \| null | currently null |
| `eligible_player_count` | int | |

**`GET /api/market/national-teams`** → top-level JSON **array**, each element:

| key | type | notes |
|---|---|---|
| `team_id` | str | equals `country_code` |
| `country_code` | str | |
| `slug` | str | |
| `display_name` | str | e.g. `"Nigeria National Team"` |
| `flag_url` | str \| null | |
| `eligible_player_count` | int | |

## 2. Schema comparison vs frontend expectations

`national_team_api.dart` `_mapListPayload` already accepts **both** a top-level
array and a `{countries|teams|items|results: [...]}` envelope, so the array shape
needs no change at the API layer — `listCountries`/`listTeams` return raw
`List<Map<String, dynamic>>`.

The consumer `gtex_national_team_rental_screen_v2.dart` reads each row with
multi-key lookups. Comparison:

| Field | Consumer lookup keys | Backend key | Match before | Action |
|---|---|---|---|---|
| Country code | `country_code`, `code` | `country_code` | ✅ | none |
| Country name | `country_name`, `name`, `label` | `display_name` | ❌ → "Country not returned" | **add `display_name`** |
| Eligible count | `eligible_players`, `eligible_player_count`, `player_count` | `eligible_player_count` | ✅ | none |
| Confederation | `confederation`, `federation`, `region` | (not provided) | fallback "Backend authority" | acceptable |
| Flag | `flag_emoji`, `flag` | `flag_url` (null) | empty | acceptable (decorative) |
| Team id | `id`, `team_id` | `team_id` | ✅ | none |
| Team name | `name`, `team_name`, `country_name` | `display_name` | ❌ → "Team not returned" | **add `display_name`** |

**Only mismatch:** display name lives under `display_name`. Fixed by adding
`display_name` to the existing lookup lists — a legitimate key alias, not a hack,
fallback, or typing change.

## 3. Changes (before → after)

| File | Before | After |
|---|---|---|
| `frontend/lib/data/national_team_api.dart:78` | `/api/national/countries` | `/api/market/nationalities` |
| `frontend/lib/data/national_team_api.dart:98` | `/api/national/teams` | `/api/market/national-teams` |
| `gtex_national_team_rental_screen_v2.dart` (country name) | `['country_name','name','label']` | `['country_name','display_name','name','label']` |
| `gtex_national_team_rental_screen_v2.dart` (team name) | `['name','team_name','country_name']` | `['name','team_name','display_name','country_name']` |

`display_name` is inserted after the existing first-priority keys, so any
fixture/stub already supplying `country_name`/`name` is unaffected (the widget
test's expectations are preserved).

No mocks, no fake routes, no business-logic change, no weakened typing, no silent
fallbacks. Query params previously passed (`competition_id`, `country_code`) are
harmlessly ignored by the market catalog endpoints (FastAPI drops unknown query
params), so no runtime error.

## 4. Validation evidence

**Contract checker:**
```
$ python tools/audit/check_api_contract_violations.py
[api-contract] No contract violations detected.   (exit 0)
docs/CONTRACT_VIOLATIONS.md → "Violations detected: 0"
```

**Flutter analyze:**
```
$ flutter analyze
No issues found! (ran in 483.4s)   (exit 0)
```

**Targeted test:**
```
$ flutter test test/national_teams/national_team_rental_screen_v2_test.dart
+1: national rental V2 loads country and team authority before the pool
All tests passed!   (exit 0)
```

**No stale references:** `grep` for `api/national/countries` / `api/national/teams`
across `frontend/` and `shared/` → none remaining.

## Verdict

Contract violations: **0**. Flutter analyze: **0 issues**. National-team test:
**pass**. No regressions. Frontend now calls real, contract-declared endpoints.
