# GTEX screen completion — Command Center

## Home surface map

| Area | Authoritative source today | Command Center treatment |
| --- | --- | --- |
| Identity / club context | `profileDataProvider` | masthead identity block; truthful guest fallback |
| Economy / player discovery | `marketDashboardProvider` | capital and player metrics; detailed market module retained |
| Competition | `competitionHubProvider` | direct action and competition metric; live module retained |
| Progression / reward rhythm | `liveTasksProvider` | daily rhythm metric; task panel retained |
| World / social signals | `worldAggregateProvider` | existing world pulse rail retained |
| Ownership / movement / activity | `homeDigestProvider` | existing personalized sections retained |
| Notifications | notification routes and backend payloads | not duplicated; destination remains available in shell |

## States completed in this slice

- guest preview: labelled identity and sign-in action;
- signed-in member: live metrics and direct competition/market actions;
- data loading: individual metric labels show `Loading` rather than fake data;
- missing wallet authority: `Locked` rather than zero balance;
- no club / no owned assets / no market movement: existing truthful route-level
  panels or absent digest sections remain in effect.

Active match and competition details continue to be supplied by their existing
authoritative routes; Home does not fabricate a fixture to populate the
masthead.

## Competition command surface (Slice 4)

| Area | Authoritative source | Treatment |
| --- | --- | --- |
| Hub families | `competitionHubProvider` | GTEX, hosted, and creator lists stay visibly distinct. |
| GTEX detail | `gtexCompetitionDetailProvider(id)` | metadata, financial contract, standings, and fixtures are fetched together; any live-provider failure is unavailable, not a fabricated empty detail. |
| Participation | `CompetitionJoinEligibility` and `CompetitionApi.joinCompetition` | sign-in, locked, invite/passcode, eligible, and join-in-flight states are explicit. |
| Matchday path | fixture `match_key` | the existing `/matches/viewer/:matchKey` route is offered only when supplied by the fixture. |

The canonical shell now mounts the provider-backed Competition Command surface.
It does not use the prior V2 adapter's synthetic empty fixtures, standings, or
derived lifecycle content.
