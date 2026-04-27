using System;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace FStudio.GTEX.Core
{
    public static class GtexOriginalVisualRuntimePolicy
    {
        public const string SceneName = GtexSceneLoader.OriginalVisualRuntimeSceneName;

        public static bool AllowGtexDevBootstrap => !IsOriginalVisualRuntime();

        public static bool AllowMatchStarter => !IsOriginalVisualRuntime();

        public static bool AllowLegacyFallback => !IsOriginalVisualRuntime();

        public static bool AllowExternalPlayback => !IsOriginalVisualRuntime();

        public static bool AllowDefaultSceneNavigation => !IsOriginalVisualRuntime();

        public static bool AllowAutonomousResetToMenu => !IsOriginalVisualRuntime();

        public static bool AllowPauseMenuCameraControl => !IsOriginalVisualRuntime();

        public static bool AllowGtexTransformPlayback => !IsOriginalVisualRuntime();

        public static bool IsOriginalVisualRuntimeScene()
        {
            return string.Equals(SceneManager.GetActiveScene().name, SceneName, StringComparison.Ordinal);
        }

        public static bool IsOriginalVisualRuntime()
        {
            if (IsOriginalVisualRuntimeScene())
            {
                return true;
            }

            try
            {
                var config = GtexMatchConfigLoader.Load(false);
                return config != null &&
                       config.ResolveRuntimeMode() == GtexRuntimeMode.OriginalVisualRuntime;
            }
            catch
            {
                return false;
            }
        }

        public static bool ShouldBlockSceneLoadForOriginalVisualRuntime(string debugName)
        {
            if (!IsOriginalVisualRuntime())
            {
                return false;
            }

            var normalized = (debugName ?? string.Empty).Trim();
            if (normalized.Length == 0)
            {
                return false;
            }

            return normalized.IndexOf("DefaultScene", StringComparison.OrdinalIgnoreCase) >= 0 ||
                   normalized.IndexOf("MainMenu", StringComparison.OrdinalIgnoreCase) >= 0 ||
                   normalized.IndexOf("Home", StringComparison.OrdinalIgnoreCase) >= 0 ||
                   normalized.IndexOf("Menu", StringComparison.OrdinalIgnoreCase) >= 0;
        }

        public static void LogBlocked(string system)
        {
            Debug.Log("[GTEX OriginalVisualRuntime] Blocked " + system + "; original visual runtime owns this scene.");
        }
    }
}
