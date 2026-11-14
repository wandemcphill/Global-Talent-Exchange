import React, { memo, useEffect, useRef, useState } from "react";
import * as THREE from "three";

import * as matchRenderer from "./createMatchRenderer";
import { animationFor, effectFor, sceneObjectCount, type PitchPlayer } from "./matchStateAdapter";
import {
  ATLAS_COLUMNS,
  ATLAS_ROWS,
  CELL,
  buildAtlasPixels,
  buildDigitPixels,
  cellUv,
  paintRig,
  presentationAction,
  rasterBall,
  rasterPitch,
  rasterRing,
  sampleTrajectory,
  type RigAction,
} from "./playerRig";

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
};

const PITCH_W = 105;
const PITCH_H = 68;
const POOL_SIZE = 26;

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
    vec3 color = mix(body.rgb, uKitColor, kit.a);
    float alpha = max(body.a, kit.a);
    vec2 localUv = (vUv - uOffset) / uRepeat;
    float digitAlpha = 0.0;
    if (localUv.y > 0.42 && localUv.y < 0.62 && localUv.x > 0.36 && localUv.x < 0.64) {
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
    }
    color = mix(color, vec3(0.97), digitAlpha);
    float visible = max(alpha, digitAlpha);
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
  logged: false,
};

function dataTexture(data: Uint8Array, width: number, height: number) {
  const texture = new THREE.DataTexture(data, width, height, THREE.RGBAFormat);
  texture.flipY = true;
  texture.needsUpdate = true;
  texture.magFilter = THREE.LinearFilter;
  texture.minFilter = THREE.LinearFilter;
  texture.generateMipmaps = false;
  return texture;
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
  });
  const cameraRef = useRef({ zoom: 1, panX: 0, panY: 0, follow: false });
  const [follow, setFollow] = useState(false);
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
  };
  cameraRef.current.follow = follow;

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
    const scene = new THREE.Scene();
    const camera = new THREE.OrthographicCamera(-PITCH_W / 2, PITCH_W / 2, PITCH_H / 2, -PITCH_H / 2, 0.1, 50);
    camera.position.set(0, 0, 10);
    const pitchPixels = rasterPitch();
    const pitchTexture = dataTexture(pitchPixels, 512, 320);
    const pitch = new THREE.Mesh(
      new THREE.PlaneGeometry(PITCH_W, PITCH_H),
      new THREE.MeshBasicMaterial({ map: pitchTexture, side: THREE.DoubleSide }),
    );
    scene.add(pitch);
    const atlas = buildAtlasPixels();
    const bodyTexture = dataTexture(atlas.body, atlas.width, atlas.height);
    const kitTexture = dataTexture(atlas.kit, atlas.width, atlas.height);
    const digits = buildDigitPixels();
    const digitTexture = dataTexture(digits.data, digits.width, digits.height);
    digitTexture.magFilter = THREE.NearestFilter;
    digitTexture.minFilter = THREE.NearestFilter;
    const ballTexture = dataTexture(rasterBall(), 48, 48);
    const ballMesh = new THREE.Mesh(
      new THREE.PlaneGeometry(2.4, 2.4),
      new THREE.MeshBasicMaterial({ map: ballTexture, transparent: true, depthWrite: false, side: THREE.DoubleSide }),
    );
    scene.add(ballMesh);
    const ringTexture = dataTexture(rasterRing(), 64, 64);
    const ring = new THREE.Mesh(
      new THREE.PlaneGeometry(3.2, 3.2),
      new THREE.MeshBasicMaterial({ map: ringTexture, transparent: true, depthWrite: false, side: THREE.DoubleSide }),
    );
    ring.visible = false;
    scene.add(ring);
    const effect = new THREE.Mesh(
      new THREE.PlaneGeometry(1, 0.28),
      new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.9, depthWrite: false, side: THREE.DoubleSide }),
    );
    effect.visible = false;
    scene.add(effect);
    const cueMesh = new THREE.Mesh(
      new THREE.PlaneGeometry(2.2, 2.2),
      new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.55, depthWrite: false, side: THREE.DoubleSide }),
    );
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
    const motion = new Map<string, { x: number; y: number; facing: number; speed: number }>();
    let previousBall: { x: number; y: number } | null = null;

    const ensureFallback = () => {
      if (fallbackCanvas) return;
      fallbackCanvas = document.createElement("canvas");
      try {
        fallback = fallbackCanvas.getContext("2d");
      } catch {
        fallback = null;
      }
      host.appendChild(fallbackCanvas);
      resize();
    };

    const resize = () => {
      const width = Math.max(host.clientWidth, 320);
      const height = Math.max(Math.round(width * 0.62), 200);
      if (renderer && !contextLost) renderer.setSize(width, height, false);
      if (fallbackCanvas) {
        fallbackCanvas.width = width;
        fallbackCanvas.height = height;
      }
    };

    try {
      renderer = matchRenderer.createMatchRenderer();
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      host.appendChild(renderer.domElement);
      renderer.domElement.addEventListener("webglcontextlost", (event) => {
        event.preventDefault();
        contextLost = true;
        ensureFallback();
      });
      renderer.domElement.addEventListener("webglcontextrestored", () => {
        contextLost = false;
        pitchTexture.needsUpdate = true;
        bodyTexture.needsUpdate = true;
        kitTexture.needsUpdate = true;
        digitTexture.needsUpdate = true;
        ballTexture.needsUpdate = true;
        ringTexture.needsUpdate = true;
        resize();
      });
      renderer.domElement.style.width = "100%";
      renderer.domElement.style.height = "100%";
      renderer.domElement.style.touchAction = "none";
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

    const acquire = (playerId: string) => {
      let mesh = assigned.get(playerId);
      if (mesh) return mesh;
      mesh = free.pop();
      if (!mesh) return null;
      mesh.visible = true;
      assigned.set(playerId, mesh);
      return mesh;
    };

    const paint = () => {
      if (stopped) return;
      frameId = window.requestAnimationFrame(paint);
      const frameStart = performance.now();
      const view = cameraRef.current;
      const current = propsRef.current;
      camera.zoom = view.zoom;
      camera.position.x = view.panX;
      camera.position.y = view.panY;
      const ballPoint =
        current.ballTrajectory && current.ballTrajectory.length > 0
          ? sampleTrajectory(current.ballTrajectory, current.trajectoryAlpha)
          : current.ball;
      if (view.follow && ballPoint) {
        const focus = toWorld(ballPoint.x, ballPoint.y);
        camera.position.x += (focus.x * 0.25 - camera.position.x) * 0.08;
        camera.position.y += (focus.y * 0.25 - camera.position.y) * 0.08;
        view.panX = camera.position.x;
        view.panY = camera.position.y;
      }
      camera.updateProjectionMatrix();
      const seen = new Set<string>();
      const frame = Math.floor(performance.now() / 120) % 4;
      current.players.forEach((player) => {
        seen.add(player.playerId);
        const previous = motion.get(player.playerId);
        const dx = previous ? player.x - previous.x : 0;
        const dy = previous ? previous.y - player.y : 0;
        const speed = Math.min(0.08, Math.hypot(player.x - (previous?.x ?? player.x), player.y - (previous?.y ?? player.y)));
        const facing = speed > 0.002 ? Math.atan2(dy, dx) : previous?.facing ?? 0;
        const direction = ((Math.round((facing / (Math.PI * 2)) * 8) % 8) + 8) % 8;
        let facingDelta = previous ? facing - previous.facing : 0;
        if (facingDelta > Math.PI) facingDelta -= Math.PI * 2;
        if (facingDelta < -Math.PI) facingDelta += Math.PI * 2;
        const action = presentationAction(animationFor(player, current.eventType), {
          facingDelta,
          speed,
          previousSpeed: previous?.speed ?? speed,
          hasBall: Boolean(player.hasBall),
        });
        motion.set(player.playerId, { x: player.x, y: player.y, facing, speed });
        const keeper = Boolean(player.isGoalkeeper) || String(player.role || "").toLowerCase().includes("gk");
        const kitColor = keeper
          ? player.side === "home"
            ? current.goalkeeperHome
            : current.goalkeeperAway
          : player.side === "home"
            ? current.homeColor
            : current.awayColor;
        const point = toWorld(player.x, player.y);
        const mesh = acquire(player.playerId);
        if (mesh) {
          mesh.position.set(point.x, point.y, 1);
          const material = mesh.material as THREE.ShaderMaterial;
          const uv = cellUv(action, direction, frame);
          material.uniforms.uOffset.value.set(uv.offsetX, uv.offsetY);
          material.uniforms.uKitColor.value.set(kitColor);
          material.uniforms.uShirt.value = player.shirtNumber;
        }
        if (current.selectedKey === `${player.side}:${player.playerId}`) {
          ring.visible = true;
          ring.position.set(point.x, point.y - 1.2, 0.4);
        }
      });
      if (!current.players.some((player) => current.selectedKey === `${player.side}:${player.playerId}`)) ring.visible = false;
      assigned.forEach((mesh, id) => {
        if (!seen.has(id)) {
          mesh.visible = false;
          assigned.delete(id);
          free.push(mesh);
          motion.delete(id);
        }
      });
      const cue = effectFor(current.eventType);
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
          const material = effect.material as THREE.MeshBasicMaterial;
          material.color.set(cue === "goal" ? "#ffffff" : cue === "shot" ? "#f43f5e" : "#67e8f9");
          material.opacity = cue === "goal" ? 0.45 + Math.abs(Math.sin(performance.now() / 120)) * 0.4 : 0.85;
        }
        previousBall = ballPoint;
      } else {
        ballMesh.visible = false;
        effect.visible = false;
      }
      if (cue === "save" || cue === "card" || cue === "substitution") {
        const focus =
          current.players.find((player) => current.selectedKey === `${player.side}:${player.playerId}`) ||
          current.players.find((player) => player.hasBall) ||
          current.players[0];
        if (focus) {
          const point = toWorld(focus.x, focus.y);
          cueMesh.visible = true;
          cueMesh.position.set(point.x, point.y + 2.2, 1.5);
          const material = cueMesh.material as THREE.MeshBasicMaterial;
          material.color.set(cue === "save" ? "#38bdf8" : cue === "card" ? "#facc15" : "#a78bfa");
          material.opacity = 0.35 + Math.abs(Math.sin(performance.now() / 180)) * 0.35;
        } else {
          cueMesh.visible = false;
        }
      } else {
        cueMesh.visible = false;
      }

      const objectCount = sceneObjectCount(current.players.length, Boolean(cue));
      lastRenderProfile.objectCount = objectCount;
      fpsFrames += 1;
      const elapsed = performance.now() - fpsStarted;
      if (elapsed >= 1000) {
        lastRenderProfile.fps = Math.round((fpsFrames * 1000) / elapsed);
        lastRenderProfile.frameMs = elapsed / Math.max(1, fpsFrames);
        fpsFrames = 0;
        fpsStarted = performance.now();
        if (process.env.NODE_ENV !== "production" && !lastRenderProfile.logged) {
          lastRenderProfile.logged = true;
          // eslint-disable-next-line no-console
          console.info("[match2d]", lastRenderProfile);
        }
      }
      lastRenderProfile.frameMs = Math.max(lastRenderProfile.frameMs, performance.now() - frameStart);

      if (renderer && !contextLost) {
        renderer.render(scene, camera);
        lastRenderProfile.calls = renderer.info.render.calls;
        lastRenderProfile.sampledFrames += 1;
      } else if (fallback && fallbackCanvas) {
        paintCanvasFallback(fallback, fallbackCanvas, pitchPixels, current, ballPoint, frame);
        lastRenderProfile.sampledFrames += 1;
      }
    };
    paint();

    let dragging = false;
    let lastX = 0;
    let lastY = 0;
    const onPointerDown = (event: PointerEvent) => {
      dragging = true;
      lastX = event.clientX;
      lastY = event.clientY;
    };
    const onPointerMove = (event: PointerEvent) => {
      if (!dragging) return;
      const dx = event.clientX - lastX;
      const dy = event.clientY - lastY;
      lastX = event.clientX;
      lastY = event.clientY;
      cameraRef.current.panX -= dx * 0.08;
      cameraRef.current.panY += dy * 0.08;
    };
    const onPointerUp = () => {
      dragging = false;
    };
    const onClick = (event: MouseEvent) => {
      if (Math.abs(event.movementX) + Math.abs(event.movementY) > 4) return;
      const rect = (renderer?.domElement || fallbackCanvas)?.getBoundingClientRect();
      if (!rect || !onSelect) return;
      const nx = (event.clientX - rect.left) / rect.width;
      const ny = (event.clientY - rect.top) / rect.height;
      const hit = propsRef.current.players.find((player) => Math.hypot(player.x - nx, player.y - ny) < 0.035);
      if (hit) onSelect(`${hit.side}:${hit.playerId}`);
    };
    const target = renderer?.domElement || fallbackCanvas;
    target?.addEventListener("pointerdown", onPointerDown);
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);
    target?.addEventListener("click", onClick);

    return () => {
      stopped = true;
      window.cancelAnimationFrame(frameId);
      observer?.disconnect();
      target?.removeEventListener("pointerdown", onPointerDown);
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
      target?.removeEventListener("click", onClick);
      pool.forEach((mesh) => (mesh.material as THREE.Material).dispose());
      sharedGeometry.dispose();
      pitchTexture.dispose();
      bodyTexture.dispose();
      kitTexture.dispose();
      digitTexture.dispose();
      ballTexture.dispose();
      ringTexture.dispose();
      renderer?.dispose();
      renderer?.domElement.remove();
      fallbackCanvas?.remove();
    };
  }, [onSelect]);

  return (
    <div className="space-y-2" data-testid="orthographic-pitch">
      <div ref={hostRef} className="relative aspect-[16/10] w-full overflow-hidden rounded-xl border border-emerald-500/40 bg-[#0c2418]" />
      <div className="flex flex-wrap gap-2 text-[10px] font-black uppercase tracking-wider">
        <button
          type="button"
          className="rounded border border-white/15 px-2 py-1"
          onClick={() => {
            cameraRef.current = { zoom: 1, panX: 0, panY: 0, follow: false };
            setFollow(false);
          }}
        >
          Fit
        </button>
        <button
          type="button"
          className="rounded border border-white/15 px-2 py-1"
          onClick={() => {
            cameraRef.current.zoom = Math.min(2.4, cameraRef.current.zoom + 0.2);
          }}
        >
          Zoom in
        </button>
        <button
          type="button"
          className="rounded border border-white/15 px-2 py-1"
          onClick={() => {
            cameraRef.current.zoom = Math.max(0.8, cameraRef.current.zoom - 0.2);
          }}
        >
          Zoom out
        </button>
        <button
          type="button"
          className="rounded border border-white/15 px-2 py-1"
          onClick={() => setFollow((value) => !value)}
        >
          {follow ? "Follow on" : "Follow"}
        </button>
      </div>
      {unavailable && (
        <p className="rounded border border-amber-400/40 bg-amber-500/10 px-3 py-2 text-xs font-bold text-amber-200">
          MATCH FEED UNAVAILABLE — RECONNECTING
        </p>
      )}
      {demo && <p className="text-[10px] font-black uppercase tracking-widest text-amber-300">DEMO</p>}
      <span className="sr-only">
        draw-budget {CELL} fps {lastRenderProfile.fps} objects {lastRenderProfile.objectCount}
      </span>
    </div>
  );
}

