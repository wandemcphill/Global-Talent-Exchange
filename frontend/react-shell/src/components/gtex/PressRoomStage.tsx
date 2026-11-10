import React, { useEffect, useRef } from "react";
import * as THREE from "three";
import { AssetStreamingCache } from "@/lib/3d/broadcast/AssetStreamingCache";
import { MIXAMO_KIT_URL } from "@/lib/3d/broadcast/MixamoKitFootballer";
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
      renderer = new THREE.WebGLRenderer({ antialias: true });
    } catch {
      return;
    }
    const width = Math.max(320, mount.clientWidth || 800);
    const height = 320;
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
    mount.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(36, width / height, 0.1, 40);
    camera.position.set(0, 1.45, 4.4);
    camera.lookAt(0, 1.15, 0);
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
    void AssetStreamingCache.getInstance()
      .loadGltf(MIXAMO_KIT_URL, renderer)
      .then((gltf) => {
        if (cancelled || !gltf?.scene) return;
        const person = gltf.scene.clone(true);
        const shirt = new THREE.Color(primaryColor);
        person.traverse((obj) => {
          const mesh = obj as THREE.Mesh;
          if (!mesh.isMesh) return;
          const list = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
          mesh.material = list.map((material) => {
            const tinted = material.clone() as THREE.MeshStandardMaterial;
            if (material.name.toLowerCase().includes("shirt") || material.name.toLowerCase().includes("tshirt")) {
              tinted.color = shirt;
            }
            return tinted;
          });
        });
        const box = new THREE.Box3().setFromObject(person);
        const heightSpan = Math.max(box.max.y - box.min.y, 0.001);
        const scale = 1.72 / heightSpan;
        person.scale.setScalar(scale);
        person.position.y = -box.min.y * scale;
        person.position.z = -0.15;
        scene.add(person);
      });

    let raf = 0;
    const loop = () => {
      raf = requestAnimationFrame(loop);
      renderer.render(scene, camera);
    };
    loop();

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
