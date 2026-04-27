using FStudio.Events;
using FStudio.GTEX;
using FStudio.MatchEngine.Events;
using UnityEngine;

namespace FStudio.MatchEngine {
    public class MatchPause {
        public static bool IsPaused { private set; get; }

        private static bool CanOpenPauseMenu()
        {
            if (GtexRuntimeFlags.IsUnattendedPlayback)
            {
                return false;
            }

            if (GtexRuntimeFlags.IsLocalSimulation)
            {
                return false;
            }

            return true;
        }

        public static void Pause() {
            if (!CanOpenPauseMenu()) {
                Debug.Log("[GTEX UI] Escape ignored during unattended local simulation.");
                return;
            }

            IsPaused = !IsPaused;

            if (!IsPaused) {
                Time.timeScale = 1.5f;
                EventManager.Trigger<MatchPauseEvent> (null);
            } else {
                EventManager.Trigger(new MatchPauseEvent());
                Time.timeScale = 0;
            }
        }
    }
}
