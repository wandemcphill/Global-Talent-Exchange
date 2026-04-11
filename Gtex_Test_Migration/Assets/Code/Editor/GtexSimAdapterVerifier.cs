using System;
using Stopwatch = System.Diagnostics.Stopwatch;
using FStudio.GTEX.Simulation;
using UnityEditor;
using UnityEngine;

namespace FStudio.GTEX.Editor
{
    public static class GtexSimAdapterVerifier
    {
        private sealed class VerificationResult
        {
            public int RenderedEvents;
            public int CheerCount;
            public int BooCount;
            public int HomeScore;
            public int AwayScore;

            public string Scoreline => HomeScore + "-" + AwayScore;

            public string Summary =>
                "RenderedEvents=" + RenderedEvents +
                ", Cheers=" + CheerCount +
                ", Boos=" + BooCount +
                ", Score=" + Scoreline + ".";
        }

        [MenuItem("Tools/GTEX/Simulation/Verify Adapters")]
        public static void VerifyFromEditorMenu()
        {
            VerifyAdapters();
        }

        public static void VerifyFromCommandLine()
        {
            VerifyAdapters();
        }

        private static VerificationResult VerifyAdapters()
        {
            const string actionName = "Adapter test";
            var stopwatch = Stopwatch.StartNew();
            GtexRuntimeToolStatus.Begin(actionName);
            Debug.Log("[GTEX Sim Verify] Starting adapter verification.");

            var host = new GameObject("GTEX Sim Adapter Verification");

            try
            {
                var renderer = host.AddComponent<GtexSimRenderer>();
                var crowd = host.AddComponent<GtexSimCrowdController>();

                var engine = new GtexSimEngine(new GtexSimConfig
                {
                    FullMatchMinutes = 90f,
                    HalfLengthMinutes = 45f,
                    TargetRealDurationMinutes = 1f,
                    EventCheckWindowMinutes = 1f,
                    BaseEventChancePerWindow = 1d,
                    RandomSeed = 7,
                    Logger = message => Debug.Log(message)
                });

                renderer.Bind(engine);
                crowd.Bind(engine);

                engine.StartMatch();

                for (var index = 0; index < 120; index += 1)
                {
                    engine.UpdateMatch(1f);
                }

                if (engine.State != GtexSimState.FullTime)
                {
                    throw new InvalidOperationException("Simulation did not reach full-time.");
                }

                if (renderer.RenderedEventCount <= 0)
                {
                    throw new InvalidOperationException("Renderer adapter did not react to any simulation events.");
                }

                if (crowd.CheerCount <= 0)
                {
                    throw new InvalidOperationException("Crowd adapter did not react to any goal events.");
                }

                if (crowd.BooCount <= 0)
                {
                    throw new InvalidOperationException("Crowd adapter did not react to any foul events.");
                }

                var result = new VerificationResult
                {
                    RenderedEvents = renderer.RenderedEventCount,
                    CheerCount = crowd.CheerCount,
                    BooCount = crowd.BooCount,
                    HomeScore = engine.HomeScore,
                    AwayScore = engine.AwayScore
                };

                stopwatch.Stop();
                GtexRuntimeToolStatus.CompleteSuccess(
                    actionName,
                    "Adapter test passed. " + result.Summary,
                    result.Scoreline,
                    stopwatch.Elapsed.TotalMilliseconds);

                Debug.Log("[GTEX Sim Verify] Success. " + result.Summary);
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
                UnityEngine.Object.DestroyImmediate(host);
            }
        }
    }
}
