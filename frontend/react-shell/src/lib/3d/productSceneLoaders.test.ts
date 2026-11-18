import { hasProductSceneLoader, PRODUCT_SCENE_LOADERS } from "./productSceneLoaders";

describe("productSceneLoaders", () => {
  const required = [
    "club_takeover",
    "facility_upgrade",
    "signing_walkout",
    "manager_arrival",
    "academy_upgrade",
    "wonderkid_emergence",
    "build_a_son",
    "world_gala",
    "competition_final",
    "negotiation_table",
    "boardroom_meeting",
    "boardroom_clash",
    "luxury_turntable",
    "private_jet_flex",
    "club_announcement",
    "new_ad_deal",
    "stadium_ad_display",
  ];

  test("registers a loader for every product presentation", () => {
    required.forEach((sceneId) => {
      expect(hasProductSceneLoader(sceneId)).toBe(true);
      expect(typeof PRODUCT_SCENE_LOADERS[sceneId]).toBe("function");
    });
  });

  test("does not treat the tactician test scene as a product renderer", () => {
    expect(hasProductSceneLoader("tactician_suite")).toBe(false);
  });

  test("club takeover loader resolves the takeover scene", async () => {
    const renderer = await PRODUCT_SCENE_LOADERS.club_takeover();
    expect(renderer.name).toBe("ClubTakeoverScene");
  });
});
