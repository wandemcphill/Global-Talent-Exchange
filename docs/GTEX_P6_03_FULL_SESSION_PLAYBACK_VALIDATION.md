# GTEX P6-03 Full-Session Playback Validation

## Scope

This document captures the committed validation lane for `P6-03`:
- bootstrap through full time on the current-engine path
- moving players
- moving ball
- stable camera behavior
- score and clock continuity
- scene stability with saved artifacts

`P6-03` is not passed by source inspection alone. It needs an exercised full-session run plus retained logs and screenshots.

## Committed Validation Assets

The repo now includes a dedicated full-session validation harness:
- mock backend server: [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tools\gtex_live_full_session_mock_server.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tools/gtex_live_full_session_mock_server.py>)
- Windows player runner: [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tools\run_gtex_full_session_validation.ps1](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tools/run_gtex_full_session_validation.ps1>)
- screenshot capture helper reused by the runner: [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tools\capture_gtex_player_session.ps1](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tools/capture_gtex_player_session.ps1>)

## Session Scenario

Match id:
- `live-full-session-test`

Controlled scenario:
- live bootstrap starts from kickoff
- websocket frames advance the clock from first half through halftime and second half to full time
- scoreline progresses `0-0 -> 1-0 -> 1-1 -> 2-1`
- camera presets rotate through the shipped preset mapping without transport errors
- player and ball motion stay active during the live phases
- final websocket frame delivers a terminal `fulltime` state

## Pass Criteria

The run passes only if all of the following are true:
- bootstrap finished on the shipped Windows player
- runtime trace recorded active player motion
- runtime trace recorded non-zero ball motion
- runtime trace clock and score never regressed
- halftime, second-half, and full-time phases were all exercised
- final frame reached `90'` / full time
- the player log showed normal camera switching without runtime exceptions
- screenshot capture produced an early, mid, and late-session image set

## How To Run

PowerShell:

```powershell
& 'C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tools\run_gtex_full_session_validation.ps1'
```

Artifacts written by the runner:
- summary: [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tmp\gtex_full_session_summary.json](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_full_session_summary.json>)
- capture output directory: [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tmp\gtex_full_session_capture](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_full_session_capture>)
- server logs:
  - [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tmp\gtex_full_session_server.out.log](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_full_session_server.out.log>)
  - [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tmp\gtex_full_session_server.err.log](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_full_session_server.err.log>)

## Executed Evidence

Execution date:
- `2026-04-22`

Runner command:

```powershell
& 'C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tools\run_gtex_full_session_validation.ps1'
```

Result:
- full-session harness summary returned `passed: true`
- bootstrap, motion, score continuity, phase continuity, and full-time completion all passed
- screenshot capture produced three saved checkpoints across the run

Observed proof:
- the shipped Windows player completed bootstrap and applied a continuous live session from kickoff through `90'`
- runtime trace showed moving players and non-zero ball motion across the live phases
- runtime trace advanced through `FirstHalf`, `HalfTime`, `SecondHalf`, and `FullTime`
- the final applied state reached `90'` with score `2-1`
- backend summary preserved the expected score timeline `0-0 -> 1-0 -> 1-1 -> 2-1`
- screenshot capture produced early, mid, and late-session images from the shipped player window

Saved artifacts:
- summary: [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tmp\gtex_full_session_summary.json](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_full_session_summary.json>)
- capture output directory: [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tmp\gtex_full_session_capture](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_full_session_capture>)
- captured screenshots:
  - [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tmp\gtex_full_session_capture\gtex_full_session_validation_t0012s.png](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_full_session_capture/gtex_full_session_validation_t0012s.png>)
  - [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tmp\gtex_full_session_capture\gtex_full_session_validation_t0024s.png](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_full_session_capture/gtex_full_session_validation_t0024s.png>)
  - [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tmp\gtex_full_session_capture\gtex_full_session_validation_t0042s.png](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_full_session_capture/gtex_full_session_validation_t0042s.png>)
- server logs:
  - [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tmp\gtex_full_session_server.out.log](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_full_session_server.out.log>)
  - [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tmp\gtex_full_session_server.err.log](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_full_session_server.err.log>)
- runtime trace:
  - [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tmp\gtex_full_session_capture\gtex_full_session_validation.runtime.log](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_full_session_capture/gtex_full_session_validation.runtime.log>)
- session metadata:
  - [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tmp\gtex_full_session_capture\gtex_full_session_validation.metadata.txt](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_full_session_capture/gtex_full_session_validation.metadata.txt>)

## Current Status

Current status: `PASSED`
