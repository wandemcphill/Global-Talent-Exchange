using System.Collections;
using UnityEngine;

namespace Gtex.Match3D.Runtime
{
    [DefaultExecutionOrder(-1000)]
    public sealed class AuthoritativeSceneSyncGuard : MonoBehaviour
    {
        private static AuthoritativeSceneSyncGuard _instance;

        private FlutterUnityBridge _bridge;
        private MatchController _controller;
        private bool _pollingDisabled;

        private void Awake()
        {
            if (_instance != null && _instance != this)
            {
                Destroy(gameObject);
                return;
            }

            _instance = this;
            DontDestroyOnLoad(gameObject);
            ResolveReferences();
            StartCoroutine(WatchExternalAuthority());
        }

        private void ResolveReferences()
        {
            if (_bridge == null)
            {
                _bridge = FindObjectOfType<FlutterUnityBridge>();
            }

            if (_controller == null)
            {
                _controller = FindObjectOfType<MatchController>();
            }
        }

        private IEnumerator WatchExternalAuthority()
        {
            WaitForSecondsRealtime interval = new WaitForSecondsRealtime(0.20f);
            while (!_pollingDisabled)
            {
                ResolveReferences();
                if (_bridge != null && _controller != null)
                {
                    string state = _bridge.GetSessionStateJson();
                    if (IsExternalAuthoritativeSession(state))
                    {
                        _controller.SetLiveFeedPlaybackEnabled(false);
                        _pollingDisabled = true;
                    }
                }

                yield return interval;
            }
        }

        private static bool IsExternalAuthoritativeSession(string json)
        {
            if (string.IsNullOrWhiteSpace(json))
            {
                return false;
            }

            return json.Contains("\"status\":\"open\"") ||
                   json.Contains("\"status\":\"implicit\"");
        }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void EnsureGuardExists()
        {
            AuthoritativeSceneSyncGuard existing = FindObjectOfType<AuthoritativeSceneSyncGuard>();
            if (existing != null)
            {
                return;
            }

            GameObject root = GameObject.Find("GTEXRuntimeAuthorityGuard");
            if (root == null)
            {
                root = new GameObject("GTEXRuntimeAuthorityGuard");
            }

            root.AddComponent<AuthoritativeSceneSyncGuard>();
        }
    }
}
