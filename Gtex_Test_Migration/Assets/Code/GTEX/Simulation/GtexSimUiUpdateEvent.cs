using FStudio.Events;

namespace FStudio.GTEX.Simulation
{
    public sealed class GtexSimUiUpdateEvent : IBaseEvent
    {
        public GtexSimUiUpdateEvent(
            string homeTeamName,
            string awayTeamName,
            int homeScore,
            int awayScore,
            float matchMinute,
            GtexSimState state,
            string lastEventSummary)
        {
            HomeTeamName = homeTeamName;
            AwayTeamName = awayTeamName;
            HomeScore = homeScore;
            AwayScore = awayScore;
            MatchMinute = matchMinute;
            State = state;
            LastEventSummary = lastEventSummary;
        }

        public string HomeTeamName { get; }

        public string AwayTeamName { get; }

        public int HomeScore { get; }

        public int AwayScore { get; }

        public float MatchMinute { get; }

        public GtexSimState State { get; }

        public string LastEventSummary { get; }
    }
}
