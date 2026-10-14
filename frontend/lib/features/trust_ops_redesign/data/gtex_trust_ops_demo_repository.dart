import '../models/gtex_trust_ops_models.dart';

abstract class GtexTrustOpsRepository {
  const GtexTrustOpsRepository();

  Future<GtexTrustOpsState> load();

  /// Approve or reject a treasury KYC profile. Demo/fixture repos no-op.
  Future<void> reviewKyc(
    String profileId, {
    required bool approve,
    String? rejectionReason,
  }) async {}

  /// Post an admin reply on a treasury dispute. Demo/fixture repos no-op.
  Future<void> replyToDispute(
    String disputeId, {
    required String message,
  }) async {}

  /// Approve or reject a withdrawal / purchase order. Demo/fixture repos no-op.
  Future<void> reviewOrder(
    String orderId, {
    required bool approve,
    required GtexOrderKind kind,
    String? notes,
  }) async {}
}

/// Fixture repository used by tests and offline preview mode.
class GtexTrustOpsDemoRepository extends GtexTrustOpsRepository {
  const GtexTrustOpsDemoRepository();

  @override
  Future<GtexTrustOpsState> load() async {
    await Future<void>.delayed(const Duration(milliseconds: 80));
    return const GtexTrustOpsState(
      wallet: GtexWalletSummary(
        balanceCredits: 12500000,
        availableCredits: 10250000,
        pendingWithdrawalCredits: 750000,
        kycStatus: 'Tier 2 verified',
        lastUpdatedLabel: 'Updated just now',
      ),
      transactions: <GtexTransactionRecord>[
        GtexTransactionRecord(
          id: 'tx-001',
          title: 'Top up confirmed',
          subtitle: 'Wallet funding via card',
          amountCredits: 2500000,
          status: GtexTrustStatus.healthy,
          timestampLabel: 'Today, 09:40',
          type: 'Deposit',
        ),
        GtexTransactionRecord(
          id: 'tx-002',
          title: 'Player purchase escrow',
          subtitle: 'Arsenal shortlist basket',
          amountCredits: -4100000,
          status: GtexTrustStatus.pending,
          timestampLabel: 'Yesterday, 21:12',
          type: 'Order',
        ),
        GtexTransactionRecord(
          id: 'tx-003',
          title: 'Withdrawal requested',
          subtitle: 'Bank payout pending review',
          amountCredits: -750000,
          status: GtexTrustStatus.attention,
          timestampLabel: '2 days ago',
          type: 'Withdrawal',
        ),
      ],
      orders: <GtexOrderRecord>[
        GtexOrderRecord(
          id: 'wd-901',
          title: 'Withdrawal WD-901',
          subtitle: 'GTBank · Ayo Clubhouse · pending review',
          totalCredits: 750000,
          status: GtexTrustStatus.pending,
          createdLabel: 'Today',
          itemCount: 1,
          kind: GtexOrderKind.withdrawal,
        ),
        GtexOrderRecord(
          id: 'po-902',
          title: 'Purchase PO-902',
          subtitle: 'Card top-up · reviewing',
          totalCredits: 1250000,
          status: GtexTrustStatus.attention,
          createdLabel: 'Yesterday',
          itemCount: 1,
          kind: GtexOrderKind.purchase,
        ),
      ],
      kycCases: <GtexKycCaseRecord>[
        GtexKycCaseRecord(
          id: 'kyc-201',
          userName: 'Ayo Clubhouse',
          country: 'Nigeria',
          level: 'Tier 1',
          status: GtexTrustStatus.pending,
          submittedLabel: '12 minutes ago',
          riskLabel: 'Manual review',
          notes: 'Address document needs operator confirmation.',
        ),
        GtexKycCaseRecord(
          id: 'kyc-user',
          userName: 'Current user',
          country: 'Nigeria',
          level: 'Tier 2',
          status: GtexTrustStatus.healthy,
          submittedLabel: 'Approved',
          riskLabel: 'Low risk',
          notes:
              'User can top up, withdraw, buy players, and join paid tournaments.',
        ),
      ],
      disputes: <GtexDisputeRecord>[
        GtexDisputeRecord(
          id: 'dsp-301',
          title: 'Order escrow clarification',
          counterparty: 'Lagos Titans FC',
          status: GtexTrustStatus.attention,
          amountCredits: 2200000,
          openedLabel: 'Today',
          summary:
              'Buyer claims basket payment was captured but club transfer status is still pending.',
        ),
        GtexDisputeRecord(
          id: 'dsp-302',
          title: 'Rental eligibility challenge',
          counterparty: 'GTEX AFCON U20',
          status: GtexTrustStatus.resolved,
          amountCredits: 450000,
          openedLabel: 'Last week',
          summary:
              'Resolved after national-team eligibility check was refreshed.',
        ),
      ],
    );
  }
}
