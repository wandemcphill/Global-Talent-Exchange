/**
 * GTEX Unit 2A (U2A-006) — Humanoid Footballer GLB Asset Compiler
 *
 * Compiles the canonical rigged humanoid footballer model (`Player_Mobile_Mesh.fbx`,
 * 9,888 vertices, 26-bone Mixamo Humanoid skeleton) and its motion-capture FBX
 * animation library into a single WebGL-ready binary glTF asset:
 *   `public/models/footballer/gtex_humanoid_footballer.glb`
 *
 * Also copies supporting kit/AO texture maps into `public/models/footballer/textures/`.
 */

import * as fs from "fs";
import * as path from "path";
import * as THREE from "file:///C:/Users/ayomc/Desktop/GLOBAL%20TALENT%20EXCHANGE/frontend/react-shell/node_modules/three/build/three.module.js";
import { FBXLoader } from "file:///C:/Users/ayomc/Desktop/GLOBAL%20TALENT%20EXCHANGE/frontend/react-shell/node_modules/three/examples/jsm/loaders/FBXLoader.js";
import { GLTFExporter } from "file:///C:/Users/ayomc/Desktop/GLOBAL%20TALENT%20EXCHANGE/frontend/react-shell/node_modules/three/examples/jsm/exporters/GLTFExporter.js";
import { GLTFLoader } from "file:///C:/Users/ayomc/Desktop/GLOBAL%20TALENT%20EXCHANGE/frontend/react-shell/node_modules/three/examples/jsm/loaders/GLTFLoader.js";

globalThis.window = globalThis;
globalThis.document = {
  createElementNS: () => ({ style: {} }),
  createElement: () => ({ style: {} }),
};

class NodeFileReader {
  readAsArrayBuffer(blob) {
    blob.arrayBuffer().then((ab) => {
      this.result = ab;
      if (this.onloadend) this.onloadend();
    });
  }
  readAsDataURL(blob) {
    blob.arrayBuffer().then((ab) => {
      const b64 = Buffer.from(ab).toString("base64");
      this.result = `data:${blob.type || "application/octet-stream"};base64,${b64}`;
      if (this.onloadend) this.onloadend();
    });
  }
}
globalThis.FileReader = NodeFileReader;

const repoRoot = "C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE";
const sourceDir = path.join(repoRoot, "Gtex_Test_Migration/Assets/Arts/FootballPlayer");
const outDir = path.join(repoRoot, "frontend/react-shell/public/models/footballer");
const outTexDir = path.join(outDir, "textures");

fs.mkdirSync(outDir, { recursive: true });
fs.mkdirSync(outTexDir, { recursive: true });

// Copy texture masks for reference & material mapping
const texturesToCopy = [
  "PlayerModel/Textures/PlayerAO.png",
  "PlayerModel/Textures/KitMasks/FaceAndSkin.png",
  "PlayerModel/Textures/KitMasks/Boots.png",
  "PlayerModel/Textures/KitMasks/FakeClothAreas.png",
  "PlayerModel/Textures/KitMasks/Accessories1.png",
  "PlayerModel/Textures/KitSchemas/KitMask1.png",
  "PlayerModel/Textures/KitSchemas/KitMask2.png",
];

for (const relTex of texturesToCopy) {
  const src = path.join(sourceDir, relTex);
  if (fs.existsSync(src)) {
    const dest = path.join(outTexDir, path.basename(relTex));
    fs.copyFileSync(src, dest);
  }
}

const fbxLoader = new FBXLoader();

function loadFBX(filePath) {
  const buf = fs.readFileSync(filePath);
  return fbxLoader.parse(
    buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength),
    path.dirname(filePath) + "/"
  );
}

// 1. Load Rigged Humanoid Mesh
const playerRoot = loadFBX(path.join(sourceDir, "PlayerModel/Player_Mobile_Mesh.fbx"));
playerRoot.name = "GTEXHumanoidFootballerRoot";

let skinnedMesh = null;
playerRoot.traverse((child) => {
  if (child.isSkinnedMesh) {
    skinnedMesh = child;
  }
});

if (!skinnedMesh) {
  throw new Error("Failed to locate SkinnedMesh in Player_Mobile_Mesh.fbx");
}

// Upgrade material to PBR MeshStandardMaterial with vertexColors enabled
skinnedMesh.material = new THREE.MeshStandardMaterial({
  name: "GTEXFootballerKitMaterial",
  vertexColors: true,
  roughness: 0.65,
  metalness: 0.08,
});

