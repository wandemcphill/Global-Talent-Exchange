/**
 * GTEX Living Football Ecosystem — Shared WebGL 3D Experience Framework
 * Official GtexSceneRegistry: Central catalog of reusable 3D environments,
 * device-quality profiling, asset dependency resolution, and 2D fallback routing.
 */

import {
  DeviceQualityTier,
  FallbackMode,
  GtexSceneDescriptor,
  QualityProfile,
  SceneCategory,
} from "./GtexSceneTypes";

export const QUALITY_PROFILES: Record<DeviceQualityTier, QualityProfile> = {
  ultra: {
    tier: "ultra",
    targetFps: 60,
    pixelRatio: 2.0,
    shadowsEnabled: true,
    antialias: true,
    maxParticles: 300,
    textureResolutionCap: 2048,
    lodDistanceScale: 1.5,
    description: "Maximum visual fidelity: soft directional shadows, 2x retina sampling, high-density particle fx.",
  },
  high: {
    tier: "high",
    targetFps: 60,
    pixelRatio: 1.5,
    shadowsEnabled: true,
    antialias: true,
    maxParticles: 180,
    textureResolutionCap: 1024,
    lodDistanceScale: 1.0,
    description: "Desktop standard: dynamic lighting, crisp textures, standard 60fps particle choreographies.",
  },
  medium: {
    tier: "medium",
    targetFps: 60,
    pixelRatio: 1.0,
    shadowsEnabled: false,
    antialias: true,
    maxParticles: 90,
    textureResolutionCap: 1024,
    lodDistanceScale: 0.8,
    description: "Balanced mobile/laptop: ambient lighting, fast shaders, reduced particle budget.",
  },
  low: {
    tier: "low",
    targetFps: 30,
    pixelRatio: 0.85,
    shadowsEnabled: false,
    antialias: false,
    maxParticles: 30,
    textureResolutionCap: 512,
    lodDistanceScale: 0.5,
    description: "Battery saver / low-spec: simplified materials, minimal canvas physics, 2D fallback eligible.",
  },
};

const STORAGE_QUALITY_KEY = "gtex_3d_quality_tier_override";

/**
 * Canonical GTEX Initial Scene Catalog.
 * Registers CampusBuilder, all 17 Cinema3DStage scenes, and next-gen Living Ecosystem destinations.
 */
