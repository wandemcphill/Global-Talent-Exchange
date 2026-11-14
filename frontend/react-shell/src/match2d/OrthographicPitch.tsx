import React, { memo, useEffect, useRef, useState } from "react";
import * as THREE from "three";

import * as matchRenderer from "./createMatchRenderer";
import {
  animationFor,
  deriveDirectorShot,
  effectFor,
  isWoodworkPosition,
  passArcColor,
  playerIdentityKey,
  predictPassReceiver,
  progressivePassMeters,
  resolveBallPresentation,
  sceneObjectCount,
  type FeedPresentationStatus,
  type PitchBall,
  type PitchFrame,
  type PitchPlayer,
  type PitchShotMarker,
  type PitchSide,
} from "./matchStateAdapter";
import {
  ATLAS_COLUMNS,
  ATLAS_ROWS,
  CELL,
  PlayerMotionTracker,
  buildAtlasPixels,
  buildDigitPixels,
  cellUv,
  getCachedBallBitmap,
  getCachedPitchBitmap,
  getCachedRingBitmap,
  paintRig,
  rasterBall,
  rasterPitch,
  rasterRing,
  sampleTrajectory,
  type RigAction,
} from "./playerRig";

export type PitchCameraMode = "2d" | "2.5d" | "zoom";

export type SampledPitchFrame = {
  players: PitchPlayer[];
  ball: PitchBall | null;
  ballTrajectory?: PitchBall[] | null;
  trajectoryAlpha?: number;
  eventType?: string | null;
  phase?: string | null;
  stage?: string | null;
  cameraPreset?: string | null;
  possessionSide?: PitchSide | null;
  dangerZone?: string | null;
  primaryPlayerId?: string | null;
  secondaryPlayerId?: string | null;
  homeAttacksRight?: boolean;
  clockMinute?: number | null;
  homeScore?: number | null;
  awayScore?: number | null;
  eventBanner?: string | null;
};

export type OrthographicPitchProps = {
  players: PitchPlayer[];
  ball: PitchBall | null;
  ballTrajectory?: PitchBall[] | null;
  trajectoryAlpha?: number;
  eventType?: string | null;
  phase?: string | null;
  stage?: string | null;
  cameraPreset?: string | null;
  possessionSide?: PitchSide | null;
  dangerZone?: string | null;
  primaryPlayerId?: string | null;
  secondaryPlayerId?: string | null;
  homeAttacksRight?: boolean;
  homeColor?: string;
  awayColor?: string;
  goalkeeperHome?: string;
  goalkeeperAway?: string;
  selectedKey?: string | null;
  onSelect?: (key: string) => void;
  unavailable?: boolean;
  demo?: boolean;
  cameraMode?: PitchCameraMode;
  onCameraModeChange?: (mode: PitchCameraMode) => void;
  showVoronoi?: boolean;
  showHeatmap?: boolean;
  showTactics?: boolean;
  showPassingLanes?: boolean;
  showShotMap?: boolean;
  shotMarkers?: PitchShotMarker[];
  /** Optional match clock + score so the broadcast director can stage injury-time framing. */
  clockMinute?: number | null;
  homeScore?: number | null;
  awayScore?: number | null;
  feedStatus?: FeedPresentationStatus;
  feedFreshness?: FeedPresentationStatus;
  feedAgeSeconds?: number | null;
  sampleFrame?: ((nowMs: number) => SampledPitchFrame | null) | null;
};

export const PITCH_W = 105;
export const PITCH_H = 68;
const POOL_SIZE = 26;
const PITCH_TEX_W = 1024;
const PITCH_TEX_H = 640;
const OVERLAY_W = 768;
const OVERLAY_H = 480;
const GRID_W = 64;
const GRID_H = 40;

const VERTEX = `
  precision highp float;
  uniform vec2 uOffset;
  uniform vec2 uRepeat;
  varying vec2 vUv;
  void main() {
    vUv = uOffset + uv * uRepeat;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const FRAGMENT = `
  precision highp float;
  uniform sampler2D uBody;
  uniform sampler2D uKit;
  uniform sampler2D uDigits;
  uniform vec3 uKitColor;
  uniform vec2 uOffset;
  uniform vec2 uRepeat;
  uniform float uShirt;
  varying vec2 vUv;
  void main() {
    vec4 body = texture2D(uBody, vUv);
    vec4 kit = texture2D(uKit, vUv);
    vec3 shadedKit = uKitColor * kit.rgb;
    vec3 color = mix(body.rgb, shadedKit, kit.a);
    float alpha = max(body.a, kit.a);
    vec2 localUv = (vUv - uOffset) / uRepeat;
    float digitAlpha = 0.0;
    float digitShadow = 0.0;
    if (localUv.y > 0.41 && localUv.y < 0.63 && localUv.x > 0.35 && localUv.x < 0.65) {
      float span = uShirt >= 10.0 ? 0.12 : 0.16;
      float ones = mod(floor(uShirt + 0.5), 10.0);
      float tens = floor(uShirt / 10.0);
      float which = ones;
      float start = 0.5 - span * 0.5;
      if (uShirt >= 10.0) {
        which = localUv.x < 0.5 ? tens : ones;
        start = localUv.x < 0.5 ? 0.5 - span : 0.5;
      }
      float gx = clamp((localUv.x - start) / span, 0.0, 0.999);
      float gy = clamp((0.62 - localUv.y) / 0.2, 0.0, 0.999);
      digitAlpha = texture2D(uDigits, vec2((which + gx) / 10.0, 1.0 - gy)).a;
      float sx = clamp((localUv.x - 0.012 - start) / span, 0.0, 0.999);
      float sy = clamp((0.62 - (localUv.y - 0.012)) / 0.2, 0.0, 0.999);
      digitShadow = texture2D(uDigits, vec2((which + sx) / 10.0, 1.0 - sy)).a * (1.0 - digitAlpha);
    }
    color = mix(color, vec3(0.05, 0.08, 0.12), digitShadow * 0.75);
    color = mix(color, vec3(0.98, 0.99, 1.0), digitAlpha);
    float visible = max(alpha, max(digitAlpha, digitShadow * 0.6));
    if (visible < 0.05) discard;
    gl_FragColor = vec4(color, visible);
  }
