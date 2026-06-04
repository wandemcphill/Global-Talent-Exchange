import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/build_a_son/build_a_son.dart';
import 'package:gte_frontend/models/regen_creation_models.dart';
import 'package:gte_frontend/shared/realtime/realtime.dart';

void main() {
  test('regen order realtime parser accepts wallet topic event families', () {
    final BuildASonOrderRealtimeEvent? snakeCase =
        BuildASonOrderRealtimeEvent.fromRealtimeEvent(
          const GtexRealtimeEvent(
            type: 'regen_creation_order_update',
            topic: 'wallet',
            payload: <String, Object?>{'order_id': 'order-1'},
          ),
        );
    final BuildASonOrderRealtimeEvent? dotted =
        BuildASonOrderRealtimeEvent.fromRealtimeEvent(
          const GtexRealtimeEvent(
            type: 'regen.creation_order.generated',
            topic: 'wallet',
            payload: <String, Object?>{
              'creationOrder': <String, Object?>{'id': 'order-2'},
            },
          ),
        );
    final BuildASonOrderRealtimeEvent? walletOnly =
        BuildASonOrderRealtimeEvent.fromRealtimeEvent(
          const GtexRealtimeEvent(
            type: 'wallet_update',
            topic: 'wallet',
            payload: <String, Object?>{'order_id': 'order-3'},
          ),
        );

    expect(snakeCase?.orderId, 'order-1');
    expect(snakeCase?.appliesToOrder('order-1'), isTrue);
    expect(snakeCase?.appliesToOrder('order-2'), isFalse);
    expect(dotted?.orderId, 'order-2');
    expect(walletOnly, isNull);
  });

  testWidgets(
    'matching realtime order event refreshes the active backend order',
    (WidgetTester tester) async {
      await _setLargeSurface(tester);
      final _RealtimeBuildASonClient client = _RealtimeBuildASonClient();
      final StreamController<BuildASonOrderRealtimeEvent> realtimeEvents =
          StreamController<BuildASonOrderRealtimeEvent>.broadcast();
      int completedCount = 0;
      addTearDown(realtimeEvents.close);

      await tester.pumpWidget(
        MaterialApp(
          home: BuildASonWizard(
            client: client,
            orderRealtimeEvents: realtimeEvents.stream,
            onCompleted: (RegenCreationOrder order) async {
              completedCount += 1;
            },
          ),
        ),
      );
      await tester.pumpAndSettle();
      await _completeCurrentWizardDraftAndPreview(tester);

      final Finder createButton = find.widgetWithText(
        FilledButton,
        'Create GEN-2 Regen - GTC 200',
      );
      await tester.ensureVisible(createButton);
      await tester.pumpAndSettle();
      await tester.tap(createButton);
      await tester.pump();
      await client.generateStarted.future;

      expect(client.fetchedOrderIds, isEmpty);

      realtimeEvents.add(
        BuildASonOrderRealtimeEvent.fromRealtimeEvent(
          const GtexRealtimeEvent(
            type: 'regen.creation_order.generated',
            topic: 'wallet',
            payload: <String, Object?>{'order_id': 'order-1'},
          ),
        )!,
      );
      await tester.pump();
      await tester.pump();

      expect(client.fetchedOrderIds, <String>['order-1']);
      expect(find.text('Regen creation confirmed'), findsOneWidget);
      expect(
        find.textContaining(
          'Ayo Realtime entered the academy as ST, OVR 55, POT 91.',
        ),
        findsOneWidget,
      );
      expect(completedCount, 1);

      client.completeGeneration();
      await tester.pumpAndSettle();

      expect(client.fetchedOrderIds, <String>['order-1', 'order-1']);
      expect(completedCount, 1);
    },
  );
}

Future<void> _completeCurrentWizardDraftAndPreview(WidgetTester tester) async {
  await _tapVisible(tester, find.text('Victor Adebayo'));
  await _tapVisible(tester, find.widgetWithText(FilledButton, 'Next'));
  await _tapVisible(
    tester,
    find.widgetWithText(FilterChip, 'Clinical Finisher - Parent'),
  );
  await _tapVisible(
    tester,
    find.widgetWithText(FilterChip, 'Pace Burst - Parent'),
  );
  await _tapVisible(
    tester,
    find.widgetWithText(FilterChip, 'Poacher - Parent'),
  );
  await _tapVisible(tester, find.widgetWithText(FilledButton, 'Next'));
  await tester.enterText(_regenNameField, 'Ayo Adebayo');
  await _tapVisible(tester, find.widgetWithText(FilledButton, 'Next'));
}

Future<void> _setLargeSurface(WidgetTester tester) async {
  await tester.binding.setSurfaceSize(const Size(1200, 1000));
  addTearDown(() => tester.binding.setSurfaceSize(null));
}

