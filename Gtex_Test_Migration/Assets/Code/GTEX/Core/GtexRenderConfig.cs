using UnityEngine;

namespace FStudio.GTEX.Core
{
    public sealed class GtexRenderConfig : MonoBehaviour
    {
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
        private static void Bootstrap()
        {
            ApplyForCurrentMode();
        }

        private void Awake()
        {
            ApplyForCurrentMode();
        }

        public static void ApplyForCurrentMode()
        {
            if (QualitySettings.names == null || QualitySettings.names.Length == 0)
            {
                Debug.Log("[GTEX] No quality levels configured.");
                return;
            }

            var targetQualityIndex = GtexConfig.IsDev
                ? Mathf.Clamp(GtexConfig.DevelopmentQualityIndex, 0, QualitySettings.names.Length - 1)
                : Mathf.Clamp(GtexConfig.ProductionQualityIndex, 0, QualitySettings.names.Length - 1);

            QualitySettings.SetQualityLevel(targetQualityIndex, true);
            Debug.Log(
                "[GTEX] Render mode applied: " +
                GtexConfig.Mode +
                " -> " +
                QualitySettings.names[targetQualityIndex]);
        }
    }
}
