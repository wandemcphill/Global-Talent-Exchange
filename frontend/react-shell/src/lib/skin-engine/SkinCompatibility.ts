/**
 * GTEX Skin Engine — Compatibility & Fallback Verification
 * Ensures installed skins meet schema integrity and provides graceful fallbacks.
 */

import { SkinManifest } from "./SkinManifest";
import { GTEX_MATCHDAY_SKIN, SkinRegistry } from "./SkinRegistry";

export const SKIN_ENGINE_VERSION = "1.0.0";
export const MIN_SUPPORTED_ENGINE_VERSION = "1.0.0";

export interface CompatibilityReport {
  compatible: boolean;
  skinId: string;
  errors: string[];
  warnings: string[];
}

const REQUIRED_TOKENS: (keyof SkinManifest["tokens"])[] = [
  "surfaceApp",
  "surfacePanel",
  "surfaceCard",
  "surfaceInput",
  "textPrimary",
  "textSecondary",
  "borderSubtle",
  "actionPrimaryBg",
  "actionPrimaryText",
  "statusSuccess",
  "statusWarning",
  "statusDanger",
  "footballPitch",
  "adsSurface",
  "adsBorder",
];

export function validateSkinManifest(skin?: any): CompatibilityReport {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!skin || typeof skin !== "object") {
    return {
      compatible: false,
      skinId: "unknown",
      errors: ["Skin manifest is missing or not a valid object"],
      warnings: [],
    };
  }

  const skinId = typeof skin.id === "string" ? skin.id : "invalid-id";

  if (!skin.id || typeof skin.id !== "string") {
    errors.push("Missing required field: id");
  }
  if (!skin.name || typeof skin.name !== "string") {
    errors.push("Missing required field: name");
  }
  if (!skin.tokens || typeof skin.tokens !== "object") {
    errors.push("Missing required tokens object");
  } else {
    for (const requiredToken of REQUIRED_TOKENS) {
      if (!skin.tokens[requiredToken] || typeof skin.tokens[requiredToken] !== "string") {
        errors.push(`Missing mandatory design token: ${requiredToken}`);
      }
    }
  }

  // Version compatibility checks
  if (skin.engineVersion && skin.engineVersion !== SKIN_ENGINE_VERSION) {
    warnings.push(
      `Skin engine version '${skin.engineVersion}' differs from runtime engine '${SKIN_ENGINE_VERSION}'`,
    );
  }

  return {
    compatible: errors.length === 0,
    skinId,
    errors,
    warnings,
  };
}

/**
 * Resolves a safe skin, falling back to GTEX Matchday if the requested skin is
 * missing, unverified, or incompatible.
 */
export function resolveSafeSkin(requestedSkinId?: string | null): SkinManifest {
  if (!requestedSkinId) {
    return GTEX_MATCHDAY_SKIN;
  }

  const registered = SkinRegistry.get(requestedSkinId);
  if (!registered) {
    return GTEX_MATCHDAY_SKIN;
  }

  const validation = validateSkinManifest(registered);
  if (!validation.compatible) {
    // eslint-disable-next-line no-console
    console.warn(
      `Skin '${requestedSkinId}' failed compatibility check. Restoring reference Matchday skin.`,
      validation.errors,
    );
    return GTEX_MATCHDAY_SKIN;
  }

  return registered;
}
