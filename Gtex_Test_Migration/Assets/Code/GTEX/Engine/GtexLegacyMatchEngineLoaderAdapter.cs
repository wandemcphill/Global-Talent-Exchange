using System.Threading.Tasks;
using FStudio.GTEX;
using FStudio.MatchEngine;
using FStudio.UI;
using FStudio.UI.MatchThemes.MatchEvents;
using Shared.Responses;

namespace FStudio.GTEX.Engine
{
    public sealed class GtexLegacyMatchEngineLoaderAdapter
    {
        public bool IsAvailable => MatchEngineLoader.Current != null;

        public bool IsPlaybackSceneReady =>
            MatchEngineLoader.Current != null &&
            UILoader.Current != null;

        public string DescribePlaybackSceneAvailability()
        {
            return "MatchEngineLoader present=" + (MatchEngineLoader.Current != null) +
                   ", UILoader present=" + (UILoader.Current != null) + ".";
        }

        public Task CreateMatch(MatchCreateRequest matchData)
        {
            return MatchEngineLoader.CreateMatch(matchData);
        }

        public Task StartMatchEngine(UpcomingMatchEvent matchEvent, bool homeKit, bool awayKit, GtexMatchConfig config = null)
        {
            if (MatchEngineLoader.Current == null)
            {
                return Task.CompletedTask;
            }

            return MatchEngineLoader.Current.StartMatchEngine(matchEvent, homeKit, awayKit, config);
        }

        public Task UnloadMatch()
        {
            if (MatchEngineLoader.Current == null)
            {
                return Task.CompletedTask;
            }

            return MatchEngineLoader.Current.UnloadMatch();
        }
    }
}
