/**
 * GTEX Unit 2A (U2A-006) — Humanoid Footballer GLB Asset Compiler
 *
 * Compiles the canonical rigged humanoid footballer model (`Player_Mobile_Mesh.fbx`,
 * 9,888 vertices, 26-bone Mixamo Humanoid skeleton) and its 29 motion-capture FBX
 * animation clips (retargeted from `Animations/Avatar.fbx` T-Pose to `Player_Mobile_Mesh.fbx`
 * world-aligned A-Pose bind matrices) into a single WebGL-ready binary glTF asset:
 *   `public/models/footballer/gtex_humanoid_footballer.glb`
 *
 * Also copies supporting kit/AO texture maps into `public/models/footballer/textures/`.
 */

import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import * as THREE from "three";
import { FBXLoader } from "three/addons/loaders/FBXLoader.js";
import { GLTFExporter } from "three/addons/exporters/GLTFExporter.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

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

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(process.env.GTEX_REPO_ROOT || path.join(scriptDir, "../../.."));
const sourceDir = path.resolve(
  process.env.GTEX_HUMANOID_SOURCE_DIR ||
    path.join(repoRoot, "Gtex_Test_Migration/Assets/Arts/FootballPlayer"),
);
const outDir = path.join(repoRoot, "frontend/react-shell/public/models/footballer");
const outTexDir = path.join(outDir, "textures");

const requiredSourceFiles = [
  "PlayerModel/Player_Mobile_Mesh.fbx",
  "Animations/Avatar.fbx",
];
const missingSourceFiles = requiredSourceFiles.filter(
  (file) => !fs.existsSync(path.join(sourceDir, file)),
);
if (missingSourceFiles.length > 0) {
  throw new Error(
    `Humanoid source files are missing from ${sourceDir}: ${missingSourceFiles.join(", ")}. ` +
      "Set GTEX_HUMANOID_SOURCE_DIR to the extracted FootballPlayer source directory.",
  );
}

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
    path.dirname(filePath) + "/",
  );
}

// 1. Load Rigged Humanoid Mesh (`Player_Mobile_Mesh.fbx`) & Source Animation Avatar (`Animations/Avatar.fbx`)
const playerRoot = loadFBX(path.join(sourceDir, "PlayerModel/Player_Mobile_Mesh.fbx"));
playerRoot.name = "GTEXHumanoidFootballerRoot";
playerRoot.updateMatrixWorld(true);

const avatarRoot = loadFBX(path.join(sourceDir, "Animations/Avatar.fbx"));
avatarRoot.updateMatrixWorld(true);

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

for (let i = 0; i < posAttr.count; i++) {
  const bIdx = skinIdxAttr.getX(i);
  const boneName = bones[bIdx]?.name || "Spine";
  const y = posAttr.getY(i);
  let r = 0.0, g = 0.9, b = 0.46; // default home emerald jersey

  if (boneName === "Head" || boneName === "Neck") {
    if (y > 168.0) {
      r = 0.12;
      g = 0.10;
      b = 0.09; // hair
    } else {
      r = 0.88;
      g = 0.68;
      b = 0.54; // skin
    }
  } else if (
    boneName.includes("ForeArm") ||
    boneName.includes("Hand") ||
    (boneName.includes("Arm") && y < 116.0)
  ) {
    r = 0.88;
    g = 0.68;
    b = 0.54; // forearm/hand skin
  } else if ((boneName === "Hips" && y < 98.0) || (boneName.includes("UpLeg") && y >= 46.0)) {
    r = 0.96;
    g = 0.72;
    b = 0.24; // shorts
  } else if (boneName.includes("UpLeg") && y < 46.0) {
    r = 0.88;
    g = 0.68;
    b = 0.54; // knee/thigh skin
  } else if (boneName.includes("Leg") && !boneName.includes("UpLeg")) {
    if (y > 24.5) {
      r = 0.88;
      g = 0.68;
      b = 0.54; // knee skin
    } else if (y >= 6.8) {
      r = 0.08;
      g = 0.78;
      b = 0.42; // socks
    } else {
      r = 0.12;
      g = 0.14;
      b = 0.18; // boots
    }
  } else if (boneName.includes("Foot") || boneName.includes("Toe")) {
    r = 0.12;
    g = 0.14;
    b = 0.18; // boots
  }

  colors[i * 3] = r;
  colors[i * 3 + 1] = g;
  colors[i * 3 + 2] = b;
}
skinnedMesh.geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));

