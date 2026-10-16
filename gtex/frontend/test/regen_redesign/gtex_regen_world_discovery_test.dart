import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/player_detail/gtex_player_navigator.dart';
import 'package:gte_frontend/features/regen_redesign/data/gtex_regen_demo_dossier.dart';
import 'package:gte_frontend/features/regen_redesign/data/gtex_regen_repository.dart';
import 'package:gte_frontend/features/regen_redesign/models/gtex_regen_dossier.dart';
import 'package:gte_frontend/features/regen_redesign/models/gtex_regen_models.dart';
import 'package:gte_frontend/features/regen_redesign/models/gtex_regen_wire_models.dart';
import 'package:gte_frontend/features/regen_redesign/presentation/gtex_regen_world_screen_v2.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

/// Regen World's job is DISCOVER -> LINEAGE -> POTENTIAL -> DEVELOP -> OWN ->
/// TRACK. These cover the lanes that carry that loop, and the honest states
/// each one falls back to when the backend has published nothing.
class _EmptyWorldRepository extends DemoGtexRegenRepository {
  const _EmptyWorldRepository();

  @override
  Future<List<RegenBloodlineChain>> loadBloodlines() async =>
      const <RegenBloodlineChain>[];

  @override
  Future<List<RegenRankingEntry>> loadRankings() async =>
      const <RegenRankingEntry>[];

  @override
  Future<List<RegenHallOfFameEntry>> loadHallOfFame() async =>
      const <RegenHallOfFameEntry>[];
}

class _FailingBloodlineRepository extends DemoGtexRegenRepository {
  const _FailingBloodlineRepository();

  @override
  Future<List<RegenBloodlineChain>> loadBloodlines() async {
    throw StateError('bloodlines endpoint unreachable');
  }
}

