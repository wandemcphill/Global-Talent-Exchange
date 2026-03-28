using UnityEngine;

namespace Gtex.Match3D.Runtime
{
    public sealed class FlutterUnityBridge : MonoBehaviour
    {
        [SerializeField] private MatchController matchController;

        private void Awake()
        {
            if (matchController == null)
            {
                matchController = GetComponent<MatchController>();
            }
        }

        public void SetController(MatchController controller)
        {
            matchController = controller;
        }

        public void HandleMessage(string json)
        {
            HandleSceneSync(json);
        }

        public void HandleSceneSync(string json)
        {
            MatchSceneSyncPayload payload = MatchRuntimeJson.DeserializeSceneSync(json);
            if (payload == null || matchController == null)
            {
                return;
            }

            matchController.ApplySceneSync(payload);
        }

        public void HandleMatchEvent(string json)
        {
            MatchEventDto matchEvent = MatchRuntimeJson.DeserializeMatchEvent(json);
            if (matchEvent == null || matchController == null)
            {
                return;
            }

            matchController.HandleEvent(matchEvent);
        }
    }
}
