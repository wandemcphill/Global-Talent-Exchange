import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/features/build_a_son/build_a_son.dart';
import 'package:gte_frontend/features/capital/wallet/data/capital_wallet_api.dart';
import 'package:gte_frontend/features/capital/wallet/data/capital_wallet_availability.dart';
import 'package:gte_frontend/features/capital/wallet/providers/capital_wallet_providers.dart';
import 'package:gte_frontend/models/regen_creation_models.dart';

typedef _PreviewFactory =
    RequestSonPreview Function(RequestSonPreviewDraft draft);

const List<RequestSonNationalityOption> _requestSonNationalityOptions =
    <RequestSonNationalityOption>[
      RequestSonNationalityOption(
        code: 'NG',
        name: 'Nigeria',
        alpha2Code: 'NG',
        isDefault: true,
      ),
      RequestSonNationalityOption(code: 'GH', name: 'Ghana', alpha2Code: 'GH'),
    ];

const List<RequestSonPositionOption> _requestSonPositionOptions =
    <RequestSonPositionOption>[
      RequestSonPositionOption(
        code: 'AM',
        label: 'Attacking Midfielder',
        aliases: <String>['CAM'],
        group: 'midfielder',
        isDefault: true,
      ),
      RequestSonPositionOption(
        code: 'DM',
        label: 'Defensive Midfielder',
        aliases: <String>['CDM'],
        group: 'midfielder',
      ),
      RequestSonPositionOption(
        code: 'ST',
        label: 'Striker',
        aliases: <String>['CF'],
        group: 'forward',
      ),
    ];

