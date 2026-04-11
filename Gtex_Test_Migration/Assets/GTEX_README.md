GTEX FootballSimulator Upgrade

Unity target:
- Unity 6.3 LTS (`6000.3.12f1`)

What changed:
- GTEX boot path added in `Code/Boot.cs`
- Live polling client for `GET /match/{id}/live`
- Match response models: `MatchResponse`, `Event`, `PlayerPosition`
- Backend-authoritative playback mode added to the match engine
- Retry with last-known-state fallback
- Configurable base URL and startup config in `Resources/GTEX/match-config.json`
- Exact scoreboard sync from backend state
- Stadium atmosphere upgrade layer:
  crowd stands, perimeter LED boards, floodlights, lighting/fog polish, and broadcast rig dressing

GTEX code location:
- `Code/GTEX/`

Startup:
1. Open `Resources/GTEX/match-config.json`
2. Set `matchId`
3. Set `environment` to `local`, `production`, or `custom`
4. Update the corresponding base URL
5. Keep `autoStartOnBoot` enabled if you want the match to launch directly on boot

Notes:
- The original FootballSimulator local match AI is bypassed when GTEX playback mode is enabled.
- Unity remains the visual runtime while GTEX remains the match authority.
- Crowd and stadium upgrades are runtime-generated so they do not depend on extra purchased art packs.
