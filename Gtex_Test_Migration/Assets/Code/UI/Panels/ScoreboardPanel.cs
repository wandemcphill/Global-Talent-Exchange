using FStudio.Events;
using FStudio.GTEX;
using FStudio.MatchEngine.Events;
using FStudio.UI.MatchThemes.MatchEvents;
using TMPro;
using UnityEngine;

namespace FStudio.UI {
    public class ScoreboardPanel : EventPanel<UpcomingMatchEvent>  {
        [SerializeField] private TextMeshProUGUI homeTeamName;
        [SerializeField] private TextMeshProUGUI awayTeamName;
        [SerializeField] private TextMeshProUGUI timeCounter;

        [SerializeField] private TextMeshProUGUI homeScoreText;
        [SerializeField] private TextMeshProUGUI awayScoreText;

        private int homeScore, awayScore;

        protected override void OnEnable() {
            base.OnEnable();

            EventManager.Subscribe<GameTimeEvent>(GameTimeUpdate);
            EventManager.Subscribe<GoalScoredEvent>(GoalScored);
            EventManager.Subscribe<FirstWhistleEvent>(FirstWhistle);
            EventManager.Subscribe<GtexLiveStateEvent>(GtexLiveStateUpdated);
        }

        private void FirstWhistle(FirstWhistleEvent kickOffEvent) {
            if (MatchEngine.MatchManager.Current != null &&
                MatchEngine.MatchManager.Current.ExternalPlaybackEnabled) {
                return;
            }

            homeScoreText.text = "0";
            awayScoreText.text = "0";
        }

        protected override void OnDisable() {
            base.OnDisable();

            EventManager.UnSubscribe<GameTimeEvent>(GameTimeUpdate);
            EventManager.UnSubscribe<GoalScoredEvent>(GoalScored);
            EventManager.UnSubscribe<FirstWhistleEvent>(FirstWhistle);
            EventManager.UnSubscribe<GtexLiveStateEvent>(GtexLiveStateUpdated);
        }

        private void GoalScored(GoalScoredEvent goalScoredEvent) {
            if (MatchEngine.MatchManager.Current != null &&
                MatchEngine.MatchManager.Current.ExternalPlaybackEnabled) {
                return;
            }

            if (!goalScoredEvent.Side) {
                homeScoreText.text = (++homeScore).ToString();
            } else {
                awayScoreText.text = (++awayScore).ToString();
            }
        }

        private void GameTimeUpdate(GameTimeEvent gameTimeUpdate) {
            if (timeCounter == null ||
                (MatchEngine.MatchManager.Current != null &&
                 MatchEngine.MatchManager.Current.ExternalPlaybackEnabled)) {
                return;
            }

            SetClock(gameTimeUpdate.GameTime);
        }

        private void GtexLiveStateUpdated(GtexLiveStateEvent liveStateEvent) {
            if (liveStateEvent.State == null) {
                return;
            }

            homeScore = Mathf.Max(0, liveStateEvent.State.homeScore);
            awayScore = Mathf.Max(0, liveStateEvent.State.awayScore);

            if (homeScoreText != null) {
                homeScoreText.text = homeScore.ToString();
            }

            if (awayScoreText != null) {
                awayScoreText.text = awayScore.ToString();
            }

            SetClock(liveStateEvent.State.clockMinute);
        }

        private void SetClock(float matchMinute) {
            if (timeCounter == null) {
                return;
            }

            float time = Mathf.Max(0, matchMinute) * 60;

            int minutes = (int)time / 60;
            int seconds = (int)time - 60 * minutes;

            timeCounter.text = string.Format("{0:00}:{1:00}", minutes, seconds);
        }

        protected override void OnEventCalled(UpcomingMatchEvent eventObject) {
            timeCounter.text = string.Empty;

            if (eventObject == null) {
                return;
            }

            homeTeamName.text = eventObject.details.homeTeam.TeamName.ToUpper();
            awayTeamName.text = eventObject.details.awayTeam.TeamName.ToUpper();

            if (homeScoreText == null || awayScoreText == null) {
                return;
            }

            homeScore = 0;
            awayScore = 0;
            homeScoreText.text = string.Empty;
            awayScoreText.text = string.Empty;
        }
    }
}
