import '../models/gtex_trust_ops_models.dart';

abstract class GtexTrustOpsRepository {
  const GtexTrustOpsRepository();

  Future<GtexTrustOpsState> load();
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
          id: 'ord-901',
          title: 'Player basket purchase',
          subtitle: '3 players shortlisted from Premier League clubs',
          totalCredits: 4100000,
          status: GtexTrustStatus.pending,
          createdLabel: 'Yesterday',
          itemCount: 3,
        ),
        GtexOrderRecord(
          id: 'ord-902',
          title: 'National team rental',
          subtitle: 'Nigeria U20 rental pool',
          totalCredits: 1250000,
          status: GtexTrustStatus.healthy,
          createdLabel: 'Last week',
          itemCount: 5,
        ),
      ],
      kycCases: <GtexKycCaseRecord>[
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
