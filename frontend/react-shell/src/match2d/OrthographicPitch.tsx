import React, { useEffect, useRef } from "react";
import * as THREE from "three";

import * as matchRenderer from "./createMatchRenderer";
import { animationFor, effectFor, type PitchPlayer } from "./matchStateAdapter";
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

export const lastRenderProfile = { calls: 0, sampledFrames: 0 };

function dataTexture(data: Uint8Array, width: number, height: number) {
  const texture = new THREE.DataTexture(data, width, height, THREE.RGBAFormat);
  texture.flipY = true;
  texture.needsUpdate = true;
  texture.magFilter = THREE.LinearFilter;
  texture.minFilter = THREE.LinearFilter;
  texture.generateMipmaps = false;
  return texture;
}

export function OrthographicPitch({
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

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return undefined;
    let renderer: THREE.WebGLRenderer | null = null;
    let fallback: CanvasRenderingContext2D | null = null;
    let fallbackCanvas: HTMLCanvasElement | null = null;
    let stopped = false;
    let frameId = 0;
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
    const bodies = new Map<string, THREE.Mesh>();
    const motion = new Map<string, { x: number; y: number; facing: number; speed: number }>();
    let previousBall: { x: number; y: number } | null = null;

    const resize = () => {
      const width = Math.max(host.clientWidth, 320);
      const height = Math.max(Math.round(width * 0.62), 200);
      if (renderer) renderer.setSize(width, height, false);
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
      });
      renderer.domElement.style.width = "100%";
      renderer.domElement.style.height = "100%";
      renderer.domElement.style.touchAction = "none";
    } catch {
      renderer = null;
      fallbackCanvas = document.createElement("canvas");
      try {
        fallback = fallbackCanvas.getContext("2d");
      } catch {
        fallback = null;
      }
      host.appendChild(fallbackCanvas);
    }
    resize();
    const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(resize);
    observer?.observe(host);

    const toWorld = (x: number, y: number) => ({
      x: (x - 0.5) * PITCH_W,
      y: (0.5 - y) * PITCH_H,
    });

    const paint = () => {
      if (stopped) return;
      frameId = window.requestAnimationFrame(paint);
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
        let mesh = bodies.get(player.playerId);
        if (!mesh && renderer) {
          const material = new THREE.ShaderMaterial({
            transparent: true,
            depthWrite: false,
            side: THREE.DoubleSide,
            uniforms: {
              uBody: { value: bodyTexture },
              uKit: { value: kitTexture },
              uDigits: { value: digitTexture },
              uKitColor: { value: new THREE.Color(kitColor) },
              uOffset: { value: new THREE.Vector2() },
              uRepeat: { value: new THREE.Vector2(1 / ATLAS_COLUMNS, 1 / ATLAS_ROWS) },
              uShirt: { value: player.shirtNumber },
            },
            vertexShader: VERTEX,
            fragmentShader: FRAGMENT,
          });
          mesh = new THREE.Mesh(new THREE.PlaneGeometry(4.8, 4.8), material);
          scene.add(mesh);
          bodies.set(player.playerId, mesh);
        }
        if (mesh) {
          mesh.position.set(point.x, point.y, 1);
          const material = mesh.material as THREE.ShaderMaterial;
          const uv = cellUv(action, direction, frame);
          material.uniforms.uOffset.value.set(uv.offsetX, uv.offsetY);
          material.uniforms.uKitColor.value.set(kitColor);
          material.uniforms.uShirt.value = player.shirtNumber;
          material.opacity = current.selectedKey === `${player.side}:${player.playerId}` ? 1 : 0.96;
        }
        if (current.selectedKey === `${player.side}:${player.playerId}`) {
          ring.visible = true;
          ring.position.set(point.x, point.y - 1.2, 0.4);
        }
      });
      if (!current.players.some((player) => current.selectedKey === `${player.side}:${player.playerId}`)) ring.visible = false;
      bodies.forEach((mesh, id) => {
        if (!seen.has(id)) {
          scene.remove(mesh);
          (mesh.material as THREE.Material).dispose();
          bodies.delete(id);
          motion.delete(id);
        }
      });
      if (ballPoint) {
        const point = toWorld(ballPoint.x, ballPoint.y);
        ballMesh.position.set(point.x, point.y, 2);
        ballMesh.visible = true;
        const cue = effectFor(current.eventType);
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
      if (renderer) {
        renderer.render(scene, camera);
        lastRenderProfile.calls = renderer.info.render.calls;
        lastRenderProfile.sampledFrames += 1;
      } else if (fallback && fallbackCanvas) {
        paintCanvasFallback(fallback, fallbackCanvas, pitchPixels, current, ballPoint, frame);
      }
    };
    paint();

    const onClick = (event: MouseEvent) => {
      const rect = (renderer?.domElement || fallbackCanvas)?.getBoundingClientRect();
      if (!rect || !onSelect) return;
      const nx = (event.clientX - rect.left) / rect.width;
      const ny = (event.clientY - rect.top) / rect.height;
      const hit = propsRef.current.players.find((player) => Math.hypot(player.x - nx, player.y - ny) < 0.035);
      if (hit) onSelect(`${hit.side}:${hit.playerId}`);
    };
    (renderer?.domElement || fallbackCanvas)?.addEventListener("click", onClick);

    return () => {
      stopped = true;
      window.cancelAnimationFrame(frameId);
      observer?.disconnect();
      (renderer?.domElement || fallbackCanvas)?.removeEventListener("click", onClick);
      bodies.forEach((mesh) => (mesh.material as THREE.Material).dispose());
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
        <button type="button" className="rounded border border-white/15 px-2 py-1" onClick={() => { cameraRef.current = { zoom: 1, panX: 0, panY: 0, follow: false }; }}>Fit</button>
        <button type="button" className="rounded border border-white/15 px-2 py-1" onClick={() => { cameraRef.current.zoom = Math.min(2.4, cameraRef.current.zoom + 0.2); }}>Zoom in</button>
        <button type="button" className="rounded border border-white/15 px-2 py-1" onClick={() => { cameraRef.current.zoom = Math.max(0.8, cameraRef.current.zoom - 0.2); }}>Zoom out</button>
        <button type="button" className="rounded border border-white/15 px-2 py-1" onClick={() => { cameraRef.current.follow = !cameraRef.current.follow; }}>{cameraRef.current.follow ? "Follow on" : "Follow"}</button>
      </div>
      {unavailable && (
        <p className="rounded border border-amber-400/40 bg-amber-500/10 px-3 py-2 text-xs font-bold text-amber-200">
          MATCH FEED UNAVAILABLE — RECONNECTING
        </p>
      )}
      {demo && <p className="text-[10px] font-black uppercase tracking-widest text-amber-300">DEMO</p>}
      <span className="sr-only">draw-budget {CELL}</span>
    </div>
  );
}

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
