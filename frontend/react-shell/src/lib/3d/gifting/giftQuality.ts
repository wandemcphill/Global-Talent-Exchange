export interface GiftQuality {
  tier: "high" | "medium" | "low";
  pixelRatioCap: number;
  shadows: boolean;
  crowd: number;
  particles: number;
  antialias: boolean;
}

export function detectGiftQuality(width: number, cores = 8): GiftQuality {
  if (width < 760 || cores <= 4) {
    return { tier: "low", pixelRatioCap: 1, shadows: false, crowd: 48, particles: 36, antialias: false };
  }
  if (width < 1180) {
    return { tier: "medium", pixelRatioCap: 1.25, shadows: false, crowd: 120, particles: 70, antialias: true };
  }
  return { tier: "high", pixelRatioCap: 1.5, shadows: true, crowd: 220, particles: 120, antialias: true };
}
