using System;
using System.Collections;
using System.Collections.Generic;
using FStudio.GTEX.Core;
using FStudio.GTEX.Engine;
using UnityEngine;
using UnityEngine.Networking;
using UnityEngine.UI;

namespace FStudio.GTEX.Illusion
{
    public sealed class GtexIllusionRuntimeHost : MonoBehaviour
    {
        private const float PitchLength = 105f;
        private const float PitchWidth = 68f;
        private const float PlayerY = 0.95f;
        private const float BallY = 0.24f;
        private const string DefaultTimelineResourcePath = "GTEX/Illusion/illusion-sample-match";
        private static readonly string[] FreeCharacterResourceNames =
        {
            "GTEX/FreeAssets/Crowd/Characters/character-a",
            "GTEX/FreeAssets/Crowd/Characters/character-b",
            "GTEX/FreeAssets/Crowd/Characters/character-c",
            "GTEX/FreeAssets/Crowd/Characters/character-d",
            "GTEX/FreeAssets/Crowd/Characters/character-e",
            "GTEX/FreeAssets/Crowd/Characters/character-f",
            "GTEX/FreeAssets/Crowd/Characters/character-g",
            "GTEX/FreeAssets/Crowd/Characters/character-h",
            "GTEX/FreeAssets/Crowd/Characters/character-i",
            "GTEX/FreeAssets/Crowd/Characters/character-j",
            "GTEX/FreeAssets/Crowd/Characters/character-k",
            "GTEX/FreeAssets/Crowd/Characters/character-l",
            "GTEX/FreeAssets/Crowd/Characters/character-m",
            "GTEX/FreeAssets/Crowd/Characters/character-n",
            "GTEX/FreeAssets/Crowd/Characters/character-o",
            "GTEX/FreeAssets/Crowd/Characters/character-p",
            "GTEX/FreeAssets/Crowd/Characters/character-q",
            "GTEX/FreeAssets/Crowd/Characters/character-r"
        };

        private enum GtexIllusionSourceMode
        {
            SampleResource,
            FilePath,
            RemoteUrl
        }

        private sealed class GtexIllusionPlayer
        {
            public string Uid;
            public string TeamId;
            public int Number;
            public Transform Transform;
            public Vector3 HomePosition;
            public Renderer BodyRenderer;
            public Renderer ShortsRenderer;
            public Renderer HeadRenderer;
            public Renderer LeftLegRenderer;
            public Renderer RightLegRenderer;
            public Renderer LeftArmRenderer;
            public Renderer RightArmRenderer;
            public Transform GroundShadowTransform;
            public Renderer GroundShadowRenderer;
            public Transform ActiveMarkerTransform;
            public Renderer ActiveMarkerRenderer;
        }

        private enum IllusionCameraPreset
        {
            Broadcast,
            MidfieldFlow,
            AttackPush,
            BoxZoom,
            GoalCelebration
        }

        [Header("Timeline")]
        [SerializeField] private TextAsset timelineAsset;
        [SerializeField] private string timelineResourcePath = DefaultTimelineResourcePath;
        [SerializeField] private bool autoStart = true;
        [SerializeField] private float interSceneDelaySeconds = 0.3f;

        [Header("Presentation")]
        [SerializeField] private bool createFallbackPitch = true;
        [SerializeField] private bool createFallbackStadium = true;
        [SerializeField] private bool createFallbackUi = true;
        [SerializeField] private bool driveBroadcastCamera = true;

        private readonly Dictionary<string, GtexIllusionPlayer> playersByUid = new Dictionary<string, GtexIllusionPlayer>();
        private readonly List<GtexIllusionPlayer> players = new List<GtexIllusionPlayer>();
        private readonly HashSet<string> activeActorUids = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        private GtexMatchConfig activeConfig;
        private GtexIllusionTimeline timeline;
        private GtexIllusionScenePackage scenePackage;
        private GtexIllusionScene[] playbackScenes = Array.Empty<GtexIllusionScene>();
        private Transform ball;
        private Camera matchCamera;
        private Text scoreText;
        private Text clockText;
        private Text commentaryText;
        private Text overlayText;
        private Text sourceStatusText;
        private Text competitionText;
        private Text playerCardText;
        private Text statsPanelText;
        private Text liveFeedText;
        private Text venueInfoText;
        private Text lowerThirdTickerText;
        private Text eventFlashText;
        private Image eventFlashImage;
        private RawImage minimapImage;
        private Material homeMaterial;
        private Material awayMaterial;
        private Material keeperMaterial;
        private Material homeShortsMaterial;
        private Material awayShortsMaterial;
        private Material keeperShortsMaterial;
        private Material homeSockMaterial;
        private Material awaySockMaterial;
        private Material keeperSockMaterial;
        private Material homeTrimMaterial;
        private Material awayTrimMaterial;
        private Material keeperTrimMaterial;
        private Material bootMaterial;
        private Material numberMaterial;
        private Material standMaterial;
        private Material seatMaterial;
        private Material tunnelMaterial;
        private Material adBoardMaterial;
        private Material pitchMaterial;
        private Material pitchStripeMaterial;
        private Material lineMaterial;
        private Material ballMaterial;
        private Material groundShadowMaterial;
        private Material activeMarkerMaterial;
        private Coroutine playbackRoutine;
        private bool initialized;
        private bool bootstrappingRemoteTimeline;
        private bool playbackStarted;
        private int homeScore;
        private int awayScore;
        private float currentMinute;
        private GtexIllusionSourceMode selectedSourceMode;
        private string homeDisplayName = "Kano Pillars";
        private string awayDisplayName = "Enyimba FC";
        private string currentBallOwnerUid = "home-6";
        private string timelineSource = "generated";
        private string timelineValidationSummary = string.Empty;
        private string currentOverlay = "GTEX PREMIER LEAGUE";
        private string currentMatchLabel = "GTEX PREMIER LEAGUE";
        private string currentWeatherLabel = "28C | Sunny";
        private string currentCrowdLabel = "Crowd 32,600";
        private Vector3 cameraFocus;
        private Vector3 cameraFocusVelocity;
        private Vector3 currentCameraOffset = new Vector3(0f, 38f, -52f);
        private Vector3 currentCameraOffsetVelocity;
        private IllusionCameraPreset currentCameraPreset = IllusionCameraPreset.Broadcast;
        private float cameraPresetHoldUntil;
        private float celebrationCrowdBoostUntil;
        private float eventFlashUntil;
        private float eventFlashFadeStart;
        private Color eventFlashColor = Color.clear;
        private readonly List<string> liveFeedLines = new List<string>();
        private readonly Dictionary<string, int> teamPassCounts = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
        private readonly Dictionary<string, int> teamShotCounts = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
        private readonly Dictionary<string, int> teamSaveCounts = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
        private AudioSource crowdLoopSource;
        private AudioSource effectsSource;
        private AudioClip crowdLoopClip;
        private AudioClip crowdAltLoopClip;
        private AudioClip crowdGoalClip;
        private AudioClip whistleClip;
        private Texture2D minimapTexture;

        public static bool TryAutoStart(GtexMatchConfig matchConfig, bool allowBatchMode = false)
        {
            if (Application.isBatchMode && !allowBatchMode)
            {
                Debug.Log("[GTEX Illusion] Auto-start skipped in batchmode.");
                GtexMatchController.ReportRuntimeState(
                    matchConfig,
                    GtexRuntimeMode.IllusionRuntime,
                    GtexMatchPhase.None,
                    false,
                    nameof(GtexIllusionRuntimeHost),
                    "Illusion runtime skipped in batchmode.");
                return false;
            }

            var existing = UnityEngine.Object.FindFirstObjectByType<GtexIllusionRuntimeHost>();
            if (existing != null)
            {
                existing.ApplyMatchConfig(matchConfig);
                existing.StartPlayback();
                return true;
            }

            var hostObject = new GameObject("GTEX Illusion Runtime");
            if (Application.isPlaying)
            {
                DontDestroyOnLoad(hostObject);
            }

            var host = hostObject.AddComponent<GtexIllusionRuntimeHost>();
            host.ApplyMatchConfig(matchConfig);
            host.StartPlayback();
            return true;
        }

        private void Awake()
        {
            if (activeConfig == null)
            {
                activeConfig = GtexMatchConfigLoader.Load();
            }

            RefreshSelectedSourceModeFromOverrides();
        }

        private void Start()
        {
            if (autoStart && !playbackStarted)
            {
                StartPlayback();
            }
        }

        private void LateUpdate()
        {
            if (!initialized)
            {
                return;
            }

            UpdatePlayerReadabilityVisuals();
            UpdateEventFlashVisuals();

            if (driveBroadcastCamera && matchCamera != null)
            {
                UpdateBroadcastCamera();
                UpdateMinimap();
            }
        }

        private void OnDestroy()
        {
            GtexMatchController.ReportRuntimeState(
                activeConfig,
                GtexRuntimeMode.IllusionRuntime,
                GtexMatchPhase.None,
                false,
                nameof(GtexIllusionRuntimeHost),
                "Illusion runtime destroyed.");
        }

        public void ApplyMatchConfig(GtexMatchConfig matchConfig)
        {
            activeConfig = matchConfig;
            if (matchConfig == null)
            {
                return;
            }

            homeDisplayName = ResolveDisplayName(matchConfig.homeTeamName, matchConfig.homeTemplateTeam, homeDisplayName);
            awayDisplayName = ResolveDisplayName(matchConfig.awayTeamName, matchConfig.awayTemplateTeam, awayDisplayName);
            RefreshSelectedSourceModeFromOverrides();
        }

        [ContextMenu("Start Illusion Playback")]
        public void StartPlayback()
        {
            playbackStarted = true;

            if (!initialized)
            {
                if (selectedSourceMode == GtexIllusionSourceMode.RemoteUrl)
                {
                    var remoteTimelineUrl = ResolveRemoteTimelineUrl();
                    if (!string.IsNullOrWhiteSpace(remoteTimelineUrl))
                    {
                        if (!bootstrappingRemoteTimeline)
                        {
                            bootstrappingRemoteTimeline = true;
                            StartCoroutine(BootstrapRemoteTimelineAndPlay(remoteTimelineUrl.Trim()));
                        }
                    }
                    else
                    {
                        UpdateUi("API source not configured.");
                    }

                    return;
                }
            }

            EnsureInitialized();

            if (playbackRoutine != null)
            {
                StopCoroutine(playbackRoutine);
            }

            playbackRoutine = StartCoroutine(PlayTimelineRoutine());
        }

        [ContextMenu("Restart Illusion Playback")]
        public void RestartPlayback()
        {
            ResetMatchVisuals();
            StartPlayback();
        }

        private void EnsureInitialized()
        {
            if (initialized)
            {
                return;
            }

            PrepareTimeline();
            FinalizeInitialization();
        }

        private void PrepareTimeline()
        {
            if ((timeline != null && timeline.events != null && timeline.events.Length > 0) ||
                (scenePackage != null && scenePackage.scenes != null && scenePackage.scenes.Length > 0) ||
                (playbackScenes != null && playbackScenes.Length > 0))
            {
                return;
            }

            LoadTimelineForSelectedSource();
        }

        private void FinalizeInitialization()
        {
            if (initialized)
            {
                return;
            }

            CreateMaterials();
            EnsurePitch();
            EnsureStadiumShell();
            EnsurePlayers();
            EnsureBall();
            EnsureCamera();
            EnsureAudio();
            EnsureUi();
            ResetMatchVisuals();

            initialized = true;
            GtexScoreAuthority.Reset(homeDisplayName, awayDisplayName);
            GtexMatchController.ReportRuntimeState(
                activeConfig,
                GtexRuntimeMode.IllusionRuntime,
                GtexMatchPhase.Bootstrap,
                false,
                nameof(GtexIllusionRuntimeHost),
                "Illusion runtime initialized.");
            Debug.Log(
                "[GTEX Illusion] Phase 2 runtime initialized. source=" +
                timelineSource +
                " scenes=" +
                (playbackScenes != null ? playbackScenes.Length : 0) +
                " validation=" +
                timelineValidationSummary);
        }

        private IEnumerator BootstrapRemoteTimelineAndPlay(string timelineUrl)
        {
            Debug.Log("[GTEX Illusion] Fetching remote timeline from " + timelineUrl);
            using (var request = UnityWebRequest.Get(timelineUrl))
            {
                yield return request.SendWebRequest();

                if (request.result == UnityWebRequest.Result.Success &&
                    GtexIllusionTimelineLoader.TryParseRawJson(
                            request.downloadHandler != null ? request.downloadHandler.text : string.Empty,
                            timelineUrl,
                            true,
                            out var remoteResult) &&
                        remoteResult != null)
                {
                    if (remoteResult.ScenePackage != null)
                    {
                        ApplyLoadedTimeline(remoteResult);
                        Debug.Log("[GTEX Illusion] Remote scene package ready source=" + timelineSource + " " + timelineValidationSummary);
                        UpdateSourceStatus();
                    }
                    else if (remoteResult.Timeline != null)
                    {
                        timeline = remoteResult.Timeline;
                        scenePackage = null;
                        timelineSource = remoteResult.Source;
                        var validation = GtexIllusionTimelineValidator.Validate(timeline, homeDisplayName, awayDisplayName);
                        if (validation.IsValid)
                        {
                            timeline = validation.Timeline;
                            timelineValidationSummary = validation.Summary;
                            homeDisplayName = ResolveDisplayName(timeline.homeTeam, homeDisplayName, "Home");
                            awayDisplayName = ResolveDisplayName(timeline.awayTeam, awayDisplayName, "Away");
                            BuildPlaybackScenesFromTimeline();
                            Debug.Log("[GTEX Illusion] Remote timeline ready source=" + timelineSource + " " + timelineValidationSummary);
                            UpdateSourceStatus();
                        }
                        else
                        {
                            Debug.LogWarning("[GTEX Illusion] Remote timeline validation failed. Falling back to local/generated timeline. " + validation.Summary);
                            timeline = null;
                            playbackScenes = Array.Empty<GtexIllusionScene>();
                        }
                    }
                }
                else
                {
                    Debug.LogWarning("[GTEX Illusion] Remote timeline fetch failed. Falling back to local/generated timeline. " + request.error);
                }
            }

            bootstrappingRemoteTimeline = false;
            EnsureInitialized();

            if (playbackRoutine != null)
            {
                StopCoroutine(playbackRoutine);
            }

            playbackStarted = true;
            playbackRoutine = StartCoroutine(PlayTimelineRoutine());
        }

        private void LoadTimelineForSelectedSource()
        {
            switch (selectedSourceMode)
            {
                case GtexIllusionSourceMode.FilePath:
                    if (TryLoadTimelineFromFile())
                    {
                        return;
                    }

                    break;
                case GtexIllusionSourceMode.RemoteUrl:
                    timeline = null;
                    timelineSource = "remote:pending";
                    timelineValidationSummary = "Waiting for remote timeline.";
                    UpdateSourceStatus();
                    return;
                default:
                    if (TryLoadTimelineFromSample())
                    {
                        return;
                    }

                    break;
            }

            LoadDefaultTimeline();
        }

        private void LoadDefaultTimeline()
        {
            var loadResult = GtexIllusionTimelineLoader.Load(timelineAsset, timelineResourcePath);
            ApplyLoadedTimeline(loadResult);

            if ((timeline == null || timeline.events == null || timeline.events.Length == 0) &&
                (scenePackage == null || scenePackage.scenes == null || scenePackage.scenes.Length == 0))
            {
                var seed = activeConfig != null ? activeConfig.simulationRandomSeed : 1337;
                timeline = GtexIllusionMatchEngine.GenerateDefaultTimeline(seed, homeDisplayName, awayDisplayName);
                timelineSource = "generated:seed-" + seed;
                scenePackage = null;
                BuildPlaybackScenesFromTimeline();
            }

            if (scenePackage != null && scenePackage.scenes != null && scenePackage.scenes.Length > 0)
            {
                timelineValidationSummary = "Scene package ready: " + scenePackage.scenes.Length + " scenes.";
                ApplyScenePackagePresentation();
                UpdateSourceStatus();
                return;
            }

            var validation = GtexIllusionTimelineValidator.Validate(timeline, homeDisplayName, awayDisplayName);
            if (!validation.IsValid)
            {
                var seed = activeConfig != null ? activeConfig.simulationRandomSeed : 1337;
                Debug.LogWarning("[GTEX Illusion] Timeline validation failed. Falling back to generated sample. reason=" + validation.Summary);
                timeline = GtexIllusionMatchEngine.GenerateDefaultTimeline(seed, homeDisplayName, awayDisplayName);
                timelineSource = "generated:seed-" + seed;
                scenePackage = null;
                validation = GtexIllusionTimelineValidator.Validate(timeline, homeDisplayName, awayDisplayName);
            }
            else
            {
                timeline = validation.Timeline;
            }

            timelineValidationSummary = validation.Summary;
            homeDisplayName = ResolveDisplayName(timeline.homeTeam, homeDisplayName, "Home");
            awayDisplayName = ResolveDisplayName(timeline.awayTeam, awayDisplayName, "Away");
            BuildPlaybackScenesFromTimeline();
            Debug.Log("[GTEX Illusion] Timeline ready source=" + timelineSource + " " + timelineValidationSummary);
            UpdateSourceStatus();
        }

