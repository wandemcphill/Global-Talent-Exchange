using System;
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

        private const string ConfigResourcePath = "match-config";
        private MatchAPI _api;
        private Coroutine _pollRoutine;
        private MatchResponse _lastKnownState;
        private int _consecutiveFailures;

        private void Awake()
        {
            ApplyResourceConfig();
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
            if (matchController != null)
            {
                matchController.SetActiveMatch(value);
            }
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

            if (matchController != null && !string.IsNullOrWhiteSpace(matchId))
            {
                matchController.SetActiveMatch(matchId);
            }
        }

        private void ApplyResourceConfig()
        {
            TextAsset configAsset = Resources.Load<TextAsset>(ConfigResourcePath);
            if (configAsset == null || string.IsNullOrWhiteSpace(configAsset.text))
            {
                return;
            }

            MatchLiveBridgeConfig config = new MatchLiveBridgeConfig
            {
                enabled = enabled,
                autoStartOnBoot = startPollingOnStart,
                matchId = matchId,
                environment = EnvironmentToConfigValue(environment),
                localBaseUrl = localBaseUrl,
                productionBaseUrl = productionBaseUrl,
                customBaseUrl = customBaseUrl,
                pollIntervalSeconds = pollIntervalSeconds,
                maxRetryDelaySeconds = maxRetryDelaySeconds,
                timeoutSeconds = timeoutSeconds,
                verboseLogging = verboseLogging,
            };

            try
            {
                JsonUtility.FromJsonOverwrite(configAsset.text, config);
            }
            catch (Exception exception)
            {
                Debug.LogError("MatchLiveBridge failed to parse match-config.json.\n" + exception);
                return;
            }

            enabled = config.enabled;
            startPollingOnStart = config.autoStartOnBoot;
            if (!string.IsNullOrWhiteSpace(config.matchId))
            {
                matchId = config.matchId.Trim();
            }

            environment = ParseEnvironment(config.environment, environment);
            if (!string.IsNullOrWhiteSpace(config.localBaseUrl))
            {
                localBaseUrl = config.localBaseUrl.Trim();
            }

            if (!string.IsNullOrWhiteSpace(config.productionBaseUrl))
            {
                productionBaseUrl = config.productionBaseUrl.Trim();
            }

            if (!string.IsNullOrWhiteSpace(config.customBaseUrl))
            {
                customBaseUrl = config.customBaseUrl.Trim();
            }

            pollIntervalSeconds = Mathf.Max(0.1f, config.pollIntervalSeconds);
            maxRetryDelaySeconds = Mathf.Max(pollIntervalSeconds, config.maxRetryDelaySeconds);
            timeoutSeconds = Mathf.Max(1, config.timeoutSeconds);
            verboseLogging = config.verboseLogging;
        }

        private static MatchApiEnvironment ParseEnvironment(string value, MatchApiEnvironment fallback)
        {
            if (string.IsNullOrWhiteSpace(value))
            {
                return fallback;
            }

            string normalized = value.Trim().ToLowerInvariant();
            switch (normalized)
            {
                case "local":
                    return MatchApiEnvironment.Local;
                case "production":
                    return MatchApiEnvironment.Production;
                case "custom":
                    return MatchApiEnvironment.Custom;
                default:
                    return fallback;
            }
        }

        private static string EnvironmentToConfigValue(MatchApiEnvironment value)
        {
            switch (value)
            {
                case MatchApiEnvironment.Production:
                    return "production";
                case MatchApiEnvironment.Custom:
                    return "custom";
                case MatchApiEnvironment.Local:
                default:
                    return "local";
            }
        }

        [Serializable]
        private sealed class MatchLiveBridgeConfig
        {
            public bool enabled = true;
            public bool autoStartOnBoot = true;
            public string matchId;
            public string environment = "local";
            public string localBaseUrl = "http://127.0.0.1:8000";
            public string productionBaseUrl;
            public string customBaseUrl;
            public float pollIntervalSeconds = 1f;
            public float maxRetryDelaySeconds = 8f;
            public int timeoutSeconds = 5;
            public bool verboseLogging;
        }
    }
}
