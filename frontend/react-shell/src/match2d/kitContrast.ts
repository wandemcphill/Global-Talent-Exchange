/**
 * Broadcast kit contrast, sRGB color parsing, and player callout formatting utilities.
 * Isolated from OrthographicPitch so tests mocking WebGL/OrthographicPitch still resolve
 * live kit palettes cleanly.
 */

export function parseHexRgb(
  hex: string,
  fallback: [number, number, number] = [0, 232, 122],
): [number, number, number] {
  const cleaned = String(hex || "").trim().replace(/^#/, "");
  if (!/^[0-9a-fA-F]{3}([0-9a-fA-F]{3})?$/.test(cleaned)) return fallback;
  const full =
    cleaned.length === 3
      ? cleaned
          .split("")
          .map((c) => c + c)
          .join("")
      : cleaned;
  return [
    parseInt(full.slice(0, 2), 16),
    parseInt(full.slice(2, 4), 16),
    parseInt(full.slice(4, 6), 16),
  ];
}

export function rgbToHex(r: number, g: number, b: number): string {
  const clamp = (n: number) =>
    Math.max(0, Math.min(255, Math.round(n)))
      .toString(16)
      .padStart(2, "0");
  return `#${clamp(r)}${clamp(g)}${clamp(b)}`;
}

export function rgbLuma([r, g, b]: [number, number, number]): number {
  return (0.299 * r + 0.587 * g + 0.114 * b) / 255;
}

export function rgbDistance(
  a: [number, number, number],
  b: [number, number, number],
): number {
  const dr = a[0] - b[0];
  const dg = a[1] - b[1];
  const db = a[2] - b[2];
  return Math.sqrt(dr * dr * 0.3 + dg * dg * 0.59 + db * db * 0.11) * 1.732;
}

function liftDarkKitHex(hex: string, fallback: [number, number, number]): string {
  const rgb = parseHexRgb(hex, fallback);
  const luma = rgbLuma(rgb);
  if (luma >= 0.14) return rgbToHex(rgb[0], rgb[1], rgb[2]);
  const boost = 46;
  return rgbToHex(rgb[0] + boost, rgb[1] + boost + 8, rgb[2] + boost + 18);
}

const AWAY_CLASH_CANDIDATES = ["#f8fafc", "#ef4444", "#f59e0b", "#2563eb", "#14b8a6"];
const GK_CANDIDATES = ["#f59e0b", "#06b6d4", "#ec4899", "#a3e635", "#fde047"];
const PITCH_GREEN_RGB: [number, number, number] = [31, 122, 69];

export function resolveDistinctKitPalette(input: {
  homeColor: string;
  awayColor: string;
  homeShortsColor?: string;
  awayShortsColor?: string;
  homeSocksColor?: string;
  awaySocksColor?: string;
  goalkeeperHome?: string;
  goalkeeperAway?: string;
}): {
  homeColor: string;
  awayColor: string;
  homeShortsColor: string;
  awayShortsColor: string;
  homeSocksColor: string;
  awaySocksColor: string;
  goalkeeperHome: string;
  goalkeeperAway: string;
} {
  const homeColor = liftDarkKitHex(input.homeColor, [16, 185, 129]);
  const homeRgb = parseHexRgb(homeColor, [16, 185, 129]);
  let awayColor = liftDarkKitHex(input.awayColor, [248, 250, 252]);
  let awayRgb = parseHexRgb(awayColor, [248, 250, 252]);

  const homeLuma = rgbLuma(homeRgb);
  const awayLuma = rgbLuma(awayRgb);
  const teamsTooClose =
    rgbDistance(homeRgb, awayRgb) < 110 ||
    (homeLuma < 0.25 && awayLuma < 0.25) ||
    (homeLuma > 0.78 && awayLuma > 0.78);

  if (teamsTooClose) {
    let bestHex = AWAY_CLASH_CANDIDATES[0];
    let bestScore = -Infinity;
    for (const candidate of AWAY_CLASH_CANDIDATES) {
      const cRgb = parseHexRgb(candidate);
      const score =
        rgbDistance(homeRgb, cRgb) * 1.3 +
        Math.abs(homeLuma - rgbLuma(cRgb)) * 180 +
        rgbDistance(PITCH_GREEN_RGB, cRgb) * 0.45;
      if (score > bestScore) {
        bestScore = score;
        bestHex = candidate;
      }
    }
    awayColor = bestHex;
    awayRgb = parseHexRgb(awayColor);
  }

  const pickDistinctGk = (
    preferred: string | undefined,
    avoid: [number, number, number][],
  ) => {
    const base = preferred ? liftDarkKitHex(preferred, [245, 158, 11]) : "";
    if (base) {
      const bRgb = parseHexRgb(base);
      if (avoid.every((a) => rgbDistance(a, bRgb) >= 92)) return base;
    }
    let best = GK_CANDIDATES[0];
    let bestMinDist = -1;
    for (const candidate of GK_CANDIDATES) {
      const cRgb = parseHexRgb(candidate);
      const minDist = Math.min(...avoid.map((a) => rgbDistance(a, cRgb)));
      if (minDist > bestMinDist) {
        bestMinDist = minDist;
        best = candidate;
      }
    }
    return best;
  };

  const goalkeeperHome = pickDistinctGk(input.goalkeeperHome, [
    homeRgb,
    awayRgb,
    PITCH_GREEN_RGB,
  ]);
  const gkHomeRgb = parseHexRgb(goalkeeperHome);
  const goalkeeperAway = pickDistinctGk(input.goalkeeperAway, [
    homeRgb,
    awayRgb,
    gkHomeRgb,
    PITCH_GREEN_RGB,
  ]);

  const homeShortsColor =
    input.homeShortsColor || (homeLuma > 0.65 ? "#0f172a" : "#f8fafc");
  const awayShortsColor = teamsTooClose
    ? rgbLuma(awayRgb) > 0.65
      ? "#1e293b"
      : "#f8fafc"
    : input.awayShortsColor || (rgbLuma(awayRgb) > 0.65 ? "#1e293b" : "#f8fafc");

  return {
    homeColor,
    awayColor,
    homeShortsColor,
    awayShortsColor,
    homeSocksColor: input.homeSocksColor || homeColor,
    awaySocksColor: teamsTooClose ? awayColor : input.awaySocksColor || awayColor,
    goalkeeperHome,
    goalkeeperAway,
  };
}

export function shortPlayerDisplayName(name: string): string {
  const trimmed = String(name || "").trim();
  if (!trimmed) return "";
  const parts = trimmed.split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 12);
  return `${parts[0][0]}. ${parts[parts.length - 1]}`.slice(0, 14);
}

export function formatPlayerCalloutLabel(
  shirtNumber?: number | null,
  name?: string | null,
): string {
  const num =
    Number.isFinite(Number(shirtNumber)) && Number(shirtNumber) > 0
      ? Math.round(Number(shirtNumber))
      : 0;
  const raw = String(name || "").trim();
  const lowered = raw.toLowerCase();
  const isRedundantName =
    !raw ||
    lowered === "unnamed" ||
    lowered === "unknown" ||
    lowered === "player" ||
    /^#?\d+$/.test(raw) ||
    (num > 0 && raw === String(num));
  const cleanedName = isRedundantName ? "" : shortPlayerDisplayName(raw);
  if (num > 0 && cleanedName) return `#${num} ${cleanedName}`;
  if (cleanedName) return cleanedName;
  if (num > 0) return `#${num}`;
  return "";
}
