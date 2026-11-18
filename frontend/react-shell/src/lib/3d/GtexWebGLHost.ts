/**
 * Shared WebGL lifecycle for GTEX presentation scenes.
 * One renderer, one animation loop, and one disposal path per mounted stage.
 */

import { useEffect, useRef } from "react";
import * as THREE from "three";
import { disposeScene } from "./disposeScene";
import type { QualityProfile } from "./GtexSceneTypes";

export interface GtexWebGLContext {
  scene: THREE.Scene;
  camera: THREE.PerspectiveCamera;
  renderer: THREE.WebGLRenderer;
  quality: QualityProfile;
  width: number;
  height: number;
  aborted: () => boolean;
}

export interface GtexSceneController {
  mount(ctx: GtexWebGLContext): void | Promise<void>;
  update?(dt: number, elapsed: number): void;
  resize?(width: number, height: number): void;
  dispose?(): void;
}

export function isJsdomEnvironment(): boolean {
  return typeof navigator !== "undefined" && /jsdom/i.test(navigator.userAgent || "");
}

export function bindWebGLContextRestoration(
  canvas: HTMLCanvasElement,
  handlers: { onLost: () => void; onRestored: () => void }
): () => void {
  const onLost = (event: Event) => {
    event.preventDefault();
    handlers.onLost();
  };
  const onRestored = () => {
    handlers.onRestored();
  };
  canvas.addEventListener("webglcontextlost", onLost);
  canvas.addEventListener("webglcontextrestored", onRestored);
  return () => {
    canvas.removeEventListener("webglcontextlost", onLost);
    canvas.removeEventListener("webglcontextrestored", onRestored);
  };
}

/** Frame scheduler used by the host. Low-power tiers accumulate until the target interval. */
export function createFrameScheduler(targetFps: number, tick: (dt: number) => boolean | void) {
  let raf = 0;
  let stopped = false;
  let last = 0;
  let acc = 0;
  const minFrame = 1 / Math.max(1, targetFps);

  const loop = (now: number) => {
    if (stopped) return;
    raf = requestAnimationFrame(loop);
    if (!last) last = now;
    const dt = Math.min(0.1, (now - last) / 1000);
    last = now;
    acc += dt;
    if (acc < minFrame) return;
    const step = acc;
    acc = 0;
    const keep = tick(step);
    if (keep === false) {
      stopped = true;
      cancelAnimationFrame(raf);
    }
  };

  return {
    start() {
      if (stopped) return;
      raf = requestAnimationFrame(loop);
    },
    stop() {
      stopped = true;
      if (raf) cancelAnimationFrame(raf);
      raf = 0;
    },
  };
}