// Initialize default vertex colors on the mesh so it has clean anatomical shading out of the box
const posAttr = skinnedMesh.geometry.attributes.position;
const skinIdxAttr = skinnedMesh.geometry.attributes.skinIndex;
const colors = new Float32Array(posAttr.count * 3);
const bones = skinnedMesh.skeleton.bones;
const validBoneNames = new Set(bones.map((b) => b.name));

for (let i = 0; i < posAttr.count; i++) {
  const bIdx = skinIdxAttr.getX(i);
  const boneName = bones[bIdx]?.name || "Spine";
  const y = posAttr.getY(i);
  let r = 0.0, g = 0.9, b = 0.46; // default home emerald jersey

  if (boneName === "Head" || boneName === "Neck") {
    if (y > 168.0) {
      r = 0.12; g = 0.10; b = 0.09; // hair
    } else {
      r = 0.88; g = 0.68; b = 0.54; // skin
    }
  } else if (
    boneName.includes("ForeArm") ||
    boneName.includes("Hand") ||
    (boneName.includes("Arm") && y < 116.0)
  ) {
    r = 0.88; g = 0.68; b = 0.54; // forearm/hand skin
  } else if ((boneName === "Hips" && y < 98.0) || (boneName.includes("UpLeg") && y >= 46.0)) {
    r = 0.96; g = 0.72; b = 0.24; // shorts
  } else if (boneName.includes("UpLeg") && y < 46.0) {
    r = 0.88; g = 0.68; b = 0.54; // knee/thigh skin
  } else if (boneName.includes("Leg") && !boneName.includes("UpLeg")) {
    if (y > 24.5) {
      r = 0.88; g = 0.68; b = 0.54; // knee skin
    } else if (y >= 6.8) {
      r = 0.08; g = 0.78; b = 0.42; // socks
    } else {
      r = 0.12; g = 0.14; b = 0.18; // boots
    }
  } else if (boneName.includes("Foot") || boneName.includes("Toe")) {
    r = 0.12; g = 0.14; b = 0.18; // boots
  }

  colors[i * 3] = r;
  colors[i * 3 + 1] = g;
  colors[i * 3 + 2] = b;
}
skinnedMesh.geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));

// 2. Load and sanitize motion-capture FBX clips
const mocapSources = [
  { clipName: "mocap_idle", file: "Animations/Locomotion/Idle.fbx", maxDuration: 3.0 },
  { clipName: "mocap_walk", file: "Animations/Locomotion/Walk/Walk Forward.fbx" },
  { clipName: "mocap_walk_back", file: "Animations/Locomotion/Walk/Walk Backward.fbx" },
  { clipName: "mocap_walk_left", file: "Animations/Locomotion/Walk/Left Strafe Walk.fbx" },
  { clipName: "mocap_walk_right", file: "Animations/Locomotion/Walk/Right Strafe Walk.fbx" },
  { clipName: "mocap_run", file: "Animations/Locomotion/Running.fbx" },
  { clipName: "mocap_run_back", file: "Animations/Locomotion/Running Backward.fbx" },
  { clipName: "mocap_strafe_left", file: "Animations/Locomotion/Left Strafe.fbx" },
  { clipName: "mocap_strafe_right", file: "Animations/Locomotion/Right Strafe.fbx" },
  { clipName: "mocap_turn_back_left", file: "Animations/Locomotion/Backward Left.fbx" },
  { clipName: "mocap_dribble", file: "Animations/Locomotion/DribbleNew.fbx" },
  { clipName: "mocap_pass", file: "Animations/Actions/Pass.fbx" },
  { clipName: "mocap_shoot", file: "Animations/Actions/Strike Foward Jog.fbx" },
  { clipName: "mocap_volley", file: "Animations/Actions/Scissor Kick.fbx" },
  { clipName: "mocap_header", file: "Animations/Actions/Soccer Header.fbx" },
  { clipName: "mocap_ground_header", file: "Animations/Actions/GroundHeader.fbx" },
  { clipName: "mocap_spin", file: "Animations/Actions/Soccer Spin.fbx" },
  { clipName: "mocap_tackle", file: "Animations/Actions/Tackling.fbx" },
  { clipName: "mocap_tackled", file: "Animations/Actions/Tackled.fbx" },
  { clipName: "mocap_struggle", file: "Animations/Actions/Struggle.fbx" },
  { clipName: "mocap_throw_in", file: "Animations/Actions/Throw In.fbx" },
  { clipName: "mocap_gk_idle", file: "Animations/Locomotion/Goalkeeper Idle Normal.fbx", maxDuration: 2.5 },
  { clipName: "mocap_gk_holding", file: "Animations/Locomotion/Goalkeeper Idle Holding.fbx", maxDuration: 2.2 },
  { clipName: "mocap_gk_sidestep", file: "Animations/Locomotion/Goalkeeper Sidestep.fbx" },
  { clipName: "mocap_gk_dive_high", file: "Animations/Locomotion/Goalkeeper Diving Save.fbx" },
  { clipName: "mocap_gk_dive_low", file: "Animations/Actions/GK BallSave Low.fbx" },
  { clipName: "mocap_gk_jump", file: "Animations/Actions/GKJump.fbx" },
  { clipName: "mocap_gk_drop_kick", file: "Animations/Actions/GK Drop Kick.fbx" },
  { clipName: "mocap_gk_miss", file: "Animations/Actions/GKMiss.fbx" },
];

