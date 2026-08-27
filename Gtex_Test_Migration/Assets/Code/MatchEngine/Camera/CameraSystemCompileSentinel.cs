#if UNITY_EDITOR
using UnityEngine;

namespace FStudio.MatchEngine.Cameras
{
    internal static class CameraSystemCompileSentinel
    {
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterAssembliesLoaded)]
        private static void ValidateCameraSystemAssembly()
        {
            _ = typeof(CameraSystem);
        }
    }
}
#endif
