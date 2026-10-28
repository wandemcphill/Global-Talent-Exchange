import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/owner_console/models/gtex_world_clock_models.dart';
import 'package:gte_frontend/features/owner_console/widgets/gtex_world_clock_panel.dart';

Map<String, Object?> _valid([Map<String, Object?> over = const <String, Object?>{}]) =>
    <String, Object?>{
      'clock_id': 'global',
      'world_time': '2031-03-14T09:05:00+00:00',
      'world_date': '2031-03-14',
      'is_paused': false,
      'progression_rate': 6,
      'virtual_months_per_season': 12,
      ...over,
    };

Widget _host(Widget child) => MaterialApp(
      home: Scaffold(body: SingleChildScrollView(child: child)),
    );

void main() {
  group('WorldClock contract (GET /api/world/clock)', () {
    test('uses the published path', () => expect(kWorldClockPath, '/api/world/clock'));

    test('parses the PR #347 shape and formats in UTC', () {
      final WorldClock c = WorldClock.fromJson(_valid());
      expect(c.clockId, 'global');
      expect(c.isPaused, isFalse);
      expect(c.displayDate, 'Fri, 14 March 2031');
      expect(c.displayTime, '09:05 UTC');
      expect(c.displayRate, '6x');
      expect(c.virtualMonthsPerSeason, 12);
      expect(
        WorldClock.fromJson(_valid(<String, Object?>{'world_time': '2031-03-14T23:30:00-02:00', 'world_date': '2031-03-15'})).displayTime,
        '01:30 UTC',
      );
    });

    test('rejects anything outside the published schema', () {
      final List<Map<String, Object?>> bad = <Map<String, Object?>>[
        _valid(<String, Object?>{'clock_id': ''}),
        _valid(<String, Object?>{'world_time': '2031-03-14T09:05:00'}),
        _valid(<String, Object?>{'world_date': '14/03/2031'}),
        _valid(<String, Object?>{'world_date': '2031-03-15'}),
        _valid(<String, Object?>{'is_paused': 'false'}),
        _valid(<String, Object?>{'progression_rate': 0}),
        _valid(<String, Object?>{'virtual_months_per_season': 1.5}),
      ];
      for (final Map<String, Object?> raw in bad) {
        expect(() => WorldClock.fromJson(raw), throwsA(isA<WorldClockContractException>()), reason: '$raw');
      }
      expect(() => WorldClock.fromJson(null), throwsA(isA<WorldClockContractException>()));
    });
  });

  group('Owner briefing boundary', () {
    test('no endpoint is published', () => expect(kOwnerBriefingEndpoint, isNull));

    test('keeps only verified events and routes targets', () {
      final OwnerBriefing b = OwnerBriefing.fromJson(<String, Object?>{
        'briefing_id': 'b1',
        'club_id': 'c1',
        'world_date': '2031-03-14',
        'events': <Object?>[
          <String, Object?>{'event_id': 'e1', 'headline': 'Won 2-1', 'occurred_at': '2031-03-13T20:00:00Z', 'target': <String, Object?>{'type': 'match_result', 'match_id': 'm9'}},
          <String, Object?>{'headline': 'No id', 'occurred_at': 'x'},
          <String, Object?>{'event_id': 'e3', 'headline': 'Odd', 'occurred_at': 'x', 'target': <String, Object?>{'type': 'wallet'}},
        ],
      });
      expect(b.events.map((BriefingEvent e) => e.eventId), <String>['e1', 'e3']);
      expect(b.rejectedEventCount, 1);
      expect(b.events[0].target!.route, '/matches/viewer/m9');
      expect(b.events[1].target, isNull);
      expect(const BriefingTarget(BriefingTargetType.clubHistory, 'c1').route, '/clubs/c1/profile');
      expect(const BriefingTarget(BriefingTargetType.decision, 'i1').route, '/app/inbox');
    });

    test('rejects a briefing without persisted identity', () {
      expect(() => OwnerBriefing.fromJson(<String, Object?>{'club_id': 'c', 'world_date': 'd'}), throwsFormatException);
    });
  });

  group('GtexWorldClockPanel', () {
    testWidgets('shows loading, then server date/time/status', (WidgetTester tester) async {
      final Completer<WorldClock> gate = Completer<WorldClock>();
      await tester.pumpWidget(_host(GtexWorldClockPanel(load: () => gate.future)));
      expect(find.byKey(const Key('world-clock-loading')), findsOneWidget);
      gate.complete(WorldClock.fromJson(_valid()));
      await tester.pumpAndSettle();
      expect(find.text('Fri, 14 March 2031'), findsOneWidget);
      expect(find.text('09:05 UTC'), findsOneWidget);
      expect(find.text('Running'), findsOneWidget);
      expect(find.textContaining('12 virtual months'), findsOneWidget);
      expect(find.byKey(const Key('world-clock-season-unavailable')), findsOneWidget);
    });

    testWidgets('shows paused and never invents a season label', (WidgetTester tester) async {
      await tester.pumpWidget(_host(GtexWorldClockPanel(
        load: () async => WorldClock.fromJson(_valid(<String, Object?>{'is_paused': true})),
      )));
      await tester.pumpAndSettle();
      expect(find.text('Paused'), findsOneWidget);
      expect(find.textContaining(RegExp(r'Season\s+20\d\d')), findsNothing);
    });

    testWidgets('error shows no time and retry recovers', (WidgetTester tester) async {
      int calls = 0;
      await tester.pumpWidget(_host(GtexWorldClockPanel(load: () async {
        calls++;
        if (calls == 1) throw Exception('down');
        return WorldClock.fromJson(_valid());
      })));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('world-clock-error')), findsOneWidget);
      expect(find.textContaining('UTC'), findsNothing);
      await tester.tap(find.byKey(const Key('world-clock-retry')));
      await tester.pumpAndSettle();
      expect(find.text('09:05 UTC'), findsOneWidget);
    });

    testWidgets('failed refresh keeps last snapshot and flags it stale', (WidgetTester tester) async {
      int calls = 0;
      await tester.pumpWidget(_host(GtexWorldClockPanel(load: () async {
        calls++;
        if (calls > 1) throw Exception('down');
        return WorldClock.fromJson(_valid());
      })));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('world-clock-refresh')));
      await tester.pumpAndSettle();
      expect(find.text('09:05 UTC'), findsOneWidget);
      expect(find.byKey(const Key('world-clock-stale')), findsOneWidget);
    });

    testWidgets('no loader means honest error, not a fake time', (WidgetTester tester) async {
      await tester.pumpWidget(_host(const GtexWorldClockPanel(load: null)));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('world-clock-error')), findsOneWidget);
    });
  });

  group('GtexOwnerBriefingPanel', () {
    Widget panel(BriefingViewState s, [ValueChanged<String>? nav]) =>
        _host(GtexOwnerBriefingPanel(state: s, onNavigate: nav ?? (String _) {}, onRetry: () {}));

    testWidgets('unavailable invents no stories', (WidgetTester tester) async {
      await tester.pumpWidget(panel(const BriefingUnavailable()));
      expect(find.byKey(const Key('owner-briefing-unavailable')), findsOneWidget);
      expect(find.textContaining('owner-briefing-card'), findsNothing);
    });

    testWidgets('loading, error and empty states', (WidgetTester tester) async {
      await tester.pumpWidget(panel(const BriefingLoading()));
      expect(find.byKey(const Key('owner-briefing-loading')), findsOneWidget);
      await tester.pumpWidget(panel(const BriefingError()));
      expect(find.byKey(const Key('owner-briefing-retry')), findsOneWidget);
      await tester.pumpWidget(panel(const BriefingEmpty(worldDate: '2031-03-14')));
      expect(find.text('Nothing to report'), findsOneWidget);
    });

    testWidgets('ready cards navigate to decision, history and match', (WidgetTester tester) async {
      final List<String> routes = <String>[];
      final OwnerBriefing b = OwnerBriefing(
        briefingId: 'b1',
        clubId: 'c1',
        worldDate: '2031-03-14',
        rejectedEventCount: 1,
        explanation: 'Prose only.',
        events: const <BriefingEvent>[
          BriefingEvent(eventId: 'e1', headline: 'Offer', occurredAt: 't', target: BriefingTarget(BriefingTargetType.decision, 'i1')),
          BriefingEvent(eventId: 'e2', headline: 'Milestone', occurredAt: 't', target: BriefingTarget(BriefingTargetType.clubHistory, 'c1')),
          BriefingEvent(eventId: 'e3', headline: 'Won', occurredAt: 't', target: BriefingTarget(BriefingTargetType.matchResult, 'm9')),
          BriefingEvent(eventId: 'e4', headline: 'No link', occurredAt: 't'),
        ],
      );
      await tester.pumpWidget(panel(BriefingReady(b, stale: true), routes.add));
      for (final String id in <String>['e1', 'e2', 'e3']) {
        await tester.tap(find.byKey(Key('owner-briefing-link-$id')));
      }
      expect(routes, <String>['/app/inbox', '/clubs/c1/profile', '/matches/viewer/m9']);
      expect(find.byKey(const Key('owner-briefing-link-e4')), findsNothing);
      expect(find.byKey(const Key('owner-briefing-stale')), findsOneWidget);
      expect(find.byKey(const Key('owner-briefing-rejected')), findsOneWidget);
      expect(find.textContaining('explanatory only'), findsOneWidget);
    });
  });
}
