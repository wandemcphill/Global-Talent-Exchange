import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/owner_console/data/owner_console_api.dart';
import 'package:gte_frontend/features/owner_console/widgets/club_legacy_desk.dart';
import 'package:gte_frontend/features/owner_console/presentation/owner_console_screen.dart';
import 'package:gte_frontend/features/owner_console/widgets/owner_console_sections.dart';
import 'package:gte_frontend/features/regen_redesign/data/gtex_share_market_api.dart';

Map<String, dynamic> _centerJson({bool withClubs = true, String? respondBy}) => <String, dynamic>{
  'user': <String, dynamic>{'username': 'flow', 'display_name': 'Flow Owner', 'role': 'user'},
  'clubs': withClubs
      ? <Map<String, dynamic>>[
          <String, dynamic>{'club_id': 'c1', 'club_name': 'Lagos Lions', 'value': '1200', 'value_trend': '15', 'manager': <String, dynamic>{'name': 'Coach A', 'mood': 72}, 'competition': <String, dynamic>{'name': 'GTEX Cup'}},
          <String, dynamic>{'club_id': 'c2', 'club_name': 'Abuja Stars', 'value': '800', 'value_trend': '-4', 'manager': <String, dynamic>{'name': 'Coach B', 'mood': 40}},
        ]
      : <Map<String, dynamic>>[],
  'max_clubs': 3,
  'decisions': withClubs
      ? <Map<String, dynamic>>[
          <String, dynamic>{'id': 'd1', 'club_id': 'c1', 'kind': 'transfer_offer', 'title': 'Offer for your striker', 'is_decision': true, 'priority': 'high'},
          <String, dynamic>{'id': 'd2', 'club_id': 'c2', 'kind': 'contract', 'title': 'Contract expiring', 'is_decision': true},
          <String, dynamic>{
            'id': 'd3', 'club_id': 'c1', 'kind': 'transfer_bid', 'title': 'Kano bid 12,400 for Ade Bello', 'is_decision': true,
            if (respondBy != null) 'respond_by': respondBy,
            'what': 'Kano offer 12,400 GTEX Coin for Ade Bello (valued 10,000).',
            'actions': <Map<String, dynamic>>[
              <String, dynamic>{'key': 'accept', 'label': 'Accept bid', 'style': 'primary'},
              <String, dynamic>{'key': 'reject', 'label': 'Reject', 'style': 'ghost'},
            ],
          },
        ]
      : <Map<String, dynamic>>[],
  'inbox': <Map<String, dynamic>>[],
  'inbox_open_count': 0,
  'health': <Map<String, dynamic>>[
    <String, dynamic>{'club_id': 'c1', 'club_name': 'Lagos Lions', 'cash': '50', 'squad_size': 18, 'squad_depth': 'thin', 'morale': 70, 'injuries': 1, 'fan_engagement': 55},
  ],
  'board': <Map<String, dynamic>>[
    <String, dynamic>{
      'competition': <String, dynamic>{'name': 'GTEX Cup'},
      'standings': <Map<String, dynamic>>[
        <String, dynamic>{'club_id': 'x', 'club_name': 'AI FC', 'played': 2, 'won': 2, 'drawn': 0, 'lost': 0, 'points': 6},
        <String, dynamic>{'club_id': 'c1', 'club_name': 'Lagos Lions', 'played': 2, 'won': 1, 'drawn': 0, 'lost': 1, 'points': 3},
      ],
    },
  ],
  'fixtures': <String, dynamic>{
    'upcoming': <Map<String, dynamic>>[
      <String, dynamic>{'id': 'm1', 'round': 3, 'home_club_id': 'c1', 'away_club_id': 'x', 'home_name': 'Lagos Lions', 'away_name': 'AI FC', 'status': 'scheduled'},
    ],
    'recent': <Map<String, dynamic>>[],
  },
  'economy': <String, dynamic>{'wallet': <String, dynamic>{'withdrawable': '20'}, 'club_cash_total': '50', 'pending_payouts': '0', 'earnings_sources': <String, dynamic>{'gate': '30', 'wages': '-12'}},
  'integrity': <String, dynamic>{'score': 98},
  'legacy': withClubs
      ? <Map<String, dynamic>>[
          <String, dynamic>{
            'club_id': 'c1',
            'prestige': 12,
            'development': 20,
            'financial_strength': 80,
            'continent_name': 'Africa',
          },
        ]
      : null,
};

