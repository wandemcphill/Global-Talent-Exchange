/**
 * GTEX Skin Engine — Approved Graphical Asset Pack Loader
 * Layer 4 decorative assets with strict canonical game asset protection.
 */

export interface AssetPack {
  id: string;
  name: string;
  description: string;
  category: "textures" | "stadiums" | "pitch" | "minimal";
  cssClass: string;
  isDefault?: boolean;
}

export const APPROVED_ASSET_PACKS: AssetPack[] = [
  {
    id: "pack-pitch-grid",
    name: "Tactical Pitch Grid",
    description: "Subtle emerald tactical pitch coordinates and tactical grid lines.",
    category: "pitch",
    cssClass: "gx-pitch-grid",
    isDefault: true,
  },
  {
    id: "pack-stadium-lights",
    name: "Stadium Floodlights",
    description: "Soft atmospheric stadium floodlight gradients and ambient illumination.",
    category: "stadiums",
    cssClass: "gx-stadium-lights",
  },
  {
    id: "pack-carbon-mesh",
    name: "Obsidian Carbon Mesh",
    description: "High-tech composite carbon grain for sleek executive surfaces.",
    category: "textures",
    cssClass: "gx-noise",
  },
  {
    id: "pack-minimal-clean",
    name: "Minimal Clean Canvas",
    description: "Zero decorative overlays. Maximum performance and clean readability.",
    category: "minimal",
    cssClass: "gx-minimal-clean",
  },
];

/**
 * Strict canonical asset protection validator.
 * Skins may alter the styling/frame of an asset container, but MUST NOT replace,
 * intercept, or remap authoritative player/club/national assets.
 */
export const PROTECTED_ASSET_INDICATORS = [
  "cloudinary.com",
  "sportmonks.com",
  "facebank",
  "regen_newgen_faces",
  "regen_portraits",
  "legend_portraits",
  "club_crest",
  "national_flag",
  "/avatars/",
  "/portraits/",
];

export function isCanonicalProtectedAsset(assetUrl?: string | null): boolean {
  if (!assetUrl || typeof assetUrl !== "string") return false;
  const lower = assetUrl.toLowerCase();
  return PROTECTED_ASSET_INDICATORS.some((indicator) => lower.includes(indicator));
}

export function getApprovedAssetPack(packId: string): AssetPack {
  return (
    APPROVED_ASSET_PACKS.find((p) => p.id === packId) ||
    APPROVED_ASSET_PACKS[0]
  );
}
