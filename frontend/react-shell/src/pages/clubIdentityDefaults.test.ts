declare const describe: any;
declare const test: any;
declare const expect: any;

import {
  buildClubDNA,
  buildCrestLibrary,
  buildKitSet,
  clubShortCode,
  filterCrestLibrary,
  filterKitPresets,
  KIT_PRESETS,
  kitChestText,
  kitSwatchDataUri,
} from "./clubIdentityDefaults";

describe("bundled club identity defaults", () => {
  test("prints a three-letter crest code for every club name", () => {
    expect(clubShortCode("VIDA FC")).toBe("VID");
    expect(clubShortCode("Vida")).toBe("VID");
    expect(clubShortCode("Ikorodu City FC")).toBe("ICF");
    expect(clubShortCode("Lagos Lions")).toBe("LLI");
    expect(clubShortCode("Real Madrid")).toBe("RMA");
    expect(clubShortCode("FC Barcelona")).toBe("FCB");
    expect(clubShortCode("VIDA FC")).toHaveLength(3);
    expect(clubShortCode("Lagos Lions")).toHaveLength(3);
  });

  test("provides hundreds of deterministic crest options with initials on the face", () => {
    const crests = buildCrestLibrary("VIDA FC");
    expect(crests.length).toBeGreaterThanOrEqual(300);
    expect(new Set(crests.map((crest) => crest.concept_id)).size).toBe(crests.length);
    expect(new Set(crests.map((crest) => crest.shape))).toEqual(
      new Set(["shield", "round", "diamond", "pennant"]),
    );
    expect(new Set(crests.map((crest) => crest.icon_family))).toEqual(
      new Set(["lion", "eagle", "crown", "star", "oak", "bolt"]),
    );
    expect(crests.every((crest) => crest.initials === "VID")).toBe(true);
    expect(crests.every((crest) => crest.svg_markup.includes(">VID<"))).toBe(true);
    expect(crests.every((crest) => crest.svg_markup.includes('font-size="36"'))).toBe(true);
    expect(crests.every((crest) => crest.data_uri.startsWith("data:image/svg+xml"))).toBe(true);
    expect(filterCrestLibrary(crests, { finish: "royal", shape: "shield" }).every((crest) => crest.finish === "royal" && crest.shape === "shield")).toBe(true);
  });

  test("provides hundreds of kit designs with the club name on every shirt", () => {
    expect(KIT_PRESETS.length).toBeGreaterThanOrEqual(200);
    expect(new Set(KIT_PRESETS.map((preset) => preset.id)).size).toBe(KIT_PRESETS.length);
    expect(kitChestText("VIDA FC")).toBe("VIDA FC");
    expect(kitChestText("International Athletic Association")).toBe("IAA");
    const kitSet = buildKitSet(KIT_PRESETS[0].id, "VIDA FC");
    expect(Object.keys(kitSet).sort()).toEqual(["away", "goalkeeper", "home", "third"]);
    expect(kitSet.home.front_text).toBe("VIDA FC");
    expect(kitSet.away.front_text).toBe("VIDA FC");
    expect(kitSet.third.front_text).toBe("VIDA FC");
    expect(kitSet.goalkeeper.front_text).toBe("VIDA FC");
    expect(kitSwatchDataUri(kitSet.home)).toContain(encodeURIComponent("VIDA FC"));
    expect(filterKitPresets(KIT_PRESETS, { pattern: "stripes" }).every((preset) => preset.pattern === "stripes")).toBe(true);
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
