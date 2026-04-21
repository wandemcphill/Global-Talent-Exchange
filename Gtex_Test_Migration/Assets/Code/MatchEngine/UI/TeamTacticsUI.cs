using FStudio.Events;
using FStudio.GTEX;
using FStudio.MatchEngine.Events;
using FStudio.UI;
using UnityEngine;
using Shared.Responses;

namespace FStudio.MatchEngine.UI {
    public class TeamTacticsUI : EventPanel<MatchInitializationCompletedEvent> {

        [SerializeField] private TacticPresenter homeTacticPresenter, awayTacticPresenter;

        protected override void OnEnable() {
            base.OnEnable();
            EventManager.Subscribe<FinalWhistleEvent>(FinalWhistle);
            EventManager.Subscribe<TeamChangedTactic>(TeamChangedTactics);
        }

        protected override void OnDisable() {
            base.OnDisable();
            EventManager.UnSubscribe<FinalWhistleEvent>(FinalWhistle);
            EventManager.UnSubscribe<TeamChangedTactic>(TeamChangedTactics);
        }

        private void TeamChangedTactics(TeamChangedTactic teamChangedTactic) {
            if (MatchManager.Current.GameTeam1 == teamChangedTactic.Team) {
                homeTacticPresenter.Set(teamChangedTactic.TacticPreset);
            } else {
                awayTacticPresenter.Set(teamChangedTactic.TacticPreset);
            }
        }

        private void FinalWhistle (FinalWhistleEvent finalWhistle) {
            Disappear();
        }

        private static bool IsExternallyDrivenMatchActive() {
            return Object.FindFirstObjectByType<GtexMatchRuntime>() != null ||
                (MatchManager.Current != null && MatchManager.Current.ExternalPlaybackEnabled);
        }

        protected override void OnEventCalled(MatchInitializationCompletedEvent eventObject) {
            if (IsExternallyDrivenMatchActive()) {
                Disappear();
                return;
            }

            Appear();
        }
    }
}
