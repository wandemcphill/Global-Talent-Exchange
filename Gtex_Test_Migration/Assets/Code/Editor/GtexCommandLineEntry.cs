#if UNITY_EDITOR
using System;
using UnityEditor;
using UnityEngine;

namespace FStudio.GTEX.Editor
{
    public static class GtexCommandLineEntry
    {
        public static void PingAndExit()
        {
            RunAndExit(() => GtexBatchPing.Run(), "PingAndExit");
        }

        public static void BuildWindowsProductionAndExit()
        {
            RunAndExit(
                () => GtexBuildTools.BuildWindows64ProductionFromCommandLine(),
                "BuildWindowsProductionAndExit");
        }

        private static void RunAndExit(Action action, string label)
        {
            try
            {
                Debug.Log("[GTEX CLI] ENTER " + label);
                action?.Invoke();
                AssetDatabase.SaveAssets();
                Debug.Log("[GTEX CLI] SUCCESS " + label);
                EditorApplication.Exit(0);
            }
            catch (Exception ex)
            {
                Debug.LogError("[GTEX CLI] FAIL " + label + "\n" + ex);
                EditorApplication.Exit(1);
            }
        }
    }
}
#endif
