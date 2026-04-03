import 'package:flutter/material.dart';

import '../../core/app_feedback.dart';
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

  Future<void> _openConvertToFanCoin() async {
    final TextEditingController amountController = TextEditingController();
    bool converted = false;
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (BuildContext context) {
        GteWalletConversionQuote? quote;
        String? error;
        bool isQuoting = false;
        bool isSubmitting = false;

        return StatefulBuilder(
          builder: (BuildContext context, StateSetter modalSetState) {
            Future<void> previewQuote() async {
              final double? amount = double.tryParse(
                amountController.text.trim(),
              );
              if (amount == null || amount <= 0) {
                modalSetState(() {
                  error = 'Enter a valid GTEX Coin amount to preview.';
                  quote = null;
                });
                return;
              }
              modalSetState(() {
                error = null;
                isQuoting = true;
              });
              try {
                final GteWalletConversionQuote response = await widget
                    .controller
                    .api
                    .quoteWalletConversion(
                      GteWalletConversionQuoteRequest(amount: amount),
                    );
                modalSetState(() {
                  quote = response;
                });
              } catch (conversionError) {
                modalSetState(() {
                  error = AppFeedback.messageFor(conversionError);
                  quote = null;
                });
              } finally {
                if (context.mounted) {
                  modalSetState(() {
                    isQuoting = false;
                  });
                }
              }
            }

            Future<void> submitConversion() async {
              final double? amount = double.tryParse(
                amountController.text.trim(),
              );
              if (amount == null || amount <= 0) {
                modalSetState(() {
                  error = 'Enter a valid GTEX Coin amount to convert.';
                });
                return;
              }
              if (quote == null) {
                modalSetState(() {
                  error = 'Preview the conversion before submitting.';
                });
                return;
              }
              modalSetState(() {
                error = null;
                isSubmitting = true;
              });
              try {
                await widget.controller.api.createWalletConversion(
                  GteWalletConversionRequest(amount: amount),
                );
                converted = true;
                if (!context.mounted) {
                  return;
                }
                Navigator.of(context).pop();
              } catch (conversionError) {
                modalSetState(() {
                  error = AppFeedback.messageFor(conversionError);
                });
              } finally {
                if (context.mounted) {
                  modalSetState(() {
                    isSubmitting = false;
                  });
                }
              }
            }

            return Padding(
              padding: EdgeInsets.fromLTRB(
                20,
                20,
                20,
                20 + MediaQuery.of(context).viewInsets.bottom,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    'Convert GTEX to Fan Coin',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Fan Coin is for gifting and user-hosted competition spending. Fan Coin cannot be converted back into GTEX Coin.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: amountController,
                    keyboardType: const TextInputType.numberWithOptions(
                      decimal: true,
                    ),
                    decoration: const InputDecoration(
                      labelText: 'GTEX Coin amount',
                      prefixIcon: Icon(Icons.compare_arrows_outlined),
                    ),
                  ),
                  const SizedBox(height: 14),
                  if (quote case final GteWalletConversionQuote preview)
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(18),
                        color: GteShellTheme.panelStrong.withValues(alpha: 0.7),
                        border: Border.all(
                          color: GteShellTheme.accentCapital.withValues(
                            alpha: 0.18,
                          ),
                        ),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(
                            'Preview',
                            style: Theme.of(context).textTheme.titleSmall,
                          ),
                          const SizedBox(height: 8),
                          Text(
                            '${gteFormatAmountForUnit(preview.sourceAmount, preview.sourceUnit)} -> ${gteFormatAmountForUnit(preview.targetAmount, preview.targetUnit)}',
                          ),
                          const SizedBox(height: 6),
                          Text(
                            'Rate: 1 GTEX Coin = ${preview.rate.toStringAsFixed(0)} Fan Coin',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        ],
                      ),
                    ),
                  if (error != null) ...<Widget>[
                    const SizedBox(height: 14),
                    GteStatePanel(
                      title: 'Conversion unavailable',
                      message: error!,
                      icon: Icons.warning_amber_rounded,
                    ),
                  ],
                  const SizedBox(height: 16),
                  Wrap(
                    spacing: 10,
                    runSpacing: 10,
                    children: <Widget>[
                      FilledButton.tonalIcon(
                        onPressed:
                            isQuoting || isSubmitting ? null : previewQuote,
                        icon: const Icon(Icons.preview_outlined),
                        label: Text(
                          isQuoting ? 'Previewing...' : 'Preview conversion',
                        ),
                      ),
                      FilledButton.icon(
                        onPressed:
                            isQuoting || isSubmitting ? null : submitConversion,
                        icon: const Icon(Icons.check_circle_outline),
                        label: Text(
                          isSubmitting ? 'Converting...' : 'Convert now',
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            );
          },
        );
      },
    );
    amountController.dispose();
    if (converted) {
      await _refresh();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Wallets'),
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
          if (!snapshot.hasData || snapshot.data!.length < 4) {
            return const Center(
              child: GteStatePanel(
                title: 'Wallets unavailable',
                message: 'Unable to load the wallet balances right now.',
                icon: Icons.account_balance_wallet_outlined,
              ),
            );
          }

          final GteWalletSummary tradeWallet =
              snapshot.data![0] as GteWalletSummary;
          final GteWalletSummary fanWallet =
              snapshot.data![1] as GteWalletSummary;
          final List<GteWalletTransactionRecord> transactions =
              snapshot.data![2] as List<GteWalletTransactionRecord>;
          final GteWithdrawalEligibility eligibility =
              snapshot.data![3] as GteWithdrawalEligibility;

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
                        'Production wallet rails',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'GTEX Coin funds player trading and withdrawals. Fan Coin covers gifting and user-hosted competition creation.',
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
                          const SizedBox(width: 12),
                          _BalanceTile(
                            label: 'Fan Coin',
                            value: gteFormatAmountForUnit(
                              fanWallet.availableBalance,
                              fanWallet.currency,
                            ),
                            detail: 'Gifting and hosted competitions',
                            accent: GteShellTheme.accentWarm,
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
                            label: 'Fan conversion',
                            value: 'GTEX only',
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
                            onPressed: _openConvertToFanCoin,
                            icon: const Icon(Icons.swap_horiz_outlined),
                            label: const Text('Convert to Fan Coin'),
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
                        'Fan Coin cannot be converted into GTEX Coin.',
                      ),
                      const SizedBox(height: 6),
                      const Text(
                        'User-hosted competitions spend Fan Coin. Player trading uses GTEX Coin.',
                      ),
                      const SizedBox(height: 6),
                      const Text(
                        'GTEX competition winnings settle into the GTEX wallet and use the same withdrawal rail.',
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
                              'Top up GTEX Coin, convert to Fan Coin, or request a withdrawal to create wallet history.',
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
