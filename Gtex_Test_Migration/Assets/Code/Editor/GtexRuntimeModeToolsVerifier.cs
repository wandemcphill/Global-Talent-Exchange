#if UNITY_EDITOR
using System;
using Stopwatch = System.Diagnostics.Stopwatch;
using FStudio.GTEX.Core;
using UnityEditor;
using UnityEngine;

namespace FStudio.GTEX.Editor
{
    public static class GtexRuntimeModeToolsVerifier
    {
        [MenuItem("Tools/GTEX/Runtime/Verify Mode Switcher")]
        public static void VerifyFromEditorMenu()
        {
            Verify();
        }

        public static void VerifyFromCommandLine()
        {
            Verify();
        }

        private static void Verify()
        {
            const string actionName = "Mode switcher verification";
            var stopwatch = Stopwatch.StartNew();
            GtexRuntimeToolStatus.Begin(actionName);
            Debug.Log("[GTEX Runtime Mode Verify] Starting runtime mode switcher verification.");
            var originalJson = GtexRuntimeModeTools.ReadConfigJson();

            try
            {
                GtexRuntimeModeTools.SetRuntimeMode(GtexRuntimeMode.LocalSimulation);
                if (GtexRuntimeModeTools.GetRuntimeMode() != GtexRuntimeMode.LocalSimulation)
                {
                    throw new InvalidOperationException("Failed to switch config to local simulation mode.");
                }

                GtexRuntimeModeTools.SetRuntimeMode(GtexRuntimeMode.LivePlayback);
                if (GtexRuntimeModeTools.GetRuntimeMode() != GtexRuntimeMode.LivePlayback)
                {
                    throw new InvalidOperationException("Failed to switch config back to live playback mode.");
                }

                stopwatch.Stop();
                GtexRuntimeToolStatus.CompleteSuccess(
                    actionName,
                    "Mode switcher verification passed.",
                    string.Empty,
                    stopwatch.Elapsed.TotalMilliseconds);

                Debug.Log("[GTEX Runtime Mode Verify] Success.");
            }
            catch (Exception exception)
            {
                stopwatch.Stop();
                GtexRuntimeToolStatus.CompleteFailure(actionName, exception, stopwatch.Elapsed.TotalMilliseconds);
                throw;
            }
            finally
            {
                GtexRuntimeModeTools.RestoreRawConfig(originalJson);
            }
        }
    }
}
#endif
