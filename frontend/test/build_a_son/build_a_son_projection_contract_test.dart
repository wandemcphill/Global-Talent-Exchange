import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/build_a_son/build_a_son.dart';
import 'package:gte_frontend/models/regen_creation_models.dart';

// Tests that _previewContractBlockReason catches semantically invalid but
// structurally parseable preview payloads — i.e. cases where the model parses
// successfully but the wizard must still block creation.

void main() {
  testWidgets(
    'zeroed DNA bars in preview block confirmation with DNA message',
    (WidgetTester tester) async {
      await _setLargeSurface(tester);
      final _ProjectionContractClient client = _ProjectionContractClient(
        previewFactory: (RequestSonPreviewDraft draft) {
          final Map<String, Object?> payload = _basePayload(draft);
          payload['projected_dna'] = <String, Object?>{
            'PAC': 0,
            'SHO': 0,
            'PAS': 0,
            'DRI': 0,
            'DEF': 0,
            'PHY': 0,
          };
          return RequestSonPreview.fromJson(payload);
        },
      );

      await _completeDraftAndPreview(tester, client);

      expect(find.text('Creation blocked'), findsOneWidget);
      expect(
        find.text('Backend preview is missing projected DNA bars.'),
        findsOneWidget,
      );
      expect(_confirmButton(tester).onPressed, isNull);
      expect(client.createdDrafts, isEmpty);
    },
  );

  testWidgets(
    'backend echoing wrong parent generation blocks confirmation',
    (WidgetTester tester) async {
      await _setLargeSurface(tester);
      // The selected parent has generationNumber = 1.
      // The backend echoes parent_generation = 2 (wrong generation for that
      // player). projected_generation = 3 (valid N+1 relative to echo, so the
      // parser accepts it), but the wizard's contract check 8 fires because
      // the echoed parent generation does not match the selected player.
      final _ProjectionContractClient client = _ProjectionContractClient(
        previewFactory: (RequestSonPreviewDraft draft) {
          final Map<String, Object?> payload = _basePayload(draft);
          payload['parent_generation'] = 2;
          payload['projected_generation'] = 3; // N+1 relative to echo — parser ok
          payload['generation_label'] = 'GEN-3';
          return RequestSonPreview.fromJson(payload);
        },
      );

      await _completeDraftAndPreview(tester, client);

      expect(find.text('Creation blocked'), findsOneWidget);
      expect(
        find.text(
          'Backend preview parent generation does not match the selected player.',
        ),
        findsOneWidget,
      );
      expect(_confirmButton(tester).onPressed, isNull);
      expect(client.createdDrafts, isEmpty);
    },
  );

  testWidgets(
    'trait echo mismatch in preview blocks confirmation',
    (WidgetTester tester) async {
      await _setLargeSurface(tester);
      // Client will select Clinical Finisher / Pace Burst / Poacher but the
      // backend echo returns a different set.
      final _ProjectionContractClient client = _ProjectionContractClient(
        previewFactory: (RequestSonPreviewDraft draft) {
          final Map<String, Object?> payload = _basePayload(draft);
          // Override echoed traits to something the user did not select.
          payload['selected_traits'] = <String>[
            'Clinical Finisher',
            'Pace Burst',
            'Set Piece Ace',
          ];
          return RequestSonPreview.fromJson(payload);
        },
      );

      await _completeDraftAndPreview(tester, client);

      expect(find.text('Creation blocked'), findsOneWidget);
      expect(
        find.text(
          'Backend preview trait echo does not match the selected inheritance set.',
        ),
        findsOneWidget,
      );
      expect(_confirmButton(tester).onPressed, isNull);
      expect(client.createdDrafts, isEmpty);
    },
  );

  testWidgets(
    'POT below OVR in preview blocks confirmation',
    (WidgetTester tester) async {
      await _setLargeSurface(tester);
      final _ProjectionContractClient client = _ProjectionContractClient(
        previewFactory: (RequestSonPreviewDraft draft) {
          final Map<String, Object?> payload = _basePayload(draft);
          payload['projected_ovr'] = 85;
          payload['projected_pot'] = 70; // POT < OVR
          return RequestSonPreview.fromJson(payload);
        },
      );

      await _completeDraftAndPreview(tester, client);

      expect(find.text('Creation blocked'), findsOneWidget);
      expect(
        find.text('Backend preview returned POT below OVR.'),
        findsOneWidget,
      );
      expect(_confirmButton(tester).onPressed, isNull);
      expect(client.createdDrafts, isEmpty);
    },
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

Future<void> _setLargeSurface(WidgetTester tester) async {
  await tester.binding.setSurfaceSize(const Size(1200, 1000));
  addTearDown(() => tester.binding.setSurfaceSize(null));
}

Future<void> _completeDraftAndPreview(
  WidgetTester tester,
  _ProjectionContractClient client,
) async {
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
  await _tapVisible(tester, find.widgetWithText(FilledButton, 'Next'));
  await tester.enterText(_regenNameField, 'Ayo Adebayo');
  await _tapVisible(tester, find.widgetWithText(FilledButton, 'Next'));
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

// A valid complete payload that can be mutated per-test to introduce specific
// contract violations.  All values are in range; wallet is available.
Map<String, Object?> _basePayload(RequestSonPreviewDraft draft) {
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

// ---------------------------------------------------------------------------
// Stub client — only preview varies; all other calls are unreachable.
// ---------------------------------------------------------------------------

typedef _PreviewFactory = RequestSonPreview Function(
  RequestSonPreviewDraft draft,
);

class _ProjectionContractClient implements BuildASonCreationClient {
  _ProjectionContractClient({required this.previewFactory});

  final _PreviewFactory previewFactory;
  final List<RequestSonOrderDraft> createdDrafts = <RequestSonOrderDraft>[];

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
    return previewFactory(draft);
  }

  @override
  Future<RegenCreationOrder> createRequestSonOrder(
    RequestSonOrderDraft draft,
  ) async {
    createdDrafts.add(draft);
    throw StateError(
      'Projection contract tests must not reach createRequestSonOrder.',
    );
  }

  @override
  Future<RegenCreationOrder> fetchCreationOrder(String orderId) async {
    throw StateError(
      'Projection contract tests must not reach fetchCreationOrder.',
    );
  }

  @override
  Future<RegenCreationOrder> payWithWallet(String orderId) async {
    throw StateError(
      'Projection contract tests must not reach payWithWallet.',
    );
  }

  @override
  Future<RegenCreationOrder> cancelCreationOrder(String orderId) async {
    throw StateError(
      'Projection contract tests must not reach cancelCreationOrder.',
    );
  }

  @override
  Future<RegenCreationOrder> generateAfterPayment(String orderId) async {
    throw StateError(
      'Projection contract tests must not reach generateAfterPayment.',
    );
  }

  @override
  Future<void> refreshWalletTruth() async {}
}