const INITIAL_SCENE_CATALOG: GtexSceneDescriptor[] = [
  // 1. Campus Builder
  {
    id: "campus_builder",
    title: "Club Campus & Infrastructure",
    category: "campus",
    description: "Sims-inspired 24x18 modular club campus builder with orthogonal placement and multi-tier construction.",
    renderBackend: "threejs",
    defaultCamera: { position: [0, 45, 55], target: [0, 0, 0], fov: 42 },
    requiredModels: [
      "/models/campus/stadium_main.glb",
      "/models/campus/club_hq.glb",
      "/models/campus/academy_complex.glb",
      "/models/campus/training_pitch.glb",
    ],
    fallbackMode: "2d_diorama",
    supportsInteraction: true,
    tags: ["campus", "facilities", "construction", "headquarters", "infrastructure"],
  },

  // 2. Cinema Stage Scenes (Mapped to Cinema3DStage - All 17 scenes)
  {
    id: "signing_walkout",
    title: "Player Signing Walkout",
    category: "cinema",
    description: "Director Cut 3-shot walkout presentation with floodlight reveal, confetti, and kit customization.",
    renderBackend: "cinema_volumetric",
    defaultCamera: { position: [0, 0, 850], target: [0, 0, 0], fov: 45 },
    requiredModels: [],
    requiredAudio: ["walkout_sub_bass", "pyro_pop", "shutter_click"],
    fallbackMode: "2d_diorama",
    supportsInteraction: true,
    cinemaSceneType: "signing_walkout",
    tags: ["walkout", "signing", "player", "celebration", "reveal"],
  },
  {
    id: "negotiation_table",
    title: "Executive Negotiation Table",
    category: "club",
    description: "Tense boardroom contract negotiations between owner, manager, player, and representative.",
    renderBackend: "cinema_volumetric",
    defaultCamera: { position: [0, 2, 780], target: [0, 0, 0], fov: 45 },
    requiredModels: [],
    fallbackMode: "2d_diorama",
    supportsInteraction: true,
    cinemaSceneType: "negotiation_table",
    tags: ["contract", "boardroom", "negotiations", "transfer", "agent"],
  },
  {
    id: "luxury_turntable",
    title: "Prestige Luxury Turntable",
    category: "showroom",
    description: "Reflective 360-degree turntable for private jets, hypercars, luxury SUVs, and horology inspection.",
    renderBackend: "cinema_volumetric",
    defaultCamera: { position: [0, 10, 820], target: [0, 0, 0], fov: 42 },
    requiredModels: [
      "/assets/showroom/sovereign_900x_jet.glb",
      "/assets/showroom/veloce_gt9_hypercar.glb",
      "/assets/showroom/executive_suv.glb",
      "/assets/showroom/chronos_tourbillon_watch.glb",
    ],
    fallbackMode: "2d_diorama",
    supportsInteraction: true,
    cinemaSceneType: "luxury_turntable",
    tags: ["showroom", "prestige", "turntable", "luxury", "jet", "car"],
  },
  {
    id: "world_gala",
    title: "World Football Awards Gala",
    category: "cinema",
    description: "Black-tie awards ceremony stage with red carpet, flashbulbs, and trophy presentations.",
    renderBackend: "cinema_volumetric",
    defaultCamera: { position: [0, 0, 800], target: [0, 0, 0], fov: 45 },
    requiredModels: [],
    fallbackMode: "2d_diorama",
    supportsInteraction: true,
    cinemaSceneType: "world_gala",
    tags: ["gala", "awards", "red_carpet", "ballon_dor", "prestige"],
  },
  {
    id: "build_a_son",
    title: "Build-A-Son Academy Lab",
    category: "academy",
    description: "Futuristic genetics and youth development laboratory for personalized youth prodigies.",
    renderBackend: "cinema_volumetric",
    defaultCamera: { position: [0, 0, 820], target: [0, 0, 0], fov: 45 },
    requiredModels: [],
    fallbackMode: "2d_diorama",
    supportsInteraction: true,
    cinemaSceneType: "build_a_son",
    tags: ["academy", "build_a_son", "regen", "youth", "custom_prodigy"],
  },
  {
    id: "manager_arrival",
    title: "Manager Tactical Arrival",
    category: "club",
    description: "High-profile manager unveiling press conference with stadium tactical board backdrop.",
    renderBackend: "cinema_volumetric",
    defaultCamera: { position: [0, 0, 800], target: [0, 0, 0], fov: 45 },
    requiredModels: [],
    fallbackMode: "2d_diorama",
    supportsInteraction: true,
    cinemaSceneType: "manager_arrival",
    tags: ["manager", "arrival", "press", "unveiling", "tactics"],
  },
  {
    id: "stadium_sponsor",
    title: "Stadium Sponsorship & Naming Rights",
    category: "cinema",
    description: "Immersive stadium floodlight overview showcasing 360 LED perimeter ribbons and naming halo.",
    renderBackend: "cinema_volumetric",
    defaultCamera: { position: [0, 15, 890], target: [0, 0, 0], fov: 45 },
    requiredModels: ["/models/campus/stadium_main.glb"],
    fallbackMode: "2d_diorama",
    supportsInteraction: true,
    cinemaSceneType: "stadium_sponsor",
    tags: ["stadium", "sponsor", "advertising", "led_ribbon", "broadcast"],
  },
  {
    id: "boardroom_clash",
    title: "Boardroom Strategic Clash",
    category: "club",
    description: "High-stakes executive discussion on club philosophy, transfer budgets, and manager tenure.",
    renderBackend: "cinema_volumetric",
    defaultCamera: { position: [0, 0, 780], target: [0, 0, 0], fov: 45 },
    requiredModels: [],
    fallbackMode: "2d_diorama",
    supportsInteraction: true,
    cinemaSceneType: "boardroom_clash",
    tags: ["boardroom", "executive", "owner", "dispute", "strategy"],
  },
  {
    id: "club_takeover",
    title: "Club Ownership Takeover",
    category: "club",
    description: "Billionaire consortium takeover announcement with corporate crest and helicopter arrival.",
    renderBackend: "cinema_volumetric",
    defaultCamera: { position: [0, 10, 840], target: [0, 0, 0], fov: 45 },
    requiredModels: [],
    fallbackMode: "2d_diorama",
    supportsInteraction: true,
    cinemaSceneType: "club_takeover",
    tags: ["takeover", "ownership", "consortium", "executive", "club"],
  },
  {
    id: "facility_upgrade",
    title: "Campus Facility Upgrade",
    category: "campus",
    description: "Ribbon-cutting ceremony for newly constructed elite training centers and analytics suites.",
    renderBackend: "cinema_volumetric",
    defaultCamera: { position: [0, 5, 820], target: [0, 0, 0], fov: 45 },
    requiredModels: ["/models/campus/club_hq.glb"],
    fallbackMode: "2d_diorama",
    supportsInteraction: true,
    cinemaSceneType: "facility_upgrade",
    tags: ["facility", "campus", "upgrade", "infrastructure", "construction"],
  },
  {
    id: "academy_upgrade",
    title: "Youth Academy Expansion",
    category: "academy",
    description: "Unveiling modern youth development pitches, scouting hubs, and boarding dorms.",
    renderBackend: "cinema_volumetric",
    defaultCamera: { position: [0, 5, 820], target: [0, 0, 0], fov: 45 },
    requiredModels: ["/models/campus/academy_complex.glb"],
    fallbackMode: "2d_diorama",
    supportsInteraction: true,
    cinemaSceneType: "academy_upgrade",
    tags: ["academy", "expansion", "youth", "campus", "upgrade"],
  },
  {
    id: "wonderkid_emergence",
    title: "Academy Wonderkid Emergence",
    category: "academy",
    description: "Youth prospect emergence with golden potential aura and youth academy crest presentation.",
    renderBackend: "cinema_volumetric",
    defaultCamera: { position: [0, 0, 820], target: [0, 0, 0], fov: 45 },
    requiredModels: ["/models/campus/academy_complex.glb"],
    fallbackMode: "2d_diorama",
    supportsInteraction: true,
    cinemaSceneType: "wonderkid_emergence",
    tags: ["academy", "wonderkid", "regen", "youth", "potential"],
  },
  {
    id: "competition_final",
    title: "Championship Trophy Ceremony",
    category: "competition",
    description: "Golden confetti storm and podium celebration for tournament champions and trophy holders.",
    renderBackend: "cinema_volumetric",
    defaultCamera: { position: [0, 0, 800], target: [0, 0, 0], fov: 45 },
    requiredModels: [],
    fallbackMode: "2d_diorama",
    supportsInteraction: true,
    cinemaSceneType: "competition_final",
    tags: ["competition", "trophy", "cup", "champion", "podium"],
  },
  {
    id: "stadium_ad_display",
    title: "Dynamic Pitchside LED Campaign",
    category: "cinema",
    description: "Full stadium in-match advertising showcase with animated LED brand placements.",
    renderBackend: "cinema_volumetric",
    defaultCamera: { position: [0, 10, 850], target: [0, 0, 0], fov: 45 },
    requiredModels: ["/models/campus/stadium_main.glb"],
    fallbackMode: "2d_diorama",
    supportsInteraction: true,
    cinemaSceneType: "stadium_ad_display",
    tags: ["ad", "advertising", "led", "commercial", "sponsor"],
  },
  {
    id: "new_ad_deal",
    title: "Commercial Partnership Signing",
    category: "cinema",
    description: "Global corporate brand partnership announcement with co-branded jersey and digital displays.",
    renderBackend: "cinema_volumetric",
    defaultCamera: { position: [0, 0, 800], target: [0, 0, 0], fov: 45 },
    requiredModels: [],
    fallbackMode: "2d_diorama",
    supportsInteraction: true,
    cinemaSceneType: "new_ad_deal",
    tags: ["commercial", "partnership", "deal", "brand", "revenue"],
  },
  {
    id: "club_announcement",
    title: "Club Breaking Announcement",
    category: "club",
    description: "Official club broadcast statement with press conference lighting and official media backdrop.",
    renderBackend: "cinema_volumetric",
    defaultCamera: { position: [0, 0, 800], target: [0, 0, 0], fov: 45 },
    requiredModels: [],
    fallbackMode: "2d_diorama",
    supportsInteraction: true,
    cinemaSceneType: "club_announcement",
    tags: ["announcement", "club", "press", "breaking", "statement"],
  },
  {
    id: "private_jet_flex",
    title: "Executive Private Jet Runway",
    category: "showroom",
    description: "Tarmac presentation for VIP private jets with heat shimmer, turbine glow, and boarding stairs.",
    renderBackend: "cinema_volumetric",
    defaultCamera: { position: [0, 10, 860], target: [0, 0, 0], fov: 42 },
    requiredModels: ["/assets/showroom/sovereign_900x_jet.glb"],
    fallbackMode: "2d_diorama",
    supportsInteraction: true,
    cinemaSceneType: "private_jet_flex",
    tags: ["jet", "runway", "vip", "luxury", "flex", "showroom"],
  },

  // 3. Next-Gen Living Ecosystem Target Scenes
  {
    id: "stadium_match_broadcast",
    title: "Live Match Broadcast Stadium",
    category: "broadcast",
    description: "Full 3D pitch and stadium bowl with dynamic broadcast cameras, player tracking, and digital perimeter boards.",
    renderBackend: "threejs",
    defaultCamera: { position: [0, 32, 64], target: [0, 0, 0], fov: 38 },
    cameraAngles: {
      tactical: { position: [0, 55, 45], target: [0, 0, 0], fov: 45 },
      broadcast: { position: [0, 30, 60], target: [0, 0, 0], fov: 36 },
      goal_closeup: { position: [-35, 12, 18], target: [-50, 2, 0], fov: 32 },
    },
    requiredModels: [
      "/models/campus/stadium_main.glb",
      "/models/campus/stadium_bowl_core.glb",
      "/models/campus/floodlight_pylon_array.glb",
    ],
    requiredAudio: ["stadium_ambient", "commentary", "crowd_cheer"],
    fallbackMode: "2d_diorama",
    supportsInteraction: true,
    tags: ["broadcast", "match", "stadium", "pitch", "live"],
  },
  {
    id: "boardroom_meeting",
    title: "Executive Boardroom Suite",
    category: "club",
    description: "Private executive suite overlooking the stadium pitch for GM briefings and budget sign-offs.",
    renderBackend: "threejs",
    defaultCamera: { position: [0, 5, 18], target: [0, 2, 0], fov: 40 },
    requiredModels: ["/models/campus/vip_skybox_concourse.glb", "/models/campus/club_hq.glb"],
    fallbackMode: "2d_diorama",
    supportsInteraction: true,
    tags: ["boardroom", "gm", "owner", "executive", "budget"],
  },
  {
    id: "academy_training_pitch",
    title: "Academy Youth Training Ground",
    category: "academy",
    description: "Interactive youth pitches with training cones, coaching staff, and development metrics.",
    renderBackend: "threejs",
    defaultCamera: { position: [0, 25, 40], target: [0, 0, 0], fov: 45 },
    requiredModels: [
      "/models/campus/academy_youth_pitch.glb",
      "/models/campus/elite_academy_complex.glb",
    ],
    fallbackMode: "2d_diorama",
    supportsInteraction: true,
    tags: ["academy", "training", "youth", "development", "drills"],
  },
  {
    id: "trophy_podium",
    title: "Grand Championship Podium",
    category: "competition",
    description: "3D stadium center-circle celebration stage with fireworks, ribbons, and championship pedestal.",
    renderBackend: "threejs",
    defaultCamera: { position: [0, 8, 22], target: [0, 3, 0], fov: 42 },
    requiredModels: ["/models/campus/stadium_main.glb"],
    requiredAudio: ["trophy_anthem", "firework_burst", "crowd_roar"],
    fallbackMode: "2d_diorama",
    supportsInteraction: true,
    tags: ["trophy", "podium", "championship", "ceremony", "winner"],
  },
  {
    id: "luxury_inspection_turntable",
    title: "Prestige Showroom Studio",
    category: "showroom",
    description: "High-end studio with studio key lights, rim reflections, and interactive color & livery customizer.",
    renderBackend: "threejs",
    defaultCamera: { position: [0, 6, 20], target: [0, 2, 0], fov: 38 },
    requiredModels: [
      "/assets/showroom/gulfstream_g700_exec_jet.glb",
      "/assets/showroom/sovereign_900x_jet.glb",
      "/assets/showroom/veloce_gt9_hypercar.glb",
      "/assets/showroom/executive_suv.glb",
      "/assets/showroom/vanguard_xii_coach.glb",
      "/assets/showroom/chronos_tourbillon_watch.glb",
    ],
    fallbackMode: "2d_diorama",
    supportsInteraction: true,
    tags: ["showroom", "inspection", "prestige", "turntable", "customization"],
  },
];

