import 'package:flutter/material.dart';

import '../../core/app_feedback.dart';
import '../../data/gte_models.dart';
import '../../providers/gte_exchange_controller.dart';
import '../../widgets/gte_formatters.dart';
import '../../widgets/gte_shell_theme.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/gte_surface_panel.dart';

class GteBankDetailsScreen extends StatefulWidget {
  const GteBankDetailsScreen({
    super.key,
    required this.controller,
  });

  final GteExchangeController controller;

  @override
  State<GteBankDetailsScreen> createState() => _GteBankDetailsScreenState();
}

class _GteBankDetailsScreenState extends State<GteBankDetailsScreen> {
  late Future<List<GteUserBankAccount>> _accountsFuture;

  @override
  void initState() {
    super.initState();
    _accountsFuture = widget.controller.api.listUserBankAccounts();
  }

  Future<void> _refresh() async {
    setState(() {
      _accountsFuture = widget.controller.api.listUserBankAccounts();
    });
  }

  Future<void> _openForm([GteUserBankAccount? account]) async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => GteBankDetailsFormScreen(
          controller: widget.controller,
          account: account,
        ),
      ),
    );
    await _refresh();
  }

  Future<void> _setPrimary(GteUserBankAccount account) async {
    try {
      await widget.controller.api.updateUserBankAccount(
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
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(AppFeedback.messageFor(error))),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Bank details'),
        actions: <Widget>[
          IconButton(onPressed: _refresh, icon: const Icon(Icons.refresh)),
          IconButton(
            onPressed: () => _openForm(),
            icon: const Icon(Icons.add),
          ),
        ],
      ),
      body: FutureBuilder<List<GteUserBankAccount>>(
        future: _accountsFuture,
        builder: (BuildContext context,
            AsyncSnapshot<List<GteUserBankAccount>> snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
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
                  accentColor: account.isActive
                      ? GteShellTheme.accentCapital
                      : null,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(account.bankName,
                          style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 6),
                      Text(
                        '${account.accountName} - ${account.accountNumber}',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      const SizedBox(height: 6),
                      Text(
                        'Currency: ${account.currencyCode} - Added ${gteFormatDateTime(account.createdAt)}',
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
  late final TextEditingController _bankNameController;
  late final TextEditingController _accountNumberController;
  late final TextEditingController _accountNameController;
  late final TextEditingController _bankCodeController;
  bool _setPrimary = true;
  bool _isSubmitting = false;
  String? _error;

  bool get _isEditing => widget.account != null;

  @override
  void initState() {
    super.initState();
    _bankNameController = TextEditingController(
        text: widget.account?.bankName ?? '');
    _accountNumberController = TextEditingController(
        text: widget.account?.accountNumber ?? '');
    _accountNameController = TextEditingController(
        text: widget.account?.accountName ?? '');
    _bankCodeController =
        TextEditingController(text: widget.account?.bankCode ?? '');
    _setPrimary = widget.account?.isActive ?? true;
  }

  @override
  void dispose() {
    _bankNameController.dispose();
    _accountNumberController.dispose();
    _accountNameController.dispose();
    _bankCodeController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final String bankName = _bankNameController.text.trim();
    final String accountNumber = _accountNumberController.text.trim();
    final String accountName = _accountNameController.text.trim();
    final String bankCode = _bankCodeController.text.trim();

    if (bankName.isEmpty || accountNumber.isEmpty || accountName.isEmpty) {
      setState(() {
        _error = 'Complete all required fields.';
      });
      return;
    }

    setState(() {
      _isSubmitting = true;
      _error = null;
    });

    try {
      if (_isEditing) {
        await widget.controller.api.updateUserBankAccount(
          widget.account!.id,
          GteUserBankAccountUpdate(
            bankName: bankName,
            accountNumber: accountNumber,
            accountName: accountName,
            bankCode: bankCode.isEmpty ? null : bankCode,
            isActive: _setPrimary,
          ),
        );
      } else {
        await widget.controller.api.createUserBankAccount(
          GteUserBankAccountCreate(
            bankName: bankName,
            accountNumber: accountNumber,
            accountName: accountName,
            bankCode: bankCode.isEmpty ? null : bankCode,
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
                Text('Account details',
                    style: Theme.of(context).textTheme.titleMedium),
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
                    child: Text(_isSubmitting ? 'Saving...' : 'Save bank details'),
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
