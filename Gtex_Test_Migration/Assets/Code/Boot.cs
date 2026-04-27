using System;
using FStudio.Events;
using FStudio.GTEX.Core;
using FStudio.GTEX;
using FStudio.Loaders;
using FStudio.UI;
using FStudio.UI.Events;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace FStudio {
    public class Boot : MonoBehaviour {
        private async void Start() {
            var config = GtexMatchConfigLoader.Load(true);
            var mode = ResolveBootMode(config);
            var unattended = GtexBootModeResolver.ResolveUnattended(mode);
            GtexRuntimeFlags.SetMode(mode, unattended);
            GtexBootModeResolver.PrepareConfigForMode(config, mode);

            if (config != null) {
                Debug.Log(
                    "[GTEX] Boot startup scene '" +
                    SceneManager.GetActiveScene().name +
                    "' selected boot mode -> " +
                    mode +
                    " (runtime=" +
                    config.ResolveRuntimeMode() +
                    ", raw='" +
                    config.runtimeMode +
                    "', matchId='" +
                    config.matchId +
                    "', baseUrl='" +
                    config.ResolveBaseUrl() +
                    "', localSim3DPlaybackRequested=" +
                    config.use3DPlaybackForLocalSimulation +
                    ").");
            }

            if (mode == GtexBootMode.LocalSimulation && config != null) {
                Debug.Log("[GTEX Boot] Starting directly in local simulation mode. Live auth/matchId not required.");
            } else if (mode == GtexBootMode.OriginalVisualRuntime) {
                Debug.Log("[GTEX Boot] Starting in original visual runtime mode.");
            } else if (mode == GtexBootMode.Live) {
                Debug.Log("[GTEX Boot] Starting in live mode.");
            }

            var activeScene = SceneManager.GetActiveScene();
            if (mode == GtexBootMode.OriginalVisualRuntime &&
                !string.Equals(activeScene.name, GtexSceneLoader.OriginalVisualRuntimeSceneName, StringComparison.Ordinal))
            {
                Debug.Log(
                    "[GTEX Boot] Redirecting boot scene '" +
                    activeScene.name +
                    "' to '" +
                    GtexSceneLoader.OriginalVisualRuntimeSceneName +
                    "'.");
                SceneManager.LoadScene(GtexSceneLoader.OriginalVisualRuntimeSceneName);
                return;
            }

            if (mode == GtexBootMode.OriginalVisualRuntime)
            {
                if (!GtexRuntimeState.TryBeginBoot(config != null ? config.ResolveRuntimeMode() : GtexRuntimeMode.OriginalVisualRuntime, "Boot"))
                {
                    return;
                }

                Debug.Log("[GTEX Boot] Starting OriginalVisualRuntime as sole boot owner.");
                if (config != null && GtexRuntimeBootstrap.TryAutoStart(config))
                {
                    GtexRuntimeState.MarkStarted(config.ResolveRuntimeMode(), "Boot");
                    return;
                }

                GtexRuntimeState.ResetForSceneUnload();
                Debug.LogError("[GTEX Boot] Failed to start OriginalVisualRuntime.");
                return;
            }

            if (config != null && GtexRuntimeBootstrap.TryAutoStart(config)) {
                return;
            }

            if (mode == GtexBootMode.Live && TryFallbackToLocalSimulation(config)) {
                return;
            }

            await UILoader.Current.GeneralUILoader.Load();
            await SceneLoader.LoadDefaultScene();
            EventManager.Trigger(new MainMenuEvent());
        }

        private static GtexBootMode ResolveBootMode(GtexMatchConfig config)
        {
            return GtexBootModeResolver.ResolveBootMode(config);
        }

        private static bool TryFallbackToLocalSimulation(GtexMatchConfig config)
        {
            if (config == null ||
                config.ResolveRuntimeMode() != GtexRuntimeMode.LivePlayback ||
                config.CanAutoStartLivePlayback ||
                !config.use3DPlaybackForLocalSimulation)
            {
                return false;
            }

            Debug.Log(
                "[GTEX] LivePlayback auto-start is unavailable in standalone boot. " +
                "Falling back to LocalSimulation 3D playback for offline validation.");

            GtexRuntimeFlags.SetMode(GtexBootMode.LocalSimulation, GtexBootModeResolver.ResolveUnattended(GtexBootMode.LocalSimulation));
            GtexBootModeResolver.PrepareConfigForMode(config, GtexBootMode.LocalSimulation);
            return GtexRuntimeBootstrap.TryAutoStart(config);
        }
    }
}
