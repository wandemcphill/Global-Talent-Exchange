using System;
using System.Collections.Generic;
using System.IO;
using System.Globalization;
using FStudio.Data;
using FStudio.GTEX.Core;
using UnityEngine;

namespace FStudio.GTEX
{
    [Serializable]
    public sealed class GtexMatchConfig
    {
        private const string RuntimeModeEnvVar = "GTEX_RUNTIME_MODE";
        private const string MatchIdEnvVar = "GTEX_MATCH_ID";
        private const string EnvironmentEnvVar = "GTEX_ENVIRONMENT";
        private const string BaseUrlEnvVar = "GTEX_BASE_URL";
        private const string LiveAccessTokenEnvVar = "GTEX_LIVE_ACCESS_TOKEN";
        private const string LiveRefreshTokenEnvVar = "GTEX_LIVE_REFRESH_TOKEN";

        public bool enabled = true;
        public bool autoStartOnBoot = true;
        public string runtimeMode = "live";
        public string matchId = string.Empty;
        public string environment = "local";
        public string localBaseUrl = "http://127.0.0.1:8000";
        public string productionBaseUrl = "https://api.gtex.example";
        public string customBaseUrl = string.Empty;
        public string liveAccessToken = string.Empty;
        public string liveRefreshToken = string.Empty;
        public float pollIntervalSeconds = 1f;
        public float maxRetryDelaySeconds = 12f;
        public int timeoutSeconds = 20;
        public string homeTemplateTeam = "City";
        public string awayTemplateTeam = "Royal";
        public string homeTeamName = string.Empty;
        public string awayTeamName = string.Empty;
        public string dayTime = "Night";
        public bool enableStadiumUpgrade = true;
        public bool showCrowd = true;
        public string stadiumVariant = "broadcast";
        public bool verboseLogging;
        public float stalePredictionSeconds = 1.25f;
        public float teleportDistance = 6f;
        public float simulationTargetDurationMinutes = 15f;
        public float simulationEventCheckWindowMinutes = 1f;
        public float simulationBaseEventChancePerWindow = 0.42f;
        public int simulationRandomSeed = 1337;

        public bool CanAutoStartLivePlayback =>
            enabled &&
            autoStartOnBoot &&
            !string.IsNullOrWhiteSpace(matchId) &&
            !string.IsNullOrWhiteSpace(ResolveBaseUrl()) &&
            HasLiveAuthBootstrap;

        public bool CanAutoStartSelectedRuntime
        {
            get
            {
                if (!enabled || !autoStartOnBoot)
                {
                    return false;
                }

                return ResolveRuntimeMode() == GtexRuntimeMode.LivePlayback
                    ? CanAutoStartLivePlayback
                    : true;
            }
        }

        public bool CanAutoStart => CanAutoStartSelectedRuntime;

        public bool HasLiveAuthBootstrap =>
            !string.IsNullOrWhiteSpace(liveAccessToken) ||
            !string.IsNullOrWhiteSpace(liveRefreshToken);

        public void ApplyRuntimeOverrides()
        {
            var appliedOverrides = new List<string>();

            ApplyStringOverride(ref runtimeMode, ResolveRuntimeOverride("runtime-mode", RuntimeModeEnvVar), "runtimeMode", appliedOverrides);
            ApplyStringOverride(ref matchId, ResolveRuntimeOverride("match-id", MatchIdEnvVar), "matchId", appliedOverrides);
            ApplyStringOverride(ref environment, ResolveRuntimeOverride("environment", EnvironmentEnvVar), "environment", appliedOverrides);

            var baseUrlOverride = ResolveRuntimeOverride("base-url", BaseUrlEnvVar);
            if (!string.IsNullOrWhiteSpace(baseUrlOverride))
            {
                customBaseUrl = baseUrlOverride.Trim();
                environment = "custom";
                appliedOverrides.Add("baseUrl");
            }

            if (TryResolveCredentialOverride("live-access-token", LiveAccessTokenEnvVar, out var accessTokenOverride))
            {
                liveAccessToken = accessTokenOverride;
                appliedOverrides.Add("liveAccessToken");
            }

            if (TryResolveCredentialOverride("live-refresh-token", LiveRefreshTokenEnvVar, out var refreshTokenOverride))
            {
                liveRefreshToken = refreshTokenOverride;
                appliedOverrides.Add("liveRefreshToken");
            }

            if (appliedOverrides.Count > 0)
            {
                Debug.Log("[GTEX] Applied runtime config overrides: " + string.Join(", ", appliedOverrides));
            }
        }

