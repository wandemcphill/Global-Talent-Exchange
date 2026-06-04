import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/features/capital/disputes/data/capital_dispute_fixture_store.dart';
import 'package:gte_frontend/features/capital/payouts/data/capital_payout_fixture_store.dart';
import 'package:gte_frontend/features/capital/settlement/data/capital_deposit_fixture_store.dart';
import 'package:gte_frontend/features/capital/wallet/data/capital_wallet_fixture_store.dart';

class CapitalTreasuryDashboardFixtureStore {
  CapitalTreasuryDashboardFixtureStore({
    required this.wallet,
    required this.deposits,
    required this.payouts,
    required this.disputes,
  });

  final CapitalWalletFixtureStore wallet;
  final CapitalDepositFixtureStore deposits;
  final CapitalPayoutFixtureStore payouts;
  final CapitalDisputeFixtureStore disputes;

  GteTreasuryDashboard fetchTreasuryDashboard() {
    final int pendingDeposits = deposits.pendingDepositCount;
    final int pendingWithdrawals = payouts.activeWithdrawalCount;
    final int pendingKyc =
        wallet.kycProfile.status == GteKycStatus.pending ? 1 : 0;
    final int openDisputes = disputes.openCount;
    return GteTreasuryDashboard(
      totalUsers: 12840,
      activeUsers: 3210,
      pendingDeposits: pendingDeposits,
      pendingWithdrawals: pendingWithdrawals,
      pendingKyc: pendingKyc,
      openDisputes: openDisputes,
      depositsConfirmedToday: 18,
      withdrawalsPaidToday: 7,
      walletLiability: wallet.coinSummary.totalBalance,
      pendingTreasuryExposure: pendingDeposits.toDouble(),
    );
  }
}
