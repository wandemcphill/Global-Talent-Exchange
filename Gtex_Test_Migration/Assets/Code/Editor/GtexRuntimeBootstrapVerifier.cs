using System;
using Stopwatch = System.Diagnostics.Stopwatch;
using FStudio.GTEX.Core;
using FStudio.GTEX.Simulation;
using UnityEditor;
using UnityEngine;

namespace FStudio.GTEX.Editor
{
    public static class GtexRuntimeBootstrapVerifier
    {
        private sealed class VerificationResult
        {
            public GtexRuntimeMode Mode;
            public int HomeScore;
            public int AwayScore;
            public GtexSimState State;

            public string Scoreline => HomeScore + "-" + AwayScore;

            public string Summary =>
                "Mode=" + Mode +
                ", Score=" + Scoreline +
                ", State=" + State + ".";
        }

        [MenuItem("Tools/GTEX/Simulation/Verify Runtime Bootstrap")]
        public static void VerifyFromEditorMenu()
        {
            VerifyLocalSimulationBootstrap();
        }

        public static void VerifyFromCommandLine()
        {
            VerifyLocalSimulationBootstrap();
        }

        private static VerificationResult VerifyLocalSimulationBootstrap()
        {
            const string actionName = "Local simulation test";
            var stopwatch = Stopwatch.StartNew();
            GtexRuntimeToolStatus.Begin(actionName);
            Debug.Log("[GTEX Runtime Verify] Starting runtime bootstrap verification.");
            DestroyExistingRuntimeObjects();

            try
            {
                var config = new GtexMatchConfig
                {
                    enabled = true,
                    autoStartOnBoot = true,
                    runtimeMode = "simulation",
                    matchId = "sim-bootstrap-test",
                    verboseLogging = false,
                    showCrowd = true,
                    simulationTargetDurationMinutes = 1f,
                    simulationEventCheckWindowMinutes = 1f,
                    simulationBaseEventChancePerWindow = 1f,
                    simulationRandomSeed = 7
                };

                config.EnsureDefaults();

                if (!GtexRuntimeBootstrap.TryAutoStart(config, true))
                {
                    throw new InvalidOperationException("Runtime bootstrap did not start local simulation.");
                }

                var simHost = UnityEngine.Object.FindFirstObjectByType<GtexSimRuntimeHost>();
                if (simHost == null)
                {
                    throw new InvalidOperationException("Local simulation host was not created.");
                }

                if (UnityEngine.Object.FindFirstObjectByType<GtexMatchRuntime>() != null)
                {
                    throw new InvalidOperationException("Live GTEX runtime should not be created in local simulation mode.");
                }

                if (simHost.Engine == null || !simHost.Engine.IsRunning)
                {
                    throw new InvalidOperationException("Local simulation engine was not started.");
                }

                var targetRealDurationSeconds = simHost.Engine.Clock.TargetRealDurationSeconds;
                if (Math.Abs(targetRealDurationSeconds - 60f) > 0.01f)
                {
                    throw new InvalidOperationException(
                        "Local simulation did not apply config duration. Target seconds=" + targetRealDurationSeconds + ".");
                }

                var updateSteps = Mathf.CeilToInt(targetRealDurationSeconds) + 2;
                for (var index = 0; index < updateSteps; index += 1)
                {
                    simHost.Engine.UpdateMatch(1f);
                }

                if (simHost.Engine.State != GtexSimState.FullTime)
                {
                    throw new InvalidOperationException("Local simulation did not reach full-time.");
                }

                var result = new VerificationResult
                {
                    Mode = config.ResolveRuntimeMode(),
                    HomeScore = simHost.Engine.HomeScore,
                    AwayScore = simHost.Engine.AwayScore,
                    State = simHost.Engine.State
                };

                stopwatch.Stop();
                GtexRuntimeToolStatus.CompleteSuccess(
                    actionName,
                    "Local simulation test passed. " + result.Summary,
                    result.Scoreline,
                    stopwatch.Elapsed.TotalMilliseconds);

                Debug.Log("[GTEX Runtime Verify] Success. " + result.Summary);
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
