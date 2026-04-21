using Shared.Responses;

namespace FStudio.GTEX.Engine
{
    public readonly struct GtexLiveStateSignal
    {
        public GtexLiveStateSignal(MatchResponse state, bool isFallback)
        {
            State = state;
            IsFallback = isFallback;
        }

        public MatchResponse State { get; }

        public bool IsFallback { get; }
    }
}
