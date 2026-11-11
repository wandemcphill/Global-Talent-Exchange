/**
 * GTEX Living Football Ecosystem — WebGL 3D Match Broadcast
 * MatchPitchLiveScene: Three.js Real-Time Match Broadcast Canvas.
 *
 * Implements:
 * 1. Procedural 105m x 68m FIFA match pitch with turf stripes, chalk lines, and 3D goal nets.
 * 2. 4-corner stadium floodlight arrays and atmospheric hemisphere lighting.
 * 3. 22 dynamic player meshes styled with club kit colors and number/name billboards.
 * 4. Authoritative 3D match ball with flight elevation and dynamic ground shadow.
 * 5. CameraDirector cinematography executing the 6 canonical camera presets.
 * 6. TV-grade BroadcastOverlayHUD scorebug, minimap radar, and event banners.
 * 7. WebGL context-loss resilience and seamless 2D fallback.
 * 8. Phase 2 Expansion: Tiered Stadiums, Weather & Atmospherics, 3D Touchline Managers, Spatial Audio.
 */

import React, { useEffect, useRef, useState, useMemo, useCallback } from "react";
import * as THREE from "three";
import { FIFA_PITCH_DIMENSIONS, pitchTo3D, PITCH_BOUNDS } from "./matchCoordinates";
import {
  calculateTimelineAdvanceSeconds,
  SpatialInterpolator,
  InterpolatedMatchState,
  TacticalVisualConfig,
} from "./SpatialInterpolator";
import { CameraDirector, ManualCameraMode, type CameraPose } from "./CameraDirector";
import { BroadcastOverlayHUD } from "./BroadcastOverlayHUD";
import {
  SpectatorSafeMatchView,
  SpectatorSafeFrameView,
  SpectatorSafeEventView,
  SpectatorSafeTeamView,
  MatchViewerContractInput,
  sanitizeForSpectator,
} from "./spectatorContract";
import { GtexSceneRegistry, QUALITY_PROFILES } from "../GtexSceneRegistry";
import type { DeviceQualityTier } from "../GtexSceneTypes";
import {
  StadiumArenaEnvironment,
  type StadiumTier,
} from "./StadiumArenaEnvironment";
import {
  WeatherAtmosphereSystem,
  type StadiumWeatherPreset,
} from "./WeatherAtmosphereSystem";
import { TouchlineManagerSystem } from "./TouchlineManagerSystem";
import { StadiumAudioEngine } from "./StadiumAudioEngine";
import { MatchOfficialsSystem } from "./MatchOfficialsSystem";
import {
  BroadcastTacticalAROverlay,
  type BroadcastAROverlayMode,
} from "./BroadcastTacticalAROverlay";
import { GoalNetPhysicsAndSetPieces } from "./GoalNetPhysicsAndSetPieces";
import {
  StadiumCeremonySystem,
  type StadiumCeremonyState,
} from "./StadiumCeremonySystem";
import {
  ReplayDirectorStudio,
  type ReplayStudioAngle,
} from "./ReplayDirectorStudio";
import { PitchTurfDegradationSystem } from "./PitchTurfDegradationSystem";
import { StadiumTifoAndJumbotronSystem } from "./StadiumTifoAndJumbotronSystem";
import {
  SpectatorImmersionLayer,
  type CommentaryCue,
  type SpectatorReactionItem,
} from "./SpectatorImmersionLayer";
import { BroadcastPostProcessingPipeline } from "./BroadcastPostProcessingPipeline";
import { PbrTurfShaderMaterial } from "./PbrTurfShaderMaterial";
import { AssetStreamingCache } from "./AssetStreamingCache";
import { CrowdChoreographyAndImpactSystem } from "./CrowdChoreographyAndImpactSystem";
import { WebGpuCapabilityBridge } from "./WebGpuCapabilityBridge";
import { polyHavenUrlForWeather, StadiumEnvironmentLighting } from "./StadiumEnvironmentLighting";
import { DynamicShadowRig } from "./DynamicShadowRig";
import { PlayerImpostorLodSystem, type ImpostorCandidate } from "./PlayerImpostorLodSystem";
import { AdaptiveQualityGovernor, type AdaptiveQualityDecision } from "./AdaptiveQualityGovernor";
import {
  type StadiumLedCampaign,
  type StadiumAdImpressionEvent,
} from "./StadiumAdvertisingNetwork";
import type { GtexAdCampaign } from "@/components/advertising/GtexAdvertising";
import { HumanoidFootballerRig } from "./HumanoidFootballerRig";
import { MixamoKitFootballer } from "./MixamoKitFootballer";
import { FootballAnimationStateMachine } from "./FootballAnimationStateMachine";
import { gtexAudio } from "@/lib/audio";

/**
 * Grass-coloured shirts disappear on the pitch. When the primary colour sits in
 * the green band, the team plays in its secondary colour and keeps green as trim.
 */
export function pitchSafeShirt(
  primary: string | undefined,
  secondary: string | undefined,
): { primary: string; secondary: string } {
  const fallbackPrimary = primary || "#00E676";
  const fallbackSecondary = secondary || "";
  const isGrass = (hex: string): boolean => {
    if (!hex) return false;
    const hsl = { h: 0, s: 0, l: 0 };
    new THREE.Color(hex).getHSL(hsl, THREE.SRGBColorSpace);
    return hsl.h > 0.22 && hsl.h < 0.48 && hsl.s > 0.3 && hsl.l > 0.18 && hsl.l < 0.75;
  };
  if (!isGrass(fallbackPrimary) || !fallbackSecondary || isGrass(fallbackSecondary)) {
    return { primary: fallbackPrimary, secondary: fallbackSecondary || fallbackPrimary };
  }
  return { primary: fallbackSecondary, secondary: fallbackPrimary };
}

export interface SpectatorLiveScoreUpdate {
  home_score: number;
  away_score: number;
  minute?: number;
  status?: string;
}

export interface MatchPitchLiveSceneProps {
  /** Strongly typed match viewer contract input (DTO or sanitized view) */
  matchViewState: MatchViewerContractInput;
  /** Verified owner or manager flag (determines confidential coach note visibility) */
  isOwnerOrManager?: boolean;
  /** Whether the match is actively broadcasting live */
  isLive?: boolean;
  /** Live spectator viewer count */
  viewerCount?: number;
  /** Optional quality tier override (auto-detected if omitted) */
  qualityTier?: DeviceQualityTier;
  /** Optional current playback time in seconds (for external scrubber sync) */
  playbackTimeSeconds?: number;
  /** Optional playback speed multiplier */
  playbackSpeed?: number;
  /** Whether playback is currently paused */
  isPaused?: boolean;
  /** Optional live frame streamed over WebSocket */
  liveFrame?: SpectatorSafeFrameView | null;
  /** Optional live events streamed over WebSocket */
  liveEvents?: SpectatorSafeEventView[];
  /** Latest authoritative score/clock update from the M1 spectator stream */
  liveScore?: SpectatorLiveScoreUpdate | null;
  /** Live tactical configuration (formation, defensive line, pressing, width, tempo) */
  tacticalConfig?: TacticalVisualConfig | null;
  /** Custom or club/competition stadium LED advertising campaigns */
  stadiumCampaigns?: StadiumLedCampaign[];
  /** Active GTEX public brand campaigns from GtexAdvertising */
  publicBrandCampaigns?: GtexAdCampaign[];
  /** Stadium LED slot rotation interval in seconds (default 10s) */
  adRotationIntervalSec?: number;
  /** Optional callback when a stadium LED campaign impression is recorded */
  onAdImpressionRecorded?: (event: StadiumAdImpressionEvent) => void;
  /** Callback when time advances (for scrubbing sync) */
  onTimeUpdate?: (timeSeconds: number) => void;
  /** Fallback toggle callback when user selects 2D tactical view */
  onToggle2DCompanion?: () => void;
  /** Whether Full-Screen 16:9 Match Theatre mode is active */
  isTheatreMode?: boolean;
  /** Callback when user toggles Full-Screen Match Theatre mode */
  onToggleTheatreMode?: () => void;
  /** Callback when user changes graphics quality profile */
  onQualityTierChange?: (tier: DeviceQualityTier) => void;
  /** Phase 2: Stadium architecture tier (1 = Community 12.5k, 2 = Regional 36k, 3 = Sovereign 68k) */
  stadiumTier?: StadiumTier;
  /** Callback when user changes stadium tier */
  onStadiumTierChange?: (tier: StadiumTier) => void;
  /** Phase 2: Dynamic matchday weather & atmospheric preset */
  weatherPreset?: StadiumWeatherPreset;
  /** Callback when user changes weather preset */
  onWeatherPresetChange?: (preset: StadiumWeatherPreset) => void;
  /** Phase 3: On-pitch 3D Broadcast AR Telestrator overlay mode */
  arOverlayMode?: BroadcastAROverlayMode;
  /** Callback when user changes AR overlay mode */
  onArOverlayModeChange?: (mode: BroadcastAROverlayMode) => void;
  /** Phase 4: Cinematic Replay Studio camera angle */
  replayStudioAngle?: ReplayStudioAngle;
  /** Callback when user changes Replay Studio camera angle */
  onReplayStudioAngleChange?: (angle: ReplayStudioAngle) => void;
  /** Phase 4: Toggle web haptics */
  hapticsEnabled?: boolean;
  /** Callback when user toggles haptics */
  onHapticsChange?: (enabled: boolean) => void;
  /** React WebGL Upgrades: Toggle bloom & cinematic post-processing */
  bloomEnabled?: boolean;
  /** Callback when user toggles bloom post-processing */
  onToggleBloom?: () => void;
  /** Additional container CSS class */
  className?: string;
  /** Test identifier */
  testId?: string;
}

