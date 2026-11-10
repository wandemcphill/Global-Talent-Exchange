import React, { useEffect, useRef } from "react";
import * as THREE from "three";
import { AssetStreamingCache } from "@/lib/3d/broadcast/AssetStreamingCache";
import { MIXAMO_KIT_URL } from "@/lib/3d/broadcast/MixamoKitFootballer";

/**
 * One textured kit figure for the lineup sheet.
 * The sheet itself stays the broadcast graphic. This is the player in it.
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
    renderer.setSize(mount.clientWidth || 220, mount.clientHeight || 280);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
    mount.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(32, 220 / 280, 0.1, 20);
    camera.position.set(0, 1.15, 3.4);
    camera.lookAt(0, 0.95, 0);
    scene.add(new THREE.HemisphereLight(0xdbeafe, 0x1e5631, 1.2));
    const key = new THREE.DirectionalLight(0xffffff, 1.4);
    key.position.set(2, 4, 3);
    scene.add(key);

    let cancelled = false;
    let player: THREE.Object3D | null = null;
    void AssetStreamingCache.getInstance()
      .loadGltf(MIXAMO_KIT_URL, renderer)
      .then((gltf) => {
        if (cancelled || !gltf?.scene) return;
        player = gltf.scene.clone(true);
        player.traverse((obj) => {
          const mesh = obj as THREE.Mesh;
          if (!mesh.isMesh) return;
          const list = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
          mesh.material = list.map((material) => {
            const tinted = material.clone() as THREE.MeshStandardMaterial;
            const name = `${material.name}`.toLowerCase();
            if (name.includes("tshirt") || name.includes("shirt")) tinted.color = new THREE.Color(primaryColor);
            return tinted;
          });
        });
        const box = new THREE.Box3().setFromObject(player);
        const height = Math.max(box.max.y - box.min.y, 0.001);
        const scale = 1.75 / height;
        player.scale.setScalar(scale);
        player.position.y = -box.min.y * scale;
        scene.add(player);
      });

    let raf = 0;
    const loop = () => {
      raf = requestAnimationFrame(loop);
      if (player) player.rotation.y += 0.008;
      renderer.render(scene, camera);
    };
    loop();

    return () => {
      cancelled = true;
      cancelAnimationFrame(raf);
      renderer.dispose();
      if (mount.contains(renderer.domElement)) mount.removeChild(renderer.domElement);
    };
  }, [primaryColor]);

  return (
    <div className="overflow-hidden rounded-xl border border-white/10 bg-slate-950/80" data-testid="kit-player-portrait">
      <div ref={mountRef} className="h-64 w-full" />
      <div className="flex items-center justify-between px-3 py-2 text-[11px] text-slate-300">
        <span className="font-bold uppercase tracking-wider text-white">{playerName || "Matchday kit"}</span>
        <span className="gx-mono text-emerald-300">{shirtNumber ?? ""}</span>
      </div>
    </div>
  );
}
