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
  SpectatorSafeTeamView,
  sanitizeForSpectator,
} from "./spectatorContract";
import { DeviceQualityTier, QUALITY_PROFILES } from "../GtexSceneRegistry";
import { StadiumArenaEnvironment } from "./StadiumArenaEnvironment";

export interface MatchPitchLiveSceneProps {
  /** Authoritative raw or sanitized match view state */
  matchViewState: SpectatorSafeMatchView | Record<string, unknown>;
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
  /** Callback when time advances (for scrubbing sync) */
  onTimeUpdate?: (timeSeconds: number) => void;
  /** Fallback toggle callback when user selects 2D tactical view */
  onToggle2DCompanion?: () => void;
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
  qualityTier = "high",
  playbackTimeSeconds: externalTime,
  playbackSpeed = 1.0,
  isPaused = false,
  onTimeUpdate,
  onToggle2DCompanion,
  className = "",
  testId = "match-pitch-live-scene",
}) => {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const [webglSupported, setWebglSupported] = useState<boolean>(true);
  const [contextLost, setContextLost] = useState<boolean>(false);
  const [cameraMode, setCameraMode] = useState<ManualCameraMode>("director_auto");
  const [is2DActive, setIs2DActive] = useState<boolean>(false);
  const [audioMuted, setAudioMuted] = useState<boolean>(false);

  // Sanitize spectator-safe match view state
  const safeView: SpectatorSafeMatchView = useMemo(() => {
    return sanitizeForSpectator(matchViewState, isOwnerOrManager);
  }, [matchViewState, isOwnerOrManager]);

  // Spatial interpolator instance
  const interpolator = useMemo(() => {
    return new SpatialInterpolator(safeView.frames);
  }, [safeView.frames]);

  // Camera director instance
  const cameraDirector = useMemo(() => new CameraDirector(), []);

  // Internal playback time tracker
  const [currentTime, setCurrentTime] = useState<number>(() => {
    if (typeof externalTime === "number") return externalTime;
    return interpolator.getStartTime();
  });

  const [currentMatchState, setCurrentMatchState] = useState<InterpolatedMatchState | null>(null);

  // Sync external scrubber changes
  useEffect(() => {
    if (typeof externalTime === "number" && Math.abs(externalTime - currentTime) > 0.5) {
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
    const hemiLight = new THREE.HemisphereLight(0xa5c4d4, 0x144222, 0.65);
    scene.add(hemiLight);

    const keyLight = new THREE.DirectionalLight(0xffffff, 0.85);
    keyLight.position.set(20, 50, 40);
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

    const stadiumArena = new StadiumArenaEnvironment(scene, {
      homeTeam: safeView.home_team,
      awayTeam: safeView.away_team,
      qualityTier,
      stadiumName: safeView.venue_name || "GTEX National Arena",
    });

    // -------------------------------------------------------------------------
    // 4. Player Meshes (Pool of 22 Players)
    // -------------------------------------------------------------------------
    const playersGroup = new THREE.Group();
    scene.add(playersGroup);

    const playerMeshes = new Map<string, THREE.Group>();

    const getOrCreatePlayerMesh = (
      playerId: string,
      side: "home" | "away",
      shirtNum: number = 10,
      isGK: boolean = false
    ): THREE.Group => {
      if (playerMeshes.has(playerId)) {
        return playerMeshes.get(playerId)!;
      }

      const pGroup = new THREE.Group();

      // Team colors
      const primaryHex = side === "home" ? safeView.home_team.primary_color : safeView.away_team.primary_color;
      const gkHex = side === "home" ? safeView.home_team.goalkeeper_color : safeView.away_team.goalkeeper_color;
      const jerseyColor = new THREE.Color(isGK ? gkHex : primaryHex);
      const shortsColor = new THREE.Color(side === "home" ? safeView.home_team.secondary_color : safeView.away_team.secondary_color);

      // Torso / Jersey
      const torsoGeo = new THREE.CylinderGeometry(0.32, 0.28, 0.9, 12);
      const torsoMat = new THREE.MeshLambertMaterial({ color: jerseyColor });
      const torsoMesh = new THREE.Mesh(torsoGeo, torsoMat);
      torsoMesh.position.y = 1.05;
      torsoMesh.castShadow = true;
      pGroup.add(torsoMesh);

      // Head
      const headGeo = new THREE.SphereGeometry(0.2, 10, 10);
      const headMat = new THREE.MeshLambertMaterial({ color: 0xf5d0b5 });
      const headMesh = new THREE.Mesh(headGeo, headMat);
      headMesh.position.y = 1.65;
      pGroup.add(headMesh);

      // Shorts / Legs
      const shortsGeo = new THREE.CylinderGeometry(0.28, 0.26, 0.4, 10);
      const shortsMat = new THREE.MeshLambertMaterial({ color: shortsColor });
      const shortsMesh = new THREE.Mesh(shortsGeo, shortsMat);
      shortsMesh.position.y = 0.55;
      pGroup.add(shortsMesh);

      // Ground Marker Ring (subtle player shadow/ring)
      const ringGeo = new THREE.RingGeometry(0.35, 0.42, 16);
      const ringMat = new THREE.MeshBasicMaterial({
        color: jerseyColor,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.6,
      });
      const ringMesh = new THREE.Mesh(ringGeo, ringMat);
      ringMesh.rotation.x = -Math.PI / 2;
      ringMesh.position.y = 0.03;
      pGroup.add(ringMesh);

      playersGroup.add(pGroup);
      playerMeshes.set(playerId, pGroup);
      return pGroup;
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
    // 6. Animation / Render Loop
    // -------------------------------------------------------------------------
    let animationFrameId: number;
    let lastTimestamp = performance.now();
    let localTime = currentTime;

    const renderLoop = (now: number) => {
      animationFrameId = requestAnimationFrame(renderLoop);

      const deltaSec = Math.min(0.1, (now - lastTimestamp) / 1000);
      lastTimestamp = now;

      // Update stadium dynamics (scrolling LED ad boards, flag flutter)
      stadiumArena.update(deltaSec);

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

      // Query interpolated match state at localTime
      const state = interpolator.interpolate(localTime);
      setCurrentMatchState(state);

      if (state) {
        // Update Ball
        const [bx, by, bz] = state.ball.position3D;
        ballMesh.position.set(bx, by + ballRadius, bz);

        // Update ball drop shadow
        ballShadowMesh.position.set(bx, 0.03, bz);
        const shadowScale = Math.max(0.4, 1.0 - by * 0.15);
        ballShadowMesh.scale.set(shadowScale, shadowScale, 1);
        (ballShadowMesh.material as THREE.MeshBasicMaterial).opacity = Math.max(
          0.1,
          0.6 - by * 0.1
        );

        // Update Players
        const activeIds = new Set<string>();
        for (const p of state.players) {
          activeIds.add(p.player_id);
          const isGK = p.role === "GK";
          const pMesh = getOrCreatePlayerMesh(p.player_id, p.side, p.shirt_number, isGK);

          pMesh.visible = true;
          pMesh.position.set(p.position3D[0], 0, p.position3D[2]);
          pMesh.rotation.y = p.facingAngleRad;
        }

        // Hide inactive/substituted player meshes
        playerMeshes.forEach((mesh, id) => {
          if (!activeIds.has(id)) {
            mesh.visible = false;
          }
        });

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

    // Resize observer
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

    // Cleanup on unmount
    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener("resize", handleResize);
      canvasElement.removeEventListener("webglcontextlost", handleContextLost);
      canvasElement.removeEventListener("webglcontextrestored", handleContextRestored);

      // Dispose Three.js objects
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
  }, [safeView, qualityTier, interpolator, cameraDirector, isLive, playbackSpeed, isPaused]);

  // Handle 2D companion mode toggle
  const handleToggle2D = useCallback(() => {
    setIs2DActive((prev) => !prev);
    onToggle2DCompanion?.();
  }, [onToggle2DCompanion]);

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
        />
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Primary 3D WebGL Broadcast Canvas
  // ---------------------------------------------------------------------------
  return (
    <div
      data-testid={testId}
      className={`relative h-[560px] w-full overflow-hidden rounded-xl border border-white/10 bg-slate-950 shadow-2xl ${className}`}
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
      />
    </div>
  );
};
