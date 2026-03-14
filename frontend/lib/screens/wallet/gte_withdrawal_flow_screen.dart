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
  String? _error;
  List<GteUserBankAccount> _accounts = const <GteUserBankAccount>[];
  String? _selectedBankId;

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
          notes:
              _notesController.text.trim().isEmpty ? null : _notesController.text.trim(),
        ),
      );
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Withdrawal ${request.reference} submitted.'),
        ),
      );
      Navigator.of(context).pop();
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
                    onPressed:
                        _isSubmitting || _selectedBankId == null ? null : _submit,
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
                );
              },
            ),
          );
        },
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
