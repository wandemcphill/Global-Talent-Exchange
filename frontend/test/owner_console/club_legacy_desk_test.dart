import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/owner_console/widgets/club_legacy_desk.dart';

void main() {
  testWidgets('club desk shows equity apart from club value and runs each action', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(900, 1600);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    final List<String> actions = <String>[];
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ClubLegacyDesk(
            data: const ClubLegacyDeskData(
              staff: <Map<String, dynamic>>[<String, dynamic>{'role': 'gm', 'name': 'Ada Okonkwo'}],
              policies: <Map<String, dynamic>>[<String, dynamic>{'task_key': 'operating_spend', 'mode': 'approval_required'}],
              clubValuation: '100000.00',
              equity: '60000.00',
              preseason: <Map<String, dynamic>>[<String, dynamic>{'match_on': '2026-06-12', 'status': 'accepted'}],
              sponsors: <Map<String, dynamic>>[<String, dynamic>{'sponsor_name': 'Harbour Trust', 'placement': 'front', 'status': 'approved'}],
              offers: <Map<String, dynamic>>[<String, dynamic>{'candidate_name': 'Tunde Bakare', 'outcome': 'declined'}],
              cases: <Map<String, dynamic>>[<String, dynamic>{'rule_code': 'late_wages', 'status': 'appealed'}],
            ),
            onAction: actions.add,
          ),
        ),
      ),
    );
    expect(find.text('Club value 100000.00'), findsOneWidget);
    expect(find.text('Your equity 60000.00'), findsOneWidget);
    expect(find.text('gm: Ada Okonkwo'), findsOneWidget);
    expect(find.text('2026-06-12 · accepted'), findsOneWidget);
    expect(find.text('Harbour Trust · front · approved'), findsOneWidget);
    expect(find.text('Tunde Bakare · declined'), findsOneWidget);
    expect(find.text('late_wages · appealed'), findsOneWidget);

    await tester.tap(find.byKey(const Key('club-desk-hire')));
    await tester.tap(find.byKey(const Key('club-desk-preset')));
    await tester.tap(find.byKey(const Key('club-desk-sponsor')));
    await tester.tap(find.byKey(const Key('club-desk-manager')));
    await tester.ensureVisible(find.byKey(const Key('club-desk-case')));
    await tester.tap(find.byKey(const Key('club-desk-case')));
    expect(actions, <String>['hire', 'preset', 'sponsor', 'manager', 'case']);
  });
}
