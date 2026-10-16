import 'package:gte_frontend/app/test_runtime_detector.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';
import 'package:gte_frontend/data/gte_models.dart';

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
      final List<Map<String, dynamic>> payloads = await Future.wait(<
        Future<Map<String, dynamic>>
      >[
        client.getMap('/api/admin/operations-readiness'),
        client.getMap(
          '/api/admin/treasury/kyc',
          query: const <String, Object?>{'limit': 50, 'offset': 0},
        ),
        client.getMap(
          '/api/admin/treasury/disputes',
          query: const <String, Object?>{'limit': 50, 'offset': 0},
        ),
        client.getMap(
          '/api/admin/treasury/withdrawals',
          query: const <String, Object?>{'limit': 50, 'offset': 0},
        ),
        client.getMap(
          '/api/admin/wallets/purchase-orders',
          query: const <String, Object?>{'page': 1, 'per_page': 50},
        ),
      ]);
      final GtexOperationsReadinessSnapshot readiness =
          GtexOperationsReadinessSnapshot.fromJson(
            Map<String, Object?>.from(payloads[0]),
          );
      final GteAdminQueuePage<GteAdminKyc> kycPage =
          GteAdminQueuePage<GteAdminKyc>.fromJson(
            Map<String, Object?>.from(payloads[1]),
            GteAdminKyc.fromJson,
          );
      final GteAdminQueuePage<GteDispute> disputePage =
          GteAdminQueuePage<GteDispute>.fromJson(
            Map<String, Object?>.from(payloads[2]),
            GteDispute.fromJson,
          );
      final GteAdminQueuePage<GteAdminWithdrawal> withdrawalPage =
          GteAdminQueuePage<GteAdminWithdrawal>.fromJson(
            Map<String, Object?>.from(payloads[3]),
            GteAdminWithdrawal.fromJson,
          );
      final List<GtexOrderRecord> purchaseOrders = _mapPurchaseOrders(
        payloads[4],
      );
      final List<GtexOrderRecord> withdrawalOrders =
          withdrawalPage.items
              .map(_mapAdminWithdrawal)
              .toList(growable: false);
      return _stateFromOperationsReadiness(
        readiness,
        kycCases: kycPage.items.map(_mapAdminKyc).toList(growable: false),
        disputes:
            disputePage.items.map(_mapAdminDispute).toList(growable: false),
        orders: <GtexOrderRecord>[
          ...withdrawalOrders,
          ...purchaseOrders,
        ],
        transactions:
            withdrawalPage.items
                .map(_transactionFromWithdrawal)
                .toList(growable: false),
        pendingWithdrawalCredits: withdrawalPage.items
            .where(
              (GteAdminWithdrawal item) =>
                  item.status == GteWithdrawalStatus.pendingReview ||
                  item.status == GteWithdrawalStatus.pendingKyc ||
                  item.status == GteWithdrawalStatus.approved ||
                  item.status == GteWithdrawalStatus.processing,
            )
            .fold<double>(
              0,
              (double total, GteAdminWithdrawal item) =>
                  total + item.amountCoin,
            ),
      );
    }, () => _requireFixtures().load());
  }

  @override
  Future<void> reviewKyc(
    String profileId, {
    required bool approve,
    String? rejectionReason,
  }) {
    return client.withFallback<void>(() async {
      await client.post(
        '/api/admin/treasury/kyc/$profileId/review',
        body: <String, Object?>{
          'status': approve ? 'verified' : 'rejected',
          if (!approve)
            'rejection_reason':
                (rejectionReason != null && rejectionReason.trim().isNotEmpty)
                    ? rejectionReason.trim()
                    : 'Rejected by trust ops',
        },
      );
    }, () => _requireFixtures().reviewKyc(
      profileId,
      approve: approve,
      rejectionReason: rejectionReason,
    ));
  }

  @override
  Future<void> replyToDispute(
    String disputeId, {
    required String message,
  }) {
    final String trimmed = message.trim();
    if (trimmed.isEmpty) {
      throw const GteApiException(
        type: GteApiErrorType.validation,
        message: 'Dispute reply message is required.',
      );
    }
    return client.withFallback<void>(() async {
      await client.post(
        '/api/admin/treasury/disputes/$disputeId/messages',
        body: <String, Object?>{'message': trimmed},
      );
    }, () => _requireFixtures().replyToDispute(disputeId, message: trimmed));
  }

  @override
  Future<void> reviewOrder(
    String orderId, {
    required bool approve,
    required GtexOrderKind kind,
    String? notes,
  }) {
    return client.withFallback<void>(() async {
      switch (kind) {
        case GtexOrderKind.withdrawal:
          await client.post(
            '/api/admin/treasury/withdrawals/$orderId/status',
            body: <String, Object?>{
              'status': approve ? 'approved' : 'rejected',
              if (notes != null && notes.trim().isNotEmpty)
                'admin_notes': notes.trim(),
            },
          );
        case GtexOrderKind.purchase:
          await client.post(
            '/api/admin/wallets/purchase-orders/$orderId/status',
            body: <String, Object?>{
              'status': approve ? 'settled' : 'rejected',
              if (notes != null && notes.trim().isNotEmpty) 'notes': notes.trim(),
            },
          );
        case GtexOrderKind.ops:
          throw const GteApiException(
            type: GteApiErrorType.validation,
            message: 'Ops readiness rows are not mutable.',
          );
      }
    }, () => _requireFixtures().reviewOrder(
      orderId,
      approve: approve,
      kind: kind,
      notes: notes,
    ));
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
    GtexOperationsReadinessSnapshot snapshot, {
    required List<GtexKycCaseRecord> kycCases,
    required List<GtexDisputeRecord> disputes,
    required List<GtexOrderRecord> orders,
    required List<GtexTransactionRecord> transactions,
    required double pendingWithdrawalCredits,
  }) {
    final GtexOperationsReadinessQueue risk = _queue(
      snapshot,
      'risk_compliance',
    );
    final GtexOperationsReadinessQueue ledger = _queue(
      snapshot,
      'ledger_worker_health',
    );
    return GtexTrustOpsState(
      wallet: GtexWalletSummary(
        balanceCredits: _metricValue(ledger, 'user_wallets'),
        availableCredits: _metricValue(ledger, 'ledger_entries_24h'),
        pendingWithdrawalCredits: pendingWithdrawalCredits,
        kycStatus: _statusLabel(risk.status),
        lastUpdatedLabel: 'Ops ${_statusLabel(snapshot.status).toLowerCase()}',
      ),
      transactions: transactions,
      orders: orders,
      kycCases: kycCases,
      disputes: disputes,
      operationsReadiness: snapshot,
    );
  }

  List<GtexOrderRecord> _mapPurchaseOrders(Map<String, dynamic> payload) {
    final Object? rawItems = payload['items'];
    if (rawItems is! List) {
      return const <GtexOrderRecord>[];
    }
    return rawItems
        .whereType<Object>()
        .map(_mapPurchaseOrder)
        .toList(growable: false);
  }

  GtexOrderRecord _mapPurchaseOrder(Object value) {
    final Map<String, Object?> json = Map<String, Object?>.from(
      value as Map<dynamic, dynamic>,
    );
    final String id = '${json['id'] ?? ''}';
    final String reference = '${json['reference'] ?? id}';
    final String status = '${json['status'] ?? 'requested'}'.toLowerCase();
    final String provider = '${json['provider_key'] ?? 'provider'}';
    final double amount = _asDouble(json['net_amount'] ?? json['gross_amount']);
    return GtexOrderRecord(
      id: id,
      title: 'Purchase $reference',
      subtitle: '$provider · $status',
      totalCredits: amount,
      status: _purchaseTrustStatus(status),
      createdLabel:
          '${json['created_at'] ?? json['createdAt'] ?? 'Created'}',
      itemCount: 1,
      kind: GtexOrderKind.purchase,
    );
  }

  GtexOrderRecord _mapAdminWithdrawal(GteAdminWithdrawal item) {
    final String? fullName = item.userFullName?.trim();
    final String userLabel =
        (fullName != null && fullName.isNotEmpty) ? fullName : item.userEmail;
    return GtexOrderRecord(
      id: item.id,
      title: 'Withdrawal ${item.reference}',
      subtitle: '${item.bankName} · $userLabel · ${_withdrawalStatusLabel(item.status)}',
      totalCredits: item.amountCoin,
      status: _withdrawalTrustStatus(item.status),
      createdLabel:
          item.createdAt?.toUtc().toIso8601String() ?? 'Created',
      itemCount: 1,
      kind: GtexOrderKind.withdrawal,
    );
  }

  GtexTransactionRecord _transactionFromWithdrawal(GteAdminWithdrawal item) {
    return GtexTransactionRecord(
      id: item.id,
      title: 'Withdrawal ${item.reference}',
      subtitle: '${item.bankName} · ${_withdrawalStatusLabel(item.status)}',
      amountCredits: -item.amountCoin,
      status: _withdrawalTrustStatus(item.status),
      timestampLabel:
          item.createdAt?.toUtc().toIso8601String() ?? 'Live',
      type: 'Withdrawal',
    );
  }

  GtexTrustStatus _withdrawalTrustStatus(GteWithdrawalStatus status) {
    switch (status) {
      case GteWithdrawalStatus.paid:
      case GteWithdrawalStatus.approved:
        return GtexTrustStatus.healthy;
      case GteWithdrawalStatus.rejected:
      case GteWithdrawalStatus.cancelled:
        return GtexTrustStatus.blocked;
      case GteWithdrawalStatus.disputed:
        return GtexTrustStatus.attention;
      case GteWithdrawalStatus.pendingReview:
      case GteWithdrawalStatus.pendingKyc:
      case GteWithdrawalStatus.draft:
      case GteWithdrawalStatus.processing:
        return GtexTrustStatus.pending;
    }
  }

  String _withdrawalStatusLabel(GteWithdrawalStatus status) {
    switch (status) {
      case GteWithdrawalStatus.pendingReview:
        return 'pending review';
      case GteWithdrawalStatus.pendingKyc:
        return 'pending KYC';
      case GteWithdrawalStatus.approved:
        return 'approved';
      case GteWithdrawalStatus.rejected:
        return 'rejected';
      case GteWithdrawalStatus.processing:
        return 'processing';
      case GteWithdrawalStatus.paid:
        return 'paid';
      case GteWithdrawalStatus.disputed:
        return 'disputed';
      case GteWithdrawalStatus.cancelled:
        return 'cancelled';
      case GteWithdrawalStatus.draft:
        return 'draft';
    }
  }

  GtexTrustStatus _purchaseTrustStatus(String status) {
    switch (status) {
      case 'settled':
        return GtexTrustStatus.healthy;
      case 'rejected':
      case 'failed':
      case 'cancelled':
      case 'expired':
        return GtexTrustStatus.blocked;
      case 'disputed':
      case 'chargeback':
      case 'reversed':
        return GtexTrustStatus.attention;
      case 'reviewing':
      case 'requested':
      case 'processing':
      default:
        return GtexTrustStatus.pending;
    }
  }

  double _asDouble(Object? value) {
    if (value is num) {
      return value.toDouble();
    }
    return double.tryParse('$value') ?? 0;
  }

  GtexDisputeRecord _mapAdminDispute(GteDispute item) {
    final String? fullName = item.userFullName?.trim();
    final String counterparty =
        (fullName != null && fullName.isNotEmpty) ? fullName : item.userEmail;
    final String? subject = item.subject?.trim();
    return GtexDisputeRecord(
      id: item.id,
      title:
          (subject != null && subject.isNotEmpty) ? subject : item.reference,
      counterparty: counterparty,
      status: _disputeTrustStatus(item.status),
      amountCredits: 0,
      openedLabel:
          item.createdAt?.toUtc().toIso8601String() ?? 'Opened',
      summary:
          '${item.resourceType} ${item.resourceId} · ${item.reference}',
    );
  }

  GtexTrustStatus _disputeTrustStatus(GteDisputeStatus status) {
    switch (status) {
      case GteDisputeStatus.resolved:
      case GteDisputeStatus.closed:
        return GtexTrustStatus.resolved;
      case GteDisputeStatus.awaitingUser:
        return GtexTrustStatus.pending;
      case GteDisputeStatus.awaitingAdmin:
      case GteDisputeStatus.open:
        return GtexTrustStatus.attention;
    }
  }

  GtexKycCaseRecord _mapAdminKyc(GteAdminKyc item) {
    final String? fullName = item.userFullName?.trim();
    final String userName =
        (fullName != null && fullName.isNotEmpty) ? fullName : item.userEmail;
    final String? country = item.country?.trim();
    return GtexKycCaseRecord(
      id: item.id,
      userName: userName,
      country:
          (country != null && country.isNotEmpty) ? country : 'Unknown',
      level: _kycLevelLabel(item.status),
      status: _kycTrustStatus(item.status),
      submittedLabel:
          item.submittedAt?.toUtc().toIso8601String() ?? 'Awaiting submit time',
      riskLabel: _kycRiskLabel(item.status),
      notes: _kycNotes(item),
    );
  }

  GtexTrustStatus _kycTrustStatus(GteKycStatus status) {
    switch (status) {
      case GteKycStatus.fullyVerified:
        return GtexTrustStatus.healthy;
      case GteKycStatus.rejected:
        return GtexTrustStatus.blocked;
      case GteKycStatus.pending:
      case GteKycStatus.partialVerifiedNoId:
        return GtexTrustStatus.pending;
      case GteKycStatus.unverified:
        return GtexTrustStatus.attention;
    }
  }

  String _kycLevelLabel(GteKycStatus status) {
    switch (status) {
      case GteKycStatus.fullyVerified:
        return 'Verified';
      case GteKycStatus.rejected:
        return 'Rejected';
      case GteKycStatus.partialVerifiedNoId:
        return 'Partial';
      case GteKycStatus.pending:
        return 'Under review';
      case GteKycStatus.unverified:
        return 'Unverified';
    }
  }

  String _kycRiskLabel(GteKycStatus status) {
    switch (status) {
      case GteKycStatus.fullyVerified:
        return 'Cleared';
      case GteKycStatus.rejected:
        return 'Rejected';
      case GteKycStatus.pending:
      case GteKycStatus.partialVerifiedNoId:
        return 'Manual review';
      case GteKycStatus.unverified:
        return 'Incomplete';
    }
  }

  String _kycNotes(GteAdminKyc item) {
    final String? reason = item.rejectionReason?.trim();
    if (reason != null && reason.isNotEmpty) {
      return reason;
    }
    final List<String> parts = <String>[
      if (item.userEmail.isNotEmpty) item.userEmail,
      if (item.city != null && item.city!.trim().isNotEmpty) item.city!.trim(),
      if (item.state != null && item.state!.trim().isNotEmpty) item.state!.trim(),
    ];
    if (parts.isEmpty) {
      return 'Treasury KYC profile ${item.id}';
    }
    return parts.join(' · ');
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
}
