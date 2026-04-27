using FStudio.Events;
using FStudio.GTEX;
using FStudio.GTEX.Engine;
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
            GtexMatchController.LiveStateObserved += GtexLiveStateUpdated;
            GtexScoreAuthority.ScoreChanged += GtexScoreChanged;

            if (GtexRuntimeFlags.UsesGtexScoreAuthority) {
                GtexScoreChanged(GtexScoreAuthority.Current);
            }
        }

        private void FirstWhistle(FirstWhistleEvent kickOffEvent) {
            if (GtexRuntimeFlags.UsesGtexScoreAuthority ||
                (MatchEngine.MatchManager.Current != null &&
                 MatchEngine.MatchManager.Current.ExternalPlaybackEnabled)) {
                return;
            }

            if (homeScoreText == null || awayScoreText == null) {
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
            GtexMatchController.LiveStateObserved -= GtexLiveStateUpdated;
            GtexScoreAuthority.ScoreChanged -= GtexScoreChanged;
        }

        private void GoalScored(GoalScoredEvent goalScoredEvent) {
            if (GtexRuntimeFlags.UsesGtexScoreAuthority ||
                (MatchEngine.MatchManager.Current != null &&
                 MatchEngine.MatchManager.Current.ExternalPlaybackEnabled)) {
                return;
            }

            if (homeScoreText == null || awayScoreText == null) {
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
                GtexRuntimeFlags.UsesGtexScoreAuthority ||
                (MatchEngine.MatchManager.Current != null &&
                 MatchEngine.MatchManager.Current.ExternalPlaybackEnabled)) {
                return;
            }

            SetClock(gameTimeUpdate.GameTime);
        }

        private void GtexLiveStateUpdated(GtexLiveStateSignal liveStateSignal) {
            if (GtexRuntimeFlags.UsesGtexScoreAuthority || liveStateSignal.State == null) {
                return;
            }

            homeScore = Mathf.Max(0, liveStateSignal.State.homeScore);
            awayScore = Mathf.Max(0, liveStateSignal.State.awayScore);

            if (homeScoreText != null) {
                homeScoreText.text = homeScore.ToString();
            }

            if (awayScoreText != null) {
                awayScoreText.text = awayScore.ToString();
            }

            SetClock(liveStateSignal.State.clockMinute);
        }

        private void GtexScoreChanged(GtexScoreState score) {
            if (!GtexRuntimeFlags.UsesGtexScoreAuthority || score == null) {
                return;
            }

            ApplyScoreState(score.homeLabel, score.awayLabel, score.homeScore, score.awayScore, score.minute);
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

        private void ApplyScoreState(string homeLabel, string awayLabel, int nextHomeScore, int nextAwayScore, float matchMinute) {
            SetTeamLabel(homeTeamName, homeLabel);
            SetTeamLabel(awayTeamName, awayLabel);

            homeScore = Mathf.Max(0, nextHomeScore);
            awayScore = Mathf.Max(0, nextAwayScore);

            if (homeScoreText != null) {
                homeScoreText.text = homeScore.ToString();
            }

            if (awayScoreText != null) {
                awayScoreText.text = awayScore.ToString();
            }

            SetClock(matchMinute);
        }

        private static void SetTeamLabel(TextMeshProUGUI target, string value) {
            if (target == null || string.IsNullOrWhiteSpace(value)) {
                return;
            }

            target.text = value.Trim().ToUpperInvariant();
        }

        protected override void OnEventCalled(UpcomingMatchEvent eventObject) {
            if (timeCounter != null) {
                timeCounter.text = string.Empty;
            }

            if (eventObject == null) {
                return;
            }

            if (homeTeamName != null) {
                homeTeamName.text = eventObject.details.homeTeam.TeamName.ToUpper();
            }

            if (awayTeamName != null) {
                awayTeamName.text = eventObject.details.awayTeam.TeamName.ToUpper();
            }

            if (homeScoreText == null || awayScoreText == null) {
                return;
            }

            homeScore = 0;
            awayScore = 0;
            homeScoreText.text = string.Empty;
            awayScoreText.text = string.Empty;

            if (GtexRuntimeFlags.UsesGtexScoreAuthority) {
                GtexScoreChanged(GtexScoreAuthority.Current);
            }
        }
    }
}
