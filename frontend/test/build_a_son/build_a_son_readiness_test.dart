import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/build_a_son/build_a_son.dart';
import 'package:gte_frontend/models/regen_creation_models.dart';

void main() {
  testWidgets(
    'backend preview syncing state blocks confirmation until resolved',
    (WidgetTester tester) async {
      await _setLargeSurface(tester);
      final _ReadinessBuildASonClient client = _ReadinessBuildASonClient();

      await tester.pumpWidget(
        MaterialApp(home: BuildASonWizard(client: client)),
      );
      await tester.pumpAndSettle();

      await _completeDraftUntilPreviewRequest(tester);

      expect(client.previewDrafts, hasLength(1));
      expect(find.text('Syncing backend preview'), findsOneWidget);
      expect(
        find.textContaining(
          'GTEX is requesting projected DNA, OVR, POT, generation, cost, and wallet availability.',
        ),
        findsOneWidget,
      );
      final FilledButton awaitingButton = tester.widget<FilledButton>(
        find.widgetWithText(FilledButton, 'Awaiting backend preview'),
      );
      expect(awaitingButton.onPressed, isNull);
      expect(client.createdDrafts, isEmpty);

      client.completePreview();
      await tester.pumpAndSettle();

      expect(find.text('Projected DNA Stats'), findsOneWidget);
      expect(find.text('Wallet available'), findsOneWidget);
      final FilledButton confirmButton = tester.widget<FilledButton>(
        find.widgetWithText(FilledButton, 'Create GEN-2 Regen - GTC 200'),
      );
      expect(confirmButton.onPressed, isNotNull);
    },
  );

  testWidgets('backend option refresh resets stale parent selection safely', (
    WidgetTester tester,
  ) async {
    await _setLargeSurface(tester);
    final _ReadinessBuildASonClient client = _ReadinessBuildASonClient();

    await tester.pumpWidget(MaterialApp(home: BuildASonWizard(client: client)));
    await tester.pumpAndSettle();

    await _tapVisible(tester, find.text('Victor Adebayo'));
    await _tapVisible(tester, find.widgetWithText(FilledButton, 'Next'));
    expect(find.text('Choose exactly 3 inherited traits'), findsOneWidget);

    client.replaceParentsWithBackendRefresh();
    await _tapVisible(tester, find.byTooltip('Refresh backend options'));

    expect(find.text('Choose a senior parent'), findsOneWidget);
    expect(find.text('Choose exactly 3 inherited traits'), findsNothing);
    expect(find.text('Victor Adebayo'), findsNothing);
    expect(find.text('Musa Bello'), findsOneWidget);
    expect(client.previewDrafts, isEmpty);
    expect(client.createdDrafts, isEmpty);
  });
}

Future<void> _completeDraftUntilPreviewRequest(WidgetTester tester) async {
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
  final Finder confirmStepNext = find.widgetWithText(FilledButton, 'Next');
  await tester.ensureVisible(confirmStepNext);
  await tester.pump();
  await tester.tap(confirmStepNext);
  await tester.pump();
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

class _ReadinessBuildASonClient implements BuildASonCreationClient {
  final Completer<RequestSonPreview> _previewCompleter =
      Completer<RequestSonPreview>();
  final List<RequestSonPreviewDraft> previewDrafts = <RequestSonPreviewDraft>[];
  final List<RequestSonOrderDraft> createdDrafts = <RequestSonOrderDraft>[];
  bool _useRefreshedParents = false;

  void replaceParentsWithBackendRefresh() {
    _useRefreshedParents = true;
  }

  void completePreview() {
    if (_previewCompleter.isCompleted) {
      return;
    }
    _previewCompleter.complete(_completePreview(previewDrafts.single));
  }

  @override
  Future<RequestSonOptions> fetchRequestSonOptions() async {
    return RequestSonOptions(
      clubId: 'club-1',
      clubName: 'Lagos Royals',
      currency: 'GTC',
      pricing: const RegenCreationPricing(
        baseCostCoin: 200,
        nameCostCoin: 0,
        customizationCostCoin: 0,
      ),
      nationalityOptions: const <RequestSonNationalityOption>[
        RequestSonNationalityOption(
          code: 'NG',
          name: 'Nigeria',
          isDefault: true,
        ),
      ],
      positionOptions: const <RequestSonPositionOption>[
        RequestSonPositionOption(
          code: 'AM',
          label: 'Attacking Midfielder',
          isDefault: true,
        ),
        RequestSonPositionOption(code: 'CM', label: 'Central Midfielder'),
        RequestSonPositionOption(code: 'ST', label: 'Striker'),
      ],
      defaultCountryCode: 'NG',
      defaultPosition: 'AM',
      eligibleParents:
          _useRefreshedParents
              ? const <RegenCreationParentPlayer>[
                RegenCreationParentPlayer(
                  playerId: 'parent-2',
                  fullName: 'Musa Bello',
                  position: 'CM',
                  countryCode: 'NGA',
                  overallRating: 79,
                  generationNumber: 1,
                  generationLabel: 'GEN-1',
                  traits: <String>[
                    'Tempo Setter',
                    'Line Breaker',
                    'Press Resistant',
                  ],
                  lineage: <String>['Bello Line'],
                ),
              ]
              : const <RegenCreationParentPlayer>[
                RegenCreationParentPlayer(
                  playerId: 'parent-1',
                  fullName: 'Victor Adebayo',
                  position: 'ST',
                  countryCode: 'NGA',
                  overallRating: 84,
                  generationNumber: 1,
                  generationLabel: 'GEN-1',
                  traits: <String>[
                    'Clinical Finisher',
                    'Pace Burst',
                    'Poacher',
                  ],
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
    return _previewCompleter.future;
  }

  @override
  Future<RegenCreationOrder> createRequestSonOrder(
    RequestSonOrderDraft draft,
  ) async {
    createdDrafts.add(draft);
    return _order(status: 'pending_payment');
  }

  @override
  Future<RegenCreationOrder> fetchCreationOrder(String orderId) async {
    return _order(status: 'generated', generated: true);
  }

  @override
  Future<RegenCreationOrder> payWithWallet(String orderId) async {
    return _order(status: 'paid');
  }

  @override
  Future<RegenCreationOrder> cancelCreationOrder(String orderId) async {
    return _order(status: 'cancelled');
  }

  @override
  Future<RegenCreationOrder> generateAfterPayment(String orderId) async {
    return _order(status: 'generated', generated: true);
  }

  @override
  Future<void> refreshWalletTruth() async {}

  RegenCreationOrder _order({required String status, bool generated = false}) {
    final DateTime now = DateTime.utc(2026, 6);
    return RegenCreationOrder(
      id: 'order-1',
      userId: 'user-1',
      requestType: 'son',
      amountCoin: 200,
      currency: 'GTC',
      paymentMethod: 'wallet',
      paymentReference:
          status == 'pending_payment'
              ? 'regen-wallet-reserve:order-1'
              : 'regen-wallet-order-1',
      status: status,
      walletReservation: RegenCreationWalletReservation(
        kind: 'regen_creation_order',
        key: 'order-1',
        status: status == 'pending_payment' ? 'reserved' : 'settled',
        amountCoin: 200,
        currency: 'coin',
        reference:
            status == 'pending_payment'
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

RequestSonPreview _completePreview(RequestSonPreviewDraft draft) {
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