        private bool TryLoadTimelineFromSample()
        {
            GtexIllusionTimelineLoadResult loadResult = null;
            if (timelineAsset != null &&
                GtexIllusionTimelineLoader.TryParseRawJson(timelineAsset.text, "asset:" + timelineAsset.name, false, out loadResult))
            {
                ApplyLoadedTimeline(loadResult);
                return true;
            }

            if (!string.IsNullOrWhiteSpace(timelineResourcePath) &&
                GtexIllusionTimelineLoader.TryLoadFromResource(timelineResourcePath.Trim(), false, out loadResult))
            {
                ApplyLoadedTimeline(loadResult);
                return true;
            }

            return false;
        }

        private bool TryLoadTimelineFromFile()
        {
            var path = GtexIllusionTimelineLoader.ResolveTimelinePathOverride();
            if (string.IsNullOrWhiteSpace(path))
            {
                timelineSource = "file:missing";
                timelineValidationSummary = "No file path configured.";
                UpdateSourceStatus();
                return false;
            }

            if (GtexIllusionTimelineLoader.TryLoadFromPath(path.Trim(), out var loadResult))
            {
                ApplyLoadedTimeline(loadResult);
                return true;
            }

            timelineSource = "file:" + path.Trim();
            timelineValidationSummary = "Configured file could not be loaded.";
            UpdateSourceStatus();
            return false;
        }

        private void ApplyLoadedTimeline(GtexIllusionTimelineLoadResult loadResult)
        {
            timeline = loadResult != null ? loadResult.Timeline : null;
            scenePackage = loadResult != null ? loadResult.ScenePackage : null;
            timelineSource = loadResult != null && !string.IsNullOrWhiteSpace(loadResult.Source)
                ? loadResult.Source
                : timelineSource;
            if (scenePackage != null && scenePackage.scenes != null && scenePackage.scenes.Length > 0)
            {
                timeline = null;
                BuildPlaybackScenesFromScenePackage();
                ApplyScenePackagePresentation();
                timelineValidationSummary = "Scene package ready: " + scenePackage.scenes.Length + " scenes.";
                return;
            }

            BuildPlaybackScenesFromTimeline();
        }

        private void BuildPlaybackScenesFromTimeline()
        {
            if (timeline == null || timeline.events == null || timeline.events.Length == 0)
            {
                playbackScenes = Array.Empty<GtexIllusionScene>();
                return;
            }

            playbackScenes = new GtexIllusionScene[timeline.events.Length];
            for (var index = 0; index < timeline.events.Length; index += 1)
            {
                playbackScenes[index] = GtexIllusionSceneBuilder.Build(timeline.events[index]);
            }
        }

        private void BuildPlaybackScenesFromScenePackage()
        {
            if (scenePackage == null || scenePackage.scenes == null || scenePackage.scenes.Length == 0)
            {
                playbackScenes = Array.Empty<GtexIllusionScene>();
                return;
            }

            playbackScenes = new GtexIllusionScene[scenePackage.scenes.Length];
            for (var index = 0; index < scenePackage.scenes.Length; index += 1)
            {
                playbackScenes[index] = GtexIllusionSceneBuilder.Build(scenePackage.scenes[index]);
            }
        }

        private void ApplyScenePackagePresentation()
        {
            if (scenePackage == null)
            {
                return;
            }

            homeDisplayName = ResolveDisplayName(scenePackage.homeTeam, homeDisplayName, "Home");
            awayDisplayName = ResolveDisplayName(scenePackage.awayTeam, awayDisplayName, "Away");
            if (!string.IsNullOrWhiteSpace(scenePackage.overlay))
            {
                currentOverlay = scenePackage.overlay.Trim();
                currentMatchLabel = currentOverlay;
            }

            liveFeedLines.Clear();
            if (scenePackage.liveFeed != null)
            {
                for (var index = 0; index < scenePackage.liveFeed.Length; index += 1)
                {
                    var item = scenePackage.liveFeed[index];
                    if (item == null || string.IsNullOrWhiteSpace(item.text))
                    {
                        continue;
                    }

                    liveFeedLines.Add(FormatLiveFeedItem(item.minute, item.label, item.text));
                    if (liveFeedLines.Count >= 6)
                    {
                        break;
                    }
                }
            }
        }

        private void RefreshSelectedSourceModeFromOverrides()
        {
            if (!string.IsNullOrWhiteSpace(ResolveRemoteTimelineUrl()))
            {
                selectedSourceMode = GtexIllusionSourceMode.RemoteUrl;
                return;
            }

            if (!string.IsNullOrWhiteSpace(GtexIllusionTimelineLoader.ResolveTimelinePathOverride()))
            {
                selectedSourceMode = GtexIllusionSourceMode.FilePath;
                return;
            }

            selectedSourceMode = GtexIllusionSourceMode.SampleResource;
        }

        private void CreateMaterials()
        {
            homeMaterial = CreateMaterial("GTEX Illusion Home", new Color(1f, 0.86f, 0.05f));
            awayMaterial = CreateMaterial("GTEX Illusion Away", new Color(0.04f, 0.28f, 1f));
            keeperMaterial = CreateMaterial("GTEX Illusion Keeper", new Color(0.9f, 0.18f, 1f));
            homeShortsMaterial = CreateMaterial("GTEX Illusion Home Shorts", new Color(0.02f, 0.34f, 0.08f));
            awayShortsMaterial = CreateMaterial("GTEX Illusion Away Shorts", new Color(0.98f, 0.98f, 1f));
            keeperShortsMaterial = CreateMaterial("GTEX Illusion Keeper Shorts", new Color(0.16f, 0.16f, 0.21f));
            homeSockMaterial = CreateMaterial("GTEX Illusion Home Socks", new Color(1f, 0.9f, 0.12f));
            awaySockMaterial = CreateMaterial("GTEX Illusion Away Socks", new Color(0.03f, 0.18f, 0.95f));
            keeperSockMaterial = CreateMaterial("GTEX Illusion Keeper Socks", new Color(0.95f, 0.32f, 1f));
            homeTrimMaterial = CreateMaterial("GTEX Illusion Home Trim", new Color(0.02f, 0.22f, 0.08f));
            awayTrimMaterial = CreateMaterial("GTEX Illusion Away Trim", new Color(0.97f, 0.97f, 0.99f));
            keeperTrimMaterial = CreateMaterial("GTEX Illusion Keeper Trim", new Color(0.14f, 0.14f, 0.17f));
            bootMaterial = CreateMaterial("GTEX Illusion Boots", new Color(0.08f, 0.08f, 0.1f));
            numberMaterial = CreateMaterial("GTEX Illusion Number", new Color(0.96f, 0.96f, 0.98f));
            standMaterial = CreateMaterial("GTEX Illusion Stand", new Color(0.3f, 0.31f, 0.34f));
            seatMaterial = CreateMaterial("GTEX Illusion Seat", new Color(0.1f, 0.14f, 0.22f));
            tunnelMaterial = CreateMaterial("GTEX Illusion Tunnel", new Color(0.08f, 0.08f, 0.1f));
            adBoardMaterial = CreateMaterial("GTEX Illusion AdBoard", new Color(0.05f, 0.22f, 0.54f));
            pitchMaterial = CreateMaterial("GTEX Illusion Pitch", new Color(0.12f, 0.49f, 0.12f));
            pitchStripeMaterial = CreateMaterial("GTEX Illusion Pitch Stripe", new Color(0.15f, 0.56f, 0.15f));
            lineMaterial = CreateMaterial("GTEX Illusion Line", Color.white);
            ballMaterial = CreateMaterial("GTEX Illusion Ball", new Color(0.94f, 0.94f, 0.9f));
            groundShadowMaterial = CreateTransparentMaterial("GTEX Illusion Ground Shadow", new Color(0f, 0.045f, 0.015f, 0.42f));
            activeMarkerMaterial = CreateTransparentMaterial("GTEX Illusion Active Marker", new Color(1f, 0.88f, 0.12f, 0.52f));
        }

        private void EnsurePitch()
        {
            if (!createFallbackPitch)
            {
                return;
            }

            if (GameObject.Find("GTEX Illusion Pitch") != null)
            {
                return;
            }

            var pitch = GameObject.CreatePrimitive(PrimitiveType.Plane);
            pitch.name = "GTEX Illusion Pitch";
            pitch.transform.position = Vector3.zero;
            pitch.transform.localScale = new Vector3(PitchLength / 10f, 1f, PitchWidth / 10f);
            var renderer = pitch.GetComponent<Renderer>();
            if (renderer != null)
            {
                renderer.sharedMaterial = pitchMaterial;
            }

            CreatePitchStripes(pitch.transform);
            DrawPitchLine("Halfway Line", new Vector3(0f, 0.025f, -PitchWidth * 0.5f), new Vector3(0f, 0.025f, PitchWidth * 0.5f));
            DrawPitchLine("Home Goal Line", new Vector3(-PitchLength * 0.5f, 0.025f, -PitchWidth * 0.5f), new Vector3(-PitchLength * 0.5f, 0.025f, PitchWidth * 0.5f));
            DrawPitchLine("Away Goal Line", new Vector3(PitchLength * 0.5f, 0.025f, -PitchWidth * 0.5f), new Vector3(PitchLength * 0.5f, 0.025f, PitchWidth * 0.5f));
            DrawPitchLine("Bottom Touchline", new Vector3(-PitchLength * 0.5f, 0.025f, -PitchWidth * 0.5f), new Vector3(PitchLength * 0.5f, 0.025f, -PitchWidth * 0.5f));
            DrawPitchLine("Top Touchline", new Vector3(-PitchLength * 0.5f, 0.025f, PitchWidth * 0.5f), new Vector3(PitchLength * 0.5f, 0.025f, PitchWidth * 0.5f));
            DrawBox("Home Box", -PitchLength * 0.5f, 16.5f);
            DrawBox("Away Box", PitchLength * 0.5f, -16.5f);
            DrawCircle("Centre Circle", Vector3.zero, 9.15f, 72);
            CreatePitchMarker("Centre Spot", Vector3.zero, 0.34f);
            CreatePitchMarker("Home Penalty Spot", new Vector3(-PitchLength * 0.5f + 11f, 0f, 0f), 0.26f);
            CreatePitchMarker("Away Penalty Spot", new Vector3(PitchLength * 0.5f - 11f, 0f, 0f), 0.26f);
            CreateGoalFrame("Home Goal", -PitchLength * 0.5f, false);
            CreateGoalFrame("Away Goal", PitchLength * 0.5f, true);
        }

        private void EnsurePlayers()
        {
            if (players.Count > 0)
            {
                return;
            }

            for (var number = 1; number <= 11; number += 1)
            {
                CreatePlayer("home-" + number, "home", number, ResolveFormationPosition("home", number));
                CreatePlayer("away-" + number, "away", number, ResolveFormationPosition("away", number));
            }
        }

        private void EnsureStadiumShell()
        {
            if (!createFallbackStadium)
            {
                return;
            }

            if (GameObject.Find("GTEX Illusion Stadium") != null)
            {
                return;
            }

            var stadiumRoot = new GameObject("GTEX Illusion Stadium");
            CreateTunnel(stadiumRoot.transform, new Vector3(0f, 0.8f, -PitchWidth * 0.5f - 3.5f), new Vector3(2.1f, 1.05f, 1.45f));
            CreateAdBoardRing(stadiumRoot.transform);
            PopulateCrowdRows(stadiumRoot.transform, -PitchWidth * 0.5f - 22f, false, 8, 1);
            PopulateCrowdRows(stadiumRoot.transform, PitchWidth * 0.5f + 22f, false, 8, 1);
            PopulateCrowdRows(stadiumRoot.transform, -PitchLength * 0.5f - 18f, true, 5, 1);
            PopulateCrowdRows(stadiumRoot.transform, PitchLength * 0.5f + 18f, true, 5, 1);
        }

        private void EnsureBall()
        {
            if (ball != null)
            {
                return;
            }

            var ballObject = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            ballObject.name = "GTEX Illusion Ball";
            ballObject.transform.localScale = Vector3.one * 0.48f;
            var renderer = ballObject.GetComponent<Renderer>();
            if (renderer != null)
            {
                renderer.sharedMaterial = ballMaterial;
            }

            ball = ballObject.transform;
        }

        private void EnsureCamera()
        {
            matchCamera = Camera.main;
            if (matchCamera == null)
            {
                var cameraObject = new GameObject("GTEX Illusion Broadcast Camera");
                matchCamera = cameraObject.AddComponent<Camera>();
                cameraObject.tag = "MainCamera";
            }

            matchCamera.clearFlags = CameraClearFlags.SolidColor;
            matchCamera.backgroundColor = new Color(0.05f, 0.08f, 0.14f);
            matchCamera.allowHDR = true;
            matchCamera.fieldOfView = 46f;
            cameraFocus = Vector3.zero;
            currentCameraOffset = new Vector3(0f, 48f, -68f);
            UpdateBroadcastCamera(true);
            RenderSettings.ambientLight = new Color(0.62f, 0.67f, 0.7f);
            RenderSettings.fog = true;
            RenderSettings.fogColor = new Color(0.1f, 0.13f, 0.18f);
            RenderSettings.fogStartDistance = 82f;
            RenderSettings.fogEndDistance = 190f;
        }

        private void EnsureAudio()
        {
            if (crowdLoopSource != null && effectsSource != null)
            {
                return;
            }

            var audioRoot = new GameObject("GTEX Illusion Audio");
            audioRoot.transform.SetParent(transform, false);

            crowdLoopSource = audioRoot.AddComponent<AudioSource>();
            crowdLoopSource.loop = true;
            crowdLoopSource.playOnAwake = false;
            crowdLoopSource.spatialBlend = 0f;
            crowdLoopSource.volume = 0.2f;

            effectsSource = audioRoot.AddComponent<AudioSource>();
            effectsSource.loop = false;
            effectsSource.playOnAwake = false;
            effectsSource.spatialBlend = 0f;
            effectsSource.volume = 0.48f;

            crowdLoopClip = Resources.Load<AudioClip>("GTEX/FreeAssets/Audio/mixkit_ambient_sports_crowd");
            crowdAltLoopClip = Resources.Load<AudioClip>("GTEX/FreeAssets/Audio/mixkit_crowd_at_the_stadium");
            crowdGoalClip = Resources.Load<AudioClip>("GTEX/FreeAssets/Audio/mixkit_huge_crowd_cheering_victory");
            whistleClip = Resources.Load<AudioClip>("GTEX/FreeAssets/Audio/mixkit_police_short_whistle");

            if (crowdLoopClip != null)
            {
                crowdLoopSource.clip = crowdLoopClip;
                crowdLoopSource.Play();
            }
        }

