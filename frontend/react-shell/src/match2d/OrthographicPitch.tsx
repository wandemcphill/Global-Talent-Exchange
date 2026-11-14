import React, { memo, useEffect, useRef, useState } from "react";
import * as THREE from "three";

import * as matchRenderer from "./createMatchRenderer";
import {
  animationFor,
  effectFor,
  playerIdentityKey,
  sceneObjectCount,
  type FeedPresentationStatus,
  type PitchPlayer,
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
  ball: { x: number; y: number } | null;
  ballTrajectory?: { x: number; y: number }[] | null;
  trajectoryAlpha?: number;
  eventType?: string | null;
};

export type OrthographicPitchProps = {
  players: PitchPlayer[];
  ball: { x: number; y: number } | null;
  ballTrajectory?: { x: number; y: number }[] | null;
  trajectoryAlpha?: number;
  eventType?: string | null;
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
  feedStatus?: FeedPresentationStatus;
  feedAgeSeconds?: number | null;
  sampleFrame?: ((nowMs: number) => SampledPitchFrame | null) | null;
};

export const PITCH_W = 105;
export const PITCH_H = 68;
const POOL_SIZE = 26;
const OVERLAY_W = 512;
const OVERLAY_H = 320;
const GRID_W = 64;
const GRID_H = 40;

const VERTEX = `
  uniform vec2 uOffset;
  uniform vec2 uRepeat;
  varying vec2 vUv;
  void main() {
    vUv = uOffset + uv * uRepeat;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const FRAGMENT = `
  precision mediump float;
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

