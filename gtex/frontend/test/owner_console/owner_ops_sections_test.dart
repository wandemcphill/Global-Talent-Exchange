import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/owner_console/data/owner_console_api.dart';
import 'package:gte_frontend/features/owner_console/data/owner_ops_api.dart';
import 'package:gte_frontend/features/owner_console/ops/owner_club_ops.dart';
import 'package:gte_frontend/features/owner_console/ops/owner_competitions_section.dart';
import 'package:gte_frontend/features/owner_console/ops/owner_finance_section.dart';
import 'package:gte_frontend/features/owner_console/ops/owner_inbox_section.dart';
import 'package:gte_frontend/features/owner_console/ops/owner_setup_section.dart';

final Map<String, dynamic> _club = <String, dynamic>{
  'club_id': 'c1', 'club_name': 'Lagos Lions', 'stage': 'active', 'value': '90000', 'mentality': 'balanced',
  'health': <String, dynamic>{'fans': 1200, 'prestige': 40, 'squad_size': 2},
  'economy': <String, dynamic>{'cash_gtex': '50000', 'pending_payouts': '0'},
  'facilities': <String, dynamic>{'training': <String, dynamic>{'level': 1, 'next_cost': 5000}, 'academy': <String, dynamic>{'level': 2, 'next_cost': 8000}},
  'manager_profile': <String, dynamic>{'name': 'Coach Ade', 'is_default': false, 'mood': 70, 'youth_development': 12},
  'manager': <String, dynamic>{'name': 'Coach Ade'},
  'sponsors': <dynamic>[], 'disclosures': <dynamic>[],
  'squad': <Map<String, dynamic>>[
    <String, dynamic>{'id': 's1', 'name': 'Ade Bello', 'position': 'forward', 'age': 24, 'rating': 70, 'potential': 75, 'morale': 66, 'minutes': 90, 'value_coin': '12000', 'player_ref': 'p1'},
    <String, dynamic>{'id': 'r1', 'name': 'Tunde Kid', 'position': 'midfielder', 'age': 17, 'rating': 55, 'potential': 78, 'morale': 70, 'minutes': 0, 'value_coin': '3000', 'is_regen': true, 'personality': <String, dynamic>{'ambition': 14}},
  ],
};

class _FakeOps implements OwnerOpsClient {
  _FakeOps({this.stage = 'active'});

  final String stage;
  final List<String> calls = <String>[];

  @override
  Future<Map<String, dynamic>> get(String path, {Map<String, Object?> query = const <String, Object?>{}}) async {
    calls.add('GET $path');
    switch (path) {
      case '/owner/finance':
        return <String, dynamic>{
          'wallet': <String, dynamic>{'gtex_total': '1500', 'fan_total': '1000', 'withdrawable': '200'},
          'clubs': <Map<String, dynamic>>[<String, dynamic>{'club_id': 'c1', 'club_name': 'Lagos Lions', 'cash_gtex': '50000', 'earnings_sources': <String, dynamic>{'gate': 10}}],
          'paystack_configured': false, 'treasury_rates': <String, dynamic>{'deposit_rate': '880', 'deposit_direction': 'fiat_per_coin', 'withdrawal_rate': '880'},
          'withdrawals': <dynamic>[], 'ledger': <Map<String, dynamic>>[<String, dynamic>{'id': 'l1', 'event_type': 'launch_grant', 'net_amount': '100000', 'status': 'completed', 'currency': 'GTEX_COIN'}],
          'fan_coin_per_gtex': 10, 'support_unit_price': 50, 'support_units': <dynamic>[],
        };
      case '/owner/withdrawals/eligibility':
        return <String, dynamic>{'eligible': false, 'checks': <String, dynamic>{'kyc': false}, 'integrity_score': 100, 'kyc_status': 'none', 'kyc_threshold': 500, 'supported_countries': <String>['NG']};
      case '/owner/world/clubs':
        return <String, dynamic>{'clubs': <dynamic>[]};
      case '/owner/onboarding':
        return <String, dynamic>{'clubs': <Map<String, dynamic>>[<String, dynamic>{'club_id': 'c1', 'club_name': 'Lagos Lions', 'stage': stage}], 'max_clubs': 3, 'min_squad': 11, 'launch_grant': '100000'};
      case '/owner/competitions':
        return <String, dynamic>{'competitions': <Map<String, dynamic>>[<String, dynamic>{'id': 'k1', 'name': 'Naija Cup', 'host_type': 'gtex', 'format': 'knockout', 'status': 'open', 'entry_fee': '500', 'prize_pool': '5000', 'entrants': 2, 'max_clubs': 8, 'my_club_ids': <dynamic>[]}]};
      case '/owner/inbox':
        return <String, dynamic>{'items': <Map<String, dynamic>>[<String, dynamic>{'id': 'i1', 'kind': 'decision_expired', 'title': 'Expired: bid', 'what': 'Bid rejected.', 'status': 'open', 'is_decision': false}]};
      case '/owner/deposits/verify/ref1':
        return <String, dynamic>{'status': 'success'};
    }
    if (path.startsWith('/owner/clubs/')) return _club;
    return <String, dynamic>{};
  }