        private void EnsureUi()
        {
            if (!createFallbackUi)
            {
                return;
            }

            if (scoreText != null)
            {
                return;
            }

            var canvasObject = new GameObject("GTEX Illusion UI");
            var canvas = canvasObject.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            canvas.sortingOrder = 50;
            canvasObject.AddComponent<CanvasScaler>();
            canvasObject.AddComponent<GraphicRaycaster>();

            var eventFlashObject = new GameObject("GTEX Illusion UI Event Flash");
            eventFlashObject.transform.SetParent(canvas.transform, false);
            var eventFlashRect = eventFlashObject.AddComponent<RectTransform>();
            eventFlashRect.anchorMin = Vector2.zero;
            eventFlashRect.anchorMax = Vector2.one;
            eventFlashRect.pivot = new Vector2(0.5f, 0.5f);
            eventFlashRect.anchoredPosition = Vector2.zero;
            eventFlashRect.sizeDelta = Vector2.zero;
            eventFlashImage = eventFlashObject.AddComponent<Image>();
            eventFlashImage.color = Color.clear;
            eventFlashImage.raycastTarget = false;
            eventFlashText = CreateText(eventFlashObject.transform, "EventFlashText", Vector2.zero, Vector2.one, Vector2.zero, new Vector2(-80f, -80f), 42, TextAnchor.MiddleCenter);
            eventFlashText.color = Color.clear;
            eventFlashText.raycastTarget = false;

            var scorePanel = CreatePanel(canvas.transform, "ScorePanel", new Vector2(0f, 1f), new Vector2(0f, 1f), new Vector2(24f, -18f), new Vector2(540f, 84f), new Color(0.03f, 0.05f, 0.1f, 0.92f));
            competitionText = CreateText(scorePanel.transform, "Competition", new Vector2(0f, 1f), new Vector2(1f, 1f), new Vector2(0f, -14f), new Vector2(-20f, 20f), 14, TextAnchor.UpperLeft);
            competitionText.color = new Color(0.95f, 0.82f, 0.32f);
            scoreText = CreateText(scorePanel.transform, "Score", new Vector2(0f, 0f), new Vector2(1f, 1f), new Vector2(0f, -4f), new Vector2(-20f, -4f), 26, TextAnchor.MiddleLeft);

            var clockPanel = CreatePanel(canvas.transform, "ClockPanel", new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(0f, -18f), new Vector2(146f, 58f), new Color(0.03f, 0.05f, 0.1f, 0.92f));
            clockText = CreateText(clockPanel.transform, "Clock", Vector2.zero, Vector2.one, Vector2.zero, new Vector2(-12f, -12f), 24, TextAnchor.MiddleCenter);

            var overlayPanel = CreatePanel(canvas.transform, "OverlayPanel", new Vector2(1f, 1f), new Vector2(1f, 1f), new Vector2(-24f, -18f), new Vector2(360f, 84f), new Color(0.03f, 0.05f, 0.1f, 0.92f));
            overlayText = CreateText(overlayPanel.transform, "Overlay", Vector2.zero, Vector2.one, new Vector2(-8f, -4f), new Vector2(-20f, -16f), 20, TextAnchor.MiddleRight);

            var venuePanel = CreatePanel(canvas.transform, "VenuePanel", new Vector2(1f, 1f), new Vector2(1f, 1f), new Vector2(-24f, -112f), new Vector2(220f, 92f), new Color(0.04f, 0.06f, 0.1f, 0.88f));
            venueInfoText = CreateText(venuePanel.transform, "VenueInfo", Vector2.zero, Vector2.one, new Vector2(0f, 0f), new Vector2(-18f, -16f), 15, TextAnchor.MiddleCenter);

            var liveFeedPanel = CreatePanel(canvas.transform, "LiveFeedPanel", new Vector2(1f, 0.5f), new Vector2(1f, 0.5f), new Vector2(-24f, -12f), new Vector2(360f, 320f), new Color(0.03f, 0.05f, 0.1f, 0.86f));
            var liveFeedLabel = CreateText(liveFeedPanel.transform, "LiveFeedLabel", new Vector2(0f, 1f), new Vector2(1f, 1f), new Vector2(0f, -12f), new Vector2(-20f, 24f), 18, TextAnchor.UpperLeft);
            liveFeedLabel.text = "GTEX LIVE FEED";
            liveFeedLabel.color = new Color(0.94f, 0.26f, 0.26f);
            liveFeedText = CreateText(liveFeedPanel.transform, "LiveFeed", new Vector2(0f, 0f), new Vector2(1f, 1f), new Vector2(0f, -18f), new Vector2(-24f, -54f), 15, TextAnchor.UpperLeft);

            var playerCardPanel = CreatePanel(canvas.transform, "PlayerCardPanel", new Vector2(0f, 0f), new Vector2(0f, 0f), new Vector2(24f, 24f), new Vector2(316f, 116f), new Color(0.03f, 0.05f, 0.1f, 0.92f));
            playerCardText = CreateText(playerCardPanel.transform, "PlayerCard", Vector2.zero, Vector2.one, new Vector2(0f, 0f), new Vector2(-20f, -18f), 17, TextAnchor.UpperLeft);

            var statsPanel = CreatePanel(canvas.transform, "StatsPanel", new Vector2(1f, 0f), new Vector2(1f, 0f), new Vector2(-24f, 24f), new Vector2(360f, 184f), new Color(0.03f, 0.05f, 0.1f, 0.9f));
            statsPanelText = CreateText(statsPanel.transform, "Stats", Vector2.zero, Vector2.one, new Vector2(0f, 0f), new Vector2(-20f, -20f), 15, TextAnchor.UpperLeft);

            var minimapPanel = CreatePanel(canvas.transform, "MinimapPanel", new Vector2(0.5f, 0f), new Vector2(0.5f, 0f), new Vector2(0f, 110f), new Vector2(190f, 120f), new Color(0.03f, 0.05f, 0.1f, 0.88f));
            var minimapObject = new GameObject("GTEX Illusion UI Minimap");
            minimapObject.transform.SetParent(minimapPanel.transform, false);
            var minimapRect = minimapObject.AddComponent<RectTransform>();
            minimapRect.anchorMin = new Vector2(0.5f, 0.5f);
            minimapRect.anchorMax = new Vector2(0.5f, 0.5f);
            minimapRect.pivot = new Vector2(0.5f, 0.5f);
            minimapRect.anchoredPosition = Vector2.zero;
            minimapRect.sizeDelta = new Vector2(168f, 92f);
            minimapImage = minimapObject.AddComponent<RawImage>();

            var commentaryPanel = CreatePanel(canvas.transform, "CommentaryPanel", new Vector2(0.5f, 0f), new Vector2(0.5f, 0f), new Vector2(0f, 24f), new Vector2(860f, 88f), new Color(0.035f, 0.16f, 0.07f, 0.93f));
            commentaryText = CreateText(commentaryPanel.transform, "Commentary", new Vector2(0f, 0.38f), Vector2.one, Vector2.zero, new Vector2(-22f, -10f), 20, TextAnchor.MiddleCenter);
            lowerThirdTickerText = CreateText(commentaryPanel.transform, "Ticker", Vector2.zero, new Vector2(1f, 0.38f), new Vector2(0f, 2f), new Vector2(-26f, -8f), 13, TextAnchor.MiddleCenter);
            lowerThirdTickerText.color = new Color(0.86f, 0.94f, 0.86f);
            CreateSourceSelector(canvas.transform);

            UpdateUi("Ready");
        }

        private void CreateSourceSelector(Transform parent)
        {
            var panelObject = new GameObject("GTEX Illusion UI Source Panel");
            panelObject.transform.SetParent(parent, false);
            var panelRect = panelObject.AddComponent<RectTransform>();
            panelRect.anchorMin = new Vector2(0f, 0f);
            panelRect.anchorMax = new Vector2(0f, 0f);
            panelRect.pivot = new Vector2(0f, 0f);
            panelRect.anchoredPosition = new Vector2(24f, 146f);
            panelRect.sizeDelta = new Vector2(260f, 30f);

            var panelImage = panelObject.AddComponent<Image>();
            panelImage.color = new Color(0f, 0f, 0f, 0.22f);

            sourceStatusText = CreateText(panelRect, "SourceStatus", new Vector2(0f, 0f), new Vector2(0f, 0f), new Vector2(10f, 3f), new Vector2(236f, 24f), 13, TextAnchor.MiddleLeft);
            sourceStatusText.color = new Color(0.92f, 0.94f, 0.98f);
            UpdateSourceStatus();
        }

        private IEnumerator PlayTimelineRoutine()
        {
            GtexRuntimeState.MarkStarted(GtexRuntimeMode.IllusionRuntime, nameof(GtexIllusionRuntimeHost));
            GtexMatchController.ReportRuntimeState(
                activeConfig,
                GtexRuntimeMode.IllusionRuntime,
                GtexMatchPhase.FirstHalf,
                true,
                nameof(GtexIllusionRuntimeHost),
                "Illusion playback started.");
            Debug.Log("[GTEX Illusion] Start timeline id=" + ResolvePlaybackMatchId() + " source=" + timelineSource + " scenes=" + playbackScenes.Length);

            for (var index = 0; index < playbackScenes.Length; index += 1)
            {
                var scene = playbackScenes[index];
                currentMinute = scene.Minute;
                RegisterSceneStats(scene);
                PushLiveFeed(scene);
                TriggerEventFlash(scene);
                UpdateUi(scene.Commentary, scene.Overlay);
                Debug.Log(
                    "[GTEX Illusion] Scene " +
                    (index + 1).ToString("00") +
                    " " +
                    scene.EventKind +
                    " minute=" +
                    scene.Minute.ToString("0.0") +
                    " actor=" +
                    scene.ActorUid +
                    " target=" +
                    scene.TargetUid +
                    " outcome=" +
                    scene.Outcome);
                GtexMatchController.ReportMatchSnapshot(
                    GtexRuntimeMode.IllusionRuntime,
                    scene.Minute < 45f ? GtexMatchPhase.FirstHalf : GtexMatchPhase.SecondHalf,
                    true,
                    nameof(GtexIllusionRuntimeHost),
                    scene.Minute,
                    homeScore,
                    awayScore,
                    "Illusion scene " + scene.EventKind);

                yield return PlaySceneRoutine(scene);

                if (interSceneDelaySeconds > 0f)
                {
                    yield return new WaitForSeconds(interSceneDelaySeconds);
                }
            }

            currentMinute = 90f;
            UpdateUi("Full time.");
            GtexMatchController.ReportRuntimeState(
                activeConfig,
                GtexRuntimeMode.IllusionRuntime,
                GtexMatchPhase.FullTime,
                false,
                nameof(GtexIllusionRuntimeHost),
                "Illusion playback complete.");
            Debug.Log("[GTEX Illusion] Complete timeline id=" + ResolvePlaybackMatchId());
            playbackRoutine = null;
        }

        private IEnumerator PlaySceneRoutine(GtexIllusionScene scene)
        {
            activeActorUids.Clear();
            if (!string.IsNullOrWhiteSpace(scene.ActorUid))
            {
                activeActorUids.Add(scene.ActorUid);
            }

            if (!string.IsNullOrWhiteSpace(scene.TargetUid))
            {
                activeActorUids.Add(scene.TargetUid);
            }

            SetCameraPresetForScene(scene);
            PlaySceneAudio(scene);
            UpdateUi(
                string.IsNullOrWhiteSpace(scene.Commentary) ? scene.EventKind.ToString() : scene.Commentary,
                ResolveBroadcastOverlay(scene));

            switch (scene.SceneKind)
            {
                case GtexIllusionSceneKind.PassScene:
                    yield return PlayPassRoutine(scene, false);
                    break;
                case GtexIllusionSceneKind.ThroughPassScene:
                    yield return PlayPassRoutine(scene, true);
                    break;
                case GtexIllusionSceneKind.DribbleScene:
                    yield return PlayDribbleRoutine(scene);
                    break;
                case GtexIllusionSceneKind.ShotScene:
                    yield return PlayShotRoutine(scene);
                    break;
                case GtexIllusionSceneKind.SaveScene:
                    yield return PlaySaveRoutine(scene);
                    break;
                case GtexIllusionSceneKind.GoalScene:
                    yield return PlayGoalRoutine(scene);
                    break;
                case GtexIllusionSceneKind.TackleScene:
                    yield return PlayTackleRoutine(scene);
                    break;
                case GtexIllusionSceneKind.FoulScene:
                    yield return PlayFoulRoutine(scene);
                    break;
                case GtexIllusionSceneKind.ResetScene:
                    yield return ResetFormationRoutine(scene.DurationSeconds);
                    break;
                default:
                    yield return new WaitForSeconds(Mathf.Max(0.25f, scene.DurationSeconds));
                    break;
            }
        }

        private IEnumerator PlayPassRoutine(GtexIllusionScene scene, bool throughPass)
        {
            if (!TryResolvePlayer(scene.ActorUid, out var passer) ||
                !TryResolvePlayer(scene.TargetUid, out var receiver))
            {
                yield break;
            }

            currentBallOwnerUid = passer.Uid;
            FaceTowards(passer.Transform, receiver.Transform.position);
            PlaceBallAtFeet(passer);

            var duration = Mathf.Max(0.65f, scene.DurationSeconds);
            var receiverTarget = throughPass
                ? ResolveThroughPassPoint(passer, receiver)
                : receiver.Transform.position;
            receiverTarget = ClampToPitch(receiverTarget);
            receiverTarget.y = PlayerY;

            BeginOffBallDrift(duration, passer.Uid, receiver.Uid);
            StartCoroutine(MovePlayerRoutine(receiver.Transform, receiverTarget, duration * 0.92f));

            var ballTarget = BallPointForPlayerAt(receiver, receiverTarget);
            yield return MoveBallRoutine(ball.position, ballTarget, duration, throughPass ? 0.08f : 0.02f);

            receiver.Transform.position = receiverTarget;
            FaceTowards(receiver.Transform, passer.Transform.position);
            currentBallOwnerUid = receiver.Uid;
            PlaceBallAtFeet(receiver);
        }

        private IEnumerator PlayDribbleRoutine(GtexIllusionScene scene)
        {
            if (!TryResolvePlayer(scene.ActorUid, out var carrier))
            {
                yield break;
            }

            currentBallOwnerUid = carrier.Uid;
            var direction = ResolveAttackDirection(carrier.TeamId);
            var target = scene.TargetX != 0f || scene.TargetZ != 0f
                ? new Vector3(scene.TargetX, PlayerY, scene.TargetZ)
                : carrier.Transform.position + direction * 10f;
            target = ClampToPitch(target);
            target.y = PlayerY;

            BeginOffBallDrift(scene.DurationSeconds, carrier.Uid);
            yield return MovePlayerWithBallRoutine(carrier, target, Mathf.Max(0.75f, scene.DurationSeconds));
        }

        private IEnumerator PlayShotRoutine(GtexIllusionScene scene)
        {
            if (!TryResolvePlayer(scene.ActorUid, out var shooter))
            {
                yield break;
            }

            currentBallOwnerUid = shooter.Uid;
            PlaceBallAtFeet(shooter);

            var outcome = string.IsNullOrWhiteSpace(scene.Outcome)
                ? EvaluateShotOutcome(shooter)
                : scene.Outcome;
            var opponentKeeperUid = ResolveOpponentTeam(shooter.TeamId) + "-1";
            TryResolvePlayer(opponentKeeperUid, out var keeper);

            var goal = ResolveGoalCenter(shooter.TeamId);
            var shotTarget = ResolveShotTarget(shooter.TeamId, outcome);
            FaceTowards(shooter.Transform, goal);

            BeginOffBallDrift(scene.DurationSeconds, shooter.Uid, opponentKeeperUid);

            if (keeper != null && string.Equals(outcome, "save", StringComparison.OrdinalIgnoreCase))
            {
                var savePoint = Vector3.Lerp(keeper.Transform.position, shotTarget, 0.38f);
                savePoint.y = PlayerY;
                StartCoroutine(MovePlayerRoutine(keeper.Transform, savePoint, scene.DurationSeconds * 0.78f));
            }

            yield return MoveBallRoutine(ball.position, shotTarget, Mathf.Max(0.75f, scene.DurationSeconds), 0.35f);

            if (keeper != null && string.Equals(outcome, "save", StringComparison.OrdinalIgnoreCase))
            {
                currentBallOwnerUid = keeper.Uid;
                PlaceBallAtFeet(keeper);
            }
        }

        private IEnumerator PlaySaveRoutine(GtexIllusionScene scene)
        {
            var keeperUid = string.IsNullOrWhiteSpace(scene.ActorUid)
                ? scene.TeamId + "-1"
                : scene.ActorUid;
            if (!TryResolvePlayer(keeperUid, out var keeper))
            {
                yield break;
            }

            yield return MovePlayerRoutine(keeper.Transform, ClampToPitch(ball.position), Mathf.Max(0.45f, scene.DurationSeconds * 0.55f));
            currentBallOwnerUid = keeper.Uid;
            PlaceBallAtFeet(keeper);
        }

