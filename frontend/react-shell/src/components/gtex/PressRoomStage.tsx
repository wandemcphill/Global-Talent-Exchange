import React, { useEffect, useRef } from "react";
import * as THREE from "three";
import { clone as cloneSkinned } from "three/examples/jsm/utils/SkeletonUtils.js";
import { AssetStreamingCache } from "@/lib/3d/broadcast/AssetStreamingCache";
import { attachKitIdle, MIXAMO_KIT_URL } from "@/lib/3d/broadcast/MixamoKitFootballer";
import { StadiumEnvironmentLighting } from "@/lib/3d/broadcast/StadiumEnvironmentLighting";

/**
 * The post-match desk. Questions stay in the page underneath.
 * This is the room: table, backdrop, microphones, and the kit figure.
 */
export function PressRoomStage({
  clubName,
  scoreLine,
  primaryColor = "#104A3A",
}: {
  clubName: string;
  scoreLine?: string;
  primaryColor?: string;
}) {
  const mountRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;
    if (typeof navigator !== "undefined" && /jsdom/i.test(navigator.userAgent || "")) return;

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    } catch {
      return;
    }
    const width = Math.max(320, mount.clientWidth || 800);
    const height = 320;
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
    mount.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(28, width / height, 0.08, 40);
    camera.position.set(0.15, 1.42, 3.35);
    camera.lookAt(0, 1.18, -0.55);
    scene.add(new THREE.HemisphereLight(0xdbeafe, 0x1e293b, 0.8));
    const key = new THREE.DirectionalLight(0xfff7ed, 1.6);
    key.position.set(2, 4, 3);
    scene.add(key);

    const wall = new THREE.Mesh(
      new THREE.PlaneGeometry(8, 3.2),
      new THREE.MeshStandardMaterial({ color: primaryColor, roughness: 0.72 })
    );
    wall.position.set(0, 1.7, -1.6);
    scene.add(wall);

    const table = new THREE.Mesh(
      new THREE.BoxGeometry(3.4, 0.08, 1.1),
      new THREE.MeshStandardMaterial({ color: 0x1c1917, roughness: 0.45, metalness: 0.15 })
    );
    table.position.set(0, 0.78, 0.35);
    scene.add(table);

    for (const x of [-0.55, 0.15, 0.7]) {
      const stand = new THREE.Mesh(
        new THREE.CylinderGeometry(0.015, 0.015, 0.28, 8),
        new THREE.MeshStandardMaterial({ color: 0x94a3b8, metalness: 0.8, roughness: 0.25 })
      );
      stand.position.set(x, 0.96, 0.55);
      const head = new THREE.Mesh(
        new THREE.SphereGeometry(0.045, 10, 8),
        new THREE.MeshStandardMaterial({ color: 0x0f172a, metalness: 0.4, roughness: 0.35 })
      );
      head.position.set(x, 1.12, 0.55);
      scene.add(stand, head);
    }

    const lighting = new StadiumEnvironmentLighting(renderer, scene, "high");
    void lighting.loadPolyHaven();

    let cancelled = false;
    let mixer: THREE.AnimationMixer | null = null;
    void AssetStreamingCache.getInstance()
      .loadGltf(MIXAMO_KIT_URL, renderer)
      .then(async (gltf) => {
        if (cancelled || !gltf?.scene) return;
        const person = cloneSkinned(gltf.scene);
        const shirt = new THREE.Color(primaryColor);
        person.traverse((obj) => {
          const mesh = obj as THREE.Mesh;
          if (!mesh.isMesh) return;
          const list = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
          const tinted = list.map((material) => {
            const next = material.clone() as THREE.MeshStandardMaterial;
            const name = material.name.toLowerCase();
            const cloth = name.includes("shirt") || name.includes("tshirt") || name.includes("short") || name.includes("leg");
            if (name.includes("shirt") || name.includes("tshirt")) next.color = shirt;
            else if (name.includes("short")) next.color = new THREE.Color("#e6e6e6");
            else if (name.includes("leg")) next.color = shirt;
            if (cloth) {
              next.map = null;
              next.metalness = 0.02;
              next.roughness = 0.58;
            }
            return next;
          });
          mesh.material = tinted.length === 1 ? tinted[0] : tinted;
        });
        person.updateMatrixWorld(true);
        const box = new THREE.Box3().setFromObject(person);
        const heightSpan = box.max.y - box.min.y;
        const scale = heightSpan >= 1.2 && heightSpan <= 2.6 ? 1 : heightSpan > 2.6 ? 1.75 / heightSpan : 1;
        person.scale.setScalar(scale);
        person.updateMatrixWorld(true);
        const placed = new THREE.Box3().setFromObject(person);
        person.position.y = Number.isFinite(placed.min.y) ? -placed.min.y : 0;
        person.position.z = -0.7;
        scene.add(person);
        mixer = await attachKitIdle(person);
      });

    let raf = 0;
    let last = performance.now();
    const loop = (now: number) => {
      raf = requestAnimationFrame(loop);
      const delta = Math.min(0.05, (now - last) / 1000);
      last = now;
      mixer?.update(delta);
      renderer.render(scene, camera);
    };
    loop(last);

    return () => {
      cancelled = true;
      cancelAnimationFrame(raf);
      lighting.dispose();
      renderer.dispose();
      if (mount.contains(renderer.domElement)) mount.removeChild(renderer.domElement);
    };
  }, [primaryColor]);

  return (
    <div className="overflow-hidden rounded-lg border border-white/10 bg-slate-950" data-testid="press-room-stage">
      <div ref={mountRef} className="h-80 w-full" />
      <div className="flex items-center justify-between px-3 py-2 text-[11px] text-slate-300">
        <span className="font-black uppercase tracking-wider text-white">{clubName} press desk</span>
        <span className="gx-mono text-cyan-300">{scoreLine || "Post-match"}</span>
      </div>
    </div>
  );
}
