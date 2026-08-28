using FStudio.GTEX.Core;
using FStudio.GTEX.Simulation;
using FStudio.GTEX.VisualBridge;
using UnityEngine;

namespace FStudio.GTEX.Presentation
{
    /// <summary>
    /// Ensures LivePlayback cannot be contaminated by the legacy visual/simulation
    /// controllers that are valid for the standalone asset demo but not for GTEX.
    /// </summary>
    [DefaultExecutionOrder(10010)]
    public sealed class GtexLivePlaybackIsolationGuard : MonoBehaviour
    {
        private static GtexLivePlaybackIsolationGuard instance;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void Install()
        {
            if (instance != null)
            {
                return;
            }

            var host = new GameObject("GTEX Live Playback Isolation");
            DontDestroyOnLoad(host);
            instance = host.AddComponent<GtexLivePlaybackIsolationGuard>();
        }

        private void LateUpdate()
        {
            if (GtexRuntimeState.ActiveMode != GtexRuntimeMode.LivePlayback)
            {
                return;
            }

            // LivePlayback owns all match decisions. The original visual director
            // and local simulation host must not retain update authority over the
            // same players, ball, score, camera, or crowd.
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
