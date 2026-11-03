/**
 * GTEX Skin Engine — Community Skin Package Specification (.gtexskin)
 * Declarative package definition with strict security sandboxing.
 *
 * NOTE: Community skin package installation is disabled by default for Phase 1
 * as mandated by GTEX security architecture directives.
 */

import { SkinManifest } from "./SkinManifest";

export const COMMUNITY_SKIN_INSTALLATION_ENABLED = false;

export interface CommunitySkinPackageManifest {
  format: "gtex-skin-declarative-v1";
  id: string;
  name: string;
  version: string;
  engineVersion: string;
  minAppVersion: string;
  author: {
    name: string;
    contact?: string;
  };
  description: string;
  license: string;
  tokens: SkinManifest["tokens"];
  assets?: Record<string, string>;
}

export interface SecurityScanResult {
  passed: boolean;
  violations: string[];
}

const FORBIDDEN_PATTERNS = [
  /<script/i,
  /javascript:/i,
  /eval\s*\(/i,
  /Function\s*\(/i,
  /<iframe/i,
  /onload\s*=/i,
  /onerror\s*=/i,
  /expression\s*\(/i,
  /behavior\s*:/i,
  /url\s*\(\s*['"]?https?:\/\/(?!res\.cloudinary\.com)/i, // No arbitrary external URLs
];

export function scanDeclarativeManifestSecurity(manifestJson: string): SecurityScanResult {
  const violations: string[] = [];

  for (const pattern of FORBIDDEN_PATTERNS) {
    if (pattern.test(manifestJson)) {
      violations.push(`Forbidden executable or non-allowlisted resource pattern detected: ${pattern}`);
    }
  }

  return {
    passed: violations.length === 0,
    violations,
  };
}