`;

export const lastRenderProfile = {
  calls: 0,
  sampledFrames: 0,
  fps: 0,
  frameMs: 0,
  objectCount: 0,
  activePlayerSprites: 0,
  rendererMode: "webgl" as "webgl" | "canvas-fallback" | "unmounted",
  contextRecoveryEvents: 0,
  contextLostCount: 0,
  contextRestoredCount: 0,
  activeRenderers: 0,
  feedFreshness: "LIVE" as FeedPresentationStatus,
  logged: false,
};

export function clampCameraPan(
  panX: number,
  panY: number,
  zoom: number,
): { panX: number; panY: number; zoom: number } {
  const safeZoom = Math.min(2.6, Math.max(0.8, Number.isFinite(zoom) ? zoom : 1));
  const maxPanX = Math.max(6, (PITCH_W * (1 - 1 / Math.max(1, safeZoom))) / 2 + 8);
  const maxPanY = Math.max(4, (PITCH_H * (1 - 1 / Math.max(1, safeZoom))) / 2 + 6);
  return {
    zoom: safeZoom,
    panX: Math.min(maxPanX, Math.max(-maxPanX, Number.isFinite(panX) ? panX : 0)),
    panY: Math.min(maxPanY, Math.max(-maxPanY, Number.isFinite(panY) ? panY : 0)),
  };
}

/**
 * Converts a client pointer position to normalized pitch coordinates `[0, 1] x [0, 1]`
 * and world space `[-PITCH_W/2..PITCH_W/2, -PITCH_H/2..PITCH_H/2]` using the inverse
 * orthographic camera transformation (accounting for both camera zoom and pan).
 */
export function screenToPitchPoint(
  clientX: number,
  clientY: number,
  rect: { left: number; top: number; width: number; height: number },
  camera: { zoom: number; panX: number; panY: number },
): { x: number; y: number; worldX: number; worldY: number } {
  const width = Math.max(1, rect.width);
  const height = Math.max(1, rect.height);
  const zoom = Math.max(0.1, Number.isFinite(camera.zoom) ? camera.zoom : 1);
  const panX = Number.isFinite(camera.panX) ? camera.panX : 0;
  const panY = Number.isFinite(camera.panY) ? camera.panY : 0;

  const screenNormX = (clientX - rect.left) / width;
  const screenNormY = (clientY - rect.top) / height;
  const ndcX = screenNormX * 2 - 1;
  const ndcY = 1 - screenNormY * 2;

  const worldX = panX + ndcX * (PITCH_W / (2 * zoom));
  const worldY = panY + ndcY * (PITCH_H / (2 * zoom));

  const x = worldX / PITCH_W + 0.5;
  const y = 0.5 - worldY / PITCH_H;

  return { x, y, worldX, worldY };
}

/**
 * Selects the closest player within the hit radius at the inverse-transformed pitch coordinate.
 */
export function pickPlayerAtPoint(
  players: ReadonlyArray<PitchPlayer>,
  pitchPoint: { x: number; y: number },
  zoom = 1,
): PitchPlayer | null {
  if (!Array.isArray(players) || players.length === 0) return null;
  const effectiveZoom = Math.max(0.8, Math.min(2.6, zoom || 1));
  // Hit radius in normalized pitch space scales gently so zoomed-in sprites remain crisp and non-overlapping
  const maxRadius = Math.max(0.022, Math.min(0.045, 0.038 / Math.sqrt(effectiveZoom)));
  let bestPlayer: PitchPlayer | null = null;
  let bestDistance = maxRadius;

  for (const player of players) {
    const distance = Math.hypot(player.x - pitchPoint.x, player.y - pitchPoint.y);
    if (distance <= bestDistance) {
      bestDistance = distance;
      bestPlayer = player;
    }
  }
  return bestPlayer;
}

function dataTexture(data: Uint8Array, width: number, height: number) {
  const texture = new THREE.DataTexture(data, width, height, THREE.RGBAFormat);
  texture.flipY = true;
  texture.needsUpdate = true;
  texture.magFilter = THREE.LinearFilter;
  texture.minFilter = THREE.LinearFilter;
  texture.generateMipmaps = false;
  return texture;
}

function hexToRgbaString(hex: string, alpha: number): string {
  const cleaned = String(hex || "#00e87a").replace("#", "");
  const full =
    cleaned.length === 3
      ? cleaned
          .split("")
          .map((c) => c + c)
          .join("")
      : cleaned.padEnd(6, "0");
  const r = parseInt(full.slice(0, 2), 16) || 0;
  const g = parseInt(full.slice(2, 4), 16) || 0;
  const b = parseInt(full.slice(4, 6), 16) || 0;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function pointToSegmentDistance(
  px: number,
  py: number,
  x0: number,
  y0: number,
  x1: number,
  y1: number,
): number {
  const dx = x1 - x0;
  const dy = y1 - y0;
  const lenSq = dx * dx + dy * dy;
  if (lenSq <= 1e-6) return Math.hypot(px - x0, py - y0);
  const t = Math.max(0, Math.min(1, ((px - x0) * dx + (py - y0) * dy) / lenSq));
  return Math.hypot(px - (x0 + t * dx), py - (y0 + t * dy));
}

function safeFillText(ctx: CanvasRenderingContext2D, text: string, x: number, y: number) {
  if (typeof ctx.fillText === "function") ctx.fillText(text, x, y);
}

function strokePolyCircle(
  ctx: CanvasRenderingContext2D,
  cx: number,
  cy: number,
  rx: number,
  ry: number,
  segments = 24,
) {
  ctx.beginPath();
  for (let i = 0; i <= segments; i += 1) {
    const theta = (i / segments) * Math.PI * 2;
    const x = cx + Math.cos(theta) * rx;
    const y = cy + Math.sin(theta) * ry;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.closePath();
  ctx.stroke();
}

function fillPolyCircle(
  ctx: CanvasRenderingContext2D,
  cx: number,
  cy: number,
  rx: number,
  ry: number,
  segments = 24,
) {
  ctx.beginPath();
  for (let i = 0; i <= segments; i += 1) {
    const theta = (i / segments) * Math.PI * 2;
    const x = cx + Math.cos(theta) * rx;
    const y = cy + Math.sin(theta) * ry;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.closePath();
  ctx.fill();
}

function drawRoundedBannerBox(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  fill: string,
  stroke: string,
) {
  ctx.fillStyle = fill;
  ctx.fillRect(x, y, w, h);
  ctx.strokeStyle = stroke;
  ctx.lineWidth = 1.2;
  ctx.strokeRect(x, y, w, h);
}

function OrthographicPitchComponent({
  players,
  ball,
  ballTrajectory = null,
  trajectoryAlpha = 1,
  eventType,
  phase = null,
  stage = null,
  cameraPreset = null,
  possessionSide = null,
  dangerZone = null,
  primaryPlayerId = null,
  secondaryPlayerId = null,
  homeAttacksRight = true,
  homeColor = "#00e87a",
  awayColor = "#ffb800",
  goalkeeperHome = "#f8fafc",
  goalkeeperAway = "#111827",
  selectedKey,
  onSelect,
  unavailable = false,
  demo = false,
  cameraMode = "2d",
  onCameraModeChange,
  showVoronoi = false,
  showHeatmap = false,
  showTactics = false,
  showPassingLanes = false,
  showShotMap = false,
  shotMarkers = [],
  clockMinute = null,
  homeScore = null,
  awayScore = null,
  feedStatus = "LIVE",
  feedFreshness,
  feedAgeSeconds = null,
  sampleFrame = null,
}: OrthographicPitchProps) {
  const effectiveFeedStatus = feedFreshness || feedStatus;
  const hostRef = useRef<HTMLDivElement | null>(null);
  const propsRef = useRef({
    players,
    ball,
    ballTrajectory,
    trajectoryAlpha,
    eventType,
    phase,
    stage,
    cameraPreset,
    possessionSide,
    dangerZone,
    primaryPlayerId,
    secondaryPlayerId,
    homeAttacksRight,
    homeColor,
    awayColor,
    goalkeeperHome,
    goalkeeperAway,
    selectedKey,
    cameraMode,
    showVoronoi,
    showHeatmap,
    showTactics,
    showPassingLanes,
    showShotMap,
    shotMarkers,
    clockMinute,
    homeScore,
    awayScore,
    feedStatus: effectiveFeedStatus,
    sampleFrame,
  });
  const cameraRef = useRef({ zoom: 1, panX: 0, panY: 0, follow: false, manualOverrideUntilMs: 0 });
  const [follow, setFollow] = useState(false);
  const [zoomLevel, setZoomLevel] = useState(1);

  propsRef.current = {
    players,
    ball,
    ballTrajectory,
    trajectoryAlpha,
    eventType,
    phase,
    stage,
    cameraPreset,
    possessionSide,
    dangerZone,
    primaryPlayerId,
    secondaryPlayerId,
    homeAttacksRight,
    homeColor,
    awayColor,
    goalkeeperHome,
    goalkeeperAway,
    selectedKey,
    cameraMode,
    showVoronoi,
    showHeatmap,
    showTactics,
    showPassingLanes,
    showShotMap,
    shotMarkers,
    clockMinute,
    homeScore,
    awayScore,
    feedStatus: effectiveFeedStatus,
    sampleFrame,
  };
  cameraRef.current.follow = follow;

  // Apply cameraMode preset changes cleanly while allowing manual zoom/pan adjustments
  useEffect(() => {
    if (cameraMode === "2d") {
      cameraRef.current = { zoom: 1, panX: 0, panY: 0, follow: cameraRef.current.follow, manualOverrideUntilMs: 0 };
      setZoomLevel(1);
    } else if (cameraMode === "2.5d") {
      cameraRef.current = {
        zoom: 1.14,
        panX: cameraRef.current.panX * 0.5,
        panY: -2.0,
        follow: cameraRef.current.follow,
        manualOverrideUntilMs: 0,
      };
      setZoomLevel(1.14);
    } else if (cameraMode === "zoom") {
      cameraRef.current = {
        zoom: 1.44,
        panX: cameraRef.current.panX,
        panY: cameraRef.current.panY,
        follow: true,
        manualOverrideUntilMs: 0,
      };
      setZoomLevel(1.44);
    }
  }, [cameraMode]);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return undefined;
    let renderer: THREE.WebGLRenderer | null = null;
    let fallback: CanvasRenderingContext2D | null = null;
    let fallbackCanvas: HTMLCanvasElement | null = null;
    let stopped = false;
    let contextLost = false;
    let frameId = 0;
    let fpsFrames = 0;
    let fpsStarted = performance.now();

    lastRenderProfile.activeRenderers += 1;
    lastRenderProfile.feedFreshness = propsRef.current.feedStatus;

    const scene = new THREE.Scene();
    const camera = new THREE.OrthographicCamera(-PITCH_W / 2, PITCH_W / 2, PITCH_H / 2, -PITCH_H / 2, 0.1, 50);
    camera.position.set(0, 0, 10);

    const pitchPixels = rasterPitch(PITCH_TEX_W, PITCH_TEX_H);
    const pitchTexture = dataTexture(pitchPixels, PITCH_TEX_W, PITCH_TEX_H);
    const pitchGeometry = new THREE.PlaneGeometry(PITCH_W, PITCH_H);
    const pitchMaterial = new THREE.MeshBasicMaterial({ map: pitchTexture, side: THREE.DoubleSide });
    const pitch = new THREE.Mesh(pitchGeometry, pitchMaterial);
    scene.add(pitch);

    // Dynamic tactical, trajectory & broadcast callout overlay layer
    const overlayCanvas = document.createElement("canvas");
    overlayCanvas.width = OVERLAY_W;
    overlayCanvas.height = OVERLAY_H;
    let overlayCtx: CanvasRenderingContext2D | null = null;
    let overlayCtxAttempted = false;
    const getOverlayCtx = (): CanvasRenderingContext2D | null => {
      if (overlayCtxAttempted) return overlayCtx;
      overlayCtxAttempted = true;
      try {
        overlayCtx = overlayCanvas.getContext("2d");
      } catch {
        overlayCtx = null;
      }
      return overlayCtx;
    };
    const overlayTexture = new THREE.CanvasTexture(overlayCanvas);
    overlayTexture.minFilter = THREE.LinearFilter;
    overlayTexture.magFilter = THREE.LinearFilter;
    overlayTexture.generateMipmaps = false;
    const overlayGeometry = new THREE.PlaneGeometry(PITCH_W, PITCH_H);
    const overlayMaterial = new THREE.MeshBasicMaterial({
      map: overlayTexture,
      transparent: true,
      depthWrite: false,
      side: THREE.DoubleSide,
    });
    const overlayMesh = new THREE.Mesh(overlayGeometry, overlayMaterial);
    overlayMesh.position.set(0, 0, 0.28);
    overlayMesh.visible = false;
    scene.add(overlayMesh);

    const atlas = buildAtlasPixels();
    const bodyTexture = dataTexture(atlas.body, atlas.width, atlas.height);
    const kitTexture = dataTexture(atlas.kit, atlas.width, atlas.height);
    const digits = buildDigitPixels();
    const digitTexture = dataTexture(digits.data, digits.width, digits.height);
    digitTexture.magFilter = THREE.NearestFilter;
    digitTexture.minFilter = THREE.NearestFilter;

    // Ground shadow mesh for aerial balls (separates from ballMesh when heightMeters > 0.1)
    const ballShadowGeometry = new THREE.PlaneGeometry(1.75, 0.85);
    const ballShadowMaterial = new THREE.MeshBasicMaterial({
      color: 0x030712,
      transparent: true,
      opacity: 0.42,
      depthWrite: false,
      side: THREE.DoubleSide,
    });
    const ballShadowMesh = new THREE.Mesh(ballShadowGeometry, ballShadowMaterial);
    ballShadowMesh.visible = false;
    scene.add(ballShadowMesh);

    const ballTexture = dataTexture(rasterBall(), 48, 48);
    const ballGeometry = new THREE.PlaneGeometry(2.45, 2.45);
    const ballMaterial = new THREE.MeshBasicMaterial({
      map: ballTexture,
      transparent: true,
      depthWrite: false,
      side: THREE.DoubleSide,
    });
    const ballMesh = new THREE.Mesh(ballGeometry, ballMaterial);
    scene.add(ballMesh);

    const ringTexture = dataTexture(rasterRing(), 64, 64);
    const ringGeometry = new THREE.PlaneGeometry(3.5, 3.5);
    const ringMaterial = new THREE.MeshBasicMaterial({
      map: ringTexture,
      transparent: true,
      depthWrite: false,
      side: THREE.DoubleSide,
    });
    const ring = new THREE.Mesh(ringGeometry, ringMaterial);
    ring.visible = false;
    scene.add(ring);

    const carrierRingGeometry = new THREE.PlaneGeometry(3.0, 3.0);
    const carrierRingMaterial = new THREE.MeshBasicMaterial({
      map: ringTexture,
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.78,
      depthWrite: false,
      side: THREE.DoubleSide,
    });
    const carrierRing = new THREE.Mesh(carrierRingGeometry, carrierRingMaterial);
    carrierRing.visible = false;
    scene.add(carrierRing);

    const effectGeometry = new THREE.PlaneGeometry(1, 0.28);
    const effectMaterial = new THREE.MeshBasicMaterial({
      color: 0xffffff,
      transparent: true,
      opacity: 0.9,
      depthWrite: false,
      side: THREE.DoubleSide,
    });
    const effect = new THREE.Mesh(effectGeometry, effectMaterial);
    effect.visible = false;
    scene.add(effect);

    const cueGeometry = new THREE.PlaneGeometry(2.2, 2.2);
    const cueMaterial = new THREE.MeshBasicMaterial({
      color: 0xffffff,
      transparent: true,
      opacity: 0.55,
      depthWrite: false,
      side: THREE.DoubleSide,
    });
    const cueMesh = new THREE.Mesh(cueGeometry, cueMaterial);
    cueMesh.visible = false;
    scene.add(cueMesh);

    const pool: THREE.Mesh[] = [];
    const assigned = new Map<string, THREE.Mesh>();
    const free: THREE.Mesh[] = [];
    const sharedGeometry = new THREE.PlaneGeometry(4.85, 4.85);
    for (let index = 0; index < POOL_SIZE; index += 1) {
      const material = new THREE.ShaderMaterial({
        transparent: true,
        depthWrite: false,
        side: THREE.DoubleSide,
        uniforms: {
          uBody: { value: bodyTexture },
          uKit: { value: kitTexture },
          uDigits: { value: digitTexture },
          uKitColor: { value: new THREE.Color("#ffffff") },
          uOffset: { value: new THREE.Vector2() },
          uRepeat: { value: new THREE.Vector2(1 / ATLAS_COLUMNS, 1 / ATLAS_ROWS) },
          uShirt: { value: 0 },
        },
        vertexShader: VERTEX,
        fragmentShader: FRAGMENT,
      });
      const mesh = new THREE.Mesh(sharedGeometry, material);
      mesh.visible = false;
      scene.add(mesh);
      pool.push(mesh);
      free.push(mesh);
    }

    const motionTracker = new PlayerMotionTracker();
    const seenKeys = new Set<string>();
    const heatmapBins = new Float32Array(GRID_W * GRID_H);
    let heatmapSeeded = false;
    let lastOverlayPaintMs = -1000;
    let lastOverlaySignature = "";
    let previousBall: { x: number; y: number } | null = null;
    // Ball spin / bounce state
    let ballSpinAngle = 0;
    let ballBounceScale = 1;
    let lastBallHeightMeters = 0;
    // Broadcast director state — tracks how long the current event has been on screen
    let directorEventKey = "";
    let directorEventStartMs = 0;
    // Progressive-pass ring: shown on the receiver briefly after a completed pass
    let pendingPass: { from: { x: number; y: number }; side: PitchSide; receiverKey: string | null } | null = null;
    let passGainRing: { key: string; meters: number; startedMs: number } | null = null;

    const resize = () => {
      const width = Math.max(host.clientWidth, 320);
      const height = Math.max(Math.round(width * 0.62), 200);
      if (renderer && !contextLost) {
        renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
        renderer.setSize(width, height, false);
      }
      if (fallbackCanvas) {
        fallbackCanvas.width = width;
        fallbackCanvas.height = height;
      }
    };

    const ensureFallback = () => {
      if (renderer?.domElement && renderer.domElement.parentNode === host) {
        renderer.domElement.remove();
      }
      if (!fallbackCanvas) {
        fallbackCanvas = document.createElement("canvas");
        fallbackCanvas.setAttribute("data-testid", "pitch-canvas-fallback");
        fallbackCanvas.style.width = "100%";
        fallbackCanvas.style.height = "100%";
        fallbackCanvas.style.display = "block";
        fallbackCanvas.style.touchAction = "none";
        try {
          fallback = fallbackCanvas.getContext("2d");
        } catch {
          fallback = null;
        }
        host.appendChild(fallbackCanvas);
      } else if (fallbackCanvas.parentNode !== host) {
        fallbackCanvas.style.display = "block";
        host.appendChild(fallbackCanvas);
      }
      lastRenderProfile.rendererMode = "canvas-fallback";
      resize();
    };

    const hideFallback = () => {
      if (fallbackCanvas) {
        fallbackCanvas.remove();
        fallbackCanvas = null;
        fallback = null;
      }
      if (renderer?.domElement) {
        renderer.domElement.style.display = "block";
        if (renderer.domElement.parentNode !== host) {
          host.appendChild(renderer.domElement);
        }
      }
      lastRenderProfile.rendererMode = "webgl";
    };

    const onContextLost = (event: Event) => {
      event.preventDefault();
      contextLost = true;
      lastRenderProfile.contextLostCount += 1;
      lastRenderProfile.contextRecoveryEvents += 1;
      ensureFallback();
    };

    const onContextRestored = () => {
      contextLost = false;
      lastRenderProfile.contextRestoredCount += 1;
      lastRenderProfile.contextRecoveryEvents += 1;
      pitchTexture.needsUpdate = true;
      bodyTexture.needsUpdate = true;
      kitTexture.needsUpdate = true;
      digitTexture.needsUpdate = true;
      ballTexture.needsUpdate = true;
      ringTexture.needsUpdate = true;
      overlayTexture.needsUpdate = true;
      pitchMaterial.needsUpdate = true;
      ballMaterial.needsUpdate = true;
      ballShadowMaterial.needsUpdate = true;
      ringMaterial.needsUpdate = true;
      carrierRingMaterial.needsUpdate = true;
      overlayMaterial.needsUpdate = true;
      pool.forEach((mesh) => {
        (mesh.material as THREE.ShaderMaterial).needsUpdate = true;
      });
      hideFallback();
      resize();
    };

    try {
      renderer = matchRenderer.createMatchRenderer();
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      renderer.domElement.setAttribute("data-testid", "pitch-webgl-canvas");
      renderer.domElement.style.width = "100%";
      renderer.domElement.style.height = "100%";
      renderer.domElement.style.display = "block";
      renderer.domElement.style.touchAction = "none";
      host.appendChild(renderer.domElement);
      renderer.domElement.addEventListener("webglcontextlost", onContextLost);
      renderer.domElement.addEventListener("webglcontextrestored", onContextRestored);
      lastRenderProfile.rendererMode = "webgl";
    } catch {
      renderer = null;
      ensureFallback();
    }

    resize();
    const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(resize);
    observer?.observe(host);

    const toWorld = (x: number, y: number) => ({
      x: (x - 0.5) * PITCH_W,
      y: (0.5 - y) * PITCH_H,
    });

    const acquire = (compositeKey: string) => {
      let mesh = assigned.get(compositeKey);
      if (mesh) return mesh;
      mesh = free.pop();
      if (!mesh) return null;
      mesh.visible = true;
      assigned.set(compositeKey, mesh);
      return mesh;
    };

    const paint = () => {
      if (stopped) return;
      frameId = window.requestAnimationFrame(paint);
      const frameStart = performance.now();
      const view = cameraRef.current;
      const current = propsRef.current;

      // Sample continuous 60fps interpolated frame if provided by Pitch2DView
      const liveSampled = current.sampleFrame ? current.sampleFrame(frameStart) : null;
      const activePlayers = liveSampled && liveSampled.players.length > 0 ? liveSampled.players : current.players;
      const activeBall = liveSampled ? liveSampled.ball : current.ball;
      const activeTrajectory = liveSampled
        ? liveSampled.ballTrajectory ?? current.ballTrajectory
        : current.ballTrajectory;
      const activeAlpha = liveSampled?.trajectoryAlpha ?? current.trajectoryAlpha;
      const activeEvent = liveSampled?.eventType ?? current.eventType;
      const activePhase = liveSampled?.phase ?? current.phase;
      const activeStage = liveSampled?.stage ?? current.stage;
      const activeCameraPreset = liveSampled?.cameraPreset ?? current.cameraPreset;
      const activePossessionSide = liveSampled?.possessionSide ?? current.possessionSide;
      const activeDangerZone = liveSampled?.dangerZone ?? current.dangerZone;
      const activePrimaryId = liveSampled?.primaryPlayerId ?? current.primaryPlayerId;
      const activeSecondaryId = liveSampled?.secondaryPlayerId ?? current.secondaryPlayerId;
      const activeHomeAttacksRight = liveSampled?.homeAttacksRight ?? current.homeAttacksRight ?? true;

      // Accumulate real player coordinates into the spatial heatmap grid (with initial formation seed)
      if (activePlayers.length > 0) {
        if (!heatmapSeeded) {
          heatmapSeeded = true;
          for (const p of activePlayers) {
            const gx = Math.min(GRID_W - 1, Math.max(0, Math.floor(p.x * GRID_W)));
            const gy = Math.min(GRID_H - 1, Math.max(0, Math.floor(p.y * GRID_H)));
            for (let dy = -1; dy <= 1; dy += 1) {
              for (let dx = -1; dx <= 1; dx += 1) {
                const nx = Math.min(GRID_W - 1, Math.max(0, gx + dx));
                const ny = Math.min(GRID_H - 1, Math.max(0, gy + dy));
                const weight = dx === 0 && dy === 0 ? 1.8 : 0.75;
                heatmapBins[ny * GRID_W + nx] = Math.min(12, heatmapBins[ny * GRID_W + nx] + weight);
              }
            }
          }
        }
        for (let i = 0; i < GRID_W * GRID_H; i += 1) {
          heatmapBins[i] *= 0.996;
        }
        for (const p of activePlayers) {
          const gx = Math.min(GRID_W - 1, Math.max(0, Math.floor(p.x * GRID_W)));
          const gy = Math.min(GRID_H - 1, Math.max(0, Math.floor(p.y * GRID_H)));
          heatmapBins[gy * GRID_W + gx] = Math.min(12, heatmapBins[gy * GRID_W + gx] + 0.18);
        }
      }

      const trajectoryBallPoint =
        activeTrajectory && activeTrajectory.length > 0
          ? sampleTrajectory(activeTrajectory, activeAlpha)
          : activeBall;

      const syntheticFrame: PitchFrame = {
        timeSeconds: 0,
        players: activePlayers,
        ball: activeBall
          ? {
              ...activeBall,
              height: (trajectoryBallPoint as any)?.height ?? activeBall.height,
            }
          : (trajectoryBallPoint as PitchBall | null),
        ballTrajectory: activeTrajectory,
        eventType: activeEvent,
        phase: activePhase,
        stage: activeStage,
        cameraPreset: activeCameraPreset,
        possessionSide: activePossessionSide,
        dangerZone: activeDangerZone,
        primaryPlayerId: activePrimaryId,
        secondaryPlayerId: activeSecondaryId,
        homeAttacksRight: activeHomeAttacksRight,
      };
      const resolvedBall = resolveBallPresentation(syntheticFrame, activeAlpha, trajectoryBallPoint);
      const ballPoint = resolvedBall ? { x: resolvedBall.x, y: resolvedBall.y } : trajectoryBallPoint;

      // Broadcast director camera tracking & event-aware framing (respecting manual pan/zoom gestures)
      const isManualActive = frameStart < view.manualOverrideUntilMs;
      const directorKey = `${activeEvent || ""}:${activePrimaryId || ""}`;
      if (directorKey !== directorEventKey) {
        directorEventKey = directorKey;
        directorEventStartMs = frameStart;
      }
      const directorScorer = activePrimaryId
        ? activePlayers.find((p) => p.playerId === activePrimaryId) || null
        : null;
      const homeSc = current.homeScore ?? null;
      const awaySc = current.awayScore ?? null;
      const director = deriveDirectorShot({
        eventType: activeEvent,
        phase: activePhase,
        timeSeconds: (liveSampled as any)?.timeSeconds ?? null,
        minute: current.clockMinute ?? null,
        eventAgeMs: frameStart - directorEventStartMs,
        ball: ballPoint,
        scorer: directorScorer,
        leadingSide:
          homeSc !== null && awaySc !== null && homeSc !== awaySc ? (homeSc > awaySc ? "home" : "away") : null,
        homeAttacksRight: activeHomeAttacksRight,
      });
      const directorActive = director.kind !== "none" && current.cameraMode !== "2d" && !isManualActive;
      if ((view.follow || current.cameraMode === "zoom" || current.cameraMode === "2.5d") && ballPoint) {
        const focusPoint = directorActive && director.focus ? director.focus : ballPoint;
        const focus = toWorld(focusPoint.x, focusPoint.y);
        const eventStr = String(activeEvent || "").toLowerCase();
        const presetStr = String(activeCameraPreset || "").toLowerCase();
        const isBoxMoment =
          eventStr === "goal" ||
          eventStr === "shot" ||
          eventStr === "save" ||
          eventStr === "penalty" ||
          presetStr === "box_zoom" ||
          presetStr === "goal_celebration" ||
          activeDangerZone === "box";

        if (!isManualActive) {
          const baseZoom =
            current.cameraMode === "zoom"
              ? isBoxMoment
                ? 1.54
                : 1.44
              : current.cameraMode === "2.5d"
                ? isBoxMoment
                  ? 1.22
                  : 1.14
                : view.zoom;
          const targetZoom = directorActive ? baseZoom * director.zoomMultiplier : baseZoom;
          // TV cuts are snappier than the ambient drift
          const zoomEase = director.kind === "goal_cut" ? 0.18 : 0.05;
          view.zoom = view.zoom + (targetZoom - view.zoom) * zoomEase;
        }

        const directorPull = directorActive && director.focus ? 0.85 : 0;
        const trackStrengthX = Math.max(
          directorPull,
          current.cameraMode === "zoom" ? 0.46 : view.follow ? 0.32 : 0.22,
        );
        const trackStrengthY = Math.max(
          directorPull,
          current.cameraMode === "zoom" ? 0.34 : view.follow ? 0.26 : 0.1,
        );
        const tiltBiasY = current.cameraMode === "2.5d" ? -1.8 : 0;
        const panEase = director.kind === "goal_cut" ? 0.2 : 0.08;
        const nextPanX = camera.position.x + (focus.x * trackStrengthX - camera.position.x) * panEase;
        const nextPanY = camera.position.y + (focus.y * trackStrengthY + tiltBiasY - camera.position.y) * panEase;
        const clamped = clampCameraPan(nextPanX, nextPanY, view.zoom);
        view.panX = clamped.panX;
        view.panY = clamped.panY;
        view.zoom = clamped.zoom;
      } else {
        const clamped = clampCameraPan(view.panX, view.panY, view.zoom);
        view.panX = clamped.panX;
        view.panY = clamped.panY;
        view.zoom = clamped.zoom;
      }

      camera.zoom = view.zoom;
      camera.position.x = view.panX;
      camera.position.y = view.panY;
      camera.updateProjectionMatrix();

      seenKeys.clear();
      let selectedPlayerObj: PitchPlayer | null = null;
      let carrierPlayerObj: PitchPlayer | null = resolvedBall?.carrier ?? null;

      const animContext = {
        ball: activeBall
          ? {
              ...activeBall,
              x: ballPoint?.x ?? activeBall.x,
              y: ballPoint?.y ?? activeBall.y,
              height: resolvedBall?.heightMeters ?? activeBall.height ?? 0,
            }
          : ballPoint,
        possessionSide: activePossessionSide,
        primaryPlayerId: activePrimaryId,
        secondaryPlayerId: activeSecondaryId,
        stage: activeStage,
        homeAttacksRight: activeHomeAttacksRight,
      };

      activePlayers.forEach((player) => {
        const key = playerIdentityKey(player);
        seenKeys.add(key);

        const isCarrier =
          Boolean(player.hasBall) ||
          Boolean(resolvedBall?.carrier && playerIdentityKey(resolvedBall.carrier) === key);

        const tracked = motionTracker.update(key, player.x, player.y, frameStart, {
          baseAction: animationFor(player, activeEvent, animContext),
          hasBall: isCarrier,
          side: player.side,
          velocityHint: player.velocity,
          facingHint: player.facing,
        });

        const keeper = Boolean(player.isGoalkeeper) || String(player.role || "").toLowerCase().includes("gk");
        const kitColor = keeper
          ? player.side === "home"
            ? current.goalkeeperHome
            : current.goalkeeperAway
          : player.side === "home"
            ? current.homeColor
            : current.awayColor;

        const point = toWorld(player.x, player.y);
        const mesh = acquire(key);
        if (mesh) {
          mesh.position.set(point.x, point.y, 1 + (1 - player.y) * 0.05);
          const material = mesh.material as THREE.ShaderMaterial;
          const uv = cellUv(tracked.action, tracked.direction, tracked.frame);
          material.uniforms.uOffset.value.set(uv.offsetX, uv.offsetY);
          material.uniforms.uKitColor.value.set(kitColor);
          material.uniforms.uShirt.value = player.shirtNumber;
        }
        if (current.selectedKey === key) {
          selectedPlayerObj = player;
          ring.visible = true;
          ring.position.set(point.x, point.y - 1.2, 0.4);
          const pulse = 1 + Math.sin(frameStart / 190) * 0.06;
          ring.scale.set(pulse, pulse, 1);
        }
        if (isCarrier && !carrierPlayerObj) {
          carrierPlayerObj = player;
        }
      });

      if (!selectedPlayerObj) {
        ring.visible = false;
      }
      if (carrierPlayerObj) {
        const cp = toWorld((carrierPlayerObj as PitchPlayer).x, (carrierPlayerObj as PitchPlayer).y);
        carrierRing.visible = true;
        carrierRing.position.set(cp.x, cp.y - 1.2, 0.35);
      } else {
        carrierRing.visible = false;
      }

      assigned.forEach((mesh, key) => {
        if (!seenKeys.has(key)) {
          mesh.visible = false;
          assigned.delete(key);
          free.push(mesh);
        }
      });
      motionTracker.prune(seenKeys);

      // Pass lifecycle tracking → progressive-pass gain ring on the receiver
      const passEvent = String(activeEvent || "").toLowerCase();
      const isPassEvent = passEvent === "pass" || passEvent === "through_ball" || passEvent === "cross";
      const passer =
        (activePrimaryId && activePlayers.find((p) => p.playerId === activePrimaryId)) || carrierPlayerObj || null;
      const predictedReceiver =
        isPassEvent && resolvedBall?.inFlight ? predictPassReceiver(activeTrajectory, activePlayers, passer) : null;
      if (isPassEvent && resolvedBall?.inFlight && !pendingPass && passer) {
        const origin = activeTrajectory && activeTrajectory.length > 0 ? activeTrajectory[0] : passer;
        pendingPass = {
          from: { x: origin.x, y: origin.y },
          side: passer.side,
          receiverKey: predictedReceiver ? playerIdentityKey(predictedReceiver.player) : null,
        };
      } else if (pendingPass && !resolvedBall?.inFlight) {
        const receiver = carrierPlayerObj as PitchPlayer | null;
        if (receiver && receiver.side === pendingPass.side) {
          const meters = progressivePassMeters(pendingPass.from, receiver, receiver.side, activeHomeAttacksRight);
          if (meters >= 3) {
            passGainRing = { key: playerIdentityKey(receiver), meters, startedMs: frameStart };
          }
        }
        pendingPass = null;
      }
      if (passGainRing && frameStart - passGainRing.startedMs > 1400) passGainRing = null;
      const passGainPlayer = passGainRing
        ? activePlayers.find((p) => playerIdentityKey(p) === passGainRing!.key) || null
        : null;

      // Update tactical, trajectory & player callout overlay canvas
      const hasCalloutOrTrajectory = Boolean(
        carrierPlayerObj ||
          selectedPlayerObj ||
          activeEvent ||
          passGainPlayer ||
          (activeTrajectory && activeTrajectory.length > 1 && resolvedBall?.inFlight),
      );
      const anyOverlayActive = Boolean(
        (current.showVoronoi ||
          current.showHeatmap ||
          current.showTactics ||
          current.showPassingLanes ||
          current.showShotMap ||
          hasCalloutOrTrajectory) &&
          activePlayers.length > 0,
      );
      overlayMesh.visible = anyOverlayActive;
      const activeOverlayCtx = anyOverlayActive ? getOverlayCtx() : null;
      if (anyOverlayActive && activeOverlayCtx) {
        const carrierKey = carrierPlayerObj ? playerIdentityKey(carrierPlayerObj) : "";
        const sig = `${current.showVoronoi ? 1 : 0}:${current.showHeatmap ? 1 : 0}:${current.showTactics ? 1 : 0}:${current.showPassingLanes ? 1 : 0}:${current.showShotMap ? 1 : 0}:${current.shotMarkers?.length || 0}:${current.selectedKey || ""}:${carrierKey}:${activeEvent || ""}`;
        if (sig !== lastOverlaySignature || frameStart - lastOverlayPaintMs >= 55) {
          lastOverlaySignature = sig;
          lastOverlayPaintMs = frameStart;
          paintTacticalOverlays(activeOverlayCtx, {
            players: activePlayers,
            ball: ballPoint,
            resolvedBall,
            ballTrajectory: activeTrajectory,
            trajectoryAlpha: activeAlpha,
            eventType: activeEvent,
            selectedKey: current.selectedKey || null,
            carrierPlayer: carrierPlayerObj,
            selectedPlayer: selectedPlayerObj,
            homeColor: current.homeColor,
            awayColor: current.awayColor,
            showVoronoi: Boolean(current.showVoronoi),
            showHeatmap: Boolean(current.showHeatmap),
            showTactics: Boolean(current.showTactics),
            showPassingLanes: Boolean(current.showPassingLanes),
            showShotMap: Boolean(current.showShotMap),
            shotMarkers: current.shotMarkers || [],
            heatmapBins,
            motionTracker,
            predictedReceiver,
            passGain:
              passGainPlayer && passGainRing
                ? {
                    player: passGainPlayer,
                    meters: passGainRing.meters,
                    progress: Math.min(1, (frameStart - passGainRing.startedMs) / 1400),
                  }
                : null,
          });
          overlayTexture.needsUpdate = true;
        }
      }

      const cue = effectFor(activeEvent);
      if (ballPoint) {
        const shadowWorld = toWorld(resolvedBall?.shadowX ?? ballPoint.x, resolvedBall?.shadowY ?? ballPoint.y);
        const point = toWorld(ballPoint.x, ballPoint.y);
        const elev = resolvedBall?.heightMeters ?? 0;
        const liftY = Math.min(4.2, elev * 0.92);
        const scaleBoost = 1 + Math.min(0.32, elev * 0.09);

        if (elev > 0.14) {
          ballShadowMesh.visible = true;
          ballShadowMesh.position.set(shadowWorld.x, shadowWorld.y - 0.35, 1.4);
          const shadowScale = Math.max(0.55, 1 - elev * 0.1);
          ballShadowMesh.scale.set(shadowScale, shadowScale, 1);
          ballShadowMaterial.opacity = Math.max(0.18, 0.46 - elev * 0.07);
        } else {
          ballShadowMesh.visible = false;
        }

        ballMesh.position.set(point.x, point.y + liftY, 2.1);
        ballMesh.scale.set(scaleBoost, scaleBoost, 1);
        ballMesh.visible = true;

        // Ball spin rotation — rate proportional to speed; faster when aerial
        const spinRate = resolvedBall
          ? resolvedBall.speedNorm * (resolvedBall.inFlight ? 0.14 : 0.06)
          : 0;
        ballSpinAngle += spinRate;
        ballMesh.rotation.z = ballSpinAngle;

        // Ground bounce squash/stretch — trigger when ball transitions from aerial to ground
        const curElev = elev;
        if (lastBallHeightMeters > 0.4 && curElev < 0.12) {
          // Landing detected — trigger squash pulse
          ballBounceScale = 0.7;
        }
        lastBallHeightMeters = curElev;
        // Recover bounce scale back to 1 smoothly
        if (ballBounceScale < 1) {
          ballBounceScale = Math.min(1, ballBounceScale + 0.08);
          const stretchX = 1 / Math.max(0.6, ballBounceScale);
          ballMesh.scale.set(scaleBoost * stretchX, scaleBoost * ballBounceScale, 1);
        }

        const from = previousBall ? toWorld(previousBall.x, previousBall.y) : point;
        effect.visible = cue === "pass" || cue === "shot" || cue === "goal";
        if (effect.visible) {
          const dx = point.x - from.x;
          const dy = point.y - from.y;
          const length = Math.max(1.2, Math.hypot(dx, dy));
          effect.scale.set(length, cue === "goal" ? 2.4 : 1, 1);
          effect.position.set((point.x + from.x) / 2, (point.y + from.y) / 2, 0.6);
          effect.rotation.z = Math.atan2(dy, dx);
          effectMaterial.color.set(cue === "goal" ? "#ffffff" : cue === "shot" ? "#f43f5e" : "#67e8f9");
          effectMaterial.opacity =
            cue === "goal" ? 0.45 + Math.abs(Math.sin(frameStart / 120)) * 0.4 : 0.85;
        }
        previousBall = ballPoint;
      } else {
        ballMesh.visible = false;
        ballShadowMesh.visible = false;
        effect.visible = false;
      }

      if (cue === "save" || cue === "card" || cue === "substitution") {
        const focus = selectedPlayerObj || carrierPlayerObj || activePlayers[0];
        if (focus) {
          const point = toWorld(focus.x, focus.y);
          cueMesh.visible = true;
          cueMesh.position.set(point.x, point.y + 2.2, 1.5);
          cueMaterial.color.set(cue === "save" ? "#38bdf8" : cue === "card" ? "#facc15" : "#a78bfa");
          cueMaterial.opacity = 0.35 + Math.abs(Math.sin(frameStart / 180)) * 0.35;
        } else {
          cueMesh.visible = false;
        }
      } else {
        cueMesh.visible = false;
      }

      const objectCount = sceneObjectCount(activePlayers.length, Boolean(cue));
      lastRenderProfile.objectCount = objectCount;
      lastRenderProfile.activePlayerSprites = assigned.size;
      lastRenderProfile.feedFreshness = current.feedStatus;

      fpsFrames += 1;
      const elapsed = frameStart - fpsStarted;
      if (elapsed >= 1000) {
        lastRenderProfile.fps = Math.round((fpsFrames * 1000) / elapsed);
        lastRenderProfile.frameMs = elapsed / Math.max(1, fpsFrames);
        fpsFrames = 0;
        fpsStarted = frameStart;
        if (process.env.NODE_ENV !== "production" && !lastRenderProfile.logged) {
          lastRenderProfile.logged = true;
          // eslint-disable-next-line no-console
          console.info("[match2d]", lastRenderProfile);
        }
      }
      lastRenderProfile.frameMs = Math.max(lastRenderProfile.frameMs, performance.now() - frameStart);

      if (renderer && !contextLost) {
        renderer.render(scene, camera);
        lastRenderProfile.calls = renderer.info?.render?.calls ?? 0;
        lastRenderProfile.sampledFrames += 1;
      } else if (fallback && fallbackCanvas) {
        paintCanvasFallback(fallback, fallbackCanvas, {
          players: activePlayers,
          eventType: activeEvent,
          homeColor: current.homeColor,
          awayColor: current.awayColor,
          goalkeeperHome: current.goalkeeperHome,
          goalkeeperAway: current.goalkeeperAway,
          selectedKey: current.selectedKey || null,
          ballPoint,
          resolvedBall,
          camera: view,
          overlayCanvas: anyOverlayActive ? overlayCanvas : null,
          motionTracker,
        });
        lastRenderProfile.sampledFrames += 1;
      }

      if (typeof window !== "undefined") {
        (window as unknown as { __GTEX_MATCH2D_TELEMETRY__?: typeof lastRenderProfile }).__GTEX_MATCH2D_TELEMETRY__ =
          lastRenderProfile;
      }
    };
    paint();

    let dragging = false;
    let activePointerId: number | null = null;
    let lastX = 0;
    let lastY = 0;
    let dragDistance = 0;
    let lastHandledPointerUpMs = 0;

    const selectAtClientPoint = (clientX: number, clientY: number) => {
      if (!onSelect) return;
      const activeCanvas = (!contextLost && renderer?.domElement) || fallbackCanvas || host;
      const rect = activeCanvas.getBoundingClientRect();
      if (!rect || rect.width <= 0 || rect.height <= 0) return;
      const pitchPoint = screenToPitchPoint(clientX, clientY, rect, cameraRef.current);
      const liveSampled = propsRef.current.sampleFrame ? propsRef.current.sampleFrame(performance.now()) : null;
      const activePlayers =
        liveSampled && liveSampled.players.length > 0 ? liveSampled.players : propsRef.current.players;
      const hit = pickPlayerAtPoint(activePlayers, pitchPoint, cameraRef.current.zoom);
      if (hit) {
        onSelect(playerIdentityKey(hit));
      }
    };

    const onPointerDown = (event: PointerEvent) => {
      if (event.button !== undefined && event.button !== 0) return;
      dragging = true;
      activePointerId = event.pointerId;
      lastX = event.clientX;
      lastY = event.clientY;
      dragDistance = 0;
      try {
        host.setPointerCapture?.(event.pointerId);
      } catch {
        // Ignore in environments without pointer capture
      }
    };

    const onPointerMove = (event: PointerEvent) => {
      if (!dragging) return;
      if (activePointerId !== null && event.pointerId !== undefined && event.pointerId !== activePointerId) return;
      const dx = event.clientX - lastX;
      const dy = event.clientY - lastY;
      lastX = event.clientX;
      lastY = event.clientY;
      dragDistance += Math.hypot(dx, dy);
      if (dragDistance > 4) {
        const rect = host.getBoundingClientRect();
        const width = Math.max(320, rect.width || 320);
        const height = Math.max(200, rect.height || 200);
        const zoom = Math.max(0.8, cameraRef.current.zoom);
        const worldDx = (dx / width) * (PITCH_W / zoom);
        const worldDy = (dy / height) * (PITCH_H / zoom);
        const clamped = clampCameraPan(
          cameraRef.current.panX - worldDx,
          cameraRef.current.panY + worldDy,
          zoom,
        );
        cameraRef.current.panX = clamped.panX;
        cameraRef.current.panY = clamped.panY;
        cameraRef.current.manualOverrideUntilMs = performance.now() + 4500;
      }
    };

    const onPointerUp = (event: PointerEvent) => {
      if (!dragging) return;
      if (activePointerId !== null && event.pointerId !== undefined && event.pointerId !== activePointerId) return;
      const wasClick = dragDistance <= 5;
      dragging = false;
      activePointerId = null;
      try {
        if (event.pointerId !== undefined) {
          host.releasePointerCapture?.(event.pointerId);
        }
      } catch {
        // Ignore
      }
      if (wasClick) {
        lastHandledPointerUpMs = performance.now();
        selectAtClientPoint(event.clientX, event.clientY);
      }
    };

    const onPointerCancel = (event: PointerEvent) => {
      dragging = false;
      activePointerId = null;
      dragDistance = 0;
      try {
        if (event.pointerId !== undefined) {
          host.releasePointerCapture?.(event.pointerId);
        }
      } catch {
        // Ignore
      }
    };

    const onClick = (event: MouseEvent) => {
      if (performance.now() - lastHandledPointerUpMs < 80) return;
      if (dragDistance > 5 || Math.abs(event.movementX || 0) + Math.abs(event.movementY || 0) > 6) return;
      selectAtClientPoint(event.clientX, event.clientY);
    };

    host.addEventListener("pointerdown", onPointerDown);
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);
    window.addEventListener("pointercancel", onPointerCancel);
    host.addEventListener("click", onClick);

    return () => {
      stopped = true;
      window.cancelAnimationFrame(frameId);
      observer?.disconnect();
      host.removeEventListener("pointerdown", onPointerDown);
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
      window.removeEventListener("pointercancel", onPointerCancel);
      host.removeEventListener("click", onClick);
      renderer?.domElement.removeEventListener("webglcontextlost", onContextLost);
      renderer?.domElement.removeEventListener("webglcontextrestored", onContextRestored);

      pool.forEach((mesh) => (mesh.material as THREE.Material).dispose());
      sharedGeometry.dispose();
      pitchGeometry.dispose();
      pitchMaterial.dispose();
      overlayGeometry.dispose();
      overlayMaterial.dispose();
      ballShadowGeometry.dispose();
      ballShadowMaterial.dispose();
      ballGeometry.dispose();
      ballMaterial.dispose();
      ringGeometry.dispose();
      ringMaterial.dispose();
      carrierRingGeometry.dispose();
      carrierRingMaterial.dispose();
      effectGeometry.dispose();
      effectMaterial.dispose();
      cueGeometry.dispose();
      cueMaterial.dispose();

      pitchTexture.dispose();
      overlayTexture.dispose();
      bodyTexture.dispose();
      kitTexture.dispose();
      digitTexture.dispose();
      ballTexture.dispose();
      ringTexture.dispose();

      renderer?.dispose();
      renderer?.domElement.remove();
      fallbackCanvas?.remove();
      motionTracker.clear();

      lastRenderProfile.activeRenderers = Math.max(0, lastRenderProfile.activeRenderers - 1);
      if (lastRenderProfile.activeRenderers === 0) {
        lastRenderProfile.rendererMode = "unmounted";
      }
    };
  }, [onSelect]);

  return (
    <div
      className="space-y-2"
      data-testid="orthographic-pitch"
      data-camera-mode={cameraMode}
      data-zoom={zoomLevel.toFixed(2)}
      data-overlay-voronoi={showVoronoi ? "on" : "off"}
      data-overlay-heatmap={showHeatmap ? "on" : "off"}
      data-overlay-tactics={showTactics ? "on" : "off"}
      data-overlay-lanes={showPassingLanes ? "on" : "off"}
      data-overlay-shotmap={showShotMap ? "on" : "off"}
      data-feed-status={effectiveFeedStatus}
    >
      <div
        ref={hostRef}
        data-testid="orthographic-pitch-mount"
        className="relative aspect-[16/10] w-full overflow-hidden rounded-xl border border-emerald-500/40 bg-[#0c2418] shadow-[0_18px_48px_rgba(0,0,0,0.65)] select-none"
      />
      <div className="flex flex-wrap items-center justify-between gap-2 text-[10px] font-black uppercase tracking-wider">
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            type="button"
            data-testid="pitch-control-fit"
            className="rounded border border-white/15 bg-slate-900/80 px-2.5 py-1 text-slate-200 transition hover:border-emerald-400/50 hover:text-white"
            onClick={() => {
              cameraRef.current = { zoom: 1, panX: 0, panY: 0, follow: false, manualOverrideUntilMs: 0 };
              setFollow(false);
              setZoomLevel(1);
              onCameraModeChange?.("2d");
            }}
          >
            Fit
          </button>
          <button
            type="button"
            data-testid="pitch-control-zoom-in"
            className="rounded border border-white/15 bg-slate-900/80 px-2.5 py-1 text-slate-200 transition hover:border-emerald-400/50 hover:text-white"
            onClick={() => {
              const clamped = clampCameraPan(
                cameraRef.current.panX,
                cameraRef.current.panY,
                Math.min(2.6, cameraRef.current.zoom + 0.2),
              );
              cameraRef.current.zoom = clamped.zoom;
              cameraRef.current.panX = clamped.panX;
              cameraRef.current.panY = clamped.panY;
              cameraRef.current.manualOverrideUntilMs = performance.now() + 6000;
              setZoomLevel(clamped.zoom);
            }}
          >
            Zoom in
          </button>
          <button
            type="button"
            data-testid="pitch-control-zoom-out"
            className="rounded border border-white/15 bg-slate-900/80 px-2.5 py-1 text-slate-200 transition hover:border-emerald-400/50 hover:text-white"
            onClick={() => {
              const clamped = clampCameraPan(
                cameraRef.current.panX,
                cameraRef.current.panY,
                Math.max(0.8, cameraRef.current.zoom - 0.2),
              );
              cameraRef.current.zoom = clamped.zoom;
              cameraRef.current.panX = clamped.panX;
              cameraRef.current.panY = clamped.panY;
              cameraRef.current.manualOverrideUntilMs = performance.now() + 6000;
              setZoomLevel(clamped.zoom);
            }}
          >
            Zoom out
          </button>
          <button
            type="button"
            data-testid="pitch-control-follow"
            className={`rounded border px-2.5 py-1 transition ${
              follow
                ? "border-emerald-400/60 bg-emerald-500/20 text-emerald-300"
                : "border-white/15 bg-slate-900/80 text-slate-200 hover:text-white"
            }`}
            onClick={() => setFollow((value) => !value)}
          >
            {follow ? "Follow on" : "Follow"}
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-1.5 text-[9px] text-slate-400">
          {showVoronoi && (
            <span className="rounded bg-blue-500/20 px-1.5 py-0.5 text-blue-300" data-testid="active-overlay-voronoi">
              VORONOI
            </span>
          )}
          {showHeatmap && (
            <span className="rounded bg-rose-500/20 px-1.5 py-0.5 text-rose-300" data-testid="active-overlay-heatmap">
              HEATMAP
            </span>
          )}
          {showTactics && (
            <span className="rounded bg-emerald-500/20 px-1.5 py-0.5 text-emerald-300" data-testid="active-overlay-tactics">
              TACTICS
            </span>
          )}
          {showPassingLanes && (
            <span className="rounded bg-cyan-500/20 px-1.5 py-0.5 text-cyan-300" data-testid="active-overlay-lanes">
              PASSING LANES
            </span>
          )}
          {showShotMap && (
            <span className="rounded bg-amber-500/20 px-1.5 py-0.5 text-amber-300" data-testid="active-overlay-shotmap">
              SHOT MAP (xG)
            </span>
          )}
          {feedAgeSeconds !== null && feedAgeSeconds > 0 && feedStatus === "DELAYED" && (
            <span className="font-mono text-amber-300" data-testid="pitch-feed-age">
              {feedAgeSeconds}s old
            </span>
          )}
        </div>
      </div>
      {unavailable && (
        <p
          data-testid="pitch-feed-unavailable-banner"
          className="rounded border border-amber-400/40 bg-amber-500/10 px-3 py-2 text-xs font-bold text-amber-200"
        >
          MATCH FEED UNAVAILABLE — RECONNECTING
        </p>
      )}
      {demo && (
        <p data-testid="pitch-demo-badge" className="text-[10px] font-black uppercase tracking-widest text-amber-300">
          DEMO
        </p>
      )}
      <span className="sr-only">
        draw-budget {CELL} fps {lastRenderProfile.fps} objects {lastRenderProfile.objectCount}
      </span>
    </div>
  );
}

export const OrthographicPitch = memo(OrthographicPitchComponent);

function shortPlayerName(name: string): string {
  const trimmed = String(name || "").trim();
  if (!trimmed) return "";
  const parts = trimmed.split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 12);
  return `${parts[0][0]}. ${parts[parts.length - 1]}`.slice(0, 14);
}

function paintTacticalOverlays(
  ctx: CanvasRenderingContext2D,
  input: {
    players: PitchPlayer[];
    ball: { x: number; y: number } | null;
    resolvedBall?: ReturnType<typeof resolveBallPresentation>;
    ballTrajectory?: PitchBall[] | null;
    trajectoryAlpha?: number;
    eventType?: string | null;
    selectedKey: string | null;
    carrierPlayer: PitchPlayer | null;
    selectedPlayer: PitchPlayer | null;
    homeColor: string;
    awayColor: string;
    showVoronoi: boolean;
    showHeatmap: boolean;
    showTactics: boolean;
    showPassingLanes: boolean;
    showShotMap: boolean;
    shotMarkers?: PitchShotMarker[];
    heatmapBins: Float32Array;
    motionTracker: PlayerMotionTracker;
    predictedReceiver?: { player: PitchPlayer; target: { x: number; y: number } } | null;
    passGain?: { player: PitchPlayer; meters: number; progress: number } | null;
  },
) {
  ctx.clearRect(0, 0, OVERLAY_W, OVERLAY_H);
  const { players, ball, resolvedBall, ballTrajectory, selectedKey, homeColor, awayColor } = input;
  if (!players.length) return;

  const cellW = OVERLAY_W / GRID_W;
  const cellH = OVERLAY_H / GRID_H;

  // 1. Voronoi Space Control Overlay (computed from real player positions + live territory share)
  if (input.showVoronoi) {
    const homeFill = hexToRgbaString(homeColor, 0.2);
    const awayFill = hexToRgbaString(awayColor, 0.2);
    const owners = new Uint8Array(GRID_W * GRID_H);
    let homeCells = 0;
    let totalCells = 0;

    for (let gy = 0; gy < GRID_H; gy += 1) {
      const py = (gy + 0.5) / GRID_H;
      for (let gx = 0; gx < GRID_W; gx += 1) {
        const px = (gx + 0.5) / GRID_W;
        let nearestSide: "home" | "away" = "home";
        let minDistSq = Infinity;
        for (const p of players) {
          const dx = p.x - px;
          const dy = p.y - py;
          const dSq = dx * dx + dy * dy;
          if (dSq < minDistSq) {
            minDistSq = dSq;
            nearestSide = p.side;
          }
        }
        const isHome = nearestSide === "home";
        if (isHome) homeCells += 1;
        totalCells += 1;
        owners[gy * GRID_W + gx] = isHome ? 1 : 2;
        ctx.fillStyle = isHome ? homeFill : awayFill;
        ctx.fillRect(gx * cellW, gy * cellH, cellW + 0.6, cellH + 0.6);
      }
    }

    // Crisp boundary contour between home and away territory
    ctx.fillStyle = "rgba(248, 250, 252, 0.52)";
    for (let gy = 0; gy < GRID_H - 1; gy += 1) {
      for (let gx = 0; gx < GRID_W - 1; gx += 1) {
        const currentOwner = owners[gy * GRID_W + gx];
        if (currentOwner !== owners[gy * GRID_W + gx + 1] || currentOwner !== owners[(gy + 1) * GRID_W + gx]) {
          ctx.fillRect(gx * cellW, gy * cellH, 2.4, 2.4);
        }
      }
    }

    const homeShare = Math.round((homeCells / Math.max(1, totalCells)) * 100);
    const awayShare = 100 - homeShare;
    drawRoundedBannerBox(
      ctx,
      OVERLAY_W / 2 - 148,
      6,
      296,
      22,
      "rgba(2, 6, 23, 0.84)",
      "rgba(148, 163, 184, 0.45)",
    );
    ctx.font = "bold 10px sans-serif";
    ctx.textAlign = "center";
    ctx.fillStyle = "#f8fafc";
    safeFillText(ctx, `TERRITORY CONTROL · HOME ${homeShare}% — ${awayShare}% AWAY`, OVERLAY_W / 2, 20);
  }

  // 2. Heatmap Overlay (from accumulated real player position samples)
  if (input.showHeatmap) {
    for (let gy = 0; gy < GRID_H; gy += 1) {
      for (let gx = 0; gx < GRID_W; gx += 1) {
        const density = input.heatmapBins[gy * GRID_W + gx];
        if (density <= 0.06) continue;
        const intensity = Math.min(1, density / 3.4);
        const cx = (gx + 0.5) * cellW;
        const cy = (gy + 0.5) * cellH;
        const radius = cellW * (2.1 + intensity * 1.6);
        if (typeof ctx.createRadialGradient === "function") {
          const grad = ctx.createRadialGradient(cx, cy, 1, cx, cy, radius);
          grad.addColorStop(0, `rgba(239, 68, 68, ${(0.46 * intensity).toFixed(3)})`);
          grad.addColorStop(0.48, `rgba(245, 158, 11, ${(0.28 * intensity).toFixed(3)})`);
          grad.addColorStop(0.82, `rgba(16, 185, 129, ${(0.12 * intensity).toFixed(3)})`);
          grad.addColorStop(1, "rgba(16, 185, 129, 0)");
          ctx.fillStyle = grad;
        } else {
          ctx.fillStyle = `rgba(239, 68, 68, ${(0.34 * intensity).toFixed(3)})`;
        }
        ctx.fillRect(cx - radius, cy - radius, radius * 2, radius * 2);
      }
    }
  }

  // 3. Tactical Overlay: Defensive/Midfield/Attacking Lines, Compactness Block, Pressing Rings & Run Vectors
  if (input.showTactics) {
    (["home", "away"] as const).forEach((side) => {
      const color = side === "home" ? homeColor : awayColor;
      const sidePlayers = players.filter(
        (p) => p.side === side && !p.isGoalkeeper && !/gk|goal/i.test(String(p.role || "")),
      );
      if (sidePlayers.length === 0) return;

      // Sort along X relative to defended goal to partition Defense / Midfield / Attack lines
      const sortedX = [...sidePlayers].sort((a, b) => (side === "home" ? a.x - b.x : b.x - a.x));
      const defCount = Math.min(4, Math.max(3, Math.round(sortedX.length * 0.4)));
      const midCount = Math.min(4, Math.max(2, Math.round(sortedX.length * 0.35)));
      const defenders = sortedX.slice(0, defCount);
      const midfielders = sortedX.slice(defCount, defCount + midCount);
      const forwards = sortedX.slice(defCount + midCount);

      const defLineNormX = defenders.reduce((sum, p) => sum + p.x, 0) / Math.max(1, defenders.length);
      const defLineX = defLineNormX * OVERLAY_W;

      ctx.save();
      // Defensive Line + Height Label
      ctx.strokeStyle = hexToRgbaString(color, 0.85);
      ctx.lineWidth = 2.2;
      ctx.setLineDash([7, 5]);
      ctx.beginPath();
      ctx.moveTo(defLineX, 24);
      ctx.lineTo(defLineX, OVERLAY_H - 24);
      ctx.stroke();

      const defMeters = Math.round((side === "home" ? defLineNormX : 1 - defLineNormX) * 105);
      drawRoundedBannerBox(
        ctx,
        Math.min(OVERLAY_W - 88, Math.max(8, defLineX - 42)),
        side === "home" ? 28 : OVERLAY_H - 48,
        84,
        18,
        "rgba(2, 6, 23, 0.86)",
        hexToRgbaString(color, 0.75),
      );
      ctx.font = "bold 9px sans-serif";
      ctx.textAlign = "center";
      ctx.fillStyle = color;
      safeFillText(ctx, 
        `${side === "home" ? "HOME" : "AWAY"} LINE ${defMeters}m`,
        Math.min(OVERLAY_W - 46, Math.max(50, defLineX)),
        side === "home" ? 40 : OVERLAY_H - 36,
      );

      // Team Compactness & Pressing Shape Envelope
      const minX = Math.min(...sidePlayers.map((p) => p.x)) * OVERLAY_W;
      const maxX = Math.max(...sidePlayers.map((p) => p.x)) * OVERLAY_W;
      const minY = Math.min(...sidePlayers.map((p) => p.y)) * OVERLAY_H;
      const maxY = Math.max(...sidePlayers.map((p) => p.y)) * OVERLAY_H;
      ctx.fillStyle = hexToRgbaString(color, 0.08);
      ctx.strokeStyle = hexToRgbaString(color, 0.42);
      ctx.lineWidth = 1.4;
      ctx.setLineDash([4, 4]);
      ctx.strokeRect(minX, minY, Math.max(8, maxX - minX), Math.max(8, maxY - minY));
      ctx.fillRect(minX, minY, Math.max(8, maxX - minX), Math.max(8, maxY - minY));

      // Formation unit links across Defense, Midfield, and Attack lines
      ctx.setLineDash([]);
      const drawUnitChain = (unit: PitchPlayer[], alpha: number) => {
        if (unit.length < 2) return;
        const ordered = [...unit].sort((a, b) => a.y - b.y);
        ctx.strokeStyle = hexToRgbaString(color, alpha);
        ctx.lineWidth = 1.8;
        for (let i = 0; i < ordered.length - 1; i += 1) {
          ctx.beginPath();
          ctx.moveTo(ordered[i].x * OVERLAY_W, ordered[i].y * OVERLAY_H);
          ctx.lineTo(ordered[i + 1].x * OVERLAY_W, ordered[i + 1].y * OVERLAY_H);
          ctx.stroke();
        }
      };
      drawUnitChain(defenders, 0.58);
      drawUnitChain(midfielders, 0.48);
      drawUnitChain(forwards, 0.42);
      ctx.restore();
    });

    // Pressing triggers & forward movement run vectors
    for (const p of players) {
      const tracked = input.motionTracker.get(playerIdentityKey(p));
      const startX = p.x * OVERLAY_W;
      const startY = p.y * OVERLAY_H;
      const color = p.side === "home" ? homeColor : awayColor;
      const stateStr = `${p.state || ""} ${p.animationState || ""}`.toLowerCase();

      if (stateStr.includes("press") || stateStr.includes("tackle")) {
        ctx.save();
        ctx.strokeStyle = "rgba(250, 204, 21, 0.85)";
        ctx.lineWidth = 1.8;
        strokePolyCircle(ctx, startX, startY, 15, 10, 20);
        ctx.restore();
      }

      if (!tracked || tracked.speed < 0.0025) continue;
      const vecLen = Math.min(34, Math.max(12, tracked.speed * 620));
      const endX = startX + Math.cos(tracked.facing) * vecLen;
      const endY = startY - Math.sin(tracked.facing) * vecLen;
      ctx.save();
      ctx.strokeStyle = color;
      ctx.lineWidth = 2.0;
      ctx.beginPath();
      ctx.moveTo(startX, startY);
      ctx.lineTo(endX, endY);
      ctx.stroke();
      // Arrowhead
      const headAngle = Math.atan2(endY - startY, endX - startX);
      ctx.beginPath();
      ctx.moveTo(endX, endY);
      ctx.lineTo(endX - Math.cos(headAngle - 0.5) * 6, endY - Math.sin(headAngle - 0.5) * 6);
      ctx.lineTo(endX - Math.cos(headAngle + 0.5) * 6, endY - Math.sin(headAngle + 0.5) * 6);
      ctx.closePath();
      ctx.fillStyle = color;
      ctx.fill();
      ctx.restore();
    }
  }

  // 4. Passing LanesOverlay
  if (input.showPassingLanes) {
    const selectedPlayer = selectedKey
      ? players.find((p) => playerIdentityKey(p) === selectedKey) || null
      : null;
    const carrier =
      selectedPlayer ||
      input.carrierPlayer ||
      players.find((p) => p.hasBall) ||
      (ball
        ? [...players].sort(
            (a, b) => Math.hypot(a.x - ball.x, a.y - ball.y) - Math.hypot(b.x - ball.x, b.y - ball.y),
          )[0] || null
        : null);

    if (carrier) {
      const teammates = players.filter(
        (p) => p.side === carrier.side && p.playerId !== carrier.playerId,
      );
      const opponents = players.filter((p) => p.side !== carrier.side);
      const laneColor = carrier.side === "home" ? homeColor : awayColor;
      const attackDir = carrier.side === "home" ? 1 : -1;

      const viableTargets = teammates
        .map((mate) => {
          const dist = Math.hypot(mate.x - carrier.x, mate.y - carrier.y);
          const minClearance = opponents.reduce(
            (minD, opp) =>
              Math.min(minD, pointToSegmentDistance(opp.x, opp.y, carrier.x, carrier.y, mate.x, mate.y)),
            1,
          );
          const progressiveGain = (mate.x - carrier.x) * attackDir;
          const score = minClearance * 2.2 + progressiveGain * 1.4 - dist * 0.65;
          return { mate, dist, blocked: minClearance < 0.038, progressive: progressiveGain > 0.04, score };
        })
        .filter((item) => item.dist >= 0.045 && item.dist <= 0.52 && !item.blocked)
        .sort((a, b) => b.score - a.score)
        .slice(0, 4);

      ctx.save();
      viableTargets.forEach(({ mate, progressive }, idx) => {
        const cx = carrier.x * OVERLAY_W;
        const cy = carrier.y * OVERLAY_H;
        const mx = mate.x * OVERLAY_W;
        const my = mate.y * OVERLAY_H;
        const isPrimaryLane = idx === 0 || progressive;

        ctx.strokeStyle = isPrimaryLane ? hexToRgbaString(laneColor, 0.9) : "rgba(103, 232, 249, 0.68)";
        ctx.lineWidth = isPrimaryLane ? 2.4 : 1.7;
        ctx.setLineDash(isPrimaryLane ? [7, 4] : [4, 4]);
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(mx, my);
        ctx.stroke();

        // Target receiver diamond + shirt number callout
        ctx.setLineDash([]);
        ctx.beginPath();
        ctx.moveTo(mx, my - 7);
        ctx.lineTo(mx + 7, my);
        ctx.lineTo(mx, my + 7);
        ctx.lineTo(mx - 7, my);
        ctx.closePath();
        ctx.fillStyle = "rgba(2, 6, 23, 0.85)";
        ctx.fill();
        ctx.stroke();

        if (mate.shirtNumber) {
          const badgeText = `#${mate.shirtNumber}`;
          const badgeY = my + 16;
          drawRoundedBannerBox(ctx, mx - 13, badgeY - 7, 26, 13, "rgba(2, 6, 23, 0.88)", "rgba(148, 163, 184, 0.45)");
          ctx.font = "bold 8.5px sans-serif";
          ctx.textAlign = "center";
          ctx.fillStyle = "#f8fafc";
          safeFillText(ctx, badgeText, mx, badgeY + 2.5);
        }
      });
      ctx.restore();
    }
  }

  // 5. Active Ball Flight Trajectory Arc (shown when ball is in flight or Passing Lanes overlay is active)
  if (
    ballTrajectory &&
    ballTrajectory.length > 1 &&
    (input.showPassingLanes || resolvedBall?.inFlight)
  ) {
    ctx.save();
    const isShot = resolvedBall?.flightKind === "shot" || resolvedBall?.flightKind === "in_goal";
    const arcHex = isShot ? "#f43f5e" : passArcColor(resolvedBall?.flightKind);
    ctx.strokeStyle = hexToRgbaString(arcHex, isShot ? 0.88 : 0.84);
    ctx.lineWidth = isShot ? 2.8 : 2.1;
    ctx.setLineDash(isShot ? [] : [5, 4]);
    ctx.beginPath();
    ctx.moveTo(ballTrajectory[0].x * OVERLAY_W, ballTrajectory[0].y * OVERLAY_H);
    for (let i = 1; i < ballTrajectory.length; i += 1) {
      const pt = ballTrajectory[i];
      const liftOffset = (pt.height ?? 0) * 5.5;
      ctx.lineTo(pt.x * OVERLAY_W, pt.y * OVERLAY_H - liftOffset);
    }
    ctx.stroke();

    // Moving pass-speed pace dot along the trajectory arc
    const alpha = Math.max(0, Math.min(1, input.trajectoryAlpha ?? 0.5));
    const exactIdx = alpha * (ballTrajectory.length - 1);
    const lo = Math.floor(exactIdx);
    const hi = Math.min(ballTrajectory.length - 1, lo + 1);
    const frac = exactIdx - lo;
    const p0 = ballTrajectory[lo];
    const p1 = ballTrajectory[hi];
    const dotX = (p0.x + (p1.x - p0.x) * frac) * OVERLAY_W;
    const dotLift = ((p0.height ?? 0) + ((p1.height ?? 0) - (p0.height ?? 0)) * frac) * 5.5;
    const dotY = (p0.y + (p1.y - p0.y) * frac) * OVERLAY_H - dotLift;
    ctx.setLineDash([]);
    ctx.fillStyle = arcHex;
    fillPolyCircle(ctx, dotX, dotY, 4.5, 4.5, 12);
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 1.2;
    strokePolyCircle(ctx, dotX, dotY, 6.2, 6.2, 12);
    ctx.restore();
  }

  // 5A. Pass Receiver Ghost (predicted receive position while pass is in flight)
  if (input.predictedReceiver) {
    const { player: recv, target } = input.predictedReceiver;
    const gx = target.x * OVERLAY_W;
    const gy = target.y * OVERLAY_H;
    const rx = recv.x * OVERLAY_W;
    const ry = recv.y * OVERLAY_H;
    const ghostColor = recv.side === "home" ? homeColor : awayColor;
    ctx.save();
    ctx.strokeStyle = hexToRgbaString(ghostColor, 0.55);
    ctx.lineWidth = 1.4;
    ctx.setLineDash([3, 3]);
    ctx.beginPath();
    ctx.moveTo(rx, ry);
    ctx.lineTo(gx, gy);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = hexToRgbaString(ghostColor, 0.22);
    fillPolyCircle(ctx, gx, gy, 9, 9, 16);
    ctx.strokeStyle = hexToRgbaString(ghostColor, 0.82);
    ctx.lineWidth = 1.6;
    strokePolyCircle(ctx, gx, gy, 9, 9, 16);
    if (recv.shirtNumber) {
      ctx.font = "bold 8.5px sans-serif";
      ctx.textAlign = "center";
      ctx.fillStyle = "#f8fafc";
      safeFillText(ctx, `#${recv.shirtNumber}`, gx, gy + 3);
    }
    ctx.restore();
  }

  // 5A-2. Progressive Pass Delta Ring (territory gain flash on receiver after completed pass)
  if (input.passGain) {
    const { player: recv, meters, progress } = input.passGain;
    const rx = recv.x * OVERLAY_W;
    const ry = recv.y * OVERLAY_H;
    const fade = Math.max(0, 1 - progress);
    const radiusX = 14 + progress * 14;
    const radiusY = 10 + progress * 10;
    ctx.save();
    ctx.strokeStyle = `rgba(52, 211, 153, ${(0.88 * fade).toFixed(3)})`;
    ctx.lineWidth = 2.0;
    strokePolyCircle(ctx, rx, ry, radiusX, radiusY, 20);
    const badgeY = Math.max(18, ry - 26 - progress * 6);
    drawRoundedBannerBox(
      ctx,
      rx - 26,
      badgeY - 7,
      52,
      14,
      `rgba(6, 78, 59, ${(0.9 * fade).toFixed(3)})`,
      `rgba(52, 211, 153, ${(0.85 * fade).toFixed(3)})`,
    );
    ctx.font = "bold 8.5px sans-serif";
    ctx.textAlign = "center";
    ctx.fillStyle = `rgba(209, 250, 229, ${Math.min(1, fade + 0.15).toFixed(3)})`;
    safeFillText(ctx, `+${Math.round(meters)}m`, rx, badgeY + 3);
    ctx.restore();
  }

  const activeEventLower = String(input.eventType || "").toLowerCase();

  // 5B. Set-Piece Staging & Delivery Target Zone (Corners, Free Kicks, Penalties)
  if (
    ball &&
    (activeEventLower === "corner" || activeEventLower === "free_kick" || activeEventLower === "penalty")
  ) {
    ctx.save();
    const bx = ball.x * OVERLAY_W;
    const by = ball.y * OVERLAY_H;
    const attackingRight = ball.x >= 0.5;
    const targetX = (attackingRight ? 0.89 : 0.11) * OVERLAY_W;
    const targetY = OVERLAY_H * 0.5;

    if (activeEventLower === "penalty") {
      strokePolyCircle(ctx, bx, by, 18, 12, 24);
      ctx.strokeStyle = "rgba(250, 204, 21, 0.9)";
      ctx.lineWidth = 2.0;
      ctx.setLineDash([4, 3]);
      ctx.beginPath();
      ctx.moveTo(bx, by);
      ctx.lineTo((attackingRight ? 0.985 : 0.015) * OVERLAY_W, targetY - 18);
      ctx.moveTo(bx, by);
      ctx.lineTo((attackingRight ? 0.985 : 0.015) * OVERLAY_W, targetY + 18);
      ctx.stroke();
      ctx.setLineDash([]);
      drawRoundedBannerBox(
        ctx,
        Math.min(OVERLAY_W - 140, Math.max(8, bx - 64)),
        Math.max(10, by - 36),
        128,
        16,
        "rgba(2, 6, 23, 0.88)",
        "rgba(250, 204, 21, 0.85)",
      );
      ctx.font = "bold 8.5px sans-serif";
      ctx.textAlign = "center";
      ctx.fillStyle = "#fde047";
      safeFillText(
        ctx,
        "PENALTY SPOT · 12 YDS",
        Math.min(OVERLAY_W - 76, Math.max(72, bx)),
        Math.max(21, by - 25),
      );
    } else {
      // Corner or Free Kick delivery corridor & box target zone
      ctx.fillStyle = "rgba(56, 189, 248, 0.14)";
      fillPolyCircle(ctx, targetX, targetY, 34, 48, 24);
      ctx.strokeStyle = "rgba(56, 189, 248, 0.78)";
      ctx.lineWidth = 1.8;
      ctx.setLineDash([5, 4]);
      strokePolyCircle(ctx, targetX, targetY, 34, 48, 24);

      const midX = (bx + targetX) * 0.5;
      const midY = (by + targetY) * 0.5 - 28;
      ctx.beginPath();
      ctx.moveTo(bx, by);
      ctx.quadraticCurveTo(midX, midY, targetX, targetY);
      ctx.stroke();
      ctx.setLineDash([]);

      const label = activeEventLower === "corner" ? "CORNER TARGET ZONE" : "SET-PIECE TARGET ZONE";
      drawRoundedBannerBox(
        ctx,
        Math.min(OVERLAY_W - 134, Math.max(8, targetX - 64)),
        targetY - 64,
        128,
        16,
        "rgba(2, 6, 23, 0.88)",
        "rgba(56, 189, 248, 0.8)",
      );
      ctx.font = "bold 8.5px sans-serif";
      ctx.textAlign = "center";
      ctx.fillStyle = "#7dd3fc";
      safeFillText(ctx, label, Math.min(OVERLAY_W - 70, Math.max(72, targetX)), targetY - 53);
    }
    ctx.restore();
  }

  // 5C. Off-Ball Attacking Run Chevrons & Physical 50/50 Duel Ring
  if (input.carrierPlayer) {
    const carrier = input.carrierPlayer;
    const attackDir = carrier.side === "home" ? 1 : -1;
    const runners = players
      .filter(
        (p) =>
          p.side === carrier.side &&
          p.playerId !== carrier.playerId &&
          !p.isGoalkeeper &&
          ((p.speedRatio ?? 0) >= 0.66 ||
            `${p.state || ""} ${p.animationState || ""}`.toLowerCase().includes("sprint") ||
            `${p.state || ""} ${p.animationState || ""}`.toLowerCase().includes("attack")),
      )
      .slice(0, 2);

    ctx.save();
    for (const runner of runners) {
      const tracked = input.motionTracker.get(playerIdentityKey(runner));
      const angle = tracked ? tracked.facing : attackDir > 0 ? 0 : Math.PI;
      const rx = runner.x * OVERLAY_W + Math.cos(angle) * 14;
      const ry = runner.y * OVERLAY_H - Math.sin(angle) * 14;
      const accent = runner.side === "home" ? homeColor : awayColor;
      ctx.strokeStyle = hexToRgbaString(accent, 0.85);
      ctx.lineWidth = 1.8;
      for (let step = 0; step < 2; step += 1) {
        const cx = rx + Math.cos(angle) * (step * 6);
        const cy = ry - Math.sin(angle) * (step * 6);
        ctx.beginPath();
        ctx.moveTo(cx - Math.cos(angle - 0.65) * 5, cy + Math.sin(angle - 0.65) * 5);
        ctx.lineTo(cx, cy);
        ctx.lineTo(cx - Math.cos(angle + 0.65) * 5, cy + Math.sin(angle + 0.65) * 5);
        ctx.stroke();
      }
    }
    ctx.restore();
  }

  if (
    ball &&
    (activeEventLower === "tackle" || activeEventLower === "foul" || activeEventLower === "header")
  ) {
    ctx.save();
    const bx = ball.x * OVERLAY_W;
    const by = ball.y * OVERLAY_H;
    ctx.strokeStyle =
      activeEventLower === "foul" ? "rgba(251, 191, 36, 0.9)" : "rgba(56, 189, 248, 0.88)";
    ctx.lineWidth = 2.2;
    strokePolyCircle(ctx, bx, by, 16, 11, 18);
    strokePolyCircle(ctx, bx, by, 24, 16, 18);
    ctx.restore();

    // Duel outcome pill — "WON BALL" (tackle) or "FOUL" (foul) above the primary duel player
    if (activeEventLower === "tackle" || activeEventLower === "foul") {
      const duelPlayer =
        input.carrierPlayer ||
        [...players].sort(
          (a, b) => Math.hypot(a.x - ball.x, a.y - ball.y) - Math.hypot(b.x - ball.x, b.y - ball.y),
        )[0];
      if (duelPlayer) {
        const isFoul = activeEventLower === "foul";
        const label = isFoul ? "FOUL" : "WON BALL";
        const px = duelPlayer.x * OVERLAY_W;
        const py = Math.max(30, duelPlayer.y * OVERLAY_H - 40);
        const w = isFoul ? 40 : 60;
        drawRoundedBannerBox(
          ctx,
          px - w / 2,
          py,
          w,
          14,
          isFoul ? "rgba(127, 29, 29, 0.9)" : "rgba(6, 78, 59, 0.9)",
          isFoul ? "rgba(248, 113, 113, 0.85)" : "rgba(52, 211, 153, 0.85)",
        );
        ctx.font = "bold 8.5px sans-serif";
        ctx.textAlign = "center";
        ctx.fillStyle = isFoul ? "#fecaca" : "#d1fae5";
        safeFillText(ctx, label, px, py + 10);
      }
    }
  }

  // 5D. Live Shot xG Threat Ring & Cumulative Interactive Shot Map Overlay
  if (
    ball &&
    (activeEventLower === "shot" ||
      activeEventLower === "goal" ||
      activeEventLower === "save" ||
      activeEventLower === "miss")
  ) {
    const startPt = ballTrajectory && ballTrajectory.length > 0 ? ballTrajectory[0] : ball;
    const sx = startPt.x * OVERLAY_W;
    const sy = startPt.y * OVERLAY_H;
    ctx.save();
    ctx.strokeStyle =
      activeEventLower === "goal" ? "rgba(16, 185, 129, 0.92)" : "rgba(244, 63, 94, 0.88)";
    ctx.lineWidth = 2.2;
    strokePolyCircle(ctx, sx, sy, 18, 12, 20);
    ctx.restore();

    // Shot power meter — brief bar above the shooter fading on contact
    const shooterPlayer = input.players.find(
      (p) => p.hasBall || (startPt && Math.hypot(p.x - startPt.x, p.y - startPt.y) < 0.08),
    );
    if (shooterPlayer && activeEventLower === "shot") {
      const shooterX = shooterPlayer.x * OVERLAY_W;
      const shooterY = Math.max(14, shooterPlayer.y * OVERLAY_H - 32);
      const barW = 32;
      const barH = 5;
      // Power proxy: closer to goal = higher power
      const goalX = shooterPlayer.side === "home" ? 1.0 : 0.0;
      const distToGoal = Math.abs(shooterPlayer.x - goalX);
      const powerFill = Math.max(0.18, Math.min(0.98, 1 - distToGoal * 1.4));
      ctx.save();
      ctx.fillStyle = "rgba(2, 6, 23, 0.72)";
      ctx.fillRect(shooterX - barW / 2, shooterY, barW, barH);
      const powerColor =
        powerFill > 0.72 ? "#f43f5e" : powerFill > 0.45 ? "#fb923c" : "#facc15";
      ctx.fillStyle = powerColor;
      ctx.fillRect(shooterX - barW / 2, shooterY, barW * powerFill, barH);
      ctx.strokeStyle = "rgba(255,255,255,0.4)";
      ctx.lineWidth = 0.8;
      ctx.strokeRect(shooterX - barW / 2, shooterY, barW, barH);
      ctx.restore();
    }

    // Goalkeeper dive direction arrow — from keeper toward ball trajectory intercept
    const keeperPlayer = input.players.find((p) => p.isGoalkeeper || /gk|goal/i.test(String(p.role || "")));
    if (keeperPlayer && ballTrajectory && ballTrajectory.length > 0) {
      const finalPt = ballTrajectory[ballTrajectory.length - 1];
      const kx = keeperPlayer.x * OVERLAY_W;
      const ky = keeperPlayer.y * OVERLAY_H;
      const tx = finalPt.x * OVERLAY_W;
      const ty = finalPt.y * OVERLAY_H;
      const dist = Math.hypot(tx - kx, ty - ky);
      if (dist > 4) {
        const arrowLen = Math.min(28, dist * 0.55);
        const arrowAngle = Math.atan2(ty - ky, tx - kx);
        const ex = kx + Math.cos(arrowAngle) * arrowLen;
        const ey = ky + Math.sin(arrowAngle) * arrowLen;
        ctx.save();
        ctx.strokeStyle = "rgba(56, 189, 248, 0.88)";
        ctx.lineWidth = 2.0;
        ctx.setLineDash([4, 3]);
        ctx.beginPath();
        ctx.moveTo(kx, ky);
        ctx.lineTo(ex, ey);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = "rgba(56, 189, 248, 0.88)";
        ctx.beginPath();
        ctx.moveTo(ex, ey);
        ctx.lineTo(ex - Math.cos(arrowAngle - 0.42) * 7, ey - Math.sin(arrowAngle - 0.42) * 7);
        ctx.lineTo(ex - Math.cos(arrowAngle + 0.42) * 7, ey - Math.sin(arrowAngle + 0.42) * 7);
        ctx.closePath();
        ctx.fill();
        ctx.restore();
      }
    }

    // Crossbar / post hit detection — when ball is near goal line and horizontally near post
    if (ball && isWoodworkPosition(ball.x, ball.y) && (activeEventLower === "miss" || activeEventLower === "shot")) {
      const bx2 = ball.x * OVERLAY_W;
      const by2 = ball.y * OVERLAY_H;
      ctx.save();
      ctx.strokeStyle = "rgba(203, 213, 225, 0.92)";
      ctx.lineWidth = 2.6;
      strokePolyCircle(ctx, bx2, by2, 10, 7, 8);
      strokePolyCircle(ctx, bx2, by2, 18, 12, 8);
      ctx.restore();
      // "WOODWORK!" callout
      drawRoundedBannerBox(ctx, bx2 - 36, by2 - 24, 72, 15, "rgba(2,6,23,0.88)", "rgba(203,213,225,0.7)");
      ctx.font = "bold 8.5px sans-serif";
      ctx.textAlign = "center";
      ctx.fillStyle = "#e2e8f0";
      safeFillText(ctx, "WOODWORK!", bx2, by2 - 13);
    }
  }

  if (input.showShotMap) {
    const markers = input.shotMarkers || [];
    let homeXgSum = 0;
    let awayXgSum = 0;
    ctx.save();
    for (const m of markers) {
      if (m.side === "home") homeXgSum += m.xg;
      else awayXgSum += m.xg;
      const sx = m.x * OVERLAY_W;
      const sy = m.y * OVERLAY_H;
      const gx = (m.side === "home" ? 0.99 : 0.01) * OVERLAY_W;
      const gy = OVERLAY_H * 0.5;
      const radius = Math.max(5.5, Math.min(14, 4.5 + m.xg * 14));
      const color =
        m.outcome === "goal"
          ? "#10b981"
          : m.outcome === "saved"
            ? "#38bdf8"
            : "#f43f5e";

      ctx.strokeStyle = hexToRgbaString(color, 0.55);
      ctx.lineWidth = m.outcome === "goal" ? 2.2 : 1.3;
      ctx.setLineDash(m.outcome === "goal" ? [] : [4, 4]);
      ctx.beginPath();
      ctx.moveTo(sx, sy);
      ctx.lineTo(gx, gy);
      ctx.stroke();

      ctx.setLineDash([]);
      ctx.fillStyle = hexToRgbaString(color, 0.82);
      fillPolyCircle(ctx, sx, sy, radius, radius, 18);
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 1.4;
      strokePolyCircle(ctx, sx, sy, radius, radius, 18);
    }

    drawRoundedBannerBox(
      ctx,
      OVERLAY_W / 2 - 164,
      OVERLAY_H - 28,
      328,
      20,
      "rgba(2, 6, 23, 0.88)",
      "rgba(251, 191, 36, 0.65)",
    );
    ctx.font = "bold 9.5px sans-serif";
    ctx.textAlign = "center";
    ctx.fillStyle = "#fde68a";
    safeFillText(
      ctx,
      `ON-PITCH SHOT MAP · HOME ${homeXgSum.toFixed(2)} xG (${markers.filter((m) => m.side === "home").length}) — AWAY ${awayXgSum.toFixed(2)} xG (${markers.filter((m) => m.side === "away").length})`,
      OVERLAY_W / 2,
      OVERLAY_H - 15,
    );
    ctx.restore();
  }

  // 6. Broadcast On-Pitch Player Callout Pills (Ball Carrier & Selected Player only — never cluttered)
  const callouts: { player: PitchPlayer; accent: string; isSelected: boolean }[] = [];
  if (input.carrierPlayer) {
    callouts.push({
      player: input.carrierPlayer,
      accent: input.carrierPlayer.side === "home" ? homeColor : awayColor,
      isSelected: false,
    });
  }
  if (
    input.selectedPlayer &&
    (!input.carrierPlayer ||
      playerIdentityKey(input.selectedPlayer) !== playerIdentityKey(input.carrierPlayer))
  ) {
    callouts.push({
      player: input.selectedPlayer,
      accent: "#38bdf8",
      isSelected: true,
    });
  }

  const placedCallouts: { x: number; y: number; w: number; h: number }[] = [];
  for (const { player, accent } of callouts) {
    const label = `${player.shirtNumber ? `#${player.shirtNumber} ` : ""}${shortPlayerName(player.name)}`;
    if (!label.trim()) continue;
    const px = player.x * OVERLAY_W;
    const py = Math.max(24, player.y * OVERLAY_H - 24);
    const boxW = Math.max(58, Math.min(126, label.length * 6.4 + 14));
    const boxX = Math.min(OVERLAY_W - boxW - 6, Math.max(6, px - boxW / 2));
    let boxY = py - 15;
    for (const prev of placedCallouts) {
      const overlapsX = boxX < prev.x + prev.w + 4 && boxX + boxW + 4 > prev.x;
      const overlapsY = Math.abs(boxY - prev.y) < 19;
      if (overlapsX && overlapsY) {
        boxY = prev.y > 32 ? prev.y - 20 : prev.y + 20;
      }
    }
    placedCallouts.push({ x: boxX, y: boxY, w: boxW, h: 16 });

    ctx.save();
    drawRoundedBannerBox(ctx, boxX, boxY, boxW, 16, "rgba(2, 6, 23, 0.86)", hexToRgbaString(accent, 0.85));
    ctx.fillStyle = accent;
    ctx.fillRect(boxX, boxY, 3.5, 16);
    ctx.font = "bold 9.5px sans-serif";
    ctx.textAlign = "center";
    ctx.fillStyle = "#f8fafc";
    safeFillText(ctx, label, boxX + boxW / 2 + 1.5, boxY + 11.5);
    ctx.restore();
  }
}

