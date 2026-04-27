
using FStudio.UI.Events;
using FStudio.GTEX;
using FStudio.GTEX.Core;
using FStudio.MatchEngine;
using System.Threading.Tasks;
using UnityEngine;

namespace FStudio.UI {
    public class BigLoadingPanel : EventPanel<BigLoadingEvent> {
        private static bool IsExternallyDrivenMatchActive() {
            return GtexRuntimeFlags.UsesGtexScoreAuthority ||
                GtexRuntimeBootstrap.IsOriginalVisualRuntimeActive() ||
                GtexRuntimeBootstrap.IsLivePlaybackPendingOrActive() ||
                (MatchManager.Current != null && MatchManager.Current.ExternalPlaybackEnabled);
        }

        protected override void Update() {
            base.Update();

            if (IsActive && IsExternallyDrivenMatchActive()) {
                Disappear();
            }
        }

        protected override async void OnEventCalled(BigLoadingEvent eventObject) {
            if (IsExternallyDrivenMatchActive()) {
                Disappear();
                return;
            }

            Debug.Log("Big loading : " + (eventObject != null));
            if (eventObject == null) {
                await Task.Delay(1000);
                Disappear();
            } else {
                Appear();
            }
        }
    }
}
