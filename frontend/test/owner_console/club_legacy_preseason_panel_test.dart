import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/owner_console/widgets/club_legacy_preseason_panel.dart';

void main() {
  testWidgets('preseason panel keeps the previous offer and separates reputation from money', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(900, 1800);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    final List<String> actions = <String>[];
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ClubLegacyPreseasonPanel(
            data: const ClubLegacyPreseasonData(
              windowName: 'June window',
              invites: <Map<String, dynamic>>[
                <String, dynamic>{'id': 'inv-1', 'match_on': '2026-06-18', 'status': 'countered', 'appearance_fee': '650.00'},
              ],
              history: <Map<String, dynamic>>[
                <String, dynamic>{'sequence': 1, 'status': 'pending'},
                <String, dynamic>{'sequence': 2, 'status': 'countered'},
              ],
              offers: <Map<String, dynamic>>[
                <String, dynamic>{'sequence': 1, 'status': 'superseded', 'appearance_fee': '400.00', 'match_on': '2026-06-12'},
                <String, dynamic>{'sequence': 2, 'status': 'open', 'appearance_fee': '650.00', 'match_on': '2026-06-18'},
              ],
              platformShare: '200.00',
              hostShare: '500.00',
              participantShare: '300.00',
              reputation: 10,
              audience: 200,
              money: '1000.00',
              gmPolicy: 'automatic',
              tournament: 'Harbour Cup · host + 2',
            ),
            onAction: actions.add,
          ),
        ),
      ),
    );
    expect(find.text('June window'), findsOneWidget);
    expect(find.text('2026-06-18 · countered · 650.00'), findsOneWidget);
    expect(find.text('superseded · 400.00 · 2026-06-12'), findsOneWidget);
    expect(find.text('open · 650.00 · 2026-06-18'), findsOneWidget);
    expect(find.text('1 · pending'), findsOneWidget);
    expect(find.text('2 · countered'), findsOneWidget);
    expect(find.text('Platform 200.00'), findsOneWidget);
    expect(find.text('Host 500.00'), findsOneWidget);
    expect(find.text('Participants 300.00'), findsOneWidget);
    expect(find.text('Reputation 10'), findsOneWidget);
    expect(find.text('Audience 200'), findsOneWidget);
    expect(find.text('Money 1000.00'), findsOneWidget);
    expect(find.text('GM policy automatic'), findsOneWidget);
    await tester.ensureVisible(find.byKey(const Key('club-preseason-counter')));
    await tester.tap(find.byKey(const Key('club-preseason-counter')));
    await tester.tap(find.byKey(const Key('club-preseason-accept')));
    await tester.tap(find.byKey(const Key('club-preseason-reject')));
    await tester.ensureVisible(find.byKey(const Key('club-preseason-settle')));
    await tester.tap(find.byKey(const Key('club-preseason-settle')));
    expect(actions, <String>['counter', 'accept', 'reject', 'settle']);
  });
}
