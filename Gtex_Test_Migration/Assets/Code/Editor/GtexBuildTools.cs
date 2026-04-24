#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Threading;
using Stopwatch = System.Diagnostics.Stopwatch;
using FStudio.GTEX.Core;
using UnityEditor;
using UnityEditor.AddressableAssets;
using UnityEditor.AddressableAssets.Settings;
using UnityEditor.Android;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace FStudio.GTEX.Editor
{
    public static class GtexBuildTools
    {
        private const string AndroidFileName = "GTEXMatch.apk";
        private const string WindowsFileName = "GTEXMatch.exe";
        private const string BuildLogDirectoryName = "builds";
        private const string BuildLogPrefix = "[GTEX Build]";

        [MenuItem("Tools/GTEX/Build/Windows x64")]
        public static void BuildWindows64Menu()
        {
            var outputPath = EditorUtility.SaveFilePanel(
                "Build GTEX Windows Player",
                ResolvePlatformBuildDirectory("Windows"),
                Path.GetFileNameWithoutExtension(WindowsFileName),
                "exe");

            if (string.IsNullOrWhiteSpace(outputPath))
            {
                return;
            }

            RunBuild(
                "Windows x64 (Menu)",
                outputPath,
                BuildTargetGroup.Standalone,
                BuildTarget.StandaloneWindows64);
        }

        [MenuItem("Tools/GTEX/Build/Windows x64 (Production)")]
        public static void BuildWindows64ProductionMenu()
        {
            var outputPath = EditorUtility.SaveFilePanel(
                "Build GTEX Windows Player (Production)",
                ResolvePlatformBuildDirectory("WindowsProduction"),
                Path.GetFileNameWithoutExtension(WindowsFileName),
                "exe");

            if (string.IsNullOrWhiteSpace(outputPath))
            {
                return;
            }

            RunBuild(
                "Windows x64 Production (Menu)",
                outputPath,
                BuildTargetGroup.Standalone,
                BuildTarget.StandaloneWindows64,
                null,
                GtexMode.Production);
        }

        [MenuItem("Tools/GTEX/Build/WebGL")]
        public static void BuildWebGLMenu()
        {
            var outputPath = EditorUtility.OpenFolderPanel(
                "Build GTEX WebGL Player",
                ResolvePlatformBuildDirectory("WebGL"),
                string.Empty);

            if (string.IsNullOrWhiteSpace(outputPath))
            {
                return;
            }

            RunBuild(
                "WebGL (Menu)",
                outputPath,
                BuildTargetGroup.WebGL,
                BuildTarget.WebGL);
        }

        [MenuItem("Tools/GTEX/Build/Android APK")]
        public static void BuildAndroidApkMenu()
        {
            var outputPath = EditorUtility.SaveFilePanel(
                "Build GTEX Android APK",
                ResolvePlatformBuildDirectory("Android"),
                Path.GetFileNameWithoutExtension(AndroidFileName),
                "apk");

            if (string.IsNullOrWhiteSpace(outputPath))
            {
                return;
            }

            BuildAndroidApk("Android APK (Menu)", outputPath);
        }

        [MenuItem("Tools/GTEX/Build/Android Export Library")]
        public static void ExportAndroidLibraryMenu()
        {
            ExportAndroidLibrary("Android Export Library (Menu)", ResolveAndroidLibraryExportPath());
        }

        public static void BuildWindows64FromCommandLine()
        {
            WriteCommandLineInvocationMarker("BuildWindows64FromCommandLine");
            RunBuild(
                "Windows x64 (Command Line)",
                ResolveDefaultBuildPath(BuildTarget.StandaloneWindows64),
                BuildTargetGroup.Standalone,
                BuildTarget.StandaloneWindows64);
        }

        public static void BuildWindows64ProductionFromCommandLine()
        {
            WriteCommandLineInvocationMarker("BuildWindows64ProductionFromCommandLine");
            RunBuild(
                "Windows x64 Production (Command Line)",
                ResolveDefaultBuildPath(BuildTarget.StandaloneWindows64, GtexMode.Production),
                BuildTargetGroup.Standalone,
                BuildTarget.StandaloneWindows64,
                null,
                GtexMode.Production);
        }

        public static void BuildWebGLFromCommandLine()
        {
            WriteCommandLineInvocationMarker("BuildWebGLFromCommandLine");
            RunBuild(
                "WebGL (Command Line)",
                ResolveDefaultBuildPath(BuildTarget.WebGL),
                BuildTargetGroup.WebGL,
                BuildTarget.WebGL);
        }

        public static void BuildAndroidApkFromCommandLine()
        {
            WriteCommandLineInvocationMarker("BuildAndroidApkFromCommandLine");
            var outputPath = ResolveAndroidApkOutputPath();
            LogBatchCheckpoint(
                "ENTER BuildAndroidApkFromCommandLine",
                outputPath);

            try
            {
                LogBatchCheckpoint(
                    "BEFORE BUILD APK",
                    outputPath);
                BuildAndroidApk("Android APK (Command Line)", outputPath);
                LogBatchCheckpoint(
                    "AFTER BUILD APK",
                    outputPath);

                if (!File.Exists(outputPath))
                {
                    throw new FileNotFoundException(
                        "[GTEX Build] Expected APK missing at: " + outputPath);
                }

                Debug.Log("[GTEX Build] APK verified at: " + outputPath);
            }
            catch (Exception ex)
            {
                Debug.LogError("[GTEX Build] FAIL BuildAndroidApkFromCommandLine\n" + ex);
                throw;
            }
        }

        public static void ExportAndroidLibraryFromCommandLine()
        {
            WriteCommandLineInvocationMarker("ExportAndroidLibraryFromCommandLine");
            var outputPath = ResolveAndroidExportOutputPath();
            LogBatchCheckpoint(
                "ENTER ExportAndroidLibraryFromCommandLine",
                outputPath);

            try
            {
                LogBatchCheckpoint(
                    "BEFORE EXPORT ANDROID LIBRARY",
                    outputPath);
                ExportAndroidLibrary(
                    "Android Export Library (Command Line)",
                    outputPath);
                LogBatchCheckpoint(
                    "AFTER EXPORT ANDROID LIBRARY",
                    outputPath);

                var unityLibraryPath = Path.Combine(outputPath, "unityLibrary");
                if (!Directory.Exists(unityLibraryPath))
                {
                    throw new DirectoryNotFoundException(
                        "[GTEX Build] Expected unityLibrary missing at: " + unityLibraryPath);
                }

                Debug.Log("[GTEX Build] unityLibrary verified at: " + unityLibraryPath);
            }
            catch (Exception ex)
            {
                Debug.LogError("[GTEX Build] FAIL ExportAndroidLibraryFromCommandLine\n" + ex);
                throw;
            }
        }

        private static void WriteCommandLineInvocationMarker(string methodName)
        {
            try
            {
                var markerDirectory = ResolveTraceLogDirectory();
                var markerPath = Path.Combine(markerDirectory, "command-line-invocations.log");
                var line = DateTime.Now.ToString("O") + " " + methodName + Environment.NewLine;
                File.AppendAllText(markerPath, line);
            }
            catch (Exception exception)
            {
                Debug.LogWarning(BuildLogPrefix + " Failed to write command-line invocation marker: " + exception.Message);
            }
        }

        private static void RunBuild(
            string buildLabel,
            string outputPath,
            BuildTargetGroup targetGroup,
            BuildTarget target,
            Action preBuildValidation = null,
            GtexMode? buildModeOverride = null,
            BuildOptions buildOptions = BuildOptions.None,
            Action<string, BuildTarget, BuildTraceSession> postBuildValidation = null)
        {
            BuildTraceSession trace = null;
            BuildModeScope buildModeScope = null;
            BuildEnvironmentScope buildEnvironment = null;

            try
            {
                trace = BuildTraceSession.Start(buildLabel, target, outputPath);

                trace.Stage("Build requested");
                trace.Info("Unity version: " + Application.unityVersion);
                trace.Info("Batch mode: " + Application.isBatchMode);
                trace.Info("Target group: " + targetGroup);
                trace.Info("Target: " + target);
                trace.Info("Output path: " + outputPath);

                var buildMode = ResolveBuildMode(buildModeOverride);
                trace.Stage("Applying GTEX build mode");
                buildModeScope = BuildModeScope.Enter(targetGroup, buildMode, trace);

                if (preBuildValidation != null)
                {
                    trace.Stage("Running pre-build validation");
                    preBuildValidation();
                    trace.Info("Pre-build validation complete");
                }

                trace.Stage("Resolving build scenes");
                var scenes = ResolveBuildScenes(trace, buildMode);
                if (scenes.Length == 0)
                {
                    throw new InvalidOperationException(
                        "No scenes are available to build. Save the active scene or add enabled scenes to Build Settings.");
                }

                trace.Info("Resolved scenes (" + scenes.Length + "):");
                for (int index = 0; index < scenes.Length; index += 1)
                {
                    trace.Info("  [" + index + "] " + scenes[index]);
                }

                trace.Stage("Ensuring output directory");
                EnsureOutputDirectory(outputPath, target);

                trace.Stage("Switching active build target");
                SwitchActiveBuildTarget(targetGroup, target, trace);

                trace.Stage("Applying build environment");
                buildEnvironment = BuildEnvironmentScope.Enter(buildMode, trace);

                trace.Stage("Cleaning stale Bee state");
                CleanupStaleBeeState(trace);

                trace.Stage("Preparing build options");
                var options = new BuildPlayerOptions
                {
                    scenes = scenes,
                    target = target,
                    locationPathName = outputPath,
                    options = buildOptions
                };

                trace.Stage("Invoking BuildPipeline.BuildPlayer");
                var report = BuildPipeline.BuildPlayer(options);
                LogBuildSummary(report.summary, trace);

                if (report.summary.result != BuildResult.Succeeded)
                {
                    throw new InvalidOperationException(
                        "Build failed with result: " + report.summary.result +
                        ", errors: " + report.summary.totalErrors +
                        ", warnings: " + report.summary.totalWarnings);
                }

                if (postBuildValidation != null)
                {
                    trace.Stage("Running post-build validation");
                    postBuildValidation(outputPath, target, trace);
                }

                trace.Stage("Build completed successfully");
                trace.Info("Companion trace file: " + trace.TraceFilePath);
                Debug.Log(BuildLogPrefix + " Build complete: " + outputPath);
            }
            catch (Exception exception)
            {
                if (trace != null)
                {
                    trace.Error("Build failed: " + exception);
                    trace.Info("Companion trace file: " + trace.TraceFilePath);
                }

                Debug.LogError(BuildLogPrefix + " Build failed.");
                Debug.LogException(exception);
                throw;
            }
            finally
            {
                buildEnvironment?.Dispose();
                buildModeScope?.Dispose();
                trace?.Dispose();
            }
        }

        private static string[] ResolveBuildScenes(BuildTraceSession trace, GtexMode buildMode)
        {
            var preferredScenes = GtexSceneLoader.ResolveBuildScenePaths(buildMode)
                .Where(GtexSceneLoader.SceneExists)
                .ToArray();

            if (preferredScenes.Length > 0)
            {
                trace.Info("Using GTEX " + buildMode + " build scenes.");
                return preferredScenes;
            }

            var configuredScenes = EditorBuildSettings.scenes ?? Array.Empty<EditorBuildSettingsScene>();
            trace.Info("Scenes in Build Settings: " + configuredScenes.Length);

            var enabledScenes = EditorBuildSettings.scenes
                .Where(scene => scene.enabled && !string.IsNullOrWhiteSpace(scene.path))
                .Select(scene => scene.path)
                .ToArray();

            if (enabledScenes.Length > 0)
            {
                trace.Info("Using enabled scenes from Build Settings.");
                return enabledScenes;
            }

            var activeScene = EditorSceneManager.GetActiveScene();
            if (!string.IsNullOrWhiteSpace(activeScene.path))
            {
                trace.Warn(
                    "No enabled scenes were found in Build Settings. Falling back to the active scene: " +
                    activeScene.path);
                return new[] { activeScene.path };
            }

            trace.Error("No enabled build scenes and no saved active scene are available.");
            return Array.Empty<string>();
        }

        private static GtexMode ResolveBuildMode(GtexMode? buildModeOverride = null)
        {
            if (buildModeOverride.HasValue)
            {
                return buildModeOverride.Value;
            }

            return Application.isBatchMode
                ? GtexMode.Development
                : GtexMode.Production;
        }

        private static string MergeGtexSymbols(string existingSymbols, GtexMode buildMode)
        {
            var symbols = (existingSymbols ?? string.Empty)
                .Split(new[] { ';' }, StringSplitOptions.RemoveEmptyEntries)
                .Where(symbol =>
                    !string.Equals(symbol, "GTEX_DEV", StringComparison.Ordinal) &&
                    !string.Equals(symbol, "GTEX_FAST_MODE", StringComparison.Ordinal) &&
                    !string.Equals(symbol, "GTEX_PROD", StringComparison.Ordinal))
                .ToList();

            if (buildMode == GtexMode.Development)
            {
                symbols.Add("GTEX_DEV");
                symbols.Add("GTEX_FAST_MODE");
            }
            else
            {
                symbols.Add("GTEX_PROD");
            }

            return string.Join(";", symbols.Distinct().ToArray());
        }

        private sealed class BuildModeScope : IDisposable
        {
            private readonly NamedBuildTarget namedBuildTarget;
            private readonly string previousSymbols;
            private readonly string updatedSymbols;
            private readonly BuildTargetGroup targetGroup;
            private readonly BuildTraceSession trace;
            private bool disposed;

            private BuildModeScope(
                NamedBuildTarget namedBuildTarget,
                BuildTargetGroup targetGroup,
                string previousSymbols,
                string updatedSymbols,
                BuildTraceSession trace)
            {
                this.namedBuildTarget = namedBuildTarget;
                this.targetGroup = targetGroup;
                this.previousSymbols = previousSymbols;
                this.updatedSymbols = updatedSymbols;
                this.trace = trace;
            }

            public static BuildModeScope Enter(
                BuildTargetGroup targetGroup,
                GtexMode buildMode,
                BuildTraceSession trace)
            {
                var namedBuildTarget = NamedBuildTarget.FromBuildTargetGroup(targetGroup);
                var existingSymbols = PlayerSettings.GetScriptingDefineSymbols(namedBuildTarget);
                var updatedSymbols = MergeGtexSymbols(existingSymbols, buildMode);
                trace.Info("Build mode: " + buildMode);
                trace.Info("Scripting define symbols: " + updatedSymbols);

                if (string.Equals(existingSymbols, updatedSymbols, StringComparison.Ordinal))
                {
                    trace.Info("Scripting define symbols already match the requested build mode.");
                    return new BuildModeScope(namedBuildTarget, targetGroup, existingSymbols, updatedSymbols, trace);
                }

                PlayerSettings.SetScriptingDefineSymbols(namedBuildTarget, updatedSymbols);
                AssetDatabase.SaveAssets();
                trace.Info("Applied scripting define symbols for " + targetGroup + ".");
                return new BuildModeScope(namedBuildTarget, targetGroup, existingSymbols, updatedSymbols, trace);
            }

            public void Dispose()
            {
                if (disposed)
                {
                    return;
                }

                disposed = true;

                if (string.Equals(previousSymbols, updatedSymbols, StringComparison.Ordinal))
                {
                    return;
                }

                PlayerSettings.SetScriptingDefineSymbols(namedBuildTarget, previousSymbols);
                AssetDatabase.SaveAssets();
                trace.Info("Restored scripting define symbols for " + targetGroup + ": " + previousSymbols);
            }
        }

        private static void CleanupStaleBeeState(BuildTraceSession trace)
        {
            var projectRoot = Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
            var beeDirectory = Path.Combine(projectRoot, "Library", "Bee");
            if (!Directory.Exists(beeDirectory))
            {
                trace.Info("Bee state directory does not exist. Skipping cleanup.");
                return;
            }

            var staleStateFiles = Directory.GetFiles(beeDirectory, "TundraBuildState.state*");
            if (staleStateFiles.Length == 0)
            {
                trace.Info("No stale Bee state files found.");
                return;
            }

            foreach (var stateFile in staleStateFiles)
            {
                try
                {
                    File.Delete(stateFile);
                    trace.Info("Deleted stale Bee state file: " + Path.GetFileName(stateFile));
                }
                catch (Exception exception)
                {
                    trace.Warn(
                        "Failed to delete stale Bee state file '" +
                        Path.GetFileName(stateFile) +
                        "': " +
                        exception.Message);
                }
            }

            Thread.Sleep(250);
        }

        private sealed class BuildEnvironmentScope : IDisposable
        {
            private readonly AddressableAssetSettings.PlayerBuildOption? previousAddressablesBuildOption;
            private readonly int previousQualityIndex;
            private readonly string previousQualityName;
            private readonly QualitySettingsSnapshot qualitySettingsSnapshot;
            private readonly BuildTraceSession trace;
            private bool disposed;

            private BuildEnvironmentScope(
                int previousQualityIndex,
                string previousQualityName,
                QualitySettingsSnapshot qualitySettingsSnapshot,
                AddressableAssetSettings.PlayerBuildOption? previousAddressablesBuildOption,
                BuildTraceSession trace)
            {
                this.previousQualityIndex = previousQualityIndex;
                this.previousQualityName = previousQualityName;
                this.qualitySettingsSnapshot = qualitySettingsSnapshot;
                this.previousAddressablesBuildOption = previousAddressablesBuildOption;
                this.trace = trace;
            }

            public static BuildEnvironmentScope Enter(GtexMode buildMode, BuildTraceSession trace)
            {
                if (QualitySettings.names == null || QualitySettings.names.Length == 0)
                {
                    trace.Warn("No quality levels are configured. Skipping build environment changes.");
                    return null;
                }

                var previousQualityIndex = QualitySettings.GetQualityLevel();
                var previousQualityName = QualitySettings.names[Mathf.Clamp(previousQualityIndex, 0, QualitySettings.names.Length - 1)];
                var targetQualityIndex = buildMode == GtexMode.Development
                    ? Mathf.Clamp(GtexConfig.DevelopmentQualityIndex, 0, QualitySettings.names.Length - 1)
                    : Mathf.Clamp(GtexConfig.ProductionQualityIndex, 0, QualitySettings.names.Length - 1);
                var targetQualityName = QualitySettings.names[targetQualityIndex];
                QualitySettingsSnapshot qualitySettingsSnapshot = null;
                AddressableAssetSettings.PlayerBuildOption? previousAddressablesBuildOption = null;

                if (buildMode == GtexMode.Development)
                {
                    qualitySettingsSnapshot = QualitySettingsSnapshot.Capture(trace);
                    previousAddressablesBuildOption = ConfigureAddressablesForDevelopmentBuild(trace);
                    ConfigureDevelopmentRenderPipelines(targetQualityIndex, trace);
                }
                else
                {
                    trace.Info("Production build mode detected. Preserving production render pipelines and Addressables settings.");
                }

                trace.Info("Current quality level: " + previousQualityName + " (" + previousQualityIndex + ")");

                if (previousQualityIndex != targetQualityIndex)
                {
                    QualitySettings.SetQualityLevel(targetQualityIndex, true);
                    trace.Info("Applied " + buildMode + " quality level: " + targetQualityName + " (" + targetQualityIndex + ")");
                }
                else
                {
                    trace.Info(buildMode + " quality level already active: " + targetQualityName + " (" + targetQualityIndex + ")");
                }

                return new BuildEnvironmentScope(
                    previousQualityIndex,
                    previousQualityName,
                    qualitySettingsSnapshot,
                    previousAddressablesBuildOption,
                    trace);
            }

            public void Dispose()
            {
                if (disposed)
                {
                    return;
                }

                disposed = true;

                RestoreAddressablesBuildSetting();
                RestoreRenderPipelines();

                if (QualitySettings.names == null || QualitySettings.names.Length == 0)
                {
                    return;
                }

                if (QualitySettings.GetQualityLevel() == previousQualityIndex)
                {
                    trace.Info("Quality level already restored: " + previousQualityName + " (" + previousQualityIndex + ")");
                    return;
                }

                QualitySettings.SetQualityLevel(previousQualityIndex, true);
                trace.Info("Restored quality level: " + previousQualityName + " (" + previousQualityIndex + ")");
            }

            private static void ConfigureDevelopmentRenderPipelines(int targetQualityIndex, BuildTraceSession trace)
            {
                if (QualitySettings.names == null || QualitySettings.names.Length == 0)
                {
                    return;
                }

                var targetRenderPipeline = QualitySettings.GetRenderPipelineAssetAt(targetQualityIndex);
                if (targetRenderPipeline == null)
                {
                    trace.Warn("Development quality does not define a render pipeline asset. Skipping render pipeline override.");
                    return;
                }

                var previousQualityIndex = QualitySettings.GetQualityLevel();
                var changedAnyPipeline = false;

                for (var index = 0; index < QualitySettings.names.Length; index += 1)
                {
                    var previousPipeline = QualitySettings.GetRenderPipelineAssetAt(index);
                    var previousPipelineName = previousPipeline == null ? "<default>" : previousPipeline.name;

                    QualitySettings.SetQualityLevel(index, false);

                    if (previousPipeline == targetRenderPipeline)
                    {
                        trace.Info("Quality '" + QualitySettings.names[index] + "' already uses development render pipeline: " + targetRenderPipeline.name);
                        continue;
                    }

                    QualitySettings.renderPipeline = targetRenderPipeline;
                    changedAnyPipeline = true;
                    trace.Info(
                        "Assigned development render pipeline '" +
                        targetRenderPipeline.name +
                        "' to quality '" +
                        QualitySettings.names[index] +
                        "' (previous: " +
                        previousPipelineName +
                        ").");
                }

                QualitySettings.SetQualityLevel(previousQualityIndex, false);

                if (!changedAnyPipeline)
                {
                    trace.Info("All quality levels already reference the development render pipeline.");
                }
            }

            private static AddressableAssetSettings.PlayerBuildOption? ConfigureAddressablesForDevelopmentBuild(BuildTraceSession trace)
            {
                var settings = AddressableAssetSettingsDefaultObject.Settings;
                if (settings == null)
                {
                    trace.Info("No Addressables settings found. Skipping development Addressables override.");
                    return null;
                }

                var previousOption = settings.BuildAddressablesWithPlayerBuild;
                trace.Info("Current Addressables player-build option: " + previousOption);

                if (previousOption == AddressableAssetSettings.PlayerBuildOption.DoNotBuildWithPlayer)
                {
                    trace.Info("Development Addressables override not required.");
                    return previousOption;
                }

                settings.BuildAddressablesWithPlayerBuild = AddressableAssetSettings.PlayerBuildOption.DoNotBuildWithPlayer;
                trace.Info("Disabled Addressables content build for development player build.");
                return previousOption;
            }

            private void RestoreAddressablesBuildSetting()
            {
                if (!previousAddressablesBuildOption.HasValue)
                {
                    return;
                }

                var settings = AddressableAssetSettingsDefaultObject.Settings;
                if (settings == null)
                {
                    trace.Warn("Unable to restore Addressables build setting because the settings object is unavailable.");
                    return;
                }

                if (settings.BuildAddressablesWithPlayerBuild == previousAddressablesBuildOption.Value)
                {
                    trace.Info("Addressables player-build option already restored: " + previousAddressablesBuildOption.Value);
                    return;
                }

                settings.BuildAddressablesWithPlayerBuild = previousAddressablesBuildOption.Value;
                trace.Info("Restored Addressables player-build option: " + previousAddressablesBuildOption.Value);
            }

            private void RestoreRenderPipelines()
            {
                if (qualitySettingsSnapshot == null || QualitySettings.names == null || QualitySettings.names.Length == 0)
                {
                    return;
                }

                var restoreCount = Mathf.Min(qualitySettingsSnapshot.RenderPipelineGuids.Length, QualitySettings.names.Length);
                var startingQualityIndex = QualitySettings.GetQualityLevel();

                for (var index = 0; index < restoreCount; index += 1)
                {
                    QualitySettings.SetQualityLevel(index, false);

                    var targetPipeline = qualitySettingsSnapshot.LoadRenderPipelineAsset(index);

                    if (QualitySettings.GetRenderPipelineAssetAt(index) == targetPipeline)
                    {
                        continue;
                    }

                    QualitySettings.renderPipeline = targetPipeline;
                    var restoredPipelineName = targetPipeline == null
                        ? "<default>"
                        : targetPipeline.name;
                    trace.Info("Restored render pipeline for quality '" + QualitySettings.names[index] + "' to " + restoredPipelineName + ".");
                }

                QualitySettings.SetQualityLevel(startingQualityIndex, false);
                qualitySettingsSnapshot.RestoreFile(trace);
            }
        }

        private sealed class QualitySettingsSnapshot
        {
            private readonly string fileContents;
            private readonly string filePath;

            public string[] RenderPipelineGuids { get; }

            private QualitySettingsSnapshot(string filePath, string fileContents, string[] renderPipelineGuids)
            {
                this.filePath = filePath;
                this.fileContents = fileContents;
                RenderPipelineGuids = renderPipelineGuids ?? Array.Empty<string>();
            }

            public static QualitySettingsSnapshot Capture(BuildTraceSession trace)
            {
                var projectRoot = Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
                var qualitySettingsPath = Path.Combine(projectRoot, "ProjectSettings", "QualitySettings.asset");

                if (!File.Exists(qualitySettingsPath))
                {
                    trace.Warn("Unable to capture QualitySettings snapshot. File not found: " + qualitySettingsPath);
                    return null;
                }

                var fileContents = File.ReadAllText(qualitySettingsPath);
                var renderPipelineGuids = fileContents
                    .Split(new[] { "\r\n", "\n" }, StringSplitOptions.None)
                    .Where(line => line.Contains("customRenderPipeline:"))
                    .Select(ParseRenderPipelineGuid)
                    .ToArray();

                trace.Info("Captured QualitySettings snapshot with " + renderPipelineGuids.Length + " render pipeline entries.");
                return new QualitySettingsSnapshot(qualitySettingsPath, fileContents, renderPipelineGuids);
            }

            public RenderPipelineAsset LoadRenderPipelineAsset(int qualityIndex)
            {
                if (qualityIndex < 0 || qualityIndex >= RenderPipelineGuids.Length)
                {
                    return null;
                }

                var guid = RenderPipelineGuids[qualityIndex];
                if (string.IsNullOrWhiteSpace(guid))
                {
                    return null;
                }

                var assetPath = AssetDatabase.GUIDToAssetPath(guid);
                if (string.IsNullOrWhiteSpace(assetPath))
                {
                    return null;
                }

                return AssetDatabase.LoadAssetAtPath<RenderPipelineAsset>(assetPath);
            }

            public void RestoreFile(BuildTraceSession trace)
            {
                if (string.IsNullOrWhiteSpace(filePath) || fileContents == null)
                {
                    return;
                }

                var currentContents = File.Exists(filePath)
                    ? File.ReadAllText(filePath)
                    : null;

                if (string.Equals(currentContents, fileContents, StringComparison.Ordinal))
                {
                    return;
                }

                File.WriteAllText(filePath, fileContents);
                trace.Info("Restored QualitySettings.asset file contents.");
            }

            private static string ParseRenderPipelineGuid(string line)
            {
                var fileIdToken = "fileID:";
                var guidToken = "guid:";

                var fileIdIndex = line.IndexOf(fileIdToken, StringComparison.Ordinal);
                if (fileIdIndex >= 0)
                {
                    var fileIdValueStart = fileIdIndex + fileIdToken.Length;
                    var fileIdValueEnd = line.IndexOf(',', fileIdValueStart);
                    var fileIdValue = (fileIdValueEnd >= 0
                            ? line.Substring(fileIdValueStart, fileIdValueEnd - fileIdValueStart)
                            : line.Substring(fileIdValueStart))
                        .Trim();

                    if (string.Equals(fileIdValue, "0", StringComparison.Ordinal))
                    {
                        return null;
                    }
                }

                var guidIndex = line.IndexOf(guidToken, StringComparison.Ordinal);
                if (guidIndex < 0)
                {
                    return null;
                }

                var guidValueStart = guidIndex + guidToken.Length;
                var guidValueEnd = line.IndexOf(',', guidValueStart);
                var guidValue = (guidValueEnd >= 0
                        ? line.Substring(guidValueStart, guidValueEnd - guidValueStart)
                        : line.Substring(guidValueStart))
                    .Trim();

                return string.IsNullOrWhiteSpace(guidValue) ? null : guidValue;
            }
        }

        private static void EnsureAndroidSdkConfigured()
        {
            if (Directory.Exists(AndroidExternalToolsSettings.sdkRootPath))
            {
                return;
            }

            var sdkPath = Environment.GetEnvironmentVariable("ANDROID_SDK_ROOT");
            if (string.IsNullOrWhiteSpace(sdkPath))
            {
                sdkPath = Environment.GetEnvironmentVariable("ANDROID_HOME");
            }

            if (!string.IsNullOrWhiteSpace(sdkPath) && Directory.Exists(sdkPath))
            {
                AndroidExternalToolsSettings.sdkRootPath = sdkPath;
            }

            if (!Directory.Exists(AndroidExternalToolsSettings.sdkRootPath))
            {
                throw new InvalidOperationException(
                    "Unity Android SDK path is not configured. Set Edit > Preferences > External Tools > Android SDK or define ANDROID_SDK_ROOT.");
            }
        }

        private static void SwitchActiveBuildTarget(
            BuildTargetGroup targetGroup,
            BuildTarget target,
            BuildTraceSession trace)
        {
            if (EditorUserBuildSettings.activeBuildTarget == target)
            {
                trace.Info("Active build target is already " + target + ".");
                return;
            }

            if (!EditorUserBuildSettings.SwitchActiveBuildTarget(targetGroup, target))
            {
                throw new InvalidOperationException(
                    "Failed to switch the active build target to " + target + ".");
            }

            trace.Info("Active build target switched to " + target + ".");
        }

        private static void LogBuildSummary(BuildSummary summary, BuildTraceSession trace)
        {
            trace.Info("Build result: " + summary.result);
            trace.Info("Output path: " + summary.outputPath);
            trace.Info("Total warnings: " + summary.totalWarnings);
            trace.Info("Total errors: " + summary.totalErrors);
            trace.Info("Build time: " + summary.totalTime);
            trace.Info("Build size: " + summary.totalSize + " bytes");
        }

        private static void EnsureOutputDirectory(string outputPath, BuildTarget target)
        {
            if (target == BuildTarget.WebGL)
            {
                Directory.CreateDirectory(outputPath);
                return;
            }

            var directory = Path.GetDirectoryName(outputPath);
            if (!string.IsNullOrWhiteSpace(directory))
            {
                Directory.CreateDirectory(directory);
            }
        }

        private static void BuildAndroidApk(string buildLabel, string outputPath)
        {
            var previousExportAsGoogleAndroidProject = EditorUserBuildSettings.exportAsGoogleAndroidProject;
            Debug.Log(
                "[GTEX Build] Android exportAsGoogleAndroidProject (before APK build): " +
                previousExportAsGoogleAndroidProject);

            try
            {
                EditorUserBuildSettings.exportAsGoogleAndroidProject = false;
                Debug.Log("[GTEX Build] Android exportAsGoogleAndroidProject (set for APK build): false");
                Debug.Log("[GTEX Build] BEFORE BUILD PLAYER " + buildLabel + " -> " + outputPath);
                RunBuild(
                    buildLabel,
                    outputPath,
                    BuildTargetGroup.Android,
                    BuildTarget.Android,
                    () =>
                    {
                        EnsureAndroidSdkConfigured();
                        if (Directory.Exists(outputPath))
                        {
                            Directory.Delete(outputPath, true);
                            Debug.Log("[GTEX Build] Removed stale Android export directory at APK path: " + outputPath);
                        }
                    },
                    null,
                    BuildOptions.None,
                    ValidateAndroidApkOutput);
                Debug.Log("[GTEX Build] AFTER BUILD PLAYER " + buildLabel + " -> " + outputPath);
            }
            finally
            {
                EditorUserBuildSettings.exportAsGoogleAndroidProject = previousExportAsGoogleAndroidProject;
                Debug.Log(
                    "[GTEX Build] Android exportAsGoogleAndroidProject (restored after APK build): " +
                    previousExportAsGoogleAndroidProject);
            }
        }

        private static void ExportAndroidLibrary(string buildLabel, string exportPath)
        {
            var previousExportAsGoogleAndroidProject = EditorUserBuildSettings.exportAsGoogleAndroidProject;
            Debug.Log(
                "[GTEX Build] Android exportAsGoogleAndroidProject (before): " +
                previousExportAsGoogleAndroidProject);

            try
            {
                EditorUserBuildSettings.exportAsGoogleAndroidProject = true;
                Debug.Log("[GTEX Build] Android exportAsGoogleAndroidProject (set): true");
                Debug.Log("[GTEX Build] BEFORE BUILD PLAYER " + buildLabel + " -> " + exportPath);
                RunBuild(
                    buildLabel,
                    exportPath,
                    BuildTargetGroup.Android,
                    BuildTarget.Android,
                    () =>
                    {
                        EnsureAndroidSdkConfigured();
                        RecreateDirectory(exportPath);
                    },
                    null,
                    BuildOptions.None,
                    ValidateAndroidLibraryExport);
                Debug.Log("[GTEX Build] AFTER BUILD PLAYER " + buildLabel + " -> " + exportPath);
            }
            finally
            {
                EditorUserBuildSettings.exportAsGoogleAndroidProject = previousExportAsGoogleAndroidProject;
                Debug.Log(
                    "[GTEX Build] Android exportAsGoogleAndroidProject (restored): " +
                    previousExportAsGoogleAndroidProject);
            }
        }

        private static void ValidateAndroidApkOutput(
            string outputPath,
            BuildTarget target,
            BuildTraceSession trace)
        {
            if (target != BuildTarget.Android)
            {
                return;
            }

            if (!File.Exists(outputPath))
            {
                if (Directory.Exists(outputPath))
                {
                    throw new InvalidOperationException(
                        "Android build produced a directory at the APK path instead of an .apk file. " +
                        "This usually means exportAsGoogleAndroidProject was enabled or Unity exported a Gradle project unexpectedly: " +
                        outputPath);
                }

                throw new InvalidOperationException(
                    "Android build completed without producing the expected APK: " + outputPath);
            }

            trace.Info("Verified Android APK output: " + outputPath);
        }

        private static void ValidateAndroidLibraryExport(
            string exportPath,
            BuildTarget target,
            BuildTraceSession trace)
        {
            if (target != BuildTarget.Android)
            {
                return;
            }

            var unityLibraryDirectory = Path.Combine(exportPath, "unityLibrary");
            if (!Directory.Exists(unityLibraryDirectory))
            {
                throw new InvalidOperationException(
                    "Unity Android export completed without producing unityLibrary: " + unityLibraryDirectory);
            }

            PatchUnityExportGradleScripts(exportPath, trace);
            trace.Info("Verified Unity Android export: " + unityLibraryDirectory);
        }

        private static void PatchUnityExportGradleScripts(string exportPath, BuildTraceSession trace)
        {
            PatchUnityExportGradleScript(Path.Combine(exportPath, "unityLibrary", "build.gradle"), trace);
            PatchUnityExportGradleScript(Path.Combine(exportPath, "launcher", "build.gradle"), trace);
        }

        private static void PatchUnityExportGradleScript(string scriptPath, BuildTraceSession trace)
        {
            if (!File.Exists(scriptPath))
            {
                return;
            }

            const string legacySnippet =
                "['.unity3d', '.ress', '.resource', '.obb', '.bundle', '.unityexp'] + unityStreamingAssets.tokenize(', ')";
            const string patchedSnippet =
                "['.unity3d', '.ress', '.resource', '.obb', '.bundle', '.unityexp'] + ((project.findProperty('unityStreamingAssets') ?: '').toString().tokenize(', '))";
            const string unityLibraryHeader =
                "apply plugin: 'com.android.library'\n" +
                "apply from: '../shared/keepUnitySymbols.gradle'\n" +
                "apply from: '../shared/common.gradle'\n";
            const string patchedUnityLibraryHeader =
                "apply plugin: 'com.android.library'\n" +
                "apply from: '../shared/keepUnitySymbols.gradle'\n" +
                "apply from: '../shared/common.gradle'\n\n" +
                "def unityExportProperties = new Properties()\n" +
                "def unityExportPropertiesFile = new File(rootProject.projectDir, 'unityExport/gradle.properties')\n" +
                "if (unityExportPropertiesFile.exists()) {\n" +
                "    unityExportPropertiesFile.withInputStream { stream ->\n" +
                "        unityExportProperties.load(stream)\n" +
                "    }\n" +
                "}\n" +
                "ext.unityExportProperties = unityExportProperties\n\n" +
                "String unityGradleProperty(String name) {\n" +
                "    if (project.hasProperty(name)) {\n" +
                "        return project.property(name).toString()\n" +
                "    }\n\n" +
                "    def value = project.ext.unityExportProperties.getProperty(name)\n" +
                "    if (value != null) {\n" +
                "        return value\n" +
                "    }\n\n" +
                "    throw new GradleException(\"Missing Unity export Gradle property: ${name}\")\n" +
                "}\n";

            var originalContents = File.ReadAllText(scriptPath);
            var patchedContents = originalContents.Replace(legacySnippet, patchedSnippet);

            if (scriptPath.EndsWith(Path.Combine("unityLibrary", "build.gradle"), StringComparison.OrdinalIgnoreCase))
            {
                patchedContents = patchedContents
                    .Replace(unityLibraryHeader, patchedUnityLibraryHeader)
                    .Replace("getProperty(\"unity.androidSdkPath\")", "unityGradleProperty(\"unity.androidSdkPath\")")
                    .Replace("getProperty(\"unity.androidNdkPath\")", "unityGradleProperty(\"unity.androidNdkPath\")");
            }

            if (patchedContents == originalContents)
            {
                trace.Info("Unity export Gradle script already normalized: " + scriptPath);
                return;
            }

            File.WriteAllText(scriptPath, patchedContents);
            trace.Info("Patched Unity export Gradle script for AGP compatibility: " + scriptPath);
        }

        private static string ResolveDefaultBuildPath(BuildTarget target, GtexMode? buildModeOverride = null)
        {
            switch (target)
            {
                case BuildTarget.Android:
                    return Path.Combine(ResolvePlatformBuildDirectory("Android"), AndroidFileName);
                case BuildTarget.WebGL:
                    return ResolvePlatformBuildDirectory("WebGL");
                case BuildTarget.StandaloneWindows64:
                default:
                    return Path.Combine(
                        ResolvePlatformBuildDirectory(
                            buildModeOverride.HasValue && buildModeOverride.Value == GtexMode.Production
                                ? "WindowsProduction"
                                : "Windows"),
                        WindowsFileName);
            }
        }

        private static string ResolveAndroidLibraryExportPath()
        {
            return Path.GetFullPath(Path.Combine(ProjectRoot(), "..", "frontend", "android", "unityExport"));
        }

        private static void LogBatchCheckpoint(string marker, string outputPath)
        {
            Debug.Log(
                "[GTEX Build] " + marker + "\n" +
                "[GTEX Build] projectPath=" + Directory.GetCurrentDirectory() + "\n" +
                "[GTEX Build] outputPath=" + outputPath + "\n" +
                "[GTEX Build] unityVersion=" + Application.unityVersion + "\n" +
                "[GTEX Build] activeBuildTarget=" + EditorUserBuildSettings.activeBuildTarget + "\n" +
#if UNITY_ANDROID
                "[GTEX Build] UNITY_ANDROID=true\n" +
#else
                "[GTEX Build] UNITY_ANDROID=false\n" +
#endif
                "[GTEX Build] isBatchMode=" + Application.isBatchMode);
        }

        private static string ResolveAndroidApkOutputPath()
        {
            return Path.GetFullPath(
                Path.Combine(
                    Directory.GetCurrentDirectory(),
                    "Builds",
                    "Android",
                    "GTEXMatch.apk"));
        }

        private static string ResolveAndroidExportOutputPath()
        {
            return Path.GetFullPath(
                Path.Combine(
                    Directory.GetCurrentDirectory(),
                    "..",
                    "frontend",
                    "android",
                    "unityExport"));
        }

        private static string ResolvePlatformBuildDirectory(string platformName)
        {
            var buildDirectory = Path.Combine(ProjectRoot(), "Builds", platformName);
            Directory.CreateDirectory(buildDirectory);
            return buildDirectory;
        }

        private static string ResolveTraceLogDirectory()
        {
            var logDirectory = Path.Combine(ProjectRoot(), "tmp", BuildLogDirectoryName);
            Directory.CreateDirectory(logDirectory);
            return logDirectory;
        }

        private static string ProjectRoot()
        {
            return Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
        }

        private static void RecreateDirectory(string path)
        {
            if (Directory.Exists(path))
            {
                Directory.Delete(path, true);
            }

            Directory.CreateDirectory(path);
        }

        private sealed class BuildTraceSession : IDisposable
        {
            private readonly Stopwatch stopwatch = Stopwatch.StartNew();

            public string TraceFilePath { get; }

            private BuildTraceSession(string traceFilePath)
            {
                TraceFilePath = traceFilePath;
            }

            public static BuildTraceSession Start(string buildLabel, BuildTarget target, string outputPath)
            {
                var timestamp = DateTime.Now.ToString("yyyyMMdd-HHmmss");
                var fileName = "gtex-build-" + SanitizeFileName(target.ToString()) + "-" + timestamp + ".log";
                var traceFilePath = Path.Combine(ResolveTraceLogDirectory(), fileName);
                var session = new BuildTraceSession(traceFilePath);

                session.Info("Starting " + buildLabel);
                session.Info("Trace file: " + traceFilePath);
                session.Info("Requested output path: " + outputPath);

                return session;
            }

            public void Stage(string message)
            {
                Write("STAGE", message, Debug.Log);
            }

            public void Info(string message)
            {
                Write("INFO", message, Debug.Log);
            }

            public void Warn(string message)
            {
                Write("WARN", message, Debug.LogWarning);
            }

            public void Error(string message)
            {
                Write("ERROR", message, Debug.LogError);
            }

            public void Dispose()
            {
                stopwatch.Stop();
                Write("INFO", "Trace session closed.", Debug.Log);
            }

            private void Write(string level, string message, Action<object> unityLogger)
            {
                var elapsed = stopwatch.Elapsed.ToString(@"hh\:mm\:ss\.fff");
                var line =
                    DateTime.Now.ToString("O") +
                    " [" + elapsed + "]" +
                    " [" + level + "] " +
                    message;

                try
                {
                    File.AppendAllText(TraceFilePath, line + Environment.NewLine);
                }
                catch (Exception exception)
                {
                    Debug.LogWarning(BuildLogPrefix + " Failed to write companion trace file: " + exception.Message);
                }

                unityLogger(BuildLogPrefix + " " + message);
            }

            private static string SanitizeFileName(string value)
            {
                var invalidCharacters = Path.GetInvalidFileNameChars();
                var sanitized = new string(
                    value.Select(character => invalidCharacters.Contains(character) ? '-' : character).ToArray());
                return sanitized;
            }
        }
    }
}
#endif
