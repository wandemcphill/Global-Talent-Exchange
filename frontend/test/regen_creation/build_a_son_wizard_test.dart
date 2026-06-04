import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/regen_creation/data/build_a_son_creation_client.dart';
import 'package:gte_frontend/features/regen_creation/presentation/build_a_son_wizard.dart';
import 'package:gte_frontend/models/regen_creation_models.dart';

void main() {
  testWidgets('Build-a-Son mirrors v13 steps and confirms wallet flow', (
    WidgetTester tester,
  ) async {
    await _setLargeSurface(tester);
    final _FakeBuildASonClient client = _FakeBuildASonClient();

    await tester.pumpWidget(MaterialApp(home: BuildASonWizard(client: client)));
    await tester.pumpAndSettle();

    expect(find.text('Choose a senior parent'), findsOneWidget);
    expect(find.text('Victor Adebayo'), findsOneWidget);

    await _tapVisible(tester, find.text('Victor Adebayo'));
    await _tapVisible(tester, find.widgetWithText(FilledButton, 'Next'));
    await tester.pumpAndSettle();

    expect(find.text('Choose exactly 3 inherited traits'), findsOneWidget);
    await _tapVisible(
      tester,
      find.widgetWithText(FilterChip, 'Leader - Parent'),
    );
    await _tapVisible(
      tester,
      find.widgetWithText(FilterChip, 'Two-Footed - Parent'),
    );
    await _tapVisible(
      tester,
      find.widgetWithText(FilterChip, 'Clutch Finisher - Parent'),
    );
    await tester.pumpAndSettle();
    expect(find.text('3/3 selected'), findsOneWidget);

    await _tapVisible(tester, find.widgetWithText(FilledButton, 'Next'));
    await tester.pumpAndSettle();
    expect(find.text('Identity'), findsOneWidget);

    await tester.enterText(_regenNameField, 'Ayo Adebayo');
    await _tapVisible(tester, find.widgetWithText(FilledButton, 'Next'));
    await tester.pumpAndSettle();

    expect(client.previewDrafts, hasLength(1));
    expect(client.previewDrafts.single.selectedTraits, hasLength(3));
    expect(find.text('Projected DNA Stats'), findsOneWidget);
    expect(find.text('Wallet available'), findsOneWidget);
    expect(find.text('Create GEN-2 Regen - GTC 200'), findsOneWidget);

    await _tapVisible(
      tester,
      find.widgetWithText(FilledButton, 'Create GEN-2 Regen - GTC 200'),
    );
    await tester.pumpAndSettle();

    expect(client.createdDrafts, hasLength(1));
    expect(client.createdDrafts.single.selectedTraits, hasLength(3));
    expect(client.createdOrder?.status, 'pending_payment');
    expect(
      client.createdOrder?.paymentReference,
      'regen-wallet-reserve:order-1',
    );
    expect(client.createdOrder?.walletReservation?.isReserved, isTrue);
    expect(client.createdOrder?.hasReservedWalletFunds, isTrue);
    expect(client.paidOrderIds, <String>['order-1']);
    expect(client.paidOrder?.paymentReference, 'regen-wallet-order-1');
    expect(client.paidOrder?.walletReservation?.isSettled, isTrue);
    expect(client.generatedOrderIds, <String>['order-1']);
    expect(client.walletRefreshCount, 2);
    expect(client.fetchedOrderIds, <String>['order-1']);
    expect(client.lifecycleEvents, <String>[
      'create:pending_payment:regen-wallet-reserve:order-1',
      'refresh-wallet',
      'pay:order-1',
      'generate:order-1',
      'refresh-wallet',
      'fetch:order-1',
    ]);
    expect(find.text('Regen creation confirmed'), findsOneWidget);
  });

  testWidgets('Build-a-Son blocks confirmation when preview is unavailable', (
    WidgetTester tester,
  ) async {
    await _setLargeSurface(tester);
    final _FakeBuildASonClient client = _FakeBuildASonClient(
      previewError: StateError('preview contract missing'),
    );

    await tester.pumpWidget(MaterialApp(home: BuildASonWizard(client: client)));
    await tester.pumpAndSettle();

    await _tapVisible(tester, find.text('Victor Adebayo'));
    await _tapVisible(tester, find.widgetWithText(FilledButton, 'Next'));
    await tester.pumpAndSettle();
    await _tapVisible(
      tester,
      find.widgetWithText(FilterChip, 'Leader - Parent'),
    );
    await _tapVisible(
      tester,
      find.widgetWithText(FilterChip, 'Two-Footed - Parent'),
    );
    await _tapVisible(
      tester,
      find.widgetWithText(FilterChip, 'Clutch Finisher - Parent'),
    );
    await tester.pumpAndSettle();
    await _tapVisible(tester, find.widgetWithText(FilledButton, 'Next'));
    await tester.pumpAndSettle();
    await tester.enterText(_regenNameField, 'Ayo Adebayo');
    await _tapVisible(tester, find.widgetWithText(FilledButton, 'Next'));
    await tester.pumpAndSettle();

    expect(find.text('Preview unavailable'), findsOneWidget);
    expect(find.textContaining('preview contract missing'), findsOneWidget);
    expect(client.createdDrafts, isEmpty);
  });
}

