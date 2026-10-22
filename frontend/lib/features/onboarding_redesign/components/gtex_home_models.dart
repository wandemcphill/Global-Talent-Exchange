import 'package:flutter/material.dart';

class ClubStageData {
  const ClubStageData({
    required this.stage,
    required this.name,
    required this.scoreRange,
    required this.tvSharePercentage,
    required this.hostTournamentCut,
    required this.facilitiesTitle,
    required this.facilitiesDescription,
    required this.luxuryAssetAvailable,
    required this.averageValuationCoin,
    required this.tacticalFreedom,
    required this.badgeColor,
  });

  final String stage;
  final String name;
  final String scoreRange;
  final int tvSharePercentage;
  final int hostTournamentCut;
  final String facilitiesTitle;
  final String facilitiesDescription;
  final String luxuryAssetAvailable;
  final String averageValuationCoin;
  final String tacticalFreedom;
  final Color badgeColor;
}

const List<ClubStageData> kClubStages = <ClubStageData>[
  ClubStageData(
    stage: 'foundation',
    name: 'Foundation Tier',
    scoreRange: '< 20 Development Score',
    tvSharePercentage: 30,
    hostTournamentCut: 40,
    facilitiesTitle: 'Grassroots Academy Pitch',
    facilitiesDescription: 'Initial municipal pitch, local trial day intakes, basic treatment rooms.',
    luxuryAssetAvailable: 'Standard Transit van',
    averageValuationCoin: '120,000 GTC',
    tacticalFreedom: 'Single 4-4-2 base plan',
    badgeColor: Color(0xFF6B7A93),
  ),
  ClubStageData(
    stage: 'growing',
    name: 'Growing Contender',
    scoreRange: '20–39 Development Score',
    tvSharePercentage: 40,
    hostTournamentCut: 40,
    facilitiesTitle: 'Regional Training Centre',
    facilitiesDescription: 'Dedicated hybrid pitch, video analytics booth, contracted physiotherapist.',
    luxuryAssetAvailable: 'Club Minibus Fleet',
    averageValuationCoin: '380,000 GTC',
    tacticalFreedom: 'Dual tactical variations',
    badgeColor: Color(0xFF3B82F6),
  ),
  ClubStageData(
    stage: 'established',
    name: 'Established League Member',
    scoreRange: '40–59 Development Score',
    tvSharePercentage: 50,
    hostTournamentCut: 40,
    facilitiesTitle: '25,000-Cap Club Ground',
    facilitiesDescription: 'Floodlit stadium, sports science lab, international youth scouting network.',
    luxuryAssetAvailable: 'VIP Directorate Lounge',
    averageValuationCoin: '1,250,000 GTC',
    tacticalFreedom: 'Three tactical variations + set-piece designer',
    badgeColor: Color(0xFF10B981),
  ),
  ClubStageData(
    stage: 'elite',
    name: 'Elite Championship Club',
    scoreRange: '60–79 Development Score',
    tvSharePercentage: 60,
    hostTournamentCut: 40,
    facilitiesTitle: 'Apex Performance Campus',
    facilitiesDescription: 'Cryotherapy chambers, youth boarding academy, high-performance data suite.',
    luxuryAssetAvailable: 'Vanguard XII Luxury Coach (320 GTX)',
    averageValuationCoin: '4,600,000 GTC',
    tacticalFreedom: 'Custom game models + live match adaptations',
    badgeColor: Color(0xFF8B5CF6),
  ),
  ClubStageData(
    stage: 'legacy',
    name: 'Legacy Football Institution',
    scoreRange: '80+ Development Score',
    tvSharePercentage: 70,
    hostTournamentCut: 40,
    facilitiesTitle: 'Arena Imperiale (65,000+ Cap)',
    facilitiesDescription: 'Retractable roof stadium, global academy satellites, private aviation hangar.',
    luxuryAssetAvailable: 'Sovereign 900X Private Jet (4,800 GTX)',
    averageValuationCoin: '18,500,000 GTC',
    tacticalFreedom: 'Complete institutional tactical autonomy',
    badgeColor: Color(0xFFD4AF37),
  ),
];

