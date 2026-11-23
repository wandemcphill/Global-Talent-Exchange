import {
  formatPlayerCalloutLabel,
  parseHexRgb,
  resolveDistinctKitPalette,
  rgbDistance,
  rgbLuma,
} from "./kitContrast";

describe("kitContrast and callout label hygiene", () => {
  test("separates clashing dark kits and lifts near-black jerseys to readable luminance", () => {
    const resolved = resolveDistinctKitPalette({
      homeColor: "#060912",
      awayColor: "#0c1220",
    });

    const homeRgb = parseHexRgb(resolved.homeColor);
    const awayRgb = parseHexRgb(resolved.awayColor);
    expect(rgbLuma(homeRgb)).toBeGreaterThanOrEqual(0.14);
    expect(rgbDistance(homeRgb, awayRgb)).toBeGreaterThanOrEqual(110);
    // Goalkeepers remain distinct from both outfield teams
    expect(rgbDistance(parseHexRgb(resolved.goalkeeperHome), homeRgb)).toBeGreaterThanOrEqual(85);
    expect(rgbDistance(parseHexRgb(resolved.goalkeeperAway), awayRgb)).toBeGreaterThanOrEqual(85);
  });

  test("preserves distinct club colors when they already contrast well", () => {
    const resolved = resolveDistinctKitPalette({
      homeColor: "#006633",
      awayColor: "#f8fafc",
    });
    expect(resolved.homeColor).toBe("#006633");
    expect(resolved.awayColor).toBe("#f8fafc");
  });

  test("formatPlayerCalloutLabel eliminates #7 7 and Unnamed duplicates", () => {
    expect(formatPlayerCalloutLabel(7, "7")).toBe("#7");
    expect(formatPlayerCalloutLabel(7, "#7")).toBe("#7");
    expect(formatPlayerCalloutLabel(7, "Unnamed")).toBe("#7");
    expect(formatPlayerCalloutLabel(7, "")).toBe("#7");
    expect(formatPlayerCalloutLabel(7, "Victor Osimhen")).toBe("#7 V. Osimhen");
    expect(formatPlayerCalloutLabel(10, "Saka")).toBe("#10 Saka");
  });
});
