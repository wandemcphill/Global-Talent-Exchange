using FStudio.GTEX.Core;
using FStudio.GTEX.VisualBridge;
using FStudio.MatchEngine;
using UnityEngine;

namespace FStudio.GTEX.Presentation
{
    /// <summary>
    /// Keeps Original Visual Runtime from fighting live transform playback.
    /// When OVR owns the scene, live GtexMatchRuntime must stay off and
    /// MatchManager external playback must stay false.
    /// </summary>
    [DefaultExecutionOrder(10011)]
    public sealed class GtexOriginalVisualIsolationGuard : MonoBehaviour
    {
        private const float AuditIntervalSeconds = 1f;

        private static GtexOriginalVisualIsolationGuard instance;
        private float nextAuditAt;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void Install()
        {
            if (instance != null)
            {
                return;
            }

            var host = new GameObject("GTEX Original Visual Isolation");
            DontDestroyOnLoad(host);
            instance = host.AddComponent<GtexOriginalVisualIsolationGuard>();
        }

        private void LateUpdate()
        {
            if (!GtexOriginalVisualRuntimePolicy.IsOriginalVisualRuntime())
            {
                return;
            }

            if (Time.unscaledTime < nextAuditAt)
            {
                return;
            }

            nextAuditAt = Time.unscaledTime + AuditIntervalSeconds;
            Enforce();
        }

        private static void Enforce()
        {
            var liveRuntime = FindFirstObjectByType<GtexMatchRuntime>();
            if (liveRuntime != null && liveRuntime.enabled)
            {
                liveRuntime.enabled = false;
                Debug.LogWarning(
                    "[GTEX OriginalVisualRuntime] Disabled GtexMatchRuntime so live transform playback cannot fight native football.");
            }

            if (MatchManager.Current != null && MatchManager.Current.ExternalPlaybackEnabled)
            {
                MatchManager.Current.SetExternalPlayback(false);
                Debug.LogWarning(
                    "[GTEX OriginalVisualRuntime] Cleared ExternalPlayback; original simulator owns the pitch.");
            }

            // Ensure the visual bridge can run if present in the OVR scene.
            var visualDirector = FindFirstObjectByType<GtexVisualMatchDirector>();
            if (visualDirector != null && !visualDirector.enabled)
            {
                visualDirector.enabled = true;
                Debug.Log("[GTEX OriginalVisualRuntime] Re-enabled GtexVisualMatchDirector.");
            }
        }
    }
}
