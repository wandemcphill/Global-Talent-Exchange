using FStudio.Events;
using FStudio.GTEX.Core;
using FStudio.Loaders;
using FStudio.UI;
using FStudio.UI.Events;
using UnityEngine;

namespace FStudio {
    public class Boot : MonoBehaviour {
        private async void Start() {
            if (GtexRuntimeBootstrap.TryAutoStart()) {
                return;
            }

            await UILoader.Current.GeneralUILoader.Load();
            await SceneLoader.LoadDefaultScene();
            EventManager.Trigger(new MainMenuEvent());
        }
    }
}
