import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';
import 'package:gte_frontend/data/gte_mock_api.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/features/capital/wallet/presentation/gte_kyc_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('KYC screen does not invent country or submission timestamp', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1400, 1800);
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final _KycTruthApi repository = _KycTruthApi();
    final GteExchangeController controller = GteExchangeController(
      api: _fixtureClient(repository),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GteKycScreen(controller: controller),
      ),
    );
    await tester.pumpAndSettle();

    expect(
      find.text('No submission timestamp published by backend.'),
      findsOneWidget,
    );
    expect(find.text('Nigeria'), findsNothing);

    await tester.enterText(find.byType(TextField).at(0), '12345678901');
    await tester.enterText(find.byType(TextField).at(2), '12 Marina Road');
    await tester.tap(find.text('Submit KYC'));
    await tester.pumpAndSettle();

    expect(find.text('Country is required.'), findsOneWidget);

    await tester.enterText(find.byType(TextField).at(6), 'Ghana');
    await tester.tap(find.text('Submit KYC'));
    await tester.pumpAndSettle();

    expect(repository.submittedCountry, 'Ghana');
  });

  testWidgets('KYC accepts backend document proof without local ID defaults', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1400, 1800);
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final _KycDocumentOnlyApi repository = _KycDocumentOnlyApi();
    final GteExchangeController controller = GteExchangeController(
      api: _fixtureClient(repository),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GteKycScreen(controller: controller),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('National ID number (if required)'), findsOneWidget);
    expect(find.text('Bank verification number (if required)'), findsOneWidget);

    await tester.enterText(find.byType(TextField).at(2), '12 Marina Road');
    await tester.enterText(find.byType(TextField).at(6), 'Ghana');
    await tester.tap(find.text('Submit KYC'));
    await tester.pumpAndSettle();

    expect(repository.submittedNin, isNull);
    expect(repository.submittedBvn, isNull);
    expect(repository.submittedAttachmentId, 'kyc-existing-doc');
  });
}

class _KycTruthApi extends GteMockApi {
  String? submittedCountry;

  @override
  Future<GteKycProfile> fetchKycProfile() async {
    return const GteKycProfile(
      id: 'kyc-profile-1',
      status: GteKycStatus.unverified,
      nin: null,
      bvn: null,
      addressLine1: null,
      addressLine2: null,
      city: null,
      state: null,
      country: null,
      idDocumentAttachmentId: null,
      submittedAt: null,
      reviewedAt: null,
      rejectionReason: null,
      createdAt: null,
      updatedAt: null,
    );
  }

  @override
  Future<GteKycProfile> submitKycProfile(GteKycSubmitRequest request) async {
    submittedCountry = request.country;
    return GteKycProfile(
      id: 'kyc-profile-1',
      status: GteKycStatus.pending,
      nin: request.nin,
      bvn: request.bvn,
      addressLine1: request.addressLine1,
      addressLine2: request.addressLine2,
      city: request.city,
      state: request.state,
      country: request.country,
      idDocumentAttachmentId: request.idDocumentAttachmentId,
      submittedAt: DateTime.utc(2026, 5, 29, 0, 0),
      reviewedAt: null,
      rejectionReason: null,
      createdAt: null,
      updatedAt: null,
    );
  }
}

class _KycDocumentOnlyApi extends GteMockApi {
  String? submittedNin;
  String? submittedBvn;
  String? submittedAttachmentId;

  @override
  Future<GteKycProfile> fetchKycProfile() async {
    return const GteKycProfile(
      id: 'kyc-profile-2',
      status: GteKycStatus.unverified,
      nin: null,
      bvn: null,
      addressLine1: null,
      addressLine2: null,
      city: null,
      state: null,
      country: null,
      idDocumentAttachmentId: 'kyc-existing-doc',
      submittedAt: null,
      reviewedAt: null,
      rejectionReason: null,
      createdAt: null,
      updatedAt: null,
    );
  }

  @override
  Future<GteKycProfile> submitKycProfile(GteKycSubmitRequest request) async {
    submittedNin = request.nin;
    submittedBvn = request.bvn;
    submittedAttachmentId = request.idDocumentAttachmentId;
    return GteKycProfile(
      id: 'kyc-profile-2',
      status: GteKycStatus.pending,
      nin: request.nin,
      bvn: request.bvn,
      addressLine1: request.addressLine1,
      addressLine2: request.addressLine2,
      city: request.city,
      state: request.state,
      country: request.country,
      idDocumentAttachmentId: request.idDocumentAttachmentId,
      submittedAt: DateTime.utc(2026, 5, 29),
      reviewedAt: null,
      rejectionReason: null,
      createdAt: null,
      updatedAt: null,
    );
  }
}

GteExchangeApiClient _fixtureClient(GteMockApi repository) {
  return GteExchangeApiClient(
    config: const GteRepositoryConfig(
      baseUrl: 'http://127.0.0.1:8000',
      mode: GteBackendMode.fixture,
    ),
    transport: GteHttpTransport(),
    repository: repository,
  );
}
