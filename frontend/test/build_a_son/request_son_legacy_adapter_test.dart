import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/build_a_son/build_a_son.dart';
import 'package:gte_frontend/features/regens/request_son_screen.dart';
import 'package:gte_frontend/models/regen_creation_models.dart';

void main() {
  testWidgets('legacy request-son route mounts canonical Build-a-Son wizard', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1100, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          buildASonCreationClientProvider.overrideWithValue(
            const _AdapterBuildASonClient(),
          ),
        ],
        child: const MaterialApp(
          home: RequestSonScreen(
            apiBaseUrl: 'https://api.gtex.local',
            backendMode: GteBackendMode.live,
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Build-a-Son'), findsWidgets);
    expect(find.text('Choose a senior parent'), findsOneWidget);
    expect(find.text('Request a son'), findsNothing);
    expect(find.text('Current quote'), findsNothing);
    expect(find.text('Create KoraPay order'), findsNothing);
    expect(find.text('Create and pay with wallet'), findsNothing);
  });
}

class _AdapterBuildASonClient implements BuildASonCreationClient {
  const _AdapterBuildASonClient();

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
  Future<RequestSonPreview> previewRequestSon(RequestSonPreviewDraft draft) {
    throw UnimplementedError();
  }

  @override
  Future<RegenCreationOrder> createRequestSonOrder(RequestSonOrderDraft draft) {
    throw UnimplementedError();
  }

  @override
  Future<RegenCreationOrder> fetchCreationOrder(String orderId) {
    throw UnimplementedError();
  }

  @override
  Future<RegenCreationOrder> generateAfterPayment(String orderId) {
    throw UnimplementedError();
  }

  @override
  Future<RegenCreationOrder> payWithWallet(String orderId) {
    throw UnimplementedError();
  }

  @override
  Future<RegenCreationOrder> cancelCreationOrder(String orderId) {
    throw UnimplementedError();
  }

  @override
  Future<void> refreshWalletTruth() {
    throw UnimplementedError();
  }
}
