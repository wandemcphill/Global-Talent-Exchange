/**
 * GTEX Skin Engine — Football Module View Registry
 * Layer 3 display modes for core GTEX football activities.
 */

export interface ModuleViewOption {
  id: string;
  label: string;
  description: string;
  iconName?: string;
  badge?: string;
}

export interface ModuleDefinition {
  moduleKey: string;
  title: string;
  description: string;
  defaultView: string;
  views: ModuleViewOption[];
}

export const REGISTERED_FOOTBALL_MODULES: Record<string, ModuleDefinition> = {
  market: {
    moduleKey: "market",
    title: "Player Market & Talent Exchange",
    description: "Choose between FC-style visual player cards or FM-style comprehensive data tables.",
    defaultView: "cards",
    views: [
      {
        id: "cards",
        label: "FC Player Cards",
        description: "Holographic cards, tier foil gradients, visual badges, and key pricing metrics.",
        badge: "DEFAULT",
      },
      {
        id: "table",
        label: "FM Scouting Table",
        description: "High-density multi-column table with sorting, rapid signing, and side-by-side metrics.",
        badge: "FM PRO",
      },
    ],
  },
  squad: {
    moduleKey: "squad",
    title: "Squad Management & Roster",
    description: "Control how first-team players, substitutes, and tactical positions are presented.",
    defaultView: "table",
    views: [
      {
        id: "table",
        label: "Squad Roster Table",
        description: "Structured tabular roster with wage bills, contract duration, morale, and ratings.",
        badge: "DEFAULT",
      },
      {
        id: "cards",
        label: "Player Card Grid",
        description: "Grid of individual player cards showing captain foil and position badges.",
        badge: "VISUAL",
      },
      {
        id: "pitch",
        label: "2.5D Tactical Pitch",
        description: "Interactive stadium pitch formation mapping squad positions directly onto grass.",
        badge: "TACTICAL",
      },
    ],
  },
  profiles: {
    moduleKey: "profiles",
    title: "Player Dossiers & Profiles",
    description: "Select the depth of player stats, radar graphs, and contract breakdown.",
    defaultView: "dossier",
    views: [
      {
        id: "dossier",
        label: "Card-Focused Dossier",
        description: "Visual card presentation with archetype badges, traits, and player bio.",
        badge: "DEFAULT",
      },
      {
        id: "stats",
        label: "Detailed Statistical Profile",
        description: "Deep attribute radar polygons, career historical stats, and developmental ceiling analysis.",
        badge: "ANALYTICAL",
      },
    ],
  },
  match_center: {
    moduleKey: "match_center",
    title: "Match Centre & Broadcast",
    description: "Configure the live match experience for matchday command and spectator viewing.",
    defaultView: "broadcast",
    views: [
      {
        id: "broadcast",
        label: "Broadcast Presentation",
        description: "Cinematic 3D camera angles, spectator gifts, ambient lighting, and commentary stream.",
        badge: "DEFAULT",
      },
      {
        id: "tactical",
        label: "Tactical Command View",
        description: "Emphasis on pressing intensity, Gegenpress/Tiki-taka sliders, and in-game adjustments.",
        badge: "MANAGER",
      },
      {
        id: "compact",
        label: "Compact Ticker",
        description: "Streamlined live scoreboard with critical match stats and clean event chronology.",
        badge: "LIGHTWEIGHT",
      },
    ],
  },
  competitions: {
    moduleKey: "competitions",
    title: "Tournaments & Competitions",
    description: "Switch between discovery presentation and detailed tournament standings.",
    defaultView: "discovery",
    views: [
      {
        id: "discovery",
        label: "Tournament Discovery",
        description: "Visual tournament showcase cards with prize pools and entry fee badges.",
        badge: "DEFAULT",
      },
      {
        id: "table",
        label: "Detailed Tables & Fixtures",
        description: "Comprehensive group stage tables, match schedules, and bracket ladders.",
        badge: "DATA",
      },
    ],
  },
  scouting: {
    moduleKey: "scouting",
    title: "Scouting & Regen World",
    description: "Discover new wonderkids, academy regens, and world-class prospects.",
    defaultView: "cards",
    views: [
      {
        id: "cards",
        label: "Prospect Cards",
        description: "Photorealistic regen face cards with potential stars and academy heritage.",
        badge: "DEFAULT",
      },
      {
        id: "table",
        label: "Scouting Database",
        description: "Filterable database table designed for high-throughput global talent recruitment.",
        badge: "RECRUITER",
      },
      {
        id: "development",
        label: "Development Pipeline",
        description: "Cohort maturation pipeline mapping prospects by developmental ceiling and growth trajectory.",
        badge: "ACADEMY",
      },
    ],
  },
};

export function getModuleViewOptions(moduleKey: string): ModuleViewOption[] {
  return REGISTERED_FOOTBALL_MODULES[moduleKey]?.views || [];
}

export function getDefaultModuleView(moduleKey: string): string {
  return REGISTERED_FOOTBALL_MODULES[moduleKey]?.defaultView || "default";
}