        private IEnumerator PlayGoalRoutine(GtexIllusionScene scene)
        {
            if (string.Equals(scene.TeamId, "away", StringComparison.OrdinalIgnoreCase))
            {
                awayScore += 1;
            }
            else
            {
                homeScore += 1;
            }

            GtexScoreAuthority.SetScore(homeScore, awayScore, currentMinute, "Illusion goal");
            TriggerEventFlash(scene, true);
            UpdateUi(string.IsNullOrWhiteSpace(scene.Commentary) ? "Goal." : scene.Commentary, ResolveBroadcastOverlay(scene));

            if (TryResolvePlayer(scene.ActorUid, out var scorer))
            {
                yield return new WaitForSeconds(0.18f);
                yield return PlayCelebrationRoutine(scorer, Mathf.Max(0.8f, scene.DurationSeconds));
            }
            else
            {
                yield return new WaitForSeconds(Mathf.Max(0.6f, scene.DurationSeconds));
            }
        }

        private IEnumerator PlayTackleRoutine(GtexIllusionScene scene)
        {
            if (!TryResolvePlayer(scene.ActorUid, out var defender))
            {
                yield break;
            }

            if (!TryResolvePlayer(scene.TargetUid, out var attacker))
            {
                attacker = null;
            }

            var target = attacker != null
                ? Vector3.Lerp(defender.Transform.position, attacker.Transform.position, 0.62f)
                : defender.Transform.position + ResolveAttackDirection(defender.TeamId) * 3f;
            target = ClampToPitch(target);
            target.y = PlayerY;

            yield return MovePlayerRoutine(defender.Transform, target, Mathf.Max(0.5f, scene.DurationSeconds));
            currentBallOwnerUid = defender.Uid;
            PlaceBallAtFeet(defender);
        }

        private IEnumerator PlayFoulRoutine(GtexIllusionScene scene)
        {
            if (TryResolvePlayer(scene.ActorUid, out var actor) &&
                TryResolvePlayer(scene.TargetUid, out var target))
            {
                FaceTowards(actor.Transform, target.Transform.position);
                FaceTowards(target.Transform, actor.Transform.position);
            }

            yield return new WaitForSeconds(Mathf.Max(0.5f, scene.DurationSeconds));
        }

        private IEnumerator ResetFormationRoutine(float duration)
        {
            duration = Mathf.Max(0.75f, duration);
            for (var index = 0; index < players.Count; index += 1)
            {
                StartCoroutine(MovePlayerRoutine(players[index].Transform, players[index].HomePosition, duration));
            }

            yield return new WaitForSeconds(duration);
            currentBallOwnerUid = "home-6";
            if (TryResolvePlayer(currentBallOwnerUid, out var owner))
            {
                PlaceBallAtFeet(owner);
            }
        }

        private IEnumerator MovePlayerRoutine(Transform target, Vector3 end, float duration)
        {
            if (target == null)
            {
                yield break;
            }

            var start = target.position;
            end = ClampToPitch(end);
            start.y = PlayerY;
            end.y = PlayerY;
            var elapsed = 0f;
            while (elapsed < duration)
            {
                elapsed += Time.deltaTime;
                var t = Mathf.Clamp01(elapsed / Mathf.Max(0.01f, duration));
                var eased = Mathf.SmoothStep(0f, 1f, t);
                var next = Vector3.Lerp(start, end, eased);
                next.y += Mathf.Sin(eased * Mathf.PI * 3f) * 0.06f;
                FaceTowards(target, next);
                target.position = next;
                yield return null;
            }

            target.position = end;
        }

        private IEnumerator MovePlayerWithBallRoutine(GtexIllusionPlayer player, Vector3 end, float duration)
        {
            if (player == null || player.Transform == null)
            {
                yield break;
            }

            var start = player.Transform.position;
            end = ClampToPitch(end);
            start.y = PlayerY;
            end.y = PlayerY;
            var elapsed = 0f;
            while (elapsed < duration)
            {
                elapsed += Time.deltaTime;
                var t = Mathf.Clamp01(elapsed / Mathf.Max(0.01f, duration));
                var eased = Mathf.SmoothStep(0f, 1f, t);
                var next = Vector3.Lerp(start, end, eased);
                next.y += Mathf.Sin(eased * Mathf.PI * 4f) * 0.04f;
                player.Transform.position = next;
                FaceTowards(player.Transform, end);
                PlaceBallAtFeet(player);
                yield return null;
            }

            player.Transform.position = end;
            PlaceBallAtFeet(player);
        }

        private IEnumerator MoveBallRoutine(Vector3 start, Vector3 end, float duration, float arcHeight)
        {
            if (ball == null)
            {
                yield break;
            }

            start.y = BallY;
            end.y = BallY;
            var elapsed = 0f;
            while (elapsed < duration)
            {
                elapsed += Time.deltaTime;
                var t = Mathf.Clamp01(elapsed / Mathf.Max(0.01f, duration));
                var eased = Mathf.SmoothStep(0f, 1f, t);
                var next = Vector3.Lerp(start, end, eased);
                next.y = BallY + Mathf.Sin(eased * Mathf.PI) * Mathf.Max(0f, arcHeight);
                ball.position = next;
                yield return null;
            }

            ball.position = end;
        }

        private void BeginOffBallDrift(float duration, params string[] excludedUids)
        {
            var excluded = new HashSet<string>(excludedUids ?? Array.Empty<string>(), StringComparer.OrdinalIgnoreCase);
            var ballX = ball != null ? ball.position.x : 0f;
            for (var index = 0; index < players.Count; index += 1)
            {
                var player = players[index];
                if (player == null || excluded.Contains(player.Uid) || player.Number == 1)
                {
                    continue;
                }

                var attackShift = ResolveAttackDirection(player.TeamId) * Mathf.Clamp(ballX * 0.12f, -8f, 8f);
                var widthShift = Vector3.forward * Mathf.Sin((currentMinute + player.Number) * 0.35f) * 0.9f;
                var target = ClampToPitch(player.HomePosition + attackShift + widthShift);
                target.y = PlayerY;
                StartCoroutine(MovePlayerRoutine(player.Transform, target, Mathf.Max(0.5f, duration * 0.8f)));
            }
        }

        private void ResetMatchVisuals()
        {
            homeScore = 0;
            awayScore = 0;
            currentMinute = 0f;
            currentBallOwnerUid = "home-6";
            currentOverlay = !string.IsNullOrWhiteSpace(scenePackage != null ? scenePackage.overlay : string.Empty)
                ? scenePackage.overlay.Trim()
                : "GTEX PREMIER LEAGUE";
            currentMatchLabel = currentOverlay;
            teamPassCounts.Clear();
            teamShotCounts.Clear();
            teamSaveCounts.Clear();
            if (scenePackage == null || scenePackage.liveFeed == null || scenePackage.liveFeed.Length == 0)
            {
                liveFeedLines.Clear();
            }

            for (var index = 0; index < players.Count; index += 1)
            {
                var player = players[index];
                if (player == null || player.Transform == null)
                {
                    continue;
                }

                player.Transform.position = player.HomePosition;
                FaceTowards(player.Transform, player.HomePosition + ResolveAttackDirection(player.TeamId));
            }

            if (TryResolvePlayer(currentBallOwnerUid, out var owner))
            {
                PlaceBallAtFeet(owner);
            }

            GtexScoreAuthority.SetScore(0, 0, 0f, "Illusion kickoff");
            UpdateUi("Ready");
        }

        private void CreatePlayer(string uid, string teamId, int number, Vector3 position)
        {
            var playerObject = new GameObject("GTEX Illusion Player " + uid);
            playerObject.name = "GTEX Illusion Player " + uid;
            playerObject.transform.position = position;
            playerObject.transform.localScale = Vector3.one * 1.08f;

            var rootCollider = playerObject.AddComponent<CapsuleCollider>();
            rootCollider.center = new Vector3(0f, 0.9f, 0f);
            rootCollider.height = 1.85f;
            rootCollider.radius = 0.26f;

            Renderer renderer;
            Renderer shortsRenderer;
            Renderer headRenderer;
            Renderer leftLegRenderer;
            Renderer rightLegRenderer;
            Renderer leftArmRenderer;
            Renderer rightArmRenderer;

            if (!TryCreateFreeAssetPlayerVisual(
                    playerObject.transform,
                    uid,
                    teamId,
                    number,
                    out renderer,
                    out shortsRenderer,
                    out headRenderer,
                    out leftLegRenderer,
                    out rightLegRenderer,
                    out leftArmRenderer,
                    out rightArmRenderer))
            {
                CreateFallbackPlayerVisual(
                    playerObject.transform,
                    uid,
                    teamId,
                    number,
                    out renderer,
                    out shortsRenderer,
                    out headRenderer,
                    out leftLegRenderer,
                    out rightLegRenderer,
                    out leftArmRenderer,
                    out rightArmRenderer);
            }

            var groundShadowRenderer = CreateGroundDisc(playerObject.transform, uid + "-GroundShadow", new Vector3(0f, -0.91f, 0f), new Vector3(0.62f, 0.012f, 0.44f), groundShadowMaterial);
            var activeMarkerRenderer = CreateGroundDisc(playerObject.transform, uid + "-ActiveMarker", new Vector3(0f, -0.905f, 0f), new Vector3(0.78f, 0.01f, 0.56f), activeMarkerMaterial);
            if (activeMarkerRenderer != null)
            {
                activeMarkerRenderer.enabled = false;
            }

            var player = new GtexIllusionPlayer
            {
                Uid = uid,
                TeamId = teamId,
                Number = number,
                Transform = playerObject.transform,
                HomePosition = position,
                BodyRenderer = renderer,
                ShortsRenderer = shortsRenderer,
                HeadRenderer = headRenderer,
                LeftLegRenderer = leftLegRenderer,
                RightLegRenderer = rightLegRenderer,
                LeftArmRenderer = leftArmRenderer,
                RightArmRenderer = rightArmRenderer,
                GroundShadowTransform = groundShadowRenderer != null ? groundShadowRenderer.transform : null,
                GroundShadowRenderer = groundShadowRenderer,
                ActiveMarkerTransform = activeMarkerRenderer != null ? activeMarkerRenderer.transform : null,
                ActiveMarkerRenderer = activeMarkerRenderer
            };

            players.Add(player);
            playersByUid[uid] = player;
            FaceTowards(player.Transform, position + ResolveAttackDirection(teamId));
        }

        private bool TryCreateFreeAssetPlayerVisual(
            Transform parent,
            string uid,
            string teamId,
            int number,
            out Renderer bodyRenderer,
            out Renderer shortsRenderer,
            out Renderer headRenderer,
            out Renderer leftLegRenderer,
            out Renderer rightLegRenderer,
            out Renderer leftArmRenderer,
            out Renderer rightArmRenderer)
        {
            bodyRenderer = null;
            shortsRenderer = null;
            headRenderer = null;
            leftLegRenderer = null;
            rightLegRenderer = null;
            leftArmRenderer = null;
            rightArmRenderer = null;

            if (FreeCharacterResourceNames == null || FreeCharacterResourceNames.Length == 0)
            {
                return false;
            }

            var index = Mathf.Abs((number - 1) + (string.Equals(teamId, "away", StringComparison.OrdinalIgnoreCase) ? 7 : 0)) % FreeCharacterResourceNames.Length;
            var prefab = Resources.Load<GameObject>(FreeCharacterResourceNames[index]);
            if (prefab == null)
            {
                return false;
            }

            var visualRoot = Instantiate(prefab, parent, false);
            visualRoot.name = uid + "-Visual";
            visualRoot.transform.localPosition = Vector3.zero;
            visualRoot.transform.localRotation = Quaternion.identity;

            RemoveCollidersRecursive(visualRoot);
            var sourceRenderers = visualRoot.GetComponentsInChildren<Renderer>(true);
            if (sourceRenderers == null || sourceRenderers.Length == 0)
            {
                Destroy(visualRoot);
                return false;
            }

            for (var rendererIndex = 0; rendererIndex < sourceRenderers.Length; rendererIndex += 1)
            {
                if (sourceRenderers[rendererIndex] == null)
                {
                    continue;
                }

                sourceRenderers[rendererIndex].shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                sourceRenderers[rendererIndex].receiveShadows = false;
            }

            FitVisualHeight(visualRoot.transform, sourceRenderers, 1.84f);
            CenterVisualOnFeet(visualRoot.transform, sourceRenderers);

            bodyRenderer = CreateKitShell(parent, uid, teamId, number, out shortsRenderer, out leftLegRenderer, out rightLegRenderer, out leftArmRenderer, out rightArmRenderer);
            headRenderer = sourceRenderers[0];
            return bodyRenderer != null;
        }

        private void CreateFallbackPlayerVisual(
            Transform parent,
            string uid,
            string teamId,
            int number,
            out Renderer bodyRenderer,
            out Renderer shortsRenderer,
            out Renderer headRenderer,
            out Renderer leftLegRenderer,
            out Renderer rightLegRenderer,
            out Renderer leftArmRenderer,
            out Renderer rightArmRenderer)
        {
            var bodyObject = GameObject.CreatePrimitive(PrimitiveType.Capsule);
            bodyObject.name = uid + "-Body";
            bodyObject.transform.SetParent(parent, false);
            bodyObject.transform.localPosition = new Vector3(0f, 0.84f, 0f);
            bodyObject.transform.localScale = new Vector3(0.56f, 0.58f, 0.36f);
            var bodyCollider = bodyObject.GetComponent<Collider>();
            if (bodyCollider != null)
            {
                Destroy(bodyCollider);
            }

            bodyRenderer = bodyObject.GetComponent<Renderer>();
            if (bodyRenderer != null)
            {
                bodyRenderer.sharedMaterial = ResolveShirtMaterial(teamId, number);
            }

            var headObject = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            headObject.name = uid + "-Head";
            headObject.transform.SetParent(parent, false);
            headObject.transform.localPosition = new Vector3(0f, 1.7f, 0f);
            headObject.transform.localScale = new Vector3(0.28f, 0.28f, 0.28f);
            var headCollider = headObject.GetComponent<Collider>();
            if (headCollider != null)
            {
                Destroy(headCollider);
            }

            headRenderer = headObject.GetComponent<Renderer>();
            if (headRenderer != null)
            {
                headRenderer.sharedMaterial = CreateMaterial(
                    "GTEX Illusion Skin " + uid,
                    string.Equals(teamId, "away", StringComparison.OrdinalIgnoreCase)
                        ? new Color(0.47f, 0.31f, 0.2f)
                        : new Color(0.62f, 0.43f, 0.28f));
            }

            var leftArmObject = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            leftArmObject.name = uid + "-LeftArm";
            leftArmObject.transform.SetParent(parent, false);
            leftArmObject.transform.localPosition = new Vector3(-0.34f, 1.03f, 0f);
            leftArmObject.transform.localRotation = Quaternion.Euler(0f, 0f, 78f);
            leftArmObject.transform.localScale = new Vector3(0.08f, 0.24f, 0.08f);
            var leftArmCollider = leftArmObject.GetComponent<Collider>();
            if (leftArmCollider != null)
            {
                Destroy(leftArmCollider);
            }

            var rightArmObject = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            rightArmObject.name = uid + "-RightArm";
            rightArmObject.transform.SetParent(parent, false);
            rightArmObject.transform.localPosition = new Vector3(0.34f, 1.03f, 0f);
            rightArmObject.transform.localRotation = Quaternion.Euler(0f, 0f, -78f);
            rightArmObject.transform.localScale = new Vector3(0.08f, 0.24f, 0.08f);
            var rightArmCollider = rightArmObject.GetComponent<Collider>();
            if (rightArmCollider != null)
            {
                Destroy(rightArmCollider);
            }

            leftArmRenderer = leftArmObject.GetComponent<Renderer>();
            if (leftArmRenderer != null)
            {
                leftArmRenderer.sharedMaterial = bodyRenderer != null ? bodyRenderer.sharedMaterial : ResolveShirtMaterial(teamId, number);
            }

            rightArmRenderer = rightArmObject.GetComponent<Renderer>();
            if (rightArmRenderer != null)
            {
                rightArmRenderer.sharedMaterial = bodyRenderer != null ? bodyRenderer.sharedMaterial : ResolveShirtMaterial(teamId, number);
            }

            var shortsObject = GameObject.CreatePrimitive(PrimitiveType.Cube);
            shortsObject.name = uid + "-Shorts";
            shortsObject.transform.SetParent(parent, false);
            shortsObject.transform.localPosition = new Vector3(0f, 0.5f, 0f);
            shortsObject.transform.localScale = new Vector3(0.46f, 0.18f, 0.28f);
            var shortsCollider = shortsObject.GetComponent<Collider>();
            if (shortsCollider != null)
            {
                Destroy(shortsCollider);
            }

            shortsRenderer = shortsObject.GetComponent<Renderer>();
            if (shortsRenderer != null)
            {
                shortsRenderer.sharedMaterial = ResolveShortsMaterial(teamId, number);
            }

            var leftLegObject = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            leftLegObject.name = uid + "-LeftLeg";
            leftLegObject.transform.SetParent(parent, false);
            leftLegObject.transform.localPosition = new Vector3(-0.12f, 0.2f, 0f);
            leftLegObject.transform.localScale = new Vector3(0.09f, 0.28f, 0.09f);
            var leftLegCollider = leftLegObject.GetComponent<Collider>();
            if (leftLegCollider != null)
            {
                Destroy(leftLegCollider);
            }

            var rightLegObject = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            rightLegObject.name = uid + "-RightLeg";
            rightLegObject.transform.SetParent(parent, false);
            rightLegObject.transform.localPosition = new Vector3(0.12f, 0.2f, 0f);
            rightLegObject.transform.localScale = new Vector3(0.09f, 0.28f, 0.09f);
            var rightLegCollider = rightLegObject.GetComponent<Collider>();
            if (rightLegCollider != null)
            {
                Destroy(rightLegCollider);
            }

            leftLegRenderer = leftLegObject.GetComponent<Renderer>();
            if (leftLegRenderer != null)
            {
                leftLegRenderer.sharedMaterial = ResolveSockMaterial(teamId, number);
            }

            rightLegRenderer = rightLegObject.GetComponent<Renderer>();
            if (rightLegRenderer != null)
            {
                rightLegRenderer.sharedMaterial = ResolveSockMaterial(teamId, number);
            }
        }