Future<void> _tapVisible(WidgetTester tester, Finder finder) async {
  await tester.ensureVisible(finder);
  await tester.pumpAndSettle();
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

Finder get _regenNameField {
  return find.byWidgetPredicate(
    (Widget widget) =>
        widget is TextField && widget.decoration?.labelText == 'Regen name',
  );
}

class _RealtimeBuildASonClient implements BuildASonCreationClient {
  final List<RequestSonPreviewDraft> previewDrafts = <RequestSonPreviewDraft>[];
  final List<RequestSonOrderDraft> createdDrafts = <RequestSonOrderDraft>[];
  final List<String> paidOrderIds = <String>[];
  final List<String> generatedOrderIds = <String>[];
  final List<String> fetchedOrderIds = <String>[];
  final Completer<void> generateStarted = Completer<void>();
  final Completer<RegenCreationOrder> _generateCompleter =
      Completer<RegenCreationOrder>();

  void completeGeneration() {
    if (_generateCompleter.isCompleted) {
      return;
    }
    _generateCompleter.complete(_order(status: 'generated', generated: true));
  }

  @override
  Future<RequestSonOptions> fetchRequestSonOptions() async {
    return const RequestSonOptions(
      clubId: 'club-1',
      clubName: 'Lagos Royals',
      currency: 'GTC',
      pricing: RegenCreationPricing(
        baseCostCoin: 200,
        nameCostCoin: 0,
        customizationCostCoin: 0,
      ),
      nationalityOptions: <RequestSonNationalityOption>[
        RequestSonNationalityOption(
          code: 'NG',
          name: 'Nigeria',
          isDefault: true,
        ),
      ],
      positionOptions: <RequestSonPositionOption>[
        RequestSonPositionOption(
          code: 'AM',
          label: 'Attacking Midfielder',
          isDefault: true,
        ),
        RequestSonPositionOption(code: 'ST', label: 'Striker'),
      ],
      defaultCountryCode: 'NG',
      defaultPosition: 'AM',
      eligibleParents: <RegenCreationParentPlayer>[
        RegenCreationParentPlayer(
          playerId: 'parent-1',
          fullName: 'Victor Adebayo',
          position: 'ST',
          countryCode: 'NGA',
          overallRating: 84,
          generationNumber: 1,
          generationLabel: 'GEN-1',
          traits: <String>['Clinical Finisher', 'Pace Burst', 'Poacher'],
          lineage: <String>['Adebayo Line'],
        ),
      ],
    );
  }

  @override
  Future<RequestSonPreview> previewRequestSon(
    RequestSonPreviewDraft draft,
  ) async {
    previewDrafts.add(draft);
    return RequestSonPreview.fromJson(<String, Object?>{
      'parent': <String, Object?>{
        'player_id': draft.parentPlayerId,
        'full_name': 'Victor Adebayo',
        'position': 'ST',
        'country_code': 'NGA',
        'current_rating': 84,
        'generation': 1,
        'traits': <String>['Clinical Finisher', 'Pace Burst', 'Poacher'],
      },
      'selected_traits': draft.selectedTraits,
      'projected_dna': <String, Object?>{
        'PAC': 78,
        'SHO': 74,
        'PAS': 69,
        'DRI': 76,
        'DEF': 44,
        'PHY': 73,
      },
      'projected_ovr': 67,
      'projected_pot': 91,
      'parent_generation': 1,
      'projected_generation': 2,
      'generation_label': 'GEN-2',
      'total_cost_coin': 200,
      'wallet': <String, Object?>{
        'can_pay_with_wallet': true,
        'available_balance': 500,
        'reserved_balance': 0,
        'locked_balance': 0,
        'pending_withdrawal_balance': 0,
        'total_balance': 500,
        'currency': 'GTC',
      },
    });
  }

  @override
  Future<RegenCreationOrder> createRequestSonOrder(
    RequestSonOrderDraft draft,
  ) async {
    createdDrafts.add(draft);
    return _order(status: 'pending_payment');
  }

  @override
  Future<RegenCreationOrder> payWithWallet(String orderId) async {
    paidOrderIds.add(orderId);
    return _order(status: 'paid');
  }

  @override
  Future<RegenCreationOrder> generateAfterPayment(String orderId) {
    generatedOrderIds.add(orderId);
    if (!generateStarted.isCompleted) {
      generateStarted.complete();
    }
    return _generateCompleter.future;
  }

  @override
  Future<RegenCreationOrder> fetchCreationOrder(String orderId) async {
    fetchedOrderIds.add(orderId);
    return _order(
      status: 'generated',
      generated: true,
      playerName: 'Ayo Realtime',
    );
  }

  @override
  Future<RegenCreationOrder> cancelCreationOrder(String orderId) async {
    return _order(status: 'cancelled');
  }

  @override
  Future<void> refreshWalletTruth() async {}

  static RegenCreationOrder _order({
    required String status,
    bool generated = false,
    String playerName = 'Ayo Adebayo',
  }) {
    final DateTime now = DateTime.utc(2026, 5, 28, 12);
    final bool pendingReservation = status == 'pending_payment';
    return RegenCreationOrder(
      id: 'order-1',
      userId: 'user-1',
      requestType: 'son',
      amountCoin: 200,
      currency: 'GTC',
      paymentMethod: 'wallet',
      paymentReference:
          pendingReservation
              ? 'regen-wallet-reserve:order-1'
              : 'regen-wallet-order-1',
      status: status,
      walletReservation: RegenCreationWalletReservation(
        kind: 'regen_creation_order',
        key: 'order-1',
        status: pendingReservation ? 'reserved' : 'settled',
        amountCoin: 200,
        currency: 'coin',
        reference:
            pendingReservation
                ? 'regen-wallet-reserve:order-1'
                : 'regen-wallet-settle:order-1',
        lockReason: 'Build-a-Son creation reservation',
        updatedAt: now,
      ),
      createdAt: now,
      updatedAt: now,
      parentPlayerId: 'parent-1',
      requestedName: 'Ayo Adebayo',
      requestedCountryCode: 'NGA',
      requestedPosition: 'ST',
      generatedPlayer:
          generated
              ? RegenCreationGeneratedPlayer(
                playerId: 'regen-1',
                regenProfileId: 'profile-1',
                fullName: playerName,
                age: 15,
                position: 'ST',
                currentRating: 55,
                potentialRating: 91,
              )
              : null,
    );
  }
}
