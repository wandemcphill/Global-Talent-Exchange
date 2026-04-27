using FStudio.GTEX;
using FStudio.GTEX.Engine;
using FStudio.MatchEngine;
using FStudio.MatchEngine.Enums;
using UnityEngine;

namespace FStudio.GTEX.VisualBridge
{
    public sealed class GtexScoreVisualBridge : MonoBehaviour
    {
        [SerializeField] private bool forceOriginalVisualRuntimeFlag = true;

        private void OnEnable()
        {
            if (forceOriginalVisualRuntimeFlag)
            {
                GtexRuntimeFlags.SetMode(GtexBootMode.OriginalVisualRuntime, true);
            }

            GtexScoreAuthority.ScoreChanged += HandleScoreChanged;
            HandleScoreChanged(GtexScoreAuthority.Current);
        }

        private void OnDisable()
        {
            GtexScoreAuthority.ScoreChanged -= HandleScoreChanged;
        }

        private static void HandleScoreChanged(GtexScoreState score)
        {
            if (score == null)
            {
                return;
            }

            var manager = MatchManager.Current;
            if (manager != null)
            {
                if (manager.ExternalPlaybackEnabled)
                {
                    manager.SetExternalPlayback(false);
                }

                manager.homeTeamScore = Mathf.Max(0, score.homeScore);
                manager.awayTeamScore = Mathf.Max(0, score.awayScore);
            }

            GtexMatchController.ReportMatchSnapshot(
                FStudio.GTEX.Core.GtexRuntimeMode.OriginalVisualRuntime,
                ResolvePhase(score.minute),
                true,
                nameof(GtexScoreVisualBridge),
                score.minute,
                score.homeScore,
                score.awayScore,
                score.lastEvent);
        }

        private static GtexMatchPhase ResolvePhase(float minute)
        {
            if (minute >= 90f)
            {
                return GtexMatchPhase.FullTime;
            }

            if (minute >= 45f)
            {
                return GtexMatchPhase.SecondHalf;
            }

            return GtexMatchPhase.FirstHalf;
        }
    }
}
