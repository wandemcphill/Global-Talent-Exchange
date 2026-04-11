#if UNITY_EDITOR
using System;
using System.IO;
using System.Text.RegularExpressions;
using FStudio.GTEX.Core;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace FStudio.GTEX.Editor
{
    public static class GtexRuntimeModeTools
    {
        private const string RelativeConfigPath = "Assets/Resources/GTEX/match-config.json";
        private static readonly Regex RuntimeModeRegex =
            new Regex("\"runtimeMode\"\\s*:\\s*\"(?<value>[^\"]*)\"", RegexOptions.Compiled | RegexOptions.IgnoreCase);

        [MenuItem("Tools/GTEX/Runtime/Mode Window")]
        public static void OpenWindow()
        {
            GtexRuntimeModeWindow.ShowWindow();
        }

        [MenuItem("Tools/GTEX/Runtime/Switch To Live Playback")]
        public static void SwitchToLivePlaybackMenu()
        {
            SetRuntimeMode(GtexRuntimeMode.LivePlayback);
        }

        [MenuItem("Tools/GTEX/Runtime/Switch To Local Simulation")]
        public static void SwitchToLocalSimulationMenu()
        {
            SetRuntimeMode(GtexRuntimeMode.LocalSimulation);
        }

        [MenuItem("Tools/GTEX/Runtime/Run Local Simulation Test")]
        public static void RunLocalSimulationTestMenu()
        {
            GtexRuntimeBootstrapVerifier.VerifyFromEditorMenu();
        }

        [MenuItem("Tools/GTEX/Runtime/Run Live Playback Boot Check")]
        public static void RunLivePlaybackBootCheckMenu()
        {
            GtexLivePlaybackVerifier.VerifyFromEditorMenu();
        }

        [MenuItem("Tools/GTEX/Runtime/Run Live Playback Smoke Test")]
        public static void RunLivePlaybackSmokeTestMenu()
        {
            GtexLivePlaybackSmokeVerifier.VerifyFromEditorMenu();
        }

        [MenuItem("Tools/GTEX/Runtime/Run Adapter Test")]
        public static void RunAdapterTestMenu()
        {
            GtexSimAdapterVerifier.VerifyFromEditorMenu();
        }

        [MenuItem("Tools/GTEX/Runtime/Open Dev Scene")]
        public static void OpenDevSceneMenu()
        {
            OpenScene(GtexSceneLoader.DevelopmentScenePath);
        }

        [MenuItem("Tools/GTEX/Runtime/Open Dev Scene With Local Simulation")]
        public static void OpenDevSceneWithLocalSimulationMenu()
        {
            SetRuntimeMode(GtexRuntimeMode.LocalSimulation);
            OpenScene(GtexSceneLoader.DevelopmentScenePath);
        }

        public static string AbsoluteConfigPath =>
            Path.GetFullPath(Path.Combine(Application.dataPath, "..", RelativeConfigPath));

        public static GtexRuntimeMode GetRuntimeMode()
        {
            var json = ReadConfigJson();
            return ResolveRuntimeMode(json);
        }

        public static void SetRuntimeMode(GtexRuntimeMode runtimeMode)
        {
            var path = AbsoluteConfigPath;
            var json = ReadConfigJson();
            var nextToken = ToToken(runtimeMode);
            var updatedJson = RuntimeModeRegex.IsMatch(json)
                ? RuntimeModeRegex.Replace(json, "\"runtimeMode\": \"" + nextToken + "\"", 1)
                : InsertRuntimeMode(json, nextToken);

            if (string.Equals(json, updatedJson, StringComparison.Ordinal))
            {
                Debug.Log("[GTEX Runtime Mode] Runtime mode already set to " + runtimeMode + ".");
                return;
            }

            File.WriteAllText(path, NormalizeJson(updatedJson));
            AssetDatabase.ImportAsset(RelativeConfigPath, ImportAssetOptions.ForceSynchronousImport);
            AssetDatabase.Refresh();

            Debug.Log("[GTEX Runtime Mode] Runtime mode switched to " + runtimeMode + ".");
        }

        public static void RestoreRawConfig(string originalJson)
        {
            File.WriteAllText(AbsoluteConfigPath, NormalizeJson(originalJson));
            AssetDatabase.ImportAsset(RelativeConfigPath, ImportAssetOptions.ForceSynchronousImport);
            AssetDatabase.Refresh();
        }

        public static string ReadConfigJson()
        {
            var path = AbsoluteConfigPath;
            if (!File.Exists(path))
            {
                throw new FileNotFoundException("GTEX match config was not found.", path);
            }

            return File.ReadAllText(path);
        }

        public static void OpenScene(string scenePath)
        {
            if (string.IsNullOrWhiteSpace(scenePath))
            {
                throw new ArgumentException("Scene path is required.", nameof(scenePath));
            }

            if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())
            {
                return;
            }

            EditorSceneManager.OpenScene(scenePath);
            Debug.Log("[GTEX Runtime Mode] Opened scene " + scenePath + ".");
        }

        private static GtexRuntimeMode ResolveRuntimeMode(string json)
        {
            var match = RuntimeModeRegex.Match(json ?? string.Empty);
            var token = match.Success ? match.Groups["value"].Value : "live";

            switch ((token ?? string.Empty).Trim().ToLowerInvariant())
            {
                case "simulation":
                case "sim":
                case "local-simulation":
                case "localsimulation":
                    return GtexRuntimeMode.LocalSimulation;
                default:
                    return GtexRuntimeMode.LivePlayback;
            }
        }

        private static string ToToken(GtexRuntimeMode runtimeMode)
        {
            return runtimeMode == GtexRuntimeMode.LocalSimulation ? "simulation" : "live";
        }

        private static string InsertRuntimeMode(string json, string token)
        {
            var normalizedJson = NormalizeJson(json);
            var insertionLine = "  \"runtimeMode\": \"" + token + "\",";
            var anchor = "\"autoStartOnBoot\"";
            var anchorIndex = normalizedJson.IndexOf(anchor, StringComparison.Ordinal);
            if (anchorIndex < 0)
            {
                return normalizedJson;
            }

            var lineEndIndex = normalizedJson.IndexOf('\n', anchorIndex);
            if (lineEndIndex < 0)
            {
                lineEndIndex = normalizedJson.Length;
            }

            return normalizedJson.Insert(lineEndIndex + 1, insertionLine + "\n");
        }

        private static string NormalizeJson(string json)
        {
            return (json ?? string.Empty).Replace("\r\n", "\n").Replace('\r', '\n').TrimEnd() + "\n";
        }
    }

    public sealed class GtexRuntimeModeWindow : EditorWindow
    {
        [MenuItem("Tools/GTEX/Runtime/Show Mode Window")]
        public static void ShowWindow()
        {
            var window = GetWindow<GtexRuntimeModeWindow>("GTEX Runtime");
            window.minSize = new Vector2(360f, 160f);
        }

        private void OnGUI()
        {
            var currentMode = GtexRuntimeModeTools.GetRuntimeMode();

            EditorGUILayout.LabelField("GTEX Runtime Mode", EditorStyles.boldLabel);
            EditorGUILayout.Space(6f);
            EditorGUILayout.LabelField("Config", GtexRuntimeModeTools.AbsoluteConfigPath, EditorStyles.wordWrappedLabel);
            EditorGUILayout.Space(6f);
            EditorGUILayout.HelpBox("Current mode: " + currentMode, MessageType.Info);
            EditorGUILayout.Space(8f);

            EditorGUILayout.LabelField("Last Test Status", EditorStyles.boldLabel);
            EditorGUILayout.HelpBox(
                GtexRuntimeToolStatus.LastSummary,
                ResolveStatusMessageType(GtexRuntimeToolStatus.LastState));
            EditorGUILayout.LabelField("Last Action", GtexRuntimeToolStatus.LastAction);
            EditorGUILayout.LabelField("State", GtexRuntimeToolStatus.LastState.ToString());
            EditorGUILayout.LabelField(
                "Scoreline",
                string.IsNullOrWhiteSpace(GtexRuntimeToolStatus.LastScoreline) ? "-" : GtexRuntimeToolStatus.LastScoreline);
            EditorGUILayout.LabelField(
                "Elapsed",
                GtexRuntimeToolStatus.LastDurationMs > 0d
                    ? GtexRuntimeToolStatus.LastDurationMs.ToString("0") + " ms"
                    : "-");
            EditorGUILayout.LabelField("Updated", GtexRuntimeToolStatus.LastCompletedDisplay);

            EditorGUILayout.Space(8f);

            using (new EditorGUILayout.HorizontalScope())
            {
                if (GUILayout.Button("Live Playback"))
                {
                    GtexRuntimeModeTools.SetRuntimeMode(GtexRuntimeMode.LivePlayback);
                }

                if (GUILayout.Button("Local Simulation"))
                {
                    GtexRuntimeModeTools.SetRuntimeMode(GtexRuntimeMode.LocalSimulation);
                }
            }

            EditorGUILayout.Space(8f);
            EditorGUILayout.LabelField("Tests", EditorStyles.boldLabel);
            EditorGUILayout.HelpBox(
                "These actions run editor-side verification and do not leave the saved runtime mode changed.",
                MessageType.None);

            using (new EditorGUILayout.HorizontalScope())
            {
                if (GUILayout.Button("Run Live Boot Check"))
                {
                    RunAction("Live playback boot check", GtexLivePlaybackVerifier.VerifyFromEditorMenu);
                }

                if (GUILayout.Button("Run Live Smoke Test"))
                {
                    RunAction("Live playback smoke test", GtexLivePlaybackSmokeVerifier.VerifyFromEditorMenu);
                }

                if (GUILayout.Button("Run Local Sim Test"))
                {
                    RunAction("Local simulation test", GtexRuntimeBootstrapVerifier.VerifyFromEditorMenu);
                }

                if (GUILayout.Button("Run Adapter Test"))
                {
                    RunAction("Adapter test", GtexSimAdapterVerifier.VerifyFromEditorMenu);
                }
            }

            if (GUILayout.Button("Verify Mode Switcher"))
            {
                RunAction("Mode switcher verification", GtexRuntimeModeToolsVerifier.VerifyFromEditorMenu);
            }

            EditorGUILayout.Space(8f);
            EditorGUILayout.LabelField("Workflow", EditorStyles.boldLabel);

            using (new EditorGUILayout.HorizontalScope())
            {
                if (GUILayout.Button("Open Dev Scene"))
                {
                    RunAction("Open dev scene", () => GtexRuntimeModeTools.OpenScene(GtexSceneLoader.DevelopmentScenePath));
                }

                if (GUILayout.Button("Dev Scene + Sim"))
                {
                    RunAction(
                        "Open dev scene with local simulation",
                        GtexRuntimeModeTools.OpenDevSceneWithLocalSimulationMenu);
                }
            }

            EditorGUILayout.Space(8f);
            if (GUILayout.Button("Reveal Config File"))
            {
                EditorUtility.RevealInFinder(GtexRuntimeModeTools.AbsoluteConfigPath);
            }
        }

        private static void RunAction(string actionName, Action action)
        {
            try
            {
                action?.Invoke();
                EditorUtility.DisplayDialog("GTEX Runtime", actionName + " completed. Check the Console for logs.", "OK");
            }
            catch (Exception exception)
            {
                Debug.LogException(exception);
                EditorUtility.DisplayDialog("GTEX Runtime", actionName + " failed. Check the Console for details.", "OK");
            }
        }

        private static MessageType ResolveStatusMessageType(GtexRuntimeToolRunState state)
        {
            switch (state)
            {
                case GtexRuntimeToolRunState.Running:
                    return MessageType.Warning;
                case GtexRuntimeToolRunState.Failed:
                    return MessageType.Error;
                case GtexRuntimeToolRunState.Passed:
                    return MessageType.Info;
                case GtexRuntimeToolRunState.NotRun:
                default:
                    return MessageType.None;
            }
        }
    }
}
#endif
