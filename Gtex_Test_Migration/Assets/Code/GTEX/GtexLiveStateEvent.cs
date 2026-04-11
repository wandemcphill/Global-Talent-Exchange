using FStudio.Events;

namespace FStudio.GTEX {
    public struct GtexLiveStateEvent : IBaseEvent {
        public readonly MatchResponse State;
        public readonly bool IsFallback;

        public GtexLiveStateEvent(MatchResponse state, bool isFallback) {
            State = state;
            IsFallback = isFallback;
        }
    }
}
