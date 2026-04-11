using System.Collections.Generic;
using UnityEngine;

namespace FStudio.GTEX.Simulation
{
    public sealed class GtexSimRenderer : MonoBehaviour
    {
        private const float DefaultBannerDurationSeconds = 3.5f;
        private const int MaxRecentFeedEntries = 5;

        [SerializeField] private bool logStateChanges = true;
        [SerializeField] private bool logMatchEvents = true;

        private GtexSimEngine engine;
        private float bannerTimerRemaining;
        private readonly List<string> recentFeedEntries = new List<string>(MaxRecentFeedEntries);

        public int RenderedEventCount { get; private set; }

        public GtexSimState LastObservedState { get; private set; } = GtexSimState.Kickoff;

        public string LastReaction { get; private set; } = string.Empty;

        public string LastEventSummary { get; private set; } = "Waiting for kickoff";

        public string ActiveBannerText { get; private set; } = "Pre-match";

        public Color ActiveBannerColor { get; private set; } = new Color(0.91f, 0.96f, 0.98f, 1f);

        public IReadOnlyList<string> RecentFeedEntries => recentFeedEntries;

        public void Bind(GtexSimEngine simulationEngine)
        {
            if (ReferenceEquals(engine, simulationEngine))
            {
                return;
            }

            Unbind();
            engine = simulationEngine;

            if (engine == null)
            {
                return;
            }

            engine.StateChanged += HandleStateChanged;
            engine.EventSystem.EventGenerated += HandleEventGenerated;
            Debug.Log("[GTEX Sim Renderer] Bound to simulation engine.");
        }

        public void Unbind()
        {
            if (engine == null)
            {
                return;
            }

            engine.StateChanged -= HandleStateChanged;
            engine.EventSystem.EventGenerated -= HandleEventGenerated;
            engine = null;
        }

        private void OnDestroy()
        {
            Unbind();
        }

        private void Update()
        {
            if (bannerTimerRemaining <= 0f)
            {
                return;
            }

            bannerTimerRemaining = Mathf.Max(0f, bannerTimerRemaining - Time.unscaledDeltaTime);
            if (bannerTimerRemaining > 0f)
            {
                return;
            }

            ActiveBannerText = "Match Live";
            ActiveBannerColor = new Color(0.91f, 0.96f, 0.98f, 1f);
        }

        private void HandleStateChanged(GtexSimState state)
        {
            LastObservedState = state;
            LastReaction = "State -> " + state;
            LastEventSummary = DescribeState(state);
            SetBanner(LastEventSummary, ResolveStateColor(state));
            AppendFeedEntry(FormatFeedEntry(engine != null ? engine.Clock.CurrentMatchMinute : 0f, LastEventSummary));

            if (logStateChanges)
            {
                Debug.Log("[GTEX Sim Renderer] " + LastReaction);
            }
        }

        private void HandleEventGenerated(GtexSimEvent matchEvent)
        {
            RenderedEventCount += 1;
            LastReaction = DescribeReaction(matchEvent);
            LastEventSummary = matchEvent != null ? matchEvent.Summary : LastEventSummary;
            SetBanner(LastEventSummary, ResolveEventColor(matchEvent));
            AppendFeedEntry(FormatFeedEntry(matchEvent != null ? matchEvent.Time : 0f, LastEventSummary));

            if (logMatchEvents)
            {
                Debug.Log("[GTEX Sim Renderer] " + LastReaction);
            }
        }

        private void SetBanner(string bannerText, Color bannerColor)
        {
            ActiveBannerText = bannerText;
            ActiveBannerColor = bannerColor;
            bannerTimerRemaining = DefaultBannerDurationSeconds;
        }

        private void AppendFeedEntry(string entry)
        {
            if (string.IsNullOrWhiteSpace(entry))
            {
                return;
            }

            if (recentFeedEntries.Count == MaxRecentFeedEntries)
            {
                recentFeedEntries.RemoveAt(0);
            }

            recentFeedEntries.Add(entry);
        }

        private static string FormatFeedEntry(float minute, string summary)
        {
            return minute.ToString("0.0") + "'  " + summary;
        }

        private static string DescribeReaction(GtexSimEvent matchEvent)
        {
            if (matchEvent is GtexGoalEvent goalEvent)
            {
                return "Render goal for " + goalEvent.ScoringTeam + " at " + goalEvent.Time.ToString("0.0") + ".";
            }

            if (matchEvent is GtexFoulEvent foulEvent)
            {
                return "Render foul for " + foulEvent.Team + " at " + foulEvent.Time.ToString("0.0") + ".";
            }

            if (matchEvent is GtexCardEvent cardEvent)
            {
                return "Render " + cardEvent.CardType + " card for " + cardEvent.Team + " at " + cardEvent.Time.ToString("0.0") + ".";
            }

            if (matchEvent is GtexMissedChanceEvent missedChanceEvent)
            {
                return "Render missed chance for " + missedChanceEvent.Team + " at " + missedChanceEvent.Time.ToString("0.0") + ".";
            }

            return "Render event: " + matchEvent;
        }

        private static string DescribeState(GtexSimState state)
        {
            switch (state)
            {
                case GtexSimState.FirstHalf:
                    return "First Half";
                case GtexSimState.HalfTime:
                    return "Half-Time";
                case GtexSimState.SecondHalf:
                    return "Second Half";
                case GtexSimState.FullTime:
                    return "Full-Time";
                case GtexSimState.Kickoff:
                default:
                    return "Kickoff";
            }
        }

        private static Color ResolveStateColor(GtexSimState state)
        {
            switch (state)
            {
                case GtexSimState.HalfTime:
                    return new Color(0.94f, 0.82f, 0.28f, 1f);
                case GtexSimState.FullTime:
                    return new Color(0.58f, 0.85f, 0.71f, 1f);
                default:
                    return new Color(0.91f, 0.96f, 0.98f, 1f);
            }
        }

        private static Color ResolveEventColor(GtexSimEvent matchEvent)
        {
            if (matchEvent is GtexGoalEvent)
            {
                return new Color(0.43f, 0.89f, 0.57f, 1f);
            }

            if (matchEvent is GtexCardEvent cardEvent)
            {
                return cardEvent.CardType == GtexSimCardType.Red
                    ? new Color(0.9f, 0.31f, 0.29f, 1f)
                    : new Color(0.96f, 0.79f, 0.22f, 1f);
            }

            if (matchEvent is GtexFoulEvent)
            {
                return new Color(0.95f, 0.62f, 0.28f, 1f);
            }

            return new Color(0.76f, 0.88f, 0.98f, 1f);
        }
    }
}
