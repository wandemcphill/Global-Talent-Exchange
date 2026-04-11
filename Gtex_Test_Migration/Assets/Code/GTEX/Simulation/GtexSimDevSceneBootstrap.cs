using FStudio.GTEX.Core;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace FStudio.GTEX.Simulation
{
    public static class GtexSimDevSceneBootstrap
    {
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void TryBootstrap()
        {
            if (Application.isBatchMode)
            {
                return;
            }

            var config = GtexMatchConfigLoader.Load();
            if (config == null || config.ResolveRuntimeMode() != GtexRuntimeMode.LocalSimulation)
            {
                return;
            }

            var activeScene = SceneManager.GetActiveScene();
            if (!activeScene.IsValid())
            {
                return;
            }

            if (!string.Equals(activeScene.name, GtexSceneLoader.DevelopmentSceneName) &&
                !string.Equals(activeScene.name, GtexSceneLoader.BuildSceneName))
            {
                return;
            }

            if (Object.FindFirstObjectByType<GtexSimRuntimeHost>() != null ||
                Object.FindFirstObjectByType<GtexMatchRuntime>() != null)
            {
                return;
            }

            if (GtexSimRuntimeHost.TryAutoStart(config))
            {
                Debug.Log("[GTEX Sim Bootstrap] Local simulation auto-started for scene '" + activeScene.name + "'.");
            }
        }
    }
}
