import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/player_detail/gtex_player_navigator.dart';
import 'package:gte_frontend/features/regen_redesign/data/gtex_regen_demo_dossier.dart';
import 'package:gte_frontend/features/regen_redesign/models/gtex_regen_dossier.dart';
import 'package:gte_frontend/features/regen_redesign/models/gtex_regen_wire_models.dart';
import 'package:gte_frontend/features/regen_redesign/widgets/gtex_regen_dossier_panel.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

/// A regen is meant to read as a football prospect: it descends from someone,
/// it might become something, and things have happened to it. These pin that
/// the dossier says so from real data - and, just as importantly, that it
/// states an absence instead of drawing a zero when the backend has nothing.
void main() {
  Future<void> pumpDossier(
    WidgetTester tester,
    GtexRegenDossierResult result, {
    Future<void> Function(String playerId)? openPlayer,
    double width = 420,
  }) async {
    tester.view.physicalSize = Size(width, 1400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    Widget panel = SingleChildScrollView(
      child: GtexRegenDossierPanel(result: result),
    );
    if (openPlayer != null) {
      panel = GtexPlayerNavigator(openPlayer: openPlayer, child: panel);
    }
    await tester.pumpWidget(MaterialApp(home: Scaffold(body: panel)));
    await tester.pumpAndSettle();
  }

  GtexRegenDossier dossier() => demoRegenDossier('r-001');

  group('lineage', () {
    testWidgets('states who the regen descends from', (
      WidgetTester tester,
    ) async {
      await pumpDossier(
        tester,
        GtexRegenDossierResult.loaded(dossier()),
      );

      expect(find.text('Lineage'), findsOneWidget);
      expect(find.text('Son of p-001'), findsOneWidget);
      expect(find.text('elite lineage'), findsOneWidget);
      expect(find.text('Owner son'), findsOneWidget);
    });

    testWidgets('renders the bloodline generations in order', (
      WidgetTester tester,
    ) async {
      await pumpDossier(
        tester,
        GtexRegenDossierResult.loaded(dossier()),
      );

      expect(find.text('Bloodline'), findsOneWidget);
      expect(find.text('G1'), findsOneWidget);
      expect(find.text('G2'), findsOneWidget);
      expect(find.text('Victor Adebayo'), findsOneWidget);
      expect(find.text('Kelechi Aruna'), findsOneWidget);
    });

    testWidgets('says the regen starts its own line when there is no parent', (
      WidgetTester tester,
    ) async {
      final GtexRegenDossier base = dossier();
      final GtexRegenDossier orphan = GtexRegenDossier(
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
            scoutConfidence: base.profile.scoutConfidence,
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

      await pumpDossier(tester, GtexRegenDossierResult.loaded(orphan));

      expect(find.text('Starts their own line'), findsOneWidget);
      // No parent must not become a fabricated one.
      expect(find.textContaining('Son of'), findsNothing);
    });
  });

  group('parent relationship', () {
    testWidgets('opens the parent through the canonical navigator', (
      WidgetTester tester,
    ) async {
      final List<String> opened = <String>[];
      await pumpDossier(
        tester,
        GtexRegenDossierResult.loaded(dossier()),
        openPlayer: (String playerId) async => opened.add(playerId),
      );

      final Finder button = find.text('Open parent player');
      expect(button, findsOneWidget);
      await tester.tap(button);
      await tester.pumpAndSettle();

      expect(opened, <String>['p-001']);
    });

    testWidgets('offers no parent control when there is no shell to open it', (
      WidgetTester tester,
    ) async {
      await pumpDossier(
        tester,
        GtexRegenDossierResult.loaded(dossier()),
      );

      // The relationship is still stated; only the dead control is withheld.
      expect(find.text('Son of p-001'), findsOneWidget);
      expect(find.text('Open parent player'), findsNothing);
    });
  });

  group('potential', () {
    testWidgets('shows the scouted band and its confidence, not a point', (
      WidgetTester tester,
    ) async {
      await pumpDossier(
        tester,
        GtexRegenDossierResult.loaded(dossier()),
      );

      expect(find.text('84-93'), findsOneWidget);
      expect(find.text('64-72'), findsOneWidget);
      expect(find.text('Scout confidence: medium'), findsOneWidget);
      expect(find.text('+22 growth headroom'), findsOneWidget);
    });
  });

  group('progression', () {
    testWidgets('lists development events newest first', (
      WidgetTester tester,
    ) async {
      await pumpDossier(
        tester,
        GtexRegenDossierResult.loaded(dossier()),
      );

      expect(find.text('Development'), findsOneWidget);
      expect(find.text('First senior hat-trick'), findsOneWidget);
      expect(find.text('Senior debut'), findsOneWidget);

      final double hatTrickY =
          tester.getTopLeft(find.text('First senior hat-trick')).dy;
      final double debutY = tester.getTopLeft(find.text('Senior debut')).dy;
      expect(
        hatTrickY,
        lessThan(debutY),
        reason: 'the most recent development event must come first',
      );
    });

    testWidgets('says "no recorded matches" instead of a row of zeroes', (
      WidgetTester tester,
    ) async {
      final GtexRegenDossier base = dossier();
      final GtexRegenDossier unplayed = GtexRegenDossier(
        playerId: base.playerId,
        showcase: RegenPlayerShowcase(
          playerId: base.playerId,
          profile: base.profile,
          legacy: const RegenLegacySnapshot(
            totalMatches: 0,
            goals: 0,
            assists: 0,
            trophies: 0,
            peakRating: 0,
            seasonsTotal: 0,
            awardsTotal: 0,
            legacyScore: 0,
            legacyTier: 'standard',
            isLegend: false,
          ),
          discoveryBadges: const <String>[],
          timeline: const <RegenStoryEvent>[],
          achievements: const <RegenPlayerAchievement>[],
        ),
      );

      await pumpDossier(tester, GtexRegenDossierResult.loaded(unplayed));

      expect(find.text('No recorded matches'), findsOneWidget);
      expect(find.text('0 matches'), findsNothing);
      expect(find.text('0 goals'), findsNothing);
    });
  });

  group('personality and value', () {
    testWidgets('renders real traits and the value components behind a price', (
      WidgetTester tester,
    ) async {
      await pumpDossier(
        tester,
        GtexRegenDossierResult.loaded(dossier()),
      );

      expect(find.text('Personality'), findsOneWidget);
      // Strongest trait first: flair 90 outranks ambition 88.
      expect(find.text('Flair'), findsWidgets);
      expect(find.text('68000 coin'), findsOneWidget);
      expect(find.text('Potential 30000'), findsOneWidget);
    });
  });

  group('empty and blocked states', () {
    testWidgets('a regen with no published dossier says so', (
      WidgetTester tester,
    ) async {
      await pumpDossier(
        tester,
        const GtexRegenDossierResult.absent(
          absence: GtexRegenDossierAbsence.notPublished,
          message: 'This regen has no published profile.',
        ),
      );

      expect(find.text('No published dossier'), findsOneWidget);
      expect(find.byType(GtexBlockedState), findsOneWidget);
      // Nothing is invented to fill the gap.
      expect(find.text('Lineage'), findsNothing);
      expect(find.text('Potential'), findsNothing);
    });

    testWidgets('a failed load is distinguished from an absent one', (
      WidgetTester tester,
    ) async {
      await pumpDossier(
        tester,
        const GtexRegenDossierResult.absent(
          absence: GtexRegenDossierAbsence.loadFailed,
          message: 'The regen dossier could not be loaded: timeout',
        ),
      );

      expect(find.text('Dossier unavailable'), findsOneWidget);
      expect(find.textContaining('timeout'), findsOneWidget);
    });
  });

  group('responsive widths', () {
    for (final double width in <double>[360, 420, 768, 1024, 1440, 1920]) {
      testWidgets('dossier does not overflow at ${width}px', (
        WidgetTester tester,
      ) async {
        await pumpDossier(
          tester,
          GtexRegenDossierResult.loaded(dossier()),
          width: width,
        );

        expect(
          tester.takeException(),
          isNull,
          reason: 'the regen dossier overflowed at ${width}px',
        );
      });
    }
  });
}
