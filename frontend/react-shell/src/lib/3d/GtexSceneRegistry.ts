import type React from "react";
/**
 * GTEX Living Football Ecosystem — Shared WebGL 3D Experience Framework
 * Official GtexSceneRegistry: Central catalog of reusable 3D environments,
 * device-quality profiling, asset dependency resolution, and 2D fallback routing.
 */

import {
  DeviceQualityTier,
  FallbackMode,
  GtexCustomSceneRenderer,
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
 * Registers campus, presentation, broadcast, and showroom environments.
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

  // 2. Presentation environments. Each id resolves through productSceneLoaders.
  {
    id: "signing_walkout",
    title: "Player Signing Walkout",
    category: "cinema",
    description: "Director Cut 3-shot walkout presentation with floodlight reveal, confetti, and kit customization.",
    renderBackend: "threejs",
    defaultCamera: { position: [0, 2.2, 16], target: [0, 1.6, 0], fov: 32 },
    requiredModels: ["/models/match/football-stadium.glb", "/models/footballer/gtex_home_kit_mixamo.glb"],
    requiredAudio: ["walkout_sub_bass", "pyro_pop", "shutter_click"],
    fallbackMode: "2d_diorama",
    supportsInteraction: true,
    tags: ["walkout", "signing", "player", "celebration", "reveal"],
  },
  {
    id: "negotiation_table",
    title: "Executive Negotiation Table",
    category: "club",
    description: "Tense boardroom contract negotiations between owner, manager, player, and representative.",
    renderBackend: "threejs",
    defaultCamera: { position: [0, 5, 18], target: [0, 2, 0], fov: 40 },
    requiredModels: ["/models/campus/club_hq.glb"],
    fallbackMode: "2d_diorama",
    supportsInteraction: true,
    tags: ["contract", "boardroom", "negotiations", "transfer", "agent"],
  },
  {
    id: "luxury_turntable",
    title: "Prestige Luxury Turntable",
    category: "showroom",
    description: "Reflective 360-degree turntable for private jets, hypercars, luxury SUVs, and horology inspection.",
    renderBackend: "threejs",
    defaultCamera: { position: [6.5, 3.2, 8.5], target: [0, 1.1, 0], fov: 38 },
    requiredModels: [
      "/assets/showroom/sovereign_900x_jet.glb",
      "/assets/showroom/veloce_gt9_hypercar.glb",
      "/assets/showroom/executive_suv.glb",
      "/assets/showroom/chronos_tourbillon_watch.glb",
    ],
    fallbackMode: "2d_diorama",
    supportsInteraction: true,
    tags: ["showroom", "prestige", "turntable", "luxury", "jet", "car"],
  },
  {
    id: "world_gala",
    title: "World Football Awards Gala",
    category: "cinema",
    description: "Black-tie awards ceremony stage with red carpet, flashbulbs, and trophy presentations.",
    renderBackend: "threejs",
    defaultCamera: { position: [16, 6, 22], target: [0, 2.2, 0], fov: 36 },
    requiredModels: ["/models/match/football-stadium.glb", "/assets/showroom/trophy_plinth.glb"],
    fallbackMode: "2d_diorama",
    supportsInteraction: true,
    tags: ["gala", "awards", "red_carpet", "ballon_dor", "prestige"],
  },
  {
    id: "build_a_son",
    title: "Build-A-Son Academy Lab",
    category: "academy",
    description: "Futuristic genetics and youth development laboratory for personalized youth prodigies.",
    renderBackend: "threejs",
    defaultCamera: { position: [12, 6, 14], target: [0, 1.2, 0], fov: 38 },
    requiredModels: ["/models/campus/elite_academy_complex.glb", "/models/campus/academy_youth_pitch.glb"],
    fallbackMode: "2d_diorama",
    supportsInteraction: true,
    tags: ["academy", "build_a_son", "regen", "youth", "custom_prodigy"],
  },
  {
    id: "manager_arrival",
    title: "Manager Tactical Arrival",
    category: "club",
    description: "High-profile manager unveiling press conference with stadium tactical board backdrop.",
    renderBackend: "threejs",
    defaultCamera: { position: [8, 3.2, 12], target: [0, 1.5, 0], fov: 36 },
    requiredModels: ["/models/campus/training_pitch.glb", "/models/footballer/gtex_home_kit_mixamo.glb"],
    fallbackMode: "2d_diorama",
    supportsInteraction: true,
    tags: ["manager", "arrival", "press", "unveiling", "tactics"],
  },
  {
    id: "stadium_sponsor",
    title: "Stadium Sponsorship & Naming Rights",
    category: "cinema",
    description: "Immersive stadium floodlight overview showcasing 360 LED perimeter ribbons and naming halo.",
    renderBackend: "threejs",
    defaultCamera: { position: [24, 8, 22], target: [0, 4, 8], fov: 38 },
    requiredModels: ["/models/match/football-stadium.glb"],
    fallbackMode: "2d_diorama",
    supportsInteraction: true,
    tags: ["stadium", "sponsor", "advertising", "led_ribbon", "broadcast"],
  },
  {
    id: "boardroom_clash",
    title: "Boardroom Strategic Clash",
    category: "club",
    description: "High-stakes executive discussion on club philosophy, transfer budgets, and manager tenure.",
    renderBackend: "threejs",
    defaultCamera: { position: [0, 4.2, 14], target: [0, 1.6, 0], fov: 40 },
    requiredModels: ["/models/campus/club_hq.glb"],
    fallbackMode: "2d_diorama",
    supportsInteraction: true,
    tags: ["boardroom", "executive", "owner", "dispute", "strategy"],
  },
  {
    id: "club_takeover",
    title: "Club Ownership Takeover",
    category: "club",
    description: "Night stadium takeover. The club name and crest are carried on the bowl display.",
    renderBackend: "threejs",
    defaultCamera: { position: [78, 40, 92], target: [0, 12, 0], fov: 38 },
    requiredModels: ["/models/presentation/cc0_football_stadium.glb", "/models/campus/club_hq.glb"],
    fallbackMode: "2d_diorama",
    supportsInteraction: true,
    tags: ["takeover", "ownership", "consortium", "executive", "club"],
  },
  {
    id: "facility_upgrade",
    title: "Campus Facility Upgrade",
    category: "campus",
    description: "Ribbon-cutting ceremony for newly constructed elite training centers and analytics suites.",
    renderBackend: "threejs",
    defaultCamera: { position: [90, 42, 70], target: [0, 8, 0], fov: 38 },
    requiredModels: ["/models/campus/club_hq.glb"],
    fallbackMode: "2d_diorama",
    supportsInteraction: true,
    tags: ["facility", "campus", "upgrade", "infrastructure", "construction"],
  },
  {
    id: "academy_upgrade",
    title: "Youth Academy Expansion",
    category: "academy",
    description: "Unveiling modern youth development pitches, scouting hubs, and boarding dorms.",
    renderBackend: "threejs",
    defaultCamera: { position: [40, 22, 36], target: [0, 4, 0], fov: 40 },
    requiredModels: ["/models/campus/academy_complex.glb"],
    fallbackMode: "2d_diorama",
    supportsInteraction: true,
    tags: ["academy", "expansion", "youth", "campus", "upgrade"],
  },
  {
    id: "wonderkid_emergence",
    title: "Academy Wonderkid Emergence",
    category: "academy",
    description: "Youth prospect emergence with golden potential aura and youth academy crest presentation.",
    renderBackend: "threejs",
    defaultCamera: { position: [8, 2.4, 10], target: [0, 1.4, 0], fov: 34 },
    requiredModels: ["/models/campus/academy_complex.glb"],
    fallbackMode: "2d_diorama",
    supportsInteraction: true,
    tags: ["academy", "wonderkid", "regen", "youth", "potential"],
  },
  {
    id: "competition_final",
    title: "Championship Trophy Ceremony",
    category: "competition",
    description: "Golden confetti storm and podium celebration for tournament champions and trophy holders.",
    renderBackend: "threejs",
    defaultCamera: { position: [28, 14, 36], target: [0, 3, 0], fov: 36 },
    requiredModels: ["/models/match/football-stadium.glb", "/assets/showroom/trophy_plinth.glb"],
    fallbackMode: "2d_diorama",
    supportsInteraction: true,
    tags: ["competition", "trophy", "cup", "champion", "podium"],
  },
  {
    id: "stadium_ad_display",
    title: "Dynamic Pitchside LED Campaign",
    category: "cinema",
    description: "Full stadium in-match advertising showcase with animated LED brand placements.",
    renderBackend: "threejs",
    defaultCamera: { position: [24, 8, 22], target: [0, 4, 8], fov: 36 },
    requiredModels: ["/models/match/football-stadium.glb"],
    fallbackMode: "2d_diorama",
    supportsInteraction: true,
    tags: ["ad", "advertising", "led", "commercial", "sponsor"],
  },
  {
    id: "new_ad_deal",
    title: "Commercial Partnership Signing",
    category: "cinema",
    description: "Global corporate brand partnership announcement with co-branded jersey and digital displays.",
    renderBackend: "threejs",
    defaultCamera: { position: [0, 5, 18], target: [0, 4, 6], fov: 36 },
    requiredModels: ["/models/match/football-stadium.glb"],
    fallbackMode: "2d_diorama",
    supportsInteraction: true,
    tags: ["commercial", "partnership", "deal", "brand", "revenue"],
  },
  {
    id: "club_announcement",
    title: "Club Breaking Announcement",
    category: "club",
    description: "Official club broadcast statement set as an editorial communiqué.",
    renderBackend: "react_editorial",
    defaultCamera: { position: [0, 2, 8], target: [0, 1.4, 0], fov: 40 },
    requiredModels: [],
    fallbackMode: "2d_diorama",
    supportsInteraction: true,
    tags: ["announcement", "club", "press", "breaking", "statement"],
  },
  {
    id: "private_jet_flex",
    title: "Executive Private Jet Runway",
    category: "showroom",
    description: "Tarmac presentation for VIP private jets with heat shimmer, turbine glow, and boarding stairs.",
    renderBackend: "threejs",
    defaultCamera: { position: [6.5, 3.2, 8.5], target: [0, 1.1, 0], fov: 38 },
    requiredModels: ["/assets/showroom/sovereign_900x_jet.glb"],
    fallbackMode: "2d_diorama",
    supportsInteraction: true,
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
    id: "tactician_suite",
    title: "Manager Tactician War Room",
    category: "club",
    description: "Manager's tactical command center with glowing magnetic formation board and dugout tunnel view.",
    renderBackend: "threejs",
    defaultCamera: { position: [0, 2.4, 4.2], target: [0, 2.2, 0], fov: 40 },
    requiredModels: [],
    fallbackMode: "2d_diorama",
    supportsInteraction: true,
    tags: ["tactics", "manager", "formation", "war_room", "dugout"],
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
      "/assets/showroom/sovereign_900x_jet.glb",
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
  private customRenderers = new Map<string, GtexCustomSceneRenderer>();

  /** Register a custom component renderer for a scene ID (decoupling viewports from concrete scenes) */
  public registerRenderer<P = any>(sceneId: string, renderer: GtexCustomSceneRenderer<P>): void {
    this.customRenderers.set(sceneId, renderer as GtexCustomSceneRenderer);
  }

  /** Retrieve a custom component renderer for a scene ID */
  public getRenderer<P = any>(sceneId: string): GtexCustomSceneRenderer<P> | undefined {
    return this.customRenderers.get(sceneId) as GtexCustomSceneRenderer<P> | undefined;
  }

  /** Unregister a custom component renderer */
  public unregisterRenderer(sceneId: string): void {
    this.customRenderers.delete(sceneId);
  }

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

  /** Look up a scene by its unique identifier. */
  public getScene(id: string): GtexSceneDescriptor | undefined {
    return this.scenes.get(id);
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
    this.customRenderers.clear();
    this.qualityOverride = null;
    this.initDefaultCatalog();
  }
}

/** Global singleton export of the GTEX Scene Registry */
export const GtexSceneRegistry = new SceneRegistryStore();