/**
 * Singleton Registry for all GTEX 3D Scenes.
 */
class SceneRegistryStore {
  private scenes = new Map<string, GtexSceneDescriptor>();
  private qualityOverride: DeviceQualityTier | null = null;

  constructor() {
    this.initDefaultCatalog();
  }

  private initDefaultCatalog(): void {
    for (const descriptor of INITIAL_SCENE_CATALOG) {
      this.scenes.set(descriptor.id, descriptor);
    }
  }

  /** Register or update a 3D scene descriptor */
  public registerScene(descriptor: GtexSceneDescriptor): void {
    if (!descriptor.id || typeof descriptor.id !== "string") {
      throw new Error("Invalid scene descriptor: missing required 'id'");
    }
    this.scenes.set(descriptor.id, { ...descriptor });
  }

  /** Look up a scene by its unique identifier or Cinema3DSceneType alias */
  public getScene(id: string): GtexSceneDescriptor | undefined {
    if (this.scenes.has(id)) {
      return this.scenes.get(id);
    }
    // Check cinemaSceneType alias
    for (const desc of this.scenes.values()) {
      if (desc.cinemaSceneType === id) {
        return desc;
      }
    }
    return undefined;
  }

  /** Returns true if a scene with the specified ID exists */
  public hasScene(id: string): boolean {
    return this.getScene(id) !== undefined;
  }

