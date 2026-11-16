declare const describe: any;
declare const test: any;
declare const expect: any;

import {
  buildClubDNA,
  buildCrestLibrary,
  buildKitSet,
  clubShortCode,
  KIT_PRESETS,
  kitSwatchDataUri,
} from "./clubIdentityDefaults";

describe("bundled club identity defaults", () => {
  test("provides 72 deterministic crest options with SVG previews", () => {
    const crests = buildCrestLibrary("Ikorodu City FC");
    expect(crests).toHaveLength(72);
    expect(new Set(crests.map((crest) => crest.concept_id)).size).toBe(72);
    expect(new Set(crests.map((crest) => crest.shape))).toEqual(
      new Set(["shield", "round", "diamond", "pennant"]),
    );
    expect(new Set(crests.map((crest) => crest.icon_family))).toEqual(
      new Set(["lion", "eagle", "crown", "star", "oak", "bolt"]),
    );
    expect(crests.every((crest) => crest.initials === "ICFC")).toBe(true);
    expect(crests.every((crest) => crest.svg_markup.startsWith("<svg"))).toBe(true);
    expect(crests.every((crest) => crest.data_uri.startsWith("data:image/svg+xml"))).toBe(true);
  });

  test("provides 16 complete home, away, third and goalkeeper kit presets", () => {
    expect(KIT_PRESETS).toHaveLength(16);
    const shortCode = clubShortCode("Ikorodu City FC");
    expect(shortCode).toBe("ICFC");
    for (const preset of KIT_PRESETS) {
      const kitSet = buildKitSet(preset.id, shortCode);
      expect(Object.keys(kitSet).sort()).toEqual(["away", "goalkeeper", "home", "third"]);
      expect(kitSet.home.jersey_type).toBe("home");
      expect(kitSet.away.jersey_type).toBe("away");
      expect(kitSet.third.jersey_type).toBe("third");
      expect(kitSet.goalkeeper.jersey_type).toBe("goalkeeper");
      expect(kitSet.home.front_text).toBe(shortCode);
      expect(kitSet.third.front_text).toBe(`${shortCode} ALT`);
      expect(kitSwatchDataUri(kitSet.home)).toMatch(/^data:image\\/svg\\+xml/);
    }
  });

  test("builds club DNA locally without a generated recommendation", () => {
    const dna = buildClubDNA("Ikorodu City FC", "Ikorodu", "NG", "balanced", "U23", "preferred");
    expect(dna.primary_philosophy).toBe("balanced");
    expect(dna.nationality_mode).toBe("preferred");
    expect(dna.target_nationalities).toEqual(["NG"]);
    expect(dna.preferred_max_age).toBe(23);
    expect(dna.vision_narrative).toContain("Ikorodu City FC");
  });
});