        private Renderer CreateKitShell(
            Transform parent,
            string uid,
            string teamId,
            int number,
            out Renderer shortsRenderer,
            out Renderer leftLegRenderer,
            out Renderer rightLegRenderer,
            out Renderer leftArmRenderer,
            out Renderer rightArmRenderer)
        {
            var shirtMaterial = ResolveShirtMaterial(teamId, number);
            var trimMaterial = ResolveTrimMaterial(teamId, number);
            var shortsMaterial = ResolveShortsMaterial(teamId, number);
            var sockMaterial = ResolveSockMaterial(teamId, number);

            var torso = CreateVisualPrimitive(parent, PrimitiveType.Cube, uid + "-Jersey", new Vector3(0f, 1.03f, 0f), Quaternion.identity, new Vector3(0.54f, 0.64f, 0.28f), shirtMaterial);
            CreateVisualPrimitive(parent, PrimitiveType.Cube, uid + "-Collar", new Vector3(0f, 1.34f, 0.05f), Quaternion.identity, new Vector3(0.2f, 0.06f, 0.22f), trimMaterial);
            leftArmRenderer = CreateVisualPrimitive(parent, PrimitiveType.Cube, uid + "-LeftSleeve", new Vector3(-0.34f, 1.06f, 0f), Quaternion.Euler(0f, 0f, 25f), new Vector3(0.14f, 0.34f, 0.16f), shirtMaterial);
            rightArmRenderer = CreateVisualPrimitive(parent, PrimitiveType.Cube, uid + "-RightSleeve", new Vector3(0.34f, 1.06f, 0f), Quaternion.Euler(0f, 0f, -25f), new Vector3(0.14f, 0.34f, 0.16f), shirtMaterial);

            CreateVisualPrimitive(parent, PrimitiveType.Cube, uid + "-LeftSleeveTrim", new Vector3(-0.42f, 1.08f, 0f), Quaternion.Euler(0f, 0f, 25f), new Vector3(0.05f, 0.16f, 0.18f), trimMaterial);
            CreateVisualPrimitive(parent, PrimitiveType.Cube, uid + "-RightSleeveTrim", new Vector3(0.42f, 1.08f, 0f), Quaternion.Euler(0f, 0f, -25f), new Vector3(0.05f, 0.16f, 0.18f), trimMaterial);

            shortsRenderer = CreateVisualPrimitive(parent, PrimitiveType.Cube, uid + "-Shorts", new Vector3(0f, 0.62f, 0f), Quaternion.identity, new Vector3(0.5f, 0.22f, 0.28f), shortsMaterial);
            leftLegRenderer = CreateVisualPrimitive(parent, PrimitiveType.Cylinder, uid + "-LeftSock", new Vector3(-0.14f, 0.28f, 0f), Quaternion.identity, new Vector3(0.08f, 0.28f, 0.08f), sockMaterial);
            rightLegRenderer = CreateVisualPrimitive(parent, PrimitiveType.Cylinder, uid + "-RightSock", new Vector3(0.14f, 0.28f, 0f), Quaternion.identity, new Vector3(0.08f, 0.28f, 0.08f), sockMaterial);
            CreateVisualPrimitive(parent, PrimitiveType.Cube, uid + "-LeftBoot", new Vector3(-0.14f, 0.05f, 0.06f), Quaternion.identity, new Vector3(0.12f, 0.05f, 0.2f), bootMaterial);
            CreateVisualPrimitive(parent, PrimitiveType.Cube, uid + "-RightBoot", new Vector3(0.14f, 0.05f, 0.06f), Quaternion.identity, new Vector3(0.12f, 0.05f, 0.2f), bootMaterial);

            CreateNumberMesh(parent, uid + "-FrontNumber", number.ToString(), new Vector3(0f, 1.02f, 0.15f), Quaternion.Euler(18f, 180f, 0f), 0.08f, TextAnchor.MiddleCenter);
            CreateNumberMesh(parent, uid + "-BackNumber", number.ToString(), new Vector3(0f, 1.04f, -0.15f), Quaternion.Euler(18f, 0f, 0f), 0.1f, TextAnchor.MiddleCenter);
            return torso;
        }

        private Renderer CreateVisualPrimitive(
            Transform parent,
            PrimitiveType primitiveType,
            string name,
            Vector3 localPosition,
            Quaternion localRotation,
            Vector3 localScale,
            Material material)
        {
            var primitive = GameObject.CreatePrimitive(primitiveType);
            primitive.name = name;
            primitive.transform.SetParent(parent, false);
            primitive.transform.localPosition = localPosition;
            primitive.transform.localRotation = localRotation;
            primitive.transform.localScale = localScale;
            var collider = primitive.GetComponent<Collider>();
            if (collider != null)
            {
                Destroy(collider);
            }

            var renderer = primitive.GetComponent<Renderer>();
            if (renderer != null)
            {
                renderer.sharedMaterial = material;
                renderer.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                renderer.receiveShadows = false;
            }

            return renderer;
        }

        private Renderer CreateGroundDisc(Transform parent, string name, Vector3 localPosition, Vector3 localScale, Material material)
        {
            var disc = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            disc.name = name;
            disc.transform.SetParent(parent, false);
            disc.transform.localPosition = localPosition;
            disc.transform.localRotation = Quaternion.identity;
            disc.transform.localScale = localScale;

            var collider = disc.GetComponent<Collider>();
            if (collider != null)
            {
                Destroy(collider);
            }

            var renderer = disc.GetComponent<Renderer>();
            if (renderer != null)
            {
                renderer.sharedMaterial = material;
                renderer.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                renderer.receiveShadows = false;
            }

            return renderer;
        }

        private void CreateNumberMesh(
            Transform parent,
            string name,
            string text,
            Vector3 localPosition,
            Quaternion localRotation,
            float characterSize,
            TextAnchor anchor)
        {
            var numberObject = new GameObject(name);
            numberObject.transform.SetParent(parent, false);
            numberObject.transform.localPosition = localPosition;
            numberObject.transform.localRotation = localRotation;
            var mesh = numberObject.AddComponent<TextMesh>();
            mesh.text = text;
            mesh.font = ResolveUiFont(32);
            mesh.fontSize = 32;
            mesh.characterSize = characterSize;
            mesh.anchor = anchor;
            mesh.alignment = TextAlignment.Center;
            mesh.color = numberMaterial != null ? numberMaterial.color : Color.white;
            var renderer = numberObject.GetComponent<MeshRenderer>();
            if (renderer != null)
            {
                renderer.sharedMaterial = mesh.font != null ? mesh.font.material : numberMaterial;
                renderer.sortingOrder = 2;
            }
        }

        private void RemoveCollidersRecursive(GameObject root)
        {
            if (root == null)
            {
                return;
            }

            var colliders = root.GetComponentsInChildren<Collider>(true);
            for (var index = 0; index < colliders.Length; index += 1)
            {
                if (colliders[index] != null)
                {
                    Destroy(colliders[index]);
                }
            }
        }

        private void FitVisualHeight(Transform visualRoot, Renderer[] renderers, float targetHeight)
        {
            if (visualRoot == null || renderers == null || renderers.Length == 0)
            {
                return;
            }

            var bounds = renderers[0].bounds;
            for (var index = 1; index < renderers.Length; index += 1)
            {
                if (renderers[index] != null)
                {
                    bounds.Encapsulate(renderers[index].bounds);
                }
            }

            var currentHeight = Mathf.Max(0.01f, bounds.size.y);
            var scale = targetHeight / currentHeight;
            visualRoot.localScale = Vector3.one * scale;
        }

        private void CenterVisualOnFeet(Transform visualRoot, Renderer[] renderers)
        {
            if (visualRoot == null || renderers == null || renderers.Length == 0)
            {
                return;
            }

            var bounds = renderers[0].bounds;
            for (var index = 1; index < renderers.Length; index += 1)
            {
                if (renderers[index] != null)
                {
                    bounds.Encapsulate(renderers[index].bounds);
                }
            }

            var localOffset = visualRoot.InverseTransformPoint(new Vector3(bounds.center.x, bounds.min.y, bounds.center.z));
            visualRoot.localPosition -= localOffset;
        }

        private Material ResolveShirtMaterial(string teamId, int number)
        {
            if (number == 1)
            {
                return keeperMaterial;
            }

            return string.Equals(teamId, "home", StringComparison.OrdinalIgnoreCase)
                ? homeMaterial
                : awayMaterial;
        }

        private Material ResolveShortsMaterial(string teamId, int number)
        {
            if (number == 1)
            {
                return keeperShortsMaterial;
            }

            return string.Equals(teamId, "home", StringComparison.OrdinalIgnoreCase)
                ? homeShortsMaterial
                : awayShortsMaterial;
        }

        private Material ResolveSockMaterial(string teamId, int number)
        {
            if (number == 1)
            {
                return keeperSockMaterial;
            }

            return string.Equals(teamId, "home", StringComparison.OrdinalIgnoreCase)
                ? homeSockMaterial
                : awaySockMaterial;
        }

        private Material ResolveTrimMaterial(string teamId, int number)
        {
            if (number == 1)
            {
                return keeperTrimMaterial;
            }

            return string.Equals(teamId, "home", StringComparison.OrdinalIgnoreCase)
                ? homeTrimMaterial
                : awayTrimMaterial;
        }

        private Vector3 ResolveFormationPosition(string teamId, int number)
        {
            Vector3 homePosition;
            switch (number)
            {
                case 1:
                    homePosition = new Vector3(-47f, PlayerY, 0f);
                    break;
                case 2:
                    homePosition = new Vector3(-31f, PlayerY, -23f);
                    break;
                case 3:
                    homePosition = new Vector3(-31f, PlayerY, 23f);
                    break;
                case 4:
                    homePosition = new Vector3(-35f, PlayerY, -8f);
                    break;
                case 5:
                    homePosition = new Vector3(-35f, PlayerY, 8f);
                    break;
                case 6:
                    homePosition = new Vector3(-18f, PlayerY, 0f);
                    break;
                case 7:
                    homePosition = new Vector3(-4f, PlayerY, -10f);
                    break;
                case 8:
                    homePosition = new Vector3(-4f, PlayerY, 10f);
                    break;
                case 9:
                    homePosition = new Vector3(20f, PlayerY, 0f);
                    break;
                case 10:
                    homePosition = new Vector3(12f, PlayerY, 22f);
                    break;
                case 11:
                    homePosition = new Vector3(12f, PlayerY, -22f);
                    break;
                default:
                    homePosition = Vector3.zero;
                    break;
            }

            if (string.Equals(teamId, "away", StringComparison.OrdinalIgnoreCase))
            {
                homePosition.x *= -1f;
            }

            return homePosition;
        }

        private bool TryResolvePlayer(string uid, out GtexIllusionPlayer player)
        {
            player = null;
            if (string.IsNullOrWhiteSpace(uid))
            {
                Debug.LogWarning("[GTEX Illusion] Missing player uid.");
                return false;
            }

            if (playersByUid.TryGetValue(uid.Trim(), out player) && player != null && player.Transform != null)
            {
                return true;
            }

            Debug.LogWarning("[GTEX Illusion] Unknown player uid: " + uid);
            return false;
        }

        private Vector3 ResolveThroughPassPoint(GtexIllusionPlayer passer, GtexIllusionPlayer receiver)
        {
            var direction = ResolveAttackDirection(passer.TeamId);
            var widthNudge = Mathf.Sign(receiver.Transform.position.z == 0f ? 1f : receiver.Transform.position.z) * 1.8f;
            return receiver.Transform.position + direction * 8f + Vector3.forward * widthNudge;
        }

        private Vector3 ResolveShotTarget(string teamId, string outcome)
        {
            var goal = ResolveGoalCenter(teamId);
            var zOffset = string.Equals(outcome, "goal", StringComparison.OrdinalIgnoreCase) ? 1.4f : 3.6f;
            goal.z += string.Equals(teamId, "home", StringComparison.OrdinalIgnoreCase) ? zOffset : -zOffset;
            return goal;
        }

        private string EvaluateShotOutcome(GtexIllusionPlayer shooter)
        {
            var distance = Vector3.Distance(shooter.Transform.position, ResolveGoalCenter(shooter.TeamId));
            return distance <= 20f ? "goal" : "save";
        }

        private Vector3 ResolveGoalCenter(string attackingTeamId)
        {
            return string.Equals(attackingTeamId, "away", StringComparison.OrdinalIgnoreCase)
                ? new Vector3(-PitchLength * 0.5f, BallY, 0f)
                : new Vector3(PitchLength * 0.5f, BallY, 0f);
        }

        private static string ResolveOpponentTeam(string teamId)
        {
            return string.Equals(teamId, "away", StringComparison.OrdinalIgnoreCase) ? "home" : "away";
        }

        private static Vector3 ResolveAttackDirection(string teamId)
        {
            return string.Equals(teamId, "away", StringComparison.OrdinalIgnoreCase) ? Vector3.left : Vector3.right;
        }

        private Vector3 BallPointForPlayerAt(GtexIllusionPlayer player, Vector3 playerPosition)
        {
            var forward = player != null && player.Transform != null
                ? player.Transform.forward
                : Vector3.forward;
            var point = playerPosition + forward * 0.58f;
            point.y = BallY;
            return ClampToPitch(point);
        }

        private void PlaceBallAtFeet(GtexIllusionPlayer player)
        {
            if (ball == null || player == null || player.Transform == null)
            {
                return;
            }

            ball.position = BallPointForPlayerAt(player, player.Transform.position);
        }

        private void FaceTowards(Transform subject, Vector3 target)
        {
            if (subject == null)
            {
                return;
            }

            var direction = target - subject.position;
            direction.y = 0f;
            if (direction.sqrMagnitude <= 0.0001f)
            {
                return;
            }

            subject.rotation = Quaternion.LookRotation(direction.normalized, Vector3.up);
        }

        private Vector3 ClampToPitch(Vector3 position)
        {
            position.x = Mathf.Clamp(position.x, -PitchLength * 0.48f, PitchLength * 0.48f);
            position.z = Mathf.Clamp(position.z, -PitchWidth * 0.48f, PitchWidth * 0.48f);
            return position;
        }

