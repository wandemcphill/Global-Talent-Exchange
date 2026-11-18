import type { GtexCustomSceneRenderer } from "./GtexSceneTypes";

type SceneLoader = () => Promise<GtexCustomSceneRenderer>;

async function component<T>(loader: () => Promise<T>, pick: (mod: T) => GtexCustomSceneRenderer): Promise<GtexCustomSceneRenderer> {
  const mod = await loader();
  return pick(mod);
}

/**
 * The only product-scene import map. A renderer file that is not listed here
 * is not treated as an implemented product renderer.
 * The live match scene stays on its own Match Center import.
 */
export const PRODUCT_SCENE_LOADERS: Record<string, SceneLoader> = {
  club_takeover: () => component(() => import("./scenes/PresentationStage"), (m) => m.ClubTakeoverScene),
  facility_upgrade: () => component(() => import("./scenes/PresentationStage"), (m) => m.StadiumCampusScene),
  stadium_sponsor: () => component(() => import("./scenes/PresentationStage"), (m) => m.SponsorshipBowlScene),
  signing_walkout: () => component(() => import("./scenes/PresentationStage"), (m) => m.TunnelWalkoutScene),
  academy_upgrade: () => component(() => import("./scenes/PresentationStage"), (m) => m.AcademyGroundScene),
  academy_training_pitch: () => component(() => import("./scenes/PresentationStage"), (m) => m.AcademyGroundScene),
  wonderkid_emergence: () => component(() => import("./scenes/PresentationStage"), (m) => m.AcademyGroundScene),
  build_a_son: () => component(() => import("./scenes/PresentationStage"), (m) => m.AcademyGroundScene),
  world_gala: () => component(() => import("./scenes/PresentationStage"), (m) => m.CeremonyScene),
  competition_final: () => component(() => import("./scenes/PresentationStage"), (m) => m.CeremonyScene),
  trophy_podium: () => component(() => import("./scenes/PresentationStage"), (m) => m.CeremonyScene),
  new_ad_deal: () => component(() => import("./scenes/PresentationStage"), (m) => m.SponsorshipBowlScene),
  stadium_ad_display: () => component(() => import("./scenes/PresentationStage"), (m) => m.SponsorshipBowlScene),
  manager_arrival: () => component(() => import("./scenes/ManagerArrivalScene"), (m) => m.ManagerArrivalScene),
  negotiation_table: () => component(() => import("./scenes/BoardroomScene"), (m) => m.BoardroomScene),
  boardroom_meeting: () => component(() => import("./scenes/BoardroomScene"), (m) => m.BoardroomScene),
  boardroom_clash: () => component(() => import("./scenes/BoardroomScene"), (m) => m.BoardroomScene),
  luxury_turntable: () => component(() => import("./scenes/LuxuryTurntableScene"), (m) => m.LuxuryTurntableScene),
  luxury_inspection_turntable: () => component(() => import("./scenes/PrestigeShowroomScene"), (m) => m.PrestigeShowroomScene),
  private_jet_flex: () => component(() => import("./scenes/LuxuryTurntableScene"), (m) => m.LuxuryTurntableScene),
  club_announcement: () => component(() => import("./scenes/EditorialAnnouncement"), (m) => m.EditorialAnnouncement),
};

export function hasProductSceneLoader(sceneId: string): boolean {
  return Object.prototype.hasOwnProperty.call(PRODUCT_SCENE_LOADERS, sceneId);
}
