import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/owner_console/widgets/club_legacy_market_panel.dart';

void main() {
  testWidgets('market panel shows one purchase, a pending gift, and provenance', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(900, 1600);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    final List<String> actions = <String>[];
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ClubLegacyMarketPanel(
            data: const ClubLegacyMarketData(
              feeRate: '0.0500',
              jetCap: 5,
              coachCap: 10,
              listings: <Map<String, dynamic>>[
                <String, dynamic>{'id': 'list-1', 'name': 'Harbour Jet', 'status': 'open', 'price': '1000.00'},
              ],
              gifts: <Map<String, dynamic>>[
                <String, dynamic>{'id': 'gift-1', 'recipient_ref': 'player-1', 'status': 'offered'},
              ],
              provenance: <Map<String, dynamic>>[
                <String, dynamic>{
                  'id': 'prov-1',
                  'from_owner_class': 'club',
                  'to_owner_class': 'player',
                  'price': '0.00',
                  'actor_user_id': 'owner-1',
                },
              ],
            ),
            onAction: actions.add,
          ),
        ),
      ),
    );
    expect(find.text('Transfer fee 0.0500'), findsOneWidget);
    expect(find.text('Jet cap 5'), findsOneWidget);
    expect(find.text('Coach cap 10'), findsOneWidget);
    expect(find.text('Harbour Jet · open · 1000.00'), findsOneWidget);
    expect(find.text('player-1 · offered'), findsOneWidget);
    expect(find.text('club → player · 0.00 · owner-1'), findsOneWidget);
    await tester.tap(find.byKey(const Key('club-market-buy')));
    await tester.tap(find.byKey(const Key('club-market-transfer')));
    await tester.ensureVisible(find.byKey(const Key('club-market-gift')));
    await tester.tap(find.byKey(const Key('club-market-gift')));
    expect(actions, <String>['buy', 'transfer', 'gift']);
  });
}
