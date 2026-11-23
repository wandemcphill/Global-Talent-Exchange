import React, { useEffect, useRef } from "react";
import * as THREE from "three";
import { clone as cloneSkinned } from "three/examples/jsm/utils/SkeletonUtils.js";
import { AssetStreamingCache } from "@/lib/3d/broadcast/AssetStreamingCache";
import {
  attachKitIdle,
  fitAndGround,
  MIXAMO_KIT_URL,
} from "@/lib/3d/broadcast/MixamoKitFootballer";

/**
 * One textured kit figure for the lineup sheet.
 * Uses skinned bounding-box measurement, ResizeObserver aspect sync, and the Mixamo idle clip
 * so the player stands naturally at true proportions with zero T-posing or stretching.
 */
export function KitPlayerPortrait({
  shirtNumber,
  playerName,
  primaryColor = "#104A3A",
}: {
  shirtNumber?: number;
  playerName?: string;
  primaryColor?: string;
}) {
  const mountRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;
    if (typeof navigator !== "undefined" && /jsdom/i.test(navigator.userAgent || "")) return;

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    } catch {
      return;
    }
    const initW = Math.max(160, mount.clientWidth || 260);
    const initH = Math.max(160, mount.clientHeight || 256);
    renderer.setSize(initW, initH);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75));
    renderer.domElement.style.width = "100%";
    renderer.domElement.style.height = "100%";
    renderer.domElement.style.display = "block";
    mount.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(30, initW / initH, 0.1, 20);
    camera.position.set(0, 1.06, 3.65);
    camera.lookAt(0, 0.92, 0);

    scene.add(new THREE.HemisphereLight(0xe2f1ff, 0x1e5631, 1.35));
    const key = new THREE.DirectionalLight(0xffffff, 1.5);
    key.position.set(2.2, 4.2, 3.4);
    scene.add(key);
    const rim = new THREE.DirectionalLight(0x7dd3fc, 0.65);
    rim.position.set(-2.5, 2.5, -2.5);
    scene.add(rim);

    const resize = () => {
      const w = Math.max(160, mount.clientWidth || 260);
      const h = Math.max(160, mount.clientHeight || 256);
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    };
    const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(resize);
    observer?.observe(mount);

    let cancelled = false;
    let player: THREE.Object3D | null = null;
    let mixer: THREE.AnimationMixer | null = null;
    const clonedMaterials: THREE.Material[] = [];

    void AssetStreamingCache.getInstance()
      .loadGltf(MIXAMO_KIT_URL, renderer)
      .then(async (gltf) => {
        if (cancelled || !gltf?.scene) return;
        const clone = cloneSkinned(gltf.scene);
        clone.traverse((obj) => {
          const mesh = obj as THREE.Mesh;
          if (!mesh.isMesh) return;
          mesh.frustumCulled = false;
          const list = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
          const tinted = list.map((material) => {
            const next = material.clone() as THREE.MeshStandardMaterial;
            clonedMaterials.push(next);
            const name = `${material.name}`.toLowerCase();
            if (name.includes("tshirt") || name.includes("shirt")) {
              next.color = new THREE.Color(primaryColor);
            }
            return next;
          });
          mesh.material = tinted.length === 1 ? tinted[0] : tinted;
        });

        try {
          const idleMixer = await attachKitIdle(clone);
          if (cancelled) {
            idleMixer?.stopAllAction();
            return;
          }
          mixer = idleMixer;
          // Advance 1 tick so idle arms-down pose is active before measuring skinned bounds
          mixer?.update(1 / 60);
        } catch {
          // Graceful fallback if clip bundle unavailable
        }

        fitAndGround(clone, 1.75);
        player = clone;
        scene.add(clone);
      });

    let raf = 0;
    let lastMs = typeof performance !== "undefined" ? performance.now() : Date.now();
    const loop = () => {
      raf = requestAnimationFrame(loop);
      const nowMs = typeof performance !== "undefined" ? performance.now() : Date.now();
      const dt = Math.min(0.05, Math.max(0.001, (nowMs - lastMs) / 1000));
      lastMs = nowMs;
      if (mixer) mixer.update(dt);
      if (player) player.rotation.y += 0.36 * dt;
      renderer.render(scene, camera);
    };
    loop();

    return () => {
      cancelled = true;
      cancelAnimationFrame(raf);
      observer?.disconnect();
      mixer?.stopAllAction();
      clonedMaterials.forEach((m) => m.dispose());
      renderer.dispose();
      if (mount.contains(renderer.domElement)) mount.removeChild(renderer.domElement);
    };
  }, [primaryColor]);

  const cleanName = String(playerName || "").trim();
  const displayName =
    cleanName && cleanName.toLowerCase() !== "unnamed" && !/^#?\d+$/.test(cleanName)
      ? cleanName
      : "Matchday Kit";

  return (
    <div
      className="mx-auto w-full max-w-[320px] overflow-hidden rounded-xl border border-white/10 bg-[radial-gradient(circle_at_50%_35%,rgba(16,185,129,0.16),rgba(2,6,23,0.92)_72%)]"
      data-testid="kit-player-portrait"
    >
      <div ref={mountRef} className="h-56 w-full" />
      <div className="flex items-center justify-between border-t border-white/10 px-3 py-2 text-[11px] text-slate-300">
        <span className="font-bold uppercase tracking-wider text-white">{displayName}</span>
        <span className="gx-mono font-bold text-emerald-300">
          {shirtNumber && shirtNumber > 0 ? `#${shirtNumber}` : ""}
        </span>
      </div>
    </div>
  );
}
