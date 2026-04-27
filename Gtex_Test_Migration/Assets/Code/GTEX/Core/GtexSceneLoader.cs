using System.IO;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace FStudio.GTEX.Core
{
    public static class GtexSceneLoader
    {
        public const string BuildScenePath = "Assets/Scenes/Gtex_BuildScene.unity";
        public const string DevelopmentScenePath = "Assets/Scenes/Gtex_DevScene.unity";
        public const string ProductionScenePath = "Assets/Scenes/Gtex_MainScene.unity";
        public const string OriginalVisualRuntimeScenePath = "Assets/Scenes/GTEX_OriginalVisualRuntime.unity";

        public const string BuildSceneName = "Gtex_BuildScene";
        public const string DevelopmentSceneName = "Gtex_DevScene";
        public const string ProductionSceneName = "Gtex_MainScene";
        public const string OriginalVisualRuntimeSceneName = "GTEX_OriginalVisualRuntime";

        public static string ResolveStartupScenePath(GtexMode mode)
        {
            return mode == GtexMode.Development
                ? DevelopmentScenePath
                : ProductionScenePath;
        }

        public static string ResolveStartupSceneName(GtexMode mode)
        {
            return mode == GtexMode.Development
                ? DevelopmentSceneName
                : ProductionSceneName;
        }

        public static string[] ResolveBuildScenePaths(GtexMode mode)
        {
            return mode == GtexMode.Development
                ? new[] { BuildScenePath }
                : new[] { ProductionScenePath, OriginalVisualRuntimeScenePath };
        }

        public static bool SceneExists(string scenePath)
        {
            if (string.IsNullOrWhiteSpace(scenePath))
            {
                return false;
            }

            var projectRoot = Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
            var normalizedScenePath = scenePath.Replace('/', Path.DirectorySeparatorChar);
            return File.Exists(Path.Combine(projectRoot, normalizedScenePath));
        }

        public static void LoadStartupScene()
        {
            var startupScene = ResolveStartupSceneName(GtexConfig.Mode);
            var activeScene = SceneManager.GetActiveScene();
            if (activeScene.name == startupScene)
            {
                return;
            }

            SceneManager.LoadScene(startupScene);
        }
    }
}
