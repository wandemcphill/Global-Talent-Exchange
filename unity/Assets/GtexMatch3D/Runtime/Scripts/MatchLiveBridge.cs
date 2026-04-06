using System.Collections;
using UnityEngine;

namespace Gtex.Match3D.Runtime
{
    public sealed class MatchLiveBridge : MonoBehaviour
    {
        private enum MatchApiEnvironment
        {
            Local = 0,
            Production = 1,
            Custom = 2,
        }

        [SerializeField] private MatchController matchController;
        [SerializeField] private FlutterUnityBridge flutterUnityBridge;
        [SerializeField] private string matchId;
        [SerializeField] private bool startPollingOnStart = true;
        [SerializeField] private MatchApiEnvironment environment = MatchApiEnvironment.Local;
        [SerializeField] private string localBaseUrl = "http://127.0.0.1:8000";
        [SerializeField] private string productionBaseUrl = "https://api.gtex.example";
        [SerializeField] private string customBaseUrl;
        [SerializeField] private float pollIntervalSeconds = 1f;
        [SerializeField] private float maxRetryDelaySeconds = 8f;
        [SerializeField] private int timeoutSeconds = 5;
        [SerializeField] private bool verboseLogging;

        private MatchAPI _api;
        private Coroutine _pollRoutine;
        private MatchResponse _lastKnownState;
        private int _consecutiveFailures;

        private void Awake()
        {
            ResolveDependencies();
        }

        private void Start()
        {
            if (startPollingOnStart)
            {
                StartPolling();
            }
        }

        private void OnDisable()
        {
            StopPolling();
        }

        public void Configure(MatchController controller, FlutterUnityBridge bridge)
        {
            matchController = controller;
            flutterUnityBridge = bridge;
            ResolveDependencies();
        }

        public void SetMatchId(string value)
        {
            matchId = value;
        }

        public void StartPolling()
        {
            ResolveDependencies();
            if (_pollRoutine != null)
            {
                return;
            }

            if (string.IsNullOrWhiteSpace(matchId))
            {
                Debug.LogWarning("MatchLiveBridge cannot start without a match ID.");
                return;
            }

            if (matchController == null && flutterUnityBridge == null)
            {
                Debug.LogWarning("MatchLiveBridge cannot start without a MatchController or FlutterUnityBridge.");
                return;
            }

            EnsureApi();
            _pollRoutine = StartCoroutine(PollLoop());
        }

        public void StopPolling()
        {
            if (_pollRoutine == null)
            {
                return;
            }

            StopCoroutine(_pollRoutine);
            _pollRoutine = null;
        }

        private IEnumerator PollLoop()
        {
            while (true)
            {
                EnsureApi();

                MatchResponse response = null;
                string errorMessage = null;
                long statusCode = 0L;

                yield return _api.GetLiveMatch(
                    matchId,
                    result => response = result,
                    (message, code) =>
                    {
                        errorMessage = message;
                        statusCode = code;
                    });

                if (response != null)
                {
                    _consecutiveFailures = 0;
                    _lastKnownState = response;
                    ApplyResponse(response);
                    yield return new WaitForSecondsRealtime(Mathf.Max(0.1f, pollIntervalSeconds));
                    continue;
                }

                _consecutiveFailures += 1;
                if (_lastKnownState != null)
                {
                    Debug.LogWarning(
                        "MatchLiveBridge request failed; keeping last known state. " +
                        errorMessage);
                }
                else
                {
                    Debug.LogWarning(
                        "MatchLiveBridge request failed with no cached state. " +
                        errorMessage +
                        (statusCode > 0 ? " (" + statusCode + ")" : string.Empty));
                }

                yield return new WaitForSecondsRealtime(ResolveRetryDelay());
            }
        }

        private void ApplyResponse(MatchResponse response)
        {
            MatchSceneSyncPayload payload = MatchLiveMapper.ToSceneSync(response);
            if (payload == null)
            {
                Debug.LogWarning("MatchLiveBridge could not map the live response to a scene sync payload.");
                return;
            }

            ResolveDependencies();

            if (flutterUnityBridge != null)
            {
                flutterUnityBridge.HandleSceneSyncWithAck(MatchRuntimeJson.SerializeSceneSync(payload));
            }
            else if (matchController != null)
            {
                matchController.ApplySceneSync(payload);
            }

            if (verboseLogging)
            {
                Debug.Log(
                    "Applied live match frame " +
                    payload.frameId +
                    " at " +
                    payload.clockMinute.ToString("0.00") +
                    " minute(s).");
            }
        }

        private void EnsureApi()
        {
            if (_api == null)
            {
                _api = new MatchAPI(ResolveBaseUrl, timeoutSeconds);
            }
        }

        private string ResolveBaseUrl()
        {
            switch (environment)
            {
                case MatchApiEnvironment.Production:
                    return productionBaseUrl;
                case MatchApiEnvironment.Custom:
                    return customBaseUrl;
                case MatchApiEnvironment.Local:
                default:
                    return localBaseUrl;
            }
        }

        private float ResolveRetryDelay()
        {
            if (_consecutiveFailures <= 0)
            {
                return Mathf.Max(0.1f, pollIntervalSeconds);
            }

            float exponentialDelay = pollIntervalSeconds * Mathf.Pow(2f, Mathf.Min(4, _consecutiveFailures - 1));
            return Mathf.Clamp(
                exponentialDelay,
                pollIntervalSeconds,
                Mathf.Max(pollIntervalSeconds, maxRetryDelaySeconds));
        }

        private void ResolveDependencies()
        {
            if (matchController == null)
            {
                matchController = GetComponentInChildren<MatchController>(true);
            }

            if (flutterUnityBridge == null)
            {
                flutterUnityBridge = GetComponentInChildren<FlutterUnityBridge>(true);
            }

            if (matchController == null && flutterUnityBridge != null)
            {
                matchController = flutterUnityBridge.GetComponent<MatchController>();
            }
        }
    }
}
