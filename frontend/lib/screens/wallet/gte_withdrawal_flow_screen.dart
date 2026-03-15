import 'package:flutter/material.dart';

import '../../core/app_feedback.dart';
import '../../data/gte_models.dart';
import '../../providers/gte_exchange_controller.dart';
import '../../widgets/gte_formatters.dart';
import '../../widgets/gte_shell_theme.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/gte_surface_panel.dart';
import '../support/gte_support_dispute_screens.dart';
import 'gte_bank_details_screen.dart';
import 'gte_kyc_screen.dart';

class GteWithdrawalEligibilityScreen extends StatefulWidget {
  const GteWithdrawalEligibilityScreen({
    super.key,
    required this.controller,
  });

  final GteExchangeController controller;

  @override
  State<GteWithdrawalEligibilityScreen> createState() =>
      _GteWithdrawalEligibilityScreenState();
}

class _GteWithdrawalEligibilityScreenState
    extends State<GteWithdrawalEligibilityScreen> {
  late Future<GteWithdrawalEligibility> _eligibilityFuture;

  @override
  void initState() {
    super.initState();
    _eligibilityFuture = widget.controller.api.fetchWithdrawalEligibility();
  }

  Future<void> _refresh() async {
    setState(() {
      _eligibilityFuture = widget.controller.api.fetchWithdrawalEligibility();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Withdrawals'),
        actions: <Widget>[
          IconButton(onPressed: _refresh, icon: const Icon(Icons.refresh)),
        ],
      ),
      body: FutureBuilder<GteWithdrawalEligibility>(
        future: _eligibilityFuture,
        builder: (BuildContext context,
            AsyncSnapshot<GteWithdrawalEligibility> snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (!snapshot.hasData) {
            return const Center(
              child: GteStatePanel(
                title: 'Eligibility unavailable',
                message: 'We could not load withdrawal eligibility.',
                icon: Icons.warning_amber_rounded,
              ),
            );
          }
          final GteWithdrawalEligibility eligibility = snapshot.data!;
          return RefreshIndicator(
            onRefresh: _refresh,
            child: ListView(
              padding: const EdgeInsets.all(20),
              children: <Widget>[
                GteSurfacePanel(
                  emphasized: true,
                  accentColor: GteShellTheme.accentCapital,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text('Withdrawable now',
                          style: Theme.of(context).textTheme.titleLarge),
                      const SizedBox(height: 8),
                      Text(
                        gteFormatCredits(eligibility.withdrawableNow),
                        style: Theme.of(context)
                            .textTheme
                            .displaySmall
                            ?.copyWith(fontSize: 30),
                      ),
                      const SizedBox(height: 12),
                      Text(
                        'Remaining allowance: ${gteFormatCredits(eligibility.remainingAllowance)}',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        eligibility.nextEligibleAt == null
                            ? 'No throttling window in effect.'
                            : 'Next eligibility: ${gteFormatDateTime(eligibility.nextEligibleAt)}',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 18),
                GteSurfacePanel(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text('Eligibility checks',
                          style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 12),
                      _StatusRow(
                        label: 'KYC status',
                        value: _kycLabel(eligibility.kycStatus),
                        ok: !eligibility.requiresKyc,
                      ),
                      const SizedBox(height: 8),
                      _StatusRow(
                        label: 'Bank details',
                        value: eligibility.requiresBankAccount
                            ? 'Required'
                            : 'On file',
                        ok: !eligibility.requiresBankAccount,
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 18),
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: <Widget>[
                    OutlinedButton.icon(
                      onPressed: () {
                        Navigator.of(context).push<void>(
                          MaterialPageRoute<void>(
                            builder: (BuildContext context) => GteKycScreen(
                              controller: widget.controller,
                            ),
                          ),
                        );
                      },
                      icon: const Icon(Icons.verified_user_outlined),
                      label: const Text('Complete KYC'),
                    ),
                    OutlinedButton.icon(
                      onPressed: () {
                        Navigator.of(context).push<void>(
                          MaterialPageRoute<void>(
                            builder: (BuildContext context) =>
                                GteBankDetailsScreen(
                              controller: widget.controller,
                            ),
                          ),
                        );
                      },
                      icon: const Icon(Icons.account_balance_outlined),
                      label: const Text('Bank details'),
                    ),
                    FilledButton.icon(
                      onPressed: eligibility.withdrawableNow > 0 &&
                              !eligibility.requiresKyc &&
                              !eligibility.requiresBankAccount
                          ? () {
                              Navigator.of(context).push<void>(
                                MaterialPageRoute<void>(
                                  builder: (BuildContext context) =>
                                      GteWithdrawalRequestScreen(
                                    controller: widget.controller,
                                    eligibility: eligibility,
                                  ),
                                ),
                              );
                            }
                          : null,
                      icon: const Icon(Icons.payments_outlined),
                      label: const Text('Request withdrawal'),
                    ),
                    OutlinedButton.icon(
                      onPressed: () {
                        Navigator.of(context).push<void>(
                          MaterialPageRoute<void>(
                            builder: (BuildContext context) =>
                                GteWithdrawalHistoryScreen(
                              controller: widget.controller,
                            ),
                          ),
                        );
                      },
                      icon: const Icon(Icons.history),
                      label: const Text('History'),
                    ),
                  ],
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

class GteWithdrawalRequestScreen extends StatefulWidget {
  const GteWithdrawalRequestScreen({
    super.key,
    required this.controller,
    required this.eligibility,
  });

  final GteExchangeController controller;
  final GteWithdrawalEligibility eligibility;

  @override
  State<GteWithdrawalRequestScreen> createState() =>
      _GteWithdrawalRequestScreenState();
}

class _GteWithdrawalRequestScreenState
    extends State<GteWithdrawalRequestScreen> {
  final TextEditingController _amountController = TextEditingController();
  final TextEditingController _notesController = TextEditingController();
  bool _isSubmitting = false;
  bool _isQuoting = false;
  String? _error;
  String? _quoteError;
  GteWithdrawalQuote? _quote;
  List<GteUserBankAccount> _accounts = const <GteUserBankAccount>[];
  String? _selectedBankId;
  String _sourceScope = 'trade';

  @override
  void initState() {
    super.initState();
    _loadAccounts();
  }

  Future<void> _loadAccounts() async {
    final List<GteUserBankAccount> accounts =
        await widget.controller.api.listUserBankAccounts();
    if (!mounted) {
      return;
    }
    GteUserBankAccount? activeAccount;
    for (final GteUserBankAccount account in accounts) {
      if (account.isActive) {
        activeAccount = account;
        break;
      }
    }
    setState(() {
      _accounts = accounts;
      _selectedBankId =
          activeAccount?.id ?? (accounts.isNotEmpty ? accounts.first.id : null);
    });
  }

  @override
  void dispose() {
    _amountController.dispose();
    _notesController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final double? amount = double.tryParse(_amountController.text.trim());
    if (amount == null || amount <= 0) {
      setState(() {
        _error = 'Enter a valid withdrawal amount.';
      });
      return;
    }
    if (_quote == null || _quote?.blockedReason != null) {
      setState(() {
        _error = _quote?.blockedReason ??
            'Generate a withdrawal quote before submitting.';
      });
      return;
    }
    if (_selectedBankId == null) {
      setState(() {
        _error = 'Add a bank account to continue.';
      });
      return;
    }
    setState(() {
      _isSubmitting = true;
      _error = null;
    });
    try {
      final GteTreasuryWithdrawalRequest request =
          await widget.controller.api.createWithdrawalRequest(
        GteWithdrawalCreateRequest(
          amountCoin: amount,
          bankAccountId: _selectedBankId,
          sourceScope: _sourceScope,
          notes:
              _notesController.text.trim().isEmpty ? null : _notesController.text.trim(),
        ),
      );
      if (!mounted) {
        return;
      }
      await Navigator.of(context).push<void>(
        MaterialPageRoute<void>(
          builder: (BuildContext context) => GteWithdrawalReceiptScreen(
            controller: widget.controller,
            withdrawalId: request.id,
            reference: request.reference,
          ),
        ),
      );
      if (mounted) {
        Navigator.of(context).pop();
      }
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = AppFeedback.messageFor(error);
      });
    } finally {
      if (mounted) {
        setState(() {
          _isSubmitting = false;
        });
      }
    }
  }

  Future<void> _requestQuote() async {
    final double? amount = double.tryParse(_amountController.text.trim());
    if (amount == null || amount <= 0) {
      setState(() {
        _quoteError = 'Enter a valid amount to preview a quote.';
        _quote = null;
      });
      return;
    }
    setState(() {
      _isQuoting = true;
      _quoteError = null;
    });
    try {
      final GteWithdrawalQuote quote =
          await widget.controller.api.fetchWithdrawalQuote(
        GteWithdrawalQuoteRequest(
          amountCoin: amount,
          sourceScope: _sourceScope,
        ),
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _quote = quote;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _quoteError = AppFeedback.messageFor(error);
        _quote = null;
      });
    } finally {
      if (mounted) {
        setState(() {
          _isQuoting = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Request withdrawal')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: <Widget>[
          GteSurfacePanel(
            emphasized: true,
            accentColor: GteShellTheme.accentCapital,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text('Withdrawable now',
                    style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 8),
                Text(
                  gteFormatCredits(widget.eligibility.withdrawableNow),
                  style: Theme.of(context)
                      .textTheme
                      .displaySmall
                      ?.copyWith(fontSize: 28),
                ),
                const SizedBox(height: 14),
                Text('Withdrawal source',
                    style: Theme.of(context).textTheme.titleSmall),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: <Widget>[
                    ChoiceChip(
                      label: const Text('Trade balance'),
                      selected: _sourceScope == 'trade',
                      onSelected: _isSubmitting
                          ? null
                          : (_) {
                              setState(() {
                                _sourceScope = 'trade';
                                _quote = null;
                              });
                            },
                    ),
                    ChoiceChip(
                      label: const Text('Competition rewards'),
                      selected: _sourceScope == 'competition',
                      onSelected: _isSubmitting
                          ? null
                          : (_) {
                              setState(() {
                                _sourceScope = 'competition';
                                _quote = null;
                              });
                            },
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                TextField(
                  controller: _amountController,
                  keyboardType:
                      const TextInputType.numberWithOptions(decimal: true),
                  decoration: const InputDecoration(
                    labelText: 'Amount (coins)',
                    prefixIcon: Icon(Icons.payments_outlined),
                  ),
                ),
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton.tonalIcon(
                    onPressed: _isQuoting ? null : _requestQuote,
                    icon: const Icon(Icons.receipt_long_outlined),
                    label: Text(
                      _isQuoting ? 'Generating quote...' : 'Preview quote',
                    ),
                  ),
                ),
              ],
            ),
          ),
          if (_isQuoting) ...<Widget>[
            const SizedBox(height: 16),
            const GteSurfacePanel(
              child: Text('Generating withdrawal quote...'),
            ),
          ] else if (_quoteError != null) ...<Widget>[
            const SizedBox(height: 16),
            GteStatePanel(
              title: 'Quote unavailable',
              message: _quoteError!,
              icon: Icons.warning_amber_outlined,
              actionLabel: 'Retry',
              onAction: _requestQuote,
            ),
          ] else if (_quote != null) ...<Widget>[
            const SizedBox(height: 16),
            GteSurfacePanel(
              accentColor: _quote?.blockedReason != null
                  ? GteShellTheme.accentWarm
                  : GteShellTheme.accentCapital,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text('Withdrawal quote',
                      style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 12,
                    runSpacing: 12,
                    children: <Widget>[
                      _QuoteMetric(
                        label: 'Gross',
                        value: gteFormatCredits(_quote!.grossAmount),
                      ),
                      _QuoteMetric(
                        label: 'Fee',
                        value: gteFormatCredits(_quote!.feeAmount),
                      ),
                      _QuoteMetric(
                        label: 'Total debit',
                        value: gteFormatCredits(_quote!.totalDebit),
                      ),
                      _QuoteMetric(
                        label: 'Est. payout',
                        value: gteFormatFiat(
                          _quote!.estimatedFiatPayout,
                          currency: _quote!.currencyCode,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Text(
                    'Processor: ${_quote!.processorMode.replaceAll('_', ' ')} • Channel: ${_quote!.payoutChannel.replaceAll('_', ' ')}',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  if (_quote!.blockedReason != null) ...<Widget>[
                    const SizedBox(height: 12),
                    GteStatePanel(
                      title: 'Withdrawal blocked',
                      message: _quote!.blockedReason!,
                      icon: Icons.block_outlined,
                    ),
                  ],
                ],
              ),
            ),
          ],
          const SizedBox(height: 16),
          GteSurfacePanel(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text('Payout destination',
                    style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 12),
                if (_accounts.isEmpty)
                  GteStatePanel(
                    title: 'Bank details required',
                    message:
                        'Add a bank account before submitting a withdrawal request.',
                    icon: Icons.account_balance_outlined,
                    actionLabel: 'Add bank details',
                    onAction: () {
                      Navigator.of(context).push<void>(
                        MaterialPageRoute<void>(
                          builder: (BuildContext context) =>
                              GteBankDetailsScreen(
                            controller: widget.controller,
                          ),
                        ),
                      ).then((_) => _loadAccounts());
                    },
                  )
                else
                  DropdownButtonFormField<String>(
                    value: _selectedBankId,
                    items: _accounts
                        .map((GteUserBankAccount account) =>
                            DropdownMenuItem<String>(
                              value: account.id,
                              child: Text(
                                  '${account.bankName} - ${account.accountNumber}'),
                            ))
                        .toList(growable: false),
                    onChanged: (String? value) {
                      setState(() {
                        _selectedBankId = value;
                      });
                    },
                    decoration: const InputDecoration(
                      labelText: 'Bank account',
                      prefixIcon: Icon(Icons.account_balance_outlined),
                    ),
                  ),
                const SizedBox(height: 12),
                TextField(
                  controller: _notesController,
                  decoration: const InputDecoration(
                    labelText: 'Notes (optional)',
                    prefixIcon: Icon(Icons.notes_outlined),
                  ),
                ),
                if (_error != null) ...<Widget>[
                  const SizedBox(height: 12),
                  GteStatePanel(
                    title: 'Withdrawal error',
                    message: _error!,
                    icon: Icons.warning_amber_rounded,
                  ),
                ],
                const SizedBox(height: 18),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton(
                    onPressed: _isSubmitting || _selectedBankId == null
                        ? null
                        : _submit,
                    child: Text(_isSubmitting ? 'Submitting...' : 'Submit'),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class GteWithdrawalReceiptScreen extends StatefulWidget {
  const GteWithdrawalReceiptScreen({
    super.key,
    required this.controller,
    required this.withdrawalId,
    this.reference,
  });

  final GteExchangeController controller;
  final String withdrawalId;
  final String? reference;

  @override
  State<GteWithdrawalReceiptScreen> createState() =>
      _GteWithdrawalReceiptScreenState();
}

class _GteWithdrawalReceiptScreenState
    extends State<GteWithdrawalReceiptScreen> {
  late Future<GteWithdrawalReceipt> _receiptFuture;

  @override
  void initState() {
    super.initState();
    _receiptFuture =
        widget.controller.api.fetchWithdrawalReceipt(widget.withdrawalId);
  }

  Future<void> _refresh() async {
    setState(() {
      _receiptFuture =
          widget.controller.api.fetchWithdrawalReceipt(widget.withdrawalId);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Withdrawal receipt'),
        actions: <Widget>[
          IconButton(onPressed: _refresh, icon: const Icon(Icons.refresh)),
        ],
      ),
      body: FutureBuilder<GteWithdrawalReceipt>(
        future: _receiptFuture,
        builder:
            (BuildContext context, AsyncSnapshot<GteWithdrawalReceipt> snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (!snapshot.hasData) {
            return GteStatePanel(
              title: 'Receipt unavailable',
              message: 'We could not load this withdrawal receipt.',
              icon: Icons.receipt_long_outlined,
              actionLabel: 'Retry',
              onAction: _refresh,
            );
          }
          final GteWithdrawalReceipt receipt = snapshot.data!;
          final GteTreasuryWithdrawalRequest withdrawal = receipt.withdrawal;
          return RefreshIndicator(
            onRefresh: _refresh,
            child: ListView(
              padding: const EdgeInsets.all(20),
              children: <Widget>[
                GteSurfacePanel(
                  emphasized: true,
                  accentColor: GteShellTheme.accentCapital,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        widget.reference ?? withdrawal.reference,
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 6),
                      Text(
                        'Status: ${gteFormatOrderStatus(_withdrawalStatusLabel(withdrawal.status))}',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      const SizedBox(height: 12),
                      Wrap(
                        spacing: 12,
                        runSpacing: 12,
                        children: <Widget>[
                          _QuoteMetric(
                            label: 'Gross',
                            value: gteFormatCredits(receipt.grossAmount),
                          ),
                          _QuoteMetric(
                            label: 'Fee',
                            value: gteFormatCredits(receipt.feeAmount),
                          ),
                          _QuoteMetric(
                            label: 'Total debit',
                            value: gteFormatCredits(receipt.totalDebit),
                          ),
                          _QuoteMetric(
                            label: 'Fiat payout',
                            value: gteFormatFiat(
                              withdrawal.amountFiat,
                              currency: withdrawal.currencyCode,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                GteSurfacePanel(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text('Payout destination',
                          style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 8),
                      Text(
                        '${withdrawal.bankName} • ${withdrawal.bankAccountNumber}',
                      ),
                      const SizedBox(height: 6),
                      Text(
                        withdrawal.bankAccountName,
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      const SizedBox(height: 12),
                      Text(
                        'Processor: ${receipt.processorMode.replaceAll('_', ' ')}',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      Text(
                        'Channel: ${receipt.payoutChannel.replaceAll('_', ' ')}',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      const SizedBox(height: 12),
                      Text(
                        'Created ${gteFormatDateTime(withdrawal.createdAt)}',
                        style: Theme.of(context).textTheme.bodySmall,
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

class GteWithdrawalHistoryScreen extends StatefulWidget {
  const GteWithdrawalHistoryScreen({
    super.key,
    required this.controller,
  });

  final GteExchangeController controller;

  @override
  State<GteWithdrawalHistoryScreen> createState() =>
      _GteWithdrawalHistoryScreenState();
}

class _GteWithdrawalHistoryScreenState
    extends State<GteWithdrawalHistoryScreen> {
  late Future<List<GteTreasuryWithdrawalRequest>> _withdrawalsFuture;

  @override
  void initState() {
    super.initState();
    _withdrawalsFuture = widget.controller.api.listWithdrawalRequests();
  }

  Future<void> _refresh() async {
    setState(() {
      _withdrawalsFuture = widget.controller.api.listWithdrawalRequests();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Withdrawal history'),
        actions: <Widget>[
          IconButton(onPressed: _refresh, icon: const Icon(Icons.refresh)),
        ],
      ),
      body: FutureBuilder<List<GteTreasuryWithdrawalRequest>>(
        future: _withdrawalsFuture,
        builder: (BuildContext context,
            AsyncSnapshot<List<GteTreasuryWithdrawalRequest>> snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          final List<GteTreasuryWithdrawalRequest> withdrawals =
              snapshot.data ?? <GteTreasuryWithdrawalRequest>[];
          if (withdrawals.isEmpty) {
            return const Center(
              child: GteStatePanel(
                title: 'No withdrawals yet',
                message: 'Submit a withdrawal request to see it here.',
                icon: Icons.payments_outlined,
              ),
            );
          }
          return RefreshIndicator(
            onRefresh: _refresh,
            child: ListView.separated(
              padding: const EdgeInsets.all(20),
              itemCount: withdrawals.length,
              separatorBuilder: (_, __) => const SizedBox(height: 12),
              itemBuilder: (BuildContext context, int index) {
                final GteTreasuryWithdrawalRequest withdrawal =
                    withdrawals[index];
                return GteSurfacePanel(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(withdrawal.reference,
                          style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 6),
                      Text(
                        'Status: ${gteFormatOrderStatus(_withdrawalStatusLabel(withdrawal.status))}',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      const SizedBox(height: 6),
                      Text(
                        '${gteFormatCredits(withdrawal.amountCoin)} - ${gteFormatFiat(withdrawal.amountFiat, currency: withdrawal.currencyCode)}',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 6),
                      Text(
                        'Created ${gteFormatDateTime(withdrawal.createdAt)}',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      const SizedBox(height: 12),
                      Wrap(
                        spacing: 12,
                        runSpacing: 12,
                        children: <Widget>[
                          OutlinedButton(
                            onPressed: () {
                              Navigator.of(context).push<void>(
                                MaterialPageRoute<void>(
                                  builder: (BuildContext context) =>
                                      GteWithdrawalReceiptScreen(
                                    controller: widget.controller,
                                    withdrawalId: withdrawal.id,
                                    reference: withdrawal.reference,
                                  ),
                                ),
                              );
                            },
                            child: const Text('View receipt'),
                          ),
                          OutlinedButton(
                            onPressed: () {
                              Navigator.of(context).push<void>(
                                MaterialPageRoute<void>(
                                  builder: (BuildContext context) =>
                                      GteDisputeCreateScreen(
                                    controller: widget.controller,
                                    reference: withdrawal.reference,
                                    resourceId: withdrawal.id,
                                    resourceType: 'withdrawal',
                                  ),
                                ),
                              );
                            },
                            child: const Text('Open dispute'),
                          ),
                        ],
                      ),
                    ],
                  ),
                );
              },
            ),
          );
        },
      ),
    );
  }
}

class _QuoteMetric extends StatelessWidget {
  const _QuoteMetric({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        color: Colors.white.withValues(alpha: 0.04),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Text(label, style: Theme.of(context).textTheme.labelMedium),
          const SizedBox(height: 4),
          Text(value, style: Theme.of(context).textTheme.titleMedium),
        ],
      ),
    );
  }
}

class _StatusRow extends StatelessWidget {
  const _StatusRow({
    required this.label,
    required this.value,
    required this.ok,
  });

  final String label;
  final String value;
  final bool ok;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: <Widget>[
        Icon(ok ? Icons.check_circle : Icons.warning_amber_rounded,
            color: ok ? GteShellTheme.positive : GteShellTheme.warning),
        const SizedBox(width: 8),
        Expanded(
          child: Text('$label: $value',
              style: Theme.of(context).textTheme.bodyMedium),
        ),
      ],
    );
  }
}

String _kycLabel(GteKycStatus status) {
  switch (status) {
    case GteKycStatus.unverified:
      return 'Unverified';
    case GteKycStatus.pending:
      return 'Pending';
    case GteKycStatus.partialVerifiedNoId:
      return 'Partial (no ID)';
    case GteKycStatus.fullyVerified:
      return 'Verified';
    case GteKycStatus.rejected:
      return 'Rejected';
  }
}

String _withdrawalStatusLabel(GteWithdrawalStatus status) {
  switch (status) {
    case GteWithdrawalStatus.draft:
      return 'draft';
    case GteWithdrawalStatus.pendingKyc:
      return 'pending_kyc';
    case GteWithdrawalStatus.pendingReview:
      return 'pending_review';
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
  }
}