class _FakeOwner implements OwnerConsoleReader {
  _FakeOwner({this.withClubs = true, this.failDecide = false, this.emptyQueue = false, this.respondBy});

  bool withClubs;
  final bool failDecide;
  final bool emptyQueue;
  final String? respondBy;
  int seeds = 0;
  int suggestions = 0;
  int centerLoads = 0;
  final List<String> calls = <String>[];

  @override
  Future<OwnerControlCenter> fetchControlCenter() async {
    centerLoads++;
    return OwnerControlCenter.fromJson(_centerJson(withClubs: withClubs, respondBy: respondBy));
  }

  @override
  Future<void> claimClub({String? city, String? country}) async {
    calls.add('claim');
    calls.add('claim-city:${city ?? ''}');
    calls.add('claim-country:${country ?? ''}');
    withClubs = true;
  }

  @override
  Future<OwnerInboxEntry> decide(String itemId, String action) async {
    calls.add('decide:$itemId:$action');
    if (failDecide) throw Exception('insufficient_club_cash');
    return OwnerInboxEntry.fromJson(<String, dynamic>{'id': itemId, 'kind': 'transfer_bid', 'title': 't', 'status': 'resolved', 'outcome': 'Ade Bello sold for 12,400.'});
  }

  @override
  Future<OwnerReviewQueue> fetchReviewQueue() async => OwnerReviewQueue.fromJson(emptyQueue
      ? <String, dynamic>{}
      : <String, dynamic>{
          'withdrawals': <Map<String, dynamic>>[
            <String, dynamic>{'id': 'w1', 'user_id': 'u1', 'amount_coin': '20', 'amount_ngn': '17600', 'bank_name': 'GTBank', 'account_last4': '6789', 'account_name': 'Ada Obi', 'status': 'pending_review', 'checks': <String, dynamic>{'risk': 'low'}},
          ],
          'flags': <Map<String, dynamic>>[
            <String, dynamic>{'id': 'f1', 'flag_type': 'related_party_transfer', 'severity': 'high', 'detail': 'Fee outside fair band', 'score_impact': -10},
          ],
          'held_payouts': <Map<String, dynamic>>[
            <String, dynamic>{'id': 'p1', 'event_type': 'prize_payout', 'net_amount': '40', 'currency': 'gtex_coin', 'memo': 'Cup prize'},
          ],
        });

  @override
  Future<void> reviewWithdrawal(String withdrawalId, String decision, {String? note}) async =>
      calls.add('withdrawal:$withdrawalId:$decision:${note ?? ''}');

  @override
  Future<void> decideFlag(String flagId, String decision) async => calls.add('flag:$flagId:$decision');

  @override
  Future<void> releasePayout(String eventId) async => calls.add('release:$eventId');

  @override
  Future<List<OwnerNationalCompetition>> fetchNationalCompetitions() async =>
      <OwnerNationalCompetition>[OwnerNationalCompetition.fromJson(<String, dynamic>{'id': 'nc1', 'title': 'Nations Cup', 'status': 'open'})];

  @override
  Future<List<OwnerNationalEntry>> fetchManagedEntries() async =>
      <OwnerNationalEntry>[OwnerNationalEntry.fromJson(<String, dynamic>{'id': 'e1', 'competition_id': 'nc1', 'country_code': 'NG', 'country_name': 'Nigeria'})];

  @override
  Future<OwnerNationalSquad> fetchSquad(String entryId) async => OwnerNationalSquad.fromJson(<String, dynamic>{
    'country_name': 'Nigeria',
    'minimum_squad_size': 18,
    'rental_squad_members': <Map<String, dynamic>>[
      <String, dynamic>{'player_id': 'p1', 'player_name': 'Victor Boniface', 'overall_rating': 82, 'source_type': 'rental'},
    ],
  });

