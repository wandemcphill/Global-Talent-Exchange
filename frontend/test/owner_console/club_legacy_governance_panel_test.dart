import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/owner_console/widgets/club_legacy_governance_panel.dart';

void main() {
  testWidgets('governance panel keeps cases, votes, reviews, and net worth apart', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(900, 1800);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    final List<String> actions = <String>[];
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ClubLegacyGovernancePanel(
            data: const ClubLegacyGovernancePanelData(
              cases: <Map<String, dynamic>>[
                <String, dynamic>{
                  'rule_code': 'related_party_transfer',
                  'allegation': 'Sold to a sister club',
                  'evidence': 'Listing 44',
                  'status': 'appealed',
                  'sanction': 'warning',
                  'reason': 'First related-party sale',
                  'appeal_outcome': 'Warning stands',
                },
              ],
              stakes: <Map<String, dynamic>>[
                <String, dynamic>{'holder': 'Ada', 'percentage': '75.00', 'voting_rights': '10.00'},
              ],
              reviews: <Map<String, dynamic>>[
                <String, dynamic>{'kind': 'related_party', 'status': 'reviewable'},
                <String, dynamic>{'kind': 'sister_club', 'status': 'reviewable'},
              ],
              personalAssets: '20000.00',
              clubAssets: '50000.00',
              minorityStakes: '16000.00',
              distribution: 'Paid 100.00 once',
            ),
            onAction: actions.add,
          ),
        ),
      ),
    );

    expect(find.text('related_party_transfer'), findsOneWidget);
    expect(find.text('Sold to a sister club'), findsOneWidget);
    expect(find.text('Listing 44'), findsOneWidget);
    expect(find.text('appealed'), findsOneWidget);
    expect(find.text('warning · First related-party sale'), findsOneWidget);
    expect(find.text('Warning stands'), findsOneWidget);
    expect(find.text('Ada · economic 75.00% · votes 10.00%'), findsOneWidget);
    expect(find.text('Paid 100.00 once'), findsOneWidget);
    expect(find.text('related_party · reviewable'), findsOneWidget);
    expect(find.text('sister_club · reviewable'), findsOneWidget);
    expect(find.text('Personal assets 20000.00'), findsOneWidget);
    expect(find.text('Club assets 50000.00'), findsOneWidget);
    expect(find.text('Minority stakes 16000.00'), findsOneWidget);

    await tester.ensureVisible(find.byKey(const Key('governance-case')));
    await tester.tap(find.byKey(const Key('governance-case')));
    await tester.ensureVisible(find.byKey(const Key('governance-stake')));
    await tester.tap(find.byKey(const Key('governance-stake')));
    await tester.ensureVisible(find.byKey(const Key('governance-distribute')));
    await tester.tap(find.byKey(const Key('governance-distribute')));
    expect(actions, <String>['case', 'stake', 'distribute']);
  });
}