// 2. Build Exact Avatar-to-Mesh World-Quaternion & Segment-Vector Retargeting Tables
const meshBonesByName = new Map();
bones.forEach((b) => meshBonesByName.set(b.name, b));

const avatarBonesByName = new Map();
avatarRoot.traverse((b) => {
  if (b.name && meshBonesByName.has(b.name)) {
    avatarBonesByName.set(b.name, b);
  }
});

const DIRECTION_BONE_PAIRS = {
  Hips: ["Hips", "Spine"],
  Spine: ["Spine", "Spine1"],
  Spine1: ["Spine1", "Spine2"],
  Spine2: ["Spine2", "Neck"],
  Neck: ["Neck", "Head"],
  Head: ["Neck", "Head"],
  LeftShoulder: ["LeftShoulder", "LeftArm"],
  LeftArm: ["LeftArm", "LeftForeArm"],
  LeftForeArm: ["LeftForeArm", "LeftHand"],
  LeftHand: ["LeftForeArm", "LeftHand"],
  RightShoulder: ["RightShoulder", "RightArm"],
  RightArm: ["RightArm", "RightForeArm"],
  RightForeArm: ["RightForeArm", "RightHand"],
  RightHand: ["RightForeArm", "RightHand"],
  LeftUpLeg: ["LeftUpLeg", "LeftLeg"],
  LeftLeg: ["LeftLeg", "LeftFoot"],
  LeftFoot: ["LeftFoot", "LeftToeBase"],
  LeftToeBase: ["LeftFoot", "LeftToeBase"],
  RightUpLeg: ["RightUpLeg", "RightLeg"],
  RightLeg: ["RightLeg", "RightFoot"],
  RightFoot: ["RightFoot", "RightToeBase"],
  RightToeBase: ["RightFoot", "RightToeBase"],
};

const qSrcAligned = new Map();
const qDstBind = new Map();

for (const [name, mb] of meshBonesByName.entries()) {
  const ab = avatarBonesByName.get(name);
  const wqDst = new THREE.Quaternion();
  mb.getWorldQuaternion(wqDst);
  qDstBind.set(name, wqDst.clone());

  if (!ab) {
    qSrcAligned.set(name, wqDst.clone());
    continue;
  }

  const wqSrc = new THREE.Quaternion();
  ab.getWorldQuaternion(wqSrc);

  const pair = DIRECTION_BONE_PAIRS[name];
  if (
    pair &&
    meshBonesByName.has(pair[0]) &&
    meshBonesByName.has(pair[1]) &&
    avatarBonesByName.has(pair[0]) &&
    avatarBonesByName.has(pair[1])
  ) {
    const mp0 = new THREE.Vector3().setFromMatrixPosition(meshBonesByName.get(pair[0]).matrixWorld);
    const mp1 = new THREE.Vector3().setFromMatrixPosition(meshBonesByName.get(pair[1]).matrixWorld);
    const uDst = mp1.clone().sub(mp0).normalize();

    const ap0 = new THREE.Vector3().setFromMatrixPosition(
      avatarBonesByName.get(pair[0]).matrixWorld,
    );
    const ap1 = new THREE.Vector3().setFromMatrixPosition(
      avatarBonesByName.get(pair[1]).matrixWorld,
    );
    const uSrc = ap1.clone().sub(ap0).normalize();

    const rPose = new THREE.Quaternion().setFromUnitVectors(uSrc, uDst);
    qSrcAligned.set(name, rPose.multiply(wqSrc));
  } else {
    qSrcAligned.set(name, wqSrc.clone());
  }
}