        public void EnsureDefaults()
        {
            var normalizedRuntimeMode = NormalizeRuntimeModeToken(runtimeMode);
            if (!string.Equals(runtimeMode, normalizedRuntimeMode, StringComparison.OrdinalIgnoreCase))
            {
                Debug.LogWarning("[GTEX] runtimeMode was invalid. Defaulting to '" + normalizedRuntimeMode + "'.");
            }

            runtimeMode = normalizedRuntimeMode;
            var runtimeModeValue = ResolveRuntimeMode();

            if (runtimeModeValue == GtexRuntimeMode.LivePlayback && string.IsNullOrWhiteSpace(matchId))
            {
#if UNITY_EDITOR
                Debug.LogWarning("[GTEX] matchId is empty for live mode. Waiting for bootstrap or runtime override.");
#else
                Debug.LogError("[GTEX] matchId is required for live mode.");
#endif
            }

            if (string.IsNullOrWhiteSpace(environment))
            {
                environment = "local";
                Debug.LogWarning("[GTEX] environment missing. Defaulting to LOCAL.");
            }

            if (string.IsNullOrWhiteSpace(ResolveBaseUrl()))
            {
                if (runtimeModeValue == GtexRuntimeMode.LivePlayback &&
                    !string.Equals((environment ?? string.Empty).Trim(), "local", StringComparison.OrdinalIgnoreCase))
                {
                    Debug.LogError("[GTEX] Base URL is missing for live environment '" + environment + "'.");
                }
                else
                {
                    localBaseUrl = "http://127.0.0.1:8000";
                    Debug.LogWarning("[GTEX] Base URL missing. Defaulting to http://127.0.0.1:8000");
                }
            }

            if (runtimeModeValue == GtexRuntimeMode.LivePlayback && !HasLiveAuthBootstrap)
            {
                Debug.LogWarning("[GTEX] Live playback auth bootstrap is missing.");
            }

            if (maxRetryDelaySeconds < 1f)
            {
                maxRetryDelaySeconds = 12f;
                Debug.LogWarning("[GTEX] maxRetryDelaySeconds was invalid. Defaulting to 12.");
            }

            if (timeoutSeconds < 5)
            {
                timeoutSeconds = 20;
                Debug.LogWarning("[GTEX] timeoutSeconds was too low. Defaulting to 20.");
            }

            if (simulationTargetDurationMinutes <= 0f)
            {
                simulationTargetDurationMinutes = 15f;
                Debug.LogWarning("[GTEX] simulationTargetDurationMinutes was invalid. Defaulting to 15.");
            }

            if (simulationEventCheckWindowMinutes <= 0f)
            {
                simulationEventCheckWindowMinutes = 1f;
                Debug.LogWarning("[GTEX] simulationEventCheckWindowMinutes was invalid. Defaulting to 1.");
            }

            if (simulationBaseEventChancePerWindow < 0f || simulationBaseEventChancePerWindow > 1f)
            {
                simulationBaseEventChancePerWindow = Mathf.Clamp01(simulationBaseEventChancePerWindow);
                Debug.LogWarning("[GTEX] simulationBaseEventChancePerWindow was out of range. Clamping into [0,1].");
            }

            if (simulationRandomSeed == 0)
            {
                simulationRandomSeed = 1337;
                Debug.LogWarning("[GTEX] simulationRandomSeed was zero. Defaulting to 1337.");
            }
        }

        public string ResolveBaseUrl()
        {
            switch ((environment ?? string.Empty).Trim().ToLowerInvariant())
            {
                case "production":
                    return productionBaseUrl;
                case "custom":
                    return customBaseUrl;
                case "local":
                default:
                    return localBaseUrl;
            }
        }