  @override
  Future<OwnerAutoBuildPlan> suggestSquad({required String competitionId, required String countryCode, required double budgetCoin}) async {
    suggestions++;
    return OwnerAutoBuildPlan.fromJson(<String, dynamic>{
      'formation': '4-3-3', 'selected_count': 11, 'squad_size': 18, 'total_cost_coin': '420', 'remaining_budget_coin': '80',
      'players': <Map<String, dynamic>>[<String, dynamic>{'player_id': 'p9', 'player_name': 'Tunde Olawale', 'overall_rating': 80, 'assigned_slot': 'ST'}],
    });
  }

  @override
  Future<void> seedDefaultTournaments() async => seeds++;

  @override
  Future<double> fetchWalletBalance() async => 75;

  @override
  Future<List<ShowroomExhibit>> fetchShowroom() async => const <ShowroomExhibit>[
    ShowroomExhibit(id: 'jet-1', name: 'Harbour Jet', category: 'jet', ownershipLabel: 'Club', fallbackLabel: 'Static jet card', owned: true),
  ];

  final List<String> purchases = <String>[];
  final List<String> gifts = <String>[];

  @override
  Future<void> purchaseCatalogueSku(
    String sku, {
    String ownerClass = 'club',
    String? idempotencyKey,
  }) async {
    purchases.add('$sku:$ownerClass:${idempotencyKey ?? ''}');
  }

  @override
  Future<void> offerShowroomGift({
    required String assetId,
    required String recipientRef,
  }) async {
    gifts.add('$assetId->$recipientRef');
  }

  @override
  Future<ClubLegacyDeskData> fetchDesk() async => const ClubLegacyDeskData(staff: [], policies: [], clubValuation: '0', equity: '0', preseason: [], sponsors: [], offers: [], cases: []);

  @override
  Future<void> performDesk(String action, [Map<String, Object?> payload = const <String, Object?>{}]) async {}
}

class _FakeShare implements GtexShareMarketReader {
  @override
  Future<List<GtexShareNation>> fetchRegenNations() async => const <GtexShareNation>[];

  @override
  Future<List<GtexWonderkid>> fetchWonderkids({String? nation, int limit = 20}) async =>
      const <GtexWonderkid>[GtexWonderkid(playerId: 'w1', name: 'Kid One', sharePriceCoin: 0.02, rating: 80, potential: 99)];

  @override
  Future<GtexSharePriceHistory> fetchPriceHistory(String playerId, {String range = '30d'}) => throw UnimplementedError();
}

Future<List<String>> _pump(WidgetTester tester, OwnerConsoleReader reader, {String role = 'user', Size size = const Size(1400, 1000), double? wallet = 50}) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  final List<String> visited = <String>[];
  await tester.pumpWidget(MaterialApp(
    theme: ThemeData(splashFactory: InkRipple.splashFactory),
    home: Scaffold(
      body: OwnerConsoleScreen(
        reader: reader,
        shareMarket: _FakeShare(),
        role: role,
        signedInAs: 'Flow Owner',
        walletBalance: wallet,
        onNavigate: visited.add,
      ),
    ),
  ));
  await tester.pumpAndSettle();
  return visited;
}

