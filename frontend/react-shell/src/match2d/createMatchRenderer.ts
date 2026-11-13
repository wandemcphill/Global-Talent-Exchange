import * as THREE from "three";

export function createMatchRenderer() {
  return new THREE.WebGLRenderer({ antialias: true, alpha: false });
}
