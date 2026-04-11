namespace FStudio.GTEX.Simulation
{
    public enum GtexSimTeamSide
    {
        Home,
        Away
    }

    public enum GtexSimCardType
    {
        Yellow,
        Red
    }

    public abstract class GtexSimEvent
    {
        protected GtexSimEvent(float time)
        {
            Time = time;
        }

        public float Time { get; protected set; }

        public abstract string Summary { get; }

        public override string ToString()
        {
            return Summary + " @ " + Time.ToString("0.0");
        }
    }

    public sealed class GtexGoalEvent : GtexSimEvent
    {
        public GtexGoalEvent(float time, GtexSimTeamSide scoringTeam, int homeScore, int awayScore)
            : base(time)
        {
            ScoringTeam = scoringTeam;
            HomeScore = homeScore;
            AwayScore = awayScore;
        }

        public GtexSimTeamSide ScoringTeam { get; }

        public int HomeScore { get; }

        public int AwayScore { get; }

        public override string Summary => ScoringTeam + " goal (" + HomeScore + "-" + AwayScore + ")";
    }

    public sealed class GtexMissedChanceEvent : GtexSimEvent
    {
        public GtexMissedChanceEvent(float time, GtexSimTeamSide team, float chanceQuality)
            : base(time)
        {
            Team = team;
            ChanceQuality = chanceQuality;
        }

        public GtexSimTeamSide Team { get; }

        public float ChanceQuality { get; }

        public override string Summary => Team + " missed chance (quality " + ChanceQuality.ToString("0.00") + ")";
    }

    public sealed class GtexFoulEvent : GtexSimEvent
    {
        public GtexFoulEvent(float time, GtexSimTeamSide team, float severity)
            : base(time)
        {
            Team = team;
            Severity = severity;
        }

        public GtexSimTeamSide Team { get; }

        public float Severity { get; }

        public override string Summary => Team + " foul (severity " + Severity.ToString("0.00") + ")";
    }

    public sealed class GtexCardEvent : GtexSimEvent
    {
        public GtexCardEvent(float time, GtexSimTeamSide team, GtexSimCardType cardType)
            : base(time)
        {
            Team = team;
            CardType = cardType;
        }

        public GtexSimTeamSide Team { get; }

        public GtexSimCardType CardType { get; }

        public override string Summary => Team + " " + CardType + " card";
    }
}
