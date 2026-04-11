using FStudio.Events;
using FStudio.UI.Events;
using UnityEngine;

namespace FStudio.GTEX.Simulation
{
    public sealed class GtexSimUiBridge : MonoBehaviour
    {
        [SerializeField] private bool broadcastLegacyUiSignals = true;
        [SerializeField] private bool logBroadcasts = true;

        private GtexSimEngine engine;
        private GtexSimRuntimeHost host;
        private bool hasRaisedMatchComplete;

        public string LastEventSummary { get; private set; } = "Waiting for kickoff";

        public string Scoreline { get; private set; } = "0 - 0";

        public GtexSimState LastState { get; private set; } = GtexSimState.Kickoff;

        public float LastMatchMinute { get; private set; }

        public void Bind(GtexSimRuntimeHost runtimeHost, GtexSimEngine simulationEngine)
        {
            if (ReferenceEquals(engine, simulationEngine) && ReferenceEquals(host, runtimeHost))
            {
                return;
            }

            Unbind();
            host = runtimeHost;
            engine = simulationEngine;

            if (engine == null)
            {
                return;
            }

            hasRaisedMatchComplete = false;
            engine.StateChanged += HandleStateChanged;
            engine.EventSystem.EventGenerated += HandleEventGenerated;
            RefreshSnapshot("Simulation bridge ready.");
            RaiseScoreboardSignal();
            RaiseUpdateEvent();
            Debug.Log("[GTEX Sim UI Bridge] Bound to simulation engine.");
        }

        public void Unbind()
        {
            if (engine != null)
            {
                engine.StateChanged -= HandleStateChanged;
                engine.EventSystem.EventGenerated -= HandleEventGenerated;
            }

            engine = null;
            host = null;
            hasRaisedMatchComplete = false;
        }

        private void OnDestroy()
        {
            Unbind();
        }

        private void HandleStateChanged(GtexSimState state)
        {
            LastState = state;
            RefreshSnapshot(DescribeState(state));
            RaiseScoreboardSignal();
            RaiseUpdateEvent();

            if (state == GtexSimState.FullTime)
            {
                RaiseMatchCompleteSignal();
            }
        }

        private void HandleEventGenerated(GtexSimEvent matchEvent)
        {
            RefreshSnapshot(matchEvent?.Summary ?? "Simulation event");
            RaiseInfoSignal();
            RaiseScoreboardSignal();
            RaiseUpdateEvent();
        }

        private void RefreshSnapshot(string fallbackSummary)
        {
            if (engine == null)
            {
                return;
            }

            LastState = engine.State;
            LastMatchMinute = engine.Clock.CurrentMatchMinute;
            Scoreline = engine.HomeScore + " - " + engine.AwayScore;
            LastEventSummary = string.IsNullOrWhiteSpace(fallbackSummary) ? LastEventSummary : fallbackSummary;
        }

        private void RaiseScoreboardSignal()
        {
            if (!broadcastLegacyUiSignals || !EventManager.HasSubscribers<ShowScoreboardEvent>())
            {
                return;
            }

            EventManager.Trigger(new ShowScoreboardEvent());
            LogSignal("ShowScoreboardEvent");
        }

        private void RaiseInfoSignal()
        {
            if (!broadcastLegacyUiSignals || !EventManager.HasSubscribers<InfoboardEvent>())
            {
                return;
            }

            EventManager.Trigger(new InfoboardEvent());
            LogSignal("InfoboardEvent");
        }

        private void RaiseMatchCompleteSignal()
        {
            if (hasRaisedMatchComplete)
            {
                return;
            }

            hasRaisedMatchComplete = true;

            if (!broadcastLegacyUiSignals || !EventManager.HasSubscribers<MatchCompleteEvent>())
            {
                return;
            }

            EventManager.Trigger(new MatchCompleteEvent());
            LogSignal("MatchCompleteEvent");
        }

        private void RaiseUpdateEvent()
        {
            if (!EventManager.HasSubscribers<GtexSimUiUpdateEvent>())
            {
                return;
            }

            EventManager.Trigger(
                new GtexSimUiUpdateEvent(
                    host != null ? host.HomeDisplayName : "Home",
                    host != null ? host.AwayDisplayName : "Away",
                    engine != null ? engine.HomeScore : 0,
                    engine != null ? engine.AwayScore : 0,
                    engine != null ? engine.Clock.CurrentMatchMinute : 0f,
                    LastState,
                    LastEventSummary));
        }

        private void LogSignal(string signalName)
        {
            if (!logBroadcasts)
            {
                return;
            }

            Debug.Log("[GTEX Sim UI Bridge] Broadcast " + signalName + ".");
        }

        private static string DescribeState(GtexSimState state)
        {
            switch (state)
            {
                case GtexSimState.FirstHalf:
                    return "First half underway";
                case GtexSimState.HalfTime:
                    return "Half-time";
                case GtexSimState.SecondHalf:
                    return "Second half underway";
                case GtexSimState.FullTime:
                    return "Full-time";
                case GtexSimState.Kickoff:
                default:
                    return "Kickoff";
            }
        }
    }
}
