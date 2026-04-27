using System;
using FStudio.GTEX.Core;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace FStudio.GTEX
{
    public enum GtexBootMode
    {
        Auto,
        Live,
        LocalSimulation,
        OriginalVisualRuntime
    }

    public static class GtexRuntimeFlags
    {
        public static bool IsLocalSimulation { get; private set; }

        public static bool IsLiveMode { get; private set; }

        public static bool IsOriginalVisualRuntime { get; private set; }

        public static bool UsesGtexScoreAuthority => IsLocalSimulation || IsOriginalVisualRuntime;

        public static bool IsUnattendedPlayback { get; private set; }

        public static void SetMode(GtexBootMode mode, bool unattended)
        {
            IsLocalSimulation = mode == GtexBootMode.LocalSimulation;
            IsLiveMode = mode == GtexBootMode.Live;
            IsOriginalVisualRuntime = mode == GtexBootMode.OriginalVisualRuntime;
            IsUnattendedPlayback = unattended;
        }
    }

    public static class GtexBootModeResolver
    {
        public static GtexBootMode ResolveBootMode(GtexMatchConfig config = null)
        {
            var activeScene = SceneManager.GetActiveScene();
            if (activeScene.IsValid() &&
                string.Equals(activeScene.name, FStudio.GTEX.Core.GtexSceneLoader.OriginalVisualRuntimeSceneName, StringComparison.Ordinal))
            {
                return GtexBootMode.OriginalVisualRuntime;
            }

            var requestedScene = GetArgValue("scene", "gtex-scene");
            if (!string.IsNullOrWhiteSpace(requestedScene) &&
                IsOriginalVisualSceneToken(requestedScene))
            {
                return GtexBootMode.OriginalVisualRuntime;
            }

            var requestedRuntimeMode = GetArgValue("gtex-runtime-mode", "runtime-mode", "runtimeMode");
            if (IsOriginalVisualRuntimeToken(requestedRuntimeMode))
            {
                return GtexBootMode.OriginalVisualRuntime;
            }

            if (config != null && config.ResolveRuntimeMode() == GtexRuntimeMode.OriginalVisualRuntime)
            {
                return GtexBootMode.OriginalVisualRuntime;
            }

            var hasLiveConfig = HasLiveConfig(config);
            var forceLocal =
                HasArg("local") ||
                HasArg("offline") ||
                Application.isEditor;

            if (forceLocal || !hasLiveConfig)
            {
                return GtexBootMode.LocalSimulation;
            }

            return GtexBootMode.Live;
        }

        public static bool ResolveUnattended(GtexBootMode mode)
        {
            return HasArg("watch") ||
                   HasArg("capture") ||
                   HasArg("unattended") ||
                   mode == GtexBootMode.OriginalVisualRuntime ||
                   mode == GtexBootMode.LocalSimulation;
        }

        public static void PrepareConfigForMode(GtexMatchConfig config, GtexBootMode mode)
        {
            if (config == null)
            {
                return;
            }

            if (mode == GtexBootMode.LocalSimulation)
            {
                config.runtimeMode = "simulation";
                config.allowLocalSimulationInProductionScene = true;
                return;
            }

            if (mode == GtexBootMode.OriginalVisualRuntime)
            {
                config.runtimeMode = "original-visual";
                config.preserveOriginalScenePresentation = true;
                config.useOriginalMatchCamera = true;
                config.enableStadiumUpgrade = false;
                config.showBroadcastScaffolding = false;
                config.showCrowd = false;
            }
        }

        public static bool HasLiveConfig(GtexMatchConfig config = null)
        {
            var matchId = FirstNonEmpty(
                GetArgValue("matchId", "match-id", "gtex-match-id"),
                config != null ? config.matchId : null);
            var authToken = FirstNonEmpty(
                GetArgValue("auth", "live-access-token", "gtex-live-access-token"),
                config != null ? config.liveAccessToken : null,
                config != null ? config.liveRefreshToken : null);

            return !string.IsNullOrWhiteSpace(matchId) &&
                   !string.IsNullOrWhiteSpace(authToken);
        }

        public static bool HasArg(string argName)
        {
            if (string.IsNullOrWhiteSpace(argName))
            {
                return false;
            }

            var normalizedArg = NormalizeArgName(argName);
            var args = GetCommandLineArgs();
            for (var index = 0; index < args.Length; index += 1)
            {
                var normalizedToken = NormalizeArgName(args[index]);
                if (string.IsNullOrWhiteSpace(normalizedToken))
                {
                    continue;
                }

                if (string.Equals(normalizedToken, normalizedArg, StringComparison.OrdinalIgnoreCase))
                {
                    return true;
                }

                var equalsIndex = normalizedToken.IndexOf('=');
                if (equalsIndex <= 0)
                {
                    continue;
                }

                if (string.Equals(
                        normalizedToken.Substring(0, equalsIndex),
                        normalizedArg,
                        StringComparison.OrdinalIgnoreCase))
                {
                    return true;
                }
            }

            return false;
        }

        public static string GetArgValue(params string[] argNames)
        {
            if (argNames == null || argNames.Length == 0)
            {
                return null;
            }

            var args = GetCommandLineArgs();
            for (var index = 0; index < args.Length; index += 1)
            {
                var rawToken = args[index];
                var normalizedToken = NormalizeArgName(rawToken);
                if (string.IsNullOrWhiteSpace(normalizedToken))
                {
                    continue;
                }

                for (var nameIndex = 0; nameIndex < argNames.Length; nameIndex += 1)
                {
                    var normalizedName = NormalizeArgName(argNames[nameIndex]);
                    if (string.IsNullOrWhiteSpace(normalizedName))
                    {
                        continue;
                    }

                    if (string.Equals(normalizedToken, normalizedName, StringComparison.OrdinalIgnoreCase))
                    {
                        if (index + 1 < args.Length)
                        {
                            return args[index + 1];
                        }

                        return string.Empty;
                    }

                    var equalsToken = normalizedName + "=";
                    if (normalizedToken.StartsWith(equalsToken, StringComparison.OrdinalIgnoreCase))
                    {
                        return normalizedToken.Substring(equalsToken.Length);
                    }
                }
            }

            return null;
        }

        private static string[] GetCommandLineArgs()
        {
            try
            {
                return Environment.GetCommandLineArgs() ?? Array.Empty<string>();
            }
            catch
            {
                return Array.Empty<string>();
            }
        }

        private static string NormalizeArgName(string value)
        {
            return string.IsNullOrWhiteSpace(value)
                ? string.Empty
                : value.Trim().TrimStart('-', '/');
        }

        private static string FirstNonEmpty(params string[] values)
        {
            if (values == null)
            {
                return null;
            }

            for (var index = 0; index < values.Length; index += 1)
            {
                if (!string.IsNullOrWhiteSpace(values[index]))
                {
                    return values[index].Trim();
                }
            }

            return null;
        }

        private static bool IsOriginalVisualSceneToken(string value)
        {
            if (string.IsNullOrWhiteSpace(value))
            {
                return false;
            }

            var trimmed = value.Trim();
            return string.Equals(trimmed, FStudio.GTEX.Core.GtexSceneLoader.OriginalVisualRuntimeSceneName, StringComparison.OrdinalIgnoreCase) ||
                   string.Equals(trimmed, FStudio.GTEX.Core.GtexSceneLoader.OriginalVisualRuntimeScenePath, StringComparison.OrdinalIgnoreCase) ||
                   trimmed.EndsWith("/" + FStudio.GTEX.Core.GtexSceneLoader.OriginalVisualRuntimeSceneName + ".unity", StringComparison.OrdinalIgnoreCase) ||
                   trimmed.EndsWith("\\" + FStudio.GTEX.Core.GtexSceneLoader.OriginalVisualRuntimeSceneName + ".unity", StringComparison.OrdinalIgnoreCase);
        }

        private static bool IsOriginalVisualRuntimeToken(string value)
        {
            if (string.IsNullOrWhiteSpace(value))
            {
                return false;
            }

            switch (value.Trim().ToLowerInvariant())
            {
                case "originalvisualruntime":
                case "original-visual-runtime":
                case "originalvisual":
                case "original-visual":
                    return true;
                default:
                    return false;
            }
        }
    }
}