// Save avatar rest pose so we can reset between clips
const avatarRestLocalPos = new Map();
const avatarRestLocalQuat = new Map();
for (const [name, ab] of avatarBonesByName.entries()) {
  avatarRestLocalPos.set(name, ab.position.clone());
  avatarRestLocalQuat.set(name, ab.quaternion.clone());
}

// 3. Load and retarget all 29 motion-capture FBX clips onto Player_Mobile_Mesh's skeleton
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
  {
    clipName: "mocap_gk_idle",
    file: "Animations/Locomotion/Goalkeeper Idle Normal.fbx",
    maxDuration: 2.5,
  },
  {
    clipName: "mocap_gk_holding",
    file: "Animations/Locomotion/Goalkeeper Idle Holding.fbx",
    maxDuration: 2.2,
  },
  { clipName: "mocap_gk_sidestep", file: "Animations/Locomotion/Goalkeeper Sidestep.fbx" },
  { clipName: "mocap_gk_dive_high", file: "Animations/Locomotion/Goalkeeper Diving Save.fbx" },
  { clipName: "mocap_gk_dive_low", file: "Animations/Actions/GK BallSave Low.fbx" },
  { clipName: "mocap_gk_jump", file: "Animations/Actions/GKJump.fbx" },
  { clipName: "mocap_gk_drop_kick", file: "Animations/Actions/GK Drop Kick.fbx" },
  { clipName: "mocap_gk_miss", file: "Animations/Actions/GKMiss.fbx" },
];

const animatedBoneNames = [
  "Hips",
  "Spine",
  "Spine1",
  "Spine2",
  "Neck",
  "Head",
  "LeftShoulder",
  "LeftArm",
  "LeftForeArm",
  "LeftHand",
  "RightShoulder",
  "RightArm",
  "RightForeArm",
  "RightHand",
  "LeftUpLeg",
  "LeftLeg",
  "LeftFoot",
  "LeftToeBase",
  "RightUpLeg",
  "RightLeg",
  "RightFoot",
  "RightToeBase",
];

