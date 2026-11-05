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
 */

import React, { useEffect, useRef, useState, useMemo, useCallback } from "react";
import * as THREE from "three";
import { FIFA_PITCH_DIMENSIONS, pitchTo3D, PITCH_BOUNDS } from "./matchCoordinates";
import { SpatialInterpolator, InterpolatedMatchState } from "./SpatialInterpolator";
import { CameraDirector, ManualCameraMode } from "./CameraDirector";
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
import { StadiumArenaEnvironment } from "./StadiumArenaEnvironment";
import { HumanoidFootballerRig } from "./HumanoidFootballerRig";
import { FootballAnimationStateMachine } from "./FootballAnimationStateMachine";

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
  onTimeUpdate,
  onToggle2DCompanion,
  isTheatreMode: externalTheatreMode,
  onToggleTheatreMode,
  onQualityTierChange,
  className = "",
  testId = "match-pitch-live-scene",
}) => {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const [webglSupported, setWebglSupported] = useState<boolean>(true);
  const [contextLost, setContextLost] = useState<boolean>(false);
  const [cameraMode, setCameraMode] = useState<ManualCameraMode>("director_auto");
  const [is2DActive, setIs2DActive] = useState<boolean>(false);
  const [audioMuted, setAudioMuted] = useState<boolean>(false);
  const [qualityTier, setQualityTierState] = useState<DeviceQualityTier>(propQualityTier);
  const [internalTheatreMode, setInternalTheatreMode] = useState<boolean>(false);
  const [minimalHud, setMinimalHud] = useState<boolean>(false);
  const [isReplayActive, setIsReplayActive] = useState<boolean>(false);
  const replayReturnTimeRef = useRef<number | null>(null);

  const isTheatreMode = externalTheatreMode ?? internalTheatreMode;

  useEffect(() => {
    setQualityTierState(propQualityTier);
  }, [propQualityTier]);

  const handleSelectQualityTier = useCallback(
    (tier: "high" | "medium" | "low") => {
      setQualityTierState(tier);
      onQualityTierChange?.(tier);
    },
    [onQualityTierChange]
  );

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
  const localTimeRef = useRef<number>(currentTime);

  useEffect(() => {
    safeViewRef.current = safeView;
    interpolator.setFrames(safeView.frames);
  }, [safeView, interpolator]);

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

  // ---------------------------------------------------------------------------
  // Three.js WebGL Scene Lifecycle
  // ---------------------------------------------------------------------------
  useEffect(() => {
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
    scene.background = new THREE.Color("#07101e");
    scene.fog = new THREE.FogExp2("#07101e", 0.0022);

    const camera = new THREE.PerspectiveCamera(38, width / height, 0.5, 300);
    camera.position.set(0, 32, 55);
    camera.lookAt(0, 0, 0);

    let renderer: THREE.WebGLRenderer | null = null;
    try {
      renderer = new THREE.WebGLRenderer({
        antialias: qualityTier === "high" || qualityTier === "ultra",
        powerPreference: "high-performance",
      });
      renderer.setSize(width, height);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, qualityTier === "ultra" ? 2.0 : 1.5));
      if (qualityTier === "high" || qualityTier === "ultra") {
        renderer.shadowMap.enabled = true;
        renderer.shadowMap.type = THREE.PCFSoftShadowMap;
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
    // 2. Comprehensive Stadium & Pitch Environment (Milestone 2 Expansion)
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
      stadiumName: safeViewRef.current.venue_name || "GTEX National Arena",
    });

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

    const playerRigs = new Map<string, HumanoidFootballerRig>();

    const getOrCreatePlayerRig = (
      playerId: string,
      side: "home" | "away",
      shirtNum: number = 10,
      label: string = "Player",
      role: string = "MID",
      isGK: boolean = false
    ): HumanoidFootballerRig => {
      if (playerRigs.has(playerId)) {
        return playerRigs.get(playerId)!;
      }

      const currentSafeView = safeViewRef.current;
      const teamView = side === "home" ? currentSafeView.home_team : currentSafeView.away_team;
      const rig = new HumanoidFootballerRig({
        playerId,
        side,
        shirtNumber: shirtNum,
        label,
        role,
        isGoalkeeper: isGK,
        primaryColor: teamView.primary_color,
        secondaryColor: teamView.secondary_color,
        accentColor: teamView.accent_color,
        goalkeeperColor: teamView.goalkeeper_color,
      });

      playersGroup.add(rig.rootGroup);
      playerRigs.set(playerId, rig);
      return rig;
    };

    // -------------------------------------------------------------------------
    // 5. 3D Ball Mesh & Dynamic Drop Shadow
    // -------------------------------------------------------------------------
    const ballGroup = new THREE.Group();
    scene.add(ballGroup);

    const ballRadius = 0.22;
    const ballGeo = new THREE.SphereGeometry(ballRadius, 16, 16);
    const ballMat = new THREE.MeshStandardMaterial({
      color: 0xffffff,
      roughness: 0.2,
      metalness: 0.1,
    });
    const ballMesh = new THREE.Mesh(ballGeo, ballMat);
    ballMesh.castShadow = true;
    ballGroup.add(ballMesh);

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
    const frameDeltaSamplesMs: number[] = [];
    let frameDeltaSumMs = 0;
    let telemetryTick = 0;
    let cachedP50Ms = 16.6;
    let cachedP95Ms = 16.6;
    let cachedP99Ms = 16.6;
    let cachedWorstOnePctAvgMs = 16.6;
    const observedStatesHistory = new Set<string>();
    const observedCameraPresetsHistory = new Set<string>();
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
        setQualityTier: (tier: "high" | "medium" | "low") => {
          handleSelectQualityTier(tier);
        },
        setTheatreMode: (enabled: boolean) => {
          setInternalTheatreMode(enabled);
        },
        triggerReplay: () => {
          const liveNow = localTimeRef.current;
          replayReturnTimeRef.current = liveNow;
          const rewindTo = Math.max(interpolator.getStartTime(), liveNow - 8.0);
          localTimeRef.current = rewindTo;
          setCurrentTime(rewindTo);
          setIsReplayActive(true);
          setCameraMode("closeup_action");
        },
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
        if (frameDeltaSamplesMs.length > 3600) {
          const removed = frameDeltaSamplesMs.shift() || 0;
          frameDeltaSumMs -= removed;
        }
      }

      // Update stadium dynamics (GPU UV offset LED ad boards)
      stadiumArena.update(deltaSec);

      // Advance time if live or playing
      if (!isPausedRef.current) {
        const effectiveSpeed =
          replayReturnTimeRef.current !== null ? Math.min(0.85, playbackSpeedRef.current) : playbackSpeedRef.current;
        localTimeRef.current += deltaSec * effectiveSpeed;
        if (replayReturnTimeRef.current !== null && localTimeRef.current >= replayReturnTimeRef.current) {
          localTimeRef.current = replayReturnTimeRef.current;
          replayReturnTimeRef.current = null;
          setIsReplayActive(false);
          setCameraMode("director_auto");
        }
        const endTime = interpolator.getEndTime();
        if (endTime > 0 && localTimeRef.current > endTime) {
          localTimeRef.current = isLiveRef.current ? endTime : interpolator.getStartTime();
        }
        onTimeUpdateRef.current?.(localTimeRef.current);
      }

      const localTime = localTimeRef.current;

      // Query interpolated match state at localTime
      const state = interpolator.interpolate(localTime);
      if (now - lastUiStateUpdateMs >= 100 || !state) {
        lastUiStateUpdateMs = now;
        setCurrentTime(localTime);
        setCurrentMatchState(state);
      }

      const activeStatesSnapshot: Record<string, string> = {};

      if (state) {
        observedCameraPresetsHistory.add(state.camera_preset);
        const activeEvent = animationStateMachine.getEventById(state.active_event_id);

        // Update Camera first so LOD distance checks use the exact current camera pose
        const scorer = state.players.find((p) => p.animation_state === "celebrate");
        const scorerPos = scorer ? scorer.position3D : null;
        const pose = cameraDirector.update(
          deltaSec,
          state.camera_preset,
          state.ball.position3D,
          scorerPos
        );

        camera.position.set(pose.position[0], pose.position[1], pose.position[2]);
        camera.lookAt(pose.target[0], pose.target[1], pose.target[2]);
        camera.fov = pose.fov;
        camera.updateProjectionMatrix();

        // Update Ball (with dribble stride lead offset when controlled at player's feet)
        let [bx, by, bz] = state.ball.position3D;
        const ballOwner = state.players.find(
          (p) => p.has_possession || state.ball.owner_player_id === p.player_id
        );
        if (ballOwner && state.ball.state === "controlled" && by < 0.25) {
          const distToOwner = Math.hypot(bx - ballOwner.position3D[0], bz - ballOwner.position3D[2]);
          if (distToOwner < 0.35) {
            const strideLead = 0.42 + Math.sin(localTime * 9.5) * 0.08 * ballOwner.speed_ratio;
            bx = ballOwner.position3D[0] + Math.cos(ballOwner.facingAngleRad) * strideLead;
            bz = ballOwner.position3D[2] + Math.sin(ballOwner.facingAngleRad) * strideLead;
          }
        }

        ballMesh.position.set(bx, by + ballRadius, bz);
        if (state.ball.spin) {
          ballMesh.rotation.x += state.ball.spin[0] * deltaSec * 8.0;
          ballMesh.rotation.y += state.ball.spin[1] * deltaSec * 8.0;
          ballMesh.rotation.z += state.ball.spin[2] * deltaSec * 8.0;
        } else if (state.ball.state !== "idle") {
          ballMesh.rotation.x += deltaSec * 4.5;
          ballMesh.rotation.z -= deltaSec * 3.2;
        }

        // Update ball drop shadow
        ballShadowMesh.position.set(bx, 0.03, bz);
        const shadowScale = Math.max(0.4, 1.0 - by * 0.15);
        ballShadowMesh.scale.set(shadowScale, shadowScale, 1);
        (ballShadowMesh.material as THREE.MeshBasicMaterial).opacity = Math.max(
          0.1,
          0.6 - by * 0.1
        );

        // Update 22 Rigged Humanoid Players & Skeletal Animations
        const activeIds = new Set<string>();
        for (const p of state.players) {
          if (p.active === false) continue;
          activeIds.add(p.player_id);
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
          if (!activeIds.has(id)) {
            rig.rootGroup.visible = false;
          }
        });
      }

      if (renderer) {
        renderer.render(scene, camera);

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
      resizeObserver?.disconnect();
      canvasElement.removeEventListener("webglcontextlost", handleContextLost);
      canvasElement.removeEventListener("webglcontextrestored", handleContextRestored);

      // Dispose Three.js objects
      playerRigs.forEach((rig) => rig.dispose());
      playerRigs.clear();
      scene.clear();
      stadiumArena.dispose();
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
  }, [qualityTier, cameraDirector, interpolator, animationStateMachine, handleSelectQualityTier]);

  // Handle 2D companion mode toggle
  const handleToggle2D = useCallback(() => {
    setIs2DActive((prev) => !prev);
    onToggle2DCompanion?.();
  }, [onToggle2DCompanion]);

  // Handle 8-second Action Replay toggle
  const handleTriggerReplay = useCallback(() => {
    if (isReplayActive && replayReturnTimeRef.current !== null) {
      localTimeRef.current = replayReturnTimeRef.current;
      replayReturnTimeRef.current = null;
      setIsReplayActive(false);
      setCameraMode("director_auto");
    } else {
      const liveNow = localTimeRef.current;
      replayReturnTimeRef.current = liveNow;
      const rewindTo = Math.max(interpolator.getStartTime(), liveNow - 8.0);
      localTimeRef.current = rewindTo;
      setCurrentTime(rewindTo);
      setIsReplayActive(true);
      setCameraMode("closeup_action");
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
          isTheatreMode={isTheatreMode}
          onToggleTheatreMode={handleToggleTheatre}
          minimalHud={minimalHud}
          onToggleMinimalHud={() => setMinimalHud((h) => !h)}
          isReplayActive={isReplayActive}
          onTriggerReplay={handleTriggerReplay}
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
          isTheatreMode={isTheatreMode}
          onToggleTheatreMode={handleToggleTheatre}
          minimalHud={minimalHud}
          onToggleMinimalHud={() => setMinimalHud((h) => !h)}
          isReplayActive={isReplayActive}
          onTriggerReplay={handleTriggerReplay}
        />
      </div>
    </div>
  );
};

// Register renderer in GtexSceneRegistry for generic decoupled viewport resolution
GtexSceneRegistry.registerRenderer("stadium_match_broadcast", MatchPitchLiveScene);
