#if UNITY_EDITOR
using System;
using Stopwatch = System.Diagnostics.Stopwatch;
using FStudio.GTEX.Core;
using FStudio.GTEX.Simulation;
using UnityEditor;
using UnityEngine;

namespace FStudio.GTEX.Editor
{
    public static class GtexLivePlaybackVerifier
    {
        private sealed class VerificationResult
        {
            public GtexRuntimeMode Mode;
            public string MatchId;
            public string BaseUrl;
            public bool SkipBootstrap;

            public string Summary =>
                "Mode=" + Mode +
                ", MatchId=" + MatchId +
                ", SkipBootstrap=" + SkipBootstrap +
                ", BaseUrl=" + BaseUrl + ".";
        }

        [MenuItem("Tools/GTEX/Simulation/Verify Live Playback Boot")]
        public static void VerifyFromEditorMenu()
        {
            Verify();
        }

        public static void VerifyFromCommandLine()
        {
            Verify();
        }

        private static VerificationResult Verify()
        {
            const string actionName = "Live playback boot check";
            var stopwatch = Stopwatch.StartNew();
            GtexRuntimeToolStatus.Begin(actionName);
            Debug.Log("[GTEX Live Verify] Starting live playback boot verification.");
            DestroyExistingRuntimeObjects();

            try
            {
                var config = new GtexMatchConfig
                {
                    enabled = true,
                    autoStartOnBoot = true,
                    runtimeMode = "live",
                    matchId = "live-bootstrap-test",
                    environment = "local",
                    localBaseUrl = "http://127.0.0.1:8000",
                    liveAccessToken = "live-bootstrap-test-token",
                    timeoutSeconds = 1,
                    verboseLogging = false
                };

                config.EnsureDefaults();

                if (!GtexRuntimeBootstrap.TryAutoStart(config))
                {
                    throw new InvalidOperationException("Runtime bootstrap did not start live playback.");
                }

                var liveRuntime = UnityEngine.Object.FindFirstObjectByType<GtexMatchRuntime>();
                if (liveRuntime == null)
                {
                    throw new InvalidOperationException("Live GTEX runtime was not created.");
                }

                if (UnityEngine.Object.FindFirstObjectByType<GtexSimRuntimeHost>() != null)
                {
                    throw new InvalidOperationException("Local simulation host should not be created in live playback mode.");
                }

                if (!liveRuntime.HasConfig)
                {
                    throw new InvalidOperationException("Live GTEX runtime was created without config.");
                }

                if (!string.Equals(liveRuntime.MatchId, config.matchId, StringComparison.Ordinal))
                {
                    throw new InvalidOperationException("Live GTEX runtime did not keep the requested match id.");
                }

                if (Application.isBatchMode && !liveRuntime.SkipBootstrapInCurrentContext)
                {
                    throw new InvalidOperationException("Live GTEX runtime should skip bootstrap in batchmode.");
                }

                var result = new VerificationResult
                {
                    Mode = GtexRuntimeMode.LivePlayback,
                    MatchId = liveRuntime.MatchId,
                    BaseUrl = liveRuntime.BaseUrl,
                    SkipBootstrap = liveRuntime.SkipBootstrapInCurrentContext
                };

                stopwatch.Stop();
                GtexRuntimeToolStatus.CompleteSuccess(
                    actionName,
                    "Live playback boot check passed. " + result.Summary,
                    string.Empty,
                    stopwatch.Elapsed.TotalMilliseconds);

                Debug.Log("[GTEX Live Verify] Success. " + result.Summary);
                return result;
            }
            catch (Exception exception)
            {
                stopwatch.Stop();
                GtexRuntimeToolStatus.CompleteFailure(actionName, exception, stopwatch.Elapsed.TotalMilliseconds);
                throw;
            }
            finally
            {
                DestroyExistingRuntimeObjects();
            }
        }

        private static void DestroyExistingRuntimeObjects()
        {
            var simHost = UnityEngine.Object.FindFirstObjectByType<GtexSimRuntimeHost>();
            if (simHost != null)
            {
                UnityEngine.Object.DestroyImmediate(simHost.gameObject);
            }

            var liveRuntime = UnityEngine.Object.FindFirstObjectByType<GtexMatchRuntime>();
            if (liveRuntime != null)
            {
                UnityEngine.Object.DestroyImmediate(liveRuntime.gameObject);
            }
        }
    }
}
#endif
