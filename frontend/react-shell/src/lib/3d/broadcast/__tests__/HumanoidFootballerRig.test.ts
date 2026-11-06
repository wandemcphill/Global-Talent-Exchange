/**
 * GTEX Unit 2A (U2A-006) — Humanoid Football Animation Engine
 * Unit & Asset Integration Tests for HumanoidFootballerRig and `gtex_humanoid_footballer.glb`.
 */

import * as fs from "fs";
import * as path from "path";
import * as THREE from "three";
import {
  AnatomicalZone,
  classifyAnatomicalZone,
  HumanoidFootballerRig,
  parseHumanoidFootballerGLBBuffer,
} from "../HumanoidFootballerRig";
import { ALL_FOOTBALL_ANIMATION_STATES, GTEX_HUMANOID_BONE_NAMES } from "../FootballAnimationStateMachine";

describe("HumanoidFootballerRig & GLB Asset Verification", () => {
  it("creates a 26-bone SkinnedMesh humanoid rig with Spine2 shirt number badge and AnimationMixer", () => {
    const rig = new HumanoidFootballerRig({
      playerId: "home_9",
      side: "home",
      shirtNumber: 9,
      label: "Osimhen",
      role: "FWD",
      isGoalkeeper: false,
      primaryColor: "#00E676",
      secondaryColor: "#0F172A",
      accentColor: "#F5B83D",
      goalkeeperColor: "#FFB800",
    });

    expect(rig.skinnedMesh).toBeInstanceOf(THREE.SkinnedMesh);
    expect(rig.skeleton).toBeInstanceOf(THREE.Skeleton);
    expect(rig.skeleton.bones).toHaveLength(26);
    expect(rig.skeleton.bones.map((b) => b.name)).toEqual(GTEX_HUMANOID_BONE_NAMES);

    // Check skinIndex, skinWeight, and color attributes on geometry
    expect(rig.skinnedMesh.geometry.attributes.skinIndex).toBeDefined();
    expect(rig.skinnedMesh.geometry.attributes.skinWeight).toBeDefined();
    expect(rig.skinnedMesh.geometry.attributes.color).toBeDefined();

    // Check Spine2 shirt number badge attachment (both back and front chest badges)
    const spine2 = rig.boneByName.get("Spine2");
    expect(spine2).toBeDefined();
    const badge = spine2!.children.find((c) => c.name === "ShirtNumberBadge_9");
    const frontBadge = spine2!.children.find((c) => c.name === "FrontChestNumberBadge_9");
    expect(badge).toBeDefined();
    expect(frontBadge).toBeDefined();
    expect(rig.appearanceProfile.heightCm).toBeGreaterThanOrEqual(172);
    expect(rig.appearanceProfile.heightCm).toBeLessThanOrEqual(194);
    expect(rig.appearanceProfile.skinToneHex).toMatch(/^#[0-9A-Fa-f]{6}$/);

    // Step animation states and verify bone transformations update cleanly
    for (const state of ["walk", "run", "sprint", "dribble", "shoot", "goal_celebration"] as const) {
      rig.update({
        deltaSec: 0.1,
        targetState: state,
        position3D: [12, 0, -5],
        facingAngleRad: 0.25,
        speedRatio: 0.75,
        angularVelocityRad: 0.4,
        hasPossession: true,
        ballPosition3D: [15, 0.2, -4],
        cameraPosition3D: [0, 28, 48],
        qualityTier: "high",
      });
      expect(rig.getCurrentState()).toBe(state);
    }

    rig.dispose();
  });

  it("classifies bind-pose humanoid vertices into the 8 anatomical kit & appearance zones", () => {
    expect(classifyAnatomicalZone("Head", 0, 172, 0)).toBe(AnatomicalZone.HAIR);
    expect(classifyAnatomicalZone("Head", 0, 162, 5)).toBe(AnatomicalZone.SKIN);
    expect(classifyAnatomicalZone("Spine2", 0, 140, 0)).toBe(AnatomicalZone.JERSEY_PRIMARY);
    expect(classifyAnatomicalZone("Spine2", 0, 150, 0)).toBe(AnatomicalZone.JERSEY_TRIM);
    expect(classifyAnatomicalZone("Hips", 0, 85, 0)).toBe(AnatomicalZone.SHORTS);
    expect(classifyAnatomicalZone("LeftLeg", 12, 15, 0)).toBe(AnatomicalZone.SOCKS);
    expect(classifyAnatomicalZone("LeftFoot", 16, 4, 5)).toBe(AnatomicalZone.BOOTS);
    expect(classifyAnatomicalZone("LeftHand", 40, 82, 6)).toBe(AnatomicalZone.GLOVES);
  });

  it("loads and verifies the compiled `public/models/footballer/gtex_humanoid_footballer.glb` asset (9,888 vertices, 26 bones, 29 mocap clips)", async () => {
    const glbPath = path.resolve(
      __dirname,
      "../../../../../public/models/footballer/gtex_humanoid_footballer.glb"
    );
    expect(fs.existsSync(glbPath)).toBe(true);

    const fileBuf = fs.readFileSync(glbPath);
    const arrayBuffer = fileBuf.buffer.slice(
      fileBuf.byteOffset,
      fileBuf.byteOffset + fileBuf.byteLength
    );

    const asset = await parseHumanoidFootballerGLBBuffer(arrayBuffer);
    expect(asset.skinnedMesh).toBeInstanceOf(THREE.SkinnedMesh);
    expect(asset.skinnedMesh.geometry.attributes.position.count).toBe(9888);
    expect(asset.skinnedMesh.skeleton.bones).toHaveLength(26);
    expect(asset.mocapClips).toHaveLength(29);
    expect(asset.clipLibrary.size).toBe(ALL_FOOTBALL_ANIMATION_STATES.length);

    // Instantiate a goalkeeper rig from the parsed GLB asset and test GK animations
    const gkRig = new HumanoidFootballerRig({
      playerId: "away_1",
      side: "away",
      shirtNumber: 1,
      label: "Nwabali",
      role: "GK",
      isGoalkeeper: true,
      primaryColor: "#3B82F6",
      secondaryColor: "#FFFFFF",
      accentColor: "#F43F5E",
      goalkeeperColor: "#EC4899",
    });

    expect(gkRig.skinnedMesh.geometry.attributes.position.count).toBe(9888);
    expect(gkRig.skeleton.bones).toHaveLength(26);

    gkRig.update({
      deltaSec: 0.15,
      targetState: "gk_dive_high",
      position3D: [50, 0, 0],
      facingAngleRad: Math.PI,
      speedRatio: 0.6,
      hasPossession: false,
      ballPosition3D: [48, 1.6, 2],
      cameraPosition3D: [35, 16, 25],
      qualityTier: "high",
    });
    expect(gkRig.getCurrentState()).toBe("gk_dive_high");
    expect(gkRig.getLODLevel()).toBe("full");

    // Verify far LOD throttling when camera is > 64m away
    gkRig.update({
      deltaSec: 0.016,
      targetState: "idle",
      position3D: [-50, 0, -30],
      facingAngleRad: 0,
      speedRatio: 0,
      hasPossession: false,
      ballPosition3D: [0, 0.05, 0],
      cameraPosition3D: [45, 32, 55],
      qualityTier: "medium",
    });
    // First update aftergk_dive_high holds minHoldSec; advance past minHoldSec to enter idle
    gkRig.update({
      deltaSec: 0.9,
      targetState: "idle",
      position3D: [-50, 0, -30],
      facingAngleRad: 0,
      speedRatio: 0,
      hasPossession: false,
      ballPosition3D: [0, 0.05, 0],
      cameraPosition3D: [45, 32, 55],
      qualityTier: "medium",
    });
    expect(gkRig.getCurrentState()).toBe("idle");
    expect(gkRig.getLODLevel()).toBe("far");

    gkRig.dispose();
  });

  it("shares read-only GPU BufferAttributes across rigs, switches High/Medium/Low materials, and locks root drift", () => {
    const rigA = new HumanoidFootballerRig({
      playerId: "atlas_10",
      side: "home",
      shirtNumber: 10,
      label: "Bellingham",
      role: "MID",
      isGoalkeeper: false,
      primaryColor: "#10263F",
      secondaryColor: "#F2B632",
      accentColor: "#26D07C",
      goalkeeperColor: "#FFB800",
    });
    const rigB = new HumanoidFootballerRig({
      playerId: "rio_9",
      side: "away",
      shirtNumber: 9,
      label: "Awoniyi",
      role: "FWD",
      isGoalkeeper: false,
      primaryColor: "#1D3557",
      secondaryColor: "#E63946",
      accentColor: "#F1FAEE",
      goalkeeperColor: "#10B981",
    });

    // Shared position/normal/skinIndex/skinWeight BufferAttribute references across rigs
    expect(rigA.skinnedMesh.geometry.attributes.position).toBe(
      rigB.skinnedMesh.geometry.attributes.position
    );
    expect(rigA.skinnedMesh.geometry.attributes.skinIndex).toBe(
      rigB.skinnedMesh.geometry.attributes.skinIndex
    );
    // Independent per-player kit/appearance color attribute
    expect(rigA.skinnedMesh.geometry.attributes.color).not.toBe(
      rigB.skinnedMesh.geometry.attributes.color
    );
    expect(rigA.skinnedMesh.frustumCulled).toBe(true);
    expect(rigA.skinnedMesh.geometry.boundingSphere).toBeDefined();

    // High tier uses MeshStandardMaterial; Medium/Low uses MeshLambertMaterial
    expect(rigA.skinnedMesh.material).toBeInstanceOf(THREE.MeshStandardMaterial);
    rigA.update({
      deltaSec: 0.12,
      targetState: "jumping_challenge",
      position3D: [10, 0, 0],
      facingAngleRad: 0,
      speedRatio: 0.5,
      hasPossession: true,
      ballPosition3D: [10.4, 2.1, 0],
      cameraPosition3D: [0, 22, 38],
      qualityTier: "medium",
    });
    expect(rigA.skinnedMesh.material).toBeInstanceOf(THREE.MeshLambertMaterial);
    expect(rigA.modelContainer.position.y).toBeGreaterThan(0.05);

    rigA.dispose();
    rigB.dispose();
  });
});