        public GtexRuntimeMode ResolveRuntimeMode()
        {
            return NormalizeRuntimeModeToken(runtimeMode) == "simulation"
                ? GtexRuntimeMode.LocalSimulation
                : GtexRuntimeMode.LivePlayback;
        }

        public DayTimes ResolveDayTime()
        {
            if (Enum.TryParse(dayTime, true, out DayTimes parsed))
            {
                return parsed;
            }

            return DayTimes.Night;
        }

        private static string NormalizeRuntimeModeToken(string value)
        {
            switch ((value ?? string.Empty).Trim().ToLowerInvariant())
            {
                case "simulation":
                case "sim":
                case "local-simulation":
                case "localsimulation":
                    return "simulation";
                case "live":
                case "live-playback":
                case "liveplayback":
                default:
                    return "live";
            }
        }

        public void ApplyBootstrapPayload(GtexLiveBootstrapPayload payload, string sourcePath)
        {
            if (payload == null)
            {
                return;
            }

            var appliedOverrides = new List<string>();

            ApplyStringOverride(ref runtimeMode, payload.runtimeMode, "runtimeMode", appliedOverrides);
            ApplyStringOverride(ref matchId, payload.matchId, "matchId", appliedOverrides);
            ApplyStringOverride(ref environment, payload.environment, "environment", appliedOverrides);

            if (!string.IsNullOrWhiteSpace(payload.baseUrl))
            {
                customBaseUrl = payload.baseUrl.Trim();
                environment = "custom";
                appliedOverrides.Add("baseUrl");
            }

            if (payload.liveAccessToken != null)
            {
                liveAccessToken = payload.liveAccessToken.Trim();
                appliedOverrides.Add("liveAccessToken");
            }

            if (payload.liveRefreshToken != null)
            {
                liveRefreshToken = payload.liveRefreshToken.Trim();
                appliedOverrides.Add("liveRefreshToken");
            }

            if (appliedOverrides.Count > 0)
            {
                Debug.Log("[GTEX] Applied bootstrap payload from '" + sourcePath + "': " + string.Join(", ", appliedOverrides));
            }
        }

        private static void ApplyStringOverride(ref string target, string candidate, string label, List<string> appliedOverrides)
        {
            if (string.IsNullOrWhiteSpace(candidate))
            {
                return;
            }

            target = candidate.Trim();
            appliedOverrides.Add(label);
        }

        private static bool TryResolveCredentialOverride(string argName, string envVarName, out string value)
        {
            value = ResolveRuntimeOverride(argName, envVarName);
            if (value == null)
            {
                value = string.Empty;
                return false;
            }

            value = value.Trim();
            return true;
        }

        private static string ResolveRuntimeOverride(string argName, string envVarName)
        {
            var commandLineValue = ResolveCommandLineOverride(argName);
            if (commandLineValue != null)
            {
                return commandLineValue;
            }

            try
            {
                return Environment.GetEnvironmentVariable(envVarName);
            }
            catch (Exception exception)
            {
                Debug.LogWarning("[GTEX] Failed to read environment override '" + envVarName + "'.\n" + exception);
                return null;
            }
        }

        private static string ResolveCommandLineOverride(string argName)
        {
            try
            {
                var args = Environment.GetCommandLineArgs();
                var flag = "--gtex-" + argName;
                for (var index = 0; index < args.Length; index += 1)
                {
                    var candidate = args[index];
                    if (string.IsNullOrWhiteSpace(candidate))
                    {
                        continue;
                    }

                    if (string.Equals(candidate, flag, StringComparison.OrdinalIgnoreCase))
                    {
                        if (index + 1 < args.Length)
                        {
                            return args[index + 1];
                        }

                        return string.Empty;
                    }

                    if (candidate.StartsWith(flag + "=", StringComparison.OrdinalIgnoreCase))
                    {
                        return candidate.Substring(flag.Length + 1);
                    }
                }
            }
            catch (Exception exception)
            {
                Debug.LogWarning("[GTEX] Failed to inspect command line args for '" + argName + "'.\n" + exception);
            }

            return null;
        }
    }