void main() {
  test('preview parser requires backend wallet availability', () {
    const RequestSonPreviewDraft draft = RequestSonPreviewDraft(
      parentPlayerId: 'parent-1',
      selectedTraits: <String>['Clinical Finisher', 'Pace Burst', 'Poacher'],
      requestedName: 'Ayo Adebayo',
      requestedCountryCode: 'NGA',
      requestedPosition: 'ST',
    );
    final Map<String, Object?> payload = _completePreviewPayload(draft);
    payload.remove('wallet');

    expect(
      () => RequestSonPreview.fromJson(payload),
      throwsA(
        isA<GteParsingException>().having(
          (GteParsingException error) => error.message,
          'message',
          contains('wallet availability'),
        ),
      ),
    );
  });

  test('parent options tolerate backend metadata DNA without six bars', () {
    final RequestSonOptions options = RequestSonOptions.fromJson(
      <String, Object?>{
        'club_id': 'club-1',
        'club_name': 'Preview FC',
        'currency': 'coin',
        'pricing': <String, Object?>{
          'base_cost_coin': 200,
          'name_cost_coin': 0,
          'customization_cost_coin': 0,
        },
        'nationality_options': <Object?>[
          <String, Object?>{
            'code': 'NG',
            'name': 'Nigeria',
            'alpha2_code': 'NG',
            'is_default': true,
          },
          <String, Object?>{'code': 'GH', 'name': 'Ghana', 'alpha2_code': 'GH'},
        ],
        'position_options': <Object?>[
          <String, Object?>{
            'code': 'AM',
            'label': 'Attacking Midfielder',
            'aliases': <String>['CAM'],
            'group': 'midfielder',
            'is_default': true,
          },
          <String, Object?>{
            'code': 'ST',
            'label': 'Striker',
            'aliases': <String>['CF'],
            'group': 'forward',
          },
        ],
        'default_country_code': 'NG',
        'default_position': 'AM',
        'eligible_parents': <Object?>[
          <String, Object?>{
            'player_id': 'parent-1',
            'full_name': 'Tomi Adebayo',
            'position': 'ST',
            'current_rating': 72,
            'nationality': 'Nigeria',
            'traits': <String>[
              'line breaker',
              'press resistant',
              'late runner',
            ],
            'generation': 1,
            'dna_profile': <String, Object?>{
              'archetype': 'poacher',
              'tempo': 64,
              'risk_taking': 58,
              'creativity': 61,
              'discipline': 72,
              'generation_label': 'GEN-1',
            },
            'lineage': <String, Object?>{
              'parent_player_id': 'root-player',
              'generation': 1,
            },
          },
        ],
      },
    );

    expect(options.eligibleParents.single.fullName, 'Tomi Adebayo');
    expect(options.eligibleParents.single.traits, hasLength(3));
    expect(options.eligibleParents.single.generationLabel, 'GEN-1');
    expect(options.eligibleParents.single.lineage, <String>['GEN-1']);
    expect(
      options.eligibleParents.single.lineage,
      isNot(contains('root-player')),
    );
    expect(options.eligibleParents.single.dnaProfile, isNull);
    expect(options.nationalityOptions.map((option) => option.code), <String>[
      'NG',
      'GH',
    ]);
    expect(
      options.positionOptions
          .singleWhere((option) => option.code == 'AM')
          .aliases,
      <String>['CAM'],
    );
    expect(options.defaultCountryCode, 'NG');
    expect(options.defaultPosition, 'AM');
  });

  test('preview parser requires backend pending withdrawal balance', () {
    const RequestSonPreviewDraft draft = RequestSonPreviewDraft(
      parentPlayerId: 'parent-1',
      selectedTraits: <String>['Clinical Finisher', 'Pace Burst', 'Poacher'],
      requestedName: 'Ayo Adebayo',
      requestedCountryCode: 'NGA',
      requestedPosition: 'ST',
    );
    final Map<String, Object?> payload = _completePreviewPayload(draft);
    final Map<String, Object?> wallet = Map<String, Object?>.from(
      payload['wallet']! as Map,
    );
    wallet.remove('pending_withdrawal_balance');
    payload['wallet'] = wallet;

    expect(
      () => RequestSonPreview.fromJson(payload),
      throwsA(
        isA<GteParsingException>().having(
          (GteParsingException error) => error.message,
          'message',
          contains('wallet.pending_withdrawal_balance'),
        ),
      ),
    );
  });

  test('order parser exposes backend wallet reservation truth', () {
    final DateTime now = DateTime.utc(2026, 5, 31, 9);
    final RegenCreationOrder order = RegenCreationOrder.fromJson(
      <String, Object?>{
        'id': 'order-1',
        'user_id': 'user-1',
        'request_type': 'son',
        'amount_coin': 200,
        'currency': 'COIN',
        'payment_method': 'wallet',
        'payment_provider': 'wallet',
        'payment_reference': 'regen-wallet-reserve:order-1',
        'status': 'pending_payment',
        'created_at': now.toIso8601String(),
        'updated_at': now.toIso8601String(),
        'wallet_reservation': <String, Object?>{
          'kind': 'regen_creation_order',
          'key': 'order-1',
          'status': 'reserved',
          'amount_coin': 200,
          'currency': 'coin',
          'reference': 'regen-wallet-reserve:order-1',
          'lock_reason': 'Build-a-Son creation reservation',
          'updated_at': now.toIso8601String(),
        },
      },
    );

    expect(order.isPendingPayment, isTrue);
    expect(order.hasReservedWalletFunds, isTrue);
    expect(order.walletReservation?.isReserved, isTrue);
    expect(order.walletReservation?.amountCoin, 200);
    expect(
      order.walletReservation?.lockReason,
      'Build-a-Son creation reservation',
    );
  });

  test('preview parser rejects generic DNA aliases as projected truth', () {
    const RequestSonPreviewDraft draft = RequestSonPreviewDraft(
      parentPlayerId: 'parent-1',
      selectedTraits: <String>['Clinical Finisher', 'Pace Burst', 'Poacher'],
      requestedName: 'Ayo Adebayo',
      requestedCountryCode: 'NGA',
      requestedPosition: 'ST',
    );
    final Map<String, Object?> payload = _completePreviewPayload(draft);
    final Object? projectedDna = payload.remove('projected_dna');
    payload['dna_profile'] = projectedDna;

    expect(
      () => RequestSonPreview.fromJson(payload),
      throwsA(
        isA<GteParsingException>().having(
          (GteParsingException error) => error.message,
          'message',
          contains('projected_dna'),
        ),
      ),
    );
  });

  testWidgets('requires exactly 3 inherited traits before previewing', (
    WidgetTester tester,
  ) async {
    await _setLargeSurface(tester);
    final _BuildASonClosureClient client = _BuildASonClosureClient();

    await _openWizard(tester, client);
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
    await _tapVisible(tester, find.widgetWithText(FilledButton, 'Next'));

    expect(find.text('Choose exactly 3 inherited traits'), findsOneWidget);
    expect(client.previewDrafts, isEmpty);

    await _tapVisible(
      tester,
      find.widgetWithText(FilterChip, 'Poacher - Parent'),
    );
    expect(find.text('3/3 selected'), findsOneWidget);

    final FilterChip fourthTrait = tester.widget<FilterChip>(
      find.widgetWithText(FilterChip, 'Set Piece Ace - Parent'),
    );
    expect(fourthTrait.onSelected, isNull);

    await _tapVisible(tester, find.widgetWithText(FilledButton, 'Next'));
    await tester.enterText(_regenNameField, 'Ayo Adebayo');
    await _tapVisible(tester, find.widgetWithText(FilledButton, 'Next'));

    expect(client.previewDrafts, hasLength(1));
    expect(client.previewDrafts.single.selectedTraits, hasLength(3));
    expect(
      client.previewDrafts.single.selectedTraits,
      unorderedEquals(<String>['Clinical Finisher', 'Pace Burst', 'Poacher']),
    );
    expect(
      client.previewDrafts.single.selectedTraits,
      isNot(contains('Set Piece Ace')),
    );
  });

  testWidgets('identity step uses backend position and nationality selectors', (
    WidgetTester tester,
  ) async {
    await _setLargeSurface(tester);
    final _BuildASonClosureClient client = _BuildASonClosureClient();

    await _openWizard(tester, client);
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

    final Finder dropdowns = find.byType(DropdownButtonFormField<String>);
    expect(dropdowns, findsNWidgets(2));
    expect(find.text('Nationality code'), findsNothing);

    await tester.tap(dropdowns.first);
    await tester.pumpAndSettle();
    expect(find.text('AM - Attacking Midfielder'), findsWidgets);
    expect(find.text('DM - Defensive Midfielder'), findsOneWidget);
    expect(find.text('CF'), findsNothing);
    await tester.tap(find.text('DM - Defensive Midfielder').last);
    await tester.pumpAndSettle();

    await tester.tap(dropdowns.at(1));
    await tester.pumpAndSettle();
    expect(find.text('GH - Ghana'), findsOneWidget);
    await tester.tap(find.text('GH - Ghana').last);
    await tester.pumpAndSettle();

    await tester.enterText(_regenNameField, 'Ayo Adebayo');
    await _tapVisible(tester, find.widgetWithText(FilledButton, 'Next'));

    expect(client.previewDrafts, hasLength(1));
    expect(client.previewDrafts.single.requestedPosition, 'DM');
    expect(client.previewDrafts.single.requestedCountryCode, 'GH');
    expect(
      client.previewDrafts.single.toJson(),
      containsPair('requested_position', 'DM'),
    );
    expect(
      client.previewDrafts.single.toJson(),
      containsPair('requested_country_code', 'GH'),
    );
  });

  testWidgets('missing backend preview fields block confirmation', (
    WidgetTester tester,
  ) async {
    await _setLargeSurface(tester);
    final _BuildASonClosureClient client = _BuildASonClosureClient(
      previewFactory: (RequestSonPreviewDraft draft) {
        final Map<String, Object?> payload = _completePreviewPayload(draft);
        payload.remove('projected_pot');
        return RequestSonPreview.fromJson(payload);
      },
    );

    await _completeDraftAndPreview(tester, client);

    expect(find.text('Preview unavailable'), findsOneWidget);
    expect(find.textContaining('projected_pot'), findsOneWidget);
    expect(_confirmButton(tester).onPressed, isNull);
    expect(client.createdDrafts, isEmpty);
  });

  testWidgets('generic DNA payloads cannot masquerade as projections', (
    WidgetTester tester,
  ) async {
    await _setLargeSurface(tester);
    final _BuildASonClosureClient client = _BuildASonClosureClient(
      previewFactory: (RequestSonPreviewDraft draft) {
        final Map<String, Object?> payload = _completePreviewPayload(draft);
        final Object? projectedDna = payload.remove('projected_dna');
        payload['dna_profile'] = projectedDna;
        return RequestSonPreview.fromJson(payload);
      },
    );

    await _completeDraftAndPreview(tester, client);

    expect(find.text('Preview unavailable'), findsOneWidget);
    expect(_confirmButton(tester).onPressed, isNull);
    expect(client.createdDrafts, isEmpty);
  });

  testWidgets('backend wallet availability evidence is required', (
    WidgetTester tester,
  ) async {
    await _setLargeSurface(tester);
    final _BuildASonClosureClient client = _BuildASonClosureClient(
      previewFactory: _previewWithoutWalletEvidence,
    );

    await _completeDraftAndPreview(tester, client);

    expect(find.text('Creation blocked'), findsOneWidget);
    expect(
      find.text('Backend wallet availability is missing.'),
      findsOneWidget,
    );
    expect(_confirmButton(tester).onPressed, isNull);
    expect(client.createdDrafts, isEmpty);
  });

  testWidgets('backend wallet eligibility owns confirmation decision', (
    WidgetTester tester,
  ) async {
    await _setLargeSurface(tester);
    final _BuildASonClosureClient client = _BuildASonClosureClient(
      previewFactory: _previewWithBackendEligibleLowDisplayedBalance,
    );

    await _completeDraftAndPreview(tester, client);

    expect(
      find.text('Backend wallet availability does not cover the preview cost.'),
      findsNothing,
    );

    final FilledButton confirmButton = tester.widget<FilledButton>(
      find.widgetWithText(FilledButton, 'Create GEN-2 Regen - GTC 200'),
    );
    expect(confirmButton.onPressed, isNotNull);

    await _tapVisible(
      tester,
      find.widgetWithText(FilledButton, 'Create GEN-2 Regen - GTC 200'),
    );

    expect(client.createdDrafts, hasLength(1));
    expect(client.createdDrafts.single.paymentMethod, 'wallet');
  });

  testWidgets(
    'create pay generate path is skipped when backend is incomplete',
    (WidgetTester tester) async {
      await _setLargeSurface(tester);
      final _BuildASonClosureClient client = _BuildASonClosureClient(
        previewFactory: (RequestSonPreviewDraft draft) {
          final Map<String, Object?> payload = _completePreviewPayload(draft);
          payload.remove('wallet');
          return RequestSonPreview.fromJson(payload);
        },
      );

      await _completeDraftAndPreview(tester, client);

      expect(find.text('Preview unavailable'), findsOneWidget);
      expect(client.previewDrafts, hasLength(1));
      expect(_confirmButton(tester).onPressed, isNull);
      expect(client.createdDrafts, isEmpty);
      expect(client.paidOrderIds, isEmpty);
      expect(client.generatedOrderIds, isEmpty);
    },
  );

  testWidgets(
    'wallet confirmation refreshes wallet truth and re-fetches final order',
    (WidgetTester tester) async {
      await _setLargeSurface(tester);
      final _BuildASonClosureClient client = _BuildASonClosureClient(
        reconciledPlayerName: 'Ayo Reconciled',
      );

      await _completeDraftAndPreview(tester, client);
      await _tapVisible(
        tester,
        find.widgetWithText(FilledButton, 'Create GEN-2 Regen - GTC 200'),
      );

      expect(client.createdDrafts, hasLength(1));
      expect(client.paidOrderIds, <String>['order-1']);
      expect(client.generatedOrderIds, <String>['order-1']);
      expect(client.walletRefreshCount, 2);
      expect(client.fetchedOrderIds, <String>['order-1']);
      expect(find.text('Regen creation confirmed'), findsOneWidget);
      expect(
        find.textContaining(
          'Ayo Reconciled entered the academy as ST, OVR 55, POT 91.',
        ),
        findsOneWidget,
      );
    },
  );

  testWidgets(
    'generation reconciliation polls until backend publishes generated son',
    (WidgetTester tester) async {
      await _setLargeSurface(tester);
      final _BuildASonClosureClient client = _BuildASonClosureClient(
        reconciledPlayerName: 'Ayo Eventually',
        fetchStatuses: <String>['generating', 'generated'],
      );

      await _completeDraftAndPreview(tester, client);
      await _tapVisible(
        tester,
        find.widgetWithText(FilledButton, 'Create GEN-2 Regen - GTC 200'),
      );

      expect(client.fetchedOrderIds, <String>['order-1', 'order-1']);
      expect(find.text('Regen creation confirmed'), findsOneWidget);
      expect(
        find.textContaining(
          'Ayo Eventually entered the academy as ST, OVR 55, POT 91.',
        ),
        findsOneWidget,
      );
    },
  );

  testWidgets(
    'generated status without generated player never completes the flow',
    (WidgetTester tester) async {
      await _setLargeSurface(tester);
      final _BuildASonClosureClient client = _BuildASonClosureClient(
        fetchStatuses: <String>['generated'],
        generatedFetchMissingPlayer: true,
      );
      int settledCount = 0;

      await tester.pumpWidget(
        MaterialApp(
          home: BuildASonWizard(
            client: client,
            onCompleted: (RegenCreationOrder order) async {
              settledCount += 1;
            },
          ),
        ),
      );
      await tester.pumpAndSettle();
      await _completeCurrentWizardDraftAndPreview(tester);
      await _tapVisible(
        tester,
        find.widgetWithText(FilledButton, 'Create GEN-2 Regen - GTC 200'),
      );

      expect(client.fetchedOrderIds, hasLength(4));
      expect(settledCount, 0);
      expect(find.text('Regen creation confirmed'), findsNothing);
      expect(
        find.textContaining('generated without generated player truth'),
        findsOneWidget,
      );
    },
  );

  testWidgets('wallet reservation order is settled before wallet refresh', (
    WidgetTester tester,
  ) async {
    await _setLargeSurface(tester);
    final _BuildASonClosureClient client = _BuildASonClosureClient(
      reconciledPlayerName: 'Ayo Reserved',
    );

    await _completeDraftAndPreview(tester, client);
    await _tapVisible(
      tester,
      find.widgetWithText(FilledButton, 'Create GEN-2 Regen - GTC 200'),
    );

    expect(client.createdDrafts, hasLength(1));
    expect(client.createdDrafts.single.paymentMethod, 'wallet');
    expect(
      client.createdOrder?.status,
      'pending_payment',
      reason: 'Create must reserve wallet funds instead of settling locally.',
    );
    expect(
      client.createdOrder?.paymentReference,
      'regen-wallet-reserve:order-1',
    );
    expect(client.createdOrder?.walletReservation?.isReserved, isTrue);
    expect(client.createdOrder?.hasReservedWalletFunds, isTrue);
    expect(client.createdOrder?.generatedPlayer, isNull);
    expect(client.paidOrderIds, <String>['order-1']);
    expect(client.paidOrder?.status, 'paid');
    expect(client.paidOrder?.paymentReference, 'regen-wallet-order-1');
    expect(client.paidOrder?.walletReservation?.isSettled, isTrue);
    expect(client.generatedOrderIds, <String>['order-1']);
    expect(client.walletRefreshCount, 2);
    expect(
      client.lifecycleEvents,
      <String>[
        'create:pending_payment:regen-wallet-reserve:order-1',
        'refresh-wallet',
        'pay:order-1',
        'generate:order-1',
        'refresh-wallet',
        'fetch:order-1',
      ],
      reason:
          'Flutter should settle the backend reservation, refresh wallet '
          'truth after payment, then reconcile the generated order.',
    );
    expect(find.text('Regen creation confirmed'), findsOneWidget);
    expect(
      find.textContaining(
        'Ayo Reserved entered the academy as ST, OVR 55, POT 91.',
      ),
      findsOneWidget,
    );
    expect(
      find.textContaining('Wallet reservation settled for coin 200.'),
      findsOneWidget,
    );
  });

  testWidgets('wallet reservation is released when payment fails', (
    WidgetTester tester,
  ) async {
    await _setLargeSurface(tester);
    final _BuildASonClosureClient client = _BuildASonClosureClient(
      payError: StateError('wallet settlement failed'),
    );

    await _completeDraftAndPreview(tester, client);
    await _tapVisible(
      tester,
      find.widgetWithText(FilledButton, 'Create GEN-2 Regen - GTC 200'),
    );

    expect(client.createdDrafts, hasLength(1));
    expect(client.paidOrderIds, <String>['order-1']);
    expect(client.cancelledOrderIds, <String>['order-1']);
    expect(client.generatedOrderIds, isEmpty);
    expect(client.fetchedOrderIds, isEmpty);
    expect(client.walletRefreshCount, 2);
    expect(client.lifecycleEvents, <String>[
      'create:pending_payment:regen-wallet-reserve:order-1',
      'refresh-wallet',
      'pay:order-1',
      'cancel:order-1',
      'refresh-wallet',
    ]);
    expect(find.textContaining('wallet settlement failed'), findsOneWidget);
    expect(
      find.textContaining('Reserved wallet funds were released.'),
      findsOneWidget,
    );
  });

  test('wallet reservation references stay on pending and paid orders', () {
    final _BuildASonClosureClient client = _BuildASonClosureClient();

    final RegenCreationOrder pending = client.orderForTest(
      status: 'pending_payment',
    );
    final RegenCreationOrder paid = client.orderForTest(status: 'paid');
    final RegenCreationOrder cancelled = client.orderForTest(
      status: 'cancelled',
    );

    expect(pending.usesWallet, isTrue);
    expect(pending.isPendingPayment, isTrue);
    expect(pending.paymentReference, 'regen-wallet-reserve:order-1');
    expect(
      pending.walletReservation?.reference,
      'regen-wallet-reserve:order-1',
    );
    expect(
      pending.walletReservation?.lockReason,
      'Build-a-Son creation reservation',
    );
    expect(pending.walletReservation?.amountCoin, 200);
    expect(pending.hasReservedWalletFunds, isTrue);
    expect(pending.generatedPlayer, isNull);
    expect(paid.paymentReference, 'regen-wallet-order-1');
    expect(paid.walletReservation?.reference, 'regen-wallet-settle:order-1');
    expect(paid.walletReservation?.isSettled, isTrue);
    expect(paid.isGenerated, isFalse);
    expect(cancelled.paymentReference, 'regen-wallet-reserve:order-1');
    expect(
      cancelled.walletReservation?.reference,
      'regen-wallet-release:order-1',
    );
    expect(cancelled.walletReservation?.isReleased, isTrue);
    expect(cancelled.isCancelled, isTrue);
  });

  testWidgets(
    'screen completion forwards the reconciled order to shell hooks',
    (WidgetTester tester) async {
      await _setLargeSurface(tester);
      final _BuildASonClosureClient client = _BuildASonClosureClient(
        reconciledPlayerName: 'Ayo Reconciled',
      );
      int settledCount = 0;
      RegenCreationOrder? settledOrder;

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            buildASonCreationClientProvider.overrideWithValue(client),
          ],
          child: MaterialApp(
            home: BuildASonScreen(
              onCompleted: (RegenCreationOrder order) async {
                settledCount += 1;
                settledOrder = order;
              },
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      await _completeCurrentWizardDraftAndPreview(tester);
      await _tapVisible(
        tester,
        find.widgetWithText(FilledButton, 'Create GEN-2 Regen - GTC 200'),
      );

      expect(client.walletRefreshCount, 2);
      expect(client.fetchedOrderIds, <String>['order-1']);
      expect(settledCount, 1);
      expect(settledOrder?.generatedPlayer?.fullName, 'Ayo Reconciled');
    },
  );

  test(
    'provider wallet refresh reconciles the shared capital wallet provider',
    () async {
      final _CountingCapitalWalletApi walletApi = _CountingCapitalWalletApi();
      final ProviderContainer container = ProviderContainer(
        overrides: [capitalWalletApiProvider.overrideWithValue(walletApi)],
      );
      addTearDown(container.dispose);

      await container.read(capitalWalletAvailabilityProvider.future);
      expect(walletApi.fetchAvailabilityCount, 1);

      final BuildASonCreationClient client = container.read(
        buildASonCreationClientProvider,
      );
      await client.refreshWalletTruth();

      expect(walletApi.fetchAvailabilityCount, 2);
      expect(
        container
            .read(capitalWalletAvailabilityProvider)
            .requireValue
            .availableBalanceCoin,
        502,
      );
    },
  );
}

Future<void> _openWizard(
  WidgetTester tester,
  _BuildASonClosureClient client,
) async {
  await tester.pumpWidget(MaterialApp(home: BuildASonWizard(client: client)));
  await tester.pumpAndSettle();
}

Future<void> _completeDraftAndPreview(
  WidgetTester tester,
  _BuildASonClosureClient client,
) async {
  await _openWizard(tester, client);
  await _completeCurrentWizardDraftAndPreview(tester);
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

FilledButton _confirmButton(WidgetTester tester) {
  return tester.widget<FilledButton>(
    find.widgetWithText(FilledButton, 'Awaiting backend preview'),
  );
}

Finder get _regenNameField {
  return find.byWidgetPredicate(
    (Widget widget) =>
        widget is TextField && widget.decoration?.labelText == 'Regen name',
  );
}

class _BuildASonClosureClient implements BuildASonCreationClient {
  _BuildASonClosureClient({
    this.previewFactory = _completePreview,
    this.reconciledPlayerName = 'Ayo Adebayo',
    this.fetchStatuses = const <String>['generated'],
    this.generatedFetchMissingPlayer = false,
    this.payError,
  });

  final _PreviewFactory previewFactory;
  final String reconciledPlayerName;
  final List<String> fetchStatuses;
  final bool generatedFetchMissingPlayer;
  final Object? payError;
  final List<RequestSonPreviewDraft> previewDrafts = <RequestSonPreviewDraft>[];
  final List<RequestSonOrderDraft> createdDrafts = <RequestSonOrderDraft>[];
  final List<String> paidOrderIds = <String>[];
  final List<String> cancelledOrderIds = <String>[];
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
      nationalityOptions: _requestSonNationalityOptions,
      positionOptions: _requestSonPositionOptions,
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
          traits: <String>[
            'Clinical Finisher',
            'Pace Burst',
            'Poacher',
            'Set Piece Ace',
          ],
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
    return previewFactory(draft);
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
    final int fetchIndex = fetchedOrderIds.length - 1;
    final List<String> statuses =
        fetchStatuses.isEmpty ? <String>['generated'] : fetchStatuses;
    final String status =
        statuses[fetchIndex < statuses.length
            ? fetchIndex
            : statuses.length - 1];
    return _order(
      status: status,
      generated: status == 'generated' && !generatedFetchMissingPlayer,
      playerName: reconciledPlayerName,
    );
  }

  @override
  Future<RegenCreationOrder> payWithWallet(String orderId) async {
    paidOrderIds.add(orderId);
    lifecycleEvents.add('pay:$orderId');
    final Object? error = payError;
    if (error != null) {
      throw error;
    }
    final RegenCreationOrder order = _order(status: 'paid');
    paidOrder = order;
    return order;
  }

  @override
  Future<RegenCreationOrder> cancelCreationOrder(String orderId) async {
    cancelledOrderIds.add(orderId);
    lifecycleEvents.add('cancel:$orderId');
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

  RegenCreationOrder orderForTest({required String status}) {
    return _order(status: status);
  }

  RegenCreationOrder _order({
    required String status,
    bool generated = false,
    String playerName = 'Ayo Adebayo',
  }) {
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

class _CountingCapitalWalletApi extends CapitalWalletApi {
  _CountingCapitalWalletApi() : super(client: _unusedAuthedApi());

  int fetchAvailabilityCount = 0;

  @override
  Future<CapitalWalletAvailability> fetchAvailability({
    GteLedgerUnit currency = GteLedgerUnit.coin,
  }) async {
    fetchAvailabilityCount += 1;
    return CapitalWalletAvailability(
      isAvailable: true,
      availableBalanceCoin: 500 + fetchAvailabilityCount.toDouble(),
      reservedBalanceCoin: 0,
      lockedBalanceCoin: 0,
      pendingWithdrawalBalanceCoin: 0,
      totalBalanceCoin: 500 + fetchAvailabilityCount.toDouble(),
      currency: currency,
    );
  }
}

GteAuthedApi _unusedAuthedApi() {
  return GteAuthedApi(
    config: const GteRepositoryConfig(baseUrl: 'https://api.gtex.test'),
    transport: const _FailingTransport(),
    accessToken: 'test-token',
  );
}

class _FailingTransport implements GteTransport {
  const _FailingTransport();

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) {
    throw StateError('Build-a-Son wallet refresh tests override wallet calls.');
  }
}

RequestSonPreview _completePreview(RequestSonPreviewDraft draft) {
  return RequestSonPreview.fromJson(_completePreviewPayload(draft));
}

RequestSonPreview _previewWithBackendEligibleLowDisplayedBalance(
  RequestSonPreviewDraft draft,
) {
  final Map<String, Object?> payload = _completePreviewPayload(draft);
  final Map<String, Object?> wallet = Map<String, Object?>.from(
    payload['wallet']! as Map,
  );
  wallet['can_pay_with_wallet'] = true;
  wallet['available_balance'] = 100;
  wallet['total_balance'] = 100;
  payload['wallet'] = wallet;
  return RequestSonPreview.fromJson(payload);
}

RequestSonPreview _previewWithoutWalletEvidence(RequestSonPreviewDraft draft) {
  return RequestSonPreview(
    parentPlayerId: draft.parentPlayerId,
    selectedTraits: draft.selectedTraits,
    projectedDna: const RegenDnaProfile(
      ratings: <String, int>{
        'PAC': 78,
        'SHO': 74,
        'PAS': 69,
        'DRI': 76,
        'DEF': 44,
        'PHY': 73,
      },
    ),
    projectedOverall: 67,
    projectedPotential: 91,
    parentGeneration: 1,
    generationNumber: 2,
    generationLabel: 'GEN-2',
    totalCostCoin: 200,
    currency: 'GTC',
    walletAvailability: const RegenCreationWalletAvailability(
      isAvailable: true,
      availableBalanceCoin: 0,
      reservedBalanceCoin: 0,
      lockedBalanceCoin: 0,
      pendingWithdrawalBalanceCoin: 0,
    ),
  );
}

Map<String, Object?> _completePreviewPayload(RequestSonPreviewDraft draft) {
  return <String, Object?>{
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
  };
}
