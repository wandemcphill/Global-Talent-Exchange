#if UNITY_EDITOR
using UnityEditor;

namespace FStudio.GTEX.Editor
{
    [InitializeOnLoad]
    internal static class GTEXProductionCompileSentinel
    {
        static GTEXProductionCompileSentinel()
        {
            EditorApplication.delayCall += () =>
            {
                if (EditorUtility.scriptCompilationFailed)
                {
                    UnityEngine.Debug.LogError("[GTEX] Production compile sentinel: script compilation has errors.");
                }
            };
        }
    }
}
#endif