    [Serializable]
    public sealed class GtexLiveBootstrapPayload
    {
        public string profile = string.Empty;
        public string runtimeMode = string.Empty;
        public string matchId = string.Empty;
        public string environment = string.Empty;
        public string baseUrl = string.Empty;
        public string liveAccessToken;
        public string liveRefreshToken;
        public string issuedAtUtc = string.Empty;
        public int bootstrapTtlSeconds;
        public bool consumeOnLoad;
    }

    public static class GtexMatchConfigLoader
    {
        private const string ResourcePath = "GTEX/match-config";
        private const string BootstrapPathEnvVar = "GTEX_BOOTSTRAP_PATH";

        private enum BootstrapLoadOutcome
        {
            NotChecked,
            FileMissing,
            EmptyFile,
            InvalidJson,
            Expired,
            Loaded,
            LoadedLegacy,
            FailedToRead
        }

        private sealed class BootstrapLoadStatus
        {
            public BootstrapLoadOutcome Outcome = BootstrapLoadOutcome.NotChecked;
            public string Path = string.Empty;
            public string Profile = string.Empty;
            public string Message = string.Empty;
        }

        public static GtexMatchConfig Load()
        {
            GtexLiveStartupStatus.Clear();
            var asset = Resources.Load<TextAsset>(ResourcePath);

            if (asset == null)
            {
                Debug.LogError("[GTEX] match-config.json NOT FOUND at Resources/GTEX/");
                GtexLiveStartupStatus.ReportError(
                    "match_config_missing",
                    "Live config missing",
                    "match-config.json could not be found under Resources/GTEX.",
                    "Restore Assets/Resources/GTEX/match-config.json.");
                return null;
            }

            if (string.IsNullOrWhiteSpace(asset.text))
            {
                Debug.LogError("[GTEX] match-config.json is EMPTY");
                GtexLiveStartupStatus.ReportError(
                    "match_config_empty",
                    "Live config empty",
                    "match-config.json is present but empty.",
                    "Restore a valid JSON config before running live mode.");
                return null;
            }

            try
            {
                var parsed = JsonUtility.FromJson<GtexMatchConfig>(asset.text);

                if (parsed == null)
                {
                    Debug.LogError("[GTEX] Failed to parse config.");
                    GtexLiveStartupStatus.ReportError(
                        "match_config_invalid",
                        "Live config invalid",
                        "match-config.json could not be parsed.",
                        "Fix the JSON syntax in Assets/Resources/GTEX/match-config.json.");
                    return null;
                }

                var bootstrapStatus = TryApplyBootstrapPayload(parsed);
                parsed.ApplyRuntimeOverrides();
                parsed.EnsureDefaults();
                UpdateLiveStartupStatus(parsed, bootstrapStatus);

                Debug.Log("[GTEX] Config loaded -> MatchId: " + parsed.matchId);
                Debug.Log("[GTEX] RuntimeMode -> " + parsed.ResolveRuntimeMode());
                Debug.Log("[GTEX] BaseUrl -> " + parsed.ResolveBaseUrl());
                Debug.Log("[GTEX] CanAutoStart -> " + parsed.CanAutoStart);
                Debug.Log("[GTEX] LiveAccessTokenPresent -> " + (!string.IsNullOrWhiteSpace(parsed.liveAccessToken)));
                Debug.Log("[GTEX] LiveRefreshTokenPresent -> " + (!string.IsNullOrWhiteSpace(parsed.liveRefreshToken)));

                return parsed;
            }
            catch (Exception exception)
            {
                Debug.LogError("[GTEX] Failed to parse match-config.json.\n" + exception);
                GtexLiveStartupStatus.ReportError(
                    "match_config_exception",
                    "Live config exception",
                    "match-config.json threw while loading.",
                    "Check the Unity console for the parsing exception.");
                return null;
            }
        }

