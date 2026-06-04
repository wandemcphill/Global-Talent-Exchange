import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/core/theme/app_theme.dart';
import 'package:gte_frontend/features/regen_world/regen_world.dart';
import 'package:gte_frontend/models/regen_creation_models.dart';
import 'package:gte_frontend/models/regen_universe_models.dart';
import 'package:gte_frontend/shared/providers/regen_provider.dart';

void main() {
  testWidgets('renders v13 Regen World facts from backend data', (
    WidgetTester tester,
  ) async {
    await _pumpRegenWorld(tester, data: _completeHubData());

    expect(find.text('Regen World'), findsWidgets);
    expect(find.text('Discover Regen Talent'), findsOneWidget);
    expect(find.text('Kwame Jr.'), findsOneWidget);
    expect(find.text('GEN-2'), findsWidgets);
    expect(find.text('Ghana'), findsWidgets);
    expect(find.text('rare'), findsWidgets);
    expect(find.text('GTC 1.8M'), findsWidgets);
    expect(find.text('Ghost Goal'), findsWidgets);

    await tester.tap(find.text('Kwame Jr.'));
    await tester.pumpAndSettle();

    expect(find.text('DNA Radar'), findsOneWidget);
    expect(find.text('Lineage Tree'), findsOneWidget);
    expect(find.text('Kwame Sr.'), findsOneWidget);
    expect(find.text('Asante G.'), findsOneWidget);
    expect(find.text('Lagos Academy'), findsOneWidget);
    expect(find.text('Market Access'), findsOneWidget);
    expect(find.text('National pool only'), findsWidgets);
    expect(find.text('Buy CTA hidden'), findsOneWidget);
    expect(find.text('View dossier'), findsOneWidget);
    expect(find.text('Timeline hidden'), findsWidgets);
    expect(find.text('Watchlist hidden'), findsOneWidget);
    expect(find.text('Backend Fields'), findsOneWidget);
    expect(find.text('DNA published'), findsOneWidget);
    expect(find.text('Market Access published'), findsOneWidget);
  });

  testWidgets('shows blocked and degraded states for missing backend fields', (
    WidgetTester tester,
  ) async {
    await _pumpRegenWorld(tester, data: _missingFieldsHubData());

    expect(find.text('Backend Pending Prospect'), findsOneWidget);
    expect(find.text('Backend truth blocked'), findsWidgets);
    expect(find.text('Position not published'), findsWidgets);
    expect(find.text('Nationality not published'), findsWidgets);
    expect(find.text('Projected value not published'), findsWidgets);

    await tester.tap(find.text('Backend Pending Prospect'));
    await tester.pumpAndSettle();

    expect(
      find.text(
        'Missing backend fields: generation, position, potential, current rating, traits, lineage, DNA, origin story, projected value, market access, rarity, nationality.',
      ),
      findsOneWidget,
    );
    expect(find.text('Traits not published by backend.'), findsOneWidget);
    expect(find.text('Lineage not published by backend.'), findsOneWidget);
    expect(find.text('DNA not published by backend.'), findsOneWidget);
    expect(
      find.text('Market access not published by backend.'),
      findsOneWidget,
    );
  });

  testWidgets('shows partial feed degradation without hiding published data', (
    WidgetTester tester,
  ) async {
    await _pumpRegenWorld(
      tester,
      data: _completeHubData(
        degradedFeeds: const <String>['Scouting feed', 'Bloodlines'],
      ),
    );

    expect(find.text('Kwame Jr.'), findsOneWidget);
    expect(find.text('Backend truth degraded'), findsOneWidget);
    expect(find.textContaining('Scouting feed'), findsOneWidget);
    expect(find.textContaining('Bloodlines'), findsOneWidget);
    expect(
      find.textContaining('Published backend data is shown'),
      findsOneWidget,
    );
  });

  testWidgets('uses reusable loading and error panels', (
    WidgetTester tester,
  ) async {
    final Completer<RegenUniverseHubData> completer =
        Completer<RegenUniverseHubData>();

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          regenUniverseHubProvider.overrideWith((Ref ref) => completer.future),
        ],
        child: MaterialApp(
          theme: AppTheme.dark(),
          home: const Scaffold(body: RegenWorldScreen()),
        ),
      ),
    );

    expect(find.text('Syncing Regen World'), findsOneWidget);
    completer.complete(_completeHubData());
    await tester.pumpAndSettle();

    await tester.pumpWidget(
      ProviderScope(
        key: UniqueKey(),
        overrides: [
          regenUniverseHubProvider.overrideWith(
            (Ref ref) async => throw StateError('lineage endpoint unavailable'),
          ),
        ],
        child: MaterialApp(
          theme: AppTheme.dark(),
          home: const Scaffold(body: RegenWorldScreen()),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Regen World is blocked'), findsOneWidget);
    expect(find.textContaining('lineage endpoint unavailable'), findsOneWidget);
  });
}

