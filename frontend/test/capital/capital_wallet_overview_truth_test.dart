import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/features/capital/wallet/data/capital_wallet_api.dart';
import 'package:gte_frontend/features/capital/wallet/data/capital_wallet_display_snapshot.dart';

void main() {
  test('capital market snapshot uses wallet overview as balance authority', () {
    final CapitalWalletMarketSnapshot snapshot =
        CapitalWalletMarketSnapshot.fromBackend(
          coinSnapshot: const CapitalWalletDisplaySnapshot(
            availableBalance: 7777,
            reservedBalance: 7777,
            lockedBalance: 7777,
            totalBalance: 7777,
            currency: GteLedgerUnit.coin,
            lockReasons: <String>['stale summary lock'],
          ),
          creditSnapshot: const CapitalWalletDisplaySnapshot(
            availableBalance: 320,
            reservedBalance: 0,
            lockedBalance: 0,
            totalBalance: 320,
            currency: GteLedgerUnit.credit,
          ),
          overview: const GteWalletOverview(
            availableBalance: 1200,
            reservedBalance: 250,
            lockedBalance: 250,
            lockReasons: <String>['backend transfer reservation'],
            pendingDeposits: 75,
            pendingWithdrawals: 125,
            totalInflow: 2000,
            totalOutflow: 800,
            withdrawableNow: 900,
            currency: GteLedgerUnit.coin,
            countryCode: 'NG',
            requiredPolicyAcceptancesMissing: 0,
            policyBlocked: false,
            depositMode: 'korapay_plus_bank_transfer',
            withdrawalMode: 'bank_transfer',
            paymentProviderStatus: <String, String>{
              'bank_transfer_manual': 'ready',
              'korapay': 'ready',
            },
          ),
          compliance: const GteComplianceStatus(
            countryCode: 'NG',
            countryPolicyBucket: 'ng_live',
            depositsEnabled: true,
            marketTradingEnabled: true,
            platformRewardWithdrawalsEnabled: true,
            requiredPolicyAcceptancesMissing: 0,
            missingPolicyAcceptances: <GtePolicyRequirementSummary>[],
            canDeposit: true,
            canWithdrawPlatformRewards: true,
            canTradeMarket: true,
          ),
        );

    expect(snapshot.coinAvailableBalance, 1200);
    expect(snapshot.reservedCoinBalance, 250);
    expect(snapshot.lockedCoinBalance, 250);
    expect(snapshot.pendingWithdrawalCoinBalance, 125);
    expect(snapshot.lockReasons, <String>['backend transfer reservation']);
    expect(snapshot.lockReasons, isNot(contains('stale summary lock')));
  });
}