        private static BootstrapLoadStatus TryApplyBootstrapPayload(GtexMatchConfig config)
        {
            var status = new BootstrapLoadStatus();
            var bootstrapPath = ResolveBootstrapPath();
            if (string.IsNullOrWhiteSpace(bootstrapPath))
            {
                return status;
            }

            status.Path = bootstrapPath;

            if (!File.Exists(bootstrapPath))
            {
                status.Outcome = BootstrapLoadOutcome.FileMissing;
                status.Message = "No bootstrap file found.";
                return status;
            }

            try
            {
                var json = File.ReadAllText(bootstrapPath);
                if (string.IsNullOrWhiteSpace(json))
                {
                    Debug.LogWarning("[GTEX] Bootstrap file is empty: " + bootstrapPath);
                    status.Outcome = BootstrapLoadOutcome.EmptyFile;
                    status.Message = "Bootstrap file is empty.";
                    return status;
                }

                var payload = JsonUtility.FromJson<GtexLiveBootstrapPayload>(json);
                if (payload == null)
                {
                    Debug.LogWarning("[GTEX] Bootstrap file could not be parsed: " + bootstrapPath);
                    status.Outcome = BootstrapLoadOutcome.InvalidJson;
                    status.Message = "Bootstrap file could not be parsed.";
                    return status;
                }

                var isLegacyPayload = IsLegacyBootstrapPayload(payload);
                status.Profile = string.IsNullOrWhiteSpace(payload.profile)
                    ? string.Empty
                    : payload.profile.Trim().ToLowerInvariant();
                if (IsBootstrapPayloadExpired(payload, bootstrapPath))
                {
                    DeleteBootstrapFile(bootstrapPath, "expired");
                    status.Outcome = BootstrapLoadOutcome.Expired;
                    status.Message = "Bootstrap file expired.";
                    return status;
                }

                config.ApplyBootstrapPayload(payload, bootstrapPath);
                status.Outcome = isLegacyPayload
                    ? BootstrapLoadOutcome.LoadedLegacy
                    : BootstrapLoadOutcome.Loaded;

                if (payload.consumeOnLoad)
                {
                    DeleteBootstrapFile(bootstrapPath, "consumed");
                }

                return status;
            }
            catch (Exception exception)
            {
                Debug.LogWarning("[GTEX] Failed to load bootstrap file '" + bootstrapPath + "'.\n" + exception);
                status.Outcome = BootstrapLoadOutcome.FailedToRead;
                status.Message = exception.Message;
                return status;
            }
        }

        private static string ResolveBootstrapPath()
        {
            var explicitPath = ResolveRuntimeOverride("bootstrap-path", BootstrapPathEnvVar);
            if (!string.IsNullOrWhiteSpace(explicitPath))
            {
                return explicitPath.Trim();
            }

            try
            {
#if UNITY_ANDROID && !UNITY_EDITOR
                var persistentDataPath = Application.persistentDataPath;
                if (!string.IsNullOrWhiteSpace(persistentDataPath))
                {
                    return Path.Combine(persistentDataPath, "tmp", "gtex-live-bootstrap.json");
                }
#endif
                var dataPath = Application.dataPath;
                if (string.IsNullOrWhiteSpace(dataPath))
                {
                    return null;
                }

                var projectRoot = Directory.GetParent(dataPath);
                if (projectRoot == null)
                {
                    return null;
                }

                return Path.Combine(projectRoot.FullName, "tmp", "gtex-live-bootstrap.json");
            }
            catch (Exception exception)
            {
                Debug.LogWarning("[GTEX] Failed to resolve the default bootstrap path.\n" + exception);
                return null;
            }
        }

