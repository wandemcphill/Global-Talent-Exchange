import 'package:gte_frontend/app/test_runtime_detector.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';

import '../models/gtex_trust_ops_models.dart';
import 'gtex_trust_ops_demo_repository.dart';

class GtexTrustOpsApiRepository extends GtexTrustOpsRepository {
  GtexTrustOpsApiRepository({required this.client, required this.fixtures});

  final GteAuthedApi client;
  final GtexTrustOpsDemoRepository? fixtures;

  factory GtexTrustOpsApiRepository.standard({
    required String baseUrl,
    required String? accessToken,
    GteBackendMode mode = GteBackendMode.live,
  }) {
    final GteBackendMode resolvedMode = gteProductionBackendMode(mode);
    return GtexTrustOpsApiRepository(
      client: GteAuthedApi(
        config: GteRepositoryConfig(baseUrl: baseUrl, mode: resolvedMode),
        transport: GteHttpTransport(),
        accessToken: accessToken,
        mode: resolvedMode,
      ),
      fixtures: null,
    );
  }

  factory GtexTrustOpsApiRepository.fixture() {
    assertFixtureFactoryAllowed('GtexTrustOpsApiRepository.fixture');
    return GtexTrustOpsApiRepository(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.fixture,
        ),
        transport: GteHttpTransport(),
        accessToken: 'fixture-token',
        mode: GteBackendMode.fixture,
      ),
      fixtures: const GtexTrustOpsDemoRepository(),
    );
  }

  @override
  Future<GtexTrustOpsState> load() {
    return client.withFallback<GtexTrustOpsState>(() async {
      final Map<String, dynamic> payload = await client.getMap(
        '/api/admin/operations-readiness',
      );
      return _stateFromOperationsReadiness(
        GtexOperationsReadinessSnapshot.fromJson(payload),
      );
    }, () => _requireFixtures().load());
  }

  GtexTrustOpsDemoRepository _requireFixtures() {
    final GtexTrustOpsDemoRepository? resolvedFixtures = fixtures;
    if (resolvedFixtures == null) {
      throw StateError(
        'Trust Ops demo repository is not registered in strict-live runtime.',
      );
    }
    return resolvedFixtures;
  }

  GtexTrustOpsState _stateFromOperationsReadiness(
    GtexOperationsReadinessSnapshot snapshot,
  ) {
    final GtexOperationsReadinessQueue risk = _queue(
      snapshot,
      'risk_compliance',
    );
    final GtexOperationsReadinessQueue moderation = _queue(
      snapshot,
      'moderation_disputes',
    );
    final GtexOperationsReadinessQueue policy = _queue(
      snapshot,
      'policy_launch_control',
    );
    final GtexOperationsReadinessQueue diagnostics = _queue(
      snapshot,
      'production_data_diagnostics',
    );
    final GtexOperationsReadinessQueue ledger = _queue(
      snapshot,
      'ledger_worker_health',
    );
    return GtexTrustOpsState(
      wallet: GtexWalletSummary(
        balanceCredits: _metricValue(ledger, 'user_wallets'),
        availableCredits: _metricValue(ledger, 'ledger_entries_24h'),
        pendingWithdrawalCredits: _metricValue(
          ledger,
          'pending_wallet_transactions',
        ),
        kycStatus: _statusLabel(risk.status),
        lastUpdatedLabel: 'Ops ${_statusLabel(snapshot.status).toLowerCase()}',
      ),
      transactions: <GtexTransactionRecord>[
        _transactionFromQueue(ledger, 'ledger'),
        _transactionFromQueue(policy, 'launch'),
        _transactionFromQueue(diagnostics, 'data'),
      ],
      orders: <GtexOrderRecord>[
        _orderFromQueue(ledger),
        _orderFromQueue(policy),
        _orderFromQueue(diagnostics),
      ],
      kycCases: <GtexKycCaseRecord>[
        GtexKycCaseRecord(
          id: 'risk-compliance',
          userName: risk.title,
          country: 'Global',
          level: '${_metricDisplay(risk, 'pending_kyc')} pending KYC',
          status: _trustStatus(risk.status),
          submittedLabel: 'Live',
          riskLabel: _statusLabel(risk.status),
          notes: risk.description,
        ),
        GtexKycCaseRecord(
          id: 'policy-launch',
          userName: policy.title,
          country: 'Regions',
          level:
              '${_metricDisplay(policy, 'active_policy_documents')} policies',
          status: _trustStatus(policy.status),
          submittedLabel: 'Live',
          riskLabel: _statusLabel(policy.status),
          notes: policy.description,
        ),
      ],
      disputes: <GtexDisputeRecord>[
        GtexDisputeRecord(
          id: 'moderation-disputes',
          title: moderation.title,
          counterparty: moderation.owner,
          status: _trustStatus(moderation.status),
          amountCredits: _metricValue(moderation, 'open_disputes'),
          openedLabel: 'Live',
          summary:
              moderation.alerts.isNotEmpty
                  ? moderation.alerts.join(' ')
                  : moderation.description,
        ),
      ],
      operationsReadiness: snapshot,
    );
  }

  GtexOperationsReadinessQueue _queue(
    GtexOperationsReadinessSnapshot snapshot,
    String key,
  ) {
    for (final GtexOperationsReadinessQueue queue in snapshot.queues) {
      if (queue.key == key) return queue;
    }
    return GtexOperationsReadinessQueue(
      key: key,
      title: key,
      description: 'No live data available.',
      status: 'ok',
      route: null,
      owner: 'operations',
      metrics: const <GtexOperationsReadinessMetric>[],
      alerts: const <String>[],
      actionRoutes: const <String>[],
    );
  }

  GtexTransactionRecord _transactionFromQueue(
    GtexOperationsReadinessQueue queue,
    String type,
  ) {
    final double value = queue.metrics.fold<double>(
      0,
      (double total, GtexOperationsReadinessMetric metric) =>
          total + metric.value,
    );
    return GtexTransactionRecord(
      id: 'ops-${queue.key}',
      title: queue.title,
      subtitle:
          queue.alerts.isNotEmpty ? queue.alerts.first : queue.description,
      amountCredits: value,
      status: _trustStatus(queue.status),
      timestampLabel: 'Live',
      type: type,
    );
  }

  GtexOrderRecord _orderFromQueue(GtexOperationsReadinessQueue queue) {
    final double issueCount = queue.metrics
        .where(
          (GtexOperationsReadinessMetric metric) =>
              metric.status == 'attention' || metric.status == 'blocked',
        )
        .fold<double>(
          0,
          (double total, GtexOperationsReadinessMetric metric) =>
              total + metric.value,
        );
    return GtexOrderRecord(
      id: 'ops-${queue.key}',
      title: queue.title,
      subtitle: queue.description,
      totalCredits: issueCount,
      status: _trustStatus(queue.status),
      createdLabel: 'Live',
      itemCount: queue.metrics.length,
    );
  }

  GtexTrustStatus _trustStatus(String status) {
    switch (status) {
      case 'blocked':
        return GtexTrustStatus.blocked;
      case 'attention':
      case 'maintenance':
        return GtexTrustStatus.attention;
      case 'gated':
      case 'hidden':
        return GtexTrustStatus.pending;
      default:
        return GtexTrustStatus.healthy;
    }
  }

  String _statusLabel(String status) {
    switch (status) {
      case 'blocked':
        return 'Blocked';
      case 'attention':
        return 'Needs attention';
      case 'gated':
        return 'Gated';
      case 'maintenance':
        return 'Maintenance';
      default:
        return 'Healthy';
    }
  }

  double _metricValue(GtexOperationsReadinessQueue queue, String key) {
    return queue.metric(key)?.value ?? 0;
  }

  String _metricDisplay(GtexOperationsReadinessQueue queue, String key) {
    return queue.metric(key)?.displayValue ?? '0';
  }
}