        private void UpdateBroadcastCamera(bool snap = false)
        {
            var targetFocus = ResolveActionFocusPoint();
            if (!snap && Time.time > cameraPresetHoldUntil)
            {
                currentCameraPreset = IllusionCameraPreset.Broadcast;
            }

            targetFocus.y = 0f;
            cameraFocus = snap
                ? targetFocus
                : Vector3.SmoothDamp(cameraFocus, targetFocus, ref cameraFocusVelocity, 0.25f);

            var desiredOffset = ResolveCameraOffset(currentCameraPreset, targetFocus);
            currentCameraOffset = snap
                ? desiredOffset
                : Vector3.SmoothDamp(currentCameraOffset, desiredOffset, ref currentCameraOffsetVelocity, 0.22f);
            matchCamera.fieldOfView = Mathf.Lerp(matchCamera.fieldOfView, ResolveCameraFov(currentCameraPreset), snap ? 1f : 0.12f);
            var desiredPosition = cameraFocus + currentCameraOffset;
            matchCamera.transform.position = desiredPosition;
            matchCamera.transform.LookAt(cameraFocus + Vector3.up * 1.2f);

            if (crowdLoopSource != null)
            {
                var targetVolume = Time.time < celebrationCrowdBoostUntil ? 0.32f : 0.2f;
                crowdLoopSource.volume = Mathf.Lerp(crowdLoopSource.volume, targetVolume, snap ? 1f : 0.08f);
            }
        }

        private void UpdateUi(string commentary, string overlay = "")
        {
            if (!string.IsNullOrWhiteSpace(overlay))
            {
                currentOverlay = overlay.Trim();
            }

            if (scoreText != null)
            {
                scoreText.text = homeDisplayName + "  " + homeScore + " - " + awayScore + "  " + awayDisplayName;
            }

            if (competitionText != null)
            {
                competitionText.text = string.IsNullOrWhiteSpace(currentMatchLabel) ? "GTEX PREMIER LEAGUE" : currentMatchLabel;
            }

            if (clockText != null)
            {
                clockText.text = Mathf.Clamp(Mathf.RoundToInt(currentMinute), 0, 90).ToString("00") + "'";
            }

            if (commentaryText != null)
            {
                commentaryText.text = string.IsNullOrWhiteSpace(commentary) ? "GTEX match playback" : commentary;
            }

            if (overlayText != null)
            {
                overlayText.text = currentOverlay;
            }

            if (lowerThirdTickerText != null)
            {
                lowerThirdTickerText.text = BuildLowerThirdTicker();
            }

            if (venueInfoText != null)
            {
                venueInfoText.text = currentWeatherLabel + "\n" + currentCrowdLabel;
            }

            UpdatePlayerCard();
            UpdateStatsPanel();
            UpdateLiveFeedPanel();
            UpdateSourceStatus();
        }

        private void UpdatePlayerReadabilityVisuals()
        {
            for (var index = 0; index < players.Count; index += 1)
            {
                var player = players[index];
                if (player == null || player.Transform == null)
                {
                    continue;
                }

                var pitchPosition = new Vector3(player.Transform.position.x, 0.035f, player.Transform.position.z);
                if (player.GroundShadowTransform != null)
                {
                    player.GroundShadowTransform.position = pitchPosition;
                    player.GroundShadowTransform.rotation = Quaternion.identity;
                }

                var isActive = string.Equals(player.Uid, currentBallOwnerUid, StringComparison.OrdinalIgnoreCase) ||
                    activeActorUids.Contains(player.Uid);
                if (player.ActiveMarkerRenderer != null)
                {
                    player.ActiveMarkerRenderer.enabled = isActive;
                }

                if (player.ActiveMarkerTransform != null)
                {
                    player.ActiveMarkerTransform.position = new Vector3(player.Transform.position.x, 0.04f, player.Transform.position.z);
                    player.ActiveMarkerTransform.rotation = Quaternion.identity;
                }
            }
        }

        private void UpdateEventFlashVisuals()
        {
            if (eventFlashImage == null || eventFlashText == null)
            {
                return;
            }

            var remaining = eventFlashUntil - Time.time;
            if (remaining <= 0f)
            {
                eventFlashImage.color = Color.clear;
                eventFlashText.color = Color.clear;
                return;
            }

            var fadeLength = Mathf.Max(0.01f, eventFlashUntil - eventFlashFadeStart);
            var alpha = Time.time < eventFlashFadeStart
                ? 1f
                : Mathf.Clamp01(remaining / fadeLength);
            var panelColor = eventFlashColor;
            panelColor.a *= alpha;
            eventFlashImage.color = panelColor;

            var textColor = Color.white;
            textColor.a = Mathf.Clamp01(alpha * 0.95f);
            eventFlashText.color = textColor;
        }

        private string BuildLowerThirdTicker()
        {
            var possession = "Possession " + homeDisplayName + " " + ResolvePossessionShare("home") + "%";
            var score = homeDisplayName + " " + homeScore + " - " + awayScore + " " + awayDisplayName;
            var shots = "Shots " + ResolveCount(teamShotCounts, "home") + " - " + ResolveCount(teamShotCounts, "away");
            var latest = liveFeedLines.Count > 0 ? liveFeedLines[0] : "GTEX live match feed";
            return "GTEX LIVE | " + score + " | " + possession + " | " + shots + " | " + latest;
        }

        private string ResolveBroadcastOverlay(GtexIllusionScene scene)
        {
            if (scene == null)
            {
                return currentOverlay;
            }

            var teamName = string.Equals(scene.TeamId, "away", StringComparison.OrdinalIgnoreCase)
                ? awayDisplayName
                : homeDisplayName;
            switch (scene.SceneKind)
            {
                case GtexIllusionSceneKind.GoalScene:
                    return "GOAL | " + teamName;
                case GtexIllusionSceneKind.ShotScene:
                    return "SHOT | " + teamName;
                case GtexIllusionSceneKind.SaveScene:
                    return "SAVE | KEEPER";
                case GtexIllusionSceneKind.TackleScene:
                    return "TACKLE WON";
                case GtexIllusionSceneKind.FoulScene:
                    return "FOUL";
                default:
                    return string.IsNullOrWhiteSpace(scene.Overlay) ? currentOverlay : scene.Overlay;
            }
        }

        private void TriggerEventFlash(GtexIllusionScene scene, bool forceGoal = false)
        {
            if (scene == null || eventFlashImage == null || eventFlashText == null)
            {
                return;
            }

            var overlay = ResolveBroadcastOverlay(scene);
            var duration = 0f;
            var color = Color.clear;
            switch (scene.SceneKind)
            {
                case GtexIllusionSceneKind.GoalScene:
                    duration = 1.35f;
                    color = new Color(0.75f, 0.05f, 0.02f, 0.48f);
                    break;
                case GtexIllusionSceneKind.ShotScene:
                    duration = 0.55f;
                    color = new Color(1f, 0.58f, 0.02f, 0.24f);
                    break;
                case GtexIllusionSceneKind.SaveScene:
                    duration = 0.55f;
                    color = new Color(0.08f, 0.55f, 0.95f, 0.22f);
                    break;
                case GtexIllusionSceneKind.TackleScene:
                    duration = 0.45f;
                    color = new Color(0.15f, 0.28f, 0.9f, 0.2f);
                    break;
                case GtexIllusionSceneKind.FoulScene:
                    duration = 0.65f;
                    color = new Color(0.9f, 0.04f, 0.03f, 0.28f);
                    break;
            }

            if (duration <= 0f && !forceGoal)
            {
                return;
            }

            if (forceGoal && duration <= 0f)
            {
                duration = 1.35f;
                color = new Color(0.75f, 0.05f, 0.02f, 0.48f);
            }

            eventFlashText.text = overlay;
            eventFlashColor = color;
            eventFlashUntil = Time.time + duration;
            eventFlashFadeStart = eventFlashUntil - Mathf.Min(0.35f, duration * 0.45f);
            UpdateEventFlashVisuals();
        }

        private void UpdateSourceStatus()
        {
            if (sourceStatusText == null)
            {
                return;
            }

            var label = selectedSourceMode == GtexIllusionSourceMode.FilePath
                ? "File"
                : selectedSourceMode == GtexIllusionSourceMode.RemoteUrl
                    ? "API"
                    : "Sample";
            sourceStatusText.text = "Source: " + label;
        }

        private void UpdatePlayerCard()
        {
            if (playerCardText == null)
            {
                return;
            }

            if (scenePackage != null &&
                scenePackage.playerCard != null &&
                !string.IsNullOrWhiteSpace(scenePackage.playerCard.playerName))
            {
                var packageCard = scenePackage.playerCard;
                var header = packageCard.shirtNumber > 0
                    ? "#" + packageCard.shirtNumber + " " + packageCard.playerName
                    : packageCard.playerName;
                var ratingLine = packageCard.rating > 0f ? "\nRating  " + packageCard.rating.ToString("0.0") : string.Empty;
                playerCardText.text =
                    header +
                    "\n" +
                    FirstNonEmpty(packageCard.teamName, homeDisplayName) +
                    (string.IsNullOrWhiteSpace(packageCard.role) ? string.Empty : "\n" + packageCard.role) +
                    ratingLine +
                    (string.IsNullOrWhiteSpace(packageCard.summary) ? string.Empty : "\n" + packageCard.summary);
                return;
            }

            if (TryResolvePlayer(currentBallOwnerUid, out var owner))
            {
                var teamName = owner.TeamId == "home" ? homeDisplayName : awayDisplayName;
                var teamPasses = ResolveCount(teamPassCounts, owner.TeamId);
                var teamShots = ResolveCount(teamShotCounts, owner.TeamId);
                playerCardText.text =
                    "IN POSSESSION" +
                    "\n#" + owner.Number + "  " + teamName.ToUpperInvariant() +
                    "\nPasses " + teamPasses + "   Shots " + teamShots +
                    "\n" + ResolveSourceLabel().ToUpperInvariant() + " FEED";
                return;
            }

            playerCardText.text = "GTEX Spotlight\nBroadcast player card\nWaiting for active actor";
        }

        private void UpdateStatsPanel()
        {
            if (statsPanelText == null)
            {
                return;
            }

            if (scenePackage != null && scenePackage.stats != null && scenePackage.stats.Length > 0)
            {
                var lines = new List<string> { "MATCH STATS" };
                for (var index = 0; index < scenePackage.stats.Length; index += 1)
                {
                    var stat = scenePackage.stats[index];
                    if (stat == null || string.IsNullOrWhiteSpace(stat.label))
                    {
                        continue;
                    }

                    lines.Add(stat.label + "  " + stat.homeValue + " - " + stat.awayValue);
                }

                statsPanelText.text = string.Join("\n", lines.ToArray());
                return;
            }

            statsPanelText.text =
                "MATCH STATS\n" +
                homeDisplayName + " vs " + awayDisplayName + "\n" +
                "Possession  " + ResolvePossessionShare("home") + "% - " + ResolvePossessionShare("away") + "%\n" +
                "Passes      " + ResolveCount(teamPassCounts, "home") + " - " + ResolveCount(teamPassCounts, "away") + "\n" +
                "Shots       " + ResolveCount(teamShotCounts, "home") + " - " + ResolveCount(teamShotCounts, "away") + "\n" +
                "Saves       " + ResolveCount(teamSaveCounts, "home") + " - " + ResolveCount(teamSaveCounts, "away") + "\n" +
                "Match ID    " + ResolvePlaybackMatchId();
        }

        private void UpdateLiveFeedPanel()
        {
            if (liveFeedText == null)
            {
                return;
            }

            if (liveFeedLines.Count == 0)
            {
                liveFeedText.text = "No storylines yet.\nThe broadcast feed will populate as scenes play.";
                return;
            }

            liveFeedText.text = string.Join("\n\n", liveFeedLines.ToArray());
        }

        private void SelectSampleSource()
        {
            selectedSourceMode = GtexIllusionSourceMode.SampleResource;
            ReloadSelectedSource();
        }

        private void SelectFileSource()
        {
            selectedSourceMode = GtexIllusionSourceMode.FilePath;
            ReloadSelectedSource();
        }

        private void SelectRemoteSource()
        {
            selectedSourceMode = GtexIllusionSourceMode.RemoteUrl;
            ReloadSelectedSource();
        }

        private void ReloadSelectedSource()
        {
            StopPlaybackForReload();

            if (selectedSourceMode == GtexIllusionSourceMode.RemoteUrl)
            {
                var url = ResolveRemoteTimelineUrl();
                if (string.IsNullOrWhiteSpace(url))
                {
                    timelineSource = "remote:missing";
                    timelineValidationSummary = "No API URL configured.";
                    UpdateUi("API source not configured.");
                    return;
                }

                bootstrappingRemoteTimeline = true;
                StartCoroutine(BootstrapRemoteTimelineAndPlay(url.Trim()));
                return;
            }

            timeline = null;
            scenePackage = null;
            playbackScenes = Array.Empty<GtexIllusionScene>();
            PrepareTimeline();
            ResetMatchVisuals();
            UpdateUi("Reloaded " + ResolveSourceLabel() + " timeline.");

            if (playbackScenes != null && playbackScenes.Length > 0)
            {
                playbackRoutine = StartCoroutine(PlayTimelineRoutine());
            }
        }

        private void StopPlaybackForReload()
        {
            if (playbackRoutine != null)
            {
                StopCoroutine(playbackRoutine);
                playbackRoutine = null;
            }

            StopAllCoroutines();
            bootstrappingRemoteTimeline = false;
            playbackStarted = true;
        }

        private string ResolveSourceLabel()
        {
            switch (selectedSourceMode)
            {
                case GtexIllusionSourceMode.FilePath:
                    return "file";
                case GtexIllusionSourceMode.RemoteUrl:
                    return "API";
                default:
                    return "sample";
            }
        }

        private void SetCameraPresetForScene(GtexIllusionScene scene)
        {
            if (scene == null)
            {
                return;
            }

            var sceneX = ResolveSceneFocusX(scene);
            switch (scene.SceneKind)
            {
                case GtexIllusionSceneKind.ShotScene:
                case GtexIllusionSceneKind.SaveScene:
                    currentCameraPreset = IllusionCameraPreset.AttackPush;
                    cameraPresetHoldUntil = Time.time + 1.05f;
                    break;
                case GtexIllusionSceneKind.GoalScene:
                    currentCameraPreset = IllusionCameraPreset.AttackPush;
                    cameraPresetHoldUntil = Time.time + 1.35f;
                    break;
                case GtexIllusionSceneKind.PassScene:
                case GtexIllusionSceneKind.ThroughPassScene:
                case GtexIllusionSceneKind.DribbleScene:
                    currentCameraPreset = Mathf.Abs(sceneX) > PitchLength * 0.18f
                        ? IllusionCameraPreset.AttackPush
                        : IllusionCameraPreset.MidfieldFlow;
                    cameraPresetHoldUntil = Time.time + 0.9f;
                    break;
                default:
                    currentCameraPreset = IllusionCameraPreset.Broadcast;
                    cameraPresetHoldUntil = Time.time + 0.45f;
                    break;
            }
        }

        private Vector3 ResolveCameraOffset(IllusionCameraPreset preset, Vector3 focus)
        {
            var lateralBias = Mathf.Clamp(focus.z * 0.18f, -7f, 7f);
            var depthBias = Mathf.Clamp(focus.x * 0.08f, -5f, 5f);
            switch (preset)
            {
                case IllusionCameraPreset.MidfieldFlow:
                    return new Vector3(depthBias, 44f, -62f + lateralBias * 0.16f);
                case IllusionCameraPreset.AttackPush:
                    return new Vector3(depthBias * 0.7f, 39f, -54f + lateralBias * 0.22f);
                case IllusionCameraPreset.BoxZoom:
                    return new Vector3(depthBias * 0.65f, 39f, -54f + lateralBias * 0.2f);
                case IllusionCameraPreset.GoalCelebration:
                    return new Vector3(depthBias * 0.55f, 39f, -54f + lateralBias * 0.18f);
                default:
                    return new Vector3(depthBias, 48f, -68f + lateralBias * 0.12f);
            }
        }

        private float ResolveCameraFov(IllusionCameraPreset preset)
        {
            switch (preset)
            {
                case IllusionCameraPreset.MidfieldFlow:
                    return 45f;
                case IllusionCameraPreset.AttackPush:
                    return 44f;
                case IllusionCameraPreset.BoxZoom:
                    return 44f;
                case IllusionCameraPreset.GoalCelebration:
                    return 44f;
                default:
                    return 46f;
            }
        }

