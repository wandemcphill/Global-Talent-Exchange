# Project: GTEX 3D Football Engine

## Goals
- Stable Unity builds (Windows first)
- 15-minute match simulation
- Event-driven match system
- Lightweight performance
- Matchday 3D visual bar: Football Manager 23 class (not Flutter 2.5D)

## Rules
- Never break batchmode builds
- Avoid heavy assets unless necessary
- Prioritize performance over realism
- Keep systems modular
- Canonical FM23-class 3D path is `GTEX_OriginalVisualRuntime` + `VisualBridge` only
- Do not ship canvas/2.5D as the product match visual
- See `Docs/GTEX_VISUAL_QUALITY_BAR.md`

## Key Files
- `Assets/Scenes/GTEX_OriginalVisualRuntime.unity`
- `Assets/Code/GTEX/VisualBridge/`
- `Assets/Code/GTEX/GtexMatchRuntime.cs`
- `Assets/Code/Editor/GtexBuildTools.cs`

## Build Command
```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.3.12f1\Editor\Unity.exe' `
  -batchmode -quit -nographics `
  -buildTarget StandaloneWindows64 `
  -projectPath 'C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\Gtex_Test_Migration' `
  -executeMethod FStudio.GTEX.Editor.GtexBuildTools.BuildWindows64ProductionFromCommandLine `
  -logFile 'C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tmp\gtex_test_migration_windows_build.log'
```

## Execution Order
- Follow `GTEX_TASKS.md` for implementation order
- Only implement phases marked `READY`
- Do not start blocked phases early
- Use `GTEX_PHASED_PROMPTS.md` as the source of truth for rewritten GTEX prompts