export function useGtexWebGLHost(options: {
  quality: QualityProfile;
  createController: () => GtexSceneController;
  enabled?: boolean;
  revision?: string;
  onUnavailable?: (reason: "webgl" | "asset" | "context") => void;
  onContextLost?: () => void;
  onContextRestored?: () => void;
}) {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const createRef = useRef(options.createController);
  createRef.current = options.createController;
  const unavailableRef = useRef(options.onUnavailable);
  unavailableRef.current = options.onUnavailable;
  const lostRef = useRef(options.onContextLost);
  lostRef.current = options.onContextLost;
  const restoredRef = useRef(options.onContextRestored);
  restoredRef.current = options.onContextRestored;
  const quality = options.quality;

  useEffect(() => {
    if (options.enabled === false) return;
    const mount = mountRef.current;
    if (!mount || isJsdomEnvironment()) return;

    let stopped = false;
    let renderer: THREE.WebGLRenderer | null = null;
    let scene: THREE.Scene | null = null;
    let camera: THREE.PerspectiveCamera | null = null;
    let controller: GtexSceneController | null = null;
    let removeContext: (() => void) | null = null;
    let observer: ResizeObserver | null = null;
    let intersection: IntersectionObserver | null = null;
    let scheduler: { start: () => void; stop: () => void } | null = null;
    let visible = typeof document === "undefined" || document.visibilityState !== "hidden";
    let inView = true;
    let elapsed = 0;
    let restoring = false;

    const onVisibility = () => {
      visible = document.visibilityState !== "hidden";
    };

    const teardownGraphics = () => {
      scheduler?.stop();
      scheduler = null;
      removeContext?.();
      removeContext = null;
      observer?.disconnect();
      observer = null;
      intersection?.disconnect();
      intersection = null;
      try {
        controller?.dispose?.();
      } catch {
        // Controller cleanup is best-effort.
      }
      controller = null;
      if (renderer) disposeScene(scene, renderer);
      scene = null;
      camera = null;
      renderer = null;
    };

    const boot = () => {
      if (stopped) return;
      const profile = quality;
      try {
        renderer = new THREE.WebGLRenderer({
          antialias: profile.antialias,
          alpha: false,
          preserveDrawingBuffer: true,
          powerPreference: profile.tier === "low" ? "low-power" : "high-performance",
        });
      } catch {
        unavailableRef.current?.("webgl");
        return;
      }

      const width = Math.max(1, mount.clientWidth || 640);
      const height = Math.max(1, mount.clientHeight || 360);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, profile.pixelRatio, 2));
      renderer.setSize(width, height, false);
      renderer.outputColorSpace = THREE.SRGBColorSpace;
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 1.05;
      renderer.shadowMap.enabled = profile.shadowsEnabled;
      renderer.shadowMap.type = THREE.PCFSoftShadowMap;
      renderer.domElement.style.width = "100%";
      renderer.domElement.style.height = "100%";
      renderer.domElement.style.display = "block";
      mount.appendChild(renderer.domElement);

      scene = new THREE.Scene();
      camera = new THREE.PerspectiveCamera(40, width / height, 0.1, 900);
      camera.position.set(48, 28, 72);

      controller = createRef.current();
      const ctx: GtexWebGLContext = {
        scene,
        camera,
        renderer,
        quality: profile,
        width,
        height,
        aborted: () => stopped,
      };
      Promise.resolve(controller.mount(ctx)).catch(() => {
        if (!stopped) unavailableRef.current?.("asset");
      });

      const resize = () => {
        if (!renderer || !camera || stopped) return;
        const w = Math.max(1, mount.clientWidth || 1);
        const h = Math.max(1, mount.clientHeight || 1);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, profile.pixelRatio, 2));
        renderer.setSize(w, h, false);
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
        controller?.resize?.(w, h);
      };
      if (typeof ResizeObserver !== "undefined") {
        observer = new ResizeObserver(resize);
        observer.observe(mount);
      }

      if (typeof IntersectionObserver !== "undefined") {
        intersection = new IntersectionObserver((entries) => {
          inView = entries.some((entry) => entry.isIntersecting);
        });
        intersection.observe(mount);
      }

      removeContext = bindWebGLContextRestoration(renderer.domElement, {
        onLost: () => {
          lostRef.current?.();
          unavailableRef.current?.("context");
        },
        onRestored: () => {
          restoredRef.current?.();
          if (restoring || stopped) return;
          restoring = true;
          teardownGraphics();
          restoring = false;
          boot();
        },
      });

      scheduler = createFrameScheduler(profile.targetFps, (dt) => {
        if (stopped) return false;
        if (!visible || !inView || !renderer || !scene || !camera) return;
        elapsed += dt;
        controller?.update?.(dt, elapsed);
        renderer.render(scene, camera);
      });
      scheduler.start();
    };

    document.addEventListener("visibilitychange", onVisibility);
    boot();

    return () => {
      stopped = true;
      document.removeEventListener("visibilitychange", onVisibility);
      teardownGraphics();
    };
  }, [options.enabled, options.revision, quality]);

  return { mountRef };
}
