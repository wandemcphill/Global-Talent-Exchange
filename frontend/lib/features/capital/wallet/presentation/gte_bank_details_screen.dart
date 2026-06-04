import 'package:flutter/material.dart';

import 'package:gte_frontend/core/app_feedback.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/features/capital/wallet/data/capital_wallet_api.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/widgets/gte_formatters.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class GteBankDetailsScreen extends StatefulWidget {
  const GteBankDetailsScreen({super.key, required this.controller});

  final GteExchangeController controller;

  @override
  State<GteBankDetailsScreen> createState() => _GteBankDetailsScreenState();
}

class _GteBankDetailsScreenState extends State<GteBankDetailsScreen> {
  CapitalWalletApi get _walletApi => widget.controller.walletApi;
  late Future<List<GteUserBankAccount>> _accountsFuture;

  @override
  void initState() {
    super.initState();
    _accountsFuture = _walletApi.listUserBankAccounts();
  }

  Future<void> _refresh() async {
    setState(() {
      _accountsFuture = _walletApi.listUserBankAccounts();
    });
  }

  Future<void> _openForm([GteUserBankAccount? account]) async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder:
            (BuildContext context) => GteBankDetailsFormScreen(
              controller: widget.controller,
              account: account,
            ),
      ),
    );
    await _refresh();
  }

  Future<void> _setPrimary(GteUserBankAccount account) async {
    try {
      await _walletApi.updateUserBankAccount(
        account.id,
        const GteUserBankAccountUpdate(isActive: true),
      );
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('${account.bankName} is now primary.')),
      );
      await _refresh();
    } catch (error) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(AppFeedback.messageFor(error))));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Bank details'),
        actions: <Widget>[
          IconButton(onPressed: _refresh, icon: const Icon(Icons.refresh)),
          IconButton(onPressed: () => _openForm(), icon: const Icon(Icons.add)),
        ],
      ),
      body: FutureBuilder<List<GteUserBankAccount>>(
        future: _accountsFuture,
        builder: (
          BuildContext context,
          AsyncSnapshot<List<GteUserBankAccount>> snapshot,
        ) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError && !snapshot.hasData) {
            return Center(
              child: GteStatePanel(
                title: 'Bank details unavailable',
                message:
                    'We could not sync saved payout bank accounts from the backend.',
                icon: Icons.sync_problem_outlined,
                actionLabel: 'Retry',
                onAction: _refresh,
              ),
            );
          }
          final List<GteUserBankAccount> accounts =
              snapshot.data ?? <GteUserBankAccount>[];
          if (accounts.isEmpty) {
            return Center(
              child: GteStatePanel(
                title: 'No bank details on file',
                message:
                    'Add a bank account to receive withdrawals and payouts.',
                icon: Icons.account_balance_outlined,
                actionLabel: 'Add bank details',
                onAction: () => _openForm(),
              ),
            );
          }
          return RefreshIndicator(
            onRefresh: _refresh,
            child: ListView.separated(
              padding: const EdgeInsets.all(20),
              itemCount: accounts.length,
              separatorBuilder: (_, __) => const SizedBox(height: 12),
              itemBuilder: (BuildContext context, int index) {
                final GteUserBankAccount account = accounts[index];
                return GteSurfacePanel(
                  emphasized: account.isActive,
                  accentColor:
                      account.isActive ? GteShellTheme.accentCapital : null,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        account.bankName,
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 6),
                      Text(
                        '${account.accountName} - ${account.accountNumber}',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      const SizedBox(height: 6),
                      Text(
                        'Audit reference: ${account.id}',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      const SizedBox(height: 6),
                      Text(
                        'Currency: ${account.currencyCode} - ${_bankAccountCreatedLabel(account.createdAt)}',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      const SizedBox(height: 12),
                      Wrap(
                        spacing: 8,
                        children: <Widget>[
                          OutlinedButton(
                            onPressed: () => _openForm(account),
                            child: const Text('Edit'),
                          ),
                          if (!account.isActive)
                            OutlinedButton(
                              onPressed: () => _setPrimary(account),
                              child: const Text('Set primary'),
                            ),
                          if (account.isActive)
                            const Chip(label: Text('Primary')),
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

class GteBankDetailsFormScreen extends StatefulWidget {
  const GteBankDetailsFormScreen({
    super.key,
    required this.controller,
    this.account,
  });

  final GteExchangeController controller;
  final GteUserBankAccount? account;

  @override
  State<GteBankDetailsFormScreen> createState() =>
      _GteBankDetailsFormScreenState();
}

class _GteBankDetailsFormScreenState extends State<GteBankDetailsFormScreen> {
  CapitalWalletApi get _walletApi => widget.controller.walletApi;
  late final TextEditingController _bankNameController;
  late final TextEditingController _accountNumberController;
  late final TextEditingController _accountNameController;
  late final TextEditingController _bankCodeController;
  late final TextEditingController _currencyCodeController;
  bool _setPrimary = true;
  bool _isSubmitting = false;
  String? _error;

  bool get _isEditing => widget.account != null;

  @override
  void initState() {
    super.initState();
    _bankNameController = TextEditingController(
      text: widget.account?.bankName ?? '',
    );
    _accountNumberController = TextEditingController(
      text: widget.account?.accountNumber ?? '',
    );
    _accountNameController = TextEditingController(
      text: widget.account?.accountName ?? '',
    );
    _bankCodeController = TextEditingController(
      text: widget.account?.bankCode ?? '',
    );
    _currencyCodeController = TextEditingController(
      text: widget.account?.currencyCode ?? '',
    );
    _setPrimary = widget.account?.isActive ?? true;
  }

  @override
  void dispose() {
    _bankNameController.dispose();
    _accountNumberController.dispose();
    _accountNameController.dispose();
    _bankCodeController.dispose();
    _currencyCodeController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final String bankName = _bankNameController.text.trim();
    final String accountNumber = _accountNumberController.text.trim();
    final String accountName = _accountNameController.text.trim();
    final String bankCode = _bankCodeController.text.trim();
    final String currencyCode =
        _currencyCodeController.text.trim().toUpperCase();

    if (bankName.isEmpty || accountNumber.isEmpty || accountName.isEmpty) {
      setState(() {
        _error = 'Complete all required fields.';
      });
      return;
    }
    if (currencyCode.isEmpty) {
      setState(() {
        _error = 'Currency code is required.';
      });
      return;
    }

    setState(() {
      _isSubmitting = true;
      _error = null;
    });

    try {
      if (_isEditing) {
        await _walletApi.updateUserBankAccount(
          widget.account!.id,
          GteUserBankAccountUpdate(
            bankName: bankName,
            accountNumber: accountNumber,
            accountName: accountName,
            bankCode: bankCode.isEmpty ? null : bankCode,
            currencyCode: currencyCode,
            isActive: _setPrimary,
          ),
        );
      } else {
        await _walletApi.createUserBankAccount(
          GteUserBankAccountCreate(
            bankName: bankName,
            accountNumber: accountNumber,
            accountName: accountName,
            bankCode: bankCode.isEmpty ? null : bankCode,
            currencyCode: currencyCode,
            setActive: _setPrimary,
          ),
        );
      }
      if (!mounted) {
        return;
      }
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
      appBar: AppBar(
        title: Text(_isEditing ? 'Edit bank details' : 'Add bank details'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: <Widget>[
          GteSurfacePanel(
            emphasized: true,
            accentColor: GteShellTheme.accentCapital,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  'Account details',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _bankNameController,
                  decoration: const InputDecoration(
                    labelText: 'Bank name',
                    prefixIcon: Icon(Icons.account_balance_outlined),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _accountNumberController,
                  decoration: const InputDecoration(
                    labelText: 'Account number',
                    prefixIcon: Icon(Icons.numbers_outlined),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _accountNameController,
                  decoration: const InputDecoration(
                    labelText: 'Account name',
                    prefixIcon: Icon(Icons.person_outline),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _bankCodeController,
                  decoration: const InputDecoration(
                    labelText: 'Bank code (optional)',
                    prefixIcon: Icon(Icons.qr_code_outlined),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _currencyCodeController,
                  textCapitalization: TextCapitalization.characters,
                  decoration: const InputDecoration(
                    labelText: 'Currency code',
                    prefixIcon: Icon(Icons.payments_outlined),
                  ),
                ),
                const SizedBox(height: 12),
                SwitchListTile(
                  value: _setPrimary,
                  onChanged: (bool value) {
                    setState(() {
                      _setPrimary = value;
                    });
                  },
                  title: const Text('Set as primary account'),
                  contentPadding: EdgeInsets.zero,
                ),
                if (_error != null) ...<Widget>[
                  const SizedBox(height: 12),
                  GteStatePanel(
                    title: 'Bank details error',
                    message: _error!,
                    icon: Icons.warning_amber_rounded,
                  ),
                ],
                const SizedBox(height: 18),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton(
                    onPressed: _isSubmitting ? null : _submit,
                    child: Text(
                      _isSubmitting ? 'Saving...' : 'Save bank details',
                    ),
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

String _bankAccountCreatedLabel(DateTime? createdAt) {
  if (createdAt == null) {
    return 'Added timestamp pending';
  }
  return 'Added ${gteFormatDateTime(createdAt)}';
}
