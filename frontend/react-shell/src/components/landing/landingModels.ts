export interface ClubStageData {
  stage: string;
  name: string;
  scoreRange: string;
  tvSharePercentage: number;
  hostTournamentCut: number;
  facilitiesTitle: string;
  facilitiesDescription: string;
  luxuryAssetAvailable: string;
  averageValuationCoin: string;
  tacticalFreedom: string;
  badgeColor: string;
}

export const kClubStages: ClubStageData[] = [
  {
    stage: "foundation",
    name: "Foundation Tier",
    scoreRange: "< 20 Development Score",
    tvSharePercentage: 30,
    hostTournamentCut: 40,
    facilitiesTitle: "Grassroots Academy Pitch",
    facilitiesDescription: "Initial municipal pitch, local trial day intakes, basic treatment rooms.",
    luxuryAssetAvailable: "Standard Transit van",
    averageValuationCoin: "120,000 GTC",
    tacticalFreedom: "Single 4-4-2 base plan",
    badgeColor: "#6B7A93",
  },
  {
    stage: "growing",
    name: "Growing Contender",
    scoreRange: "20–39 Development Score",
    tvSharePercentage: 40,
    hostTournamentCut: 40,
    facilitiesTitle: "Regional Training Centre",
    facilitiesDescription: "Dedicated hybrid pitch, video analytics booth, contracted physiotherapist.",
    luxuryAssetAvailable: "Club Minibus Fleet",
    averageValuationCoin: "380,000 GTC",
    tacticalFreedom: "Dual tactical variations",
    badgeColor: "#3B82F6",
  },
  {
    stage: "established",
    name: "Established League Member",
    scoreRange: "40–59 Development Score",
    tvSharePercentage: 50,
    hostTournamentCut: 40,
    facilitiesTitle: "25,000-Cap Club Ground",
    facilitiesDescription: "Floodlit stadium, sports science lab, international youth scouting network.",
    luxuryAssetAvailable: "VIP Directorate Lounge",
    averageValuationCoin: "1,250,000 GTC",
    tacticalFreedom: "Three tactical variations + set-piece designer",
    badgeColor: "#10B981",
  },
  {
    stage: "elite",
    name: "Elite Championship Club",
    scoreRange: "60–79 Development Score",
    tvSharePercentage: 60,
    hostTournamentCut: 40,
    facilitiesTitle: "Apex Performance Campus",
    facilitiesDescription: "Cryotherapy chambers, youth boarding academy, high-performance data suite.",
    luxuryAssetAvailable: "Vanguard XII Luxury Coach (320 GTX)",
    averageValuationCoin: "4,600,000 GTC",
    tacticalFreedom: "Custom game models + live match adaptations",
    badgeColor: "#8B5CF6",
  },
  {
    stage: "legacy",
    name: "Legacy Football Institution",
    scoreRange: "80+ Development Score",
    tvSharePercentage: 70,
    hostTournamentCut: 40,
    facilitiesTitle: "Arena Imperiale (65,000+ Cap)",
    facilitiesDescription: "Retractable roof stadium, global academy satellites, private aviation hangar.",
    luxuryAssetAvailable: "Sovereign 900X Private Jet (4,800 GTX)",
    averageValuationCoin: "18,500,000 GTC",
    tacticalFreedom: "Complete institutional tactical autonomy",
    badgeColor: "#D4AF37",
  },
];

export interface ShowroomAssetItem {
  catalogKey: string;
  name: string;
  category: string;
  model: string;
  priceGtex: number;
  prestigeBonus: number;
  broadcastOnPurchase: boolean;
  imageFile: string;
  description: string;
  canGiftToPlayer: boolean;
  tag: string;
}

