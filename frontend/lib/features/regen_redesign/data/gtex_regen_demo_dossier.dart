import '../models/gtex_regen_dossier.dart';
import '../models/gtex_regen_wire_models.dart';

/// Fixture regen dossier for the demo repository and widget tests.
///
/// This mirrors the shape of a real `GET /regen-universe/players/{id}`
/// response, including the parts that are legitimately absent, so tests
/// exercise the same rendering paths as live data. It is reachable only from
/// the demo repository, which is itself fixture-only.
GtexRegenDossier demoRegenDossier(String playerId) {
  final DateTime now = DateTime.utc(2026, 9, 1);
  return GtexRegenDossier(
    playerId: playerId,
    showcase: RegenPlayerShowcase(
      playerId: playerId,
      profile: RegenProfileDetail(
        id: 'profile-$playerId',
        regenId: 'regen-$playerId',
        displayName: 'Kelechi Aruna',
        age: 17,
        primaryPosition: 'AM',
        currentGsi: 69,
        scoutConfidence: 'medium',
        generationSource: 'requested_son',
        regenType: 'legend_regen',
        status: 'active',
        uniquenessScore: 0.82,
        growthCurve: 0.74,
        playerId: playerId,
        currentRating: 69,
        potential: 91,
        currentAbilityRange: const RegenAbilityRange(minimum: 64, maximum: 72),
        potentialRange: const RegenAbilityRange(minimum: 84, maximum: 93),
        personality: const RegenPersonality(
          temperament: 62,
          leadership: 71,
          ambition: 88,
          loyalty: 54,
          professionalism: 76,
          workRate: 83,
          flair: 90,
          resilience: 66,
          tags: <String>['Flair', 'Big Match', 'Ambitious'],
        ),
        origin: const RegenOrigin(
          countryCode: 'NGA',
          regionName: 'Lagos State',
          cityName: 'Lagos',
          urbanicity: 'urban',
        ),
        lineage: const RegenLineageDescriptor(
          relationshipType: 'son',
          relatedLegendType: 'player',
          relatedLegendRefId: 'p-001',
          lineageTier: 'elite',
          narrativeText:
              'Carries the Adebayo name into a generation that never saw his '
              'father play.',
          isOwnerSon: true,
          tags: <String>['Bloodline Regen'],
        ),
      ),
      personalityTag: 'Street Maestro',
      storySnippet: 'Created from a premium parent line.',
      prestige: const RegenPrestigeSummary(
        totalAwards: 2,
        seasonsActive: 1,
        legacyScore: 41.5,
        peakRank: 4,
      ),
      legacy: const RegenLegacySnapshot(
        totalMatches: 24,
        goals: 11,
        assists: 7,
        trophies: 1,
        peakRating: 72,
        seasonsTotal: 1,
        awardsTotal: 2,
        legacyScore: 41.5,
        legacyTier: 'rising',
        isLegend: false,
      ),
      latestValue: RegenValueBreakdown(
        currentValueCoin: 68000,
        abilityComponent: 21000,
        potentialComponent: 30000,
        reputationComponent: 9000,
        narrativeComponent: 5000,
        demandComponent: 3000,
        calculatedAt: now,
      ),
      discoveryBadges: const <String>['Wonderkid', 'Bloodline'],
      timeline: <RegenStoryEvent>[
        RegenStoryEvent(
          id: 'evt-1',
          eventType: 'debut',
          title: 'Senior debut',
          summary: 'Came off the bench in the GTEX U20 quarter-final.',
          occurredAt: now.subtract(const Duration(days: 30)),
        ),
        RegenStoryEvent(
          id: 'evt-2',
          eventType: 'milestone',
          title: 'First senior hat-trick',
          summary: 'Scored three in the GTEX U20 semi-final.',
          occurredAt: now.subtract(const Duration(days: 3)),
        ),
      ],
      achievements: <RegenPlayerAchievement>[
        RegenPlayerAchievement(
          id: 'ach-1',
          achievementType: 'award',
          title: 'U17 Breakthrough',
          description: 'Named breakthrough regen of the season.',
          earnedAt: now.subtract(const Duration(days: 10)),
        ),
      ],
    ),
    lineageChain: const <RegenLineageChainNode>[
      RegenLineageChainNode(
        regenProfileId: 'profile-origin',
        regenId: 'regen-origin',
        displayName: 'Victor Adebayo',
        legacyScore: 88.0,
        legacyTier: 'legend',
      ),
      RegenLineageChainNode(
        regenProfileId: 'profile-r-001',
        regenId: 'regen-r-001',
        displayName: 'Kelechi Aruna',
        parentLegacyId: 'regen-origin',
        legacyScore: 41.5,
        legacyTier: 'rising',
      ),
    ],
  );
}

/// Fixture bloodlines for the demo repository and widget tests.
List<RegenBloodlineChain> demoRegenBloodlines() {
  return const <RegenBloodlineChain>[
    RegenBloodlineChain(
      bloodlineKey: 'bl-adebayo',
      originLabel: 'Victor Adebayo',
      originRefId: 'p-001',
      originType: 'player',
      driftScore: 0.24,
      entries: <RegenBloodlineMember>[
        RegenBloodlineMember(
          playerId: 'r-001',
          regenId: 'regen-r-001',
          displayName: 'Kelechi Aruna',
          regenType: 'legend_regen',
          generationIndex: 1,
          primaryPosition: 'AM',
          currentRating: 69,
          potential: 91,
          legacyScore: 41.5,
          storySnippet: 'Carries the Adebayo name.',
        ),
      ],
    ),
  ];
}

/// Fixture rankings for the demo repository and widget tests.
List<RegenRankingEntry> demoRegenRankings() {
  return const <RegenRankingEntry>[
    RegenRankingEntry(
      id: 'rank-1',
      playerId: 'r-001',
      playerName: 'Kelechi Aruna',
      category: 'overall',
      score: 94.2,
      rank: 1,
    ),
    RegenRankingEntry(
      id: 'rank-2',
      playerId: 'r-003',
      playerName: 'Joao Varella',
      category: 'overall',
      score: 91.7,
      rank: 2,
    ),
  ];
}

/// Fixture hall-of-fame rows for the demo repository and widget tests.
List<RegenHallOfFameEntry> demoRegenHallOfFame() {
  return const <RegenHallOfFameEntry>[
    RegenHallOfFameEntry(
      id: 'hof-1',
      playerId: 'p-legend-1',
      playerName: 'Victor Adebayo',
      totalAwards: 9,
      seasonsActive: 14,
      legacyScore: 88.0,
      peakRank: 1,
    ),
  ];
}