function sanitizeAndResampleClip(rawClip, targetName, maxDuration) {
  const duration = maxDuration ? Math.min(rawClip.duration, maxDuration) : rawClip.duration;
  const sanitizedTracks = [];

  for (const track of rawClip.tracks) {
    const [boneName, prop] = track.name.split(".");
    if (!validBoneNames.has(boneName)) continue;

    // Only keep Hips.position and bone quaternion tracks
    if (prop !== "quaternion" && !(boneName === "Hips" && prop === "position")) {
      continue;
    }

    const itemSize = prop === "quaternion" ? 4 : 3;
    const times = [];
    const values = [];

    const x0 = prop === "position" && track.values.length >= 3 ? track.values[0] : 0;
    const z0 = prop === "position" && track.values.length >= 3 ? track.values[2] : 0;

    // Subsample every 2nd keyframe (or keep endpoints) to keep binary compact while preserving 100% smooth curves
    for (let k = 0; k < track.times.length; k++) {
      const t = track.times[k];
      if (t > duration + 0.001) break;
      if (k > 0 && k < track.times.length - 1 && k % 2 === 1) continue;

      times.push(Number(t.toFixed(4)));
      if (prop === "position") {
        // Lock horizontal root drift so authoritative pitch coordinates remain the sole position authority
        const rawDx = track.values[k * 3] - x0;
        const rawY = track.values[k * 3 + 1];
        const rawDz = track.values[k * 3 + 2] - z0;
        const clampedX = Math.max(-12, Math.min(12, rawDx));
        const clampedZ = Math.max(-12, Math.min(12, rawDz));
        values.push(Number(clampedX.toFixed(2)), Number(rawY.toFixed(2)), Number(clampedZ.toFixed(2)));
      } else {
        for (let c = 0; c < 4; c++) {
          values.push(Number(track.values[k * 4 + c].toFixed(4)));
        }
      }
    }

    if (times.length >= 2) {
      if (prop === "quaternion") {
        sanitizedTracks.push(new THREE.QuaternionKeyframeTrack(track.name, times, values));
      } else {
        sanitizedTracks.push(new THREE.VectorKeyframeTrack(track.name, times, values));
      }
    }
  }

  return new THREE.AnimationClip(targetName, duration, sanitizedTracks);
}

const exportedClips = [];
for (const src of mocapSources) {
  const fullPath = path.join(sourceDir, src.file);
  const fbxObj = loadFBX(fullPath);
  if (fbxObj.animations && fbxObj.animations[0]) {
    const cleanClip = sanitizeAndResampleClip(fbxObj.animations[0], src.clipName, src.maxDuration);
    exportedClips.push(cleanClip);
  }
}

console.log(`Compiled ${exportedClips.length} sanitized mocap clips for 26-bone skeleton.`);

const exporter = new GLTFExporter();
const outGlbPath = path.join(outDir, "gtex_humanoid_footballer.glb");

exporter.parse(
  playerRoot,
  (glbBuffer) => {
    fs.writeFileSync(outGlbPath, Buffer.from(glbBuffer));
    console.log(`Wrote GLB asset: ${outGlbPath} (${(glbBuffer.byteLength / 1024).toFixed(1)} KB)`);

    // Verify round-trip parse with GLTFLoader
    const gltfLoader = new GLTFLoader();
    gltfLoader.parse(
      glbBuffer,
      "",
      (gltf) => {
        let verifiedSkinnedMesh = null;
        gltf.scene.traverse((c) => {
          if (c.isSkinnedMesh) verifiedSkinnedMesh = c;
        });
        console.log(
          `Verified GLB round-trip: SkinnedMesh=${verifiedSkinnedMesh?.name}, vertices=${verifiedSkinnedMesh?.geometry.attributes.position.count}, bones=${verifiedSkinnedMesh?.skeleton.bones.length}, animations=${gltf.animations.length}`
        );
      },
      (err) => {
        console.error("GLTF verification failed:", err);
        process.exit(1);
      }
    );
  },
  (err) => {
    console.error("GLB export failed:", err);
    process.exit(1);
  },
  { binary: true, animations: exportedClips }
);
