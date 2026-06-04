import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/core/theme/app_theme.dart';
import 'package:gte_frontend/features/regens/regens_screen.dart';
import 'package:gte_frontend/models/regen_creation_models.dart';
import 'package:gte_frontend/models/regen_universe_models.dart';
import 'package:gte_frontend/shared/providers/auth_provider.dart';
import 'package:gte_frontend/shared/providers/regen_provider.dart';

void main() {
  testWidgets(
    'guest Regen World keeps Build-a-Son gated and shows live facts',
    (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1200, 1600);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authProvider.overrideWith((Ref ref) => null),
            regenUniverseHubProvider.overrideWith(
              (Ref ref) async => _hubDataWithRequestedSon(),
            ),
          ],
          child: MaterialApp(
            theme: AppTheme.dark(),
            home: const Scaffold(body: RegensScreen()),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('LIVE TALENT MAP'), findsOneWidget);
      expect(find.text('National Pool'), findsWidgets);
      expect(find.text('Rental Only'), findsWidgets);
      expect(find.text('Not Tradable'), findsWidgets);
      expect(find.text('Azeez Salisu'), findsWidgets);
      expect(find.text('TOTAL TRACKED'), findsOneWidget);
      expect(find.text('LEADING COUNTRY'), findsOneWidget);
      expect(find.text('Nigeria (24)'), findsOneWidget);

      final Finder buildASonButton = find.widgetWithText(
        FilledButton,
        'Build-a-Son',
      );
      expect(buildASonButton, findsOneWidget);
      expect(tester.widget<FilledButton>(buildASonButton).onPressed, isNull);
      expect(
        find.text('Sign in to load your live request-son orders.'),
        findsOneWidget,
      );
      expect(find.text('Seyi Adewale'), findsNothing);
    },
  );
}

RegenUniverseHubData _hubDataWithRequestedSon() {
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
            metadata: <String, Object?>{'source_type': 'generated'},
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
      seedTypes: <RegenGenerationTrackingEntry>[],
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
        generatedPlayer: const RegenCreationGeneratedPlayer(
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