function paintCanvasFallback(
  ctx: CanvasRenderingContext2D,
  canvas: HTMLCanvasElement,
  state: {
    players: PitchPlayer[];
    eventType?: string | null;
    homeColor: string;
    awayColor: string;
    goalkeeperHome: string;
    goalkeeperAway: string;
    selectedKey: string | null;
    ballPoint: { x: number; y: number } | null;
    resolvedBall?: ReturnType<typeof resolveBallPresentation>;
    camera: { zoom: number; panX: number; panY: number };
    overlayCanvas: HTMLCanvasElement | null;
    motionTracker: PlayerMotionTracker;
  },
) {
  const width = canvas.width;
  const height = canvas.height;
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#0c2418";
  ctx.fillRect(0, 0, width, height);

  const zoom = Math.max(0.8, state.camera.zoom || 1);
  const offsetX = -(state.camera.panX / PITCH_W) * width * zoom;
  const offsetY = (state.camera.panY / PITCH_H) * height * zoom;

  ctx.save();
  ctx.translate(width / 2 + offsetX, height / 2 + offsetY);
  ctx.scale(zoom, zoom);
  ctx.translate(-width / 2, -height / 2);

  const pitchBitmap = getCachedPitchBitmap(PITCH_TEX_W, PITCH_TEX_H);
  if (pitchBitmap) {
    ctx.drawImage(pitchBitmap, 0, 0, width, height);
  } else {
    ctx.fillStyle = "#1f7a45";
    ctx.fillRect(0, 0, width, height);
  }

  if (state.overlayCanvas) {
    ctx.drawImage(state.overlayCanvas, 0, 0, width, height);
  }

  const ringBitmap = getCachedRingBitmap();
  state.players.forEach((player) => {
    const key = playerIdentityKey(player);
    const tracked = state.motionTracker.get(key);
    const keeper = Boolean(player.isGoalkeeper) || String(player.role || "").toLowerCase().includes("gk");
    const kitColor = keeper
      ? player.side === "home"
        ? state.goalkeeperHome
        : state.goalkeeperAway
      : player.side === "home"
        ? state.homeColor
        : state.awayColor;

    const px = player.x * width;
    const py = player.y * height;

    if (state.selectedKey === key && ringBitmap) {
      ctx.drawImage(ringBitmap, px - 18, py - 10, 36, 20);
    }

    paintRig(ctx, px, py, 42, {
      action: (tracked?.action || animationFor(player, state.eventType)) as RigAction,
      frame: tracked?.frame ?? 0,
      direction: tracked?.direction ?? 0,
      kitColor,
      shirtNumber: player.shirtNumber,
    });
  });

  if (state.ballPoint) {
    const ballBitmap = getCachedBallBitmap();
    if (ballBitmap) {
      const elev = state.resolvedBall?.heightMeters ?? 0;
      const bx = state.ballPoint.x * width;
      const by = state.ballPoint.y * height;
      if (elev > 0.14) {
        ctx.fillStyle = "rgba(3, 7, 18, 0.42)";
        fillPolyCircle(ctx, bx, by + 3, 7, 3.2, 16);
      }
      ctx.drawImage(ballBitmap, bx - 9, by - 9 - elev * 4.5, 18, 18);
    }
  }

  ctx.restore();
}
