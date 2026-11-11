export type InspectionFrame = {
  label: string;
  kind: "image" | "video";
  src: string;
};

const media = (label: string, kind: InspectionFrame["kind"], file: string): InspectionFrame => ({
  label,
  kind,
  src: `/assets/showroom/inspection/${file}`,
});

export const SHOWROOM_INSPECTION_REELS: Record<string, InspectionFrame[]> = {
  sovereign_900x_jet: [
    media("Body", "image", "gtex-lux-jet-body.jpg"),
    media("Engine", "image", "gtex-lux-jet-engine.jpg"),
    media("Cockpit", "image", "gtex-lux-jet-cockpit.jpg"),
    media("Cabin seats", "image", "gtex-lux-jet-seats.jpg"),
    media("Lavatory", "image", "gtex-lux-jet-lavatory.jpg"),
    media("Galley", "image", "gtex-lux-jet-galley.jpg"),
    media("Cabin walk", "video", "gtex-lux-jet-cabin-walk.mp4"),
    media("Cockpit walk", "video", "gtex-lux-jet-cockpit-walk.mp4"),
    media("Lavatory walk", "video", "gtex-lux-jet-lavatory-walk.mp4"),
    media("360 turn", "video", "gtex-lux-jet-360.mp4"),
  ],
  gulfstream_g700_exec_jet: [
    media("Body", "image", "gtex-lux-flagship-body.jpg"),
    media("Cockpit", "image", "gtex-lux-flagship-cockpit.jpg"),
    media("Club suite", "image", "gtex-lux-flagship-suite.jpg"),
    media("Suite walk", "video", "gtex-lux-flagship-suite-walk.mp4"),
    media("360 turn", "video", "gtex-lux-flagship-360.mp4"),
  ],
  veloce_gt9_hypercar: [
    media("Body", "image", "gtex-lux-hypercar-body.jpg"),
    media("Rear", "image", "gtex-lux-hypercar-rear.jpg"),
    media("Cabin", "image", "gtex-lux-hypercar-interior.jpg"),
    media("Engine", "image", "gtex-lux-hypercar-engine.jpg"),
    media("Cabin walk", "video", "gtex-lux-hypercar-cabin-walk.mp4"),
    media("360 turn", "video", "gtex-lux-hypercar-360.mp4"),
  ],
  executive_suv_command: [
    media("Body", "image", "gtex-lux-suv-body.jpg"),
    media("Rear lounge", "image", "gtex-lux-suv-lounge.jpg"),
    media("Lounge walk", "video", "gtex-lux-suv-lounge-walk.mp4"),
    media("360 turn", "video", "gtex-lux-suv-360.mp4"),
  ],
  vanguard_xii_coach: [
    media("Body", "image", "gtex-lux-coach-body.jpg"),
    media("Cabin", "image", "gtex-lux-coach-cabin.jpg"),
    media("Cabin walk", "video", "gtex-lux-coach-cabin-walk.mp4"),
    media("360 turn", "video", "gtex-lux-coach-360.mp4"),
  ],
  chronos_tourbillon_watch: [
    media("Dial", "image", "gtex-lux-watch-dial.jpg"),
    media("Movement", "image", "gtex-lux-watch-movement.jpg"),
    media("360 turn", "video", "gtex-lux-watch-360.mp4"),
  ],
  superyacht: [
    media("Hull", "image", "gtex-lux-yacht-body.jpg"),
    media("Salon", "image", "gtex-lux-yacht-salon.jpg"),
    media("Owner cabin", "image", "gtex-lux-yacht-cabin.jpg"),
    media("Bridge", "image", "gtex-lux-yacht-bridge.jpg"),
    media("Salon walk", "video", "gtex-lux-yacht-salon-walk.mp4"),
    media("Cabin walk", "video", "gtex-lux-yacht-cabin-walk.mp4"),
    media("360 turn", "video", "gtex-lux-yacht-360.mp4"),
  ],
};

const GIFT_KEYS: Record<string, string> = {
  private_jet: "sovereign_900x_jet",
  luxury_private_jet: "sovereign_900x_jet",
  private_jet_flyby: "sovereign_900x_jet",
  gulfstream_g700: "gulfstream_g700_exec_jet",
  gulfstream_g700_exec_jet: "gulfstream_g700_exec_jet",
  luxury_superyacht: "superyacht",
  superyacht: "superyacht",
  luxury_team_coach: "vanguard_xii_coach",
  team_coach: "vanguard_xii_coach",
  club_coach: "vanguard_xii_coach",
  executive_suv: "executive_suv_command",
  veloce_gt9_hypercar: "veloce_gt9_hypercar",
  chronos_tourbillon_watch: "chronos_tourbillon_watch",
};

function asFrames(raw: unknown): InspectionFrame[] {
  if (!Array.isArray(raw)) return [];
  return raw.filter((frame): frame is InspectionFrame => {
    if (!frame || typeof frame !== "object") return false;
    const item = frame as InspectionFrame;
    return Boolean(item.src) && (item.kind === "image" || item.kind === "video") && Boolean(item.label);
  });
}

export function inspectionFramesFor(
  item: { catalog_key?: string; gift_code?: string; id?: string; inspection_reel?: unknown } | null | undefined,
  mode: "stills" | "full" = "full"
): InspectionFrame[] {
  const fromApi = asFrames(item?.inspection_reel);
  let frames = fromApi;
  if (frames.length === 0) {
    const candidates = [item?.catalog_key, item?.gift_code, item?.id]
      .map((value) => String(value || "").trim().toLowerCase())
      .filter(Boolean);
    for (const key of candidates) {
      const reelKey = SHOWROOM_INSPECTION_REELS[key] ? key : GIFT_KEYS[key];
      if (reelKey && SHOWROOM_INSPECTION_REELS[reelKey]) {
        frames = SHOWROOM_INSPECTION_REELS[reelKey];
        break;
      }
    }
  }
  if (mode === "stills") return frames.filter((frame) => frame.kind === "image");
  return frames;
}