        private static bool IsBootstrapPayloadExpired(GtexLiveBootstrapPayload payload, string sourcePath)
        {
            if (payload == null)
            {
                return true;
            }

            if (string.IsNullOrWhiteSpace(payload.issuedAtUtc) || payload.bootstrapTtlSeconds <= 0)
            {
                if (!string.IsNullOrWhiteSpace(payload.liveAccessToken) || !string.IsNullOrWhiteSpace(payload.liveRefreshToken))
                {
                    Debug.LogWarning("[GTEX] Bootstrap file is missing lifecycle metadata and will be treated as a legacy payload: " + sourcePath);
                }

                return false;
            }

            if (!DateTime.TryParse(
                    payload.issuedAtUtc,
                    CultureInfo.InvariantCulture,
                    DateTimeStyles.AdjustToUniversal | DateTimeStyles.AssumeUniversal,
                    out var issuedAtUtc))
            {
                Debug.LogWarning("[GTEX] Bootstrap file has an invalid issuedAtUtc value and will be ignored: " + sourcePath);
                return true;
            }

            var expiresAtUtc = issuedAtUtc.AddSeconds(Math.Max(1, payload.bootstrapTtlSeconds));
            if (DateTime.UtcNow <= expiresAtUtc)
            {
                return false;
            }

            Debug.LogWarning(
                "[GTEX] Bootstrap file expired at " +
                expiresAtUtc.ToString("O", CultureInfo.InvariantCulture) +
                " and will be ignored: " +
                sourcePath);
            return true;
        }

        private static bool IsLegacyBootstrapPayload(GtexLiveBootstrapPayload payload)
        {
            return payload != null &&
                   (string.IsNullOrWhiteSpace(payload.issuedAtUtc) || payload.bootstrapTtlSeconds <= 0);
        }

        private static void UpdateLiveStartupStatus(GtexMatchConfig config, BootstrapLoadStatus bootstrapStatus)
        {
            if (config == null || config.ResolveRuntimeMode() != GtexRuntimeMode.LivePlayback)
            {
                GtexLiveStartupStatus.Clear();
                return;
            }

            if (!config.enabled || !config.autoStartOnBoot)
            {
                GtexLiveStartupStatus.Clear();
                return;
            }

            if (!config.HasLiveAuthBootstrap)
            {
                var actionHint = "Run `python tools/provision_gtex_live_match.py` to create a fresh live bootstrap.";
                switch (bootstrapStatus != null ? bootstrapStatus.Outcome : BootstrapLoadOutcome.NotChecked)
                {
                    case BootstrapLoadOutcome.FileMissing:
                        GtexLiveStartupStatus.ReportError(
                            "bootstrap_missing",
                            "Live bootstrap missing",
                            "No live bootstrap file was found for this run.",
                            actionHint,
                            bootstrapStatus.Path);
                        return;
                    case BootstrapLoadOutcome.EmptyFile:
                        GtexLiveStartupStatus.ReportError(
                            "bootstrap_empty",
                            "Live bootstrap empty",
                            "The live bootstrap file is present but empty.",
                            actionHint,
                            bootstrapStatus.Path);
                        return;
                    case BootstrapLoadOutcome.InvalidJson:
                        GtexLiveStartupStatus.ReportError(
                            "bootstrap_invalid",
                            "Live bootstrap invalid",
                            "The live bootstrap file could not be parsed.",
                            actionHint,
                            bootstrapStatus.Path);
                        return;
                    case BootstrapLoadOutcome.Expired:
                        GtexLiveStartupStatus.ReportError(
                            "bootstrap_expired",
                            "Live bootstrap expired",
                            "The live bootstrap file expired before Unity could use it.",
                            actionHint,
                            bootstrapStatus.Path);
                        return;
                    case BootstrapLoadOutcome.FailedToRead:
                        GtexLiveStartupStatus.ReportError(
                            "bootstrap_read_failed",
                            "Live bootstrap unreadable",
                            "Unity could not read the live bootstrap file.",
                            actionHint,
                            bootstrapStatus.Path);
                        return;
                    default:
                        GtexLiveStartupStatus.ReportError(
                            "live_auth_missing",
                            "Live auth missing",
                            "Live mode is selected but no access or refresh token is available.",
                            "Provide a runtime token override or run `python tools/provision_gtex_live_match.py`.");
                        return;
                }
            }

            if (string.IsNullOrWhiteSpace(config.matchId))
            {
                GtexLiveStartupStatus.ReportError(
                    "match_id_missing",
                    "Live match id missing",
                    "Live mode has authentication but no match id to connect to.",
                    "Pass `--gtex-match-id` or regenerate the live bootstrap.");
                return;
            }

            if (GtexConfig.IsProd)
            {
                var resolvedBaseUrl = config.ResolveBaseUrl();
                if (IsLoopbackOrLocalEndpoint(resolvedBaseUrl))
                {
                    GtexLiveStartupStatus.ReportError(
                        "production_local_endpoint",
                        "Production player pointed at local backend",
                        "This live runtime is targeting a loopback or local backend endpoint.",
                        "Provision a staging/production bootstrap or override the base URL before shipping.",
                        bootstrapStatus != null ? bootstrapStatus.Path : string.Empty);
                    return;
                }

                if (bootstrapStatus != null &&
                    string.Equals(bootstrapStatus.Profile, "local", StringComparison.OrdinalIgnoreCase))
                {
                    GtexLiveStartupStatus.ReportError(
                        "production_local_profile",
                        "Production player loaded local bootstrap",
                        "A local-profile live bootstrap was loaded into a production GTEX build.",
                        "Regenerate the bootstrap with `--profile staging` or `--profile production`.",
                        bootstrapStatus.Path);
                    return;
                }
            }

            if (bootstrapStatus != null && bootstrapStatus.Outcome == BootstrapLoadOutcome.LoadedLegacy)
            {
                GtexLiveStartupStatus.ReportWarning(
                    "bootstrap_legacy",
                    "Legacy bootstrap loaded",
                    "The live bootstrap was loaded without lifecycle metadata.",
                    "Regenerate it with `python tools/provision_gtex_live_match.py`.",
                    bootstrapStatus.Path);
                return;
            }

            GtexLiveStartupStatus.Clear();
        }