        private void PlaySceneAudio(GtexIllusionScene scene)
        {
            if (effectsSource == null || scene == null)
            {
                return;
            }

            switch (scene.SceneKind)
            {
                case GtexIllusionSceneKind.PassScene:
                case GtexIllusionSceneKind.ThroughPassScene:
                    PlayEffectClip(crowdAltLoopClip, 0.08f);
                    break;
                case GtexIllusionSceneKind.ShotScene:
                    PlayEffectClip(whistleClip, 0.18f);
                    break;
                case GtexIllusionSceneKind.GoalScene:
                    PlayEffectClip(crowdGoalClip, 0.55f);
                    celebrationCrowdBoostUntil = Time.time + 2.2f;
                    break;
                case GtexIllusionSceneKind.ResetScene:
                    PlayEffectClip(whistleClip, 0.22f);
                    break;
            }
        }

        private void PlayEffectClip(AudioClip clip, float volumeScale = 1f)
        {
            if (effectsSource == null || clip == null)
            {
                return;
            }

            effectsSource.PlayOneShot(clip, Mathf.Clamp01(volumeScale));
        }

        private IEnumerator PlayCelebrationRoutine(GtexIllusionPlayer scorer, float duration)
        {
            if (scorer == null || scorer.Transform == null)
            {
                yield break;
            }

            var teammateUids = FindNearbyTeammates(scorer, 2);
            for (var index = 0; index < teammateUids.Count; index += 1)
            {
                if (TryResolvePlayer(teammateUids[index], out var teammate))
                {
                    var converge = ClampToPitch(scorer.Transform.position - ResolveAttackDirection(scorer.TeamId) * (1.4f + (index * 0.9f)));
                    converge.y = PlayerY;
                    StartCoroutine(MovePlayerRoutine(teammate.Transform, converge, Mathf.Max(0.6f, duration * 0.72f)));
                }
            }

            var start = scorer.Transform.position;
            var end = start - ResolveAttackDirection(scorer.TeamId) * 2.2f;
            end.y = PlayerY;
            var elapsed = 0f;
            while (elapsed < duration)
            {
                elapsed += Time.deltaTime;
                var t = Mathf.Clamp01(elapsed / Mathf.Max(0.01f, duration));
                var next = Vector3.Lerp(start, end, t);
                next.y += Mathf.Abs(Mathf.Sin(t * Mathf.PI * 4f)) * 0.3f;
                scorer.Transform.position = next;
                FaceTowards(scorer.Transform, end + new Vector3(0f, 0f, 2f));
                yield return null;
            }

            scorer.Transform.position = end;
        }

        private void UpdateMinimap()
        {
            if (minimapImage == null)
            {
                return;
            }

            if (minimapTexture == null)
            {
                minimapTexture = new Texture2D(168, 92, TextureFormat.RGBA32, false);
                minimapTexture.wrapMode = TextureWrapMode.Clamp;
                minimapTexture.filterMode = FilterMode.Point;
                minimapImage.texture = minimapTexture;
            }

            var pixels = new Color32[minimapTexture.width * minimapTexture.height];
            var grass = new Color32(39, 118, 44, 255);
            var line = new Color32(222, 235, 225, 255);
            for (var index = 0; index < pixels.Length; index += 1)
            {
                pixels[index] = grass;
            }

            DrawMiniLine(pixels, minimapTexture.width, minimapTexture.height, minimapTexture.width / 2, 0, minimapTexture.width / 2, minimapTexture.height - 1, line);
            DrawMiniRect(pixels, minimapTexture.width, minimapTexture.height, 2, 2, minimapTexture.width - 3, minimapTexture.height - 3, line);

            for (var index = 0; index < players.Count; index += 1)
            {
                var player = players[index];
                if (player == null || player.Transform == null)
                {
                    continue;
                }

                var point = WorldToMiniMap(player.Transform.position);
                var dot = player.TeamId == "home" ? new Color32(244, 205, 48, 255) : new Color32(71, 121, 255, 255);
                if (player.Number == 1)
                {
                    dot = new Color32(180, 118, 230, 255);
                }
                else if (activeActorUids.Contains(player.Uid))
                {
                    dot = new Color32(255, 94, 94, 255);
                }

                DrawMiniDot(pixels, minimapTexture.width, minimapTexture.height, point.x, point.y, 2, dot);
            }

            if (ball != null)
            {
                var ballPoint = WorldToMiniMap(ball.position);
                DrawMiniDot(pixels, minimapTexture.width, minimapTexture.height, ballPoint.x, ballPoint.y, 1, new Color32(255, 255, 255, 255));
            }

            minimapTexture.SetPixels32(pixels);
            minimapTexture.Apply(false, false);
        }

        private Vector2Int WorldToMiniMap(Vector3 world)
        {
            var x = Mathf.InverseLerp(-PitchLength * 0.5f, PitchLength * 0.5f, world.x);
            var y = Mathf.InverseLerp(-PitchWidth * 0.5f, PitchWidth * 0.5f, world.z);
            return new Vector2Int(
                Mathf.RoundToInt(x * (minimapTexture.width - 1)),
                Mathf.RoundToInt(y * (minimapTexture.height - 1)));
        }

        private static void DrawMiniRect(Color32[] pixels, int width, int height, int x0, int y0, int x1, int y1, Color32 color)
        {
            DrawMiniLine(pixels, width, height, x0, y0, x1, y0, color);
            DrawMiniLine(pixels, width, height, x1, y0, x1, y1, color);
            DrawMiniLine(pixels, width, height, x1, y1, x0, y1, color);
            DrawMiniLine(pixels, width, height, x0, y1, x0, y0, color);
        }

        private static void DrawMiniLine(Color32[] pixels, int width, int height, int x0, int y0, int x1, int y1, Color32 color)
        {
            var dx = Mathf.Abs(x1 - x0);
            var dy = Mathf.Abs(y1 - y0);
            var sx = x0 < x1 ? 1 : -1;
            var sy = y0 < y1 ? 1 : -1;
            var err = dx - dy;

            while (true)
            {
                if (x0 >= 0 && y0 >= 0 && x0 < width && y0 < height)
                {
                    pixels[y0 * width + x0] = color;
                }

                if (x0 == x1 && y0 == y1)
                {
                    break;
                }

                var e2 = err * 2;
                if (e2 > -dy)
                {
                    err -= dy;
                    x0 += sx;
                }

                if (e2 < dx)
                {
                    err += dx;
                    y0 += sy;
                }
            }
        }

        private static void DrawMiniDot(Color32[] pixels, int width, int height, int x, int y, int radius, Color32 color)
        {
            for (var dy = -radius; dy <= radius; dy += 1)
            {
                for (var dx = -radius; dx <= radius; dx += 1)
                {
                    var px = x + dx;
                    var py = y + dy;
                    if (px < 0 || py < 0 || px >= width || py >= height)
                    {
                        continue;
                    }

                    if ((dx * dx) + (dy * dy) <= radius * radius)
                    {
                        pixels[py * width + px] = color;
                    }
                }
            }
        }

        private Vector3 ResolveActionFocusPoint()
        {
            var hasFocus = false;
            var accumulated = Vector3.zero;
            var weight = 0f;

            if (ball != null)
            {
                accumulated += ball.position * 2.2f;
                weight += 2.2f;
                hasFocus = true;
            }

            if (TryResolvePlayer(currentBallOwnerUid, out var owner))
            {
                accumulated += owner.Transform.position * 1.5f;
                weight += 1.5f;
                hasFocus = true;
            }

            foreach (var actorUid in activeActorUids)
            {
                if (!TryResolvePlayer(actorUid, out var actor))
                {
                    continue;
                }

                accumulated += actor.Transform.position;
                weight += 1f;
                hasFocus = true;
            }

            return hasFocus && weight > 0.001f
                ? accumulated / weight
                : Vector3.zero;
        }

        private float ResolveSceneFocusX(GtexIllusionScene scene)
        {
            if (scene == null)
            {
                return 0f;
            }

            var total = 0f;
            var count = 0f;
            if (TryResolvePlayer(scene.ActorUid, out var actor))
            {
                total += actor.Transform.position.x;
                count += 1f;
            }

            if (TryResolvePlayer(scene.TargetUid, out var target))
            {
                total += target.Transform.position.x;
                count += 1f;
            }

            if (Mathf.Abs(scene.TargetX) > 0.01f)
            {
                total += scene.TargetX;
                count += 1f;
            }

            return count > 0f ? total / count : 0f;
        }

        private List<string> FindNearbyTeammates(GtexIllusionPlayer anchor, int count)
        {
            var results = new List<string>();
            if (anchor == null || anchor.Transform == null)
            {
                return results;
            }

            var candidates = new List<KeyValuePair<float, string>>();
            for (var index = 0; index < players.Count; index += 1)
            {
                var player = players[index];
                if (player == null ||
                    player.Transform == null ||
                    player.Uid == anchor.Uid ||
                    player.TeamId != anchor.TeamId ||
                    player.Number == 1)
                {
                    continue;
                }

                candidates.Add(new KeyValuePair<float, string>(
                    Vector3.SqrMagnitude(player.Transform.position - anchor.Transform.position),
                    player.Uid));
            }

            candidates.Sort((left, right) => left.Key.CompareTo(right.Key));
            for (var index = 0; index < candidates.Count && results.Count < count; index += 1)
            {
                results.Add(candidates[index].Value);
            }

            return results;
        }

        private string ResolveRemoteTimelineUrl()
        {
            var explicitUrl = GtexIllusionTimelineLoader.ResolveTimelineUrlOverride();
            if (!string.IsNullOrWhiteSpace(explicitUrl))
            {
                return explicitUrl.Trim();
            }

            if (activeConfig == null ||
                string.IsNullOrWhiteSpace(activeConfig.matchId) ||
                string.IsNullOrWhiteSpace(activeConfig.ResolveBaseUrl()))
            {
                return null;
            }

            return activeConfig.ResolveBaseUrl().TrimEnd('/') +
                   "/api/match-viewer/" +
                   UnityWebRequest.EscapeURL(activeConfig.matchId.Trim()) +
                   "/illusion";
        }

        private string ResolvePlaybackMatchId()
        {
            if (scenePackage != null && !string.IsNullOrWhiteSpace(scenePackage.matchId))
            {
                return scenePackage.matchId;
            }

            return timeline != null && !string.IsNullOrWhiteSpace(timeline.matchId)
                ? timeline.matchId
                : "illusion-sample";
        }

        private void RegisterSceneStats(GtexIllusionScene scene)
        {
            if (scene == null || string.IsNullOrWhiteSpace(scene.TeamId))
            {
                return;
            }

            switch (scene.EventKind)
            {
                case GtexIllusionEventKind.Pass:
                case GtexIllusionEventKind.ThroughPass:
                    IncrementCount(teamPassCounts, scene.TeamId);
                    break;
                case GtexIllusionEventKind.Shot:
                case GtexIllusionEventKind.Goal:
                    IncrementCount(teamShotCounts, scene.TeamId);
                    break;
                case GtexIllusionEventKind.Save:
                    IncrementCount(teamSaveCounts, scene.TeamId);
                    break;
            }
        }

        private void PushLiveFeed(GtexIllusionScene scene)
        {
            if (scene == null || string.IsNullOrWhiteSpace(scene.Commentary))
            {
                return;
            }

            liveFeedLines.Insert(0, FormatLiveFeedItem(Mathf.RoundToInt(scene.Minute), scene.EventKind.ToString(), scene.Commentary));
            while (liveFeedLines.Count > 6)
            {
                liveFeedLines.RemoveAt(liveFeedLines.Count - 1);
            }
        }

        private static string FormatLiveFeedItem(int minute, string label, string text)
        {
            var minutePrefix = minute > 0 ? minute.ToString("00") + "' " : string.Empty;
            var labelPrefix = string.IsNullOrWhiteSpace(label) ? string.Empty : label.Trim().ToUpperInvariant() + ": ";
            return minutePrefix + labelPrefix + (text ?? string.Empty).Trim();
        }

        private int ResolvePossessionShare(string teamId)
        {
            var homePasses = ResolveCount(teamPassCounts, "home");
            var awayPasses = ResolveCount(teamPassCounts, "away");
            var total = Mathf.Max(1, homePasses + awayPasses);
            var teamPasses = ResolveCount(teamPassCounts, teamId);
            return Mathf.RoundToInt((teamPasses / (float)total) * 100f);
        }

        private static int ResolveCount(Dictionary<string, int> counts, string key)
        {
            return counts != null && counts.TryGetValue(key, out var value) ? value : 0;
        }

        private static void IncrementCount(Dictionary<string, int> counts, string key)
        {
            if (counts == null || string.IsNullOrWhiteSpace(key))
            {
                return;
            }

            counts[key] = ResolveCount(counts, key) + 1;
        }

        private static string FirstNonEmpty(params string[] values)
        {
            if (values == null)
            {
                return string.Empty;
            }

            for (var index = 0; index < values.Length; index += 1)
            {
                if (!string.IsNullOrWhiteSpace(values[index]))
                {
                    return values[index].Trim();
                }
            }

            return string.Empty;
        }

        private Text CreateText(
            Transform parent,
            string name,
            Vector2 anchorMin,
            Vector2 anchorMax,
            Vector2 anchoredPosition,
            Vector2 sizeDelta,
            int fontSize,
            TextAnchor alignment)
        {
            var textObject = new GameObject("GTEX Illusion UI " + name);
            textObject.transform.SetParent(parent, false);
            var rectTransform = textObject.AddComponent<RectTransform>();
            rectTransform.anchorMin = anchorMin;
            rectTransform.anchorMax = anchorMax;
            rectTransform.pivot = new Vector2(anchorMin.x == anchorMax.x ? anchorMin.x : 0.5f, anchorMin.y == anchorMax.y ? anchorMin.y : 0.5f);
            rectTransform.anchoredPosition = anchoredPosition;
            rectTransform.sizeDelta = sizeDelta;

            var text = textObject.AddComponent<Text>();
            text.font = ResolveUiFont(fontSize);
            text.fontSize = fontSize;
            text.alignment = alignment;
            text.color = Color.white;
            text.horizontalOverflow = HorizontalWrapMode.Wrap;
            text.verticalOverflow = VerticalWrapMode.Truncate;
            return text;
        }

        private GameObject CreatePanel(
            Transform parent,
            string name,
            Vector2 anchorMin,
            Vector2 anchorMax,
            Vector2 anchoredPosition,
            Vector2 sizeDelta,
            Color color)
        {
            var panelObject = new GameObject("GTEX Illusion UI " + name);
            panelObject.transform.SetParent(parent, false);
            var rectTransform = panelObject.AddComponent<RectTransform>();
            rectTransform.anchorMin = anchorMin;
            rectTransform.anchorMax = anchorMax;
            rectTransform.pivot = new Vector2(anchorMin.x, anchorMin.y);
            rectTransform.anchoredPosition = anchoredPosition;
            rectTransform.sizeDelta = sizeDelta;

            var image = panelObject.AddComponent<Image>();
            image.color = color;
            return panelObject;
        }

        private void CreateButton(
            Transform parent,
            string label,
            Vector2 anchoredPosition,
            Vector2 sizeDelta,
            UnityEngine.Events.UnityAction onClick)
        {
            var buttonObject = new GameObject("GTEX Illusion UI Button " + label);
            buttonObject.transform.SetParent(parent, false);
            var rectTransform = buttonObject.AddComponent<RectTransform>();
            rectTransform.anchorMin = new Vector2(0f, 0f);
            rectTransform.anchorMax = new Vector2(0f, 0f);
            rectTransform.pivot = new Vector2(0f, 0f);
            rectTransform.anchoredPosition = anchoredPosition;
            rectTransform.sizeDelta = sizeDelta;

            var image = buttonObject.AddComponent<Image>();
            image.color = new Color(0.15f, 0.18f, 0.28f, 0.94f);

            var button = buttonObject.AddComponent<Button>();
            if (onClick != null)
            {
                button.onClick.AddListener(onClick);
            }

            var labelText = CreateText(
                buttonObject.transform,
                label + "Label",
                Vector2.zero,
                Vector2.one,
                Vector2.zero,
                Vector2.zero,
                15,
                TextAnchor.MiddleCenter);
            labelText.color = Color.white;
            labelText.raycastTarget = false;
        }

        private static Font ResolveUiFont(int fontSize)
        {
            var font = Resources.GetBuiltinResource<Font>("Arial.ttf");
            if (font != null)
            {
                return font;
            }

            return Font.CreateDynamicFontFromOSFont(new[] { "Arial", "Liberation Sans" }, fontSize);
        }

        private Material CreateMaterial(string name, Color color)
        {
            var shader = Shader.Find("Universal Render Pipeline/Lit");
            if (shader == null)
            {
                shader = Shader.Find("Standard");
            }

            var material = new Material(shader)
            {
                name = name,
                color = color
            };
            return material;
        }

