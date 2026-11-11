import React, { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { MatchPitchLiveScene } from "@/lib/3d/broadcast/MatchPitchLiveScene";
import { MixamoKitFootballer } from "@/lib/3d/broadcast/MixamoKitFootballer";
import { loadFiveMinuteShowcaseFixture } from "@/lib/3d/broadcast/showcaseLoader";
import { PressRoomStage } from "@/components/gtex/PressRoomStage";
import { CinematicGiftingEngine } from "@/lib/3d/gifting/CinematicGiftingEngine";
import { PrestigeShowroomScene } from "@/lib/3d/scenes/PrestigeShowroomScene";
import type { SpectatorSafeMatchView } from "@/lib/3d/broadcast/spectatorContract";

function KitCloseUp() {
  const mountRef = useRef<HTMLDivElement | null>(null);
    const kitFrame = 3;

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;
    const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
    renderer.setSize(mount.clientWidth, mount.clientHeight);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    mount.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#0b1220");
    const camera = new THREE.PerspectiveCamera(28, mount.clientWidth / Math.max(mount.clientHeight, 1), 0.05, 40);
    camera.position.set(0.2, 1.35, 6.2);
    camera.lookAt(0, 0.95, 0);
    scene.add(new THREE.HemisphereLight(0xfff4e5, 0x1e3a2f, 1.4));
    const key = new THREE.DirectionalLight(0xffffff, 2.2);
    key.position.set(1.4, 3.2, 2.4);
    scene.add(key);
    const ground = new THREE.Mesh(
      new THREE.CircleGeometry(1.4, 32),
      new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.8 })
    );
    ground.rotation.x = -Math.PI / 2;
    scene.add(ground);

    const player = new MixamoKitFootballer({
      playerId: "review-kit",
      side: "home",
      shirtNumber: 9,
      label: "Review",
      role: "ST",
      isGoalkeeper: false,
      primaryColor: "#C8102E",
      secondaryColor: "#F5F5F5",
      accentColor: "#D4A84A",
      goalkeeperColor: "#F4C430",
      shortsColor: "#F5F5F5",
      socksColor: "#C8102E",
    });
    scene.add(player.rootGroup);
    (window as unknown as { __reviewPlayer?: MixamoKitFootballer }).__reviewPlayer = player;

    let raf = 0;
    let last = performance.now();
    const loop = (now: number) => {
      raf = requestAnimationFrame(loop);
      const delta = Math.min(0.05, (now - last) / 1000);
      last = now;
      player.update({
        deltaSec: delta,
        targetState: "idle",
        position3D: [0, 0, 0],
        facingAngleRad: Math.PI / 2,
        speedRatio: 0,
        hasPossession: false,
        ballPosition3D: [0, 0, 1],
        cameraPosition3D: [camera.position.x, camera.position.y, camera.position.z],
      });
      const label = mount.parentElement?.querySelector("[data-testid='kit-debug']");
      try {
        renderer.render(scene, camera);
        const info = renderer.info.render;
        let sphere = "none";
        player.rootGroup.traverse((obj) => {
          const mesh = obj as THREE.SkinnedMesh;
          if (sphere !== "none" || !mesh.isSkinnedMesh) return;
          mesh.geometry.computeBoundingSphere();
          const s = mesh.geometry.boundingSphere;
          sphere = s ? `${s.center.x.toFixed(2)},${s.center.y.toFixed(2)},${s.center.z.toFixed(2)} r${s.radius.toFixed(2)}` : "empty";
        });
        if (label) label.textContent = `calls ${info.calls} tris ${info.triangles} sphere ${sphere}`;
      } catch (err) {
        if (label) label.textContent = err instanceof Error ? err.message : String(err);
      }
    };
    loop(last);

    return () => {
      cancelAnimationFrame(raf);
      renderer.dispose();
      if (mount.contains(renderer.domElement)) mount.removeChild(renderer.domElement);
    };
  }, [kitFrame]);

  return (
    <div>
      <div ref={mountRef} className="h-[520px] w-full" data-testid="kit-closeup" />
      <p data-testid="kit-debug" className="px-3 py-1 text-xs text-amber-200">waiting</p>
    </div>
  );
}

export default function VisualReviewPage() {
  const [match, setMatch] = useState<SpectatorSafeMatchView | null>(null);

  useEffect(() => {
    void loadFiveMinuteShowcaseFixture(300).then(setMatch);
  }, []);

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <section id="broadcast" className="h-screen">
        {match ? (
          <MatchPitchLiveScene
            matchViewState={match}
            isLive
            qualityTier="high"
            weatherPreset="clear_night"
            playbackSpeed={1}
            isPaused={false}
            className="h-screen"
          />
        ) : (
          <div className="grid h-screen place-items-center text-sm text-slate-400">Loading the showcase match</div>
        )}
      </section>

      <section id="kit" className="border-t border-white/10 bg-slate-950">
        <KitCloseUp />
      </section>

      <section id="press" className="border-t border-white/10 bg-slate-950 p-4">
        <PressRoomStage clubName="Harbour Athletic" scoreLine="FT 2 - 1" primaryColor="#C8102E" />
        <div className="mt-3 rounded border border-white/10 bg-slate-900 p-3 text-sm text-slate-200">
          <p className="text-[11px] font-bold text-sky-300">Matchday Wire</p>
          <p className="mt-1 italic">How do you see the second half after the equaliser?</p>
          <button type="button" className="mt-2 rounded border border-white/10 px-3 py-2 text-xs">
            We kept the same shape and asked the wide players to arrive earlier.
          </button>
        </div>
      </section>

      <section id="gift" className="relative h-[640px] border-t border-white/10 bg-black">
        <CinematicGiftingEngine
          soundEnabled={false}
          activeGift={{
            id: "review-coach",
            gift_code: "club_coach",
            gift_name: "Club coach",
            sender: "Review",
            amount: 1,
            rarity: "legendary",
            duration_ms: 600000,
          }}
        />
      </section>

      <section id="showroom" className="h-[720px] border-t border-white/10 bg-black">
        <PrestigeShowroomScene
          assetName="Executive convoy"
          assetCategory="vehicle"
          meshArchetype="luxury_suv"
          modelName="Executive SUV"
          clubName="Harbour Athletic"
          primaryColor="#C8102E"
          compact={false}
        />
      </section>
    </main>
  );
}
