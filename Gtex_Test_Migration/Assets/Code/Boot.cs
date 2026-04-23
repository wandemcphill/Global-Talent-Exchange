using FStudio.Events;
using FStudio.GTEX.Core;
using FStudio.GTEX;
using FStudio.Loaders;
using FStudio.UI;
using FStudio.UI.Events;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace FStudio {
    public class Boot : MonoBehaviour {
        private async void Start() {
            var config = GtexMatchConfigLoader.Load();
            if (config != null) {
                Debug.Log(
                    "[GTEX] Boot startup scene '" +
                    SceneManager.GetActiveScene().name +
                    "' selected runtime -> " +
                    config.ResolveRuntimeMode() +
                    " (raw='" +
                    config.runtimeMode +
                    "', matchId='" +
                    config.matchId +
                    "', baseUrl='" +
                    config.ResolveBaseUrl() +
                    "', localSim3DPlaybackRequested=" +
                    config.use3DPlaybackForLocalSimulation +
                    ").");
            }

            if ((config != null ? GtexRuntimeBootstrap.TryAutoStart(config) : GtexRuntimeBootstrap.TryAutoStart())) {
                return;
            }

            await UILoader.Current.GeneralUILoader.Load();
            await SceneLoader.LoadDefaultScene();
            EventManager.Trigger(new MainMenuEvent());
        }
    }
}
