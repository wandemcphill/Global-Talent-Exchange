using UnityEngine;

namespace FStudio.GTEX.VisualBridge
{
    public enum GtexVisualPassStyle
    {
        Ground,
        ThroughGround,
        Lofted,
        Cross
    }

    public sealed class GtexVisualCommand
    {
        public GtexVisualCommandType type;
        public string eventId = string.Empty;
        public int sequence = -1;
        public string actorPlayerId = string.Empty;
        public string targetPlayerId = string.Empty;
        public string secondaryTargetPlayerId = string.Empty;
        public string teamId = string.Empty;
        public Vector3 targetWorldPosition;
        public Vector3 secondaryWorldPosition;
        public float matchMinute;
        public float urgency;
        public float duration;
        public int homeScore;
        public int awayScore;
        public string homeTeamName = string.Empty;
        public string awayTeamName = string.Empty;
        public bool isSuccessful = true;
        public string outcome = string.Empty;
        public string sourceEventType = string.Empty;
        public GtexVisualPassStyle passStyle = GtexVisualPassStyle.Ground;
    }
}