export const OrthographicPitch = memo(OrthographicPitchComponent);

function paintCanvasFallback(
  ctx: CanvasRenderingContext2D,
  canvas: HTMLCanvasElement,
  pitchPixels: Uint8Array,
  current: {
    players: PitchPlayer[];
    eventType?: string | null;
    homeColor: string;
    awayColor: string;
    goalkeeperHome: string;
    goalkeeperAway: string;
  },
  ballPoint: { x: number; y: number } | null,
  frame: number,
) {
  const pitch = document.createElement("canvas");
  pitch.width = 512;
  pitch.height = 320;
  const pitchCtx = pitch.getContext("2d");
  if (pitchCtx) {
    pitchCtx.putImageData(new ImageData(new Uint8ClampedArray(pitchPixels), 512, 320), 0, 0);
    ctx.drawImage(pitch, 0, 0, canvas.width, canvas.height);
  } else {
    ctx.fillStyle = "#1f7a45";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  }
  current.players.forEach((player) => {
    const keeper = Boolean(player.isGoalkeeper) || String(player.role || "").toLowerCase().includes("gk");
    const kitColor = keeper
      ? player.side === "home"
        ? current.goalkeeperHome
        : current.goalkeeperAway
      : player.side === "home"
        ? current.homeColor
        : current.awayColor;
    paintRig(ctx, player.x * canvas.width, player.y * canvas.height, 42, {
      action: animationFor(player, current.eventType) as RigAction,
      frame,
      direction: 0,
      kitColor,
      shirtNumber: player.shirtNumber,
    });
  });
  if (ballPoint) {
    const ballCanvas = document.createElement("canvas");
    ballCanvas.width = 48;
    ballCanvas.height = 48;
    const ballCtx = ballCanvas.getContext("2d");
    if (ballCtx) {
      ballCtx.putImageData(new ImageData(new Uint8ClampedArray(rasterBall()), 48, 48), 0, 0);
      ctx.drawImage(ballCanvas, ballPoint.x * canvas.width - 8, ballPoint.y * canvas.height - 8, 16, 16);
    }
  }
}