class ShowroomAssetItem {
  const ShowroomAssetItem({
    required this.catalogKey,
    required this.name,
    required this.category,
    required this.model,
    required this.priceGtex,
    required this.prestigeBonus,
    required this.broadcastOnPurchase,
    required this.imageFile,
    required this.description,
    required this.canGiftToPlayer,
    required this.tag,
  });

  final String catalogKey;
  final String name;
  final String category;
  final String model;
  final double priceGtex;
  final int prestigeBonus;
  final bool broadcastOnPurchase;
  final String imageFile;
  final String description;
  final bool canGiftToPlayer;
  final String tag;
}

const List<ShowroomAssetItem> kShowroomAssets = <ShowroomAssetItem>[
  ShowroomAssetItem(
    catalogKey: 'sovereign_900x_jet',
    name: 'GTEX Sovereign 900X',
    category: 'Private Jet',
    model: 'Sovereign 900X Long-Range VIP',
    priceGtex: 4800.0,
    prestigeBonus: 8,
    broadcastOnPurchase: true,
    imageFile: 'assets/showroom/sovereign_900x_jet.png',
    description: 'Executive intercontinental aircraft for continental away fixtures and owner mobility. Triggers verified platform broadcast.',
    canGiftToPlayer: true,
    tag: 'GLOBAL BROADCAST',
  ),
  ShowroomAssetItem(
    catalogKey: 'vanguard_xii_coach',
    name: 'Vanguard XII Team Coach',
    category: 'Team Transit',
    model: 'Vanguard XII Armored First-Team Bus',
    priceGtex: 320.0,
    prestigeBonus: 2,
    broadcastOnPurchase: false,
    imageFile: 'assets/showroom/vanguard_xii_coach.png',
    description: 'Armored luxury transit for matchday squad arrivals with custom tactical review screens and recovery seating.',
    canGiftToPlayer: false,
    tag: 'CLUB ESSENTIAL',
  ),
  ShowroomAssetItem(
    catalogKey: 'veloce_gt9_hypercar',
    name: 'Veloce GT9 Hypercar',
    category: 'Private Hypercar',
    model: 'GT9 Twin-Turbo V12',
    priceGtex: 850.0,
    prestigeBonus: 4,
    broadcastOnPurchase: false,
    imageFile: 'assets/showroom/veloce_gt9_hypercar.png',
    description: 'Hand-built performance vehicle. Kept in private owner collection or gifted as an incentive milestone to star players.',
    canGiftToPlayer: true,
    tag: 'SQUAD INCENTIVE',
  ),
  ShowroomAssetItem(
    catalogKey: 'chronos_tourbillon_watch',
    name: 'Chronos Tourbillon Piece Unique',
    category: 'Haute Horlogerie',
    model: 'Piece Unique Sapphire-Carbon',
    priceGtex: 220.0,
    prestigeBonus: 2,
    broadcastOnPurchase: false,
    imageFile: 'assets/showroom/chronos_tourbillon_watch.png',
    description: 'Hand-finished Swiss tourbillon. Perfect personal milestone gift for squad leaders, captains, and breakout regens.',
    canGiftToPlayer: true,
    tag: 'REGEN MILESTONE',
  ),
  ShowroomAssetItem(
    catalogKey: 'arena_imperiale_stadium',
    name: 'Arena Imperiale Facility',
    category: 'Stadium Institution',
    model: 'Cat-4 Continental Venue',
    priceGtex: 12500.0,
    prestigeBonus: 25,
    broadcastOnPurchase: true,
    imageFile: 'assets/showroom/arena_imperiale_stadium.png',
    description: 'Architectural football cathedral featuring 65,000 capacity, VIP penthouses, and automated TV broadcast rigging.',
    canGiftToPlayer: false,
    tag: 'INFRASTRUCTURE',
  ),
  ShowroomAssetItem(
    catalogKey: 'apex_performance_campus',
    name: 'Apex Performance Campus',
    category: 'Training Campus',
    model: 'Integrated Sports Science Hub',
    priceGtex: 7800.0,
    prestigeBonus: 18,
    broadcastOnPurchase: true,
    imageFile: 'assets/showroom/apex_performance_campus.png',
    description: 'Next-gen training complex featuring hydrotherapy suites, data analytics labs, and youth boarding facilities.',
    canGiftToPlayer: false,
    tag: 'REGEN INCUBATOR',
  ),
];

