import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/owner_console/widgets/club_legacy_season_panel.dart';

void main() {
  testWidgets('season panel shows three tiers, metrics, and subsystem flags', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(900, 1800);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    final List<String> actions = <String>[];
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ClubLegacySeasonPanel(
            data: const ClubLegacySeasonPanelData(
              seasons: <Map<String, dynamic>>[
                <String, dynamic>{'tier': 'small', 'reputation': '36', 'revenue': '420000.00', 'youth': 'one high potential', 'sanctions': '0'},
                <String, dynamic>{'tier': 'established', 'reputation': '62', 'revenue': '3000000.00', 'youth': 'steady intake', 'sanctions': '1'},
                <String, dynamic>{'tier': 'elite', 'reputation': '88', 'revenue': '18000000.00', 'youth': 'deep intake', 'sanctions': '1'},
              ],
              invitationCount: 4,
              acceptance: 3,
              settlementTotal: '1000.00',
              supplyRemaining: '14',
              openCases: 1,
              showroomFailures: 2,
              flags: <String, bool>{
                'club_legacy': true,
                'club_legacy_market': false,
                'club_legacy_preseason': true,
                'club_legacy_sponsors': true,
                'club_legacy_governance': true,
              },
            ),
            onAction: actions.add,
          ),
        ),
      ),
    );

    expect(find.text('Reputation 36'), findsOneWidget);
    expect(find.text('Revenue 420000.00'), findsOneWidget);
    expect(find.text('Youth one high potential'), findsOneWidget);
    expect(find.text('Revenue 18000000.00'), findsOneWidget);
    expect(find.text('Sanctions 0'), findsOneWidget);
    expect(find.text('Invitations 4'), findsOneWidget);
    expect(find.text('Acceptance 3'), findsOneWidget);
    expect(find.text('Settlements 1000.00'), findsOneWidget);
    expect(find.text('Supply 14'), findsOneWidget);
    expect(find.text('Open cases 1'), findsOneWidget);
    expect(find.text('Showroom failures 2'), findsOneWidget);
    expect(find.text('club_legacy on'), findsOneWidget);
    expect(find.text('club_legacy_market off'), findsOneWidget);

    await tester.ensureVisible(find.byKey(const Key('season-simulate')));
    await tester.tap(find.byKey(const Key('season-simulate')));
    expect(actions, <String>['simulate']);
  });
}