  /** Query registered scenes by category or keyword tag */
  public listScenes(filter?: { category?: SceneCategory; tag?: string }): GtexSceneDescriptor[] {
    const all = Array.from(this.scenes.values());
    if (!filter) return all;

    return all.filter((s) => {
      if (filter.category && s.category !== filter.category) return false;
      if (filter.tag && !s.tags.includes(filter.tag)) return false;
      return true;
    });
  }

  /**
   * Detect device hardware profile and return the appropriate quality configuration.
   */
  public detectDeviceQuality(): QualityProfile {
    // 1. Check user/developer manual override
    if (this.qualityOverride && QUALITY_PROFILES[this.qualityOverride]) {
      return QUALITY_PROFILES[this.qualityOverride];
    }

    // 2. Check localStorage in browser environments
    if (typeof window !== "undefined" && window.localStorage) {
      try {
        const stored = window.localStorage.getItem(STORAGE_QUALITY_KEY) as DeviceQualityTier;
        if (stored && QUALITY_PROFILES[stored]) {
          return QUALITY_PROFILES[stored];
        }
      } catch {
        // LocalStorage access restricted or unavailable
      }
    }

    // 3. Hardware heuristics detection
    if (typeof navigator !== "undefined") {
      const cores = navigator.hardwareConcurrency || 4;
      const mem = (navigator as any).deviceMemory || 4;

      if (cores <= 2 || mem <= 2) {
        return QUALITY_PROFILES.low;
      }
      if (cores <= 4 || mem <= 4) {
        return QUALITY_PROFILES.medium;
      }
      if (cores >= 12 && mem >= 8) {
        return QUALITY_PROFILES.ultra;
      }
      return QUALITY_PROFILES.high;
    }

    return QUALITY_PROFILES.high;
  }