class NewsroomArticleItem {
  const NewsroomArticleItem({
    required this.headline,
    required this.subheadline,
    required this.category,
    required this.statusLabel,
    required this.imageFile,
    required this.editorialNotes,
    required this.editorialNarration,
  });

  final String headline;
  final String subheadline;
  final String category;
  final String statusLabel;
  final String imageFile;
  final List<String> editorialNotes;
  final String editorialNarration;
}

/// Visual story concepts only. Live headlines and transaction details must come
/// from the authoritative story feed before they can be presented as events.
const List<NewsroomArticleItem> kEditorialExamples = <NewsroomArticleItem>[
  NewsroomArticleItem(
    headline: 'A Club’s Next-Level Move: Private Aviation',
    subheadline: 'A sample editorial package about an eligible luxury-asset milestone.',
    category: 'Club Ownership',
    statusLabel: 'STORY CONCEPT',
    imageFile: 'assets/showroom/sovereign_900x_jet.png',
    editorialNotes: <String>[
      'Story premise: a club owner acquires an eligible private jet.',
      'Public announcement should follow a confirmed platform event.',
      'Any cost or gameplay effect must come from the asset catalogue.',
    ],
    editorialNarration: 'A major aviation acquisition can signal a club’s ambition and make ownership feel tangible. In the live newsroom, the story would be published only after the transaction, eligible public details and any broadcast rules had been confirmed.',
  ),
  NewsroomArticleItem(
    headline: 'TV Money and the Club’s Next Investment',
    subheadline: 'A sample story about broadcast income, competitive progress and reinvestment.',
    category: 'TV & Club Finance',
    statusLabel: 'STORY CONCEPT',
    imageFile: 'assets/showroom/arena_imperiale_stadium.png',
    editorialNotes: <String>[
      'TV distribution depends on the current GTEX stage and competition rules.',
      'Actual amounts must come from authoritative platform records.',
      'Scenario projections are illustrative, not guaranteed earnings.',
    ],
    editorialNarration: 'Broadcast revenue can become part of a club’s wider financial story, alongside sponsorships, advertising and player trading. A published GTEX story should use the club’s actual ledger and clearly separate earned amounts from illustrative projections.',
  ),
  NewsroomArticleItem(
    headline: 'From Academy Prospect to First-Team Regular',
    subheadline: 'A sample player-development story following a young regen’s journey.',
    category: 'Regen Development',
    statusLabel: 'STORY CONCEPT',
    imageFile: 'assets/showroom/apex_performance_campus.png',
    editorialNotes: <String>[
      'Player attributes and potential should come from the real regen record.',
      'Development depends on the active academy, training and competition systems.',
      'Player valuations can change and do not guarantee a future sale price.',
    ],
    editorialNarration: 'The regen economy is about potential becoming a story. Scouting, training, mentoring and competitive minutes can shape a player’s journey; in the live product, the newsroom should use the existing regen engine and verified player history rather than invented statistics.',
  ),
];

class RegenTalentProfile {
  const RegenTalentProfile({
    required this.name,
    required this.position,
    required this.age,
    required this.nationality,
    required this.countryCode,
    required this.archetype,
    required this.potentialLabel,
    required this.currentRating,
    required this.potentialRating,
    required this.gsiTierLabel,
    required this.estimatedValueCredits,
    required this.pace,
    required this.vision,
    required this.technique,
    required this.stamina,
    required this.mentality,
    required this.traits,
    required this.story,
  });

  final String name;
  final String position;
  final int age;
  final String nationality;
  final String countryCode;
  final String archetype;
  final String potentialLabel;
  final int currentRating;
  final int potentialRating;
  final String gsiTierLabel;
  final String estimatedValueCredits;
  final int pace;
  final int vision;
  final int technique;
  final int stamina;
  final int mentality;
  final List<String> traits;
  final String story;
}

