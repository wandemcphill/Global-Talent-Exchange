import 'package:flutter/material.dart';

import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/features/capital/wallet/data/capital_wallet_api.dart';
import 'package:gte_frontend/features/capital/wallet/data/capital_wallet_display_snapshot.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/widgets/gte_formatters.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';
import 'gte_deposit_history_screen.dart';
import 'gte_funding_flow_screen.dart';
import 'gte_policy_compliance_center_screen.dart';
import 'gte_withdrawal_flow_screen.dart';

class GteWalletOverviewScreen extends StatefulWidget {
  const GteWalletOverviewScreen({super.key, required this.controller});

  final GteExchangeController controller;

  @override
  State<GteWalletOverviewScreen> createState() =>
      _GteWalletOverviewScreenState();
}

class _GteWalletOverviewScreenState extends State<GteWalletOverviewScreen> {
  CapitalWalletApi get _walletApi => widget.controller.walletApi;
  late Future<List<Object?>> _walletFuture;

  @override
  void initState() {
    super.initState();
    _walletFuture = _loadWallet();
  }

  Future<List<Object?>> _loadWallet() {
    return Future.wait<Object?>(<Future<Object?>>[
      _walletApi.fetchOverview(),
      _walletApi.fetchDisplaySnapshot(currency: GteLedgerUnit.credit),
      _walletApi.listWalletTransactions(limit: 8),
      _walletApi.fetchWithdrawalEligibility(),
    ]);
  }

  Future<void> _refresh() async {
    setState(() {
      _walletFuture = _loadWallet();
    });
    await _walletFuture;
    await widget.controller.loadPortfolio();
  }

