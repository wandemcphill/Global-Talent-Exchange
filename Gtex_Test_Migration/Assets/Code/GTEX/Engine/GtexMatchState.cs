using System;
using FStudio.GTEX.Core;

namespace FStudio.GTEX.Engine
{
    [Serializable]
    public sealed class GtexMatchState
    {
        public GtexRuntimeMode RuntimeMode;
        public GtexMatchPhase Phase = GtexMatchPhase.None;
        public bool CanAutoStart;
        public bool RuntimeActive;
        public float CurrentMatchMinute;
        public int HomeScore;
        public int AwayScore;
        public string MatchId = string.Empty;
        public string BaseUrl = string.Empty;
        public string OwnershipBoundary = string.Empty;
        public string ExecutorName = string.Empty;
        public string LastMessage = string.Empty;
        public DateTime UpdatedAtUtc = DateTime.UtcNow;
        public GtexEngineCommand LastCommand = new GtexEngineCommand(
            GtexEngineCommandType.None,
            GtexRuntimeMode.LivePlayback,
            string.Empty);

        public GtexMatchState Clone()
        {
            return new GtexMatchState
            {
                RuntimeMode = RuntimeMode,
                Phase = Phase,
                CanAutoStart = CanAutoStart,
                RuntimeActive = RuntimeActive,
                CurrentMatchMinute = CurrentMatchMinute,
                HomeScore = HomeScore,
                AwayScore = AwayScore,
                MatchId = MatchId,
                BaseUrl = BaseUrl,
                OwnershipBoundary = OwnershipBoundary,
                ExecutorName = ExecutorName,
                LastMessage = LastMessage,
                UpdatedAtUtc = UpdatedAtUtc,
                LastCommand = LastCommand
            };
        }
    }
}