  /** Override the current device quality tier (persisted in localStorage if available) */
  public setQualityOverride(tier: DeviceQualityTier | null): void {
    this.qualityOverride = tier;
    if (typeof window !== "undefined" && window.localStorage) {
      try {
        if (tier) {
          window.localStorage.setItem(STORAGE_QUALITY_KEY, tier);
        } else {
          window.localStorage.removeItem(STORAGE_QUALITY_KEY);
        }
      } catch {
        // no-op
      }
    }
  }

  /** Get the current active quality override */
  public getQualityOverride(): DeviceQualityTier | null {
    return this.qualityOverride;
  }

  /** Aggregate all required assets across selected scenes for prefetching */
  public getAssetPreloadList(sceneIds: string[]): { models: string[]; audio: string[] } {
    const models = new Set<string>();
    const audio = new Set<string>();

    for (const id of sceneIds) {
      const desc = this.getScene(id);
      if (desc) {
        desc.requiredModels.forEach((m) => models.add(m));
        desc.requiredAudio?.forEach((a) => audio.add(a));
      }
    }

    return {
      models: Array.from(models),
      audio: Array.from(audio),
    };
  }

  /** Reset registry to default baseline (for unit tests) */
  public resetToDefaults(): void {
    this.scenes.clear();
    this.qualityOverride = null;
    this.initDefaultCatalog();
  }
}

/** Global singleton export of the GTEX Scene Registry */
export const GtexSceneRegistry = new SceneRegistryStore();