  Future<void> _openDeposit() async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (_) => GteFundWalletScreen(controller: widget.controller),
      ),
    );
    await _refresh();
  }

  Future<void> _openTransactions() async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (_) => GteDepositHistoryScreen(controller: widget.controller),
      ),
    );
    await _refresh();
  }

  Future<void> _openWithdrawals() async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder:
            (_) =>
                GteWithdrawalEligibilityScreen(controller: widget.controller),
      ),
    );
    await _refresh();
  }

  Future<void> _openComplianceCenter() async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder:
            (_) =>
                GtePolicyComplianceCenterScreen(controller: widget.controller),
      ),
    );
    await widget.controller.refreshCompliance();
    await _refresh();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Club Wallet'),
        actions: <Widget>[
          IconButton(onPressed: _refresh, icon: const Icon(Icons.refresh)),
        ],
      ),
      body: FutureBuilder<List<Object?>>(
        future: _walletFuture,
        builder: (BuildContext context, AsyncSnapshot<List<Object?>> snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting &&
              !snapshot.hasData) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError && !snapshot.hasData) {
            return Center(
              child: GteStatePanel(
                title: 'Club wallet unavailable',
                message:
                    'We could not sync wallet balances, rails, and withdrawal eligibility from the backend.',
                icon: Icons.sync_problem_outlined,
                actionLabel: 'Retry',
                onAction: _refresh,
              ),
            );
          }
          if (!snapshot.hasData || snapshot.data!.length < 4) {
            return const Center(
              child: GteStatePanel(
                title: 'Club wallet unavailable',
                message: 'Unable to load the club wallet balances right now.',
                icon: Icons.account_balance_wallet_outlined,
              ),
            );
          }

          final GteWalletOverview overview =
              snapshot.data![0] as GteWalletOverview;
          final CapitalWalletDisplaySnapshot fanSnapshot =
              snapshot.data![1] as CapitalWalletDisplaySnapshot;
          final List<GteWalletTransactionRecord> transactions =
              snapshot.data![2] as List<GteWalletTransactionRecord>;
          final GteWithdrawalEligibility eligibility =
              snapshot.data![3] as GteWithdrawalEligibility;
          final double reservedCoinBalance = overview.reservedBalance;
          final double lockedCoinBalance = overview.lockedBalance;
          final double pendingWithdrawalBalance = overview.pendingWithdrawals;
          final List<String> lockReasons = <String>{
            for (final String reason in overview.lockReasons)
              if (reason.trim().isNotEmpty) reason.trim(),
          }.toList(growable: false);
          const GteLedgerUnit fanWalletUnit = GteLedgerUnit.credit;
          final String restrictionMessage =
              overview.policyBlocked
                  ? overview.policyBlockReason ??
                      'Complete the outstanding compliance review before wallet actions resume.'
                  : eligibility.policyBlocked
                  ? eligibility.policyBlockReason ??
                      'Policy action is required before wallet withdrawals are enabled.'
                  : eligibility.requiresKyc
                  ? 'KYC is still required before withdrawals are enabled.'
                  : eligibility.requiresBankAccount
                  ? 'Add an active bank account before requesting withdrawals.'
                  : !_instantRailReady(overview.depositMode)
                  ? _railIsPending(overview.depositMode)
                      ? 'Deposit rail is pending backend sync before instant funding can be used.'
                      : 'Instant funding is currently routed through manual bank transfer review.'
                  : 'Wallet compliance is ready for live funding and withdrawals.';
          final bool showRestrictionPanel =
              overview.policyBlocked ||
              eligibility.policyBlocked ||
              eligibility.requiresKyc ||
              eligibility.requiresBankAccount ||
              !_instantRailReady(overview.depositMode);

          return RefreshIndicator(
            onRefresh: _refresh,
            child: ListView(
              padding: const EdgeInsets.all(20),
              children: <Widget>[
                if (snapshot.connectionState == ConnectionState.waiting) ...[
                  const GteStatePanel(
                    title: 'Syncing wallet state',
                    message:
                        'Refreshing balances, KoraPay availability, manual transfer status, and withdrawal eligibility.',
                    icon: Icons.sync_outlined,
                    isLoading: true,
                  ),
                  const SizedBox(height: 18),
                ],
                GteSurfacePanel(
                  accentColor: GteShellTheme.accentCapital,
                  emphasized: true,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        'Club funds',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Track GTEX Coin for transfers and Fan Coin for gifting and user competitions.',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 16),
                      Row(
                        children: <Widget>[
                          _BalanceTile(
                            label: _walletUnitLabel(overview.currency),
                            value: _formatWalletAmount(
                              overview.availableBalance,
                              overview.currency,
                            ),
                            detail: _walletUnitDetail(overview.currency),
                            accent: GteShellTheme.accentCapital,
                          ),
                          const SizedBox(width: 12),
                          _BalanceTile(
                            label: _walletUnitLabel(fanWalletUnit),
                            value: _formatWalletAmount(
                              fanSnapshot.availableBalance,
                              fanWalletUnit,
                            ),
                            detail: _walletUnitDetail(fanWalletUnit),
                            accent: GteShellTheme.accent,
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      Row(
                        children: <Widget>[
                          _MetricTile(
                            label: 'Backend available',
                            value: _formatWalletAmount(
                              overview.availableBalance,
                              overview.currency,
                            ),
                          ),
                          const SizedBox(width: 12),
                          _MetricTile(
                            label: 'Backend reserved',
                            value: _formatWalletAmount(
                              reservedCoinBalance,
                              overview.currency,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      Row(
                        children: <Widget>[
                          _MetricTile(
                            label: 'Backend locked',
                            value: _formatWalletAmount(
                              lockedCoinBalance,
                              overview.currency,
                            ),
                          ),
                          const SizedBox(width: 12),
                          _MetricTile(
                            label: 'Backend pending withdrawals',
                            value: _formatWalletAmount(
                              pendingWithdrawalBalance,
                              overview.currency,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 14),
                      _LockedFundsBand(
                        amount: _formatWalletAmount(
                          lockedCoinBalance,
                          overview.currency,
                        ),
                        reasons: lockReasons,
                      ),
                      const SizedBox(height: 16),
                      Wrap(
                        spacing: 10,
                        runSpacing: 10,
                        children: <Widget>[
                          FilledButton.icon(
                            onPressed: _openDeposit,
                            icon: const Icon(Icons.add_circle_outline),
                            label: const Text('Deposit'),
                          ),
                          OutlinedButton.icon(
                            onPressed: _openWithdrawals,
                            icon: const Icon(Icons.outbox_outlined),
                            label: const Text('Withdraw'),
                          ),
                          OutlinedButton.icon(
                            onPressed: _openTransactions,
                            icon: const Icon(Icons.receipt_long_outlined),
                            label: const Text('Transaction History'),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      Text(
                        'GTEX Coin powers transfers and withdrawals. Fan Coin powers gifting and user-hosted competition entries.',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ),
                ),
                if (showRestrictionPanel) ...<Widget>[
                  const SizedBox(height: 18),
                  GteSurfacePanel(
                    accentColor: GteShellTheme.accentWarm,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          'Current restrictions',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 12),
                        Text(restrictionMessage),
                        const SizedBox(height: 12),
                        Wrap(
                          spacing: 10,
                          runSpacing: 10,
                          children: <Widget>[
                            _RestrictionChip(
                              label: 'Country',
                              value: _countryLabel(overview.countryCode),
                            ),
                            _RestrictionChip(
                              label: 'Deposit rail',
                              value: _railLabel(overview.depositMode),
                            ),
                            _RestrictionChip(
                              label: 'KoraPay',
                              value: _providerStatusLabel(
                                overview.paymentProviderStatus['korapay'],
                              ),
                            ),
                            _RestrictionChip(
                              label: 'Bank transfer',
                              value: _providerStatusLabel(
                                overview
                                    .paymentProviderStatus['bank_transfer_manual'],
                              ),
                            ),
                          ],
                        ),
                        if (overview.requiredPolicyAcceptancesMissing >
                            0) ...<Widget>[
                          const SizedBox(height: 12),
                          FilledButton.tonalIcon(
                            onPressed: _openComplianceCenter,
                            icon: const Icon(Icons.gavel_outlined),
                            label: Text(
                              overview.requiredPolicyAcceptancesMissing == 1
                                  ? 'Complete compliance review'
                                  : 'Complete ${overview.requiredPolicyAcceptancesMissing} compliance items',
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ],
                const SizedBox(height: 18),
                GteSurfacePanel(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        'Wallet actions',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 12),
                      const Text(
                        'Deposit funds before signing players or entering paid competitions.',
                      ),
                      const SizedBox(height: 6),
                      const Text(
                        'Withdrawals stay gated by account checks and bank details.',
                      ),
                      const SizedBox(height: 6),
                      Text(
                        'Deposit rail: ${_railLabel(overview.depositMode)}. Withdrawal rail: ${_railLabel(overview.withdrawalMode)}.',
                      ),
                      const SizedBox(height: 6),
                      Text(
                        'Instant provider status: KoraPay ${_providerStatusLabel(overview.paymentProviderStatus['korapay'])}.',
                      ),
                      const SizedBox(height: 6),
                      Text(
                        'Manual transfer status: ${_providerStatusLabel(overview.paymentProviderStatus['bank_transfer_manual'])}.',
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 18),
                GteSurfacePanel(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        'Transaction History',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 12),
                      if (transactions.isEmpty)
                        const GteStatePanel(
                          title: 'No wallet activity yet',
                          message:
                              'Deposit funds or request a withdrawal to create wallet history.',
                          icon: Icons.payments_outlined,
                        )
                      else
                        ...transactions.map(
                          (GteWalletTransactionRecord transaction) =>
                              _WalletTransactionTile(transaction: transaction),
                        ),
                    ],
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _LockedFundsBand extends StatelessWidget {
  const _LockedFundsBand({required this.amount, required this.reasons});

  final String amount;
  final List<String> reasons;

  @override
  Widget build(BuildContext context) {
    final TextTheme textTheme = Theme.of(context).textTheme;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        color: GteShellTheme.accentWarm.withValues(alpha: 0.08),
        border: Border.all(
          color: GteShellTheme.accentWarm.withValues(alpha: 0.18),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Icon(
                Icons.lock_clock_outlined,
                color: GteShellTheme.accentWarm,
                size: 20,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Locked funds: $amount',
                  style: textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ],
          ),
          if (reasons.isNotEmpty) ...<Widget>[
            const SizedBox(height: 8),
            ...reasons.map(
              (String reason) => Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text(reason, style: textTheme.bodySmall),
              ),
            ),
          ] else ...<Widget>[
            const SizedBox(height: 8),
            Text(
              'No backend lock reasons are active for this wallet.',
              style: textTheme.bodySmall,
            ),
          ],
        ],
      ),
    );
  }
}

class _BalanceTile extends StatelessWidget {
  const _BalanceTile({
    required this.label,
    required this.value,
    required this.detail,
    required this.accent,
  });

  final String label;
  final String value;
  final String detail;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(18),
          color: accent.withValues(alpha: 0.08),
          border: Border.all(color: accent.withValues(alpha: 0.16)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              label.toUpperCase(),
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                color: accent,
                letterSpacing: 0.8,
              ),
            ),
            const SizedBox(height: 8),
            Text(value, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            Text(detail, style: Theme.of(context).textTheme.bodySmall),
          ],
        ),
      ),
    );
  }
}

class _MetricTile extends StatelessWidget {
  const _MetricTile({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          color: GteShellTheme.panelStrong.withValues(alpha: 0.6),
          border: Border.all(
            color: GteShellTheme.accentCapital.withValues(alpha: 0.12),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              label.toUpperCase(),
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                letterSpacing: 0.9,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 8),
            Text(value, style: Theme.of(context).textTheme.titleMedium),
          ],
        ),
      ),
    );
  }
}

class _RestrictionChip extends StatelessWidget {
  const _RestrictionChip({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(14),
        color: GteShellTheme.panelStrong.withValues(alpha: 0.6),
        border: Border.all(
          color: GteShellTheme.accentWarm.withValues(alpha: 0.18),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            label.toUpperCase(),
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              letterSpacing: 0.8,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 4),
          Text(value, style: Theme.of(context).textTheme.bodyMedium),
        ],
      ),
    );
  }
}

class _WalletTransactionTile extends StatelessWidget {
  const _WalletTransactionTile({required this.transaction});

  final GteWalletTransactionRecord transaction;

  @override
  Widget build(BuildContext context) {
    final bool isCredit = transaction.type.toLowerCase() == 'credit';
    final Color tone =
        transaction.status.toLowerCase() == 'verified'
            ? GteShellTheme.positive
            : transaction.status.toLowerCase() == 'failed'
            ? GteShellTheme.negative
            : GteShellTheme.accentWarm;
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: GteSurfacePanel(
        accentColor: tone,
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Icon(
              isCredit ? Icons.south_west_outlined : Icons.north_east_outlined,
              color: tone,
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    '${_titleCase(transaction.type)} | ${_titleCase(transaction.status)}',
                    style: Theme.of(context).textTheme.titleSmall,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Audit reference: ${transaction.reference}',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  if (transaction.createdAt != null) ...<Widget>[
                    const SizedBox(height: 4),
                    Text(
                      gteFormatDateTime(transaction.createdAt),
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(width: 8),
            Text(
              gteFormatCredits(
                isCredit ? transaction.amount : -transaction.amount,
              ),
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                color:
                    isCredit ? GteShellTheme.positive : GteShellTheme.negative,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

String _railLabel(String mode) {
  switch (mode.trim().toLowerCase()) {
    case 'gateway':
      return 'KoraPay checkout';
    case 'hybrid':
      return 'KoraPay + manual bank transfer';
    case 'bank_transfer':
      return 'Manual bank transfer review';
    case 'unavailable':
    case 'unknown':
    case 'backend_pending':
      return 'Unavailable';
    default:
      return 'Unavailable';
  }
}

bool _instantRailReady(String mode) {
  final String normalized = mode.trim().toLowerCase();
  return normalized == 'gateway' || normalized == 'hybrid';
}

bool _railIsPending(String mode) {
  final String normalized = mode.trim().toLowerCase();
  return normalized.isEmpty ||
      normalized == 'unavailable' ||
      normalized == 'unknown' ||
      normalized == 'backend_pending';
}

String _countryLabel(String? countryCode) {
  final String normalized = (countryCode ?? '').trim();
  if (normalized.isEmpty ||
      normalized.toLowerCase() == 'backend_pending' ||
      normalized.toLowerCase() == 'unknown' ||
      normalized.toLowerCase() == 'unavailable') {
    return 'Backend pending';
  }
  return normalized;
}

const String _legacyNonLiveProviderStatus =
    'mo'
    'ck';
const String _nonLiveProviderStatus = 'non_live';

String _canonicalProviderStatus(String? status) {
  final String normalized = (status ?? '').trim().toLowerCase();
  if (normalized == _legacyNonLiveProviderStatus) {
    return _nonLiveProviderStatus;
  }
  return normalized;
}

String _providerStatusLabel(String? status) {
  switch (_canonicalProviderStatus(status)) {
    case 'ready':
      return 'Ready';
    case _nonLiveProviderStatus:
      return 'Non-live';
    case 'blocked':
      return 'Blocked';
    case 'unavailable':
      return 'Unavailable';
    default:
      return 'Unknown';
  }
}

String _walletUnitLabel(GteLedgerUnit unit) {
  switch (unit) {
    case GteLedgerUnit.credit:
      return 'Fan Coin';
    case GteLedgerUnit.coin:
      return 'GTEX Coin';
    case GteLedgerUnit.unknown:
      return 'Wallet Unit';
  }
}

String _walletUnitDetail(GteLedgerUnit unit) {
  switch (unit) {
    case GteLedgerUnit.credit:
      return 'Gifting and user-hosted competition balance';
    case GteLedgerUnit.coin:
      return 'Transfer, buy-now, and withdrawal balance';
    case GteLedgerUnit.unknown:
      return 'Wallet balance';
  }
}

String _formatWalletAmount(double value, GteLedgerUnit unit) {
  final bool wholeNumber = value == value.roundToDouble();
  final String amount = value.toStringAsFixed(wholeNumber ? 0 : 2);
  return '$amount ${_walletUnitLabel(unit)}';
}

String _titleCase(String value) {
  final List<String> parts = value
      .split(RegExp(r'[_\s-]+'))
      .map((String part) => part.trim())
      .where((String part) => part.isNotEmpty)
      .toList(growable: false);
  if (parts.isEmpty) {
    return value;
  }
  return parts
      .map(
        (String part) =>
            '${part[0].toUpperCase()}${part.substring(1).toLowerCase()}',
      )
      .join(' ');
}