export const kShowroomAssets: ShowroomAssetItem[] = [
  {
    catalogKey: "sovereign_900x_jet",
    name: "GTEX Sovereign 900X Private Jet",
    category: "PRIVATE JET",
    model: "Sovereign 900X Long-Range VIP",
    priceGtex: 4800.0,
    prestigeBonus: 8,
    broadcastOnPurchase: true,
    imageFile: "/img/showroom/sovereign_900x_jet.webp",
    description: "Executive intercontinental aircraft for continental away fixtures and owner mobility. Triggers verified platform broadcast.",
    canGiftToPlayer: true,
    tag: "GLOBAL BROADCAST",
  },
  {
    catalogKey: "vanguard_xii_coach",
    name: "Vanguard XII Luxury Team Coach Bus",
    category: "TEAM COACH BUS",
    model: "Vanguard XII Armored First-Team Bus",
    priceGtex: 320.0,
    prestigeBonus: 2,
    broadcastOnPurchase: false,
    imageFile: "/img/showroom/vanguard_xii_coach.webp",
    description: "Armored luxury transit for matchday squad arrivals with custom tactical review screens and recovery seating.",
    canGiftToPlayer: false,
    tag: "CLUB ESSENTIAL",
  },
  {
    catalogKey: "veloce_gt9_hypercar",
    name: "Veloce GT9 Luxury Car",
    category: "LUXURY CAR",
    model: "GT9 Twin-Turbo V12",
    priceGtex: 850.0,
    prestigeBonus: 4,
    broadcastOnPurchase: false,
    imageFile: "/img/showroom/veloce_gt9_hypercar.webp",
    description: "Hand-built performance vehicle. Kept in private owner collection or gifted as an incentive milestone to star players.",
    canGiftToPlayer: true,
    tag: "SQUAD INCENTIVE",
  },
  {
    catalogKey: "chronos_tourbillon_watch",
    name: "Chronos Tourbillon Luxury Wristwatch",
    category: "LUXURY WRISTWATCH",
    model: "Piece Unique Sapphire-Carbon",
    priceGtex: 220.0,
    prestigeBonus: 2,
    broadcastOnPurchase: false,
    imageFile: "/img/showroom/chronos_tourbillon_watch.webp",
    description: "Hand-finished Swiss tourbillon. Perfect personal milestone gift for squad leaders, captains, and breakout regens.",
    canGiftToPlayer: true,
    tag: "REGEN MILESTONE",
  },
  {
    catalogKey: "arena_imperiale_stadium",
    name: "Arena Imperiale Facility",
    category: "Stadium Institution",
    model: "Cat-4 Continental Venue",
    priceGtex: 12500.0,
    prestigeBonus: 25,
    broadcastOnPurchase: true,
    imageFile: "/img/showroom/arena_imperiale_stadium.webp",
    description: "Architectural football cathedral featuring 65,000 capacity, VIP penthouses, and automated TV broadcast rigging.",
    canGiftToPlayer: false,
    tag: "INFRASTRUCTURE",
  },
  {
    catalogKey: "apex_performance_campus",
    name: "Apex Performance Campus",
    category: "Training Campus",
    model: "Integrated Sports Science Hub",
    priceGtex: 7800.0,
    prestigeBonus: 18,
    broadcastOnPurchase: true,
    imageFile: "/img/showroom/apex_performance_campus.webp",
    description: "Next-gen training complex featuring hydrotherapy suites, data analytics labs, and youth boarding facilities.",
    canGiftToPlayer: false,
    tag: "REGEN INCUBATOR",
  },
];

export interface NewsroomArticleItem {
  headline: string;
  subheadline: string;
  category: string;
  statusLabel: string;
  imageFile: string;
  editorialNotes: string[];
  editorialNarration: string;
}

export const kEditorialExamples: NewsroomArticleItem[] = [
  {
    headline: "A Club’s Next-Level Move: Private Aviation",
    subheadline: "A sample editorial package about an eligible luxury-asset milestone.",
    category: "Club Ownership",
    statusLabel: "STORY CONCEPT",
    imageFile: "/img/showroom/sovereign_900x_jet.webp",
    editorialNotes: [
      "Story premise: a club owner acquires an eligible private jet.",
      "Public announcement should follow a confirmed platform event.",
      "Any cost or gameplay effect must come from the asset catalogue.",
    ],
    editorialNarration: "A major aviation acquisition can signal a club’s ambition and make ownership feel tangible. In the live newsroom, the story would be published only after the transaction, eligible public details and any broadcast rules had been confirmed.",
  },
  {
    headline: "TV Money and the Club’s Next Investment",
    subheadline: "A sample story about broadcast income, competitive progress and reinvestment.",
    category: "TV & Club Finance",
    statusLabel: "STORY CONCEPT",
    imageFile: "/img/showroom/arena_imperiale_stadium.webp",
    editorialNotes: [
      "TV distribution depends on the current GTEX stage and competition rules.",
      "Actual amounts must come from authoritative platform records.",
      "Scenario projections are illustrative, not guaranteed earnings.",
    ],
    editorialNarration: "Broadcast revenue can become part of a club’s wider financial story, alongside sponsorships, advertising and player trading. A published GTEX story should use the club’s actual ledger and clearly separate earned amounts from illustrative projections.",
  },
  {
    headline: "From Academy Prospect to First-Team Regular",
    subheadline: "A sample player-development story following a young regen’s journey.",
    category: "Regen Development",
    statusLabel: "STORY CONCEPT",
    imageFile: "/img/showroom/apex_performance_campus.webp",
    editorialNotes: [
      "Player attributes and potential should come from the real regen record.",
      "Development depends on the active academy, training and competition systems.",
      "Player valuations can change and do not guarantee a future sale price.",
    ],
    editorialNarration: "The regen economy is about potential becoming a story. Scouting, training, mentoring and competitive minutes can shape a player’s journey; in the live product, the newsroom should use the existing regen engine and verified player history rather than invented statistics.",
  },
];