function retargetAndResampleClip(rawClip, targetName, maxDuration) {
  const duration = maxDuration ? Math.min(rawClip.duration, maxDuration) : rawClip.duration;

  // Reset avatar bones to rest pose
  for (const [name, ab] of avatarBonesByName.entries()) {
    ab.position.copy(avatarRestLocalPos.get(name));
    ab.quaternion.copy(avatarRestLocalQuat.get(name));
  }
  avatarRoot.updateMatrixWorld(true);

  const mixer = new THREE.AnimationMixer(avatarRoot);
  const action = mixer.clipAction(rawClip);
  action.play();

  // Sample at 24 Hz (plus exact endpoint)
  const sampleFps = 24;
  const numSteps = Math.max(2, Math.ceil(duration * sampleFps));
  const sampleTimes = [];
  for (let s = 0; s <= numSteps; s++) {
    sampleTimes.push(Number(Math.min(duration, (s / numSteps) * duration).toFixed(4)));
  }

  const hipsPositions = [];
  const quatValuesByBone = new Map();
  for (const name of animatedBoneNames) {
    quatValuesByBone.set(name, []);
  }

  let x0 = null;
  let z0 = null;
  const avatarHips = avatarBonesByName.get("Hips");

  // Keep a temporary clone of mesh bone world quaternions during parent-to-child evaluation
  const computedWorldQuats = new Map();

  for (const t of sampleTimes) {
    mixer.setTime(t);
    avatarRoot.updateMatrixWorld(true);

    if (x0 === null) {
      x0 = avatarHips.position.x;
      z0 = avatarHips.position.z;
    }

    const rawDx = avatarHips.position.x - x0;
    const rawDz = avatarHips.position.z - z0;
    // Scale vertical Hips height from Avatar rest (90cm) to Player_Mobile_Mesh bind (100cm)
    const scaledY = avatarHips.position.y * (100.0 / 90.0);
    const clampedX = Math.max(-12, Math.min(12, rawDx));
    const clampedZ = Math.max(-12, Math.min(12, rawDz));
    hipsPositions.push(
      Number(clampedX.toFixed(2)),
      Number(scaledY.toFixed(2)),
      Number(clampedZ.toFixed(2)),
    );

    computedWorldQuats.clear();
    for (const b of bones) {
      const ab = avatarBonesByName.get(b.name);
      if (!ab || !quatValuesByBone.has(b.name)) {
        const parentWq =
          b.parent && computedWorldQuats.has(b.parent.name)
            ? computedWorldQuats.get(b.parent.name)
            : new THREE.Quaternion();
        computedWorldQuats.set(b.name, parentWq.clone());
        continue;
      }

      const wqSrcAnim = new THREE.Quaternion();
      ab.getWorldQuaternion(wqSrcAnim);
      const wqAlignedInv = qSrcAligned.get(b.name).clone().invert();
      const wqDstTarget = wqSrcAnim.clone().multiply(wqAlignedInv).multiply(qDstBind.get(b.name));
      computedWorldQuats.set(b.name, wqDstTarget.clone());

      let localQuat = wqDstTarget.clone();
      if (b.parent && computedWorldQuats.has(b.parent.name)) {
        const parentWqInv = computedWorldQuats.get(b.parent.name).clone().invert();
        localQuat = parentWqInv.multiply(wqDstTarget);
      }
      localQuat.normalize();

      const arr = quatValuesByBone.get(b.name);
      if (arr.length === 0) {
        // Anchor frame 0 in the positive-w hemisphere (shortest path from bind pose [0,0,0,1])
        if (localQuat.w < 0) {
          localQuat.set(-localQuat.x, -localQuat.y, -localQuat.z, -localQuat.w);
        }
      } else {
        // Enforce C0 quaternion hemisphere continuity with previous keyframe
        const prevIdx = arr.length - 4;
        const dot =
          arr[prevIdx] * localQuat.x +
          arr[prevIdx + 1] * localQuat.y +
          arr[prevIdx + 2] * localQuat.z +
          arr[prevIdx + 3] * localQuat.w;
        if (dot < 0) {
          localQuat.set(-localQuat.x, -localQuat.y, -localQuat.z, -localQuat.w);
        }
      }

      arr.push(
        Number(localQuat.x.toFixed(4)),
        Number(localQuat.y.toFixed(4)),
        Number(localQuat.z.toFixed(4)),
        Number(localQuat.w.toFixed(4)),
      );
    }
  }

  mixer.stopAllAction();

  // Reset mesh bones to clean bind pose before export
  for (const b of bones) {
    b.quaternion.set(0, 0, 0, 1);
  }
  bones[0].position.set(0, 100, 0);
  playerRoot.updateMatrixWorld(true);

  const tracks = [new THREE.VectorKeyframeTrack("Hips.position", sampleTimes, hipsPositions)];
  for (const name of animatedBoneNames) {
    const qVals = quatValuesByBone.get(name);
    if (qVals && qVals.length === sampleTimes.length * 4) {
      tracks.push(new THREE.QuaternionKeyframeTrack(`${name}.quaternion`, sampleTimes, qVals));
    }
  }

  return new THREE.AnimationClip(targetName, duration, tracks);
}

const exportedClips = [];
for (const src of mocapSources) {
  const fullPath = path.join(sourceDir, src.file);
  const fbxObj = loadFBX(fullPath);
  if (fbxObj.animations && fbxObj.animations[0]) {
    const cleanClip = retargetAndResampleClip(fbxObj.animations[0], src.clipName, src.maxDuration);
    exportedClips.push(cleanClip);
  }
}

console.log(
  `Compiled and retargeted ${exportedClips.length} mocap clips from Avatar.fbx -> Player_Mobile_Mesh.fbx.`,
);

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
          `Verified GLB round-trip: SkinnedMesh=${verifiedSkinnedMesh?.name}, vertices=${verifiedSkinnedMesh?.geometry.attributes.position.count}, bones=${verifiedSkinnedMesh?.skeleton.bones.length}, animations=${gltf.animations.length}`,
        );
      },
      (err) => {
        console.error("GLTF verification failed:", err);
        process.exit(1);
      },
    );
  },
  (err) => {
    console.error("GLB export failed:", err);
    process.exit(1);
  },
  { binary: true, animations: exportedClips },
);
