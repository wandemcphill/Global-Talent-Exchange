#if UNITY_EDITOR
using UnityEngine;

namespace FStudio.MatchEngine.Cameras
{
    internal static class GTEXCameraCompileCheck
    {
        [UnityEditor.InitializeOnLoadMethod]
        private static void ValidateCameraSystemAssembly()
        {
            _ = typeof(CameraSystem);
        }
    }
}
#endif
