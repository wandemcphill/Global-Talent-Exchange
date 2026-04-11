using UnityEngine;
using FStudio.GTEX;
using FStudio.GTEX.Core;

public class StartMatch : MonoBehaviour
{
    void Start()
    {
        Debug.Log("[BOOT] StartMatch fired");

        // Use the shared GTEX bootstrap flow instead of creating an unconfigured runtime.
        bool started = GtexRuntimeBootstrap.TryAutoStart();

        Debug.Log("[BOOT] TryAutoStart result: " + started);
    }
}
