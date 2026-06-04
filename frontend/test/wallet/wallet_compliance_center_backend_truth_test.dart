import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';
import 'package:gte_frontend/data/gte_mock_api.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/features/capital/wallet/presentation/gte_policy_compliance_center_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('compliance center renders missing backend status as pending', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1400, 1600);
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final GteExchangeController controller = GteExchangeController(
      api: _fixtureClient(_PendingComplianceApi()),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: GtePolicyComplianceCenterScreen(controller: controller),
      ),
    );
    await tester.pumpAndSettle();

    expect(
      find.text('Compliance status is pending backend sync.'),
      findsOneWidget,
    );
    expect(find.text('Backend pending'), findsOneWidget);
    expect(find.text('Pending'), findsWidgets);
    expect(find.text('Open'), findsNothing);
    expect(
      find.text('All required policy acceptances are in place.'),
      findsNothing,
    );
    expect(
      find.text('Policy requirements are pending backend sync.'),
      findsOneWidget,
    );
  });
}

class _PendingComplianceApi extends GteMockApi {
  @override
  Future<List<GtePolicyDocumentSummary>> fetchPolicyDocuments({
    bool mandatoryOnly = false,
  }) async {
    return <GtePolicyDocumentSummary>[];
  }

  @override
  Future<GteComplianceStatus> fetchComplianceStatus() async {
    return GteComplianceStatus.fromJson(const <String, Object?>{});
  }

  @override
  Future<List<GtePolicyAcceptanceSummary>> fetchMyPolicyAcceptances() async {
    return <GtePolicyAcceptanceSummary>[];
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