const List<RegenTalentProfile> kFeaturedRegens = <RegenTalentProfile>[
  RegenTalentProfile(
    name: 'Kwame Asante',
    position: 'AM',
    age: 17,
    nationality: 'Ghana',
    countryCode: 'GH',
    archetype: 'Shadow Playmaker',
    potentialLabel: 'Potential 96 • Generational',
    currentRating: 78,
    potentialRating: 96,
    gsiTierLabel: 'TIER-1 PHENOM',
    estimatedValueCredits: '2,850,000 GTC',
    pace: 86,
    vision: 94,
    technique: 92,
    stamina: 81,
    mentality: 89,
    traits: <String>['Through-Ball Specialist', 'High Composure', 'Big Game Matchwinner'],
    story: 'Discovered during the Kumasi regional intake. Promoted to first-team matchday bench after 14 goals in U19 competition.',
  ),
  RegenTalentProfile(
    name: 'Mateo Alvarez',
    position: 'ST',
    age: 19,
    nationality: 'Argentina',
    countryCode: 'AR',
    archetype: 'Clinical Poacher',
    potentialLabel: 'Potential 93 • World-Class',
    currentRating: 82,
    potentialRating: 93,
    gsiTierLabel: 'TIER-1 ELITE',
    estimatedValueCredits: '4,100,000 GTC',
    pace: 92,
    vision: 79,
    technique: 88,
    stamina: 84,
    mentality: 91,
    traits: <String>['First-Time Finisher', 'Acrobatic Instinct', 'Breakaway Pace'],
    story: 'Gifted an Icon Watch by club ownership following a hat-trick in the Continental Cup semi-final.',
  ),
  RegenTalentProfile(
    name: 'Ilyas Benali',
    position: 'CB',
    age: 18,
    nationality: 'Morocco',
    countryCode: 'MA',
    archetype: 'Ball-Playing Commander',
    potentialLabel: 'Potential 91 • Continental Leader',
    currentRating: 77,
    potentialRating: 91,
    gsiTierLabel: 'TIER-2 TALENT',
    estimatedValueCredits: '1,950,000 GTC',
    pace: 82,
    vision: 84,
    technique: 85,
    stamina: 89,
    mentality: 94,
    traits: <String>['Defensive General', 'Aerial Dominance', 'Long-Range Switch'],
    story: 'Graduated from Apex Campus youth program. Boasts an 88% duel win rate across continental fixtures.',
  ),
];

class ActiveCompetitionItem {
  const ActiveCompetitionItem({
    required this.name,
    required this.type,
    required this.format,
    required this.prizePool,
    required this.currency,
    required this.status,
    required this.slotsTotal,
    required this.slotsFilled,
    required this.accentColor,
    required this.broadcastAvailable,
  });

  final String name;
  final String type;
  final String format;
  final String prizePool;
  final String currency;
  final String status;
  final int slotsTotal;
  final int slotsFilled;
  final Color accentColor;
  final bool broadcastAvailable;
}

const List<ActiveCompetitionItem> kCompetitionFormatPreviews = <ActiveCompetitionItem>[
  ActiveCompetitionItem(
    name: 'Continental Prestige League',
    type: 'League Season',
    format: 'Double round-robin league format',
    prizePool: 'See published event rules',
    currency: '',
    status: 'FORMAT PREVIEW',
    slotsTotal: 0,
    slotsFilled: 0,
    accentColor: Color(0xFFD4AF37),
    broadcastAvailable: false,
  ),
  ActiveCompetitionItem(
    name: 'West Africa Elite Circuit',
    type: 'Invitational Cup',
    format: 'Group stage followed by knockout rounds',
    prizePool: 'See published event rules',
    currency: '',
    status: 'FORMAT PREVIEW',
    slotsTotal: 0,
    slotsFilled: 0,
    accentColor: Color(0xFF10B981),
    broadcastAvailable: false,
  ),
  ActiveCompetitionItem(
    name: 'Atlantic Prospect Series',
    type: 'U21 Showcase',
    format: 'Knockout tournament for emerging talent',
    prizePool: 'See published event rules',
    currency: '',
    status: 'FORMAT PREVIEW',
    slotsTotal: 0,
    slotsFilled: 0,
    accentColor: Color(0xFF3B82F6),
    broadcastAvailable: false,
  ),
];
