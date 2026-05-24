import 'package:gte_frontend/app/test_runtime_detector.dart';

import 'gte_api_repository.dart';
import 'gte_authed_api.dart';
import 'gte_http_transport.dart';
import '../models/risk_ops_models.dart';

class RiskOpsApi {
  RiskOpsApi({required this.client, required _RiskOpsFixtures? fixtures})
    : _fixtures = fixtures;

  final GteAuthedApi client;
  final _RiskOpsFixtures? _fixtures;

  factory RiskOpsApi.standard({
    required String baseUrl,
    required String? accessToken,
    GteBackendMode mode = GteBackendMode.live,
  }) {
    final GteBackendMode resolvedMode = gteProductionBackendMode(mode);
    return RiskOpsApi(
      client: GteAuthedApi(
        config: GteRepositoryConfig(baseUrl: baseUrl, mode: resolvedMode),
        transport: GteHttpTransport(),
        accessToken: accessToken,
        mode: resolvedMode,
      ),
      fixtures: null,
    );
  }

  factory RiskOpsApi.fixture() {
    assertFixtureFactoryAllowed('RiskOpsApi.fixture');
    return RiskOpsApi(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.fixture,
        ),
        transport: GteHttpTransport(),
        accessToken: 'fixture-token',
        mode: GteBackendMode.fixture,
      ),
      fixtures: _RiskOpsFixtures.seed(),
    );
  }

  Future<RiskOverview> fetchOverview() {
    return client.withFallback<RiskOverview>(() async {
      final Map<String, dynamic> payload = await client.getMap(
        '/admin/risk-ops/overview',
      );
      return RiskOverview.fromJson(payload);
    }, () => _requireFixtures().overview());
  }

  _RiskOpsFixtures _requireFixtures() {
    final _RiskOpsFixtures? fixtures = _fixtures;
    if (fixtures == null) {
      throw const GteApiException(
        type: GteApiErrorType.unavailable,
        message: 'Risk Ops fixtures are not registered in strict-live runtime.',
      );
    }
    return fixtures;
  }
}

class _RiskOpsFixtures {
  _RiskOpsFixtures(this._overview);

  final RiskOverview _overview;

  static _RiskOpsFixtures seed() {
    return _RiskOpsFixtures(
      RiskOverview(
        openAmlCases: 2,
        openFraudCases: 1,
        openSystemEvents: 3,
        highRiskUsers: 4,
        activeScans: 1,
        lastScanSummary: 'No critical threats detected in last run.',
      ),
    );
  }

  Future<RiskOverview> overview() async => _overview;
}
