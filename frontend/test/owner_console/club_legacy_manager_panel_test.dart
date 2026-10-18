import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/owner_console/widgets/club_legacy_manager_panel.dart';

void main() {
  testWidgets('manager panel shows terms, relationship, and the negotiation actions', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(900, 1400);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    final List<String> actions = <String>[];
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ClubLegacyManagerPanel(
            data: const ClubLegacyManagerPanelData(
              name: 'Tunde Bakare',
              personality: 'demanding',
              ambition: 14,
              wageExpectation: '8000.00',
              relationshipScore: 35,
              retention: 'Stayed despite a richer rival',
              offers: <Map<String, dynamic>>[
                <String, dynamic>{'wage': '6000.00', 'contract_length': 2, 'role': 'head_coach', 'outcome': 'countered'},
                <String, dynamic>{'wage': '7500.00', 'contract_length': 4, 'role': 'director', 'outcome': 'counter'},
              ],
            ),
            onAction: actions.add,
          ),
        ),
      ),
    );

    expect(find.text('Personality demanding'), findsOneWidget);
    expect(find.text('Ambition 14'), findsOneWidget);
    expect(find.text('Wage expectation 8000.00'), findsOneWidget);
    expect(find.text('Relationship 35'), findsOneWidget);
    expect(find.text('6000.00 · 2 years · head_coach · countered'), findsOneWidget);
    expect(find.text('7500.00 · 4 years · director · counter'), findsOneWidget);
    expect(find.text('Stayed despite a richer rival'), findsOneWidget);

    for (final String key in <String>['manager-offer', 'manager-accept', 'manager-reject', 'manager-counter', 'manager-promise', 'manager-poach', 'manager-retain']) {
      await tester.ensureVisible(find.byKey(Key(key)));
      await tester.tap(find.byKey(Key(key)));
    }
    expect(actions, <String>['offer', 'accept', 'reject', 'counter', 'promise', 'poach', 'retain']);
  });
}
