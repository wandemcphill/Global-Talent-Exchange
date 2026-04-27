using UnityEngine;
using FStudio.GTEX;
using FStudio.GTEX.Core;
using FStudio.GTEX.Simulation;

public class StartMatch : MonoBehaviour
{
    void Start()
    {
        if (GtexOriginalVisualRuntimePolicy.IsOriginalVisualRuntime())
        {
            GtexOriginalVisualRuntimePolicy.LogBlocked("MatchStarter");
            enabled = false;
            return;
        }

        if (Object.FindFirstObjectByType<GtexMatchRuntime>() != null ||
            Object.FindFirstObjectByType<GtexSimRuntimeHost>() != null)
        {
            Debug.Log("[BOOT] GTEX runtime already active. Skipping StartMatch bootstrap.");
            return;
        }

        Debug.Log("[BOOT] StartMatch fired");

        // Use the shared GTEX bootstrap flow instead of creating an unconfigured runtime.
        bool started = GtexRuntimeBootstrap.TryAutoStart();

        Debug.Log("[BOOT] TryAutoStart result: " + started);
    }
}
