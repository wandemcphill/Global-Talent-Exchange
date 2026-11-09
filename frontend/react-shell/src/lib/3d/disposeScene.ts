import * as THREE from "three";

const TEXTURE_KEYS = [
  "map",
  "normalMap",
  "roughnessMap",
  "metalnessMap",
  "emissiveMap",
  "aoMap",
  "alphaMap",
  "bumpMap",
  "displacementMap",
  "envMap",
  "lightMap",
  "specularMap",
] as const;

export function disposeMaterial(material: THREE.Material | null | undefined): void {
  if (!material) return;
  const matRecord = material as unknown as Record<string, unknown>;
  for (const key of TEXTURE_KEYS) {
    const tex = matRecord[key] as THREE.Texture | undefined;
    if (tex && typeof tex.dispose === "function") {
      try {
        tex.dispose();
      } catch {
        // Ignore already-disposed textures
      }
    }
  }
  if (typeof material.dispose === "function") {
    try {
      material.dispose();
    } catch {
      // Ignore already-disposed materials
    }
  }
}

/**
 * Traverses a Three.js Object3D or Scene, disposing all geometries, materials,
 * and attached textures, and optionally disposes the WebGLRenderer and removes
 * its canvas from the DOM.
 */
export function disposeScene(
  root: THREE.Object3D | null | undefined,
  renderer?: THREE.WebGLRenderer | null
): void {
  if (root) {
    root.traverse((obj) => {
      const mesh = obj as THREE.Mesh;
      if (mesh.geometry && typeof mesh.geometry.dispose === "function") {
        try {
          mesh.geometry.dispose();
        } catch {
          // Ignore
        }
      }
      const mat = (mesh as unknown as { material?: THREE.Material | THREE.Material[] }).material;
      if (Array.isArray(mat)) {
        mat.forEach((m) => disposeMaterial(m));
      } else if (mat) {
        disposeMaterial(mat);
      }
    });
    if (typeof root.clear === "function") {
      root.clear();
    }
  }

  if (renderer) {
    try {
      renderer.dispose();
    } catch {
      // Ignore
    }
    const domElement = renderer.domElement;
    if (domElement && domElement.parentNode) {
      domElement.parentNode.removeChild(domElement);
    }
  }
}
