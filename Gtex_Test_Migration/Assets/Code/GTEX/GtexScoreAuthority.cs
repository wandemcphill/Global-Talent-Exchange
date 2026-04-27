using System;

namespace FStudio.GTEX
{
    public sealed class GtexScoreState
    {
        public string homeLabel;
        public string awayLabel;
        public int homeScore;
        public int awayScore;
        public float minute;
        public string lastEvent;
    }

    public static class GtexScoreAuthority
    {
        public static event Action<GtexScoreState> ScoreChanged;

        private static readonly GtexScoreState state = new GtexScoreState
        {
            homeLabel = "HOME",
            awayLabel = "AWAY"
        };

        public static GtexScoreState Current => state;

        public static void Reset(string homeLabel = "HOME", string awayLabel = "AWAY")
        {
            state.homeLabel = string.IsNullOrWhiteSpace(homeLabel) ? "HOME" : homeLabel.Trim();
            state.awayLabel = string.IsNullOrWhiteSpace(awayLabel) ? "AWAY" : awayLabel.Trim();
            state.homeScore = 0;
            state.awayScore = 0;
            state.minute = 0f;
            state.lastEvent = string.Empty;
            Publish();
        }

        public static void SetTeams(string home, string away)
        {
            state.homeLabel = string.IsNullOrWhiteSpace(home) ? state.homeLabel : home.Trim();
            state.awayLabel = string.IsNullOrWhiteSpace(away) ? state.awayLabel : away.Trim();
            Publish();
        }

        public static void SetScore(int home, int away, float minute, string lastEvent = null)
        {
            state.homeScore = home < 0 ? 0 : home;
            state.awayScore = away < 0 ? 0 : away;
            state.minute = minute < 0f ? 0f : minute;
            state.lastEvent = lastEvent ?? string.Empty;
            Publish();
        }

        private static void Publish()
        {
            GtexRuntimeTelemetry.RegisterScoreAuthorityUpdate();
            ScoreChanged?.Invoke(state);
        }
    }
}
