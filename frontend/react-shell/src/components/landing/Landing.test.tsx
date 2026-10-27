declare const describe: any;
declare const test: any;
declare const expect: any;

import {
  kClubStages,
  kShowroomAssets,
  kEditorialExamples,
  kFeaturedRegens,
  kCompetitionFormatPreviews,
} from "./landingModels";

describe("GTEX 2027 Landing Page Models and Pillars Test Suite", () => {
  test("5-stage club ownership progression defines canonical TV splits", () => {
    expect(kClubStages).toHaveLength(5);

    const foundation = kClubStages.find((s) => s.stage === "foundation");
    expect(foundation?.tvSharePercentage).toBe(30);
    expect(foundation?.hostTournamentCut).toBe(40);

    const growing = kClubStages.find((s) => s.stage === "growing");
    expect(growing?.tvSharePercentage).toBe(40);

    const established = kClubStages.find((s) => s.stage === "established");
    expect(established?.tvSharePercentage).toBe(50);
    expect(established?.averageValuationCoin).toBe("1,250,000 GTC");

    const elite = kClubStages.find((s) => s.stage === "elite");
    expect(elite?.tvSharePercentage).toBe(60);

    const legacy = kClubStages.find((s) => s.stage === "legacy");
    expect(legacy?.tvSharePercentage).toBe(70);
    expect(legacy?.averageValuationCoin).toBe("18,500,000 GTC");
  });

  test("luxury showroom asset catalogue contains all 6 verified assets", () => {
    expect(kShowroomAssets).toHaveLength(6);

    const jet = kShowroomAssets.find((a) => a.catalogKey === "sovereign_900x_jet");
    expect(jet).toBeDefined();
    expect(jet?.category).toBe("PRIVATE JET");
    expect(jet?.name).toContain("Private Jet");
    expect(jet?.priceGtex).toBe(4800);
    expect(jet?.prestigeBonus).toBe(8);
    expect(jet?.broadcastOnPurchase).toBe(true);

    const coach = kShowroomAssets.find((a) => a.catalogKey === "vanguard_xii_coach");
    expect(coach?.category).toBe("TEAM COACH BUS");
    expect(coach?.name).toContain("Team Coach Bus");
    expect(coach?.priceGtex).toBe(320);

    const car = kShowroomAssets.find((a) => a.catalogKey === "veloce_gt9_hypercar");
    expect(car?.category).toBe("LUXURY CAR");
    expect(car?.name).toContain("Luxury Car");
    expect(car?.priceGtex).toBe(850);

    const watch = kShowroomAssets.find((a) => a.catalogKey === "chronos_tourbillon_watch");
    expect(watch?.category).toBe("LUXURY WRISTWATCH");
    expect(watch?.name).toContain("Luxury Wristwatch");
    expect(watch?.priceGtex).toBe(220);

    const stadium = kShowroomAssets.find((a) => a.catalogKey === "arena_imperiale_stadium");
    expect(stadium?.priceGtex).toBe(12500);

    const campus = kShowroomAssets.find((a) => a.catalogKey === "apex_performance_campus");
    expect(campus?.priceGtex).toBe(7800);
  });

  test("editorial newsroom examples contain illustrative stories and disclosure rules", () => {
    expect(kEditorialExamples).toHaveLength(3);

    const aviation = kEditorialExamples[0];
    expect(aviation.headline).toBe("A Club’s Next-Level Move: Private Aviation");
    expect(aviation.statusLabel).toBe("STORY CONCEPT");
    expect(aviation.editorialNotes.length).toBeGreaterThan(0);

    const tvMoney = kEditorialExamples[1];
    expect(tvMoney.headline).toBe("TV Money and the Club’s Next Investment");

    const regenStory = kEditorialExamples[2];
    expect(regenStory.headline).toBe("From Academy Prospect to First-Team Regular");
  });

  test("featured regen dossiers contain scouting profiles and potential ratings", () => {
    expect(kFeaturedRegens).toHaveLength(3);

    const asante = kFeaturedRegens.find((r) => r.name === "Kwame Asante");
    expect(asante?.potentialRating).toBe(96);
    expect(asante?.gsiTierLabel).toBe("TIER-1 PHENOM");
    expect(asante?.position).toBe("AM");

    const alvarez = kFeaturedRegens.find((r) => r.name === "Mateo Alvarez");
    expect(alvarez?.potentialRating).toBe(93);
    expect(alvarez?.currentRating).toBe(82);

    const benali = kFeaturedRegens.find((r) => r.name === "Ilyas Benali");
    expect(benali?.potentialRating).toBe(91);
    expect(benali?.position).toBe("CB");
  });

  test("competition format previews include league season and cups", () => {
    expect(kCompetitionFormatPreviews).toHaveLength(3);
    expect(kCompetitionFormatPreviews[0].name).toBe("Continental Prestige League");
    expect(kCompetitionFormatPreviews[1].name).toBe("West Africa Elite Circuit");
    expect(kCompetitionFormatPreviews[2].name).toBe("Atlantic Prospect Series");
  });
});