        private static bool IsLoopbackOrLocalEndpoint(string baseUrl)
        {
            if (string.IsNullOrWhiteSpace(baseUrl))
            {
                return false;
            }

            if (!Uri.TryCreate(baseUrl, UriKind.Absolute, out var uri))
            {
                return false;
            }

            var host = (uri.Host ?? string.Empty).Trim().ToLowerInvariant();
            return host == "localhost" ||
                   host == "127.0.0.1" ||
                   host == "::1" ||
                   host.EndsWith(".local", StringComparison.Ordinal);
        }

        private static void DeleteBootstrapFile(string bootstrapPath, string reason)
        {
            try
            {
                if (!File.Exists(bootstrapPath))
                {
                    return;
                }

                File.Delete(bootstrapPath);
                Debug.Log("[GTEX] Deleted bootstrap file after it was " + reason + ": " + bootstrapPath);
            }
            catch (Exception exception)
            {
                Debug.LogWarning("[GTEX] Failed to delete bootstrap file '" + bootstrapPath + "' after it was " + reason + ".\n" + exception);
            }
        }

        private static string ResolveRuntimeOverride(string argName, string envVarName)
        {
            var commandLineValue = ResolveCommandLineOverride(argName);
            if (commandLineValue != null)
            {
                return commandLineValue;
            }

            try
            {
                return Environment.GetEnvironmentVariable(envVarName);
            }
            catch (Exception exception)
            {
                Debug.LogWarning("[GTEX] Failed to read environment override '" + envVarName + "'.\n" + exception);
                return null;
            }
        }

        private static string ResolveCommandLineOverride(string argName)
        {
            try
            {
                var args = Environment.GetCommandLineArgs();
                var flag = "--gtex-" + argName;
                for (var index = 0; index < args.Length; index += 1)
                {
                    var candidate = args[index];
                    if (string.IsNullOrWhiteSpace(candidate))
                    {
                        continue;
                    }

                    if (string.Equals(candidate, flag, StringComparison.OrdinalIgnoreCase))
                    {
                        if (index + 1 < args.Length)
                        {
                            return args[index + 1];
                        }

                        return string.Empty;
                    }

                    if (candidate.StartsWith(flag + "=", StringComparison.OrdinalIgnoreCase))
                    {
                        return candidate.Substring(flag.Length + 1);
                    }
                }
            }
            catch (Exception exception)
            {
                Debug.LogWarning("[GTEX] Failed to inspect command line args for '" + argName + "'.\n" + exception);
            }

            return null;
        }
    }
}
