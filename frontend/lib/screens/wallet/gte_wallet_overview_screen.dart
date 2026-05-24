import 'package:flutter/material.dart';

import '../../data/gte_models.dart';
import '../../providers/gte_exchange_controller.dart';
import '../../widgets/gte_formatters.dart';
import '../../widgets/gte_shell_theme.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/gte_surface_panel.dart';
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
  late Future<List<Object?>> _walletFuture;

  @override
  void initState() {
    super.initState();
    _walletFuture = _loadWallet();
  }

  Future<List<Object?>> _loadWallet() {
    return Future.wait<Object?>(<Future<Object?>>[
      widget.controller.api.fetchWalletOverview(),
      widget.controller.api.fetchWalletSummary(currency: GteLedgerUnit.coin),
      widget.controller.api.fetchWalletSummary(currency: GteLedgerUnit.credit),
      widget.controller.api.listWalletTransactions(limit: 8),
      widget.controller.api.fetchWithdrawalEligibility(),
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
          if (!snapshot.hasData || snapshot.data!.length < 5) {
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
          final GteWalletSummary coinSummary =
              snapshot.data![1] as GteWalletSummary;
          final GteWalletSummary fanSummary =
              snapshot.data![2] as GteWalletSummary;
          final List<GteWalletTransactionRecord> transactions =
              snapshot.data![3] as List<GteWalletTransactionRecord>;
          final GteWithdrawalEligibility eligibility =
              snapshot.data![4] as GteWithdrawalEligibility;
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
                  : overview.depositMode != 'gateway' &&
                      overview.depositMode != 'hybrid'
                  ? 'Instant funding is currently routed through manual bank transfer review.'
                  : 'Wallet compliance is ready for live funding and withdrawals.';
          final bool showRestrictionPanel =
              overview.policyBlocked ||
              eligibility.policyBlocked ||
              eligibility.requiresKyc ||
              eligibility.requiresBankAccount ||
              (overview.depositMode != 'gateway' &&
                  overview.depositMode != 'hybrid');

          return RefreshIndicator(
            onRefresh: _refresh,
            child: ListView(
              padding: const EdgeInsets.all(20),
              children: <Widget>[
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
                            label: _walletUnitLabel(coinSummary.currency),
                            value: _formatWalletAmount(
                              coinSummary.availableBalance,
                              coinSummary.currency,
                            ),
                            detail: _walletUnitDetail(coinSummary.currency),
                            accent: GteShellTheme.accentCapital,
                          ),
                          const SizedBox(width: 12),
                          _BalanceTile(
                            label: _walletUnitLabel(fanSummary.currency),
                            value: _formatWalletAmount(
                              fanSummary.availableBalance,
                              fanSummary.currency,
                            ),
                            detail: _walletUnitDetail(fanSummary.currency),
                            accent: GteShellTheme.accent,
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      Row(
                        children: <Widget>[
                          _MetricTile(
                            label: 'Withdrawable now',
                            value: gteFormatCredits(
                              eligibility.withdrawableNow,
                            ),
                          ),
                          const SizedBox(width: 12),
                          _MetricTile(
                            label: 'Funding rail',
                            value: _railLabel(overview.depositMode),
                          ),
                        ],
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
                              value: overview.countryCode ?? 'GLOBAL',
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
                        'Instant provider status: KoraPay ${_providerStatusLabel(overview.paymentProviderStatus['korapay'])}. Manual bank transfer is handled through admin review.',
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
                    transaction.reference,
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
      return 'Automatic gateway';
    case 'hybrid':
      return 'Gateway + bank transfer';
    case 'bank_transfer':
    default:
      return 'Bank transfer review';
  }
}

String _providerStatusLabel(String? status) {
  switch ((status ?? '').trim().toLowerCase()) {
    case 'ready':
      return 'Ready';
    case 'mock':
      return 'Test mode';
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