void main() {
  testWidgets('control center shows prestige, development, and financial strength separately', (WidgetTester tester) async {
    await _pump(tester, _FakeOwner());
    expect(find.byKey(const Key('owner-legacy-ratings')), findsOneWidget);
    expect(find.byKey(const Key('owner-legacy-prestige')), findsOneWidget);
    expect(find.byKey(const Key('owner-legacy-development')), findsOneWidget);
    expect(find.byKey(const Key('owner-legacy-financial')), findsOneWidget);
    expect(find.text('12'), findsWidgets);
    expect(find.text('20'), findsWidgets);
    expect(find.text('80'), findsWidgets);
  });

  testWidgets('control center renders decisions, board, health and chips', (WidgetTester tester) async {
    final List<String> visited = await _pump(tester, _FakeOwner());
    expect(find.text('50 GTX'), findsOneWidget);
    expect(find.text('USER'), findsOneWidget);
    expect(find.textContaining('Signed in as Flow Owner'), findsOneWidget);
    expect(find.text("Today's Decisions"), findsOneWidget);
    expect(find.text('Offer for your striker'), findsOneWidget);
    expect(find.text('#2 Lagos Lions'), findsOneWidget);
    expect(find.byKey(const Key('owner-board-next-fixture')), findsOneWidget);
    expect(find.text('Inbox clear'), findsOneWidget);

    await tester.tap(find.byKey(const Key('owner-decision-d1')));
    expect(visited.single, contains('market'));
    expect(find.byKey(const Key('owner-squad-seed-defaults')), findsNothing);
  });

  testWidgets('focusing a club filters Control Center to that club', (WidgetTester tester) async {
    await _pump(tester, _FakeOwner());
    await tester.tap(find.byKey(const Key('owner-console-section-clubs')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('owner-club-c2')), findsOneWidget);
    await tester.tap(find.byKey(const Key('owner-club-focus-c2')));
    await tester.pumpAndSettle();
    expect(find.text('Contract expiring'), findsOneWidget);
    expect(find.text('Offer for your striker'), findsNothing);
  });

  testWidgets('owner without clubs is guided to claim one', (WidgetTester tester) async {
    await _pump(tester, _FakeOwner(withClubs: false));
    expect(find.byKey(const Key('owner-console-claim-club')), findsOneWidget);
    expect(find.text('All clear - nothing needs you today'), findsOneWidget);
  });

  testWidgets('claim starts the club on this console', (WidgetTester tester) async {
    final _FakeOwner owner = _FakeOwner(withClubs: false);
    await _pump(tester, owner);
    await tester.tap(find.byKey(const Key('owner-console-claim-club-button')));
    await tester.pumpAndSettle();
    expect(owner.calls, contains('claim'));
    expect(owner.calls, contains('claim-city:Lagos'));
    expect(owner.calls, contains('claim-country:NG'));
    expect(find.text('#2 Lagos Lions'), findsOneWidget);
    expect(find.byKey(const Key('owner-console-claim-club')), findsNothing);
  });

  testWidgets('squad section: suggestion needs review, seed is admin-only', (WidgetTester tester) async {
    final _FakeOwner owner = _FakeOwner();
    final List<String> visited = await _pump(tester, owner, role: 'admin');
    await tester.tap(find.byKey(const Key('owner-console-section-squad')));
    await tester.pumpAndSettle();
    expect(find.text('Victor Boniface'), findsOneWidget);
    await tester.tap(find.byKey(const Key('owner-squad-seed-defaults')));
    await tester.pumpAndSettle();
    expect(owner.seeds, 1);
    await tester.tap(find.byKey(const Key('owner-squad-suggest')));
    await tester.pumpAndSettle();
    expect(owner.suggestions, 1);
    expect(find.byKey(const Key('owner-squad-plan-summary')), findsOneWidget);
    await tester.tap(find.byKey(const Key('owner-squad-review-confirm')));
    expect(visited.last, '/national-team');
  });

  testWidgets('academy section shows wonderkids and phone layout stacks', (WidgetTester tester) async {
    await _pump(tester, _FakeOwner(), size: const Size(400, 900));
    await tester.ensureVisible(find.byKey(const Key('owner-console-section-academy')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('owner-console-section-academy')));
    await tester.pumpAndSettle();
    expect(find.text('Kid One'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('wallet chip falls back to the wallet summary', (WidgetTester tester) async {
    await _pump(tester, _FakeOwner(), wallet: null);
    expect(find.text('75 GTX'), findsOneWidget);
  });

  test('decision routing by kind', () {
    expect(decisionRoute('rental_request'), '/national-team');
    expect(decisionRoute('lineup_deadline'), contains('play'));
  });

  test('money-moving decisions need confirmation', () {
    expect(decisionMovesMoney('transfer_bid', 'accept'), isTrue);
    expect(decisionMovesMoney('regen_breakthrough', 'new_contract'), isTrue);
    expect(decisionMovesMoney('transfer_bid', 'reject'), isFalse);
    expect(decisionMovesMoney('manager_meeting', 'back_manager'), isFalse);
  });

  testWidgets('inline decision: reject resolves without confirm and shows the outcome', (WidgetTester tester) async {
    final _FakeOwner owner = _FakeOwner();
    await _pump(tester, owner);
    expect(find.byKey(const Key('owner-decision-d3-action-accept')), findsOneWidget);
    expect(find.byKey(const Key('owner-decision-d1-action-accept')), findsNothing);
    await tester.tap(find.byKey(const Key('owner-decision-d3-action-reject')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('owner-confirm-dialog')), findsNothing);
    expect(owner.calls, <String>['decide:d3:reject']);
    expect(find.byKey(const Key('owner-decision-outcome')), findsOneWidget);
    expect(owner.centerLoads, 2);
  });

  testWidgets('inline decision: accepting a bid asks for confirmation first', (WidgetTester tester) async {
    final _FakeOwner owner = _FakeOwner();
    await _pump(tester, owner);
    await tester.tap(find.byKey(const Key('owner-decision-d3-action-accept')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('owner-confirm-dialog')), findsOneWidget);
    expect(find.textContaining('12,400 GTEX Coin for Ade Bello'), findsOneWidget);
    await tester.tap(find.byKey(const Key('owner-confirm-cancel')));
    await tester.pumpAndSettle();
    expect(owner.calls, isEmpty);
    await tester.tap(find.byKey(const Key('owner-decision-d3-action-accept')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('owner-confirm-ok')));
    await tester.pumpAndSettle();
    expect(owner.calls, <String>['decide:d3:accept']);
    expect(find.text('Ade Bello sold for 12,400.'), findsOneWidget);
  });

  testWidgets('inline decision: failure keeps the row and shows the error', (WidgetTester tester) async {
    await _pump(tester, _FakeOwner(failDecide: true));
    await tester.tap(find.byKey(const Key('owner-decision-d3-action-reject')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('owner-decision-d3-error')), findsOneWidget);
    expect(find.byKey(const Key('owner-decision-d3-action-reject')), findsOneWidget);
  });

  testWidgets('admin review is hidden for owners', (WidgetTester tester) async {
    await _pump(tester, _FakeOwner());
    expect(find.byKey(const Key('owner-console-section-admin')), findsNothing);
  });

  testWidgets('admin review desk: approve, clear and release', (WidgetTester tester) async {
    final _FakeOwner owner = _FakeOwner();
    await _pump(tester, owner, role: 'super_admin');
    await tester.tap(find.byKey(const Key('owner-console-section-admin')));
    await tester.pumpAndSettle();
    expect(find.text('20 GTX · ₦17600'), findsOneWidget);
    await tester.tap(find.byKey(const Key('owner-admin-withdrawal-w1-approve')));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('owner-confirm-note')), 'paid');
    await tester.tap(find.byKey(const Key('owner-confirm-ok')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('owner-admin-withdrawals-clear')), findsOneWidget);
    await tester.tap(find.byKey(const Key('owner-admin-flag-f1-clear')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('owner-admin-flags-clear')), findsOneWidget);
    await tester.tap(find.byKey(const Key('owner-admin-payout-p1-release')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('owner-confirm-ok')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('owner-admin-held-clear')), findsOneWidget);
    expect(owner.calls, <String>['withdrawal:w1:approve:paid', 'flag:f1:clear', 'release:p1']);
  });

  testWidgets('admin review desk: quiet states', (WidgetTester tester) async {
    await _pump(tester, _FakeOwner(emptyQueue: true), role: 'admin');
    await tester.tap(find.byKey(const Key('owner-console-section-admin')));
    await tester.pumpAndSettle();
    expect(find.text('Queue clear'), findsOneWidget);
    expect(find.text('No open flags'), findsOneWidget);
    expect(find.text('Nothing held'), findsOneWidget);
  });

  testWidgets('a decision shows its respond-by deadline', (WidgetTester tester) async {
    final String respondBy = DateTime.now().toUtc().add(const Duration(hours: 30)).toIso8601String();
    await _pump(tester, _FakeOwner(respondBy: respondBy));
    expect(find.byKey(const Key('owner-decision-d3-countdown')), findsOneWidget);
    expect(find.textContaining('Respond by'), findsOneWidget);
    expect(find.textContaining('1d'), findsOneWidget);
  });
}
