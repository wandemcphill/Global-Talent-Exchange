using System;

namespace FStudio.GTEX.Illusion
{
    public enum GtexIllusionEventKind
    {
        Unknown,
        Commentary,
        Pass,
        ThroughPass,
        Dribble,
        Shot,
        Save,
        Goal,
        Tackle,
        Foul,
        Reset
    }

    public enum GtexIllusionSceneKind
    {
        Unknown,
        CommentaryScene,
        PassScene,
        ThroughPassScene,
        DribbleScene,
        ShotScene,
        SaveScene,
        GoalScene,
        TackleScene,
        FoulScene,
        ResetScene
    }

    [Serializable]
    public sealed class GtexIllusionTimeline
    {
        public string matchId = "illusion-sample";
        public string homeTeam = "Home";
        public string awayTeam = "Away";
        public int seed = 1337;
        public GtexIllusionTimelineEvent[] events = Array.Empty<GtexIllusionTimelineEvent>();
    }

    [Serializable]
    public sealed class GtexIllusionTimelineEvent
    {
        public float minute;
        public string type = string.Empty;
        public string team = string.Empty;
        public string from = string.Empty;
        public string to = string.Empty;
        public string player = string.Empty;
        public string target = string.Empty;
        public string outcome = string.Empty;
        public string commentary = string.Empty;
        public string overlay = string.Empty;
        public float duration;
        public float x;
        public float z;
    }

    [Serializable]
    public sealed class GtexIllusionScenePackage
    {
        public string matchId = "illusion-sample";
        public string homeTeam = "Home";
        public string awayTeam = "Away";
        public int seed = 1337;
        public string overlay = string.Empty;
        public GtexIllusionPlayerCard playerCard = new GtexIllusionPlayerCard();
        public GtexIllusionStatLine[] stats = Array.Empty<GtexIllusionStatLine>();
        public GtexIllusionNarrativeItem[] liveFeed = Array.Empty<GtexIllusionNarrativeItem>();
        public GtexIllusionSceneRecord[] scenes = Array.Empty<GtexIllusionSceneRecord>();
    }

    [Serializable]
    public sealed class GtexIllusionPlayerCard
    {
        public string playerId = string.Empty;
        public string playerName = string.Empty;
        public string teamName = string.Empty;
        public string role = string.Empty;
        public int shirtNumber;
        public float rating;
        public string summary = string.Empty;
    }

    [Serializable]
    public sealed class GtexIllusionStatLine
    {
        public string label = string.Empty;
        public string homeValue = string.Empty;
        public string awayValue = string.Empty;
    }

    [Serializable]
    public sealed class GtexIllusionNarrativeItem
    {
        public int minute;
        public string label = string.Empty;
        public string text = string.Empty;
    }

    [Serializable]
    public sealed class GtexIllusionSceneRecord
    {
        public float minute;
        public string type = string.Empty;
        public string team = string.Empty;
        public string actor = string.Empty;
        public string target = string.Empty;
        public string outcome = string.Empty;
        public string commentary = string.Empty;
        public string overlay = string.Empty;
        public float duration;
        public float x;
        public float z;
        public string[] actors = Array.Empty<string>();
    }

    public sealed class GtexIllusionScene
    {
        public GtexIllusionEventKind EventKind;
        public GtexIllusionSceneKind SceneKind;
        public float Minute;
        public string TeamId = string.Empty;
        public string ActorUid = string.Empty;
        public string TargetUid = string.Empty;
        public string Outcome = string.Empty;
        public string Commentary = string.Empty;
        public string Overlay = string.Empty;
        public float DurationSeconds;
        public float TargetX;
        public float TargetZ;
    }
}