        private Material CreateTransparentMaterial(string name, Color color)
        {
            var material = CreateMaterial(name, color);
            material.renderQueue = 3000;

            if (material.HasProperty("_Surface"))
            {
                material.SetFloat("_Surface", 1f);
            }

            if (material.HasProperty("_Blend"))
            {
                material.SetFloat("_Blend", 0f);
            }

            if (material.HasProperty("_SrcBlend"))
            {
                material.SetFloat("_SrcBlend", (float)UnityEngine.Rendering.BlendMode.SrcAlpha);
            }

            if (material.HasProperty("_DstBlend"))
            {
                material.SetFloat("_DstBlend", (float)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
            }

            if (material.HasProperty("_ZWrite"))
            {
                material.SetFloat("_ZWrite", 0f);
            }

            material.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
            return material;
        }

        private void CreateStand(Transform parent, string name, Vector3 position, Vector3 scale)
        {
            var stand = GameObject.CreatePrimitive(PrimitiveType.Cube);
            stand.name = name;
            stand.transform.SetParent(parent, false);
            stand.transform.position = position;
            stand.transform.localScale = scale;
            var renderer = stand.GetComponent<Renderer>();
            if (renderer != null)
            {
                renderer.sharedMaterial = standMaterial;
            }

            var collider = stand.GetComponent<Collider>();
            if (collider != null)
            {
                Destroy(collider);
            }

            var seatBand = GameObject.CreatePrimitive(PrimitiveType.Cube);
            seatBand.name = name + " Seats";
            seatBand.transform.SetParent(parent, false);
            seatBand.transform.position = position + new Vector3(0f, scale.y * 0.25f, 0f);
            seatBand.transform.localScale = new Vector3(scale.x * 0.96f, scale.y * 0.18f, scale.z * 0.92f);
            var seatRenderer = seatBand.GetComponent<Renderer>();
            if (seatRenderer != null)
            {
                seatRenderer.sharedMaterial = seatMaterial;
            }

            var seatCollider = seatBand.GetComponent<Collider>();
            if (seatCollider != null)
            {
                Destroy(seatCollider);
            }
        }

        private void CreateBackdropBand(Transform parent, string name, Vector3 position, Vector3 scale)
        {
            var band = GameObject.CreatePrimitive(PrimitiveType.Cube);
            band.name = name;
            band.transform.SetParent(parent, false);
            band.transform.position = position;
            band.transform.localScale = scale;
            var renderer = band.GetComponent<Renderer>();
            if (renderer != null)
            {
                renderer.sharedMaterial = seatMaterial != null ? seatMaterial : standMaterial;
            }

            var collider = band.GetComponent<Collider>();
            if (collider != null)
            {
                Destroy(collider);
            }
        }

        private void CreateTunnel(Transform parent, Vector3 position, Vector3 scale)
        {
            var tunnel = GameObject.CreatePrimitive(PrimitiveType.Cube);
            tunnel.name = "GTEX Illusion Tunnel";
            tunnel.transform.SetParent(parent, false);
            tunnel.transform.position = position;
            tunnel.transform.localScale = scale;
            var renderer = tunnel.GetComponent<Renderer>();
            if (renderer != null)
            {
                renderer.sharedMaterial = tunnelMaterial;
            }

            var collider = tunnel.GetComponent<Collider>();
            if (collider != null)
            {
                Destroy(collider);
            }
        }

        private void CreateAdBoardRing(Transform parent)
        {
            CreateAdBoard(parent, "AdBoard North", new Vector3(0f, 0.34f, -PitchWidth * 0.5f - 2.6f), new Vector3(PitchLength - 12f, 0.46f, 0.08f), "GTEX");
            CreateAdBoard(parent, "AdBoard South", new Vector3(0f, 0.34f, PitchWidth * 0.5f + 2.6f), new Vector3(PitchLength - 12f, 0.46f, 0.08f), "PLAY YOUR LEGACY");
        }

        private void CreateAdBoard(Transform parent, string name, Vector3 position, Vector3 scale, string label)
        {
            var board = GameObject.CreatePrimitive(PrimitiveType.Cube);
            board.name = name;
            board.transform.SetParent(parent, false);
            board.transform.position = position;
            board.transform.localScale = scale;
            var renderer = board.GetComponent<Renderer>();
            if (renderer != null)
            {
                renderer.sharedMaterial = adBoardMaterial;
            }

            var collider = board.GetComponent<Collider>();
            if (collider != null)
            {
                Destroy(collider);
            }

            var textObject = new GameObject(name + " Label");
            textObject.transform.SetParent(board.transform, false);
            textObject.transform.localPosition = scale.x > scale.z
                ? new Vector3(0f, 0.02f, -0.11f)
                : new Vector3(-0.11f, 0.02f, 0f);
            textObject.transform.localRotation = scale.x > scale.z
                ? Quaternion.Euler(0f, 0f, 0f)
                : Quaternion.Euler(0f, 90f, 0f);
            var mesh = textObject.AddComponent<TextMesh>();
            mesh.text = label;
            mesh.font = ResolveUiFont(24);
            mesh.fontSize = 24;
            mesh.characterSize = 0.06f;
            mesh.anchor = TextAnchor.MiddleCenter;
            mesh.alignment = TextAlignment.Center;
            mesh.color = Color.white;
            var meshRenderer = textObject.GetComponent<MeshRenderer>();
            if (meshRenderer != null && mesh.font != null)
            {
                meshRenderer.sharedMaterial = mesh.font.material;
            }
        }

        private void PopulateCrowdRows(Transform parent, float edgeCoordinate, bool isEndStand, int countPerRow, int rowCount)
        {
            for (var row = 0; row < rowCount; row += 1)
            {
                for (var index = 0; index < countPerRow; index += 1)
                {
                    var prefab = Resources.Load<GameObject>(FreeCharacterResourceNames[(index + (row * 3)) % FreeCharacterResourceNames.Length]);
                    if (prefab == null)
                    {
                        continue;
                    }

                    var spectator = Instantiate(prefab, parent, false);
                    spectator.name = "GTEX Spectator " + row + "-" + index;
                    RemoveCollidersRecursive(spectator);

                    var lateral = isEndStand
                        ? Mathf.Lerp(-PitchWidth * 0.44f, PitchWidth * 0.44f, countPerRow <= 1 ? 0.5f : index / (float)(countPerRow - 1))
                        : Mathf.Lerp(-PitchLength * 0.46f, PitchLength * 0.46f, countPerRow <= 1 ? 0.5f : index / (float)(countPerRow - 1));
                    var depth = row * 1.7f;

                    spectator.transform.localPosition = isEndStand
                        ? new Vector3(edgeCoordinate, 4.7f + row * 1.05f, lateral)
                        : new Vector3(lateral, 4.7f + row * 1.05f, edgeCoordinate);
                    spectator.transform.localRotation = isEndStand
                        ? Quaternion.Euler(0f, edgeCoordinate < 0f ? 90f : -90f, 0f)
                        : Quaternion.Euler(0f, edgeCoordinate < 0f ? 0f : 180f, 0f);

                    var renderers = spectator.GetComponentsInChildren<Renderer>(true);
                    FitVisualHeight(spectator.transform, renderers, 0.9f);
                    if (isEndStand)
                    {
                        spectator.transform.localPosition += new Vector3(edgeCoordinate < 0f ? -depth : depth, 0f, 0f);
                    }
                    else
                    {
                        spectator.transform.localPosition += new Vector3(0f, 0f, edgeCoordinate < 0f ? -depth : depth);
                    }
                }
            }
        }

        private void CreatePitchStripes(Transform parent)
        {
            const int stripeCount = 10;
            var stripeLength = PitchLength / stripeCount;
            for (var index = 0; index < stripeCount; index += 1)
            {
                if ((index % 2) == 0)
                {
                    continue;
                }

                var stripe = GameObject.CreatePrimitive(PrimitiveType.Cube);
                stripe.name = "GTEX Illusion Pitch Stripe " + index;
                stripe.transform.SetParent(parent, false);
                stripe.transform.position = new Vector3(
                    (-PitchLength * 0.5f) + (stripeLength * 0.5f) + (index * stripeLength),
                    0.01f,
                    0f);
                stripe.transform.localScale = new Vector3(stripeLength, 0.02f, PitchWidth);
                var collider = stripe.GetComponent<Collider>();
                if (collider != null)
                {
                    Destroy(collider);
                }

                var renderer = stripe.GetComponent<Renderer>();
                if (renderer != null)
                {
                    renderer.sharedMaterial = pitchStripeMaterial != null ? pitchStripeMaterial : pitchMaterial;
                }
            }
        }

        private void CreatePitchMarker(string name, Vector3 position, float scale)
        {
            var marker = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            marker.name = "GTEX Illusion " + name;
            marker.transform.position = new Vector3(position.x, 0.02f, position.z);
            marker.transform.localScale = new Vector3(scale, 0.01f, scale);
            var collider = marker.GetComponent<Collider>();
            if (collider != null)
            {
                Destroy(collider);
            }

            var renderer = marker.GetComponent<Renderer>();
            if (renderer != null)
            {
                renderer.sharedMaterial = lineMaterial;
            }
        }

        private void CreateGoalFrame(string name, float goalLineX, bool facesLeft)
        {
            const float halfGoalWidth = 3.66f;
            const float goalHeight = 2.44f;
            const float goalDepth = 1.7f;
            const float postThickness = 0.12f;

            var root = new GameObject("GTEX Illusion " + name);
            var direction = facesLeft ? -1f : 1f;
            var frontX = goalLineX;
            var backX = goalLineX + (goalDepth * direction);

            CreateGoalBar(root.transform, name + " Left Post", new Vector3(frontX, goalHeight * 0.5f, -halfGoalWidth), new Vector3(postThickness, goalHeight, postThickness));
            CreateGoalBar(root.transform, name + " Right Post", new Vector3(frontX, goalHeight * 0.5f, halfGoalWidth), new Vector3(postThickness, goalHeight, postThickness));
            CreateGoalBar(root.transform, name + " Crossbar", new Vector3(frontX, goalHeight, 0f), new Vector3(postThickness, postThickness, halfGoalWidth * 2f));
            CreateGoalBar(root.transform, name + " Left Rear", new Vector3(backX, goalHeight * 0.5f, -halfGoalWidth), new Vector3(postThickness * 0.8f, goalHeight, postThickness * 0.8f));
            CreateGoalBar(root.transform, name + " Right Rear", new Vector3(backX, goalHeight * 0.5f, halfGoalWidth), new Vector3(postThickness * 0.8f, goalHeight, postThickness * 0.8f));
            CreateGoalBar(root.transform, name + " Roof Rear", new Vector3(backX, goalHeight, 0f), new Vector3(postThickness * 0.8f, postThickness * 0.8f, halfGoalWidth * 2f));

            var netColor = new Color(1f, 1f, 1f, 0.3f);
            for (var depthIndex = 0; depthIndex <= 2; depthIndex += 1)
            {
                var t = depthIndex / 2f;
                var netX = Mathf.Lerp(frontX, backX, t);
                DrawGoalNetLine(name + " Net Span " + depthIndex, new Vector3(netX, 0.08f, -halfGoalWidth), new Vector3(netX, goalHeight, -halfGoalWidth), netColor);
                DrawGoalNetLine(name + " Net Span B " + depthIndex, new Vector3(netX, 0.08f, halfGoalWidth), new Vector3(netX, goalHeight, halfGoalWidth), netColor);
                if (depthIndex < 2)
                {
                    DrawGoalNetLine(name + " Net Roof " + depthIndex, new Vector3(netX, goalHeight, -halfGoalWidth), new Vector3(netX, goalHeight, halfGoalWidth), netColor);
                }
            }

            for (var widthIndex = 0; widthIndex <= 4; widthIndex += 1)
            {
                var z = Mathf.Lerp(-halfGoalWidth, halfGoalWidth, widthIndex / 4f);
                DrawGoalNetLine(name + " Net Base " + widthIndex, new Vector3(frontX, 0.08f, z), new Vector3(backX, 0.08f, z), netColor);
                if (widthIndex > 0 && widthIndex < 4)
                {
                    DrawGoalNetLine(name + " Net Roof Depth " + widthIndex, new Vector3(frontX, goalHeight, z), new Vector3(backX, goalHeight, z), netColor);
                }
            }
        }

        private void CreateGoalBar(Transform parent, string name, Vector3 localPosition, Vector3 localScale)
        {
            var bar = GameObject.CreatePrimitive(PrimitiveType.Cube);
            bar.name = "GTEX Illusion " + name;
            bar.transform.SetParent(parent, false);
            bar.transform.position = localPosition;
            bar.transform.localScale = localScale;
            var collider = bar.GetComponent<Collider>();
            if (collider != null)
            {
                Destroy(collider);
            }

            var renderer = bar.GetComponent<Renderer>();
            if (renderer != null)
            {
                renderer.sharedMaterial = lineMaterial;
            }
        }

        private void DrawGoalNetLine(string name, Vector3 start, Vector3 end, Color color)
        {
            var lineObject = new GameObject("GTEX Illusion " + name);
            var line = lineObject.AddComponent<LineRenderer>();
            line.useWorldSpace = true;
            line.positionCount = 2;
            line.widthMultiplier = 0.018f;
            line.sharedMaterial = lineMaterial;
            line.startColor = color;
            line.endColor = color;
            line.SetPosition(0, start);
            line.SetPosition(1, end);
        }

        private void DrawPitchLine(string name, Vector3 start, Vector3 end)
        {
            var lineObject = new GameObject("GTEX Illusion " + name);
            var line = lineObject.AddComponent<LineRenderer>();
            line.useWorldSpace = true;
            line.positionCount = 2;
            line.widthMultiplier = 0.12f;
            line.sharedMaterial = lineMaterial;
            line.startColor = Color.white;
            line.endColor = Color.white;
            line.SetPosition(0, start);
            line.SetPosition(1, end);
        }

        private void DrawBox(string name, float goalLineX, float boxDepth)
        {
            var frontX = goalLineX + boxDepth;
            var halfWidth = 20.16f;
            DrawPitchLine(name + " A", new Vector3(goalLineX, 0.025f, -halfWidth), new Vector3(frontX, 0.025f, -halfWidth));
            DrawPitchLine(name + " B", new Vector3(frontX, 0.025f, -halfWidth), new Vector3(frontX, 0.025f, halfWidth));
            DrawPitchLine(name + " C", new Vector3(frontX, 0.025f, halfWidth), new Vector3(goalLineX, 0.025f, halfWidth));
        }

        private void DrawCircle(string name, Vector3 center, float radius, int segments)
        {
            var lineObject = new GameObject("GTEX Illusion " + name);
            var line = lineObject.AddComponent<LineRenderer>();
            line.useWorldSpace = true;
            line.loop = true;
            line.positionCount = Mathf.Max(12, segments);
            line.widthMultiplier = 0.1f;
            line.sharedMaterial = lineMaterial;
            line.startColor = Color.white;
            line.endColor = Color.white;

            for (var index = 0; index < line.positionCount; index += 1)
            {
                var angle = (index / (float)line.positionCount) * Mathf.PI * 2f;
                line.SetPosition(index, center + new Vector3(Mathf.Cos(angle) * radius, 0.025f, Mathf.Sin(angle) * radius));
            }
        }

        private static string ResolveDisplayName(string preferredName, string fallbackName, string defaultName)
        {
            if (!string.IsNullOrWhiteSpace(preferredName))
            {
                return preferredName.Trim();
            }

            if (!string.IsNullOrWhiteSpace(fallbackName))
            {
                return fallbackName.Trim();
            }

            return defaultName;
        }
    }

    public sealed class GtexIllusionRuntimeExecutor : IGtexMatchExecutor
    {
        public string Name => "IllusionRuntimeHost";

        public GtexRuntimeMode RuntimeMode => GtexRuntimeMode.IllusionRuntime;

        public bool IsRuntimeActive()
        {
            return UnityEngine.Object.FindFirstObjectByType<GtexIllusionRuntimeHost>() != null;
        }

        public bool TryAutoStart(GtexMatchConfig config, bool allowLocalSimulationInBatchMode, Action<string> logger)
        {
            logger?.Invoke("Delegating illusion runtime startup to GtexIllusionRuntimeHost.");
            return GtexIllusionRuntimeHost.TryAutoStart(config, allowLocalSimulationInBatchMode);
        }
    }
}
