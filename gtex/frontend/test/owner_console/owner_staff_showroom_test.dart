import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/owner_console/data/owner_ops_api.dart';
import 'package:gte_frontend/features/owner_console/ops/owner_showroom.dart';
import 'package:gte_frontend/features/owner_console/ops/owner_staff_section.dart';

final Map<String, dynamic> _showroom = <String, dynamic>{
  'club_name': 'Lagos Lions', 'city': 'Lagos', 'country_code': 'NG', 'primary_color': '#0F766E', 'fans': 1200, 'prestige': 40,
  'trophies': <Map<String, dynamic>>[<String, dynamic>{'competition': 'Naija Cup', 'position': 1, 'year': 2026}],
  'facilities': <String, dynamic>{'training': 2}, 'sponsors': <Map<String, dynamic>>[<String, dynamic>{'sponsor': 'Glo', 'slot': 'shirt'}],
  'top_players': <Map<String, dynamic>>[<String, dynamic>{'name': 'Ade Bello', 'position': 'forward', 'rating': 70, 'age': 24}],
};

class _Fake implements OwnerOpsClient {
  final List<String> calls = <String>[];

  @override
  Future<Map<String, dynamic>> get(String path, {Map<String, Object?> query = const <String, Object?>{}}) async {
    calls.add('GET $path');
    if (path.endsWith('/showroom')) return _showroom;
    return <String, dynamic>{
      'staff': <Map<String, dynamic>>[<String, dynamic>{'id': 's1', 'role': 'gm', 'name': 'Chidi Okafor', 'quality': 14, 'attributes': <String, dynamic>{'negotiation': 15}, 'personality': <String, dynamic>{'risk_appetite': 'bold'}, 'salary_per_cycle': '2000'}],
      'candidates': <String, dynamic>{'hoyd': <Map<String, dynamic>>[<String, dynamic>{'candidate_id': 'hoyd-2-0', 'role': 'hoyd', 'name': 'Amara Mensah', 'quality': 12, 'attributes': <String, dynamic>{'coaching': 12}, 'personality': <String, dynamic>{'risk_appetite': 'cautious'}, 'salary_per_cycle': '1600'}]},
      'policies': <Map<String, dynamic>>[<String, dynamic>{'task': 'transfer_bid', 'label': 'Bids', 'role': 'gm', 'mode': 'auto', 'budget_cap': '10000', 'version': 1}],
      'reserved': <Map<String, dynamic>>[<String, dynamic>{'task': 'capital_move', 'label': 'Money moved between clubs'}],
      'actions': <Map<String, dynamic>>[<String, dynamic>{'task': 'transfer_bid', 'recommendation': 'reject', 'status': 'executed', 'reason': 'Under bar.', 'confidence': 82, 'policy_version': 1, 'mode': 'auto'}],
    };
  }

  @override
  Future<Map<String, dynamic>> post(String path, {Object? body}) async {
    calls.add('POST $path $body');
    return <String, dynamic>{'code': 'abc123', 'executed': 1, 'recommended': 0};
  }

  @override
  Future<Map<String, dynamic>> put(String path, {Object? body}) async {
    calls.add('PUT $path $body');
    return <String, dynamic>{'version': 2};
  }
}

Future<void> _pump(WidgetTester tester, Widget child) async {
  tester.view.physicalSize = const Size(1400, 2600);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(MaterialApp(home: Scaffold(body: ListView(children: <Widget>[child]))));
  await tester.pumpAndSettle();
}

void main() {
  test('share url uses hash route', () {
    expect(showroomShareUrl('abc', Uri.parse('https://gtex.app/')), 'https://gtex.app/#/showroom/abc');
  });

  testWidgets('staff panel: hire with confirm, save policy, reserved chips, action log', (WidgetTester tester) async {
    final _Fake fake = _Fake();
    await _pump(tester, StaffDelegationPanel(client: fake, clubId: 'c1', onChanged: () {}));
    expect(find.byKey(const Key('owner-staff-s1')), findsOneWidget);
    expect(find.text('Money moved between clubs'), findsOneWidget);
    expect(find.textContaining('policy v1'), findsOneWidget);
    await tester.tap(find.byKey(const Key('owner-hire-staff-hoyd-2-0')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('owner-confirm-ok')));
    await tester.pumpAndSettle();
    expect(fake.calls, contains('POST /owner/clubs/c1/staff/hire {candidate_id: hoyd-2-0}'));
    await tester.tap(find.byKey(const Key('owner-policy-transfer_bid-approval')));
    await tester.pump();
    await tester.tap(find.byKey(const Key('owner-policy-transfer_bid-save')));
    await tester.pumpAndSettle();
    expect(fake.calls, contains('PUT /owner/clubs/c1/delegation/transfer_bid {mode: approval, budget_cap: 10000.0}'));
  });

  testWidgets('showroom cabinet renders club data and turns on drag', (WidgetTester tester) async {
    await _pump(tester, const ShowroomCabinet(data: <String, dynamic>{}));
    await _pump(tester, ShowroomCabinet(data: _showroom));
    expect(find.text('Lagos Lions'), findsOneWidget);
    expect(find.text('Naija Cup'), findsOneWidget);
    expect(find.text('Glo'), findsOneWidget);
    await tester.drag(find.byKey(const Key('owner-showroom-cabinet')), const Offset(120, 0));
    await tester.pumpAndSettle();
    expect(find.text('Ade Bello'), findsOneWidget);
  });

  testWidgets('public showroom shows only trophies, name and crest', (WidgetTester tester) async {
    final Map<String, dynamic> public = <String, dynamic>{'club_name': 'Lagos Lions', 'city': 'Lagos', 'primary_color': '#0F766E', 'crest_url': null, 'trophies': _showroom['trophies']};
    await tester.pumpWidget(MaterialApp(home: PublicShowroomScreen(load: () async => public)));
    await tester.pumpAndSettle();
    expect(find.text('GTEX CLUB SHOWROOM'), findsOneWidget);
    expect(find.text('Lagos Lions'), findsOneWidget);
    expect(find.text('Naija Cup'), findsOneWidget);
    expect(find.byKey(const Key('owner-showroom-crest')), findsOneWidget);
    expect(find.text('Glo'), findsNothing);
    expect(find.text('Ade Bello'), findsNothing);
    expect(find.text('FACILITIES'), findsNothing);
  });
}
