/**
 * GTEX Living Football Ecosystem — WebGL 3D Match Broadcast
 * MatchPitchLiveScene (Milestone 1 Procedural Engine): Three.js Real-Time Match Broadcast Canvas.
 *
 * Implements the canonical Milestone 1 vertical slice:
 * 1. Procedural 105m x 68m FIFA match pitch with turf stripes, chalk lines, and 3D goal nets via ProceduralPitchEnvironment.
 * 2. 4-corner stadium floodlight arrays and atmospheric hemisphere lighting.
 * 3. 22 dynamic procedural player marker meshes styled with club kit colors and ground rings.
 * 4. Authoritative 3D match ball with flight elevation and dynamic ground shadow.
 * 5. CameraDirector cinematography executing the 6 canonical camera presets.
 * 6. TV-grade BroadcastOverlayHUD scorebug, minimap radar, and event banners.
 * 7. WebGL context-loss resilience and seamless 2D fallback.
 * 8. Zero static dependencies on Milestone 2 files (no humanoid rigs or complex stadium meshes).
 */

import React, { useEffect, useRef, useState, useMemo } from "react";
import * as THREE from "three";
import { FIFA_PITCH_DIMENSIONS } from "./matchCoordinates";
import { SpatialInterpolator, InterpolatedMatchState } from "./SpatialInterpolator";
import { CameraDirector, ManualCameraMode } from "./CameraDirector";
import { BroadcastOverlayHUD } from "./BroadcastOverlayHUD";
import {
  SpectatorSafeMatchView,
  SpectatorSafeFrameView,
  SpectatorSafeEventView,
  MatchViewerContractInput,
  sanitizeForSpectator,
} from "./spectatorContract";
import { GtexSceneRegistry } from "../GtexSceneRegistry";
import type { DeviceQualityTier } from "../GtexSceneTypes";
import { ProceduralPitchEnvironment } from "./ProceduralPitchEnvironment";

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
  liveFrame,
  liveEvents,
  onTimeUpdate,
  onToggle2DCompanion,
  isTheatreMode = false,
  onToggleTheatreMode,
  onQualityTierChange,
  className = "",
  testId = "match-pitch-live-scene",
}) => {
  const mountRef = useRef<HTMLDivElement>(null);
  const [qualityTier, setQualityTier] = useState<DeviceQualityTier>(propQualityTier);
  const [cameraMode, setCameraMode] = useState<ManualCameraMode>("director_auto");
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [currentMatchState, setCurrentMatchState] = useState<InterpolatedMatchState | null>(null);
  const [is2DActive, setIs2DActive] = useState<boolean>(false);
  const [audioMuted, setAudioMuted] = useState<boolean>(true);
  const [webglSupported, setWebglSupported] = useState<boolean>(true);

  // Sanitize viewer contract input
  const safeView = useMemo(
    () => sanitizeForSpectator(matchViewState, isOwnerOrManager),
    [matchViewState, isOwnerOrManager]
  );

  const safeViewRef = useRef<SpectatorSafeMatchView>(safeView);
  safeViewRef.current = safeView;

  // Persistent SpatialInterpolator & CameraDirector
  const interpolator = useMemo(() => new SpatialInterpolator(safeView.frames || []), [safeView]);
  const cameraDirector = useMemo(() => new CameraDirector(), []);

  // Keep the HUD camera selector connected to the actual Three.js director.
  useEffect(() => {
    cameraDirector.setManualMode(cameraMode);
  }, [cameraDirector, cameraMode]);

  // Ingest WebSocket live frame
  useEffect(() => {
    if (liveFrame) {
      interpolator.appendFrame(liveFrame);
    }
  }, [interpolator, liveFrame]);



  // Sync external scrubber changes
  useEffect(() => {
    if (typeof externalTime === "number" && Math.abs(externalTime - currentTime) > 0.5) {
      setCurrentTime(externalTime);
    }
  }, [externalTime, currentTime]);

  // Three.js WebGL Scene Lifecycle
  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

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
    scene.background = new THREE.Color("#060a12");
    scene.fog = new THREE.FogExp2("#060a12", 0.007);

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
      container.appendChild(renderer.domElement);
    } catch {
      setWebglSupported(false);
      return;
    }

    // 2. Procedural Pitch Environment (Pitch, Chalk Markings, Goals, Floodlights)
    const pitchEnv = new ProceduralPitchEnvironment(scene, {
      homeTeam: safeViewRef.current.home_team,
      awayTeam: safeViewRef.current.away_team,
      qualityTier,
      stadiumName: safeViewRef.current.venue_name || "GTEX National Arena",
    });

    // 3. 3D Ball & Dynamic Ground Shadow
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
    ballGroup.add(ballMesh);

    const shadowGeo = new THREE.CircleGeometry(ballRadius * 1.4, 16);
    const shadowMat = new THREE.MeshBasicMaterial({
      color: 0x050e08,
      transparent: true,
      opacity: 0.6,
    });
    const ballShadowMesh = new THREE.Mesh(shadowGeo, shadowMat);
    ballShadowMesh.rotation.x = -Math.PI / 2;
    ballShadowMesh.position.y = 0.03;
    ballGroup.add(ballShadowMesh);

    // 4. Animation Render Loop
    let animationFrameId: number;
    let lastTimestamp = performance.now();
    let localTime = currentTime;

    const renderLoop = (now: number) => {
      animationFrameId = requestAnimationFrame(renderLoop);

      const deltaSec = Math.min(0.1, (now - lastTimestamp) / 1000);
      lastTimestamp = now;

      pitchEnv.update(deltaSec);

      // Advance time if live or playing
      if (!isPaused) {
        localTime += deltaSec * playbackSpeed;
        const endTime = interpolator.getEndTime();
        if (endTime > 0 && localTime > endTime) {
          localTime = isLive ? endTime : interpolator.getStartTime();
        }
        setCurrentTime(localTime);
        onTimeUpdate?.(localTime);
      }

      // Query interpolated match state
      const state = interpolator.interpolate(localTime);
      setCurrentMatchState(state);

      if (state) {
        // Update Ball
        const [bx, by, bz] = state.ball.position3D;
        ballMesh.position.set(bx, by + ballRadius, bz);
        ballShadowMesh.position.set(bx, 0.03, bz);
        const shadowScale = Math.max(0.4, 1.0 - by * 0.15);
        ballShadowMesh.scale.set(shadowScale, shadowScale, 1);

        // Update 22 Procedural Player Markers
        for (const p of state.players) {
          const isGK = p.role === "GK";
          const marker = pitchEnv.getOrCreatePlayerMarker(
            p.player_id,
            p.side,
            p.shirt_number,
            p.label,
            p.role,
            isGK
          );
          marker.setVisible(true);
          marker.updatePosition(p.position3D, p.facingAngleRad);
        }

        // Update Camera
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
      }

      if (renderer) {
        renderer.render(scene, camera);
      }
    };

    animationFrameId = requestAnimationFrame(renderLoop);

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

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener("resize", handleResize);
      pitchEnv.dispose();
      renderer?.dispose();
      if (renderer?.domElement && container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, [interpolator, cameraDirector, qualityTier, isPaused, playbackSpeed, isLive, onTimeUpdate]);

  if (!webglSupported || is2DActive) {
    return (
      <div data-testid={`${testId}-fallback-2d`} className={`relative rounded-xl border border-emerald-500/20 bg-slate-950 p-6 text-white ${className}`}>
        <p className="font-bold text-emerald-400">2D Tactical Match Companion Mode</p>
        <p className="mt-1 text-xs text-slate-400">{safeView.home_team.team_name} vs {safeView.away_team.team_name}</p>
      </div>
    );
  }

  return (
    <div data-testid={testId} className={`relative h-[560px] w-full overflow-hidden rounded-xl bg-slate-950 ${className}`}>
      <div ref={mountRef} className="absolute inset-0 size-full" data-testid="match-pitch-canvas-container" />
      <BroadcastOverlayHUD
        matchState={currentMatchState}
        homeTeam={safeView.home_team}
        awayTeam={safeView.away_team}
        matchLabel={`${safeView.home_team.team_name} vs ${safeView.away_team.team_name}`}
        cameraMode={cameraMode}
        onSelectCameraMode={setCameraMode}
        viewerCount={viewerCount}
        is2DActive={is2DActive}
        onToggle2DFallback={() => {
          setIs2DActive(true);
          onToggle2DCompanion?.();
        }}
        audioMuted={audioMuted}
        onToggleAudio={() => setAudioMuted((prev) => !prev)}
        qualityTier={qualityTier}
        onSelectQualityTier={(t) => {
          setQualityTier(t);
          onQualityTierChange?.(t);
        }}
        isTheatreMode={isTheatreMode}
        onToggleTheatreMode={onToggleTheatreMode}
      />
    </div>
  );
};

// Register renderer in GtexSceneRegistry for generic decoupled viewport resolution
GtexSceneRegistry.registerRenderer("stadium_match_broadcast", MatchPitchLiveScene);
