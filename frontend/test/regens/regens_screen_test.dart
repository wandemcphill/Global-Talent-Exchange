import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/core/theme/app_theme.dart';
import 'package:gte_frontend/features/regens/regens_screen.dart';
import 'package:gte_frontend/models/regen_creation_models.dart';
import 'package:gte_frontend/models/regen_universe_models.dart';
import 'package:gte_frontend/shared/models/auth_session.dart';
import 'package:gte_frontend/shared/providers/auth_provider.dart';
import 'package:gte_frontend/shared/providers/regen_provider.dart';

void main() {
  testWidgets('live regen universe shows a visible error instead of fixtures', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          regenUniverseHubProvider.overrideWith(
            (Ref ref) async => throw StateError('Backend unavailable.'),
          ),
        ],
        child: MaterialApp(
          theme: AppTheme.dark(),
          home: const Scaffold(body: RegensScreen()),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Prospect scouting is blocked'), findsOneWidget);
    expect(find.textContaining('Backend unavailable'), findsOneWidget);
    expect(find.text('Mateus Sol'), findsNothing);
  });

  testWidgets('regen universe renders live awards and requested sons', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          authProvider.overrideWith(
            (Ref ref) => const AuthSession(
              userId: 'user-1',
              accessToken: 'token-1',
              refreshToken: '',
              sessionId: 'session-1',
              role: 'user',
            ),
          ),
          regenUniverseHubProvider.overrideWith(
            (Ref ref) async => _sampleHubData(),
          ),
        ],
        child: MaterialApp(
          theme: AppTheme.dark(),
          home: const Scaffold(body: RegensScreen()),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('GTEX World Player of the Year'), findsOneWidget);
    expect(find.text('Azeez Salisu'), findsOneWidget);
    expect(find.text('National Pool'), findsWidgets);
    expect(find.text('Rental Only'), findsWidgets);
    expect(find.text('Not Tradable'), findsWidgets);
    expect(find.text('Seyi Adewale'), findsOneWidget);
    expect(find.text('Requested Son'), findsWidgets);
    expect(
      find.textContaining('Bloodline Regen', findRichText: true),
      findsWidgets,
    );
  });

  testWidgets('regen world marks incomplete backend records as sync states', (
    WidgetTester tester,
  ) async {
    await _pumpRegensScreen(tester, _closureHubData());

    expect(find.textContaining('Backend sync pending'), findsWidgets);
    expect(
      find.textContaining('Missing backend truth: generation'),
      findsWidgets,
    );
    expect(find.textContaining('Backend truth blocked'), findsWidgets);
    expect(find.textContaining('Nationality pending'), findsWidgets);
    expect(find.textContaining('Unknown Prospect'), findsNothing);
  });

  testWidgets(
    'regen world searches filters and sorts backend-published truth',
    (WidgetTester tester) async {
      await _pumpRegensScreen(tester, _closureHubData());

      await tester.enterText(find.byType(TextField), 'PAC 96');
      await tester.pumpAndSettle();
      expect(find.textContaining('Kojo Armah / GEN-3'), findsOneWidget);
      expect(find.textContaining('Tomas Silva / GEN-2'), findsNothing);

      await tester.enterText(find.byType(TextField), 'Adade Line');
      await tester.pumpAndSettle();
      expect(find.textContaining('Kojo Armah / GEN-3'), findsOneWidget);
      expect(find.textContaining('Tomas Silva / GEN-2'), findsNothing);

      await tester.enterText(find.byType(TextField), 'Aerial Threat');
      await tester.pumpAndSettle();
      expect(find.textContaining('Tomas Silva / GEN-2'), findsOneWidget);
      expect(find.textContaining('Kojo Armah / GEN-3'), findsNothing);

      await tester.enterText(find.byType(TextField), '1.2M');
      await tester.pumpAndSettle();
      expect(find.textContaining('Tomas Silva / GEN-2'), findsOneWidget);
      expect(find.textContaining('Kojo Armah / GEN-3'), findsNothing);

      await tester.enterText(find.byType(TextField), '');
      await tester.pumpAndSettle();

      await tester.tap(find.text('GEN-3'));
      await tester.pumpAndSettle();
      expect(find.textContaining('Kojo Armah / GEN-3'), findsOneWidget);
      expect(find.textContaining('Tomas Silva / GEN-2'), findsNothing);

      await tester.tap(find.text('All Generations'));
      await tester.pumpAndSettle();
      await _selectDropdownOption(tester, 'All Nationalities', 'Brazil');
      expect(find.textContaining('Tomas Silva / GEN-2'), findsOneWidget);
      expect(find.textContaining('Kojo Armah / GEN-3'), findsNothing);

      await _selectDropdownOption(tester, 'Brazil', 'All Nationalities');
      await _selectDropdownOption(tester, 'All Rarities', 'mythic');
      expect(find.textContaining('Kojo Armah / GEN-3'), findsOneWidget);
      expect(find.textContaining('Tomas Silva / GEN-2'), findsNothing);

      await _selectDropdownOption(tester, 'mythic', 'All Rarities');
      await tester.tap(find.text('Sort: Potential'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Sort: Value').last);
      await tester.pumpAndSettle();

      final Finder tomas = find.textContaining('Tomas Silva / GEN-2');
      final Finder kojo = find.textContaining('Kojo Armah / GEN-3');
      expect(tomas, findsOneWidget);
      expect(kojo, findsOneWidget);
      expect(tester.getTopLeft(tomas).dy, lessThan(tester.getTopLeft(kojo).dy));
    },
  );
}

Future<void> _pumpRegensScreen(
  WidgetTester tester,
  RegenUniverseHubData data,
) async {
  tester.view.physicalSize = const Size(1400, 1800);
  tester.view.devicePixelRatio = 1;
  addTearDown(() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  });

  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        authProvider.overrideWith(
          (Ref ref) => const AuthSession(
            userId: 'user-1',
            accessToken: 'token-1',
            refreshToken: '',
            sessionId: 'session-1',
            role: 'user',
          ),
        ),
        regenUniverseHubProvider.overrideWith((Ref ref) async => data),
      ],
      child: MaterialApp(
        theme: AppTheme.dark(),
        home: const Scaffold(body: RegensScreen()),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

Future<void> _selectDropdownOption(
  WidgetTester tester,
  String currentLabel,
  String optionLabel,
) async {
  await tester.tap(find.text(currentLabel));
  await tester.pumpAndSettle();
  await tester.tap(find.text(optionLabel).last);
  await tester.pumpAndSettle();
}

RegenUniverseHubData _sampleHubData() {
  const RegenMarketAccess nationalOnlyAccess = RegenMarketAccess(
    marketEligible: false,
    shareMarketEligible: false,
    tradable: false,
    buyable: false,
    transferable: false,
    cardMintEligible: false,
    buyCtaAllowed: false,
    isPreseededNationalRegen: true,
    nationalPoolOnly: true,
  );
  const NationalRegenSeed nationalSeed = NationalRegenSeed(
    id: 'seed-1',
    seedKey: 'seed:ng:1',
    displayName: 'Azeez Salisu',
    age: 16,
    ageBand: 'u17',
    countryCode: 'NG',
    countryName: 'Nigeria',
    seedType: 'national_seed',
    primaryPosition: 'RW',
    currentRating: 71,
    potentialRating: 90,
    growthCurve: 0.81,
    rarityTier: 'elite',
    status: 'active',
    metadata: <String, Object?>{},
    marketEligible: false,
    shareMarketEligible: false,
    tradable: false,
    buyable: false,
    transferable: false,
    cardMintEligible: false,
    buyCtaAllowed: false,
    isPreseededNationalRegen: true,
    nationalPoolOnly: true,
  );
  const RegenUniversePlayer clubRegen = RegenUniversePlayer(
    id: 'regen-1',
    name: 'Chidera Onwubiko',
    age: 18,
    nationality: 'Nigeria',
    nationalityCode: 'NG',
    position: 'AM',
    potential: 90,
    currentRating: 74,
    growthCurve: 0.79,
    sourceType: 'generated',
    clubId: 'club-1',
  );
  return RegenUniverseHubData(
    risingStars: const <RegenRisingStar>[
      RegenRisingStar(
        playerId: 'regen-1',
        player: clubRegen,
        momentumLabel: 'Breakout form',
        storySnippet: 'Creative midfielder surging through the academy lane.',
        badges: <String>['Scouting Pulse'],
        marketValueCoin: 240000,
      ),
    ],
    awards: <RegenAwardResult>[
      RegenAwardResult(
        award: const RegenAwardDefinition(
          id: 'award-1',
          code: 'BALLON_DOR',
          name: 'GTEX World Player of the Year',
          description: 'Best overall regen season.',
          category: 'season',
        ),
        season: RegenAwardSeason(
          id: 'season-1',
          seasonNumber: 2031,
          startDate: DateTime.utc(2031, 1, 1),
          endDate: DateTime.utc(2031, 12, 31),
        ),
        winners: <RegenAwardWinner>[
          RegenAwardWinner(
            id: 'winner-1',
            playerId: 'regen-1',
            playerName: 'Chidera Onwubiko',
            rankingScore: 97.2,
            rank: 1,
            awardedAt: DateTime.utc(2031, 12, 31),
            metadata: <String, Object?>{
              'source_type': 'generated',
              'club_id': 'club-1',
            },
          ),
        ],
      ),
    ],
    nationalRegens: <NationalRegenSeed>[nationalSeed],
    bloodlines: const <RegenBloodlineChain>[],
    scoutingFeed: <RegenScoutingFeedItem>[
      RegenScoutingFeedItem(
        feedId: 'feed-1',
        feedType: 'new_regen_discovered',
        title: 'A new national-pool winger lands on the watchlist',
        summary: 'Nigeria publishes another U17 right winger.',
        occurredAt: DateTime.utc(2031, 5, 1),
        importance: 0.8,
        badges: <String>['National Pool'],
        player: RegenUniversePlayer(
          id: 'seed-1',
          name: 'Azeez Salisu',
          age: 16,
          nationality: 'Nigeria',
          nationalityCode: 'NG',
          position: 'RW',
          potential: 90,
          currentRating: 71,
          growthCurve: 0.81,
          sourceType: 'national_seed',
          marketAccess: nationalOnlyAccess,
        ),
      ),
    ],
    tracking: const RegenGenerationTracking(
      totalSeededPlayers: 240,
      seedTypes: <RegenGenerationTrackingEntry>[
        RegenGenerationTrackingEntry(
          bucket: 'national_seed',
          count: 200,
          peakRating: 93,
          achievements: <String>[],
          metadata: <String, Object?>{},
        ),
      ],
      rarityBreakdown: <RegenGenerationTrackingEntry>[],
      countryDistribution: <RegenGenerationTrackingEntry>[
        RegenGenerationTrackingEntry(
          bucket: 'Nigeria',
          count: 24,
          peakRating: 90,
          achievements: <String>[],
          metadata: <String, Object?>{},
        ),
      ],
      globalPeakRating: 96,
      trackedAchievements: <String>[],
    ),
    creationOrders: <RegenCreationOrder>[
      RegenCreationOrder(
        id: 'order-1',
        userId: 'user-1',
        clubId: 'club-1',
        requestType: 'son',
        parentPlayerId: 'player-parent',
        requestedName: 'Seyi Adewale',
        requestedCountryCode: 'NG',
        requestedPosition: 'ST',
        amountCoin: 2500,
        currency: 'COIN',
        paymentMethod: 'wallet',
        status: 'generated',
        createdAt: DateTime.utc(2031, 3, 1),
        updatedAt: DateTime.utc(2031, 3, 1),
        generatedPlayerId: 'player-son',
        generatedRegenProfileId: 'regen-son',
        generatedAt: DateTime.utc(2031, 3, 1),
        generatedPlayer: RegenCreationGeneratedPlayer(
          playerId: 'player-son',
          regenProfileId: 'regen-son',
          fullName: 'Seyi Adewale',
          age: 15,
          position: 'ST',
          currentRating: 68,
          potentialRating: 89,
          countryCode: 'NG',
          countryName: 'Nigeria',
          clubId: 'club-1',
          clubName: 'Lagos Atlas',
        ),
      ),
    ],
  );
}

RegenUniverseHubData _closureHubData() {
  const RegenUniversePlayer kojo = RegenUniversePlayer(
    id: 'kojo-armah',
    name: 'Kojo Armah',
    age: 17,
    nationality: 'Ghana',
    nationalityCode: 'GH',
    position: 'CM',
    potential: 86,
    currentRating: 72,
    growthCurve: 0.84,
    sourceType: 'generated',
    clubId: 'club-ghana',
    generationNumber: 3,
    generationLabel: 'GEN-3',
    rarityTier: 'mythic',
    originStory: 'Accra academy creator with late-blooming press resistance.',
    projectedValueCoin: 950000,
    traits: <String>['Press Resistant'],
    lineage: <String>['Adade Line'],
    dnaProfile: RegenDnaProfile(
      ratings: <String, int>{
        'PAC': 96,
        'SHO': 72,
        'PAS': 88,
        'DRI': 91,
        'DEF': 64,
        'PHY': 78,
      },
    ),
  );
  const RegenUniversePlayer tomas = RegenUniversePlayer(
    id: 'tomas-silva',
    name: 'Tomas Silva',
    age: 16,
    nationality: 'Brazil',
    nationalityCode: 'BR',
    position: 'ST',
    potential: 84,
    currentRating: 69,
    growthCurve: 0.78,
    sourceType: 'generated',
    clubId: 'club-brazil',
    generationNumber: 2,
    generationLabel: 'GEN-2',
    rarityTier: 'elite',
    originStory: 'Sao Paulo finisher projected for high-value aerial growth.',
    projectedValueCoin: 1200000,
    traits: <String>['Aerial Threat'],
    lineage: <String>['Silva Ladder'],
    dnaProfile: RegenDnaProfile(
      ratings: <String, int>{
        'PAC': 82,
        'SHO': 89,
        'PAS': 67,
        'DRI': 81,
        'DEF': 45,
        'PHY': 92,
      },
    ),
  );
  const RegenUniversePlayer incomplete = RegenUniversePlayer(
    id: 'sync-pending',
    name: 'Nnamdi Okoro',
    age: 15,
    nationality: 'Nigeria',
    nationalityCode: 'NG',
    position: 'RW',
    potential: 81,
    currentRating: 63,
    growthCurve: 0.71,
    sourceType: 'generated',
    clubId: 'club-ng',
  );

  return RegenUniverseHubData(
    risingStars: <RegenRisingStar>[
      RegenRisingStar(
        playerId: kojo.id,
        player: kojo,
        momentumLabel: 'Backend direct truth',
        storySnippet: null,
        badges: const <String>[],
        marketValueCoin: null,
        details: _sparseDetailsFor(kojo),
      ),
      RegenRisingStar(
        playerId: tomas.id,
        player: tomas,
        momentumLabel: 'Backend direct truth',
        storySnippet: null,
        badges: const <String>[],
        marketValueCoin: null,
        details: _sparseDetailsFor(tomas),
      ),
      RegenRisingStar(
        playerId: incomplete.id,
        player: incomplete,
        momentumLabel: 'Awaiting backend profile',
        storySnippet: null,
        badges: const <String>[],
        marketValueCoin: null,
        details: _sparseDetailsFor(incomplete),
      ),
    ],
    awards: const <RegenAwardResult>[],
    nationalRegens: const <NationalRegenSeed>[],
    bloodlines: const <RegenBloodlineChain>[],
    scoutingFeed: const <RegenScoutingFeedItem>[],
    tracking: _emptyTracking,
    creationOrders: <RegenCreationOrder>[
      RegenCreationOrder(
        id: 'blocked-order',
        userId: 'user-1',
        clubId: 'club-1',
        requestType: 'son',
        parentPlayerId: 'parent-1',
        requestedName: 'Kai Pending',
        requestedPosition: 'ST',
        amountCoin: 2500,
        currency: 'COIN',
        paymentMethod: 'wallet',
        status: 'generated',
        createdAt: DateTime.utc(2032, 1, 1),
        updatedAt: DateTime.utc(2032, 1, 1),
        generatedPlayerId: 'blocked-player',
        generatedRegenProfileId: 'blocked-profile',
        generatedAt: DateTime.utc(2032, 1, 1),
        generatedPlayer: const RegenCreationGeneratedPlayer(
          playerId: 'blocked-player',
          regenProfileId: 'blocked-profile',
          fullName: 'Kai Pending',
          age: 15,
          position: 'ST',
          currentRating: 62,
          potentialRating: 82,
          generationNumber: 2,
          generationLabel: 'GEN-2',
          traits: <String>['Late Runner'],
          lineage: <String>['Pending Line'],
          dnaProfile: RegenDnaProfile(
            ratings: <String, int>{
              'PAC': 74,
              'SHO': 79,
              'PAS': 61,
              'DRI': 75,
              'DEF': 38,
              'PHY': 70,
            },
          ),
          originStory: 'Awaiting backend country assignment.',
          projectedValueCoin: 300000,
          rarityTier: 'rare',
        ),
      ),
    ],
  );
}

RegenWorldDetails _sparseDetailsFor(RegenUniversePlayer player) {
  return RegenWorldDetails(
    key: player.id,
    name: player.name,
    nationality: player.nationality,
    nationalityCode: player.nationalityCode,
    position: player.position,
    age: player.age,
    currentRating: player.currentRating,
    potentialRating: player.potential,
  );
}

const RegenGenerationTracking _emptyTracking = RegenGenerationTracking(
  totalSeededPlayers: 0,
  seedTypes: <RegenGenerationTrackingEntry>[],
  rarityBreakdown: <RegenGenerationTrackingEntry>[],
  countryDistribution: <RegenGenerationTrackingEntry>[],
  globalPeakRating: 0,
  trackedAchievements: <String>[],
);