Future<void> _setLargeSurface(WidgetTester tester) async {
  await tester.binding.setSurfaceSize(const Size(1200, 1000));
  addTearDown(() => tester.binding.setSurfaceSize(null));
}

Future<void> _tapVisible(WidgetTester tester, Finder finder) async {
  await tester.ensureVisible(finder);
  await tester.pumpAndSettle();
  await tester.tap(finder);
}

Finder get _regenNameField {
  return find.byWidgetPredicate(
    (Widget widget) =>
        widget is TextField && widget.decoration?.labelText == 'Regen name',
  );
}

class _FakeBuildASonClient implements BuildASonCreationClient {
  _FakeBuildASonClient({this.previewError});

  final Object? previewError;
  final List<RequestSonPreviewDraft> previewDrafts = <RequestSonPreviewDraft>[];
  final List<RequestSonOrderDraft> createdDrafts = <RequestSonOrderDraft>[];
  final List<String> paidOrderIds = <String>[];
  final List<String> generatedOrderIds = <String>[];
  final List<String> fetchedOrderIds = <String>[];
  final List<String> lifecycleEvents = <String>[];
  RegenCreationOrder? createdOrder;
  RegenCreationOrder? paidOrder;
  int walletRefreshCount = 0;

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
          traits: <String>['Leader', 'Two-Footed', 'Clutch Finisher'],
          lineage: <String>['Adebayo Line'],
          dnaProfile: RegenDnaProfile(
            ratings: <String, int>{
              'PAC': 88,
              'SHO': 82,
              'PAS': 72,
              'DRI': 83,
              'DEF': 40,
              'PHY': 78,
            },
          ),
        ),
      ],
    );
  }

  @override
  Future<RequestSonPreview> previewRequestSon(
    RequestSonPreviewDraft draft,
  ) async {
    previewDrafts.add(draft);
    final Object? error = previewError;
    if (error != null) {
      throw error;
    }
    return RequestSonPreview.fromJson(<String, Object?>{
      'parent': <String, Object?>{
        'player_id': draft.parentPlayerId,
        'full_name': 'Victor Adebayo',
        'position': 'ST',
        'country_code': 'NGA',
        'current_rating': 84,
        'generation': 1,
        'traits': <String>['Leader', 'Two-Footed', 'Clutch Finisher'],
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
    final RegenCreationOrder order = _order(status: 'pending_payment');
    createdOrder = order;
    lifecycleEvents.add(
      'create:${order.status}:${order.paymentReference ?? 'no-reference'}',
    );
    return order;
  }

  @override
  Future<RegenCreationOrder> fetchCreationOrder(String orderId) async {
    fetchedOrderIds.add(orderId);
    lifecycleEvents.add('fetch:$orderId');
    return _order(status: 'generated', generated: true);
  }

  @override
  Future<RegenCreationOrder> payWithWallet(String orderId) async {
    paidOrderIds.add(orderId);
    lifecycleEvents.add('pay:$orderId');
    final RegenCreationOrder order = _order(status: 'paid');
    paidOrder = order;
    return order;
  }

  @override
  Future<RegenCreationOrder> cancelCreationOrder(String orderId) async {
    return _order(status: 'cancelled');
  }

  @override
  Future<RegenCreationOrder> generateAfterPayment(String orderId) async {
    generatedOrderIds.add(orderId);
    lifecycleEvents.add('generate:$orderId');
    return _order(status: 'generated', generated: true);
  }

  @override
  Future<void> refreshWalletTruth() async {
    walletRefreshCount += 1;
    lifecycleEvents.add('refresh-wallet');
  }

  RegenCreationOrder _order({required String status, bool generated = false}) {
    final DateTime now = DateTime.utc(2026, 5, 28, 12);
    final bool pendingReservation = status == 'pending_payment';
    final bool releasedReservation = status == 'cancelled';
    return RegenCreationOrder(
      id: 'order-1',
      userId: 'user-1',
      requestType: 'son',
      amountCoin: 200,
      currency: 'GTC',
      paymentMethod: 'wallet',
      paymentReference:
          pendingReservation || releasedReservation
              ? 'regen-wallet-reserve:order-1'
              : 'regen-wallet-order-1',
      status: status,
      walletReservation: RegenCreationWalletReservation(
        kind: 'regen_creation_order',
        key: 'order-1',
        status:
            pendingReservation
                ? 'reserved'
                : releasedReservation
                ? 'released'
                : 'settled',
        amountCoin: 200,
        currency: 'coin',
        reference:
            pendingReservation
                ? 'regen-wallet-reserve:order-1'
                : releasedReservation
                ? 'regen-wallet-release:order-1'
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
              ? const RegenCreationGeneratedPlayer(
                playerId: 'regen-1',
                regenProfileId: 'profile-1',
                fullName: 'Ayo Adebayo',
                age: 15,
                position: 'ST',
                currentRating: 55,
                potentialRating: 91,
              )
              : null,
    );
  }
}
