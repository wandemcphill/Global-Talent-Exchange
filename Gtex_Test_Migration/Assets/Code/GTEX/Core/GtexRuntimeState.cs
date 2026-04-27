using UnityEngine;

namespace FStudio.GTEX.Core
{
    public static class GtexRuntimeState
    {
        public static bool IsBooting { get; private set; }

        public static bool IsStarted { get; private set; }

        public static GtexRuntimeMode ActiveMode { get; private set; }

        public static bool TryBeginBoot(GtexRuntimeMode mode, string source)
        {
            if (IsBooting || IsStarted)
            {
                Debug.Log("[GTEX Runtime] Boot ignored from " + source + "; already booting/started as " + ActiveMode + ".");
                return false;
            }

            IsBooting = true;
            ActiveMode = mode;
            Debug.Log("[GTEX Runtime] Boot begin from " + source + ": " + mode);
            return true;
        }

        public static void MarkStarted(GtexRuntimeMode mode, string source)
        {
            IsBooting = false;
            IsStarted = true;
            ActiveMode = mode;
            Debug.Log("[GTEX Runtime] Started from " + source + ": " + mode);
        }

        public static void ResetForSceneUnload()
        {
            IsBooting = false;
            IsStarted = false;
            ActiveMode = default;
        }
    }
}