Future<void> _pumpRegenWorld(
  WidgetTester tester, {
  required RegenUniverseHubData data,
}) async {
  tester.view.physicalSize = const Size(1200, 1600);
  tester.view.devicePixelRatio = 1;
  addTearDown(() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  });

  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        regenUniverseHubProvider.overrideWith((Ref ref) async => data),
      ],
      child: MaterialApp(
        theme: AppTheme.dark(),
        home: const Scaffold(body: RegenWorldScreen()),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

RegenUniverseHubData _completeHubData({
  List<String> degradedFeeds = const <String>[],
}) {
  const RegenWorldDnaProfileData dna = RegenWorldDnaProfileData();
  return _hubData(
    degradedFeeds: degradedFeeds,
    nationalRegens: <NationalRegenSeed>[
      NationalRegenSeed(
        id: 'kwame',
        seedKey: 'seed:gh:kwame',
        displayName: 'Kwame Jr.',
        age: 17,
        countryCode: 'GH',
        countryName: 'Ghana',
        seedType: 'national_seed',
        primaryPosition: 'CAM',
        generationIndex: 2,
        currentRating: 72,
        potentialRating: 82,
        growthCurve: 0.76,
        personalitySeed: const <String, Object?>{
          'traits': <String>['Ghost Goal', 'Dribbler', 'Leadership'],
          'lineage': <String>['Kwame Sr.', 'Asante G.', 'Kwame Jr.'],
        },
        rarityTier: 'rare',
        metadata: <String, Object?>{
          'origin_story': 'Lagos Academy',
          'projected_value_coin': 1800000,
          'dna': dna.values,
        },
      ),
    ],
  );
}

RegenUniverseHubData _missingFieldsHubData() {
  return _hubData(
    risingStars: const <RegenRisingStar>[
      RegenRisingStar(
        playerId: 'blocked-1',
        player: RegenUniversePlayer(
          id: 'blocked-1',
          name: 'Backend Pending Prospect',
          age: 18,
          nationality: '',
          nationalityCode: null,
          position: '',
          potential: 0,
          currentRating: 0,
          growthCurve: 0.1,
          sourceType: 'generated',
        ),
        momentumLabel: 'Pending sync',
        storySnippet: null,
        badges: <String>[],
        marketValueCoin: null,
      ),
    ],
  );
}

RegenUniverseHubData _hubData({
  List<RegenRisingStar> risingStars = const <RegenRisingStar>[],
  List<NationalRegenSeed> nationalRegens = const <NationalRegenSeed>[],
  List<String> degradedFeeds = const <String>[],
}) {
  return RegenUniverseHubData(
    risingStars: risingStars,
    awards: const <RegenAwardResult>[],
    nationalRegens: nationalRegens,
    scoutingFeed: const <RegenScoutingFeedItem>[],
    bloodlines: const <RegenBloodlineChain>[],
    tracking: const RegenGenerationTracking(
      totalSeededPlayers: 0,
      seedTypes: <RegenGenerationTrackingEntry>[],
      rarityBreakdown: <RegenGenerationTrackingEntry>[],
      countryDistribution: <RegenGenerationTrackingEntry>[],
      globalPeakRating: 0,
      trackedAchievements: <String>[],
    ),
    creationOrders: const <RegenCreationOrder>[],
    degradedFeeds: degradedFeeds,
  );
}

class RegenWorldDnaProfileData {
  const RegenWorldDnaProfileData();

  Map<String, Object?> get values => const <String, Object?>{
    'PAC': 84,
    'SHO': 78,
    'PAS': 75,
    'DRI': 88,
    'DEF': 42,
    'PHY': 71,
  };
}
