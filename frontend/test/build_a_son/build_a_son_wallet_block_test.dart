import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/build_a_son/build_a_son.dart';
import 'package:gte_frontend/models/regen_creation_models.dart';

void main() {
  testWidgets('wallet-blocked preview cannot create a Build-a-Son order', (
    WidgetTester tester,
  ) async {
    await _setLargeSurface(tester);
    final _BlockedWalletBuildASonClient client =
        _BlockedWalletBuildASonClient();

    await tester.pumpWidget(MaterialApp(home: BuildASonWizard(client: client)));
    await tester.pumpAndSettle();

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
    expect(find.text('3/3 selected'), findsOneWidget);

    await _tapVisible(tester, find.widgetWithText(FilledButton, 'Next'));
    await tester.enterText(_regenNameField, 'Ayo Adebayo');
    await _tapVisible(tester, find.widgetWithText(FilledButton, 'Next'));

    expect(client.previewDrafts, hasLength(1));
    expect(
      client.previewDrafts.single.toJson(),
      containsPair('payment_method', 'wallet'),
    );
    expect(
      client.previewDrafts.single.toJson(),
      containsPair('requested_country_code', 'NG'),
      reason: 'Build-a-Son submits the backend nationality option code.',
    );
    expect(
      client.previewDrafts.single.toJson(),
      containsPair('requested_position', 'ST'),
    );
    expect(find.text('Creation blocked'), findsOneWidget);
    expect(find.text('Wallet blocked'), findsOneWidget);
    expect(
      find.text('Wallet has 100 GTC available for a 200 GTC creation.'),
      findsWidgets,
    );
    expect(find.text('Withdrawal review lock'), findsOneWidget);

    await _tapVisible(
      tester,
      find.widgetWithText(FilledButton, 'Create GEN-2 Regen - GTC 200'),
    );

    expect(client.createdDrafts, isEmpty);
    expect(client.paidOrderIds, isEmpty);
    expect(find.text('Creation blocked'), findsOneWidget);
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
  await tester.pumpAndSettle();
}

Finder get _regenNameField {
  return find.byWidgetPredicate(
    (Widget widget) =>
        widget is TextField && widget.decoration?.labelText == 'Regen name',
  );
}

class _BlockedWalletBuildASonClient implements BuildASonCreationClient {
  final List<RequestSonPreviewDraft> previewDrafts = <RequestSonPreviewDraft>[];
  final List<RequestSonOrderDraft> createdDrafts = <RequestSonOrderDraft>[];
  final List<String> paidOrderIds = <String>[];
  final List<String> fetchedOrderIds = <String>[];
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
          traits: <String>['Clinical Finisher', 'Pace Burst', 'Poacher'],
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
        'can_pay_with_wallet': false,
        'available_balance': 100,
        'reserved_balance': 60,
        'locked_balance': 140,
        'pending_withdrawal_balance': 25,
        'total_balance': 300,
        'currency': 'GTC',
        'blocked_reason':
            'Wallet has 100 GTC available for a 200 GTC creation.',
        'lock_reasons': <String>['Withdrawal review lock'],
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
  Future<RegenCreationOrder> fetchCreationOrder(String orderId) async {
    fetchedOrderIds.add(orderId);
    return _order(status: 'generated', generated: true);
  }

  @override
  Future<RegenCreationOrder> payWithWallet(String orderId) async {
    paidOrderIds.add(orderId);
    return _order(status: 'generated', generated: true);
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
  Future<void> refreshWalletTruth() async {
    walletRefreshCount += 1;
  }

  RegenCreationOrder _order({required String status, bool generated = false}) {
    final DateTime now = DateTime.utc(2026, 5, 28, 12);
    return RegenCreationOrder(
      id: 'order-1',
      userId: 'user-1',
      requestType: 'son',
      amountCoin: 200,
      currency: 'GTC',
      paymentMethod: 'wallet',
      status: status,
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