  @override
  Future<Map<String, dynamic>> post(String path, {Object? body}) async {
    calls.add('POST $path $body');
    return <String, dynamic>{'level': 2, 'regens': <dynamic>[]};
  }

  @override
  Future<Map<String, dynamic>> put(String path, {Object? body}) async {
    calls.add('PUT $path $body');
    return <String, dynamic>{};
  }
}

class _NoReader implements OwnerConsoleReader {
  @override
  dynamic noSuchMethod(Invocation invocation) => throw UnimplementedError();
}

Future<void> _pump(WidgetTester tester, Widget child) async {
  tester.view.physicalSize = const Size(1400, 2400);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(MaterialApp(home: Scaffold(body: child)));
  await tester.pumpAndSettle();
}

void main() {
  test('helpers format money and new club body', () {
    expect(opsFmt('1234567.5', digits: 2), '1,234,567.50');
    expect(opsGtx(1500), '1,500 GTX');
    expect(setupStepIndex('manager'), 2);
    final Map<String, Object?> b = newClubBody('Abuja Eagles FC', 1700000000000);
    expect(b['slug'], startsWith('abuja-eagles-fc-'));
    expect(b['short_name'], 'Abuja Eagles');
    expect(ownerPaymentCallbackUrl(Uri.parse('https://gtex.app/')), 'https://gtex.app/#/payment/callback');
  });

  testWidgets('finance shows balances, deposit off without Paystack, ledger and withdraw gate', (WidgetTester tester) async {
    await _pump(tester, FinanceSection(client: _FakeOps(), onNavigate: (_) {}));
    expect(find.text('1,500 GTX'), findsOneWidget);
    expect(find.byKey(const Key('owner-deposit-not-configured')), findsOneWidget);
    expect(find.byKey(const Key('owner-finance-treasury-c1')), findsOneWidget);
    expect(find.textContaining('launch grant'), findsOneWidget);
    expect(find.byKey(const Key('owner-withdraw-eligibility')), findsOneWidget);
    final GtexActionButtonFinder submit = GtexActionButtonFinder(tester, 'owner-withdraw-submit');
    expect(submit.enabled, isFalse);
  });

  testWidgets('club setup walks the identity step', (WidgetTester tester) async {
    final _FakeOps ops = _FakeOps(stage: 'not_started');
    await _pump(tester, ClubSetupSection(client: ops, onChanged: () {}));
    expect(find.byKey(const Key('owner-setup-stepper')), findsOneWidget);
    await tester.tap(find.byKey(const Key('owner-setup-activate')));
    await tester.pumpAndSettle();
    expect(ops.calls, contains('POST /owner/clubs/c1/activate null'));
  });

  testWidgets('club setup offers a new club when all are active', (WidgetTester tester) async {
    await _pump(tester, ClubSetupSection(client: _FakeOps(), onChanged: () {}));
    expect(find.byKey(const Key('owner-setup-all-active')), findsOneWidget);
    expect(find.byKey(const Key('owner-setup-new-club')), findsOneWidget);
  });

  testWidgets('competitions: entering asks for confirmation', (WidgetTester tester) async {
    final _FakeOps ops = _FakeOps();
    await _pump(tester, CompetitionsSection(client: ops, clubId: 'c1', onChanged: () {}));
    await tester.tap(find.byKey(const Key('owner-competition-enter-k1')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('owner-confirm-dialog')), findsOneWidget);
    await tester.tap(find.byKey(const Key('owner-confirm-ok')));
    await tester.pumpAndSettle();
    expect(ops.calls.where((String c) => c.startsWith('POST /owner/competitions/k1/enter')), hasLength(1));
  });

  testWidgets('club actions: facility upgrade and mentality', (WidgetTester tester) async {
    final _FakeOps ops = _FakeOps();
    await _pump(tester, ListView(children: <Widget>[ClubOpsPanel(client: ops, clubId: 'c1', clubs: const <(String, String)>[('c1', 'Lagos Lions')], onChanged: () {})]));
    await tester.tap(find.byKey(const Key('owner-upgrade-training')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('owner-confirm-ok')));
    await tester.pumpAndSettle();
    expect(ops.calls, contains('POST /owner/clubs/c1/facilities/training/upgrade null'));
  });

  testWidgets('squad and academy panels render', (WidgetTester tester) async {
    final _FakeOps ops = _FakeOps();
    await _pump(tester, ListView(children: <Widget>[
      SquadOpsPanel(client: ops, clubId: 'c1', clubs: const <(String, String)>[('c1', 'Lagos Lions')], onChanged: () {}),
      AcademyOpsPanel(client: ops, clubId: 'c1', onChanged: () {}),
    ]));
    expect(find.byKey(const Key('owner-manager-sheet')), findsOneWidget);
    expect(find.byKey(const Key('owner-squad-player-s1')), findsOneWidget);
    expect(find.byKey(const Key('owner-regen-r1')), findsOneWidget);
    await tester.tap(find.byKey(const Key('owner-default-mentality-attacking')));
    await tester.pumpAndSettle();
    expect(ops.calls, contains('PUT /owner/clubs/c1/mentality {mentality: attacking}'));
  });

  testWidgets('inbox lists items and filters', (WidgetTester tester) async {
    final _FakeOps ops = _FakeOps();
    await _pump(tester, OwnerInboxSection(client: ops, reader: _NoReader(), onNavigate: (_) {}, onChanged: () {}));
    expect(find.byKey(const Key('owner-inbox-item-i1')), findsOneWidget);
    await tester.tap(find.byKey(const Key('owner-inbox-filter-resolved')));
    await tester.pumpAndSettle();
    expect(ops.calls.where((String c) => c == 'GET /owner/inbox'), hasLength(2));
  });

  testWidgets('payment callback verifies the reference', (WidgetTester tester) async {
    bool done = false;
    await tester.pumpWidget(MaterialApp(home: OwnerPaymentCallbackScreen(client: _FakeOps(), reference: 'ref1', onDone: () => done = true)));
    await tester.pumpAndSettle();
    expect(find.textContaining('Payment verified'), findsOneWidget);
    await tester.tap(find.byKey(const Key('owner-payment-callback-done')));
    expect(done, isTrue);
  });

  testWidgets('payment callback without reference', (WidgetTester tester) async {
    await tester.pumpWidget(MaterialApp(home: OwnerPaymentCallbackScreen(client: _FakeOps(), reference: null, onDone: () {})));
    await tester.pumpAndSettle();
    expect(find.text('Missing payment reference.'), findsOneWidget);
  });
}

class GtexActionButtonFinder {
  GtexActionButtonFinder(this.tester, this.key);

  final WidgetTester tester;
  final String key;

  bool get enabled {
    final Finder f = find.descendant(of: find.byKey(Key(key)), matching: find.byWidgetPredicate((Widget w) => w is ButtonStyleButton));
    return tester.widget<ButtonStyleButton>(f.first).onPressed != null;
  }
}