export interface RegenTalentProfile {
  name: string;
  position: string;
  age: number;
  nationality: string;
  countryCode: string;
  archetype: string;
  potentialLabel: string;
  currentRating: number;
  potentialRating: number;
  gsiTierLabel: string;
  estimatedValueCredits: string;
  pace: number;
  vision: number;
  technique: number;
  stamina: number;
  mentality: number;
  traits: string[];
  story: string;
}

export const kFeaturedRegens: RegenTalentProfile[] = [
  {
    name: "Kwame Asante",
    position: "AM",
    age: 17,
    nationality: "Ghana",
    countryCode: "GH",
    archetype: "Shadow Playmaker",
    potentialLabel: "Potential 96 • Generational",
    currentRating: 78,
    potentialRating: 96,
    gsiTierLabel: "TIER-1 PHENOM",
    estimatedValueCredits: "2,850,000 GTC",
    pace: 86,
    vision: 94,
    technique: 92,
    stamina: 81,
    mentality: 89,
    traits: ["Through-Ball Specialist", "High Composure", "Big Game Matchwinner"],
    story: "Discovered during the Kumasi regional intake. Promoted to first-team matchday bench after 14 goals in U19 competition.",
  },
  {
    name: "Mateo Alvarez",
    position: "ST",
    age: 19,
    nationality: "Argentina",
    countryCode: "AR",
    archetype: "Clinical Poacher",
    potentialLabel: "Potential 93 • World-Class",
    currentRating: 82,
    potentialRating: 93,
    gsiTierLabel: "TIER-1 ELITE",
    estimatedValueCredits: "4,100,000 GTC",
    pace: 92,
    vision: 79,
    technique: 88,
    stamina: 84,
    mentality: 91,
    traits: ["First-Time Finisher", "Acrobatic Instinct", "Breakaway Pace"],
    story: "Gifted an Icon Watch by club ownership following a hat-trick in the Continental Cup semi-final.",
  },
  {
    name: "Ilyas Benali",
    position: "CB",
    age: 18,
    nationality: "Morocco",
    countryCode: "MA",
    archetype: "Ball-Playing Commander",
    potentialLabel: "Potential 91 • Continental Leader",
    currentRating: 77,
    potentialRating: 91,
    gsiTierLabel: "TIER-2 TALENT",
    estimatedValueCredits: "1,950,000 GTC",
    pace: 82,
    vision: 84,
    technique: 85,
    stamina: 89,
    mentality: 94,
    traits: ["Defensive General", "Aerial Dominance", "Long-Range Switch"],
    story: "Graduated from Apex Campus youth program. Boasts an 88% duel win rate across continental fixtures.",
  },
];

export interface ActiveCompetitionItem {
  name: string;
  type: string;
  format: string;
  prizePool: string;
  currency: string;
  status: string;
  slotsTotal: number;
  slotsFilled: number;
  accentColor: string;
  broadcastAvailable: boolean;
}

export const kCompetitionFormatPreviews: ActiveCompetitionItem[] = [
  {
    name: "Continental Prestige League",
    type: "League Season",
    format: "Double round-robin league format",
    prizePool: "See published event rules",
    currency: "",
    status: "FORMAT PREVIEW",
    slotsTotal: 0,
    slotsFilled: 0,
    accentColor: "#D4AF37",
    broadcastAvailable: false,
  },
  {
    name: "West Africa Elite Circuit",
    type: "Invitational Cup",
    format: "Group stage followed by knockout rounds",
    prizePool: "See published event rules",
    currency: "",
    status: "FORMAT PREVIEW",
    slotsTotal: 0,
    slotsFilled: 0,
    accentColor: "#10B981",
    broadcastAvailable: false,
  },
  {
    name: "Atlantic Prospect Series",
    type: "U21 Showcase",
    format: "Knockout tournament for emerging talent",
    prizePool: "See published event rules",
    currency: "",
    status: "FORMAT PREVIEW",
    slotsTotal: 0,
    slotsFilled: 0,
    accentColor: "#3B82F6",
    broadcastAvailable: false,
  },
];

export interface GtexLiveWorldPulse {
  clubsOnGtex: number;
  usersOnline: number;
  playersOnline: number;
  usersOnlineWindowSeconds?: number;
  generatedAt?: string;
  labels?: Record<string, string>;
}
