import 'package:flutter/material.dart';

import '../../data/gte_models.dart';
import '../../providers/gte_exchange_controller.dart';
import '../../widgets/gte_formatters.dart';
import '../../widgets/gte_shell_theme.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/gte_surface_panel.dart';
import 'gte_deposit_history_screen.dart';
import 'gte_funding_flow_screen.dart';
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
      widget.controller.api.fetchWalletSummary(currency: GteLedgerUnit.coin),
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

  Future<void> _openTopUp() async {
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
            (_) => GteWithdrawalEligibilityScreen(
              controller: widget.controller,
            ),
      ),
    );
    await _refresh();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('GTEX wallet'),
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
          if (!snapshot.hasData || snapshot.data!.length < 3) {
            return const Center(
              child: GteStatePanel(
                title: 'GTEX wallet unavailable',
                message: 'Unable to load the GTEX wallet balances right now.',
                icon: Icons.account_balance_wallet_outlined,
              ),
            );
          }

          final GteWalletSummary tradeWallet =
              snapshot.data![0] as GteWalletSummary;
          final List<GteWalletTransactionRecord> transactions =
              snapshot.data![1] as List<GteWalletTransactionRecord>;
          final GteWithdrawalEligibility eligibility =
              snapshot.data![2] as GteWithdrawalEligibility;

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
                        'GTEX Coin wallet',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Top up GTEX Coin, buy player assets, and withdraw verified balances from one live wallet lane.',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 16),
                      Row(
                        children: <Widget>[
                          _BalanceTile(
                            label: 'GTEX Coin',
                            value: gteFormatAmountForUnit(
                              tradeWallet.availableBalance,
                              tradeWallet.currency,
                            ),
                            detail: 'Trading and withdrawal balance',
                            accent: GteShellTheme.accentCapital,
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
                            label: 'Trading rail',
                            value: 'GTEX Coin only',
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      Wrap(
                        spacing: 10,
                        runSpacing: 10,
                        children: <Widget>[
                          FilledButton.icon(
                            onPressed: _openTopUp,
                            icon: const Icon(Icons.add_circle_outline),
                            label: const Text('Top up GTEX'),
                          ),
                          OutlinedButton.icon(
                            onPressed: _openWithdrawals,
                            icon: const Icon(Icons.outbox_outlined),
                            label: const Text('Withdraw'),
                          ),
                          OutlinedButton.icon(
                            onPressed: _openTransactions,
                            icon: const Icon(Icons.receipt_long_outlined),
                            label: const Text('Transactions'),
                          ),
                        ],
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
                        'Wallet rules',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 12),
                      const Text(
                        'GTEX Coin is the only live wallet currency in this shell.',
                      ),
                      const SizedBox(height: 6),
                      const Text(
                        'Player trading, portfolio settlement, and withdrawals all clear through GTEX Coin.',
                      ),
                      const SizedBox(height: 6),
                      const Text(
                        'Competition winnings and wallet top-ups settle into the same GTEX withdrawal rail.',
                      ),
                      const SizedBox(height: 6),
                      Text(
                        eligibility.policyBlocked
                            ? eligibility.policyBlockReason ??
                                'Policy action is required before full withdrawal access is enabled.'
                            : eligibility.requiresKyc
                            ? 'KYC is still required before withdrawals are enabled.'
                            : eligibility.requiresBankAccount
                            ? 'Add an active bank account before requesting withdrawals.'
                            : 'Wallet compliance is ready for live funding and withdrawals.',
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
                        'Recent GTEX wallet activity',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 12),
                      if (transactions.isEmpty)
                        const GteStatePanel(
                          title: 'No wallet activity yet',
                          message:
                              'Top up GTEX Coin or request a withdrawal to create wallet history.',
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