function OrthographicPitchComponent({
  players,
  ball,
  ballTrajectory = null,
  trajectoryAlpha = 1,
  eventType,
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
  feedStatus = "LIVE",
  feedAgeSeconds = null,
  sampleFrame = null,
}: OrthographicPitchProps) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const propsRef = useRef({
    players,
    ball,
    ballTrajectory,
    trajectoryAlpha,
    eventType,
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
    feedStatus,
    sampleFrame,
  });
  const cameraRef = useRef({ zoom: 1, panX: 0, panY: 0, follow: false });
  const [follow, setFollow] = useState(false);
  const [zoomLevel, setZoomLevel] = useState(1);

  propsRef.current = {
    players,
    ball,
    ballTrajectory,
    trajectoryAlpha,
    eventType,
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
    feedStatus,
    sampleFrame,
  };
  cameraRef.current.follow = follow;

  // Apply cameraMode preset changes cleanly while allowing manual zoom/pan adjustments
  useEffect(() => {
    if (cameraMode === "2d") {
      cameraRef.current = { zoom: 1, panX: 0, panY: 0, follow: cameraRef.current.follow };
      setZoomLevel(1);
    } else if (cameraMode === "2.5d") {
      cameraRef.current = { zoom: 1.12, panX: cameraRef.current.panX * 0.5, panY: -2.2, follow: cameraRef.current.follow };
      setZoomLevel(1.12);
    } else if (cameraMode === "zoom") {
      cameraRef.current = { zoom: 1.42, panX: cameraRef.current.panX, panY: cameraRef.current.panY, follow: true };
      setZoomLevel(1.42);
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

    const pitchPixels = rasterPitch(OVERLAY_W, OVERLAY_H);
    const pitchTexture = dataTexture(pitchPixels, OVERLAY_W, OVERLAY_H);
    const pitchGeometry = new THREE.PlaneGeometry(PITCH_W, PITCH_H);
    const pitchMaterial = new THREE.MeshBasicMaterial({ map: pitchTexture, side: THREE.DoubleSide });
    const pitch = new THREE.Mesh(pitchGeometry, pitchMaterial);
    scene.add(pitch);

    // Dynamic tactical & spatial overlay layer (Voronoi, Heatmap, Tactics, Passing Lanes)
    const overlayCanvas = document.createElement("canvas");
    overlayCanvas.width = OVERLAY_W;
    overlayCanvas.height = OVERLAY_H;
    let overlayCtx: CanvasRenderingContext2D | null = null;
    try {
      overlayCtx = overlayCanvas.getContext("2d");
    } catch {
      overlayCtx = null;
    }
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
    overlayMesh.position.set(0, 0, 0.25);
    overlayMesh.visible = false;
    scene.add(overlayMesh);

    const atlas = buildAtlasPixels();
    const bodyTexture = dataTexture(atlas.body, atlas.width, atlas.height);
    const kitTexture = dataTexture(atlas.kit, atlas.width, atlas.height);
    const digits = buildDigitPixels();
    const digitTexture = dataTexture(digits.data, digits.width, digits.height);
    digitTexture.magFilter = THREE.NearestFilter;
    digitTexture.minFilter = THREE.NearestFilter;

    const ballTexture = dataTexture(rasterBall(), 48, 48);
    const ballGeometry = new THREE.PlaneGeometry(2.4, 2.4);
    const ballMaterial = new THREE.MeshBasicMaterial({
      map: ballTexture,
      transparent: true,
      depthWrite: false,
      side: THREE.DoubleSide,
    });
    const ballMesh = new THREE.Mesh(ballGeometry, ballMaterial);
    scene.add(ballMesh);

    const ringTexture = dataTexture(rasterRing(), 64, 64);
    const ringGeometry = new THREE.PlaneGeometry(3.4, 3.4);
    const ringMaterial = new THREE.MeshBasicMaterial({
      map: ringTexture,
      transparent: true,
      depthWrite: false,
      side: THREE.DoubleSide,
    });
    const ring = new THREE.Mesh(ringGeometry, ringMaterial);
    ring.visible = false;
    scene.add(ring);

    const carrierRingGeometry = new THREE.PlaneGeometry(2.9, 2.9);
    const carrierRingMaterial = new THREE.MeshBasicMaterial({
      map: ringTexture,
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.72,
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
    const sharedGeometry = new THREE.PlaneGeometry(4.8, 4.8);
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
    let lastOverlayPaintMs = -1000;
    let lastOverlaySignature = "";
    let previousBall: { x: number; y: number } | null = null;

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
      if (renderer?.domElement) {
        renderer.domElement.style.display = "none";
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
      } else {
        fallbackCanvas.style.display = "block";
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
      const activeTrajectory = liveSampled ? liveSampled.ballTrajectory ?? current.ballTrajectory : current.ballTrajectory;
      const activeAlpha = liveSampled?.trajectoryAlpha ?? current.trajectoryAlpha;
      const activeEvent = liveSampled?.eventType ?? current.eventType;

      // Accumulate real player coordinates into the spatial heatmap grid
      if (activePlayers.length > 0) {
        for (let i = 0; i < GRID_W * GRID_H; i += 1) {
          heatmapBins[i] *= 0.996;
        }
        for (const p of activePlayers) {
          const gx = Math.min(GRID_W - 1, Math.max(0, Math.floor(p.x * GRID_W)));
          const gy = Math.min(GRID_H - 1, Math.max(0, Math.floor(p.y * GRID_H)));
          heatmapBins[gy * GRID_W + gx] = Math.min(12, heatmapBins[gy * GRID_W + gx] + 0.18);
        }
      }

      const ballPoint =
        activeTrajectory && activeTrajectory.length > 0
          ? sampleTrajectory(activeTrajectory, activeAlpha)
          : activeBall;

      if ((view.follow || current.cameraMode === "zoom" || current.cameraMode === "2.5d") && ballPoint) {
        const focus = toWorld(ballPoint.x, ballPoint.y);
        const trackStrengthX = current.cameraMode === "zoom" ? 0.42 : view.follow ? 0.28 : 0.16;
        const trackStrengthY = current.cameraMode === "zoom" ? 0.32 : view.follow ? 0.25 : 0.08;
        const nextPanX = camera.position.x + (focus.x * trackStrengthX - camera.position.x) * 0.08;
        const nextPanY = camera.position.y + (focus.y * trackStrengthY - camera.position.y) * 0.08;
        const clamped = clampCameraPan(nextPanX, nextPanY, view.zoom);
        view.panX = clamped.panX;
        view.panY = clamped.panY;
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
      let carrierPlayerObj: PitchPlayer | null = null;

      activePlayers.forEach((player) => {
        const key = playerIdentityKey(player);
        seenKeys.add(key);

        const tracked = motionTracker.update(key, player.x, player.y, frameStart, {
          baseAction: animationFor(player, activeEvent),
          hasBall: Boolean(player.hasBall),
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
        }
        if (player.hasBall && !carrierPlayerObj) {
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

      // Update tactical & spatial overlays when active
      const anyOverlayActive = Boolean(
        (current.showVoronoi || current.showHeatmap || current.showTactics || current.showPassingLanes) &&
          activePlayers.length > 0,
      );
      overlayMesh.visible = anyOverlayActive;
      if (anyOverlayActive && overlayCtx) {
        const sig = `${current.showVoronoi ? 1 : 0}:${current.showHeatmap ? 1 : 0}:${current.showTactics ? 1 : 0}:${current.showPassingLanes ? 1 : 0}:${current.selectedKey || ""}`;
        if (sig !== lastOverlaySignature || frameStart - lastOverlayPaintMs >= 65) {
          lastOverlaySignature = sig;
          lastOverlayPaintMs = frameStart;
          paintTacticalOverlays(overlayCtx, {
            players: activePlayers,
            ball: ballPoint,
            ballTrajectory: activeTrajectory,
            selectedKey: current.selectedKey || null,
            homeColor: current.homeColor,
            awayColor: current.awayColor,
            showVoronoi: Boolean(current.showVoronoi),
            showHeatmap: Boolean(current.showHeatmap),
            showTactics: Boolean(current.showTactics),
            showPassingLanes: Boolean(current.showPassingLanes),
            heatmapBins,
            motionTracker,
          });
          overlayTexture.needsUpdate = true;
        }
      }

      const cue = effectFor(activeEvent);
      if (ballPoint) {
        const point = toWorld(ballPoint.x, ballPoint.y);
        ballMesh.position.set(point.x, point.y, 2);
        ballMesh.visible = true;
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
        effect.visible = false;
      }

      if (cue === "save" || cue === "card" || cue === "substitution") {
        const focus =
          selectedPlayerObj ||
          carrierPlayerObj ||
          activePlayers[0];
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
      data-feed-status={feedStatus}
    >
      <div
        ref={hostRef}
        className="relative aspect-[16/10] w-full overflow-hidden rounded-xl border border-emerald-500/40 bg-[#0c2418] shadow-[0_18px_48px_rgba(0,0,0,0.65)] select-none"
      />
      <div className="flex flex-wrap items-center justify-between gap-2 text-[10px] font-black uppercase tracking-wider">
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            type="button"
            data-testid="pitch-control-fit"
            className="rounded border border-white/15 bg-slate-900/80 px-2.5 py-1 text-slate-200 transition hover:border-emerald-400/50 hover:text-white"
            onClick={() => {
              cameraRef.current = { zoom: 1, panX: 0, panY: 0, follow: false };
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

function paintTacticalOverlays(
  ctx: CanvasRenderingContext2D,
  input: {
    players: PitchPlayer[];
    ball: { x: number; y: number } | null;
    ballTrajectory?: { x: number; y: number }[] | null;
    selectedKey: string | null;
    homeColor: string;
    awayColor: string;
    showVoronoi: boolean;
    showHeatmap: boolean;
    showTactics: boolean;
    showPassingLanes: boolean;
    heatmapBins: Float32Array;
    motionTracker: PlayerMotionTracker;
  },
) {
  ctx.clearRect(0, 0, OVERLAY_W, OVERLAY_H);
  const { players, ball, ballTrajectory, selectedKey, homeColor, awayColor } = input;
  if (!players.length) return;

  const cellW = OVERLAY_W / GRID_W;
  const cellH = OVERLAY_H / GRID_H;

  // 1. Voronoi Space Control Overlay (computed from real player positions)
  if (input.showVoronoi) {
    const homeFill = hexToRgbaString(homeColor, 0.16);
    const awayFill = hexToRgbaString(awayColor, 0.16);
    const owners = new Uint8Array(GRID_W * GRID_H);

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
        owners[gy * GRID_W + gx] = isHome ? 1 : 2;
        ctx.fillStyle = isHome ? homeFill : awayFill;
        ctx.fillRect(gx * cellW, gy * cellH, cellW + 0.5, cellH + 0.5);
      }
    }

    // Boundary contour between home and away territory
    ctx.fillStyle = "rgba(248, 250, 252, 0.35)";
    for (let gy = 0; gy < GRID_H - 1; gy += 1) {
      for (let gx = 0; gx < GRID_W - 1; gx += 1) {
        const currentOwner = owners[gy * GRID_W + gx];
        if (currentOwner !== owners[gy * GRID_W + gx + 1] || currentOwner !== owners[(gy + 1) * GRID_W + gx]) {
          ctx.fillRect(gx * cellW, gy * cellH, 2, 2);
        }
      }
    }
  }

  // 2. Heatmap Overlay (from accumulated real player position samples)
  if (input.showHeatmap) {
    for (let gy = 0; gy < GRID_H; gy += 1) {
      for (let gx = 0; gx < GRID_W; gx += 1) {
        const density = input.heatmapBins[gy * GRID_W + gx];
        if (density <= 0.08) continue;
        const intensity = Math.min(1, density / 4);
        const cx = (gx + 0.5) * cellW;
        const cy = (gy + 0.5) * cellH;
        const radius = cellW * (1.8 + intensity * 1.4);
        const grad = ctx.createRadialGradient(cx, cy, 1, cx, cy, radius);
        grad.addColorStop(0, `rgba(244, 63, 94, ${(0.36 * intensity).toFixed(3)})`);
        grad.addColorStop(0.55, `rgba(251, 191, 36, ${(0.18 * intensity).toFixed(3)})`);
        grad.addColorStop(1, "rgba(251, 191, 36, 0)");
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(cx, cy, radius, 0, Math.PI * 2);
        ctx.fill();
      }
    }
  }

  // 3. Tactical Overlay: Defensive Line, Compactness Block, Formation Links, and Velocity Vectors
  if (input.showTactics) {
    (["home", "away"] as const).forEach((side) => {
      const color = side === "home" ? homeColor : awayColor;
      const sidePlayers = players.filter(
        (p) => p.side === side && !p.isGoalkeeper && !/gk|goal/i.test(String(p.role || "")),
      );
      if (sidePlayers.length === 0) return;

      // Sort along X to identify defensive unit & compactness bounds
      const sortedX = [...sidePlayers].sort((a, b) => (side === "home" ? a.x - b.x : b.x - a.x));
      const defenders = sortedX.slice(0, Math.min(4, sortedX.length));
      const defLineX =
        (defenders.reduce((sum, p) => sum + p.x, 0) / Math.max(1, defenders.length)) * OVERLAY_W;

      // Defensive Line
      ctx.save();
      ctx.strokeStyle = hexToRgbaString(color, 0.78);
      ctx.lineWidth = 2;
      ctx.setLineDash([6, 4]);
      ctx.beginPath();
      ctx.moveTo(defLineX, 20);
      ctx.lineTo(defLineX, OVERLAY_H - 20);
      ctx.stroke();

      // Team Compactness & Pressing Shape Envelope
      const minX = Math.min(...sidePlayers.map((p) => p.x)) * OVERLAY_W;
      const maxX = Math.max(...sidePlayers.map((p) => p.x)) * OVERLAY_W;
      const minY = Math.min(...sidePlayers.map((p) => p.y)) * OVERLAY_H;
      const maxY = Math.max(...sidePlayers.map((p) => p.y)) * OVERLAY_H;
      ctx.fillStyle = hexToRgbaString(color, 0.07);
      ctx.strokeStyle = hexToRgbaString(color, 0.36);
      ctx.lineWidth = 1.2;
      ctx.setLineDash([4, 4]);
      ctx.strokeRect(minX, minY, Math.max(8, maxX - minX), Math.max(8, maxY - minY));
      ctx.fillRect(minX, minY, Math.max(8, maxX - minX), Math.max(8, maxY - minY));

      // Formation unit links between defenders and midfielders
      ctx.setLineDash([]);
      ctx.strokeStyle = hexToRgbaString(color, 0.42);
      ctx.lineWidth = 1.2;
      const defSortedByY = [...defenders].sort((a, b) => a.y - b.y);
      for (let i = 0; i < defSortedByY.length - 1; i += 1) {
        ctx.beginPath();
        ctx.moveTo(defSortedByY[i].x * OVERLAY_W, defSortedByY[i].y * OVERLAY_H);
        ctx.lineTo(defSortedByY[i + 1].x * OVERLAY_W, defSortedByY[i + 1].y * OVERLAY_H);
        ctx.stroke();
      }
      ctx.restore();
    });

    // Player movement velocity indicators
    for (const p of players) {
      const tracked = input.motionTracker.get(playerIdentityKey(p));
      if (!tracked || tracked.speed < 0.003) continue;
      const startX = p.x * OVERLAY_W;
      const startY = p.y * OVERLAY_H;
      const endX = startX + Math.cos(tracked.facing) * Math.min(28, tracked.speed * 520);
      const endY = startY - Math.sin(tracked.facing) * Math.min(28, tracked.speed * 520);
      ctx.save();
      ctx.strokeStyle = p.side === "home" ? homeColor : awayColor;
      ctx.lineWidth = 1.8;
      ctx.beginPath();
      ctx.moveTo(startX, startY);
      ctx.lineTo(endX, endY);
      ctx.stroke();
      ctx.restore();
    }
  }

  // 4. Passing Lanes & Supplied Ball Trajectory Overlay
  if (input.showPassingLanes) {
    const selectedPlayer = selectedKey
      ? players.find((p) => playerIdentityKey(p) === selectedKey) || null
      : null;
    const carrier =
      selectedPlayer ||
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

      const viableTargets = teammates
        .map((mate) => {
          const dist = Math.hypot(mate.x - carrier.x, mate.y - carrier.y);
          const blocked = opponents.some(
            (opp) =>
              pointToSegmentDistance(opp.x, opp.y, carrier.x, carrier.y, mate.x, mate.y) < 0.042,
          );
          return { mate, dist, blocked };
        })
        .filter((item) => item.dist >= 0.05 && item.dist <= 0.48 && !item.blocked)
        .sort((a, b) => a.dist - b.dist)
        .slice(0, 4);

      ctx.save();
      ctx.strokeStyle = hexToRgbaString(laneColor, 0.72);
      ctx.lineWidth = 1.8;
      ctx.setLineDash([5, 4]);
      for (const { mate } of viableTargets) {
        ctx.beginPath();
        ctx.moveTo(carrier.x * OVERLAY_W, carrier.y * OVERLAY_H);
        ctx.lineTo(mate.x * OVERLAY_W, mate.y * OVERLAY_H);
        ctx.stroke();

        ctx.beginPath();
        ctx.arc(mate.x * OVERLAY_W, mate.y * OVERLAY_H, 5, 0, Math.PI * 2);
        ctx.stroke();
      }
      ctx.restore();
    }

    if (ballTrajectory && ballTrajectory.length > 1) {
      ctx.save();
      ctx.strokeStyle = "rgba(103, 232, 249, 0.85)";
      ctx.lineWidth = 2.2;
      ctx.setLineDash([4, 3]);
      ctx.beginPath();
      ctx.moveTo(ballTrajectory[0].x * OVERLAY_W, ballTrajectory[0].y * OVERLAY_H);
      for (let i = 1; i < ballTrajectory.length; i += 1) {
        ctx.lineTo(ballTrajectory[i].x * OVERLAY_W, ballTrajectory[i].y * OVERLAY_H);
      }
      ctx.stroke();
      ctx.restore();
    }
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

  const pitchBitmap = getCachedPitchBitmap(OVERLAY_W, OVERLAY_H);
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
      ctx.drawImage(ballBitmap, state.ballPoint.x * width - 9, state.ballPoint.y * height - 9, 18, 18);
    }
  }

  ctx.restore();
}
