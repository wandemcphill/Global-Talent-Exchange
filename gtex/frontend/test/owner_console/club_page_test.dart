import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/owner_console/data/owner_ops_api.dart';
import 'package:gte_frontend/features/owner_console/ops/club_page.dart';
import 'package:gte_frontend/features/owner_console/ops/owner_showroom.dart';
import 'package:gte_frontend/features/owner_console/ops/showroom_card.dart';

final Map<String, dynamic> _page = <String, dynamic>{
  'club_id': 'c1',
  'overview': <String, dynamic>{'club_name': 'Lagos Lions', 'city': 'Lagos', 'country_code': 'NG', 'continent': <String, dynamic>{'code': 'africa', 'label': 'Africa'}, 'primary_color': '#0F766E', 'prestige': 40, 'fans': 1200, 'status': 'active'},
  'honours': <String, dynamic>{
    'trophies': <Map<String, dynamic>>[<String, dynamic>{'competition': 'Naija Cup', 'position': 1, 'year': 2026}],
    'record': <Map<String, dynamic>>[<String, dynamic>{'competition': 'Naija Cup', 'tier': 'Open', 'position': 1, 'played': 7, 'won': 5}],
    'milestones': <Map<String, dynamic>>[<String, dynamic>{'label': 'Joined the GTEX world', 'year': 2026}],
  },
  'staff': <String, dynamic>{'owner': 'vidvi', 'executives': <Map<String, dynamic>>[<String, dynamic>{'role_label': 'General Manager', 'name': 'Chidi Okafor', 'quality': 14, 'style': 'bold'}], 'manager': <String, dynamic>{'name': 'Coach Ade'}},
  'facilities': <String, dynamic>{'stadium': 2, 'academy': 1},
  'commercial': <String, dynamic>{'sponsors': <Map<String, dynamic>>[<String, dynamic>{'sponsor': 'Glo', 'slot': 'shirt'}], 'supporter_holders': 3, 'fans': 1200},
};

class _Fake implements OwnerOpsClient {
  final List<String> calls = <String>[];

  @override
  Future<Map<String, dynamic>> get(String path, {Map<String, Object?> query = const <String, Object?>{}}) async {
    calls.add('GET $path');
    if (path == '/owner/net-worth') {
      return <String, dynamic>{'net_worth': '15000', 'personal_cash': '5000', 'equity': '10000', 'liabilities': '0', 'fan_coin': '20', 'clubs': <Map<String, dynamic>>[<String, dynamic>{'club_id': 'c1', 'club_name': 'Lagos Lions', 'stake_pct': '100.00', 'stake_value': '10000', 'valuation': <String, dynamic>{'total': '10000'}}], 'method': 'Net worth = wallet + stake.'};
    }
    if (path.endsWith('/money-history')) {
      return <String, dynamic>{'lifetime_income': '3000', 'lifetime_spend': '1000', 'income_by_type': <String, dynamic>{'gate_receipts': '3000'}, 'spend_by_type': <String, dynamic>{'staff_salary': '1000'}, 'events': <Map<String, dynamic>>[<String, dynamic>{'direction': 'in', 'amount': '3000', 'event_type': 'gate_receipts', 'balance_after': '2000'}]};
    }
    return _page;
  }

  @override
  Future<Map<String, dynamic>> post(String path, {Object? body}) async => <String, dynamic>{'code': 'abc'};

  @override
  Future<Map<String, dynamic>> put(String path, {Object? body}) async => <String, dynamic>{};
}

Future<void> _pump(WidgetTester tester, Widget child) async {
  tester.view.physicalSize = const Size(1400, 1000);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(MaterialApp(home: Scaffold(body: child)));
  await tester.pumpAndSettle();
}

void main() {
  test('club page url uses hash route and location includes continent', () {
    expect(clubPageUrl('c1', Uri.parse('https://gtex.app/')), 'https://gtex.app/#/club-page/c1');
    expect(clubLocation(opsMap(_page['overview'])), 'Lagos · NG · Africa');
    expect(showroomCardFileName('Lagos Lions FC!'), 'lagos-lions-fc-showroom.png');
  });

  testWidgets('public club page shows the five public tabs', (WidgetTester tester) async {
    await _pump(tester, PublicClubPageScreen(load: () async => _page));
    expect(find.text('Lagos Lions'), findsOneWidget);
    expect(find.text('Lagos · NG · Africa'), findsOneWidget);
    for (final String t in <String>['Overview', 'Honours & history', 'Staff', 'Facilities', 'Commercial']) {
      expect(find.text(t), findsOneWidget);
    }
    expect(find.text('Net worth'), findsNothing);
    await tester.tap(find.text('Honours & history'));
    await tester.pumpAndSettle();
    expect(find.text('Naija Cup'), findsOneWidget);
    await tester.tap(find.text('Staff'));
    await tester.pumpAndSettle();
    expect(find.textContaining('Chidi Okafor'), findsOneWidget);
    await tester.tap(find.text('Commercial'));
    await tester.pumpAndSettle();
    expect(find.text('Glo'), findsOneWidget);
  });

  testWidgets('owner club page adds net worth and money history tabs', (WidgetTester tester) async {
    final _Fake fake = _Fake();
    await _pump(tester, OwnerClubPageSection(client: fake, clubId: 'c1'));
    await tester.tap(find.text('Net worth'));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('owner-net-worth-total')), findsOneWidget);
    expect(find.text('15,000 GTX'), findsOneWidget);
    await tester.tap(find.text('Money history'));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('owner-money-income')), findsOneWidget);
    expect(fake.calls, containsAll(<String>['GET /owner/public/clubs/c1', 'GET /owner/net-worth', 'GET /owner/clubs/c1/money-history']));
  });

  testWidgets('showroom card shows only crest, name, place, trophies and link', (WidgetTester tester) async {
    final Map<String, dynamic> showroom = <String, dynamic>{'club_name': 'Lagos Lions', 'city': 'Lagos', 'country_code': 'NG', 'trophies': opsMap(_page['honours'])['trophies'], 'top_players': <Map<String, dynamic>>[<String, dynamic>{'name': 'Ade Bello'}]};
    await _pump(tester, const Center(child: SizedBox()));
    await _pump(tester, Center(child: ShowroomShareCard(data: showroom, link: 'https://gtex.app/#/showroom/abc')));
    expect(find.text('Lagos Lions'), findsOneWidget);
    expect(find.text('Lagos · NG'), findsOneWidget);
    expect(find.text('Naija Cup'), findsOneWidget);
    expect(find.text('https://gtex.app/#/showroom/abc'), findsOneWidget);
    expect(find.text('Ade Bello'), findsNothing);
    expect(tester.getSize(find.byKey(const Key('showroom-share-card'))), const Size(540, 540));
  });

  testWidgets('public showroom opens the share card dialog', (WidgetTester tester) async {
    await _pump(tester, PublicShowroomScreen(code: 'abc', linkBase: Uri.parse('https://gtex.app/'), load: () async => <String, dynamic>{'club_name': 'Lagos Lions', 'trophies': <dynamic>[]}));
    await tester.tap(find.byKey(const Key('public-showroom-card')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('showroom-card-dialog')), findsOneWidget);
    expect(find.text('BUILDING A LEGACY'), findsOneWidget);
    expect(find.byKey(const Key('showroom-card-share')), findsOneWidget);
  });
}