void main() {
  Future<void> pumpWorld(
    WidgetTester tester, {
    GtexRegenRepository repository = const DemoGtexRegenRepository(),
    Future<void> Function(String playerId)? openPlayer,
    Size size = const Size(1440, 1400),
  }) async {
    tester.view.physicalSize = size;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    Widget screen = GtexRegenWorldScreenV2.fixture(repository: repository);
    if (openPlayer != null) {
      screen = GtexPlayerNavigator(openPlayer: openPlayer, child: screen);
    }
    await tester.pumpWidget(MaterialApp(home: Scaffold(body: screen)));
    await tester.pumpAndSettle();
  }

  Future<void> openSection(WidgetTester tester, String label) async {
    await tester.tap(find.text(label).first);
    await tester.pumpAndSettle();
  }

  group('discovery lanes', () {
    testWidgets('bloodlines lane renders origins and their descendants', (
      WidgetTester tester,
    ) async {
      await pumpWorld(tester);
      await openSection(tester, 'Bloodlines');

      expect(find.text('Victor Adebayo'), findsWidgets);
      expect(find.text('G1'), findsWidgets);
      expect(find.textContaining('1 descendant'), findsOneWidget);
    });

    testWidgets('rankings lane renders the live leaderboard in rank order', (
      WidgetTester tester,
    ) async {
      await pumpWorld(tester);
      await openSection(tester, 'Rankings');

      expect(find.text('#1'), findsOneWidget);
      expect(find.text('#2'), findsOneWidget);
      expect(
        tester.getTopLeft(find.text('#1')).dy,
        lessThan(tester.getTopLeft(find.text('#2')).dy),
      );
    });

    testWidgets('hall of fame lane renders finished careers', (
      WidgetTester tester,
    ) async {
      await pumpWorld(tester);
      await openSection(tester, 'Hall of Fame');

      expect(find.text('9 awards'), findsOneWidget);
      expect(find.textContaining('peak #1'), findsOneWidget);
    });
  });

  group('empty and error states', () {
    testWidgets('an unpopulated lane says so rather than rendering blank', (
      WidgetTester tester,
    ) async {
      await pumpWorld(tester, repository: const _EmptyWorldRepository());
      await openSection(tester, 'Rankings');

      expect(find.text('No rankings published'), findsOneWidget);
      expect(find.byType(GtexEmptyState), findsWidgets);
    });

    testWidgets('a failed lane offers a retry instead of an empty list', (
      WidgetTester tester,
    ) async {
      await pumpWorld(tester, repository: const _FailingBloodlineRepository());
      await openSection(tester, 'Bloodlines');

      expect(find.text('Could not load'), findsOneWidget);
      expect(find.textContaining('unreachable'), findsOneWidget);
      expect(find.text('Retry'), findsWidgets);
    });
  });

  group('selection drives the dossier', () {
    testWidgets('selecting a regen loads its lineage and potential', (
      WidgetTester tester,
    ) async {
      await pumpWorld(tester);

      // The first prospect is selected by default, so its dossier is present
      // without the user having to hunt for it.
      expect(find.text('Lineage'), findsOneWidget);
      expect(find.text('Son of p-001'), findsOneWidget);
      expect(find.text('Scout confidence: medium'), findsOneWidget);
    });

    testWidgets('a national-pool regen states that it has no dossier', (
      WidgetTester tester,
    ) async {
      await pumpWorld(tester);

      // r-002 is the demo national-pool seed: real seed rows have no
      // RegenProfile, so the panel must say that rather than show blanks.
      await tester.tap(find.text('MATEO SILVESTRI').first);
      await tester.pumpAndSettle();

      expect(find.text('No published dossier'), findsOneWidget);
      expect(find.text('Son of p-001'), findsNothing);
    });
  });

  group('player detail navigation', () {
    testWidgets('a tradable regen opens the canonical player detail', (
      WidgetTester tester,
    ) async {
      final List<String> opened = <String>[];
      await pumpWorld(
        tester,
        openPlayer: (String playerId) async => opened.add(playerId),
      );

      await tester.tap(find.text('Open player detail').first);
      await tester.pumpAndSettle();

      expect(opened, isNotEmpty);
      expect(opened.first, 'r-001');
    });

    testWidgets('a rental-only regen offers no player detail control', (
      WidgetTester tester,
    ) async {
      await pumpWorld(
        tester,
        openPlayer: (String playerId) async {},
      );

      await tester.tap(find.text('MATEO SILVESTRI').first);
      await tester.pumpAndSettle();

      expect(find.text('National rental only - not tradable'), findsOneWidget);
      expect(find.text('Open player detail'), findsNothing);
    });

    testWidgets('a bloodline member routes into player detail', (
      WidgetTester tester,
    ) async {
      final List<String> opened = <String>[];
      await pumpWorld(
        tester,
        openPlayer: (String playerId) async => opened.add(playerId),
      );
      await openSection(tester, 'Bloodlines');

      await tester.tap(find.text('Kelechi Aruna').first);
      await tester.pumpAndSettle();

      expect(opened, contains('r-001'));
    });
  });

  group('responsive widths', () {
    for (final double width in <double>[360, 420, 768, 1024, 1440, 1920]) {
      testWidgets('regen world holds together at ${width}px', (
        WidgetTester tester,
      ) async {
        await pumpWorld(tester, size: Size(width, 1200));

        expect(
          tester.takeException(),
          isNull,
          reason: 'regen world overflowed at ${width}px',
        );
      });
    }
  });

  group('dossier model', () {
    test('growth headroom is null when potential is unknown', () {
      final GtexRegenDossier base = demoRegenDossier('r-001');
      final GtexRegenDossier unrated = GtexRegenDossier(
        playerId: base.playerId,
        showcase: RegenPlayerShowcase(
          playerId: base.playerId,
          profile: RegenProfileDetail(
            id: base.profile.id,
            regenId: base.profile.regenId,
            displayName: base.profile.displayName,
            age: base.profile.age,
            primaryPosition: base.profile.primaryPosition,
            currentGsi: base.profile.currentGsi,
            scoutConfidence: 'low',
            generationSource: base.profile.generationSource,
            regenType: base.profile.regenType,
            status: base.profile.status,
            uniquenessScore: base.profile.uniquenessScore,
            growthCurve: base.profile.growthCurve,
          ),
          discoveryBadges: const <String>[],
          timeline: const <RegenStoryEvent>[],
          achievements: const <RegenPlayerAchievement>[],
        ),
      );

      // Unknown potential must not collapse into a zero headroom.
      expect(unrated.growthHeadroom, isNull);
      expect(unrated.potentialBandLabel, isNull);
      expect(unrated.lineageLabel, isNull);
    });

    test('a celebrity parent is stated but not navigable', () {
      const RegenLineageDescriptor celebrity = RegenLineageDescriptor(
        relationshipType: 'son',
        relatedLegendType: 'celebrity',
        relatedLegendRefId: 'celeb-9',
        lineageTier: 'rare',
      );

      expect(celebrity.parentPlayerId, isNull);
    });

    test('a player parent resolves to a navigable player id', () {
      const RegenLineageDescriptor player = RegenLineageDescriptor(
        relationshipType: 'son',
        relatedLegendType: 'player',
        relatedLegendRefId: 'p-001',
        lineageTier: 'elite',
      );

      expect(player.parentPlayerId, 'p-001');
    });
  });
}