export const MatchPitchLiveScene: React.FC<MatchPitchLiveSceneProps> = ({
  matchViewState,
  isOwnerOrManager = false,
  isLive = true,
  viewerCount,
  qualityTier: propQualityTier = "high",
  playbackTimeSeconds: externalTime,
  playbackSpeed = 1.0,
  isPaused = false,
  liveFrame = null,
  liveEvents = [],
  liveScore,
  tacticalConfig = null,
  stadiumCampaigns,
  publicBrandCampaigns,
  adRotationIntervalSec = 10,
  onAdImpressionRecorded,
  onTimeUpdate,
  onToggle2DCompanion,
  isTheatreMode: externalTheatreMode,
  onToggleTheatreMode,
  onQualityTierChange,
  stadiumTier: propStadiumTier = 3,
  onStadiumTierChange,
  weatherPreset: propWeatherPreset = "clear_night",
  onWeatherPresetChange,
  arOverlayMode: propArOverlayMode = "off",
  onArOverlayModeChange,
  replayStudioAngle: propReplayStudioAngle = "orbit_360",
  onReplayStudioAngleChange,
  hapticsEnabled: propHapticsEnabled = true,
  onHapticsChange,
  bloomEnabled: propBloomEnabled = true,
  onToggleBloom,
  className = "",
  testId = "match-pitch-live-scene",
}) => {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const stadiumArenaRef = useRef<StadiumArenaEnvironment | null>(null);
  const stadiumEnvLightingRef = useRef<StadiumEnvironmentLighting | null>(null);
  const weatherSystemRef = useRef<WeatherAtmosphereSystem | null>(null);
  const touchlineManagerRef = useRef<TouchlineManagerSystem | null>(null);
  const matchOfficialsRef = useRef<MatchOfficialsSystem | null>(null);
  const arOverlayRef = useRef<BroadcastTacticalAROverlay | null>(null);
  const goalNetAndSetPiecesRef = useRef<GoalNetPhysicsAndSetPieces | null>(null);
  const stadiumCeremonyRef = useRef<StadiumCeremonySystem | null>(null);
  const replayStudioRef = useRef<ReplayDirectorStudio | null>(null);
  const turfDegradationRef = useRef<PitchTurfDegradationSystem | null>(null);
  const tifoAndJumbotronRef = useRef<StadiumTifoAndJumbotronSystem | null>(null);
  const immersionLayerRef = useRef<SpectatorImmersionLayer | null>(null);
  const postProcessingRef = useRef<BroadcastPostProcessingPipeline | null>(null);
  const pbrTurfRef = useRef<PbrTurfShaderMaterial | null>(null);
  const crowdChoreographyRef = useRef<CrowdChoreographyAndImpactSystem | null>(null);
  const webGpuBridgeRef = useRef<WebGpuCapabilityBridge | null>(null);
  const qualityGovernorRef = useRef<AdaptiveQualityGovernor | null>(null);
  const userLockedQualityRef = useRef<boolean>(false);
  const audioEngineRef = useRef<StadiumAudioEngine>(new StadiumAudioEngine({ initialMuted: true }));
  const [webglSupported, setWebglSupported] = useState<boolean>(true);
  const [contextLost, setContextLost] = useState<boolean>(false);
  const [cameraMode, setCameraMode] = useState<ManualCameraMode>("director_auto");
  const [is2DActive, setIs2DActive] = useState<boolean>(false);
  const [audioMuted, setAudioMuted] = useState<boolean>(true);
  const [qualityTier, setQualityTierState] = useState<DeviceQualityTier>(propQualityTier);
  const [stadiumTier, setStadiumTierState] = useState<StadiumTier>(propStadiumTier);
  const [weatherPreset, setWeatherPresetState] = useState<StadiumWeatherPreset>(propWeatherPreset);
  const [arOverlayMode, setArOverlayModeState] = useState<BroadcastAROverlayMode>(propArOverlayMode);
  const [replayStudioAngle, setReplayStudioAngleState] = useState<ReplayStudioAngle>(propReplayStudioAngle);
  const [hapticsEnabled, setHapticsEnabledState] = useState<boolean>(propHapticsEnabled);
  const [bloomEnabled, setBloomEnabledState] = useState<boolean>(propBloomEnabled);
  const [commentaryCue, setCommentaryCue] = useState<CommentaryCue | null>(null);
  const [spectatorReactions, setSpectatorReactions] = useState<readonly SpectatorReactionItem[]>([]);
  const [watchPartyCheerMeter, setWatchPartyCheerMeter] = useState<number>(15);
  const [internalTheatreMode, setInternalTheatreMode] = useState<boolean>(false);
  const [minimalHud, setMinimalHud] = useState<boolean>(false);
  const [isReplayActive, setIsReplayActive] = useState<boolean>(false);
  const [replayFallbackMessage, setReplayFallbackMessage] = useState<string | null>(null);
  const [activeSponsorName, setActiveSponsorName] = useState<string | null>(null);
  const replayCursorTimeRef = useRef<number | null>(null);
  const replayEndTimeRef = useRef<number | null>(null);
  const lastCrowdEventIdRef = useRef<string | null>(null);
  const lastBallStateRef = useRef<string>("idle");
  const stadiumTierRef = useRef<StadiumTier>(propStadiumTier);
  const weatherPresetRef = useRef<StadiumWeatherPreset>(propWeatherPreset);
  const arOverlayModeRef = useRef<BroadcastAROverlayMode>(propArOverlayMode);
  const replayStudioAngleRef = useRef<ReplayStudioAngle>(propReplayStudioAngle);

  const isTheatreMode = externalTheatreMode ?? internalTheatreMode;

  useEffect(() => {
    setQualityTierState(propQualityTier);
    postProcessingRef.current?.setQualityTier(propQualityTier);
  }, [propQualityTier]);

  useEffect(() => {
    setBloomEnabledState(propBloomEnabled);
    postProcessingRef.current?.setBloomEnabled(propBloomEnabled);
  }, [propBloomEnabled]);

  useEffect(() => {
    setStadiumTierState(propStadiumTier);
    stadiumTierRef.current = propStadiumTier;
    stadiumArenaRef.current?.setStadiumTier(propStadiumTier);
  }, [propStadiumTier]);

  useEffect(() => {
    setWeatherPresetState(propWeatherPreset);
    weatherPresetRef.current = propWeatherPreset;
    weatherSystemRef.current?.setPreset(propWeatherPreset);
    void stadiumEnvLightingRef.current?.loadPolyHaven(polyHavenUrlForWeather(propWeatherPreset));
  }, [propWeatherPreset]);

  useEffect(() => {
    setArOverlayModeState(propArOverlayMode);
    arOverlayModeRef.current = propArOverlayMode;
    arOverlayRef.current?.setMode(propArOverlayMode);
  }, [propArOverlayMode]);

  useEffect(() => {
    setReplayStudioAngleState(propReplayStudioAngle);
    replayStudioAngleRef.current = propReplayStudioAngle;
    replayStudioRef.current?.setReplayAngle(propReplayStudioAngle);
  }, [propReplayStudioAngle]);

  useEffect(() => {
    setHapticsEnabledState(propHapticsEnabled);
    immersionLayerRef.current?.setHapticsEnabled(propHapticsEnabled);
  }, [propHapticsEnabled]);

  const handleSelectQualityTier = useCallback(
    (tier: "high" | "medium" | "low") => {
      // A manual choice overrides the adaptive quality governor
      userLockedQualityRef.current = true;
      qualityGovernorRef.current?.lock(tier);
      setQualityTierState(tier);
      onQualityTierChange?.(tier);
    },
    [onQualityTierChange]
  );

  const handleSelectStadiumTier = useCallback(
    (tier: StadiumTier) => {
      setStadiumTierState(tier);
      stadiumTierRef.current = tier;
      stadiumArenaRef.current?.setStadiumTier(tier);
      onStadiumTierChange?.(tier);
    },
    [onStadiumTierChange]
  );

  const handleSelectWeatherPreset = useCallback(
    (preset: StadiumWeatherPreset) => {
      setWeatherPresetState(preset);
      weatherPresetRef.current = preset;
      weatherSystemRef.current?.setPreset(preset);
      void stadiumEnvLightingRef.current?.loadPolyHaven(polyHavenUrlForWeather(preset));
      onWeatherPresetChange?.(preset);
    },
    [onWeatherPresetChange]
  );

  const handleSelectArOverlayMode = useCallback(
    (mode: BroadcastAROverlayMode) => {
      setArOverlayModeState(mode);
      arOverlayModeRef.current = mode;
      arOverlayRef.current?.setMode(mode);
      onArOverlayModeChange?.(mode);
    },
    [onArOverlayModeChange]
  );

  const handleSelectReplayStudioAngle = useCallback(
    (angle: ReplayStudioAngle) => {
      setReplayStudioAngleState(angle);
      replayStudioAngleRef.current = angle;
      replayStudioRef.current?.setReplayAngle(angle);
      onReplayStudioAngleChange?.(angle);
    },
    [onReplayStudioAngleChange]
  );

  const handleToggleHaptics = useCallback(() => {
    setHapticsEnabledState((prev) => {
      const next = !prev;
      immersionLayerRef.current?.setHapticsEnabled(next);
      onHapticsChange?.(next);
      return next;
    });
  }, [onHapticsChange]);

  const handleToggleBloom = useCallback(() => {
    setBloomEnabledState((prev) => {
      const next = !prev;
      postProcessingRef.current?.setBloomEnabled(next);
      onToggleBloom?.();
      return next;
    });
  }, [onToggleBloom]);

  const handleSendReaction = useCallback((emoji: string) => {
    immersionLayerRef.current?.sendReaction(emoji, "Viewer");
    if (immersionLayerRef.current) {
      setSpectatorReactions(immersionLayerRef.current.getRecentReactions());
      setWatchPartyCheerMeter(immersionLayerRef.current.getSummary().cheerMeter);
    }
  }, []);

  const handleToggleTheatre = useCallback(() => {
    if (onToggleTheatreMode) {
      onToggleTheatreMode();
    } else {
      setInternalTheatreMode((prev) => !prev);
    }
  }, [onToggleTheatreMode]);

  // Sanitize spectator-safe match view state
  const safeView: SpectatorSafeMatchView = useMemo(() => {
    return sanitizeForSpectator(matchViewState, isOwnerOrManager);
  }, [matchViewState, isOwnerOrManager]);

  // Persistent SpatialInterpolator & FootballAnimationStateMachine instances
  const interpolator = useMemo(() => new SpatialInterpolator(safeView.frames), []);
  const animationStateMachine = useMemo(
    () => new FootballAnimationStateMachine(safeView.events),
    []
  );

  // Camera director instance
  const cameraDirector = useMemo(() => new CameraDirector(), []);

  // Internal playback time tracker
  const [currentTime, setCurrentTime] = useState<number>(() => {
    if (typeof externalTime === "number") return externalTime;
    return interpolator.getStartTime();
  });

  const [currentMatchState, setCurrentMatchState] = useState<InterpolatedMatchState | null>(null);

  // Refs for mutable props so the Three.js WebGL context is never torn down on playback state changes
  const safeViewRef = useRef<SpectatorSafeMatchView>(safeView);
  const isLiveRef = useRef<boolean>(isLive);
  const playbackSpeedRef = useRef<number>(playbackSpeed);
  const isPausedRef = useRef<boolean>(isPaused);
  const onTimeUpdateRef = useRef<typeof onTimeUpdate>(onTimeUpdate);
  const liveScoreRef = useRef<SpectatorLiveScoreUpdate | null>(liveScore ?? null);
  liveScoreRef.current = liveScore ?? null;
  const localTimeRef = useRef<number>(currentTime);

  useEffect(() => {
    safeViewRef.current = safeView;
    interpolator.setFrames(safeView.frames);
    if (stadiumArenaRef.current) {
      stadiumArenaRef.current.setTeamIdentity(
        safeView.home_team,
        safeView.away_team,
        safeView.competition_name,
        safeView.match_id
      );
      stadiumArenaRef.current.getAdvertisingNetwork().setMatchMonetization(safeView.monetization);
    }
  }, [safeView, interpolator]);

  useEffect(() => {
    interpolator.setTacticalConfig(tacticalConfig ?? null);
    if (tacticalConfig) {
      touchlineManagerRef.current?.notifyTacticalChange("both");
    }
  }, [tacticalConfig, interpolator]);

  useEffect(() => {
    if (stadiumArenaRef.current && stadiumCampaigns) {
      stadiumArenaRef.current.getAdvertisingNetwork().setCampaigns(stadiumCampaigns);
    }
  }, [stadiumCampaigns]);

  useEffect(() => {
    if (stadiumArenaRef.current && publicBrandCampaigns) {
      stadiumArenaRef.current.getAdvertisingNetwork().setPublicBrandCampaigns(publicBrandCampaigns);
    }
  }, [publicBrandCampaigns]);

  useEffect(() => {
    const mergedEvents =
      liveEvents && liveEvents.length > 0
        ? [...safeView.events, ...liveEvents]
        : safeView.events;
    animationStateMachine.setEvents(mergedEvents);
  }, [safeView.events, liveEvents, animationStateMachine]);

  useEffect(() => {
    if (liveFrame) {
      interpolator.appendFrame(liveFrame);
    }
  }, [liveFrame, interpolator]);

  useEffect(() => {
    isLiveRef.current = isLive;
  }, [isLive]);

  useEffect(() => {
    playbackSpeedRef.current = playbackSpeed;
  }, [playbackSpeed]);

  useEffect(() => {
    isPausedRef.current = isPaused;
  }, [isPaused]);

  useEffect(() => {
    onTimeUpdateRef.current = onTimeUpdate;
  }, [onTimeUpdate]);

  // Sync external scrubber changes
  useEffect(() => {
    if (typeof externalTime === "number" && Math.abs(externalTime - localTimeRef.current) > 0.5) {
      localTimeRef.current = externalTime;
      setCurrentTime(externalTime);
    }
  }, [externalTime]);

  // Sync manual camera mode
  useEffect(() => {
    cameraDirector.setManualMode(cameraMode);
  }, [cameraMode, cameraDirector]);

  // Coordinate Match Atmosphere Audio with central GtexAudioManager & StadiumAudioEngine
  useEffect(() => {
    audioEngineRef.current.setMuted(audioMuted);
    if (!audioMuted) {
      gtexAudio.registerActiveChannelSource("ambience", "match_pitch_live_atmosphere");
    } else {
      gtexAudio.unregisterActiveChannelSource("ambience", "match_pitch_live_atmosphere");
    }
    return () => {
      gtexAudio.unregisterActiveChannelSource("ambience", "match_pitch_live_atmosphere");
    };
  }, [audioMuted]);

  useEffect(() => {
    return () => {
      audioEngineRef.current.dispose();
    };
  }, []);

  // ---------------------------------------------------------------------------
  // Three.js WebGL Scene Lifecycle
  // ---------------------------------------------------------------------------
  useEffect(() => {
    if (is2DActive) return;
    const container = mountRef.current;
    if (!container) return;

    // Test WebGL support
    try {
      const testCanvas = document.createElement("canvas");
      const gl = testCanvas.getContext("webgl") || testCanvas.getContext("experimental-webgl");
      if (!gl) {
        setWebglSupported(false);
        return;
      }
    } catch {
      setWebglSupported(false);
      return;
    }

    const width = container.clientWidth || 800;
    const height = container.clientHeight || 500;

    // 1. Scene, Camera, Renderer
    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#0c1830");
    scene.fog = new THREE.FogExp2("#0c1830", 0.0016);

    const camera = new THREE.PerspectiveCamera(38, width / height, 0.5, 300);
    camera.position.set(0, 32, 55);
    camera.lookAt(0, 0, 0);

    const pixelCap =
      qualityTier === "ultra" ? 2 : qualityTier === "high" ? 1.5 : qualityTier === "medium" ? 1.25 : 1;
    let renderer: THREE.WebGLRenderer | null = null;
    try {
      renderer = new THREE.WebGLRenderer({
        antialias: qualityTier !== "low",
        powerPreference: "high-performance",
      });
      renderer.setSize(width, height);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, pixelCap));
      renderer.outputColorSpace = THREE.SRGBColorSpace;
      if (qualityTier !== "low") {
        renderer.shadowMap.enabled = true;
        renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        renderer.shadowMap.autoUpdate = false;
        renderer.shadowMap.needsUpdate = true;
      }
      container.appendChild(renderer.domElement);
    } catch {
      setWebglSupported(false);
      return;
    }

    // Context loss listeners
    const handleContextLost = (e: Event) => {
      e.preventDefault();
      setContextLost(true);
    };
    const handleContextRestored = () => {
      setContextLost(false);
    };
    const canvasElement = renderer.domElement;
    canvasElement.addEventListener("webglcontextlost", handleContextLost);
    canvasElement.addEventListener("webglcontextrestored", handleContextRestored);

    // -------------------------------------------------------------------------
    // 2. Comprehensive Stadium & Pitch Environment (Milestone 2 + Phase 2)
    // -------------------------------------------------------------------------
    const hemiLight = new THREE.HemisphereLight(0xdbeafe, 0x1e5631, 1.15);
    scene.add(hemiLight);

    const keyLight = new THREE.DirectionalLight(0xffffff, 1.35);
    keyLight.position.set(20, 55, 42);
    if (renderer.shadowMap.enabled) {
      keyLight.castShadow = true;
      keyLight.shadow.mapSize.width = 1024;
      keyLight.shadow.mapSize.height = 1024;
      keyLight.shadow.camera.near = 10;
      keyLight.shadow.camera.far = 120;
      keyLight.shadow.camera.left = -60;
      keyLight.shadow.camera.right = 60;
      keyLight.shadow.camera.top = 40;
      keyLight.shadow.camera.bottom = -40;
    }
    scene.add(keyLight);

    const fillLight = new THREE.DirectionalLight(0xf1f5f9, 0.72);
    fillLight.position.set(-25, 42, -38);
    scene.add(fillLight);

    const stadiumArena = new StadiumArenaEnvironment(scene, {
      homeTeam: safeViewRef.current.home_team,
      awayTeam: safeViewRef.current.away_team,
      qualityTier,
      stadiumTier: stadiumTierRef.current,
      stadiumName: safeViewRef.current.venue_name || "GTEX National Arena",
      competitionName: safeViewRef.current.competition_name || "GTEX PREMIER BROADCAST",
      matchId: safeViewRef.current.match_id,
      adNetworkOptions: {
        rotationIntervalSec: adRotationIntervalSec,
        onImpressionRecorded: onAdImpressionRecorded,
        onRotationChanged: (activeCampaigns) => {
          setActiveSponsorName(activeCampaigns[0]?.brandName || null);
        },
      },
      initialCampaigns: stadiumCampaigns,
    });
    stadiumArenaRef.current = stadiumArena;
    if (typeof window !== "undefined" && !/jsdom/i.test(window.navigator?.userAgent || "")) {
      void stadiumArena.loadBroadcastBowl("/models/match/football-stadium.glb", renderer);
    }

    // -------------------------------------------------------------------------
    // 3. Phase 2: Weather & Atmospherics + 3D Touchline Managers & Bench
    // -------------------------------------------------------------------------
    const weatherSystem = new WeatherAtmosphereSystem(scene, {
      initialPreset: weatherPresetRef.current,
      qualityTier,
      hemiLight,
      keyLight,
      fillLight,
    });
    const pitchMats = stadiumArena.getPitchMaterials();
    weatherSystem.bindPitchMaterials(pitchMats.pitchTurfMat, pitchMats.pitchRunoffMat);
    weatherSystemRef.current = weatherSystem;

    const touchlineManagers = new TouchlineManagerSystem(scene, {
      homeTeam: safeViewRef.current.home_team,
      awayTeam: safeViewRef.current.away_team,
      qualityTier,
    });
    touchlineManagerRef.current = touchlineManagers;

    // -------------------------------------------------------------------------
    // 3b. Phase 3: Match Officials, Broadcast AR Overlays, Goal-Net Physics & Ceremony
    // -------------------------------------------------------------------------
    const matchOfficials = new MatchOfficialsSystem(scene, { qualityTier });
    matchOfficialsRef.current = matchOfficials;

    const arOverlay = new BroadcastTacticalAROverlay(scene, {
      initialMode: arOverlayModeRef.current,
      homeColorHex: safeViewRef.current.home_team.primary_color,
      awayColorHex: safeViewRef.current.away_team.primary_color,
    });
    arOverlayRef.current = arOverlay;

    const goalNetAndSetPieces = new GoalNetPhysicsAndSetPieces(scene);
    goalNetAndSetPiecesRef.current = goalNetAndSetPieces;

    const stadiumCeremony = new StadiumCeremonySystem(scene);
    stadiumCeremonyRef.current = stadiumCeremony;

    // -------------------------------------------------------------------------
    // 3c. Phase 4: Replay Studio, Pitch Turf Degradation, Jumbotrons/Tifo & Immersion
    // -------------------------------------------------------------------------
    const replayStudio = new ReplayDirectorStudio({
      initialAngle: replayStudioAngleRef.current,
      playbackRate: 0.45,
    });
    replayStudioRef.current = replayStudio;

    const turfDegradation = new PitchTurfDegradationSystem(scene);
    turfDegradationRef.current = turfDegradation;

    const tifoAndJumbotron = new StadiumTifoAndJumbotronSystem(scene, {
      homeShortName: safeViewRef.current.home_team.short_name,
      awayShortName: safeViewRef.current.away_team.short_name,
      homeColorHex: safeViewRef.current.home_team.primary_color,
      awayColorHex: safeViewRef.current.away_team.primary_color,
      competitionName: safeViewRef.current.competition_name || "GTEX PREMIER BROADCAST",
    });
    tifoAndJumbotronRef.current = tifoAndJumbotron;

    const immersionLayer = new SpectatorImmersionLayer({
      hapticsEnabled: propHapticsEnabled,
      watchPartyRoomSize: Math.max(12, Math.min(250, viewerCount ? Math.floor(viewerCount / 40) : 32)),
    });
    immersionLayerRef.current = immersionLayer;

    // -------------------------------------------------------------------------
    // 3d. React WebGL 3D Upgrades: Post-Processing, PBR Turf, Crowd Choreo & WebGPU
    // -------------------------------------------------------------------------
    const postProcessing = new BroadcastPostProcessingPipeline(renderer, scene, camera, {
      qualityTier,
      bloomEnabled,
      bloomStrength: 0.1,
      bloomThreshold: 0.94,
    });
    postProcessingRef.current = postProcessing;

    const pbrTurf = new PbrTurfShaderMaterial({
      moisture: weatherPresetRef.current === "rain" ? 0.75 : weatherPresetRef.current === "snow" ? 0.45 : 0.0,
      wearFactor: 0.0,
    });
    pbrTurfRef.current = pbrTurf;

    const crowdChoreography = new CrowdChoreographyAndImpactSystem();
    crowdChoreographyRef.current = crowdChoreography;

    const webGpuBridge = new WebGpuCapabilityBridge();
    webGpuBridgeRef.current = webGpuBridge;

    // PBR turf actually replaces the Lambert pitch surface
    stadiumArena.applyPitchTurfMaterial(pbrTurf.material);

    // Crowd choreography waves physically move the instanced supporters
    stadiumArena.setExternalCrowdOffsetFn((x, z) => crowdChoreography.getCrowdSectionOffset(x, z));

    // Image-based lighting, ball-following soft shadows, distant-player impostors
    const stadiumEnvLighting = new StadiumEnvironmentLighting(renderer, scene, qualityTier);
    stadiumEnvLightingRef.current = stadiumEnvLighting;
    if (typeof window !== "undefined" && !/jsdom/i.test(window.navigator?.userAgent || "")) {
      void stadiumEnvLighting.loadPolyHaven(polyHavenUrlForWeather(weatherPresetRef.current));
    }
    const shadowRig = new DynamicShadowRig(renderer, keyLight, qualityTier);
    const shadowsOn = shadowRig.getSummary().enabled;
    const playerImpostors = new PlayerImpostorLodSystem(scene, qualityTier);
    const impostorCandidatesScratch: ImpostorCandidate[] = [];

    // Adaptive quality: hardware report caps the tier, frame times drive resolution + post-FX
    const basePixelRatio = Math.min(window.devicePixelRatio || 1, pixelCap);
    const qualityGovernor = new AdaptiveQualityGovernor(qualityTier);
    if (userLockedQualityRef.current) qualityGovernor.lock(qualityTier);
    qualityGovernorRef.current = qualityGovernor;
    const applyQualityDecision = (decision: AdaptiveQualityDecision) => {
      if (!decision.changed || !renderer) return;
      renderer.setPixelRatio(basePixelRatio * decision.resolutionScale);
      postProcessing.setQualityTier(decision.postFxTier);
      playerImpostors.setQualityTier(decision.postFxTier);
      const w = container.clientWidth || width;
      const h = container.clientHeight || height;
      renderer.setSize(w, h);
      postProcessing.setSize(w, h);
    };
    webGpuBridge
      .inspectRenderer(renderer)
      .then((report) => applyQualityDecision(qualityGovernor.applyCapabilities(report)))
      .catch(() => {});

    const adNet = stadiumArena.getAdvertisingNetwork();
    if (safeViewRef.current.monetization) {
      adNet.setMatchMonetization(safeViewRef.current.monetization);
    }
    if (publicBrandCampaigns && publicBrandCampaigns.length > 0) {
      adNet.setPublicBrandCampaigns(publicBrandCampaigns);
    }
    setActiveSponsorName(adNet.getActiveCampaigns()[0]?.brandName || null);

    const handleVisibilityChange = () => {
      if (typeof document !== "undefined") {
        adNet.setDocumentVisible(!document.hidden);
      }
    };
    if (typeof document !== "undefined") {
      document.addEventListener("visibilitychange", handleVisibilityChange);
    }

    // Query physical GPU renderer info from WebGL context
    let gpuVendor = "WebGL";
    let gpuRenderer = "WebGL Hardware Renderer";
    try {
      const glCtx = renderer.getContext();
      const dbgExt = glCtx.getExtension("WEBGL_debug_renderer_info");
      if (dbgExt) {
        gpuVendor = String(glCtx.getParameter(dbgExt.UNMASKED_VENDOR_WEBGL) || gpuVendor);
        gpuRenderer = String(glCtx.getParameter(dbgExt.UNMASKED_RENDERER_WEBGL) || gpuRenderer);
      }
    } catch {
      // Ignore if debug extension is unavailable
    }

    // -------------------------------------------------------------------------
    // 4. Rigged Humanoid Footballer System (Pool of 22 Players + State Machine)
    // -------------------------------------------------------------------------
    const playersGroup = new THREE.Group();
    playersGroup.name = "HumanoidPlayersGroup";
    scene.add(playersGroup);

    const playerRigs = new Map<string, HumanoidFootballerRig | MixamoKitFootballer>();

    const getOrCreatePlayerRig = (
      playerId: string,
      side: "home" | "away",
      shirtNum: number = 10,
      label: string = "Player",
      role: string = "MID",
      isGK: boolean = false
    ): HumanoidFootballerRig | MixamoKitFootballer => {
      if (playerRigs.has(playerId)) {
        return playerRigs.get(playerId)!;
      }

      const currentSafeView = safeViewRef.current;

      // Kit Clash Detection (RGB euclidean distance < 65)
      const homeColor = new THREE.Color(
        pitchSafeShirt(currentSafeView.home_team.primary_color, currentSafeView.home_team.secondary_color).primary || "#00E676",
      );
      const awayColor = new THREE.Color(
        pitchSafeShirt(currentSafeView.away_team.primary_color, currentSafeView.away_team.secondary_color).primary || "#3B82F6",
      );
      const dr = (homeColor.r - awayColor.r) * 255;
      const dg = (homeColor.g - awayColor.g) * 255;
      const db = (homeColor.b - awayColor.b) * 255;
      const isClash = Math.sqrt(dr * dr + dg * dg + db * db) < 65;

      const teamView = side === "home" ? currentSafeView.home_team : currentSafeView.away_team;
      // A green shirt vanishes on a green pitch. Play in the change colours.
      const safeKit = pitchSafeShirt(teamView.primary_color, teamView.secondary_color);
      let primaryColor = safeKit.primary;
      let secondaryColor = safeKit.secondary;
      let patternType = teamView.pattern_type;

      if (side === "away" && isClash) {
        // High-contrast away kit fallback to secondary, third kit, or contrasting palette
        if (teamView.third_primary_color) {
          primaryColor = teamView.third_primary_color;
          secondaryColor = teamView.third_secondary_color || teamView.accent_color;
        } else if (teamView.secondary_color) {
          primaryColor = teamView.secondary_color;
          secondaryColor = teamView.primary_color;
        } else {
          primaryColor = homeColor.r + homeColor.g + homeColor.b > 1.5 ? "#0f172a" : "#ffffff";
          secondaryColor = "#94a3b8";
        }
      }

      const kitConfig = {
        playerId,
        side,
        shirtNumber: shirtNum,
        label,
        role,
        isGoalkeeper: isGK,
        primaryColor,
        secondaryColor,
        accentColor: teamView.accent_color,
        goalkeeperColor: teamView.goalkeeper_color,
        patternType: (patternType as any) || "solid",
        shortsColor: teamView.shorts_color,
        socksColor: teamView.socks_color,
        crestUrl: teamView.crest_url,
        sponsorName: teamView.sponsor_name,
        playerName: label,
      };
      const useMixamoKit =
        typeof window !== "undefined" && !/jsdom/i.test(window.navigator?.userAgent || "");
      const rig = useMixamoKit
        ? new MixamoKitFootballer(kitConfig)
        : new HumanoidFootballerRig(kitConfig);

      playersGroup.add(rig.rootGroup);
      rig.setShadowCasting(shadowsOn);
      playerRigs.set(playerId, rig);
      return rig;
    };

    // -------------------------------------------------------------------------
    // 5. 3D Ball Mesh & Dynamic Drop Shadow
    // -------------------------------------------------------------------------
    const ballGroup = new THREE.Group();
    scene.add(ballGroup);

    // Size-5 football: 68–70 cm circumference, about 21.6 cm across.
    const ballRadius = 0.108;
    let ballLift = ballRadius;
    const ballGeo = new THREE.SphereGeometry(ballRadius, 16, 16);
    const ballMat = new THREE.MeshStandardMaterial({
      color: 0xf4f4f4,
      roughness: 0.55,
      metalness: 0.02,
      envMapIntensity: 0.2,
    });
    ballMat.userData.gtexFixedEnv = 0.2;
    const ballMesh = new THREE.Mesh(ballGeo, ballMat);
    ballMesh.castShadow = false;
    ballGroup.add(ballMesh);

    if (typeof window !== "undefined" && !/jsdom/i.test(window.navigator?.userAgent || "")) {
      AssetStreamingCache.getInstance()
        .loadGltf("/models/match/football_pbr.glb", renderer)
        .then((gltf) => {
          if (!gltf?.scene) return;
          const pbrBall = gltf.scene.clone(true);
          pbrBall.traverse((obj) => {
            if (/deflated/i.test(obj.name)) obj.visible = false;
          });
          pbrBall.updateMatrixWorld(true);
          const box = new THREE.Box3().setFromObject(pbrBall);
          const size = new THREE.Vector3();
          box.getSize(size);
          const diameter = Math.max(size.x, size.y, size.z, 0.001);
          pbrBall.scale.multiplyScalar((ballRadius * 2) / diameter);
          pbrBall.updateMatrixWorld(true);
          const fitted = new THREE.Box3().setFromObject(pbrBall);
          const center = new THREE.Vector3();
          fitted.getCenter(center);
          pbrBall.position.x -= center.x;
          pbrBall.position.z -= center.z;
          pbrBall.position.y -= fitted.min.y;
          ballLift = 0;
          pbrBall.traverse((obj) => {
            const mesh = obj as THREE.Mesh;
            if (!mesh.isMesh) return;
            const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
            mats.forEach((material) => {
              const standard = material as THREE.MeshStandardMaterial;
              if (!standard.isMeshStandardMaterial) return;
              standard.envMapIntensity = 0.25;
              standard.userData.gtexFixedEnv = 0.25;
              standard.roughness = Math.max(standard.roughness ?? 0.4, 0.4);
              // Under the night rig the leather albedo lands tan. Lift the white
              // panels with the same texture so the ball reads white and black.
              if (standard.map) {
                standard.emissiveMap = standard.map;
                standard.emissive.setRGB(0.38, 0.38, 0.38);
                standard.emissiveIntensity = 1;
              }
            });
          });
          ballMesh.add(pbrBall);
          // Drop the white placeholder. An opacity change does not recompile the
          // opaque shader, so the sphere stayed on top of the textured ball.
          (ballMesh as THREE.Mesh).geometry = new THREE.BufferGeometry();
        })
        .catch(() => {});
    }

    // Ball Drop Shadow Disc on Turf
    const shadowGeo = new THREE.CircleGeometry(ballRadius * 1.4, 16);
    const shadowMat = new THREE.MeshBasicMaterial({
      color: 0x050e08,
      transparent: true,
      opacity: 0.6,
    });
    const ballShadowMesh = new THREE.Mesh(shadowGeo, shadowMat);
    ballShadowMesh.rotation.x = -Math.PI / 2;
    ballShadowMesh.position.y = 0.03;
    scene.add(ballShadowMesh);

    // -------------------------------------------------------------------------
    // 6. Animation / Render Loop + Real Browser Hardware Telemetry
    // -------------------------------------------------------------------------
    let animationFrameId: number;
    let lastTimestamp = performance.now();
    let heldAtEndSec = 0;
    let lastEndTime = -1;
    const frameDeltaSamplesMs: number[] = [];
    let frameDeltaSumMs = 0;
    let telemetryTick = 0;
    let cachedP50Ms = 16.6;
    let cachedP95Ms = 16.6;
    let cachedP99Ms = 16.6;
    let cachedWorstOnePctAvgMs = 16.6;
    const observedStatesHistory = new Set<string>();
    const observedCameraPresetsHistory = new Set<string>();
    const activePlayerIdsScratch = new Set<string>();
    let lastUiStateUpdateMs = 0;

    if (typeof window !== "undefined") {
      (window as any).__GTEX_BROADCAST_CONTROL__ = {
        seekTo: (timeSec: number) => {
          localTimeRef.current = timeSec;
          setCurrentTime(timeSec);
        },
        setCameraMode: (mode: ManualCameraMode) => {
          setCameraMode(mode);
        },
        getCamera: () => ({
          mode: cameraDirector.getManualMode(),
          position: [camera.position.x, camera.position.y, camera.position.z],
          fov: camera.fov,
        }),
        setQualityTier: (tier: "high" | "medium" | "low") => {
          handleSelectQualityTier(tier);
        },
        setStadiumTier: (tier: StadiumTier) => {
          handleSelectStadiumTier(tier);
        },
        setWeatherPreset: (preset: StadiumWeatherPreset) => {
          handleSelectWeatherPreset(preset);
        },
        setArOverlayMode: (mode: BroadcastAROverlayMode) => {
          handleSelectArOverlayMode(mode);
        },
        setCeremonyState: (state: StadiumCeremonyState, durationSec: number = 8.0) => {
          stadiumCeremony.setCeremonyState(state, durationSec);
        },
        triggerCrowdWave: () => {
          stadiumArena.triggerCrowdWave();
        },
        setTheatreMode: (enabled: boolean) => {
          setInternalTheatreMode(enabled);
        },
        triggerReplay: () => {
          if (interpolator.getFrameCount() < 2) {
            setReplayFallbackMessage("EVENT SUMMARY ONLY — SPATIAL REPLAY HISTORY UNAVAILABLE");
            return;
          }
          const liveNow = localTimeRef.current;
          replayEndTimeRef.current = liveNow;
          const rewindTo = Math.max(interpolator.getStartTime(), liveNow - 8.0);
          replayCursorTimeRef.current = rewindTo;
          setIsReplayActive(true);
          setCameraMode("replay_cam");
        },
        setTacticalConfig: (cfg: TacticalVisualConfig | null) => {
          interpolator.setTacticalConfig(cfg);
          if (cfg) {
            touchlineManagers.notifyTacticalChange("both");
          }
        },
        setStadiumCampaigns: (campaigns: StadiumLedCampaign[]) => {
          stadiumArena.getAdvertisingNetwork().setCampaigns(campaigns);
          setActiveSponsorName(stadiumArena.getAdvertisingNetwork().getActiveCampaigns()[0]?.brandName || null);
        },
        getAdvertisingSummary: () => {
          const net = stadiumArena.getAdvertisingNetwork();
          return {
            rotationIntervalSec: net.getRotationIntervalSec(),
            rotationCount: net.getRotationCount(),
            currentRotationIndex: net.getCurrentRotationIndex(),
            activeCampaigns: net.getActiveCampaigns(),
            impressions: net.getImpressionHistory(),
          };
        },
        getPhase2Summary: () => ({
          stadiumTier: stadiumArena.getStadiumTierProfile(),
          weather: weatherSystem.getTelemetry(),
          touchlineManagers: touchlineManagers.getSummary(),
          spatialAudio: audioEngineRef.current.getTelemetry(),
        }),
        getPhase3Summary: () => ({
          matchOfficials: matchOfficials.getSummary(),
          arOverlay: arOverlay.getSummary(),
          goalNetAndSetPieces: goalNetAndSetPieces.getSummary(),
          stadiumCeremony: stadiumCeremony.getSummary(),
        }),
        getPhase4Summary: () => ({
          replayStudio: replayStudio.getSummary(),
          turfDegradation: turfDegradation.getSummary(),
          tifoAndJumbotron: tifoAndJumbotron.getSummary(),
          immersionLayer: immersionLayer.getSummary(),
        }),
        getUpgradesSummary: () => ({
          postProcessing: postProcessing.getSummary(),
          pbrTurf: pbrTurf.getSummary(),
          assetCache: AssetStreamingCache.getInstance().getSummary(),
          crowdChoreography: crowdChoreography.getSummary(),
          webGpuBridge: webGpuBridge.getReport(),
        }),
        resetTelemetry: () => {
          frameDeltaSamplesMs.length = 0;
          frameDeltaSumMs = 0;
          telemetryTick = 0;
          lastTimestamp = performance.now();
        },
        getPlayerRigsSummary: () => {
          const out: Array<Record<string, unknown>> = [];
          playerRigs.forEach((rig) => {
            out.push({
              playerId: rig.options.playerId,
              side: rig.options.side,
              shirtNumber: rig.options.shirtNumber,
              label: rig.options.label,
              role: rig.options.role,
              isGoalkeeper: rig.options.isGoalkeeper,
              currentState: rig.getCurrentState(),
              lodLevel: rig.getLODLevel(),
              appearance: rig.appearance,
              position: [
                Number(rig.rootGroup.position.x.toFixed(2)),
                Number(rig.rootGroup.position.y.toFixed(2)),
                Number(rig.rootGroup.position.z.toFixed(2)),
              ],
            });
          });
          return out;
        },
      };
    }

    const renderLoop = (now: number) => {
      animationFrameId = requestAnimationFrame(renderLoop);

      const rawDeltaMs = Math.max(0.1, now - lastTimestamp);
      const deltaSec = Math.min(0.1, rawDeltaMs / 1000);
      lastTimestamp = now;

      if (rawDeltaMs < 250) {
        frameDeltaSamplesMs.push(rawDeltaMs);
        frameDeltaSumMs += rawDeltaMs;
        if (frameDeltaSamplesMs.length > 240) {
          const removed = frameDeltaSamplesMs.shift() || 0;
          frameDeltaSumMs -= removed;
        }
        applyQualityDecision(qualityGovernor.recordFrame(rawDeltaMs, deltaSec));
      }

      // Advance live match timeline monotonically (never paused by replay)
      if (!isPausedRef.current) {
        const timelineDelta = calculateTimelineAdvanceSeconds({
          currentTimeSeconds: localTimeRef.current,
          frameDeltaMs: rawDeltaMs,
          latestFrameTimeSeconds: interpolator.getEndTime(),
          isLive: isLiveRef.current,
          playbackSpeed: playbackSpeedRef.current,
        });
        localTimeRef.current += timelineDelta;
        const endTime = interpolator.getEndTime();
        if (endTime > lastEndTime + 0.01) {
          lastEndTime = endTime;
          heldAtEndSec = 0;
        }
        if (endTime > 0 && localTimeRef.current >= endTime - 0.001) {
          localTimeRef.current = endTime;
          heldAtEndSec += deltaSec;
          // A finished buffer used to pin every player on the last frame.
          // A live feed that is still adding frames keeps its end moving, so it does not restart.
          if (heldAtEndSec > 1.4) {
            localTimeRef.current = interpolator.getStartTime();
            heldAtEndSec = 0;
          }
        } else {
          heldAtEndSec = 0;
        }
        onTimeUpdateRef.current?.(localTimeRef.current);

        // If a replay window is active, advance the replay cursor independently at 0.85x slow-motion
        if (replayCursorTimeRef.current !== null && replayEndTimeRef.current !== null) {
          replayStudio.setReplayActive(true);
          replayCursorTimeRef.current += deltaSec * Math.min(0.85, playbackSpeedRef.current);
          if (replayCursorTimeRef.current >= replayEndTimeRef.current) {
            replayCursorTimeRef.current = null;
            replayEndTimeRef.current = null;
            replayStudio.setReplayActive(false);
            setIsReplayActive(false);
            setCameraMode("director_auto");
          }
        }
      }

      const localTime = localTimeRef.current;
      const sampleTime =
        replayCursorTimeRef.current !== null ? replayCursorTimeRef.current : localTime;

      // Update stadium dynamics (slot-boundary LED ad rotation + instanced crowd motion) and weather particles
      stadiumArena.update(deltaSec, localTime);
      weatherSystem.update(deltaSec);

      // Query interpolated match state at sampleTime (replay cursor during replay, live cursor otherwise)
      const state = interpolator.interpolate(sampleTime);
      const liveAuthoritativeState =
        replayCursorTimeRef.current !== null ? interpolator.interpolate(localTime) : state;
      const scoreUpdate = liveScoreRef.current;
      const hudState =
        state && scoreUpdate
          ? {
              ...state,
              home_score: scoreUpdate.home_score,
              away_score: scoreUpdate.away_score,
              clock_minute: scoreUpdate.minute ?? (liveAuthoritativeState?.clock_minute ?? state.clock_minute),
            }
          : state && liveAuthoritativeState && replayCursorTimeRef.current !== null
          ? {
              ...state,
              home_score: liveAuthoritativeState.home_score,
              away_score: liveAuthoritativeState.away_score,
              clock_minute: liveAuthoritativeState.clock_minute,
            }
          : state;
      if (now - lastUiStateUpdateMs >= 100 || !state) {
        lastUiStateUpdateMs = now;
        setCurrentTime(localTime);
        setCurrentMatchState(hudState);
      }

      const activeStatesSnapshot: Record<string, string> = {};

      if (state) {
        observedCameraPresetsHistory.add(state.camera_preset);
        const activeEvent = animationStateMachine.getEventById(state.active_event_id);

        if (replayCursorTimeRef.current === null) {
          replayStudio.recordSpatialFrame({
            timestampSec: localTime,
            clockMinute: hudState?.clock_minute ?? state.clock_minute,
            possessionSide: state.possession_side,
            ball: state.ball,
            players: state.players,
          });
        }

        // Update stadium jumbotron scoreboard and event-driven crowd reactions
        stadiumArena.updateScoreboard(
          hudState?.home_score ?? state.home_score,
          hudState?.away_score ?? state.away_score,
          `${Math.floor(hudState?.clock_minute ?? state.clock_minute)}'`,
          state.event_banner || activeEvent?.banner_text || null
        );

        const scorer = state.players.find((p) => p.animation_state === "celebrate");
        const scorerPos = scorer ? scorer.position3D : null;

        if (activeEvent && activeEvent.event_id !== lastCrowdEventIdRef.current) {
          lastCrowdEventIdRef.current = activeEvent.event_id;
          const evType = (activeEvent.event_type || "").toLowerCase();
          const evSide =
            activeEvent.team_id === safeViewRef.current.away_team.team_id
              ? "away"
              : activeEvent.team_id === safeViewRef.current.home_team.team_id
              ? "home"
              : "both";
          if (evType === "goal") {
            stadiumArena.triggerCrowdReaction("goal", evSide);
          } else if (evType === "save") {
            stadiumArena.triggerCrowdReaction("save", "both");
          } else if (evType === "miss" || evType === "shot") {
            stadiumArena.triggerCrowdReaction("near_miss", "both");
          } else if (evType === "red_card") {
            stadiumArena.triggerCrowdReaction("red_card", "both");
          } else if (evType === "fulltime") {
            stadiumArena.triggerCrowdReaction("fulltime", "both");
          } else if (evType === "attack" || evType === "penalty") {
            stadiumArena.triggerCrowdReaction("attack", evSide);
          }

          // Phase 2: Touchline manager reaction + spatial stadium audio cue
          touchlineManagers.triggerEventReaction(evType, evSide);
          audioEngineRef.current.handleMatchEvent(evType, evSide, state.ball.position3D);

          // Phase 3: Match officials, AR telestrator flash, goal-net/set-piece & ceremony reactions
          matchOfficials.triggerEventReaction(evType, state.ball.position3D);
          arOverlay.triggerEventFlash(evType);
          goalNetAndSetPieces.triggerMatchEvent(evType, evSide, state.ball.position3D);
          stadiumCeremony.triggerMatchEvent(evType);

          // Phase 4: Replay Studio bookmark, pitch turf degradation, jumbotron alerts & immersion
          replayStudio.recordBookmark({
            eventId: activeEvent.event_id,
            eventType: evType,
            timestampSec: localTime,
            clockMinute: hudState?.clock_minute ?? state.clock_minute,
            ballPosition: state.ball.position3D,
            primaryActorPosition: scorerPos,
            recommendedAngle: evType === "goal" ? "orbit_360" : evType === "red_card" ? "reverse_angle_pov" : "spidercam_overhead",
            summaryText: state.event_banner || activeEvent.banner_text || evType.toUpperCase(),
          });
          if (evType === "tackle" || evType === "foul") {
            turfDegradation.addSlideTackleDivot(state.ball.position3D[0], state.ball.position3D[2], Math.random() * Math.PI);
          }
          if (evType === "goal") {
            tifoAndJumbotron.triggerTifo("FORZA GTEX", 12);
            tifoAndJumbotron.triggerJumbotronFlash("GOAL!", "#10b981", 8);
          } else if (evType === "red_card") {
            tifoAndJumbotron.triggerJumbotronFlash("RED CARD!", "#ef4444", 6);
          } else if (evType === "var" || evType === "var_review") {
            tifoAndJumbotron.triggerJumbotronFlash("VAR CHECK", "#facc15", 8);
          }
          immersionLayer.handleMatchEvent(evType, evSide, {
            playerName: scorer?.label,
            clock: `${Math.floor(hudState?.clock_minute ?? state.clock_minute)}'`,
          });

          // React WebGL Upgrades: Camera trauma impact shake restricted strictly to goals, woodwork, major saves & red cards
          if (evType === "goal") {
            crowdChoreography.triggerCameraTrauma(0.75);
            crowdChoreography.triggerCrowdWave("celebration", 14);
          } else if (evType === "woodwork" || evType === "crossbar" || evType === "post" || evType === "save") {
            crowdChoreography.triggerCameraTrauma(0.42);
          } else if (evType === "red_card") {
            crowdChoreography.triggerCameraTrauma(0.35);
          } else if (evType === "attack") {
            crowdChoreography.triggerCrowdWave("la_ola", 10);
          }
        }

        // Update Camera first so LOD distance checks use the exact current camera pose
        let pose: CameraPose;
        if (replayCursorTimeRef.current !== null && replayEndTimeRef.current !== null) {
          const replayProgress = Math.max(0, Math.min(1, 1 - (replayEndTimeRef.current - replayCursorTimeRef.current) / 8.0));
          pose = replayStudio.computeReplayPose(deltaSec, replayProgress, state.ball.position3D, scorerPos);
        } else {
          const supportRunners = state.players
            .filter(
              (p) =>
                p.active !== false &&
                p.side === state.possession_side &&
                !p.has_possession &&
                p.role.toUpperCase() !== "GK"
            )
            .slice(0, 3)
            .map((p) => p.position3D);
          const arSummary = arOverlay.getSummary();
          const defLineX =
            state.possession_side === "home"
              ? arSummary.awayDefensiveLineX
              : arSummary.homeDefensiveLineX;
          pose = cameraDirector.update(
            deltaSec,
            state.camera_preset,
            state.ball.position3D,
            scorerPos,
            {
              ballVelocity3D: state.ball.velocity ?? null,
              eventType: activeEvent?.event_type ?? null,
              shotProbability:
                state.danger_zone === "central_box"
                  ? 0.52
                  : state.danger_zone === "wide_box"
                  ? 0.32
                  : state.danger_zone === "final_third"
                  ? 0.18
                  : 0.04,
              supportRunnerPositions3D: supportRunners,
              defensiveLineX: defLineX,
            }
          );
        }

        const crowdUpdate = crowdChoreography.update(deltaSec);
        camera.position.set(
          pose.position[0] + crowdUpdate.cameraShakeOffset[0],
          pose.position[1] + crowdUpdate.cameraShakeOffset[1],
          pose.position[2] + crowdUpdate.cameraShakeOffset[2]
        );
        camera.lookAt(pose.target[0], pose.target[1], pose.target[2]);
        camera.fov = pose.fov;
        camera.updateProjectionMatrix();

        // Update Ball (with dribble stride lead offset when controlled at player's feet)
        let [bx, by, bz] = state.ball.position3D;
        const ballOwner = state.players.find(
          (p) => p.has_possession || state.ball.owner_player_id === p.player_id
        );
        if (ballOwner && state.ball.state === "controlled") {
          const forwardX = Math.cos(ballOwner.facingAngleRad);
          const forwardZ = Math.sin(ballOwner.facingAngleRad);
          const stride = 0.36 + Math.sin(localTime * 6.2) * 0.035;
          const lateral = Math.cos(localTime * 6.2) * 0.05;
          const footX = ballOwner.position3D[0] + forwardX * stride - forwardZ * lateral;
          const footZ = ballOwner.position3D[2] + forwardZ * stride + forwardX * lateral;
          const gap = Math.hypot(bx - footX, bz - footZ);
          // Close a small visual gap to the controlling foot. Passes and shots stay on the authoritative arc.
          if (gap < 1.15 && gap > 0.001) {
            const pull = Math.min(0.42, gap * 0.55);
            bx += ((footX - bx) / gap) * pull;
            bz += ((footZ - bz) / gap) * pull;
            by = Math.min(by, 0.1);
          }
        }
        if (by < 0) by = 0;

        ballMesh.position.set(bx, by + ballLift, bz);
        const ballVelocity = state.ball.velocity;
        if (state.ball.spin) {
          ballMesh.rotation.x += state.ball.spin[0] * deltaSec * 2.4;
          ballMesh.rotation.y += state.ball.spin[1] * deltaSec * 2.4;
          ballMesh.rotation.z += state.ball.spin[2] * deltaSec * 2.4;
        } else if (ballVelocity && state.ball.state !== "controlled" && state.ball.state !== "idle") {
          ballMesh.rotation.z -= (ballVelocity[0] / ballRadius) * deltaSec;
          ballMesh.rotation.x += (ballVelocity[2] / ballRadius) * deltaSec;
        }

        // Phase 2: Detect ball kick state transitions for 3D spatial ball-strike audio
        if (state.ball.state !== lastBallStateRef.current) {
          const prevBallState = lastBallStateRef.current;
          lastBallStateRef.current = state.ball.state;
          if (
            (state.ball.state === "pass" ||
              state.ball.state === "shot" ||
              state.ball.state === "cross" ||
              state.ball.state === "lob" ||
              state.ball.state === "clearance") &&
            prevBallState !== state.ball.state
          ) {
            audioEngineRef.current.playBallKick(
              [bx, by, bz],
              state.ball.state === "shot" ? 0.95 : 0.65
            );
          }
        }

        // Phase 2: Update Touchline Managers & Crowd Ambience Audio
        touchlineManagers.update({
          deltaSec,
          ballPosition3D: [bx, by, bz],
          cameraPosition3D: pose.position,
          possessionSide: state.possession_side,
          qualityTier,
        });
        audioEngineRef.current.updateCrowdAmbience(stadiumArena.getCrowdReactionState().intensity);

        // Phase 3: Update Match Officials, 3D Broadcast AR Overlays, Goal-Net Physics & Ceremony
        matchOfficials.update({
          deltaSec,
          ballPosition3D: [bx, by, bz],
          players: state.players,
          cameraPosition3D: pose.position,
          qualityTier,
        });
        arOverlay.update({
          deltaSec,
          players: state.players,
          ballPosition3D: [bx, by, bz],
          possessionSide: state.possession_side,
        });
        goalNetAndSetPieces.update(deltaSec, [bx, by, bz]);
        stadiumCeremony.update(deltaSec);

        // Phase 4: Update Turf Degradation, Jumbotrons/Tifo & Immersion Layer
        turfDegradation.update({
          deltaSec,
          clockMinute: hudState?.clock_minute ?? state.clock_minute,
          weatherPreset: weatherPresetRef.current,
          ballPosition3D: [bx, by, bz],
          ballVelocity: state.ball.velocity ?? null,
        });
        tifoAndJumbotron.update(deltaSec, {
          homeScore: hudState?.home_score ?? state.home_score,
          awayScore: hudState?.away_score ?? state.away_score,
          clockMinute: hudState?.clock_minute ?? state.clock_minute,
          eventBanner: state.event_banner,
          phase: state.phase,
        });
        immersionLayer.update(deltaSec);
        setCommentaryCue(immersionLayer.getCurrentCommentaryCue());
        setSpectatorReactions(immersionLayer.getRecentReactions());
        setWatchPartyCheerMeter(immersionLayer.getSummary().cheerMeter);

        // React WebGL Upgrades: Update PBR turf anisotropic sheen & moisture
        pbrTurf.setMoisture(weatherPresetRef.current === "rain" ? 0.8 : weatherPresetRef.current === "snow" ? 0.45 : 0.0);
        pbrTurf.setWearFactor(hudState?.clock_minute ? Math.min(1.0, hudState.clock_minute / 90.0) : 0);
        pbrTurf.update(deltaSec, keyLight.position);

        // Update ball drop shadow
        ballShadowMesh.position.set(bx, 0.03, bz);
        const shadowScale = Math.max(0.4, 1.0 - by * 0.15);
        ballShadowMesh.scale.set(shadowScale, shadowScale, 1);
        (ballShadowMesh.material as THREE.MeshBasicMaterial).opacity = Math.max(
          0.1,
          0.6 - by * 0.1
        );

        // Update 22 Rigged Humanoid Players & Skeletal Animations
        activePlayerIdsScratch.clear();
        for (const p of state.players) {
          if (p.active === false) continue;
          activePlayerIdsScratch.add(p.player_id);
          const isGK = p.role.toUpperCase() === "GK" || p.role.toLowerCase() === "goalkeeper";
          const rig = getOrCreatePlayerRig(
            p.player_id,
            p.side,
            p.shirt_number ?? 10,
            p.label,
            p.role,
            isGK
          );

          rig.rootGroup.visible = true;
          const targetAnimState = animationStateMachine.resolvePlayerState({
            player: p,
            allPlayers: state.players,
            ball: state.ball,
            matchState: state,
            activeEvent,
            previousState: rig.getCurrentState(),
            timeInCurrentStateSec: rig.getTimeInCurrentState(),
          });

          rig.update({
            deltaSec,
            targetState: targetAnimState,
            position3D: p.position3D,
            facingAngleRad: p.facingAngleRad,
            speedRatio: p.speed_ratio,
            angularVelocityRad: p.angular_velocity_rad,
            hasPossession: p.has_possession,
            ballPosition3D: [bx, by, bz],
            cameraPosition3D: pose.position,
            qualityTier,
          });

          const resolvedState = rig.getCurrentState();
          activeStatesSnapshot[p.player_id] = resolvedState;
          observedStatesHistory.add(resolvedState);
        }

        // Hide inactive/substituted player rigs
        playerRigs.forEach((rig, id) => {
          if (!activePlayerIdsScratch.has(id)) {
            rig.rootGroup.visible = false;
          }
        });

        // Swap distant active players to the single-draw-call impostor batch
        impostorCandidatesScratch.length = 0;
        playerRigs.forEach((rig, id) => {
          if (!activePlayerIdsScratch.has(id)) return;
          const kit = rig.options;
          impostorCandidatesScratch.push({
            id,
            rootObject: rig.rootGroup,
            colorHex: kit.isGoalkeeper ? kit.goalkeeperColor : kit.primaryColor,
          });
        });
        playerImpostors.update(camera, impostorCandidatesScratch);

        // Dynamic shadows follow the ball; IBL reflections strengthen on a wet pitch
        shadowRig.update(deltaSec, [bx, by, bz]);
        stadiumEnvLighting.setFloodlightBoost(weatherPresetRef.current === "rain" ? 1.4 : 1.0);

        // Replays get a shallow depth of field focused on the ball; live play stays sharp
        const replayActiveNow = replayCursorTimeRef.current !== null;
        const ballDist = Math.hypot(
          camera.position.x - bx,
          camera.position.y - by,
          camera.position.z - bz
        );
        postProcessing.setDepthOfField(replayActiveNow, ballDist, replayActiveNow ? 10 : 18);
        postProcessing.setMotionBlur(replayActiveNow, replayActiveNow ? 0.28 : 0);
      }

      if (renderer) {
        postProcessing.render(deltaSec);

        if (typeof window !== "undefined" && frameDeltaSamplesMs.length > 0) {
          telemetryTick++;
          const sampleCount = frameDeltaSamplesMs.length;
          const avgFrameMs = frameDeltaSumMs / sampleCount;

          // Throttle O(N log N) percentile sorting to once every 15 frames (~250ms) to avoid per-frame CPU/GC stalls
          if (telemetryTick % 15 === 1 || sampleCount <= 5) {
            const sorted = frameDeltaSamplesMs.slice().sort((a, b) => a - b);
            cachedP50Ms = sorted[Math.floor(sampleCount * 0.5)] || avgFrameMs;
            cachedP95Ms = sorted[Math.floor(sampleCount * 0.95)] || avgFrameMs;
            cachedP99Ms = sorted[Math.floor(sampleCount * 0.99)] || avgFrameMs;
            const worstSliceStart = Math.max(0, Math.floor(sampleCount * 0.99));
            let worstSum = 0;
            let worstCount = 0;
            for (let wi = worstSliceStart; wi < sampleCount; wi++) {
              worstSum += sorted[wi];
              worstCount++;
            }
            cachedWorstOnePctAvgMs = worstCount > 0 ? worstSum / worstCount : avgFrameMs;
          }

          if (telemetryTick % 5 === 1 || sampleCount <= 5) {
            const perfMem = (performance as any).memory;
            (window as any).__GTEX_BROADCAST_TELEMETRY__ = {
              gpuVendor,
              gpuRenderer,
              canvasWidth: renderer.domElement.width,
              canvasHeight: renderer.domElement.height,
              clientWidth: container.clientWidth,
              clientHeight: container.clientHeight,
              pixelRatio: renderer.getPixelRatio(),
              qualityTier,
              frameCount: sampleCount,
              avgFps: Number((1000 / Math.max(0.1, avgFrameMs)).toFixed(1)),
              onePercentLowFps: Number((1000 / Math.max(0.1, cachedWorstOnePctAvgMs)).toFixed(1)),
              p50FrameMs: Number(cachedP50Ms.toFixed(2)),
              p95FrameMs: Number(cachedP95Ms.toFixed(2)),
              p99FrameMs: Number(cachedP99Ms.toFixed(2)),
              drawCalls: renderer.info.render.calls,
              triangles: renderer.info.render.triangles,
              geometries: renderer.info.memory.geometries,
              textures: renderer.info.memory.textures,
              jsHeapUsedMb: perfMem
                ? Number((perfMem.usedJSHeapSize / (1024 * 1024)).toFixed(2))
                : null,
              jsHeapTotalMb: perfMem
                ? Number((perfMem.totalJSHeapSize / (1024 * 1024)).toFixed(2))
                : null,
              currentTime: Number(localTime.toFixed(2)),
              durationSeconds: interpolator.getEndTime(),
              activeRigCount: playerRigs.size,
              cameraPreset: state?.camera_preset || "broadcast",
              clockLabel: `${state?.clock_minute ?? 0}'`,
              score: {
                home: state?.home_score ?? 0,
                away: state?.away_score ?? 0,
              },
              activeAnimationStates: activeStatesSnapshot,
              observedStatesHistory: Array.from(observedStatesHistory),
              observedCameraPresetsHistory: Array.from(observedCameraPresetsHistory),
              crowdReaction: stadiumArena.getCrowdReactionState(),
              stadiumTier: stadiumArena.getStadiumTierProfile(),
              weather: weatherSystem.getTelemetry(),
              touchlineManagers: touchlineManagers.getSummary(),
              spatialAudio: audioEngineRef.current.getTelemetry(),
              matchOfficials: matchOfficials.getSummary(),
              arOverlay: arOverlay.getSummary(),
              goalNetAndSetPieces: goalNetAndSetPieces.getSummary(),
              stadiumCeremony: stadiumCeremony.getSummary(),
              replayStudio: replayStudio.getSummary(),
              turfDegradation: turfDegradation.getSummary(),
              tifoAndJumbotron: tifoAndJumbotron.getSummary(),
              immersionLayer: immersionLayer.getSummary(),
              postProcessing: postProcessing.getSummary(),
              pbrTurf: pbrTurf.getSummary(),
              crowdChoreography: crowdChoreography.getSummary(),
              webGpuReport: webGpuBridge.getReport(),
              environmentLighting: stadiumEnvLighting.getSummary(),
              dynamicShadows: shadowRig.getSummary(),
              playerImpostors: playerImpostors.getSummary(),
              adaptiveQuality: qualityGovernor.getSummary(),
              assetCache: AssetStreamingCache.getInstance().getSummary(),
              adRotationCount: adNet.getRotationCount(),
              adImpressionCount: adNet.getImpressionHistory().length,
              activeAdCampaigns: adNet.getActiveCampaigns().map((c) => ({
                id: c.id,
                brandName: c.brandName,
                headline: c.headline,
                source: c.source,
              })),
            };
          }
        }
      }
    };

    animationFrameId = requestAnimationFrame(renderLoop);

    // Resize observer for both window and 16:9 / Theatre container transitions
    const handleResize = () => {
      if (!container || !renderer) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      if (w > 0 && h > 0) {
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
        renderer.setSize(w, h);
        postProcessing.setSize(w, h);
      }
    };
    window.addEventListener("resize", handleResize);
    let resizeObserver: ResizeObserver | null = null;
    if (typeof ResizeObserver !== "undefined") {
      resizeObserver = new ResizeObserver(handleResize);
      resizeObserver.observe(container);
    }

    // Cleanup on unmount
    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener("resize", handleResize);
      if (typeof document !== "undefined") {
        document.removeEventListener("visibilitychange", handleVisibilityChange);
      }
      resizeObserver?.disconnect();
      canvasElement.removeEventListener("webglcontextlost", handleContextLost);
      canvasElement.removeEventListener("webglcontextrestored", handleContextRestored);

      // Dispose Three.js objects
      stadiumArenaRef.current = null;
      weatherSystemRef.current = null;
      touchlineManagerRef.current = null;
      matchOfficialsRef.current = null;
      arOverlayRef.current = null;
      goalNetAndSetPiecesRef.current = null;
      stadiumCeremonyRef.current = null;
      replayStudioRef.current = null;
      turfDegradationRef.current = null;
      tifoAndJumbotronRef.current = null;
      immersionLayerRef.current = null;
      postProcessingRef.current = null;
      pbrTurfRef.current = null;
      crowdChoreographyRef.current = null;
      webGpuBridgeRef.current = null;
      playerRigs.forEach((rig) => rig.dispose());
      playerRigs.clear();
      scene.clear();
      stadiumArena.dispose();
      weatherSystem.dispose();
      touchlineManagers.dispose();
      matchOfficials.dispose();
      arOverlay.dispose();
      goalNetAndSetPieces.dispose();
      stadiumCeremony.dispose();
      replayStudio.dispose();
      turfDegradation.dispose();
      tifoAndJumbotron.dispose();
      immersionLayer.dispose();
      postProcessing.dispose();
      pbrTurf.dispose();
      crowdChoreography.dispose();
      stadiumArena.setExternalCrowdOffsetFn(null);
      stadiumEnvLightingRef.current = null;
      stadiumEnvLighting.dispose();
      playerImpostors.dispose();
      qualityGovernorRef.current = null;
      ballGeo.dispose();
      ballMat.dispose();
      shadowGeo.dispose();
      shadowMat.dispose();
      if (renderer) {
        renderer.dispose();
        if (renderer.domElement.parentNode) {
          renderer.domElement.parentNode.removeChild(renderer.domElement);
        }
      }
    };
  }, [qualityTier, cameraDirector, interpolator, animationStateMachine, handleSelectQualityTier, handleSelectStadiumTier, handleSelectWeatherPreset, is2DActive, adRotationIntervalSec, onAdImpressionRecorded]);

  // Resolve active HUD event from either timeline or live stream
  const activeHudEvent = useMemo(() => {
    if (currentMatchState?.active_event_id) {
      const fromTimeline = animationStateMachine.getEventById(currentMatchState.active_event_id);
      if (fromTimeline) return fromTimeline;
    }
    return liveEvents[0] ?? null;
  }, [currentMatchState?.active_event_id, animationStateMachine, liveEvents]);

  // Handle 2D companion mode toggle and context recovery
  const handleToggle2D = useCallback(() => {
    setIs2DActive((prev) => !prev);
    setContextLost(false);
    onToggle2DCompanion?.();
  }, [onToggle2DCompanion]);

  // Handle 8-second Non-Disruptive Action Replay toggle
  const handleTriggerReplay = useCallback(() => {
    if (isReplayActive) {
      replayCursorTimeRef.current = null;
      replayEndTimeRef.current = null;
      replayStudioRef.current?.setReplayActive(false);
      setIsReplayActive(false);
      setReplayFallbackMessage(null);
      setCameraMode("director_auto");
    } else {
      if (interpolator.getFrameCount() < 2) {
        setReplayFallbackMessage("EVENT SUMMARY ONLY — SPATIAL REPLAY HISTORY UNAVAILABLE");
        setIsReplayActive(true);
        return;
      }
      setReplayFallbackMessage(null);
      const liveNow = localTimeRef.current;
      replayEndTimeRef.current = liveNow;
      const rewindTo = Math.max(interpolator.getStartTime(), liveNow - 8.0);
      replayCursorTimeRef.current = rewindTo;
      replayStudioRef.current?.setReplayActive(true);
      setIsReplayActive(true);
      setCameraMode("replay_cam");
    }
  }, [isReplayActive, interpolator]);

  // ---------------------------------------------------------------------------
  // Fallback presentation when WebGL is unavailable or user toggles 2D
  // ---------------------------------------------------------------------------
  if (!webglSupported || contextLost || is2DActive) {
    return (
      <div
        data-testid={`${testId}-fallback-container`}
        className={`relative w-full overflow-hidden rounded-xl border border-emerald-500/30 bg-[#060a12] p-4 text-white shadow-2xl ${className}`}
      >
        <div className="flex items-center justify-between border-b border-white/10 pb-3">
          <div>
            <span className="rounded bg-emerald-500/20 px-2 py-0.5 text-xs font-mono font-bold text-emerald-400">
              2D TACTICAL COMPANION MODE
            </span>
            <h3 className="mt-1 text-lg font-bold text-slate-100">{safeView.match_label}</h3>
          </div>
          <button
            type="button"
            data-testid="return-to-3d-broadcast-button"
            onClick={handleToggle2D}
            className="rounded-lg bg-emerald-500 px-3 py-1.5 text-xs font-bold text-slate-950 hover:bg-emerald-400 transition-colors"
          >
            SWITCH TO 3D BROADCAST
          </button>
        </div>

        {/* 2D Pitch Canvas / SVG Companion */}
        <div className="relative my-4 aspect-[16/9] w-full rounded-lg border border-white/10 bg-emerald-950/40 p-4">
          <div className="relative h-full w-full rounded border-2 border-white/40">
            <div className="absolute inset-y-0 left-1/2 w-0.5 bg-white/40" />
            <div className="absolute left-1/2 top-1/2 size-20 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white/40" />

            {/* Render 2D Player Dots */}
            {currentMatchState?.players.map((p) => {
              const leftPct = ((p.position3D[0] + 52.5) / 105.0) * 100;
              const topPct = ((p.position3D[2] + 34.0) / 68.0) * 100;
              const color = p.side === "home" ? safeView.home_team.primary_color : safeView.away_team.primary_color;

              return (
                <div
                  key={p.player_id}
                  className="absolute size-3 -translate-x-1/2 -translate-y-1/2 rounded-full shadow-md text-[8px] font-mono font-bold flex items-center justify-center text-slate-950"
                  style={{
                    left: `${leftPct}%`,
                    top: `${topPct}%`,
                    backgroundColor: color,
                  }}
                  title={`${p.label} (${p.role})`}
                >
                  {p.shirt_number}
                </div>
              );
            })}

            {/* Ball Marker */}
            {currentMatchState?.ball && (
              <div
                className="absolute size-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white ring-2 ring-amber-400"
                style={{
                  left: `${((currentMatchState.ball.position3D[0] + 52.5) / 105.0) * 100}%`,
                  top: `${((currentMatchState.ball.position3D[2] + 34.0) / 68.0) * 100}%`,
                }}
              />
            )}
          </div>
        </div>

        <BroadcastOverlayHUD
          matchState={currentMatchState}
          homeTeam={safeView.home_team}
          awayTeam={safeView.away_team}
          matchLabel={safeView.match_label}
          competitionName={safeView.competition_name}
          isDemonstrationFixture={safeView.is_demonstration_fixture}
          activeEvent={activeHudEvent}
          liveEventBanner={liveEvents[0]?.banner_text || liveEvents[0]?.commentary || undefined}
          isLive={isLive}
          viewerCount={viewerCount}
          cameraMode={cameraMode}
          onSelectCameraMode={setCameraMode}
          onToggle2DFallback={handleToggle2D}
          is2DActive={true}
          audioMuted={audioMuted}
          onToggleAudio={() => setAudioMuted((m) => !m)}
          qualityTier={qualityTier}
          onSelectQualityTier={handleSelectQualityTier}
          stadiumTier={stadiumTier}
          onSelectStadiumTier={handleSelectStadiumTier}
          weatherPreset={weatherPreset}
          onSelectWeatherPreset={handleSelectWeatherPreset}
          arOverlayMode={arOverlayMode}
          onSelectArOverlayMode={handleSelectArOverlayMode}
          replayStudioAngle={replayStudioAngle}
          onSelectReplayStudioAngle={handleSelectReplayStudioAngle}
          commentaryCue={commentaryCue}
          spectatorReactions={spectatorReactions}
          watchPartyCheerMeter={watchPartyCheerMeter}
          hapticsEnabled={hapticsEnabled}
          onToggleHaptics={handleToggleHaptics}
          onSendReaction={handleSendReaction}
          bloomEnabled={bloomEnabled}
          onToggleBloom={handleToggleBloom}
          isTheatreMode={isTheatreMode}
          onToggleTheatreMode={handleToggleTheatre}
          minimalHud={minimalHud}
          onToggleMinimalHud={() => setMinimalHud((h) => !h)}
          isReplayActive={isReplayActive}
          replayFallbackMessage={replayFallbackMessage}
          onTriggerReplay={handleTriggerReplay}
          activeSponsorName={activeSponsorName}
        />
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Primary 16:9 3D WebGL Broadcast Viewport & Full-Screen Match Theatre
  // ---------------------------------------------------------------------------
  return (
    <div
      data-testid={testId}
      data-theatre-mode={isTheatreMode ? "true" : "false"}
      className={
        isTheatreMode
          ? "fixed inset-0 z-50 flex items-center justify-center bg-black"
          : `relative aspect-video min-h-[360px] w-full overflow-hidden rounded-xl border border-white/10 bg-slate-950 shadow-2xl ${className}`
      }
    >
      <div
        className={
          isTheatreMode
            ? "relative aspect-video max-h-screen w-full max-w-[177.78vh] overflow-hidden bg-slate-950 shadow-2xl"
            : "relative h-full w-full"
        }
      >
        {/* Three.js Canvas Mount */}
        <div ref={mountRef} className="h-full w-full" />

        {/* Broadcast Overlay HUD */}
        <BroadcastOverlayHUD
          matchState={currentMatchState}
          homeTeam={safeView.home_team}
          awayTeam={safeView.away_team}
          matchLabel={safeView.match_label}
          competitionName={safeView.competition_name}
          isDemonstrationFixture={safeView.is_demonstration_fixture}
          activeEvent={activeHudEvent}
          liveEventBanner={liveEvents[0]?.banner_text || liveEvents[0]?.commentary || undefined}
          isLive={isLive}
          viewerCount={viewerCount}
          cameraMode={cameraMode}
          onSelectCameraMode={setCameraMode}
          onToggle2DFallback={handleToggle2D}
          is2DActive={false}
          audioMuted={audioMuted}
          onToggleAudio={() => setAudioMuted((m) => !m)}
          qualityTier={qualityTier}
          onSelectQualityTier={handleSelectQualityTier}
          stadiumTier={stadiumTier}
          onSelectStadiumTier={handleSelectStadiumTier}
          weatherPreset={weatherPreset}
          onSelectWeatherPreset={handleSelectWeatherPreset}
          arOverlayMode={arOverlayMode}
          onSelectArOverlayMode={handleSelectArOverlayMode}
          replayStudioAngle={replayStudioAngle}
          onSelectReplayStudioAngle={handleSelectReplayStudioAngle}
          commentaryCue={commentaryCue}
          spectatorReactions={spectatorReactions}
          watchPartyCheerMeter={watchPartyCheerMeter}
          hapticsEnabled={hapticsEnabled}
          onToggleHaptics={handleToggleHaptics}
          onSendReaction={handleSendReaction}
          bloomEnabled={bloomEnabled}
          onToggleBloom={handleToggleBloom}
          isTheatreMode={isTheatreMode}
          onToggleTheatreMode={handleToggleTheatre}
          minimalHud={minimalHud}
          onToggleMinimalHud={() => setMinimalHud((h) => !h)}
          isReplayActive={isReplayActive}
          replayFallbackMessage={replayFallbackMessage}
          onTriggerReplay={handleTriggerReplay}
          activeSponsorName={activeSponsorName}
        />
      </div>
    </div>
  );
};

// Register renderer in GtexSceneRegistry for generic decoupled viewport resolution
GtexSceneRegistry.registerRenderer("stadium_match_broadcast", MatchPitchLiveScene);
