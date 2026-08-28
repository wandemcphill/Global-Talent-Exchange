using FStudio.GTEX.Core;
using FStudio.GTEX.Simulation;
using FStudio.GTEX.VisualBridge;
using UnityEngine;

namespace FStudio.GTEX.Presentation
{
    [DefaultExecutionOrder(10010)]
    public sealed class GtexLivePlaybackIsolationGuard : MonoBehaviour
    {
        private static GtexLivePlaybackIsolationGuard instance;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void Install()
        {
            if (instance != null) return;
            var host = new GameObject("GTEX Live Playback Isolation");
            DontDestroyOnLoad(host);
            instance = host.AddComponent<GtexLivePlaybackIsolationGuard>();
        }

        private void LateUpdate()
        {
            if (!GtexRuntimeState.IsStarted ||
                GtexRuntimeState.ActiveMode != GtexRuntimeMode.LivePlayback)
            {
                return;
            }

            GtexOriginalVisualRuntimePolicy.NativeAutonomousPlay = false;

            var visualDirector = FindFirstObjectByType<GtexVisualMatchDirector>();
            if (visualDirector != null && visualDirector.enabled)
            {
                visualDirector.enabled = false;
            }

            var simulationHost = FindFirstObjectByType<GtexSimRuntimeHost>();
            if (simulationHost != null && simulationHost.enabled)
            {
                simulationHost.enabled = false;
            }
        }
    }
}
