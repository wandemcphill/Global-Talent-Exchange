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
                        'Wallet command desk',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 6),
                      Text(
                        'Club funds',
                        style: Theme.of(context).textTheme.labelSmall,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Two live balances, two jobs: GTC moves football capital, FNC powers fan activity, gifts, and community play.',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 16),
                      LayoutBuilder(
                        builder: (
                          BuildContext context,
                          BoxConstraints constraints,
                        ) {
                          final bool stacked = constraints.maxWidth < 680;
                          final List<Widget> cards = <Widget>[
                            _CoinBalanceCard(
                              title: 'GTEX Coin',
                              code: 'GTC',
                              icon: Icons.monetization_on_outlined,
                              summary: coinSummary,
                              accent: GteShellTheme.accentCapital,
                              description:
                                  'Transfer bids, player purchases, trader settlement, and withdrawals.',
                              primaryActionLabel: 'Deposit',
                              secondaryActionLabel: 'Withdraw GTC',
                              onPrimaryAction: _openDeposit,
                              onSecondaryAction: _openWithdrawals,
                            ),
                            _CoinBalanceCard(
                              title: 'Fan Coin',
                              code: 'FNC',
                              icon: Icons.stars_outlined,
                              summary: fanSummary,
                              accent: const Color(0xFF3D7EFF),
                              description:
                                  'Gifting, reactions, community entry fees, and fan economy rewards.',
                              primaryActionLabel: 'View FNC history',
                              secondaryActionLabel: 'Not withdrawable',
                              onPrimaryAction: _openTransactions,
                              onSecondaryAction: null,
                            ),
                          ];
                          if (stacked) {
                            return Column(
                              children: cards
                                  .map(
                                    (Widget card) => Padding(
                                      padding: const EdgeInsets.only(
                                        bottom: 12,
                                      ),
                                      child: card,
                                    ),
                                  )
                                  .toList(growable: false),
                            );
                          }
                          return Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              Expanded(child: cards[0]),
                              const SizedBox(width: 12),
                              Expanded(child: cards[1]),
                            ],
                          );
                        },
                      ),
                      const SizedBox(height: 16),
                      LayoutBuilder(
                        builder: (
                          BuildContext context,
                          BoxConstraints constraints,
                        ) {
                          final bool stacked = constraints.maxWidth < 560;
                          final List<Widget> metrics = <Widget>[
                            _MetricTile(
                              label: 'Withdrawable GTC',
                              value: gteFormatGtc(eligibility.withdrawableNow),
                            ),
                            _MetricTile(
                              label: 'Funding rail',
                              value: _railLabel(overview.depositMode),
                            ),
                          ];
                          if (stacked) {
                            return Column(
                              children: metrics
                                  .map(
                                    (Widget metric) => Padding(
                                      padding: const EdgeInsets.only(
                                        bottom: 12,
                                      ),
                                      child: metric,
                                    ),
                                  )
                                  .toList(growable: false),
                            );
                          }
                          return Row(
                            children: <Widget>[
                              Expanded(child: metrics[0]),
                              const SizedBox(width: 12),
                              Expanded(child: metrics[1]),
                            ],
                          );
                        },
                      ),
                      const SizedBox(height: 16),
                      Wrap(
                        spacing: 10,
                        runSpacing: 10,
                        children: <Widget>[
                          _WalletQuickAction(
                            label: 'Top up via KoraPay',
                            detail: _providerStatusLabel(
                              overview.paymentProviderStatus['korapay'],
                            ),
                            icon: Icons.open_in_new_outlined,
                            accent: GteShellTheme.accentCapital,
                            onPressed: _openDeposit,
                          ),
                          _WalletQuickAction(
                            label: 'Manual deposit',
                            detail: 'Admin review',
                            icon: Icons.account_balance_outlined,
                            accent: GteShellTheme.accentWarm,
                            onPressed: _openDeposit,
                          ),
                          _WalletQuickAction(
                            label: 'Withdraw GTC',
                            detail: _railLabel(overview.withdrawalMode),
                            icon: Icons.outbox_outlined,
                            accent: GteShellTheme.positive,
                            onPressed: _openWithdrawals,
                          ),
                          _WalletQuickAction(
                            label: 'Transaction history',
                            detail: '${transactions.length} recent records',
                            icon: Icons.receipt_long_outlined,
                            accent: GteShellTheme.accent,
                            onPressed: _openTransactions,
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      Text(
                        'Live funding is available through KoraPay checkout or manual bank transfer review.',
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

class _CoinBalanceCard extends StatelessWidget {
  const _CoinBalanceCard({
    required this.title,
    required this.code,
    required this.icon,
    required this.summary,
    required this.accent,
    required this.description,
    required this.primaryActionLabel,
    required this.secondaryActionLabel,
    required this.onPrimaryAction,
    required this.onSecondaryAction,
  });

  final String title;
  final String code;
  final IconData icon;
  final GteWalletSummary summary;
  final Color accent;
  final String description;
  final String primaryActionLabel;
  final String secondaryActionLabel;
  final VoidCallback? onPrimaryAction;
  final VoidCallback? onSecondaryAction;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(22),
        gradient: RadialGradient(
          center: Alignment.topRight,
          radius: 1.2,
          colors: <Color>[
            accent.withValues(alpha: 0.24),
            GteShellTheme.panelStrong.withValues(alpha: 0.72),
          ],
        ),
        border: Border.all(color: accent.withValues(alpha: 0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: accent.withValues(alpha: 0.16),
                  border: Border.all(color: accent.withValues(alpha: 0.3)),
                ),
                child: Icon(icon, color: accent),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      code,
                      style: Theme.of(context).textTheme.labelLarge?.copyWith(
                        color: accent,
                        letterSpacing: 0.8,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    Text(
                      title.toUpperCase(),
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 18),
          Text(
            gteFormatShortAmountForUnit(
              summary.availableBalance,
              summary.currency,
            ),
            style: Theme.of(
              context,
            ).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 8),
          Text(description, style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: 14),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: <Widget>[
              _RestrictionChip(
                label: 'Reserved',
                value: gteFormatShortAmountForUnit(
                  summary.reservedBalance,
                  summary.currency,
                ),
              ),
              _RestrictionChip(
                label: 'Total',
                value: gteFormatShortAmountForUnit(
                  summary.totalBalance,
                  summary.currency,
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: <Widget>[
              FilledButton.tonalIcon(
                onPressed: onPrimaryAction,
                icon: const Icon(Icons.arrow_circle_down_outlined),
                label: Text(primaryActionLabel),
              ),
              OutlinedButton.icon(
                onPressed: onSecondaryAction,
                icon: const Icon(Icons.arrow_circle_up_outlined),
                label: Text(secondaryActionLabel),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _WalletQuickAction extends StatelessWidget {
  const _WalletQuickAction({
    required this.label,
    required this.detail,
    required this.icon,
    required this.accent,
    required this.onPressed,
  });

  final String label;
  final String detail;
  final IconData icon;
  final Color accent;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 210,
      child: OutlinedButton.icon(
        onPressed: onPressed,
        icon: Icon(icon, color: accent),
        label: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Text(label, maxLines: 1, overflow: TextOverflow.ellipsis),
            Text(
              detail,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.labelSmall,
            ),
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
    return Container(
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
    final String normalizedType = transaction.type.toLowerCase();
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
            Container(
              width: 42,
              height: 42,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: tone.withValues(alpha: 0.12),
                border: Border.all(color: tone.withValues(alpha: 0.2)),
              ),
              child: Icon(_transactionIcon(normalizedType), color: tone),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    _transactionTitle(normalizedType, isCredit),
                    style: Theme.of(context).textTheme.titleSmall,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '${_titleCase(transaction.status)} - ${transaction.reference}',
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
              gteFormatGtc(isCredit ? transaction.amount : -transaction.amount),
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

IconData _transactionIcon(String type) {
  if (type.contains('withdraw')) {
    return Icons.account_balance_outlined;
  }
  if (type.contains('trade')) {
    return Icons.currency_exchange_outlined;
  }
  if (type.contains('purchase') || type.contains('player')) {
    return Icons.person_search_outlined;
  }
  if (type.contains('rent')) {
    return Icons.flag_outlined;
  }
  return type.contains('credit')
      ? Icons.south_west_outlined
      : Icons.north_east_outlined;
}

String _transactionTitle(String type, bool isCredit) {
  if (type.contains('deposit')) {
    return 'Wallet deposit';
  }
  if (type.contains('withdraw')) {
    return 'Withdrawal request';
  }
  if (type.contains('trade')) {
    return 'Coin trade settlement';
  }
  if (type.contains('purchase')) {
    return 'Player purchase';
  }
  if (type.contains('rent')) {
    return 'National rental payment';
  }
  return isCredit ? 'Wallet credit' : 'Wallet debit';
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
