import { useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { clone as cloneSkinned } from "three/examples/jsm/utils/SkeletonUtils.js";
import { disposeScene } from "@/lib/3d/disposeScene";
import { kitSwatchDataUri, type KitVariant } from "./clubIdentityDefaults";

type JerseyTurntableProps = {
  kit: KitVariant;
  crestDataUri?: string | null;
  chestText: string;
};

const KIT_MODEL_URL = "/models/footballer/gtex_gt_mixamo_kit.glb?kit=1";

let kitTemplate: Promise<THREE.Group> | null = null;

function loadKitTemplate(): Promise<THREE.Group> {
  if (!kitTemplate) {
    kitTemplate = new Promise((resolve, reject) => {
      new GLTFLoader().load(
        KIT_MODEL_URL,
        (gltf) => resolve(gltf.scene),
        undefined,
        () => {
          kitTemplate = null;
          reject(new Error("kit model failed"));
        },
      );
    });
  }
  return kitTemplate;
}

function boneKey(name: string): string {
  return name.replace(/[^a-z0-9]/gi, "").toLowerCase();
}

function findBone(root: THREE.Object3D, suffix: string): THREE.Object3D | null {
  const needle = boneKey(suffix);
  let found: THREE.Object3D | null = null;
  root.traverse((obj) => {
    if (!found && obj.name && boneKey(obj.name) === needle) found = obj;
  });
  return found;
}

function hangSleeves(root: THREE.Object3D, style: string): void {
  const drop = style === "long" ? 1.05 : style === "raglan" ? 0.25 : 0.55;
  const left = findBone(root, "mixamorigLeftArm");
  const right = findBone(root, "mixamorigRightArm");
  if (left) left.rotateX(drop);
  if (right) right.rotateX(drop);
}

function patternCode(pattern: string): number {
  if (pattern === "stripes") return 1;
  if (pattern === "hoops") return 2;
  if (pattern === "sash") return 3;
  if (pattern === "chevron") return 4;
  if (pattern === "gradient") return 5;
  return 0;
}

function patternedCloth(
  primary: string,
  secondary: string,
  pattern: string,
  freq: THREE.Vector2,
  chestMark: THREE.Texture,
): THREE.MeshStandardMaterial {
  const material = new THREE.MeshStandardMaterial({
    color: primary,
    roughness: 0.62,
    metalness: 0.02,
    side: THREE.DoubleSide,
  });
  const code = patternCode(pattern);
  material.defines = { USE_UV: "" };
  material.onBeforeCompile = (shader) => {
    shader.uniforms.uSecondary = { value: new THREE.Color(secondary) };
    shader.uniforms.uPattern = { value: code };
    shader.uniforms.uFreq = { value: freq };
    shader.uniforms.uChestMark = { value: chestMark };
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", "#include <common>\nvarying vec3 vChestPos;")
      .replace("#include <begin_vertex>", "vChestPos = position;\n#include <begin_vertex>");
    shader.fragmentShader = shader.fragmentShader
      .replace(
        "#include <common>",
        "#include <common>\nuniform vec3 uSecondary;\nuniform float uPattern;\nuniform vec2 uFreq;\nuniform sampler2D uChestMark;\nvarying vec3 vChestPos;",
      )
      .replace(
        "#include <color_fragment>",
        `#include <color_fragment>
        vec3 alt = uSecondary;
        float stripe = step(0.5, fract(vUv.x * uFreq.x));
        float hoop = step(0.55, fract(vUv.y * uFreq.y));
        float sash = step(0.35, fract((vUv.x + vUv.y) * uFreq.x));
        float chev = step(0.5, fract(abs(vUv.x - 0.5) * uFreq.x + vUv.y * uFreq.y));
        vec3 base = diffuseColor.rgb;
        if (uPattern > 0.5 && uPattern < 1.5) diffuseColor.rgb = mix(base, alt, stripe);
        else if (uPattern > 1.5 && uPattern < 2.5) diffuseColor.rgb = mix(base, alt, hoop);
        else if (uPattern > 2.5 && uPattern < 3.5) diffuseColor.rgb = mix(base, alt, sash);
        else if (uPattern > 3.5 && uPattern < 4.5) diffuseColor.rgb = mix(base, alt, chev);
        else if (uPattern > 4.5 && uPattern < 5.5) {
          float fade = clamp(vUv.y, 0.0, 1.0);
          diffuseColor.rgb = mix(base, alt, fade);
        }
        vec2 markUv = vec2((vChestPos.x + 0.09) / 0.20, (vChestPos.y - 1.20) / 0.18);
        float onFront = step(0.105, vChestPos.z);
        float inside = step(0.0, markUv.x) * step(markUv.x, 1.0) * step(0.0, markUv.y) * step(markUv.y, 1.0);
        vec4 mark = texture2D(uChestMark, clamp(markUv, 0.0, 1.0));
        diffuseColor.rgb = mix(diffuseColor.rgb, mark.rgb, mark.a * onFront * inside);`,
      );
  };
  material.customProgramCacheKey = () => `gtex-kit-${material.uuid}`;
  return material;
}

const PREVIEW_SQUAD_NUMBER = "10";

function paintChestMark(canvas: HTMLCanvasElement, text: string, crest: HTMLImageElement | null): void {
  const context = canvas.getContext("2d");
  if (!context) return;
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.fillStyle = "#0B1220";
  context.fillRect(24, 370, 520, 300);
  context.fillStyle = "#F8FAFC";
  context.strokeStyle = "#111827";
  context.lineWidth = 16;
  context.lineJoin = "round";
  context.textAlign = "center";
  context.textBaseline = "middle";
  context.font = `900 ${text.length > 12 ? 64 : text.length > 8 ? 88 : 108}px Arial`;
  context.strokeText(text, 284, 520);
  context.fillText(text, 284, 520);
  if (crest) {
    context.drawImage(crest, 620, 280, 380, 460);
  }
}

function paintSquadNumber(canvas: HTMLCanvasElement, number: string): void {
  const context = canvas.getContext("2d");
  if (!context) return;
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.fillStyle = "#F8FAFC";
  context.strokeStyle = "#111827";
  context.lineWidth = 36;
  context.lineJoin = "round";
  context.textAlign = "center";
  context.textBaseline = "middle";
  context.font = `900 ${number.length > 1 ? 340 : 420}px Arial`;
  context.strokeText(number, canvas.width / 2, canvas.height / 2);
  context.fillText(number, canvas.width / 2, canvas.height / 2);
}

function paintRoundCrest(canvas: HTMLCanvasElement, crest: HTMLImageElement | null): void {
  const context = canvas.getContext("2d");
  if (!context) return;
  const size = canvas.width;
  context.clearRect(0, 0, size, size);
  context.save();
  context.beginPath();
  context.arc(size / 2, size / 2, size / 2 - 18, 0, Math.PI * 2);
  context.clip();
  if (crest) {
    context.drawImage(crest, 28, 28, size - 56, size - 56);
  } else {
    context.fillStyle = "#0B1220";
    context.fillRect(0, 0, size, size);
  }
  context.restore();
  context.beginPath();
  context.arc(size / 2, size / 2, size / 2 - 20, 0, Math.PI * 2);
  context.lineWidth = 28;
  context.strokeStyle = "#F8FAFC";
  context.stroke();
}

function markTexture(size: number, paint: (canvas: HTMLCanvasElement) => void): { texture: THREE.CanvasTexture; canvas: HTMLCanvasElement } {
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  paint(canvas);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.needsUpdate = true;
  return { texture, canvas };
}

function shortsCloth(
  primary: string,
  secondary: string,
  accent: string,
  pattern: string,
  squadNumber: THREE.Texture,
  crest: THREE.Texture,
): THREE.MeshStandardMaterial {
  const material = new THREE.MeshStandardMaterial({
    color: primary,
    roughness: 0.64,
    metalness: 0.02,
    side: THREE.DoubleSide,
  });
  const code = patternCode(pattern);
  material.onBeforeCompile = (shader) => {
    shader.uniforms.uSecondary = { value: new THREE.Color(secondary) };
    shader.uniforms.uAccent = { value: new THREE.Color(accent) };
    shader.uniforms.uPattern = { value: code };
    shader.uniforms.uNumber = { value: squadNumber };
    shader.uniforms.uCrest = { value: crest };
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", "#include <common>\nvarying vec3 vShortPos;")
      .replace("#include <begin_vertex>", "vShortPos = position;\n#include <begin_vertex>");
    shader.fragmentShader = shader.fragmentShader
      .replace(
        "#include <common>",
        "#include <common>\nuniform vec3 uSecondary;\nuniform vec3 uAccent;\nuniform float uPattern;\nuniform sampler2D uNumber;\nuniform sampler2D uCrest;\nvarying vec3 vShortPos;",
      )
      .replace(
        "#include <color_fragment>",
        `#include <color_fragment>
        float side = step(0.145, abs(vShortPos.x));
        float hem = step(vShortPos.y, 0.63) * step(0.57, vShortPos.y);
        float hoop = step(0.70, vShortPos.y) * step(vShortPos.y, 0.76);
        float sash = step(0.45, fract(vShortPos.x * 3.0 + vShortPos.y * 2.0));
        diffuseColor.rgb = mix(diffuseColor.rgb, uSecondary, side);
        if (uPattern > 1.5 && uPattern < 2.5) diffuseColor.rgb = mix(diffuseColor.rgb, uSecondary, hoop);
        else if (uPattern > 2.5 && uPattern < 4.5) diffuseColor.rgb = mix(diffuseColor.rgb, uSecondary, sash * step(0.08, vShortPos.z));
        else if (uPattern > 4.5) diffuseColor.rgb = mix(diffuseColor.rgb, uSecondary, clamp((0.85 - vShortPos.y) * 2.2, 0.0, 1.0));
        diffuseColor.rgb = mix(diffuseColor.rgb, uAccent, hem);
        float front = step(0.085, vShortPos.z);
        vec2 numUv = vec2((vShortPos.x + 0.175) / 0.14, (vShortPos.y - 0.60) / 0.22);
        float numInside = step(0.0, numUv.x) * step(numUv.x, 1.0) * step(0.0, numUv.y) * step(numUv.y, 1.0);
        vec4 num = texture2D(uNumber, clamp(numUv, 0.0, 1.0));
        diffuseColor.rgb = mix(diffuseColor.rgb, num.rgb, num.a * numInside * front);
        vec2 crestUv = vec2((vShortPos.x - 0.035) / 0.14, (vShortPos.y - 0.62) / 0.18);
        float crestInside = step(0.0, crestUv.x) * step(crestUv.x, 1.0) * step(0.0, crestUv.y) * step(crestUv.y, 1.0);
        vec4 badge = texture2D(uCrest, clamp(crestUv, 0.0, 1.0));
        diffuseColor.rgb = mix(diffuseColor.rgb, badge.rgb, badge.a * crestInside * front);`,
      );
  };
  material.customProgramCacheKey = () => `gtex-shorts-${material.uuid}`;
  return material;
}

function sockCloth(socks: string, secondary: string, accent: string): THREE.MeshStandardMaterial {
  const material = new THREE.MeshStandardMaterial({
    color: "#C4A484",
    roughness: 0.72,
    metalness: 0.0,
    side: THREE.DoubleSide,
  });
  material.onBeforeCompile = (shader) => {
    shader.uniforms.uSock = { value: new THREE.Color(socks) };
    shader.uniforms.uSecondary = { value: new THREE.Color(secondary) };
    shader.uniforms.uAccent = { value: new THREE.Color(accent) };
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", "#include <common>\nvarying vec3 vLegPos;")
      .replace("#include <begin_vertex>", "vLegPos = position;\n#include <begin_vertex>");
    shader.fragmentShader = shader.fragmentShader
      .replace(
        "#include <common>",
        "#include <common>\nuniform vec3 uSock;\nuniform vec3 uSecondary;\nuniform vec3 uAccent;\nvarying vec3 vLegPos;",
      )
      .replace(
        "#include <color_fragment>",
        `#include <color_fragment>
        float sock = step(0.09, vLegPos.y) * step(vLegPos.y, 0.54);
        float cuff = step(0.46, vLegPos.y) * step(vLegPos.y, 0.54);
        float hoop = step(0.36, vLegPos.y) * step(vLegPos.y, 0.41);
        float boot = step(vLegPos.y, 0.09);
        vec3 cloth = uSock;
        cloth = mix(cloth, uSecondary, hoop);
        cloth = mix(cloth, uAccent, cuff);
        diffuseColor.rgb = mix(diffuseColor.rgb, cloth, sock);
        diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.09, 0.08, 0.07), boot);`,
      );
  };
  material.customProgramCacheKey = () => `gtex-sock-${material.uuid}`;
  return material;
}

function partName(mesh: THREE.Mesh): string {
  const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
  return materials.map((material) => material.name || "").join(" ").toLowerCase();
}

function isGarment(name: string): boolean {
  return name.includes("tshirt") || name.includes("shirt") || name.includes("short");
}

export function JerseyTurntable({ kit, crestDataUri, chestText }: JerseyTurntableProps) {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const shirtRef = useRef<THREE.Group | null>(null);
  const draggingRef = useRef(false);
  const lastXRef = useRef(0);
  const [fallback, setFallback] = useState(false);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;
    const width = mount.clientWidth || 420;
    const height = mount.clientHeight || 320;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(30, width / height, 0.1, 40);
    camera.position.set(0, 0.05, 4.2);
    camera.lookAt(0, -0.05, 0);

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    } catch {
      setFallback(true);
      return;
    }
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    mount.appendChild(renderer.domElement);

    scene.add(new THREE.AmbientLight(0xffffff, 0.9));
    const key = new THREE.DirectionalLight(0xffffff, 1.45);
    key.position.set(2.2, 3.4, 4.2);
    scene.add(key);
    const rim = new THREE.DirectionalLight(0xdbeafe, 0.55);
    rim.position.set(-3.2, 1.6, -2);
    scene.add(rim);

    const shirt = new THREE.Group();
    shirt.rotation.y = 0.28;
    shirtRef.current = shirt;
    scene.add(shirt);

    const reducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
    let frame = 0;
    const render = () => {
      if (!draggingRef.current && !reducedMotion && !mount.matches(":hover")) shirt.rotation.y += 0.003;
      if (typeof document === "undefined" || !document.hidden) renderer.render(scene, camera);
      frame = requestAnimationFrame(render);
    };
    render();

    const onResize = () => {
      const nextWidth = mount.clientWidth || width;
      const nextHeight = mount.clientHeight || height;
      camera.aspect = nextWidth / nextHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(nextWidth, nextHeight);
    };
    window.addEventListener("resize", onResize);

    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", onResize);
      shirtRef.current = null;
      disposeScene(scene, renderer);
    };
  }, []);

  useEffect(() => {
    const shirt = shirtRef.current;
    if (!shirt) return;
    let cancelled = false;
    const added: THREE.Object3D[] = [];
    const marks: THREE.Texture[] = [];

    loadKitTemplate()
      .then((template) => {
        if (cancelled || shirtRef.current !== shirt) return;
        const root = cloneSkinned(template);
        root.traverse((obj) => {
          const mesh = obj as THREE.SkinnedMesh;
          if (!mesh.isMesh) return;
          mesh.geometry = mesh.geometry.clone();
          mesh.visible = true;
          mesh.frustumCulled = false;
        });
        hangSleeves(root, kit.sleeve_style);
        root.rotation.y = -Math.PI / 2;
        root.updateMatrixWorld(true);
        const freq = new THREE.Vector2(7, 5);
        const chest = markTexture(1024, (canvas) => paintChestMark(canvas, chestText, null));
        const number = markTexture(512, (canvas) => paintSquadNumber(canvas, PREVIEW_SQUAD_NUMBER));
        const badge = markTexture(512, (canvas) => paintRoundCrest(canvas, null));
        if (crestDataUri) {
          const image = new Image();
          image.onload = () => {
            paintChestMark(chest.canvas, chestText, image);
            paintRoundCrest(badge.canvas, image);
            chest.texture.needsUpdate = true;
            badge.texture.needsUpdate = true;
          };
          image.src = crestDataUri;
        }
        const shirtMaterial = patternedCloth(kit.primary_color, kit.secondary_color, kit.pattern_type, freq, chest.texture);
        const shortsMaterial = shortsCloth(
          kit.shorts_color || kit.primary_color,
          kit.secondary_color,
          kit.accent_color,
          kit.pattern_type,
          number.texture,
          badge.texture,
        );
        const socksMaterial = sockCloth(kit.socks_color || kit.secondary_color, kit.secondary_color, kit.accent_color);
        root.traverse((obj) => {
          const mesh = obj as THREE.Mesh;
          if (!mesh.isMesh || !mesh.visible) return;
          const label = partName(mesh);
          if (label.includes("short")) mesh.material = shortsMaterial;
          else if (label.includes("tshirt") || label.includes("shirt")) mesh.material = shirtMaterial;
          else if (label.includes("leg")) mesh.material = socksMaterial;
        });

        const fitted = new THREE.Box3().setFromObject(root);
        const fittedSize = fitted.getSize(new THREE.Vector3());
        const chestY = fitted.min.y + fittedSize.y * 0.62;
        const scale = 2.4 / Math.max(fittedSize.y, 0.01);
        root.scale.setScalar(scale);
        root.position.set(-fitted.getCenter(new THREE.Vector3()).x * scale, -chestY * scale, -fitted.getCenter(new THREE.Vector3()).z * scale);
        shirt.add(root);
        root.updateMatrixWorld(true);
        draggingRef.current = false;
        shirt.rotation.set(0, Math.PI - 1.15, 0);
        marks.push(chest.texture, number.texture, badge.texture);
        added.push(root);
      })
      .catch(() => {
        if (!cancelled) setFallback(true);
      });

    return () => {
      cancelled = true;
      marks.forEach((mark) => mark.dispose());
      added.forEach((object) => {
        shirt.remove(object);
        object.traverse((child) => {
          const mesh = child as THREE.Mesh;
          if (!mesh.isMesh) return;
          mesh.geometry?.dispose();
          const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
          materials.forEach((material) => {
            const mapped = material as THREE.MeshStandardMaterial;
            mapped.map?.dispose();
            material.dispose();
          });
        });
      });
    };
  }, [kit, crestDataUri, chestText]);

  const onPointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    draggingRef.current = true;
    lastXRef.current = event.clientX;
    event.currentTarget.setPointerCapture(event.pointerId);
  };
  const onPointerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (!draggingRef.current || !shirtRef.current) return;
    const delta = event.clientX - lastXRef.current;
    lastXRef.current = event.clientX;
    shirtRef.current.rotation.y += delta * 0.012;
  };
  const onPointerUp = () => {
    draggingRef.current = false;
  };

  return (
    <div className="relative h-80 w-full overflow-hidden rounded border border-white/10 bg-slate-950/80">
      {fallback ? (
        <img src={kitSwatchDataUri(kit)} alt={`${kit.jersey_type} kit`} className="mx-auto h-full object-contain" />
      ) : (
        <div
          ref={mountRef}
          className="h-full w-full cursor-grab touch-none active:cursor-grabbing"
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerCancel={onPointerUp}
          aria-label="3D jersey preview"
          data-testid="jersey-turntable"
        />
      )}
    </div>
  );
}
